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
        
        // Global database path (macOS) - this is where conversations are actually stored
        let global_db = home.join("Library/Application Support/Cursor/User/globalStorage/state.vscdb");
        if global_db.exists() {
            paths.push(global_db);
        }
        
        // Alternative global database path (Linux/Windows)
        let alt_global_db = home.join(".config/Cursor/User/globalStorage/state.vscdb");
        if alt_global_db.exists() {
            paths.push(alt_global_db);
        }
        
        // Windows path
        if cfg!(windows) {
            let windows_db = home.join("AppData/Roaming/Cursor/User/globalStorage/state.vscdb");
            if windows_db.exists() {
                paths.push(windows_db);
            }
        }
        
        if self.debug {
            println!("Found {} Cursor database(s)", paths.len());
            for path in &paths {
                println!("  - {:?}", path);
            }
        }
        
        paths
    }
    
    fn parse_cursor_database(&self, db_path: &Path, repo_name: &str, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let conn = Connection::open(db_path)?;
        let mut events = Vec::new();
        
        // Check if cursorDiskKV table exists
        let table_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='cursorDiskKV'";
        let has_cursor_table = conn.prepare(table_check)?
            .query_map([], |row| row.get::<_, String>(0))?
            .count() > 0;
        
        if !has_cursor_table {
            if self.debug {
                println!("Cursor: cursorDiskKV table not found");
            }
            return Ok(events);
        }
        
        // Get all bubble entries directly from cursorDiskKV with rowid for ordering
        // Use rowid as a timestamp approximation since Cursor doesn't store actual timestamps
        let all_bubbles_query = "SELECT rowid, key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' AND value LIKE '%\"text\":%' ORDER BY rowid";
        if let Ok(mut stmt) = conn.prepare(all_bubbles_query) {
            if let Ok(mut rows) = stmt.query([]) {
                let mut count = 0;
                while let Ok(Some(row)) = rows.next() {
                    if let Ok(rowid) = row.get::<_, i64>(0) {
                        if let Ok(key) = row.get::<_, String>(1) {
                            if let Ok(value) = row.get::<_, String>(2) {
                                // Use rowid as a pseudo-timestamp (multiply by 1000 to simulate milliseconds)
                                // This gives us ordering but not real timestamps
                                let pseudo_timestamp = rowid * 1000;
                                self.parse_conversation_data_with_timestamp(&key, &value, repo_name, pseudo_timestamp, since_ts, &mut events);
                                count += 1;
                            }
                        }
                    }
                }
                if self.debug {
                    println!("Cursor: Processed {} bubble entries", count);
                }
            }
        }
        
        Ok(events)
    }
    
    fn parse_conversation_data_with_timestamp(&self, key: &str, value: &str, repo_name: &str, timestamp: i64, since_ts: Option<i64>, events: &mut Vec<Event>) {
        // Skip if before since_ts
        if let Some(since) = since_ts {
            if timestamp <= since {
                return;
            }
        }
        
        self.parse_conversation_data_internal(key, value, repo_name, timestamp, events);
    }
    
    #[allow(dead_code)]
    fn parse_conversation_data(&self, key: &str, value: &str, repo_name: &str, _since_ts: Option<i64>, events: &mut Vec<Event>) {
        // Fallback for when we don't have a timestamp
        let timestamp = chrono::Utc::now().timestamp_millis();
        self.parse_conversation_data_internal(key, value, repo_name, timestamp, events);
    }
    
    fn parse_conversation_data_internal(&self, key: &str, value: &str, repo_name: &str, fallback_timestamp: i64, events: &mut Vec<Event>) {
        if self.debug {
            println!("Cursor: Processing conversation for key: {}", key);
        }
        
        // Parse the conversation JSON - each bubble entry is a single message
        if let Ok(msg_data) = serde_json::from_str::<Value>(value) {
            // Get message type (1 = user, 2 = assistant)
            let msg_type = msg_data.get("type").and_then(|t| t.as_i64()).unwrap_or(2);
            
            // Get message text
            let content = msg_data.get("text").and_then(|c| c.as_str());
            
            if let Some(content) = content {
                // Try to get actual timestamp from various timing fields
                // Priority order:
                // 1. timingInfo.clientRpcSendTime - when request was sent (most accurate for user messages)
                // 2. timingInfo.clientSettleTime - when response was received (good for assistant messages)
                // 3. timingInfo.clientEndTime - when operation completed
                // 4. timingInfo.clientStartTime - when operation began
                // 5. Direct clientRpcSendTime field
                // 6. Fallback to rowid-based timestamp
                let timestamp = msg_data.get("timingInfo")
                    .and_then(|ti| {
                        // For user messages (type 1), prefer send time
                        // For assistant messages (type 2), prefer settle time
                        if msg_type == 1 {
                            ti.get("clientRpcSendTime").and_then(|t| t.as_i64())
                                .or_else(|| ti.get("clientStartTime").and_then(|t| t.as_f64()).map(|t| t as i64))
                                .or_else(|| ti.get("clientEndTime").and_then(|t| t.as_i64()))
                                .or_else(|| ti.get("clientSettleTime").and_then(|t| t.as_i64()))
                        } else {
                            ti.get("clientSettleTime").and_then(|t| t.as_i64())
                                .or_else(|| ti.get("clientEndTime").and_then(|t| t.as_i64()))
                                .or_else(|| ti.get("clientRpcSendTime").and_then(|t| t.as_i64()))
                                .or_else(|| ti.get("clientStartTime").and_then(|t| t.as_f64()).map(|t| t as i64))
                        }
                    })
                    .or_else(|| msg_data.get("clientRpcSendTime").and_then(|t| t.as_i64()))
                    .or_else(|| msg_data.get("clientSettleTime").and_then(|t| t.as_i64()))
                    .or_else(|| msg_data.get("clientEndTime").and_then(|t| t.as_i64()))
                    .unwrap_or(fallback_timestamp);
                
                if self.debug && timestamp == fallback_timestamp {
                    println!("Cursor: No timing info found, using fallback timestamp for message type {}", msg_type);
                }
                
                // Skip empty messages
                if content.trim().is_empty() {
                    return;
                }
                
                // Skip tool usage messages
                if prompts::is_tool_usage(content) {
                    if self.debug {
                        println!("Skipping tool usage message in Cursor");
                    }
                    return;
                }
                
                // Determine actor based on message type
                let actor = if msg_type == 1 {
                    Actor::User
                } else {
                    Actor::Assistant
                };
                
                // Create event
                let mut event = Event::new(
                    EventSource::Cursor,
                    EventKind::Conversation,
                    repo_name.to_string(),
                    content.to_string(),
                );
                
                event = event.with_timestamp(timestamp).with_actor(actor);
                
                // Add metadata
                if let Some(bubble_id) = msg_data.get("bubbleId").and_then(|id| id.as_str()) {
                    event = event.with_meta("bubble_id".to_string(), serde_json::Value::String(bubble_id.to_string()));
                }
                
                if let Some(server_bubble_id) = msg_data.get("serverBubbleId").and_then(|id| id.as_str()) {
                    event = event.with_meta("server_bubble_id".to_string(), serde_json::Value::String(server_bubble_id.to_string()));
                }
                
                events.push(event);
                
                if self.debug {
                    println!("Cursor: Added {} message from bubble", if msg_type == 1 { "user" } else { "assistant" });
                }
            } else if self.debug {
                println!("Cursor: No text field found in message data");
            }
        } else if self.debug {
            println!("Cursor: Failed to parse JSON for key: {}", key);
        }
    }
}

