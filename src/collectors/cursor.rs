use anyhow::Result;
use async_trait::async_trait;
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::Value;
use std::path::{Path, PathBuf};
use crate::domain::{Event, EventKind, EventSource, Actor};
use crate::collectors::Collector;
use crate::prompts;

#[derive(Debug, Clone)]
pub struct CursorCollector {
    debug: bool,
}

// Note: Currently parsing JSON directly via serde_json::Value
// These structs are kept for future use if we want type-safe parsing
#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct CursorBubble {
    id: String,
    composer_id: String,
    #[serde(default)]
    messages: Vec<CursorMessage>,
    #[serde(default)]
    timestamp: i64,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct CursorMessage {
    role: String,
    content: String,
    #[serde(default)]
    timestamp: Option<i64>,
}

impl CursorCollector {
    pub fn new() -> Self {
        Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
        }
    }
    
    fn get_db_paths(&self) -> Vec<PathBuf> {
        let mut paths = Vec::new();
        let home = dirs::home_dir().unwrap_or_default();
        
        // Global database path
        let global_db = home.join(".config/Cursor/User/globalStorage/state.vscdb");
        if global_db.exists() {
            paths.push(global_db);
        }
        
        // Workspace databases
        let workspace_dir = home.join("Library/Application Support/Cursor/User/workspaceStorage");
        if workspace_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&workspace_dir) {
                for entry in entries.flatten() {
                    let state_db = entry.path().join("state.vscdb");
                    if state_db.exists() {
                        paths.push(state_db);
                    }
                }
            }
        }
        
        // Alternative workspace location
        let alt_workspace = home.join(".config/Cursor/User/workspaceStorage");
        if alt_workspace.exists() {
            if let Ok(entries) = std::fs::read_dir(&alt_workspace) {
                for entry in entries.flatten() {
                    let state_db = entry.path().join("state.vscdb");
                    if state_db.exists() {
                        paths.push(state_db);
                    }
                }
            }
        }
        
        if self.debug {
            println!("Found {} Cursor database(s)", paths.len());
        }
        
        paths
    }
    
    fn parse_cursor_database(&self, db_path: &Path, repo_name: &str, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let conn = Connection::open(db_path)?;
        let mut events = Vec::new();
        
        // Query for cursor conversation bubbles
        let query = r#"
            SELECT key, value
            FROM ItemTable
            WHERE key LIKE 'cursorDiskKV.composer.bubble.%'
               OR key LIKE 'cursorDiskKV.agentic.bubble.%'
        "#;
        
        let mut stmt = conn.prepare(query)?;
        let bubble_iter = stmt.query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?
            ))
        })?;
        
        for bubble in bubble_iter {
            let (key, value) = bubble?;
            
            // Parse the bubble JSON
            if let Ok(bubble_data) = serde_json::from_str::<Value>(&value) {
                // Extract messages from the bubble
                if let Some(messages) = bubble_data.get("messages").and_then(|m| m.as_array()) {
                    for msg in messages {
                        if let Some(role) = msg.get("role").and_then(|r| r.as_str()) {
                            if let Some(content) = msg.get("content").and_then(|c| c.as_str()) {
                                // Get timestamp (use bubble timestamp if message doesn't have one)
                                let timestamp = msg.get("timestamp")
                                    .and_then(|t| t.as_i64())
                                    .or_else(|| bubble_data.get("timestamp").and_then(|t| t.as_i64()))
                                    .unwrap_or_else(|| chrono::Utc::now().timestamp_millis());
                                
                                // Skip if before since_ts
                                if let Some(since) = since_ts {
                                    if timestamp <= since {
                                        continue;
                                    }
                                }
                                
                                // Skip tool usage messages
                                if prompts::is_tool_usage(content) {
                                    if self.debug {
                                        println!("Skipping tool usage message in Cursor");
                                    }
                                    continue;
                                }
                                
                                // Determine actor
                                let actor = match role {
                                    "user" | "human" => Actor::User,
                                    "assistant" | "ai" => Actor::Assistant,
                                    _ => Actor::User,
                                };
                                
                                // Create event
                                let mut event = Event::new(
                                    EventSource::Cursor,
                                    EventKind::Conversation,
                                    repo_name.to_string(),
                                    content.to_string(),
                                );
                                
                                event.ts = timestamp;
                                event = event.with_actor(actor);
                                
                                // Add metadata
                                if let Some(bubble_id) = bubble_data.get("id").and_then(|id| id.as_str()) {
                                    event = event.with_meta("bubble_id".to_string(), serde_json::Value::String(bubble_id.to_string()));
                                }
                                
                                if let Some(composer_id) = bubble_data.get("composerId").and_then(|id| id.as_str()) {
                                    event = event.with_meta("composer_id".to_string(), serde_json::Value::String(composer_id.to_string()));
                                }
                                
                                // Check if it's an agentic conversation
                                if key.contains("agentic") {
                                    event = event.with_meta("is_agentic".to_string(), serde_json::Value::Bool(true));
                                }
                                
                                events.push(event);
                            }
                        }
                    }
                }
            }
        }
        
        Ok(events)
    }
}

#[async_trait]
impl Collector for CursorCollector {
    fn source(&self) -> EventSource {
        EventSource::Cursor
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let db_paths = self.get_db_paths();
        let repo_name = repo_root.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown");
        
        let mut all_events = Vec::new();
        
        for db_path in db_paths {
            match self.parse_cursor_database(&db_path, repo_name, since_ts) {
                Ok(events) => all_events.extend(events),
                Err(e) if self.debug => {
                    println!("Error parsing Cursor database {:?}: {}", db_path, e);
                }
                _ => {}
            }
        }
        
        // Sort by timestamp
        all_events.sort_by_key(|e| e.ts);
        
        Ok(all_events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        // Check if any Cursor database exists
        Ok(!self.get_db_paths().is_empty())
    }
}