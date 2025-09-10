use anyhow::{Result, Context};
use clap::{Parser, Subcommand};
use colored::*;
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::infra::{ConfigManager, Storage};
use crate::domain::{Event, EventKind, EventSource};
use crate::collectors::{Collector, ClaudeCollector, CursorCollector, CliCollector};
use crate::llm::EventSummarizer;

#[derive(Parser)]
#[command(name = "sayu")]
#[command(about = "Automatically capture the 'why' behind your code changes", long_about = None)]
#[command(version = "0.9.0")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize Sayu in current repository
    Init {
        /// Skip interactive setup
        #[arg(long)]
        no_interactive: bool,
    },
    
    /// Internal command for Git hooks
    Hook {
        /// Type of hook
        #[arg(value_enum)]
        hook_type: HookType,
        
        /// File argument (for commit-msg hook)
        file: Option<String>,
    },
    
    /// Check Sayu system health
    Health,
    
    /// Show commit context for the latest commits
    Show {
        /// Number of commits to show
        #[arg(short = 'n', default_value = "5")]
        count: usize,
    },
    
    /// Uninstall Sayu from repository
    Uninstall,
}

#[derive(Clone, clap::ValueEnum)]
pub enum HookType {
    CommitMsg,
    PostCommit,
}

pub async fn run() -> Result<()> {
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Init { no_interactive } => init_command(no_interactive).await,
        Commands::Hook { hook_type, file } => hook_command(hook_type, file).await,
        Commands::Health => health_command().await,
        Commands::Show { count } => show_command(count).await,
        Commands::Uninstall => uninstall_command().await,
    }
}

async fn init_command(_no_interactive: bool) -> Result<()> {
    println!("{}", "🔧 Initializing Sayu...".bold());
    
    let repo_root = get_git_repo_root()?;
    println!("Repository: {}", repo_root.display());
    
    // Install Git hooks
    install_git_hooks(&repo_root)?;
    
    // Initialize storage
    let _storage = Storage::new(&repo_root)?;
    println!("✓ Database initialized");
    
    // Create default config
    ConfigManager::create_default(&repo_root)?;
    println!("✓ Configuration created");
    
    // Install CLI hook using the CliCollector
    match CliCollector::new() {
        Ok(cli_collector) => {
            if let Err(e) = cli_collector.install_hook() {
                println!("{} CLI hook installation failed: {}", "⚠️".yellow(), e);
            } else {
                println!("✓ zsh CLI tracking hook installed");
                println!("{} Will be active in new terminal sessions (or run: source ~/.zshrc)", 
                         "⚠️".yellow());
            }
        }
        Err(e) => {
            println!("{} Failed to initialize CLI collector: {}", "⚠️".yellow(), e);
        }
    }
    
    println!("\n{}", "✅ Sayu installation complete!".green().bold());
    
    // Check for API keys (simplified - just check env vars)
    if std::env::var("SAYU_GEMINI_API_KEY").is_err() {
        println!("\n{} No LLM API keys configured", "⚠️".yellow());
        println!("\nSet this system environment variable:");
        println!("  export SAYU_GEMINI_API_KEY=your-key");
    } else {
        println!("\n{} All set! AI context will be automatically added to your commits.", 
                 "🎉".green());
    }
    
    Ok(())
}

async fn hook_command(hook_type: HookType, file: Option<String>) -> Result<()> {
    // Get repo root
    let repo_root = match get_git_repo_root() {
        Ok(root) => root,
        Err(_) => {
            // Fail silently in hooks
            std::process::exit(0);
        }
    };
    
    match hook_type {
        HookType::CommitMsg => {
            if let Some(msg_file) = file {
                handle_commit_msg(&repo_root, &msg_file).await?;
            }
        }
        HookType::PostCommit => {
            handle_post_commit(&repo_root).await?;
        }
    }
    
    Ok(())
}

