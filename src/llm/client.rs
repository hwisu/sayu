use anyhow::{Result, Context};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
enum Provider {
    Gemini,
    OpenRouter,
}

#[derive(Debug, Clone)]
pub struct LLMClient {
    provider: Provider,
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

#[derive(Serialize)]
struct OpenRouterRequest {
    model: String,
    messages: Vec<OpenRouterMessage>,
    temperature: f32,
    max_tokens: u32,
}

#[derive(Serialize)]
struct OpenRouterMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct OpenRouterResponse {
    choices: Vec<OpenRouterChoice>,
}

#[derive(Deserialize)]
struct OpenRouterChoice {
    message: OpenRouterResponseMessage,
}

#[derive(Deserialize)]
struct OpenRouterResponseMessage {
    content: String,
}

impl LLMClient {
    pub fn new() -> Result<Self> {
        // Check for OpenRouter API key first (preferred for better model access)
        let (provider, api_key, default_model) = if let Ok(key) = std::env::var("SAYU_OPENROUTER_API_KEY") {
            // Popular OpenRouter models in order of preference
            let default_model = std::env::var("SAYU_LLM_MODEL").unwrap_or_else(|_| {
                // Try to use a fast, cost-effective model by default
                "anthropic/claude-3.5-haiku".to_string()
            });
            (Provider::OpenRouter, key, default_model)
        } else if let Ok(key) = std::env::var("SAYU_GEMINI_API_KEY") {
            (Provider::Gemini, key, "gemini-2.0-flash-exp".to_string())
        } else {
            anyhow::bail!(
                "No API key found. Please set one of the following environment variables:\n\
                - SAYU_OPENROUTER_API_KEY (recommended for access to multiple models)\n\
                - SAYU_GEMINI_API_KEY\n\n\
                Get your OpenRouter API key from: https://openrouter.ai/keys\n\
                Popular OpenRouter models:\n\
                - anthropic/claude-3.5-haiku (fast, cost-effective)\n\
                - anthropic/claude-3.5-sonnet (balanced)\n\
                - openai/gpt-4o-mini (fast, cheap)\n\
                - meta-llama/llama-3.1-8b-instruct (open source)"
            );
        };
        
        let model = default_model;
        
        let temperature = std::env::var("SAYU_LLM_TEMPERATURE")
            .ok()
            .and_then(|t| t.parse().ok())
            .unwrap_or(0.7);
        
        let max_tokens = std::env::var("SAYU_LLM_MAX_TOKENS")
            .ok()
            .and_then(|t| t.parse().ok())
            .unwrap_or(1000);
        
        Ok(Self {
            provider,
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
        
        let text = match self.provider {
            Provider::Gemini => self.complete_gemini(prompt).await?,
            Provider::OpenRouter => self.complete_openrouter(prompt).await?,
        };
        
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
    
    async fn complete_gemini(&self, prompt: &str) -> Result<String> {
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
        
        gemini_response
            .candidates
            .first()
            .and_then(|c| c.content.parts.first())
            .map(|p| p.text.clone())
            .context("No text in Gemini response")
    }
    
    async fn complete_openrouter(&self, prompt: &str) -> Result<String> {
        let request = OpenRouterRequest {
            model: self.model.clone(),
            messages: vec![OpenRouterMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            temperature: self.temperature,
            max_tokens: self.max_tokens,
        };
        
        let response = self.client
            .post("https://openrouter.ai/api/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("HTTP-Referer", "https://github.com/hwisookim/sayu")
            .header("X-Title", "Sayu CLI")
            .header("Content-Type", "application/json")
            .json(&request)
            .timeout(Duration::from_secs(60)) // OpenRouter can be slower, increase timeout
            .send()
            .await
            .context("Failed to send request to OpenRouter API")?;
        
        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            
            // Provide more helpful error messages for common issues
            let error_msg = match status.as_u16() {
                401 => "Invalid API key. Please check your SAYU_OPENROUTER_API_KEY".to_string(),
                402 => "Insufficient credits. Please add credits to your OpenRouter account".to_string(),
                429 => "Rate limit exceeded. Please try again later".to_string(),
                500..=599 => "OpenRouter server error. Please try again later".to_string(),
                _ => format!("OpenRouter API error ({}): {}", status, error_text),
            };
            
            anyhow::bail!("{}", error_msg);
        }
        
        let openrouter_response: OpenRouterResponse = response
            .json()
            .await
            .context("Failed to parse OpenRouter response")?;
        
        openrouter_response
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .context("No text in OpenRouter response")
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
