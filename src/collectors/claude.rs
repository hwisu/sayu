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
    timestamp: Option<i64>,
    role: Option<String>,
    text: Option<String>,
    content: Option<String>,
    #[serde(rename = "conversationID")]
    conversation_id: Option<String>,
    #[serde(rename = "messageID")]
    message_id: Option<String>,
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
        
        for line in content.lines() {
            if line.trim().is_empty() {
                continue;
            }
            
            match serde_json::from_str::<ClaudeMessage>(line) {
                Ok(msg) => {
                    // Extract timestamp
                    let timestamp = msg.timestamp.unwrap_or(0);
                    
                    // Skip if before since_ts
                    if let Some(since) = since_ts {
                        if timestamp <= since {
                            continue;
                        }
                    }
                    
                    // Extract text (prefer text over content)
                    let text = msg.text.or(msg.content).unwrap_or_default();
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
                    let actor = match msg.role.as_deref() {
                        Some("user") | Some("human") => Actor::User,
                        Some("assistant") => Actor::Assistant,
                        _ => Actor::User,
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
                    if let Some(conv_id) = msg.conversation_id {
                        event = event.with_meta("conversation_id".to_string(), serde_json::Value::String(conv_id));
                    }
                    if let Some(msg_id) = msg.message_id {
                        event = event.with_meta("message_id".to_string(), serde_json::Value::String(msg_id));
                    }
                    
                    events.push(event);
                }
                Err(e) if self.debug => {
                    println!("Failed to parse Claude message line: {}", e);
                }
                _ => {}
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
                Ok(events) => all_events.extend(events),
                Err(e) if self.debug => {
                    println!("Error parsing Claude conversation file {:?}: {}", path, e);
                }
                _ => {}
            }
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