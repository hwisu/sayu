# Sayu - AI Coding Context for Git Commits

> Automatically capture the "why" behind your code changes from AI conversations

[한국어](README.ko-kr.md)

## What is Sayu?

Sayu analyzes your conversations with AI coding assistants (Cursor, Claude) and automatically adds meaningful context to your git commits.

## Key Features

- **AI conversation collection**: Automatically collects conversations from Cursor and Claude Desktop
- **Smart filtering**: Focuses only on relevant conversations from your repository
- **Fast processing**: Generates context in 2-3 seconds during commit
- **Privacy-first**: All data processed locally, no persistent storage
- **Fail-safe**: Never blocks commits even if something goes wrong

## Installation

```bash
# Install with pipx (recommended)
pipx install sayu

# Or with pip
pip install sayu

# Initialize in your repository
sayu init
```

## Usage

### 1. Initialize
```bash
# Run in your Git repository
sayu init
```

This will:
- Install Git hooks (commit-msg, post-commit)
- Generate config file (`.sayu.yml`)

### 2. Set API Key

Set your API key as an environment variable:

```bash
# Gemini API key (recommended)
export SAYU_GEMINI_API_KEY=your_api_key_here

# Or OpenRouter API key
export SAYU_OPENROUTER_API_KEY=your_api_key_here
export SAYU_LLM_PROVIDER=openrouter
```

### 3. Commit as usual

```bash
git add .
git commit -m "Fix authentication bug"
```

Result:
```
Fix authentication bug

---思惟---

Intent:
  Fix JWT token validation logic to resolve login failures

What Changed:
  Improved exception handling in auth.js token decoding
  Added test cases for expired tokens in test/auth.test.js

Conversation Flow:
  Discussed error handling approaches with Claude for token expiration.
  Identified need for more granular exception handling.
  Found and fixed several edge cases during test implementation.
---FIN---
```

## Commands

```bash
# Check system status
sayu health

# Preview AI context for staged changes
sayu preview

# Install/uninstall CLI tracking (zsh)
sayu collector cli-install
sayu collector cli-uninstall
```

## Configuration (.sayu.yml)

```yaml
# Sayu Configuration
# Captures the 'why' behind your code changes

language: ko              # Language (ko, en)
commitTrailer: true       # Add AI analysis to commit messages

connectors:
  claude: true            # Claude Desktop conversation collection
  cursor: true            # Cursor editor conversation collection
  cli:
    mode: "zsh-preexec"   # CLI command collection (or "off")

# Environment variables override:
# SAYU_ENABLED=false
# SAYU_LANG=en
# SAYU_TRAILER=false
```

## Environment Variables

```bash
# Core settings
export SAYU_ENABLED=false              # Disable Sayu
export SAYU_LANG=en                    # Language (ko | en)
export SAYU_TRAILER=false              # Disable commit trailer

# LLM Configuration
export SAYU_GEMINI_API_KEY=your-key    # Gemini API key
export SAYU_OPENROUTER_API_KEY=your-key # OpenRouter API key
export SAYU_LLM_PROVIDER=gemini        # LLM provider (gemini | openrouter)
export SAYU_OPENROUTER_MODEL=anthropic/claude-3-haiku  # OpenRouter model

# Debug
export SAYU_DEBUG=true                 # Enable debug logging
```

## FAQ

### Q: Where is my data stored?
A: Sayu uses in-memory storage only. Conversations are collected during commit and immediately discarded after processing. No persistent database is created.

### Q: How do I add support for a new AI tool?
A: Create a new collector by extending `ConversationCollector` in `domain/collectors/conversation.py`

### Q: How do I change the summary language?
A: Change `language` in `.sayu.yml` or set `SAYU_LANG` environment variable

### Q: How do I disable Sayu temporarily?
A: Set `SAYU_ENABLED=false` or use `--no-verify` with git commit

### Q: What if the LLM API fails?
A: Sayu is fail-safe. If LLM fails, your commit proceeds normally with a fallback message.

## Privacy & Security

- All processing happens locally on your machine
- No data is sent except to your configured LLM API
- No persistent storage or logging of conversations
- API keys are only read from environment variables

## Troubleshooting

```bash
# Enable debug mode for detailed logs
export SAYU_DEBUG=true
git commit -m "test"

# Check if collectors are working
sayu health

# Test LLM connection
sayu preview
```

## License

MIT