async fn health_command() -> Result<()> {
    println!("{}", "🏥 Checking Sayu health...".bold());
    
    let mut all_ok = true;
    
    // Check Git repository
    match get_git_repo_root() {
        Ok(root) => {
            println!("✓ Git repository: {}", root.display());
            
            // Check database
            match Storage::new(&root) {
                Ok(_) => println!("✓ Database connection"),
                Err(e) => {
                    println!("{} Database error: {}", "✗".red(), e);
                    all_ok = false;
                }
            }
            
            // Check config
            match ConfigManager::new(&root) {
                Ok(config) => {
                    let user_config = config.get();
                    println!("✓ Configuration loaded (language: {:?})", user_config.language);
                }
                Err(e) => {
                    println!("{} Config error: {}", "✗".red(), e);
                    all_ok = false;
                }
            }
            
            // Check Git hooks
            let hooks_dir = root.join(".git").join("hooks");
            if hooks_dir.join("commit-msg").exists() {
                println!("✓ Git commit-msg hook installed");
            } else {
                println!("{} Git commit-msg hook not installed", "⚠️".yellow());
            }
        }
        Err(e) => {
            println!("{} Not in a Git repository: {}", "✗".red(), e);
            all_ok = false;
        }
    }
    
    // Check collectors in parallel
    println!("\nCollectors:");
    
    let claude_collector = ClaudeCollector::new();
    let cursor_collector = CursorCollector::new();
    let cli_collector_result = CliCollector::new();
    
    // Run all health checks in parallel
    let (claude_health, cursor_health, cli_health) = tokio::join!(
        claude_collector.health_check(),
        cursor_collector.health_check(),
        async {
            match cli_collector_result {
                Ok(collector) => collector.health_check().await,
                Err(_) => Ok(false),
            }
        }
    );
    
    // Display results
    match claude_health {
        Ok(true) => println!("  ✓ Claude Desktop collector available"),
        _ => println!("  {} Claude Desktop not found", "⚠️".yellow()),
    }
    
    match cursor_health {
        Ok(true) => println!("  ✓ Cursor collector available"),
        _ => println!("  {} Cursor not found", "⚠️".yellow()),
    }
    
    match cli_health {
        Ok(true) => println!("  ✓ CLI collector available"),
        Ok(false) => println!("  {} CLI collector not configured", "⚠️".yellow()),
        Err(_) => println!("  {} CLI collector error", "✗".red()),
    }
    
    // Check API keys
    println!("\nAPI Configuration:");
    if std::env::var("SAYU_GEMINI_API_KEY").is_ok() {
        println!("  ✓ Gemini API key configured");
    } else {
        println!("  {} No LLM API keys configured", "⚠️".yellow());
    }
    
    if all_ok {
        println!("\n{}", "✅ All systems operational!".green().bold());
    } else {
        println!("\n{} Some issues detected", "⚠️".yellow().bold());
    }
    
    Ok(())
}

async fn show_command(count: usize) -> Result<()> {
    let repo_root = get_git_repo_root()?;
    let storage = Storage::new(&repo_root)?;
    
    let repo_name = repo_root.file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown");
    
    let events = storage.get_recent_events(repo_name, count)?;
    
    if events.is_empty() {
        println!("No recent events found");
    } else {
        for event in events {
            println!("{}", "─".repeat(60));
            println!("Time: {}", chrono::DateTime::from_timestamp_millis(event.ts)
                .map(|dt| dt.format("%Y-%m-%d %H:%M:%S").to_string())
                .unwrap_or_else(|| "Unknown".to_string()));
            println!("Source: {:?}, Kind: {:?}", event.source, event.kind);
            if let Some(actor) = &event.actor {
                println!("Actor: {actor:?}");
            }
            println!("Text: {}", event.text);
        }
    }
    
    Ok(())
}

