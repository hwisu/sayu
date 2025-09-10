use anyhow::{Result, Context};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::io::{BufRead, BufReader, Write};
use std::fs::{File, OpenOptions};
use crate::domain::{Event, EventKind, EventSource};
use crate::collectors::Collector;

#[derive(Debug, Clone)]
pub struct ShellCollector {
    debug: bool,
    log_path: PathBuf,
}

#[derive(Debug, Deserialize, Serialize)]
struct ShellLogEntry {
    timestamp: i64,
    command: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    exit_code: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    duration: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cwd: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    shell: Option<String>,  // "bash" or "zsh"
}

impl ShellCollector {
    pub fn new() -> Result<Self> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let log_path = home.join(".sayu").join("shell.jsonl");
        
        Ok(Self {
            debug: std::env::var("SAYU_DEBUG").is_ok(),
            log_path,
        })
    }
    
    pub fn install_hook(&self) -> Result<()> {
        let home = dirs::home_dir().context("Could not find home directory")?;
        let sayu_dir = home.join(".sayu");
        std::fs::create_dir_all(&sayu_dir)?;
        
        // Install both zsh and bash hooks
        self.install_zsh_hook(&home, &sayu_dir)?;
        self.install_bash_hook(&home, &sayu_dir)?;
        
        Ok(())
    }
    
    fn install_zsh_hook(&self, home: &Path, sayu_dir: &Path) -> Result<()> {
        // Create the zsh hook script
        let hook_script = r#"#!/usr/bin/env zsh
# Sayu shell tracking hook for zsh

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
    echo "{\"timestamp\":$timestamp,\"command\":\"$cmd\",\"exit_code\":$exit_code,\"cwd\":\"$cwd\",\"shell\":\"zsh\"}" >> ~/.sayu/shell.jsonl
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
            let source_line = "source ~/.sayu/zsh-hook.zsh";
            
            if !content.contains(source_line) {
                let mut file = OpenOptions::new()
                    .append(true)
                    .open(&zshrc)?;
                writeln!(file, "\n# Sayu shell tracking")?;
                writeln!(file, "{}", source_line)?;
            }
        }
        
        if self.debug {
            println!("Zsh hook installed at {:?}", hook_path);
        }
        
        Ok(())
    }
    
    fn install_bash_hook(&self, home: &Path, sayu_dir: &Path) -> Result<()> {
        // Create the bash hook script
        let hook_script = r#"#!/usr/bin/env bash
# Sayu shell tracking hook for bash

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
    echo "{\"timestamp\":$timestamp,\"command\":\"$cmd\",\"exit_code\":$exit_code,\"cwd\":\"$cwd\",\"shell\":\"bash\"}" >> ~/.sayu/shell.jsonl
}

# Set up DEBUG trap for command tracking
sayu_preexec() {
    [ -n "$COMP_LINE" ] && return  # Skip completions
    [ "$BASH_COMMAND" = "$PROMPT_COMMAND" ] && return  # Skip prompt command
    SAYU_LAST_CMD="$BASH_COMMAND"
}

# Hook into PROMPT_COMMAND for post-command
sayu_prompt_command() {
    local exit_code=$?
    if [[ -n "$SAYU_LAST_CMD" ]] && [[ "$SAYU_LAST_CMD" != "sayu_prompt_command" ]]; then
        sayu_log_command "$SAYU_LAST_CMD" "$exit_code"
        unset SAYU_LAST_CMD
    fi
}

# Set up hooks
trap 'sayu_preexec' DEBUG
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND$'\n'}sayu_prompt_command"
"#;
        
        let hook_path = sayu_dir.join("bash-hook.sh");
        std::fs::write(&hook_path, hook_script)?;
        
        // Update .bashrc to source the hook
        let bashrc = home.join(".bashrc");
        if bashrc.exists() {
            let content = std::fs::read_to_string(&bashrc)?;
            let source_line = "source ~/.sayu/bash-hook.sh";
            
            if !content.contains(source_line) {
                let mut file = OpenOptions::new()
                    .append(true)
                    .open(&bashrc)?;
                writeln!(file, "\n# Sayu shell tracking")?;
                writeln!(file, "{}", source_line)?;
            }
        }
        
        // Also update .bash_profile if it exists (macOS often uses this)
        let bash_profile = home.join(".bash_profile");
        if bash_profile.exists() {
            let content = std::fs::read_to_string(&bash_profile)?;
            let source_line = "source ~/.sayu/bash-hook.sh";
            
            if !content.contains(source_line) {
                let mut file = OpenOptions::new()
                    .append(true)
                    .open(&bash_profile)?;
                writeln!(file, "\n# Sayu shell tracking")?;
                writeln!(file, "{}", source_line)?;
            }
        }
        
        if self.debug {
            println!("Bash hook installed at {:?}", hook_path);
        }
        
        Ok(())
    }
    
    pub fn track_command(&self, command: &str) -> Result<()> {
        // This method can be called directly by the CLI to log a command
        let entry = ShellLogEntry {
            timestamp: chrono::Utc::now().timestamp_millis(),
            command: command.to_string(),
            exit_code: None,
            duration: None,
            cwd: std::env::current_dir()
                .ok()
                .and_then(|p| p.to_str().map(String::from)),
            shell: None,  // Will be filled by the hook scripts
        };
        
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)?;
        
        writeln!(file, "{}", serde_json::to_string(&entry)?)?;
        
        Ok(())
    }
    
    fn read_shell_log(&self, since_ts: Option<i64>) -> Result<Vec<ShellLogEntry>> {
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
            
            match serde_json::from_str::<ShellLogEntry>(&line) {
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
                    println!("Failed to parse shell log entry: {}", e);
                }
                _ => {}
            }
        }
        
        Ok(entries)
    }
}

#[async_trait]
impl Collector for ShellCollector {
    fn source(&self) -> EventSource {
        EventSource::Shell
    }
    
    async fn collect(&self, repo_root: &Path, since_ts: Option<i64>) -> Result<Vec<Event>> {
        let entries = self.read_shell_log(since_ts)?;
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
                EventSource::Shell,
                EventKind::Command,
                repo_name.to_string(),
                entry.command.clone(),
            );
            
            event = event.with_timestamp(entry.timestamp);
            
            // Add current working directory to metadata
            if let Some(cwd) = entry.cwd {
                event = event.with_meta("cwd".to_string(), serde_json::Value::String(cwd));
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
            
            // Add shell type if available
            if let Some(shell) = entry.shell {
                event = event.with_meta("shell".to_string(), serde_json::Value::String(shell));
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
