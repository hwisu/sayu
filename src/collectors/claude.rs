use anyhow::{Result, Context};
use async_trait::async_trait;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use crate::domain::{Event, EventKind, EventSource, Actor};
use crate::collectors::{Collector, base::{BaseCollector, CollectorResult}};

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

impl Default for ClaudeCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl BaseCollector for ClaudeCollector {
    fn debug(&self) -> bool {
        self.debug
    }
    
    fn source_name(&self) -> &str {
        "Claude"
    }
}

impl ClaudeCollector {
    pub fn new() -> Self {
        Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
        }
    }
    
    fn get_claude_projects_dir(&self) -> Result<PathBuf> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        Ok(home.join(".claude").join("projects"))
    }
    
    fn escape_repo_path(&self, repo_root: &Path) -> String {
        // Convert repo path to Claude's escaped format
        // e.g., /Users/hwisookim/sayu -> -Users-hwisookim-sayu
        repo_root.to_string_lossy().replace("/", "-")
    }
    
    fn find_project_folder(&self, repo_root: &Path) -> Result<Option<PathBuf>> {
        let projects_dir = self.get_claude_projects_dir()?;
        
        if !self.check_path_exists(&projects_dir, "Claude projects directory") {
            return Ok(None);
        }
        
        let escaped_path = self.escape_repo_path(repo_root);
        self.debug_log(&format!("Looking for Claude project folder: {}", escaped_path));
        
        let project_folder = projects_dir.join(&escaped_path);
        if !self.check_path_exists(&project_folder, "Project folder") {
            return Ok(None);
        }
        
        Ok(Some(project_folder))
    }
    
    fn get_conversation_paths(&self, repo_root: &Path) -> CollectorResult<Vec<PathBuf>> {
        let project_folder = match self.find_project_folder(repo_root)? {
            Some(folder) => folder,
            None => return Ok(vec![]),
        };
        
        // Find all .jsonl files in the project folder
        let entries = self.read_directory(&project_folder)?;
        let conversation_files: Vec<PathBuf> = entries
            .into_iter()
            .filter(|path| path.extension().and_then(|s| s.to_str()) == Some("jsonl"))
            .collect();
        
        self.debug_log(&format!("Found {} Claude conversation files", conversation_files.len()));
        Ok(conversation_files)
    }
    
    fn extract_repo_name(&self, file_path: &Path) -> String {
        file_path
            .parent()
            .and_then(|p| p.file_name())
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .replace("-", "/")
    }
    
    fn parse_message_line(&self, line: &str, repo_name: &str) -> Option<Event> {
        if line.trim().is_empty() {
            return None;
        }
        
        let msg: ClaudeMessage = match serde_json::from_str(line) {
            Ok(m) => m,
            Err(e) => {
                self.debug_log(&format!("Failed to parse Claude message line: {}", e));
                return None;
            }
        };
        
        // Skip non-user/assistant messages
        if !self.is_conversation_message(&msg) {
            return None;
        }
        
        let timestamp = self.extract_timestamp(&msg);
        let inner = msg.message.as_ref()?;
        let content = inner.content.as_ref()?;
        let text = self.extract_text_content(content)?;
        
        if text.is_empty() {
            return None;
        }
        
        let actor = self.determine_actor(inner, &msg);
        
        // Create event
        let mut event = self.create_event(
            EventSource::Claude,
            EventKind::Conversation,
            repo_name.to_string(),
            text,
            timestamp,
            actor,
        );
        
        // Add metadata
        if let Some(uuid) = msg.uuid {
            event = event.with_meta("message_id".to_string(), serde_json::Value::String(uuid));
        }
        
        Some(event)
    }
    
    fn is_conversation_message(&self, msg: &ClaudeMessage) -> bool {
        matches!(msg.msg_type.as_deref(), Some("user") | Some("assistant"))
    }
    
    fn extract_timestamp(&self, msg: &ClaudeMessage) -> i64 {
        msg.timestamp
            .as_ref()
            .and_then(|ts| self.parse_timestamp(ts))
            .unwrap_or_else(|| {
                self.debug_log("No valid timestamp found, using 0");
                0
            })
    }
    
    fn determine_actor(&self, inner: &InnerMessage, msg: &ClaudeMessage) -> Actor {
        match inner.role.as_deref() {
            Some("user") | Some("human") => Actor::User,
            Some("assistant") => Actor::Assistant,
            _ => match msg.msg_type.as_deref() {
                Some("user") => Actor::User,
                Some("assistant") => Actor::Assistant,
                _ => Actor::User,
            }
        }
    }
    
    fn parse_conversation_file(&self, file_path: &Path, since_ts: Option<i64>) -> CollectorResult<Vec<Event>> {
        let content = std::fs::read_to_string(file_path)
            .with_context(|| format!("Failed to read file: {:?}", file_path))?;
        
        let repo_name = self.extract_repo_name(file_path);
        
        let events: Vec<Event> = content
            .lines()
            .filter_map(|line| self.parse_message_line(line, &repo_name))
            .collect();
        
        // Filter and sort events
        let events = self.filter_events_by_timestamp(events, since_ts);
        Ok(events)
    }
    
    fn collect_from_files(&self, paths: Vec<PathBuf>, since_ts: Option<i64>) -> Vec<Event> {
        let mut all_events = Vec::new();
        
        for path in paths {
            match self.parse_conversation_file(&path, since_ts) {
                Ok(events) => {
                    if !events.is_empty() {
                        self.debug_log(&format!("Found {} events in {:?}", events.len(), path.file_name()));
                    }
                    all_events.extend(events);
                },
                Err(e) => {
                    self.debug_error(&format!("Error parsing file {:?}", path), &e);
                }
            }
        }
        
        all_events
    }
}

#[async_trait]
impl Collector for ClaudeCollector {
    fn source(&self) -> EventSource {
        EventSource::Claude
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let conversation_paths = self.get_conversation_paths(repo_root)?;
        let mut all_events = self.collect_from_files(conversation_paths, since_ts);
        
        self.debug_log(&format!("Total {} events collected", all_events.len()));
        
        // Sort by timestamp
        all_events = self.sort_events(all_events);
        
        Ok(all_events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        let claude_dir = self.get_claude_projects_dir()?
            .parent()
            .map(|p| p.to_path_buf())
            .context("Could not get Claude directory")?;
        Ok(claude_dir.exists())
    }
}