async fn uninstall_command() -> Result<()> {
    let repo_root = get_git_repo_root()?;
    
    println!("{}", "🗑️  Uninstalling Sayu...".bold());
    
    // Remove Git hooks
    let hooks_dir = repo_root.join(".git").join("hooks");
    for hook_name in &["commit-msg", "post-commit"] {
        let hook_path = hooks_dir.join(hook_name);
        if hook_path.exists() {
            std::fs::remove_file(&hook_path)?;
            println!("✓ Removed {hook_name} hook");
        }
    }
    
    // Note: We keep the database and config for potential reinstallation
    println!("\n{}", "✅ Sayu uninstalled".green());
    println!("Note: Database and configuration preserved at .sayu/");
    
    Ok(())
}

// Helper functions

fn get_git_repo_root() -> Result<PathBuf> {
    let output = Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()
        .context("Failed to execute git command")?;
    
    if !output.status.success() {
        anyhow::bail!("Not in a git repository");
    }
    
    let path = String::from_utf8(output.stdout)?;
    Ok(PathBuf::from(path.trim()))
}

fn install_git_hooks(repo_root: &Path) -> Result<()> {
    let hooks_dir = repo_root.join(".git").join("hooks");
    std::fs::create_dir_all(&hooks_dir)?;
    
    // Create commit-msg hook
    let commit_msg_hook = hooks_dir.join("commit-msg");
    std::fs::write(
        &commit_msg_hook,
        "#!/bin/sh\nsayu hook commit-msg \"$1\"\n"
    )?;
    
    // Make executable
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(&commit_msg_hook)?.permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&commit_msg_hook, perms)?;
    }
    
    // Create post-commit hook
    let post_commit_hook = hooks_dir.join("post-commit");
    std::fs::write(
        &post_commit_hook,
        "#!/bin/sh\nsayu hook post-commit\n"
    )?;
    
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(&post_commit_hook)?.permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&post_commit_hook, perms)?;
    }
    
    println!("✓ Git hooks installed");
    Ok(())
}


async fn handle_commit_msg(repo_root: &Path, msg_file: &str) -> Result<()> {
    // Read the commit message
    let commit_message = std::fs::read_to_string(msg_file)?;
    
    // Skip if it's an amend or merge commit
    if commit_message.starts_with("Merge") || commit_message.contains("fixup!") {
        return Ok(());
    }
    
    // Get configuration
    let config = ConfigManager::new(repo_root)?;
    let language = config.get_language();
    
    // Get last commit timestamp to filter events
    let last_commit_ts = get_last_commit_timestamp(repo_root).unwrap_or(0);
    
    if std::env::var("SAYU_DEBUG").is_ok() {
        println!("Last commit timestamp: {} ({})", 
            last_commit_ts,
            chrono::DateTime::from_timestamp_millis(last_commit_ts)
                .map(|dt| dt.format("%Y-%m-%d %H:%M:%S").to_string())
                .unwrap_or_else(|| "Unknown".to_string())
        );
    }
    
    // Collect events from all sources in parallel
    let claude_collector = ClaudeCollector::new();
    let cursor_collector = CursorCollector::new();
    let cli_collector_result = CliCollector::new();
    
    // Run all collectors in parallel
    let (claude_events, cursor_events, cli_events) = tokio::join!(
        claude_collector.collect(repo_root, Some(last_commit_ts)),
        cursor_collector.collect(repo_root, Some(last_commit_ts)),
        async {
            match cli_collector_result {
                Ok(collector) => collector.collect(repo_root, Some(last_commit_ts)).await,
                Err(_) => Ok(Vec::new()),
            }
        }
    );
    
    // Combine all events
    let mut all_events = Vec::new();
    if let Ok(events) = claude_events {
        all_events.extend(events);
    }
    if let Ok(events) = cursor_events {
        all_events.extend(events);
    }
    if let Ok(events) = cli_events {
        all_events.extend(events);
    }
    
    // If no events collected, skip
    if all_events.is_empty() {
        if std::env::var("SAYU_DEBUG").is_ok() {
            println!("No events collected since last commit");
        }
        return Ok(());
    }
    
    if std::env::var("SAYU_DEBUG").is_ok() {
        println!("Collected {} events for commit summary", all_events.len());
    }
    
    // Get git diff for staged changes
    let diff_output = Command::new("git")
        .args(["diff", "--cached", "--stat"])
        .current_dir(repo_root)
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .unwrap_or_default();
    
    // Add diff as a special event if not empty
    if !diff_output.is_empty() {
        let diff_event = Event::new(
            EventSource::Git,
            EventKind::Diff,
            "git-diff".to_string(),
            format!("Changed files:\n{}", diff_output),
        );
        all_events.push(diff_event);
    }
    
    // Generate summary using LLM
    match EventSummarizer::new() {
        Ok(mut summarizer) => {
            match summarizer.summarize_for_commit(all_events, &commit_message, language).await {
                Ok(summary) => {
                    // Append summary to commit message
                    let updated_message = format!("{}\n{}", commit_message.trim(), summary);
                    std::fs::write(msg_file, updated_message)?;
                }
                Err(e) => {
                    // Don't block commit on LLM errors
                    if std::env::var("SAYU_DEBUG").is_ok() {
                        eprintln!("Failed to generate summary: {}", e);
                    }
                }
            }
        }
        Err(e) => {
            // Don't block commit if LLM is not configured
            if std::env::var("SAYU_DEBUG").is_ok() {
                eprintln!("Failed to initialize summarizer: {}", e);
            }
        }
    }
    
    Ok(())
}

