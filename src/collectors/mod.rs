pub mod claude;
pub mod cursor;
pub mod cli;

use anyhow::Result;
use crate::domain::{Event, EventSource};
use async_trait::async_trait;
use std::path::Path;

#[async_trait]
pub trait Collector: Send + Sync {
    /// Get the event source type for this collector
    fn source(&self) -> EventSource;
    
    /// Collect events from this source
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>>;
    
    /// Check if this collector is available/healthy
    async fn health_check(&self) -> Result<bool>;
}

pub use claude::ClaudeCollector;
pub use cursor::CursorCollector;
pub use cli::CliCollector;