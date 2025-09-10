use anyhow::{Result, Context};
use async_trait::async_trait;
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::Value;
use std::path::{Path, PathBuf};
use crate::domain::{Event, EventKind, EventSource, Actor};
use crate::collectors::{Collector, base::{BaseCollector, CollectorResult}};

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

impl Default for CursorCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl BaseCollector for CursorCollector {
    fn debug(&self) -> bool {
        self.debug
    }
    
    fn source_name(&self) -> &str {
        "Cursor"
    }
}

impl CursorCollector {
    pub fn new() -> Self {
        Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
        }
    }
    
    fn get_db_paths(&self) -> Vec<PathBuf> {
        let mut paths = Vec::new();
        
        if let Some(home) = dirs::home_dir() {
            // Platform-specific database paths
            let platform_paths = self.get_platform_specific_paths(&home);
            
            for path in platform_paths {
                if path.exists() {
                    paths.push(path);
                }
            }
        }
        
        self.debug_log(&format!("Found {} Cursor database(s)", paths.len()));
        for path in &paths {
            self.debug_log(&format!("  - {:?}", path));
        }
        
        paths
    }
    
    fn get_platform_specific_paths(&self, home: &Path) -> Vec<PathBuf> {
        vec![
            // macOS
            home.join("Library/Application Support/Cursor/User/globalStorage/state.vscdb"),
            // Linux
            home.join(".config/Cursor/User/globalStorage/state.vscdb"),
            // Windows
            home.join("AppData/Roaming/Cursor/User/globalStorage/state.vscdb"),
        ]
    }
    
    fn check_table_exists(&self, conn: &Connection, table_name: &str) -> Result<bool> {
        let query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?";
        let exists = conn.prepare(query)?
            .query_map([table_name], |row| row.get::<_, String>(0))?
            .count() > 0;
        Ok(exists)
    }
    
    fn query_bubble_entries(&self, conn: &Connection) -> CollectorResult<Vec<(i64, String, String)>> {
        let query = "SELECT rowid, key, value FROM cursorDiskKV \
                     WHERE key LIKE 'bubbleId:%' \
                     AND value LIKE '%\"text\":%' \
                     ORDER BY rowid";
        
        let mut stmt = conn.prepare(query)?;
        let entries = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?
        .filter_map(|r| r.ok())
        .collect();
        
        Ok(entries)
    }
    
    fn parse_cursor_database(&self, db_path: &Path, repo_name: &str, since_ts: Option<i64>) -> CollectorResult<Vec<Event>> {
        let conn = Connection::open(db_path)
            .with_context(|| format!("Failed to open database: {:?}", db_path))?;
        
        // Check if cursorDiskKV table exists
        if !self.check_table_exists(&conn, "cursorDiskKV")? {
            self.debug_log("cursorDiskKV table not found");
            return Ok(vec![]);
        }
        
        let entries = self.query_bubble_entries(&conn)?;
        let mut events = Vec::new();
        
        self.debug_log(&format!("Processing {} bubble entries", entries.len()));
        
        for (rowid, key, value) in entries {
            // Use rowid as a pseudo-timestamp
            let pseudo_timestamp = rowid * 1000;
            
            if let Some(event) = self.parse_message(&key, &value, repo_name, pseudo_timestamp, since_ts) {
                events.push(event);
            }
        }
        
        Ok(events)
    }
    
    fn parse_message(
        &self,
        key: &str,
        value: &str,
        repo_name: &str,
        fallback_timestamp: i64,
        since_ts: Option<i64>,
    ) -> Option<Event> {
        // Skip if before since_ts
        if let Some(since) = since_ts {
            if fallback_timestamp <= since {
                return None;
            }
        }
        
        self.parse_message_internal(key, value, repo_name, fallback_timestamp)
    }
    
    fn parse_message_internal(
        &self,
        key: &str,
        value: &str,
        repo_name: &str,
        fallback_timestamp: i64,
    ) -> Option<Event> {
        self.debug_log(&format!("Processing conversation for key: {}", key));
        
        // Parse the conversation JSON
        let msg_data: Value = match serde_json::from_str(value) {
            Ok(data) => data,
            Err(e) => {
                self.debug_log(&format!("Failed to parse JSON for key {}: {}", key, e));
                return None;
            }
        };
        
        // Extract message details
        let msg_type = msg_data.get("type").and_then(|t| t.as_i64()).unwrap_or(2);
        let content = msg_data.get("text").and_then(|c| c.as_str())?;
        
        if content.trim().is_empty() {
            return None;
        }
        
        // Extract timestamp from various fields
        let timestamp = self.extract_cursor_timestamp(&msg_data, msg_type, fallback_timestamp);
        
        // Determine actor
        let actor = if msg_type == 1 {
            Actor::User
        } else {
            Actor::Assistant
        };
        
        // Create event
        let mut event = self.create_event(
            EventSource::Cursor,
            EventKind::Conversation,
            repo_name.to_string(),
            content.to_string(),
            timestamp,
            actor,
        );
        
        // Add metadata
        if let Some(bubble_id) = msg_data.get("bubbleId").and_then(|id| id.as_str()) {
            event = event.with_meta("bubble_id".to_string(), serde_json::Value::String(bubble_id.to_string()));
        }
        
        if let Some(server_bubble_id) = msg_data.get("serverBubbleId").and_then(|id| id.as_str()) {
            event = event.with_meta("server_bubble_id".to_string(), serde_json::Value::String(server_bubble_id.to_string()));
        }
        
        self.debug_log(&format!("Added {} message from bubble", 
            if msg_type == 1 { "user" } else { "assistant" }));
        
        Some(event)
    }
    
    fn extract_cursor_timestamp(&self, msg_data: &Value, msg_type: i64, fallback: i64) -> i64 {
        // Try to extract timestamp from timing info
        let timestamp = msg_data.get("timingInfo")
            .and_then(|ti| self.extract_timing_info(ti, msg_type))
            .or_else(|| self.extract_direct_timestamp(msg_data))
            .unwrap_or(fallback);
        
        if timestamp == fallback {
            self.debug_log(&format!("No timing info found, using fallback timestamp for message type {}", msg_type));
        }
        
        timestamp
    }
    
    fn extract_timing_info(&self, timing_info: &Value, msg_type: i64) -> Option<i64> {
        // For user messages (type 1), prefer send time
        // For assistant messages (type 2), prefer settle time
        if msg_type == 1 {
            timing_info.get("clientRpcSendTime").and_then(|t| t.as_i64())
                .or_else(|| timing_info.get("clientStartTime").and_then(|t| t.as_f64()).map(|t| t as i64))
                .or_else(|| timing_info.get("clientEndTime").and_then(|t| t.as_i64()))
                .or_else(|| timing_info.get("clientSettleTime").and_then(|t| t.as_i64()))
        } else {
            timing_info.get("clientSettleTime").and_then(|t| t.as_i64())
                .or_else(|| timing_info.get("clientEndTime").and_then(|t| t.as_i64()))
                .or_else(|| timing_info.get("clientRpcSendTime").and_then(|t| t.as_i64()))
                .or_else(|| timing_info.get("clientStartTime").and_then(|t| t.as_f64()).map(|t| t as i64))
        }
    }
    
    fn extract_direct_timestamp(&self, msg_data: &Value) -> Option<i64> {
        msg_data.get("clientRpcSendTime").and_then(|t| t.as_i64())
            .or_else(|| msg_data.get("clientSettleTime").and_then(|t| t.as_i64()))
            .or_else(|| msg_data.get("clientEndTime").and_then(|t| t.as_i64()))
    }
    
    fn collect_from_databases(&self, db_paths: Vec<PathBuf>, repo_name: &str, since_ts: Option<i64>) -> Vec<Event> {
        let mut all_events = Vec::new();
        
        for db_path in db_paths {
            self.debug_log(&format!("Parsing database: {:?}", db_path));
            
            match self.parse_cursor_database(&db_path, repo_name, since_ts) {
                Ok(events) => {
                    if !events.is_empty() {
                        self.debug_log(&format!("Found {} events in {:?}", events.len(), db_path.file_name()));
                    }
                    all_events.extend(events);
                },
                Err(e) => {
                    self.debug_error(&format!("Error parsing database {:?}", db_path), &e);
                }
            }
        }
        
        all_events
    }
}

#[async_trait]
impl Collector for CursorCollector {
    fn source(&self) -> EventSource {
        EventSource::Cursor
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        self.debug_log("Starting collection");
        
        let db_paths = self.get_db_paths();
        let repo_name = repo_root.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown");
        
        let mut all_events = self.collect_from_databases(db_paths, repo_name, since_ts);
        
        self.debug_log(&format!("Total {} events collected", all_events.len()));
        
        // Sort by timestamp
        all_events = self.sort_events(all_events);
        
        Ok(all_events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        // Check if any Cursor database exists
        Ok(!self.get_db_paths().is_empty())
    }
}