fn get_last_commit_timestamp(repo_root: &Path) -> Option<i64> {
    let output = Command::new("git")
        .args(["log", "-1", "--format=%ct"])
        .current_dir(repo_root)
        .output()
        .ok()?;
    
    if output.status.success() {
        String::from_utf8(output.stdout)
            .ok()?
            .trim()
            .parse::<i64>()
            .ok()
            .map(|ts| ts * 1000) // Convert to milliseconds
    } else {
        None
    }
}

async fn handle_post_commit(repo_root: &Path) -> Result<()> {
    // Store the commit event
    let storage = Storage::new(repo_root)?;
    
    // Get latest commit info and timestamp
    let output = Command::new("git")
        .args(["log", "-1", "--pretty=format:%H|%s|%an|%ct"])
        .current_dir(repo_root)
        .output()?;
    
    let commit_info = String::from_utf8(output.stdout)?;
    let parts: Vec<&str> = commit_info.split('|').collect();
    
    if parts.len() >= 4 {
        let repo_name = repo_root.file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown");
        
        let event = Event::new(
            EventSource::Git,
            EventKind::Commit,
            repo_name.to_string(),
            parts[1].to_string(), // commit message
        );
        
        storage.save_event(&event)?;
        
        // Get commit timestamp in milliseconds
        let commit_timestamp_secs: i64 = parts[3].parse().unwrap_or(0);
        let since_ts = Some(commit_timestamp_secs * 1000);
        
        // Run collectors to gather context
        let claude_collector = ClaudeCollector::new();
        let cursor_collector = CursorCollector::new();
        let cli_collector = CliCollector::new()?;
        
        // Collect in parallel
        let (claude_events, cursor_events, cli_events) = tokio::join!(
            claude_collector.collect(repo_root, since_ts),
            cursor_collector.collect(repo_root, since_ts),
            cli_collector.collect(repo_root, since_ts)
        );
        
        // Store collected events
        let mut total_events = 0;
        
        if let Ok(events) = claude_events {
            for event in events {
                storage.save_event(&event)?;
                total_events += 1;
            }
        }
        
        if let Ok(events) = cursor_events {
            for event in events {
                storage.save_event(&event)?;
                total_events += 1;
            }
        }
        
        if let Ok(events) = cli_events {
            for event in events {
                storage.save_event(&event)?;
                total_events += 1;
            }
        }
        
        if total_events > 0 {
            println!("📝 Collected {} context events for commit", total_events);
        }
    }
    
    Ok(())
}