#[async_trait]
impl Collector for CursorCollector {
    fn source(&self) -> EventSource {
        EventSource::Cursor
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        if self.debug {
            println!("Cursor: Starting collection");
        }
        
        let db_paths = self.get_db_paths();
        let repo_name = repo_root.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown");
        
        if self.debug {
            println!("Cursor: Found {} database(s) to check", db_paths.len());
            for (i, path) in db_paths.iter().enumerate() {
                println!("Cursor: DB {}: {:?}", i + 1, path);
            }
        }
        
        let mut all_events = Vec::new();
        
        for db_path in db_paths {
            if self.debug {
                println!("Cursor: Parsing database: {:?}", db_path);
            }
            
            match self.parse_cursor_database(&db_path, repo_name, since_ts) {
                Ok(events) => {
                    if self.debug {
                        println!("Cursor: Found {} events in {:?}", events.len(), db_path.file_name());
                    }
                    all_events.extend(events);
                },
                Err(e) => {
                    if self.debug {
                        println!("Cursor: Error parsing database {:?}: {}", db_path, e);
                    }
                }
            }
        }
        
        if self.debug {
            println!("Cursor: Total {} events collected", all_events.len());
        }
        
        // Sort by timestamp
        all_events.sort_by_key(|e| e.id);
        
        Ok(all_events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        // Check if any Cursor database exists
        Ok(!self.get_db_paths().is_empty())
    }
}
