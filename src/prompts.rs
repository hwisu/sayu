/// All user-facing strings and prompts for Sayu
/// 
/// This module centralizes all text constants for easy maintenance and localization

// CLI Messages
pub const MSG_INITIALIZING: &str = "🔧 Initializing Sayu...";
pub const MSG_REPOSITORY: &str = "Repository: ";
pub const MSG_GIT_HOOKS_INSTALLED: &str = "✓ Git hooks installed";
pub const MSG_DATABASE_INITIALIZED: &str = "✓ Database initialized";
pub const MSG_CONFIG_CREATED: &str = "✓ Configuration created";
pub const MSG_CLI_HOOK_INSTALLED: &str = "✓ zsh CLI tracking hook installed";
pub const MSG_CLI_HOOK_FAILED: &str = "CLI hook installation failed";
pub const MSG_CLI_COLLECTOR_FAILED: &str = "Failed to initialize CLI collector";
pub const MSG_INIT_COMPLETE: &str = "✅ Sayu installation complete!";
pub const MSG_NO_API_KEYS: &str = "No LLM API keys configured";
pub const MSG_API_KEY_INSTRUCTION: &str = "Set this system environment variable:\n  export SAYU_GEMINI_API_KEY=your-key";
pub const MSG_ALL_SET: &str = "🎉 All set! AI context will be automatically added to your commits.";
pub const MSG_ZSH_RESTART_HINT: &str = "Will be active in new terminal sessions (or run: source ~/.zshrc)";

// Health Check Messages
pub const MSG_HEALTH_CHECK: &str = "🏥 Checking Sayu health...";
pub const MSG_GIT_REPO_OK: &str = "✓ Git repository";
pub const MSG_GIT_REPO_ERROR: &str = "Not in a Git repository";
pub const MSG_DATABASE_OK: &str = "✓ Database connection";
pub const MSG_DATABASE_ERROR: &str = "Database error";
pub const MSG_CONFIG_OK: &str = "✓ Configuration loaded";
pub const MSG_CONFIG_ERROR: &str = "Config error";
pub const MSG_COMMIT_HOOK_OK: &str = "✓ Git commit-msg hook installed";
pub const MSG_COMMIT_HOOK_MISSING: &str = "Git commit-msg hook not installed";
pub const MSG_COLLECTORS_HEADER: &str = "\nCollectors:";
pub const MSG_CLAUDE_OK: &str = "  ✓ Claude Desktop collector available";
pub const MSG_CLAUDE_MISSING: &str = "  Claude Desktop not found";
pub const MSG_CURSOR_OK: &str = "  ✓ Cursor collector available";
pub const MSG_CURSOR_MISSING: &str = "  Cursor not found";
pub const MSG_CLI_OK: &str = "  ✓ CLI collector available";
pub const MSG_CLI_NOT_CONFIGURED: &str = "  CLI collector not configured";
pub const MSG_CLI_ERROR: &str = "  CLI collector error";
pub const MSG_API_CONFIG_HEADER: &str = "\nAPI Configuration:";
pub const MSG_GEMINI_OK: &str = "  ✓ Gemini API key configured";
pub const MSG_NO_LLM_KEYS: &str = "  No LLM API keys configured";
pub const MSG_ALL_SYSTEMS_OK: &str = "\n✅ All systems operational!";
pub const MSG_ISSUES_DETECTED: &str = "\n⚠️ Some issues detected";

// Show Command Messages
pub const MSG_NO_RECENT_EVENTS: &str = "No recent events found";
pub const MSG_EVENT_SEPARATOR: &str = "─";

// Uninstall Messages
pub const MSG_UNINSTALLING: &str = "🗑️  Uninstalling Sayu...";
pub const MSG_HOOK_REMOVED: &str = "✓ Removed {} hook";
pub const MSG_UNINSTALL_COMPLETE: &str = "✅ Sayu uninstalled";
pub const MSG_DATA_PRESERVED: &str = "Note: Database and configuration preserved at .sayu/";

// Error Messages
pub const ERROR_NOT_GIT_REPO: &str = "Not in a git repository";
pub const ERROR_NO_ZSHRC: &str = "No .zshrc file found";
pub const ERROR_HOME_DIR_NOT_FOUND: &str = "Could not find home directory";

// Configuration File Content
pub const DEFAULT_CONFIG_CONTENT: &str = r#"# Sayu Configuration
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

language: ko  # 언어 설정 (ko, en)
"#;

// Git Hook Scripts
pub const GIT_COMMIT_MSG_HOOK: &str = "#!/bin/sh\nsayu hook commit-msg \"$1\"\n";
pub const GIT_POST_COMMIT_HOOK: &str = "#!/bin/sh\nsayu hook post-commit\n";

// Tool usage filtering helper function
pub fn is_tool_usage(text: &str) -> bool {
    let tool_patterns = [
        "<function_calls>",
        "<function_calls>",
        "<invoke",
        "<invoke",
        "</invoke>",
        "</invoke>",
        "<tool_use>",
        "tool_use",
        "<result>",
        "<function_results>",
        "<parameter",
        "<system-reminder>",
    ];
    
    let text_lower = text.to_lowercase();
    tool_patterns.iter().any(|pattern| text_lower.contains(pattern))
}