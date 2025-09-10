use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
pub struct LLMClient {
    api_key: String,
    model: String,
    temperature: f32,
    max_tokens: u32,
    cache: HashMap<String, CachedResponse>,
    client: reqwest::Client,
}

#[derive(Debug, Clone)]
struct CachedResponse {
    response: String,
    timestamp: Instant,
}

#[derive(Serialize)]
struct GeminiRequest {
    contents: Vec<Content>,
    generation_config: GenerationConfig,
}

#[derive(Serialize)]
struct Content {
    parts: Vec<Part>,
}

#[derive(Serialize)]
struct Part {
    text: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct GenerationConfig {
    temperature: f32,
    max_output_tokens: u32,
    response_mime_type: String,
}

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Vec<Candidate>,
}

#[derive(Deserialize)]
struct Candidate {
    content: CandidateContent,
}

#[derive(Deserialize)]
struct CandidateContent {
    parts: Vec<ResponsePart>,
}

#[derive(Deserialize)]
struct ResponsePart {
    text: String,
}

impl LLMClient {
    pub fn new() -> Result<Self> {
        let api_key = std::env::var("SAYU_GEMINI_API_KEY")
            .context("SAYU_GEMINI_API_KEY not set")?;
        
        let model = std::env::var("SAYU_LLM_MODEL")
            .unwrap_or_else(|_| "gemini-2.0-flash-exp".to_string());
        
        let temperature = std::env::var("SAYU_LLM_TEMPERATURE")
            .ok()
            .and_then(|t| t.parse().ok())
            .unwrap_or(0.7);
        
        let max_tokens = std::env::var("SAYU_LLM_MAX_TOKENS")
            .ok()
            .and_then(|t| t.parse().ok())
            .unwrap_or(1000);
        
        Ok(Self {
            api_key,
            model,
            temperature,
            max_tokens,
            cache: HashMap::new(),
            client: reqwest::Client::new(),
        })
    }
    
    pub async fn complete(&mut self, prompt: &str, use_cache: bool) -> Result<String> {
        // Check cache first
        if use_cache {
            let cache_key = self.hash_prompt(prompt);
            if let Some(cached) = self.get_cached(&cache_key) {
                return Ok(cached);
            }
        }
        
        // Build request
        let request = GeminiRequest {
            contents: vec![Content {
                parts: vec![Part {
                    text: prompt.to_string(),
                }],
            }],
            generation_config: GenerationConfig {
                temperature: self.temperature,
                max_output_tokens: self.max_tokens,
                response_mime_type: "text/plain".to_string(),
            },
        };
        
        // Make API call
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );
        
        let response = self.client
            .post(&url)
            .json(&request)
            .timeout(Duration::from_secs(30))
            .send()
            .await
            .context("Failed to send request to Gemini API")?;
        
        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Gemini API error ({}): {}", status, error_text);
        }
        
        let gemini_response: GeminiResponse = response
            .json()
            .await
            .context("Failed to parse Gemini response")?;
        
        // Extract text from response
        let text = gemini_response
            .candidates
            .first()
            .and_then(|c| c.content.parts.first())
            .map(|p| p.text.clone())
            .context("No text in Gemini response")?;
        
        // Cache the response
        if use_cache {
            let cache_key = self.hash_prompt(prompt);
            self.cache.insert(cache_key, CachedResponse {
                response: text.clone(),
                timestamp: Instant::now(),
            });
        }
        
        Ok(text)
    }
    
    fn hash_prompt(&self, prompt: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        prompt.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }
    
    fn get_cached(&self, key: &str) -> Option<String> {
        self.cache.get(key).and_then(|cached| {
            // Cache expires after 10 minutes
            if cached.timestamp.elapsed() < Duration::from_secs(600) {
                Some(cached.response.clone())
            } else {
                None
            }
        })
    }
}