use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

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
    pub id: i64,  // timestamp mills as primary key
    pub source: EventSource,
    pub kind: EventKind,
    pub repo: String,
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub actor: Option<Actor>,
    #[serde(default)]
    pub meta: HashMap<String, serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub branch: Option<String>,
}

impl Event {
    pub fn new(
        source: EventSource,
        kind: EventKind,
        repo: String,
        text: String,
    ) -> Self {
        let timestamp = Utc::now().timestamp_millis();
        Self {
            id: timestamp,
            source,
            kind,
            repo,
            text,
            actor: None,
            meta: HashMap::new(),
            branch: None,
        }
    }

    pub fn with_actor(mut self, actor: Actor) -> Self {
        self.actor = Some(actor);
        self
    }

    pub fn with_meta(mut self, key: String, value: serde_json::Value) -> Self {
        self.meta.insert(key, value);
        self
    }

    pub fn with_branch(mut self, branch: String) -> Self {
        self.branch = Some(branch);
        self
    }

    pub fn with_timestamp(mut self, timestamp: i64) -> Self {
        self.id = timestamp;
        self
    }
}
