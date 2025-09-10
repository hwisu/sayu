use anyhow::{Result, Context};
use async_trait::async_trait;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use crate::domain::{Event, EventKind, EventSource, Actor};
use crate::collectors::Collector;
use crate::prompts;

#[derive(Debug, Clone)]
pub struct ClaudeCollector {
    debug: bool,
}

#[derive(Debug, Deserialize)]
struct ClaudeMessage {
    #[serde(default)]
    timestamp: Option<serde_json::Value>,  // Can be i64 or string
    #[serde(rename = "type")]
    msg_type: Option<String>,
    uuid: Option<String>,
    message: Option<InnerMessage>,
}

#[derive(Debug, Deserialize)]
struct InnerMessage {
    role: Option<String>,
    content: Option<serde_json::Value>,  // Can be string or array
}

impl ClaudeCollector {
    pub fn new() -> Self {
        Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
        }
    }
    
    fn get_conversation_paths(&self, repo_root: &Path) -> Result<Vec<PathBuf>> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let claude_projects = home.join(".claude").join("projects");
        
        if !claude_projects.exists() {
            if self.debug {
                println!("Claude projects directory not found: {:?}", claude_projects);
            }
            return Ok(vec![]);
        }
        
        // Convert repo path to Claude's escaped format
        // e.g., /Users/hwisookim/sayu -> -Users-hwisookim-sayu
        let repo_str = repo_root.to_string_lossy();
        let escaped_path = repo_str.replace("/", "-");
        
        if self.debug {
            println!("Looking for Claude project folder: {}", escaped_path);
        }
        
        let project_folder = claude_projects.join(&escaped_path);
        if !project_folder.exists() {
            if self.debug {
                println!("Project folder not found: {:?}", project_folder);
            }
            return Ok(vec![]);
        }
        
        // Find all .jsonl files in the project folder
        let mut conversation_files = Vec::new();
        for entry in std::fs::read_dir(&project_folder)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("jsonl") {
                conversation_files.push(path);
            }
        }
        
        if self.debug {
            println!("Found {} Claude conversation files", conversation_files.len());
        }
        
        Ok(conversation_files)
    }
    
    fn parse_conversation_file(&self, file_path: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let content = std::fs::read_to_string(file_path)?;
        let repo_name = file_path
            .parent()
            .and_then(|p| p.file_name())
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .replace("-", "/");
        
        let mut events = Vec::new();
        
        // First pass: collect all messages and parse timestamps
        for line in content.lines() {
            if line.trim().is_empty() {
                continue;
            }
            
            match serde_json::from_str::<ClaudeMessage>(line) {
                Ok(msg) => {
                    // Skip non-user/assistant messages
                    if msg.msg_type.as_deref() != Some("user") && msg.msg_type.as_deref() != Some("assistant") {
                        continue;
                    }
                    
                    // Extract timestamp - handle both i64 and ISO string formats
                    let timestamp = match msg.timestamp {
                        Some(serde_json::Value::Number(n)) => {
                            n.as_i64().unwrap_or(0)
                        }
                        Some(serde_json::Value::String(s)) => {
                            // Parse ISO 8601 timestamp
                            chrono::DateTime::parse_from_rfc3339(&s)
                                .map(|dt| dt.timestamp_millis())
                                .unwrap_or_else(|_| {
                                    if self.debug {
                                        println!("Failed to parse timestamp: {}", s);
                                    }
                                    0
                                })
                        }
                        _ => 0,
                    };
                    
                    // Extract inner message
                    let inner = match msg.message {
                        Some(inner) => inner,
                        None => continue,
                    };
                    
                    // Extract text from content (can be string or array)
                    let text = match inner.content {
                        Some(serde_json::Value::String(s)) => s,
                        Some(serde_json::Value::Array(arr)) => {
                            // Extract text from array of content objects
                            let mut combined_text = String::new();
                            for item in arr {
                                if let Some(content_type) = item.get("type").and_then(|v| v.as_str()) {
                                    if content_type == "text" {
                                        if let Some(text) = item.get("text").and_then(|v| v.as_str()) {
                                            if !combined_text.is_empty() {
                                                combined_text.push_str("\n");
                                            }
                                            combined_text.push_str(text);
                                        }
                                    }
                                }
                            }
                            combined_text
                        }
                        _ => String::new(),
                    };
                    
                    if text.is_empty() {
                        continue;
                    }
                    
                    // Skip tool usage messages
                    if prompts::is_tool_usage(&text) {
                        if self.debug {
                            println!("Skipping tool usage message");
                        }
                        continue;
                    }
                    
                    // Determine actor based on role
                    let actor = match inner.role.as_deref() {
                        Some("user") | Some("human") => Actor::User,
                        Some("assistant") => Actor::Assistant,
                        _ => match msg.msg_type.as_deref() {
                            Some("user") => Actor::User,
                            Some("assistant") => Actor::Assistant,
                            _ => Actor::User,
                        }
                    };
                    
                    // Create event
                    let mut event = Event::new(
                        EventSource::Claude,
                        EventKind::Conversation,
                        repo_name.clone(),
                        text,
                    );
                    
                    event.ts = timestamp;
                    event = event.with_actor(actor);
                    
                    // Add metadata
                    if let Some(uuid) = msg.uuid {
                        event = event.with_meta("message_id".to_string(), serde_json::Value::String(uuid));
                    }
                    
                    events.push(event);
                }
                Err(e) if self.debug => {
                    println!("Failed to parse Claude message line: {}", e);
                }
                _ => {}
            }
        }
        
        // Second pass: filter by timestamp
        if let Some(since) = since_ts {
            if self.debug {
                let before = events.len();
                events.retain(|e| e.ts >= since);
                let after = events.len();
                if before != after {
                    println!("Claude: Filtered {} -> {} events (since {})", before, after, since);
                }
            } else {
                events.retain(|e| e.ts >= since);
            }
        }
        
        Ok(events)
    }
}

#[async_trait]
impl Collector for ClaudeCollector {
    fn source(&self) -> EventSource {
        EventSource::Claude
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let conversation_paths = self.get_conversation_paths(repo_root)?;
        
        let mut all_events = Vec::new();
        for path in conversation_paths {
            match self.parse_conversation_file(&path, since_ts) {
                Ok(events) => {
                    if self.debug && !events.is_empty() {
                        println!("Claude: Found {} events in {:?}", events.len(), path.file_name());
                    }
                    all_events.extend(events);
                },
                Err(e) if self.debug => {
                    println!("Error parsing Claude conversation file {:?}: {}", path, e);
                }
                _ => {}
            }
        }
        
        if self.debug {
            println!("Claude: Total {} events collected", all_events.len());
        }
        
        // Sort by timestamp
        all_events.sort_by_key(|e| e.ts);
        
        Ok(all_events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let claude_dir = home.join(".claude");
        Ok(claude_dir.exists())
    }
}