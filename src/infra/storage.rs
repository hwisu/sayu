use anyhow::Result;
use chrono::Utc;
use rusqlite::{params, Connection};
use serde_json;
use std::path::{Path, PathBuf};
use crate::domain::Event;

pub struct Storage {
    conn: Connection,
}

impl Storage {
    pub fn new(repo_root: impl AsRef<Path>) -> Result<Self> {
        let db_path = repo_root.as_ref().join(".sayu").join("events.db");
        
        // Ensure directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        let conn = Connection::open(&db_path)?;
        
        // Create tables
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                kind TEXT NOT NULL,
                repo TEXT NOT NULL,
                text TEXT NOT NULL,
                actor TEXT,
                meta TEXT,
                branch TEXT
            )",
            [],
        )?;
        
        // Create indices for better query performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_id ON events(id DESC)",
            [],
        )?;
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_repo ON events(repo)",
            [],
        )?;
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
            [],
        )?;
        
        Ok(Self { conn })
    }
    
    
    pub fn save_event(&self, event: &Event) -> Result<()> {
        let meta_json = serde_json::to_string(&event.meta)?;
        
        self.conn.execute(
            "INSERT OR REPLACE INTO events (id, source, kind, repo, text, actor, meta, branch)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                event.id,
                format!("{:?}", event.source).to_lowercase(),
                format!("{:?}", event.kind).to_lowercase(),
                event.repo,
                event.text,
                event.actor.as_ref().map(|a| format!("{a:?}").to_lowercase()),
                meta_json,
                event.branch,
            ],
        )?;
        
        Ok(())
    }
    
    pub fn get_recent_events(&self, repo: &str, limit: usize) -> Result<Vec<Event>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, source, kind, repo, text, actor, meta, branch
             FROM events
             WHERE repo = ?1
             ORDER BY id DESC
             LIMIT ?2"
        )?;
        
        let events = stmt.query_map(params![repo, limit], |row| {
            let source_str: String = row.get(1)?;
            let kind_str: String = row.get(2)?;
            let actor_str: Option<String> = row.get(5)?;
            let meta_json: String = row.get(6)?;
            
            Ok(Event {
                id: row.get(0)?,
                source: serde_json::from_value(serde_json::Value::String(source_str))
                    .unwrap_or(crate::domain::EventSource::Git),
                kind: serde_json::from_value(serde_json::Value::String(kind_str))
                    .unwrap_or(crate::domain::EventKind::Commit),
                repo: row.get(3)?,
                text: row.get(4)?,
                actor: actor_str.and_then(|s| 
                    serde_json::from_value(serde_json::Value::String(s)).ok()
                ),
                meta: serde_json::from_str(&meta_json).unwrap_or_default(),
                branch: row.get(7)?,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
        
        Ok(events)
    }
    
    pub fn get_events_since(&self, repo: &str, since_ts: i64) -> Result<Vec<Event>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, source, kind, repo, text, actor, meta, branch
             FROM events
             WHERE repo = ?1 AND id > ?2
             ORDER BY id ASC"
        )?;
        
        let events = stmt.query_map(params![repo, since_ts], |row| {
            let source_str: String = row.get(1)?;
            let kind_str: String = row.get(2)?;
            let actor_str: Option<String> = row.get(5)?;
            let meta_json: String = row.get(6)?;
            
            Ok(Event {
                id: row.get(0)?,
                source: serde_json::from_value(serde_json::Value::String(source_str))
                    .unwrap_or(crate::domain::EventSource::Git),
                kind: serde_json::from_value(serde_json::Value::String(kind_str))
                    .unwrap_or(crate::domain::EventKind::Commit),
                repo: row.get(3)?,
                text: row.get(4)?,
                actor: actor_str.and_then(|s| 
                    serde_json::from_value(serde_json::Value::String(s)).ok()
                ),
                meta: serde_json::from_str(&meta_json).unwrap_or_default(),
                branch: row.get(7)?,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
        
        Ok(events)
    }
    
    pub fn cleanup_old_events(&self, days: i64) -> Result<usize> {
        let cutoff = Utc::now().timestamp_millis() - (days * 24 * 60 * 60 * 1000);
        
        let deleted = self.conn.execute(
            "DELETE FROM events WHERE id < ?1",
            params![cutoff],
        )?;
        
        Ok(deleted)
    }
    
    pub fn get_all_recent_events(&self, limit: usize, source_filter: Option<&str>) -> Result<Vec<Event>> {
        let query = if let Some(_source) = source_filter {
            "SELECT id, source, kind, repo, text, actor, meta, branch
             FROM events
             WHERE source = ?1
             ORDER BY id DESC
             LIMIT ?2"
        } else {
            "SELECT id, source, kind, repo, text, actor, meta, branch
             FROM events
             ORDER BY id DESC
             LIMIT ?1"
        };
        
        let mut stmt = self.conn.prepare(query)?;
        
        let events = if let Some(source) = source_filter {
            stmt.query_map(params![source.to_lowercase(), limit], Self::row_to_event)?
        } else {
            stmt.query_map(params![limit], Self::row_to_event)?
        }
        .collect::<Result<Vec<_>, _>>()?;
        
        Ok(events)
    }
    
    fn row_to_event(row: &rusqlite::Row) -> rusqlite::Result<Event> {
        let source_str: String = row.get(1)?;
        let kind_str: String = row.get(2)?;
        let actor_str: Option<String> = row.get(5)?;
        let meta_json: String = row.get(6)?;
        
        Ok(Event {
            id: row.get(0)?,
            source: serde_json::from_value(serde_json::Value::String(source_str))
                .unwrap_or(crate::domain::EventSource::Git),
            kind: serde_json::from_value(serde_json::Value::String(kind_str))
                .unwrap_or(crate::domain::EventKind::Commit),
            repo: row.get(3)?,
            text: row.get(4)?,
            actor: actor_str.and_then(|s| 
                serde_json::from_value(serde_json::Value::String(s)).ok()
            ),
            meta: serde_json::from_str(&meta_json).unwrap_or_default(),
            branch: row.get(7)?,
        })
    }
}

// Simple cache implementation
pub struct Cache {
    cache_dir: PathBuf,
}

impl Cache {
    pub fn new(repo_root: impl AsRef<Path>) -> Result<Self> {
        let cache_dir = repo_root.as_ref().join(".sayu").join("cache");
        std::fs::create_dir_all(&cache_dir)?;
        
        Ok(Self { cache_dir })
    }
    
    pub fn get(&self, key: &str) -> Result<Option<Vec<u8>>> {
        let file_path = self.cache_dir.join(format!("{key}.cache"));
        
        if !file_path.exists() {
            return Ok(None);
        }
        
        // Check if cache is expired (simple TTL: 5 minutes)
        if let Ok(metadata) = file_path.metadata() {
            if let Ok(modified) = metadata.modified() {
                if modified.elapsed().unwrap_or_default().as_secs() > 300 {
                    let _ = std::fs::remove_file(&file_path);
                    return Ok(None);
                }
            }
        }
        
        Ok(Some(std::fs::read(&file_path)?))
    }
    
    pub fn set(&self, key: &str, value: &[u8]) -> Result<()> {
        let file_path = self.cache_dir.join(format!("{key}.cache"));
        std::fs::write(&file_path, value)?;
        Ok(())
    }
    
    pub fn clear(&self) -> Result<()> {
        for entry in std::fs::read_dir(&self.cache_dir)?.flatten() {
            if entry.path().extension().and_then(|s| s.to_str()) == Some("cache") {
                let _ = std::fs::remove_file(entry.path());
            }
        }
        Ok(())
    }
}
