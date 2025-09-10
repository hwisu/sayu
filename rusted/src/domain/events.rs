use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum EventSource {
    Claude,
    Cursor,
    Cli,
    Git,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum EventKind {
    Conversation,
    Command,
    Commit,
    Diff,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Actor {
    User,
    Assistant,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub source: EventSource,
    pub kind: EventKind,
    pub repo: String,
    pub text: String,
    pub ts: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub actor: Option<Actor>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cwd: Option<String>,
    #[serde(default)]
    pub meta: HashMap<String, serde_json::Value>,
}

impl Event {
    pub fn new(
        source: EventSource,
        kind: EventKind,
        repo: String,
        text: String,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            source,
            kind,
            repo,
            text,
            ts: Utc::now().timestamp_millis(),
            actor: None,
            file: None,
            cwd: None,
            meta: HashMap::new(),
        }
    }

    pub fn with_actor(mut self, actor: Actor) -> Self {
        self.actor = Some(actor);
        self
    }

    pub fn with_file(mut self, file: String) -> Self {
        self.file = Some(file);
        self
    }

    pub fn with_cwd(mut self, cwd: String) -> Self {
        self.cwd = Some(cwd);
        self
    }

    pub fn with_meta(mut self, key: String, value: serde_json::Value) -> Self {
        self.meta.insert(key, value);
        self
    }
}