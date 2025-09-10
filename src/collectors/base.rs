use anyhow::{Result, Context};
use std::path::{Path, PathBuf};
use crate::domain::{Event, EventKind, EventSource, Actor};

/// Common functionality for collectors
pub trait BaseCollector {
    fn debug(&self) -> bool;
    
    /// Log a debug message if debug mode is enabled
    fn debug_log(&self, message: &str) {
        if self.debug() {
            eprintln!("[{}] {}", self.source_name(), message);
        }
    }
    
    /// Log an error if debug mode is enabled
    fn debug_error(&self, context: &str, error: &anyhow::Error) {
        if self.debug() {
            eprintln!("[{}] {}: {:?}", self.source_name(), context, error);
        }
    }
    
    /// Get the source name for logging
    fn source_name(&self) -> &str;
    
    /// Filter events by timestamp
    fn filter_events_by_timestamp(&self, mut events: Vec<Event>, since_ts: Option<i64>) -> Vec<Event> {
        if let Some(since) = since_ts {
            let before = events.len();
            events.retain(|e| e.id >= since);
            let after = events.len();
            
            if before != after {
                self.debug_log(&format!("Filtered {} -> {} events (since {})", before, after, since));
            }
        }
        events
    }
    
    /// Sort events by timestamp
    fn sort_events(&self, mut events: Vec<Event>) -> Vec<Event> {
        events.sort_by_key(|e| e.id);
        events
    }
    
    /// Parse timestamp from various formats
    fn parse_timestamp(&self, value: &serde_json::Value) -> Option<i64> {
        match value {
            serde_json::Value::Number(n) => n.as_i64(),
            serde_json::Value::String(s) => {
                chrono::DateTime::parse_from_rfc3339(s)
                    .map(|dt| dt.timestamp_millis())
                    .ok()
            }
            _ => None,
        }
    }
    
    /// Extract text content from JSON value
    fn extract_text_content(&self, content: &serde_json::Value) -> Option<String> {
        match content {
            serde_json::Value::String(s) => Some(s.clone()),
            serde_json::Value::Array(arr) => {
                let mut combined_text = String::new();
                for item in arr {
                    if let Some(content_type) = item.get("type").and_then(|v| v.as_str()) {
                        if content_type == "text" {
                            if let Some(text) = item.get("text").and_then(|v| v.as_str()) {
                                if !combined_text.is_empty() {
                                    combined_text.push('\n');
                                }
                                combined_text.push_str(text);
                            }
                        }
                    }
                }
                if combined_text.is_empty() {
                    None
                } else {
                    Some(combined_text)
                }
            }
            _ => None,
        }
    }
    
    /// Create a new event with standard fields
    fn create_event(
        &self,
        source: EventSource,
        kind: EventKind,
        repo_name: String,
        content: String,
        timestamp: i64,
        actor: Actor,
    ) -> Event {
        Event::new(source, kind, repo_name, content)
            .with_timestamp(timestamp)
            .with_actor(actor)
    }
    
    /// Safely read directory entries
    fn read_directory(&self, path: &Path) -> Result<Vec<PathBuf>> {
        if !path.exists() {
            self.debug_log(&format!("Directory not found: {:?}", path));
            return Ok(vec![]);
        }
        
        let mut entries = Vec::new();
        for entry in std::fs::read_dir(path).context("Failed to read directory")? {
            match entry {
                Ok(e) => entries.push(e.path()),
                Err(e) => self.debug_log(&format!("Failed to read entry: {}", e)),
            }
        }
        Ok(entries)
    }
    
    /// Check if a path exists and log if it doesn't
    fn check_path_exists(&self, path: &Path, description: &str) -> bool {
        if !path.exists() {
            self.debug_log(&format!("{} not found: {:?}", description, path));
            false
        } else {
            true
        }
    }
}

/// Result type with context information
pub type CollectorResult<T> = Result<T>;

/// Helper to add context to errors
pub trait ErrorContext<T> {
    fn context_with_debug(self, context: &str, debug: bool) -> Result<T>;
}

impl<T> ErrorContext<T> for Result<T> {
    fn context_with_debug(self, context: &str, debug: bool) -> Result<T> {
        self.map_err(|e| {
            if debug {
                eprintln!("Error context: {}", context);
            }
            e
        })
    }
}