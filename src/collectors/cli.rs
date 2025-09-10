use anyhow::{Result, Context};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::io::{BufRead, BufReader, Write};
use std::fs::{File, OpenOptions};
use crate::domain::{Event, EventKind, EventSource};
use crate::collectors::Collector;

#[derive(Debug, Clone)]
pub struct CliCollector {
    debug: bool,
    log_path: PathBuf,
}

#[derive(Debug, Deserialize, Serialize)]
struct CliLogEntry {
    timestamp: i64,
    command: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    exit_code: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    duration: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cwd: Option<String>,
}

impl CliCollector {
    pub fn new() -> Result<Self> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let log_path = home.join(".sayu").join("cli.jsonl");
        
        Ok(Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
            log_path,
        })
    }
    
    pub fn install_hook(&self) -> Result<()> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let sayu_dir = home.join(".sayu");
        std::fs::create_dir_all(&sayu_dir)?;
        
        // Create the zsh hook script
        let hook_script = r#"#!/usr/bin/env zsh
# Sayu CLI tracking hook

# Function to log commands
sayu_log_command() {
    local cmd="$1"
    local exit_code="$2"
    local timestamp=$(date +%s000)
    local cwd="$PWD"
    
    # Escape special characters in JSON
    cmd="${cmd//\\/\\\\}"
    cmd="${cmd//\"/\\\"}"
    cwd="${cwd//\\/\\\\}"
    cwd="${cwd//\"/\\\"}"
    
    # Log to file
    echo "{\"timestamp\":$timestamp,\"command\":\"$cmd\",\"exit_code\":$exit_code,\"cwd\":\"$cwd\"}" >> ~/.sayu/cli.jsonl
}

# Hook into preexec and precmd
sayu_preexec() {
    SAYU_LAST_CMD="$1"
    SAYU_CMD_START=$(date +%s)
}

sayu_precmd() {
    local exit_code=$?
    if [[ -n "$SAYU_LAST_CMD" ]]; then
        sayu_log_command "$SAYU_LAST_CMD" "$exit_code"
        unset SAYU_LAST_CMD
        unset SAYU_CMD_START
    fi
}

# Add to hook arrays
preexec_functions+=(sayu_preexec)
precmd_functions+=(sayu_precmd)
"#;
        
        let hook_path = sayu_dir.join("zsh-hook.zsh");
        std::fs::write(&hook_path, hook_script)?;
        
        // Update .zshrc to source the hook
        let zshrc = home.join(".zshrc");
        if zshrc.exists() {
            let content = std::fs::read_to_string(&zshrc)?;
            let source_line = format!("source ~/.sayu/zsh-hook.zsh");
            
            if !content.contains(&source_line) {
                let mut file = OpenOptions::new()
                    .append(true)
                    .open(&zshrc)?;
                writeln!(file, "\n# Sayu CLI tracking")?;
                writeln!(file, "{}", source_line)?;
            }
        }
        
        if self.debug {
            println!("CLI hook installed at {:?}", hook_path);
        }
        
        Ok(())
    }
    
    pub fn track_command(&self, command: &str) -> Result<()> {
        // This method can be called directly by the CLI to log a command
        let entry = CliLogEntry {
            timestamp: chrono::Utc::now().timestamp_millis(),
            command: command.to_string(),
            exit_code: None,
            duration: None,
            cwd: std::env::current_dir()
                .ok()
                .and_then(|p| p.to_str().map(String::from)),
        };
        
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)?;
        
        writeln!(file, "{}", serde_json::to_string(&entry)?)?;
        
        Ok(())
    }
    
    fn read_cli_log(&self, since_ts: Option<i64>) -> Result<Vec<CliLogEntry>> {
        if !self.log_path.exists() {
            return Ok(vec![]);
        }
        
        let file = File::open(&self.log_path)?;
        let reader = BufReader::new(file);
        let mut entries = Vec::new();
        
        for line in reader.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            
            match serde_json::from_str::<CliLogEntry>(&line) {
                Ok(entry) => {
                    // Filter by timestamp if needed
                    if let Some(since) = since_ts {
                        if entry.timestamp <= since {
                            continue;
                        }
                    }
                    entries.push(entry);
                }
                Err(e) if self.debug => {
                    println!("Failed to parse CLI log entry: {}", e);
                }
                _ => {}
            }
        }
        
        Ok(entries)
    }
}

#[async_trait]
impl Collector for CliCollector {
    fn source(&self) -> EventSource {
        EventSource::Cli
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let entries = self.read_cli_log(since_ts)?;
        let repo_name = repo_root.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown");
        
        let repo_path = repo_root.to_string_lossy();
        
        let mut events = Vec::new();
        for entry in entries {
            // Only include commands from this repository
            if let Some(cwd) = &entry.cwd {
                if !cwd.starts_with(repo_path.as_ref()) {
                    continue;
                }
            }
            
            let mut event = Event::new(
                EventSource::Cli,
                EventKind::Command,
                repo_name.to_string(),
                entry.command.clone(),
            );
            
            event.ts = entry.timestamp;
            
            // Add current working directory
            if let Some(cwd) = entry.cwd {
                event = event.with_cwd(cwd);
            }
            
            // Add metadata
            if let Some(exit_code) = entry.exit_code {
                event = event.with_meta("exit_code".to_string(), serde_json::Value::Number(exit_code.into()));
            }
            
            if let Some(duration) = entry.duration {
                event = event.with_meta("duration".to_string(), serde_json::Value::Number(
                    serde_json::Number::from_f64(duration).unwrap_or(serde_json::Number::from(0))
                ));
            }
            
            events.push(event);
        }
        
        Ok(events)
    }
    
    async fn health_check(&self) -> Result<bool> {
        // Check if the log file exists and is writable
        if self.log_path.exists() {
            Ok(true)
        } else {
            // Try to create the log file
            if let Some(parent) = self.log_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            File::create(&self.log_path)?;
            Ok(true)
        }
    }
}