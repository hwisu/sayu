# Sayu - AI Coding Context for Git Commits

> Automatically capture the "why" behind your code changes from AI conversations

[한국어](README.ko-kr.md)

## What is Sayu?

Sayu analyzes your conversations with AI coding assistants (Cursor, Claude) and automatically adds meaningful context to your git commits.

## Key Features

- **AI conversation collection**: Automatically collects conversations from Cursor and Claude Desktop
- **Smart filtering**: Reduces noise by 93% to focus on relevant content
- **Fast processing**: Generates context in 2-3 seconds during commit
- **Privacy-first**: All data stored locally
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
- Create local database (`~/.sayu/events.db`)
- Generate config file (`.sayu.yml`)

### 2. Set API Key (System Environment)

Set your API key as a system environment variable:

```bash
# Gemini API key (required)
export SAYU_GEMINI_API_KEY=your_api_key_here
```

### 3. Commit as usual

```bash
git add .
git commit -m "Fix authentication bug"
```

Result:
```
Fix authentication bug

---
AI-Context (sayu)

Intent:
  Fix JWT token validation logic to resolve login failures

Changes:
  Improved exception handling in auth.js token decoding
  Added test cases for expired tokens in test/auth.test.js

Context:
  Discussed error handling approaches with Claude for token expiration.
  Identified need for more granular exception handling.
  Found and fixed several edge cases during test implementation.
---
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
# AI automatically collects your development context

connectors:
  claude: true
  cursor: true
  editor: true
  cli:
    mode: "zsh-preexec"   # or "atuin" | "off"

privacy:
  maskSecrets: true       # Mask sensitive information
  masks:                  # Additional masking patterns (regex)
    - "AKIA[0-9A-Z]{16}"  # AWS Access Key
    - "(?i)authorization:\\s*Bearer\\s+[A-Za-z0-9._-]+"

output:
  commitTrailer: true     # Add trailer to commit messages
```

## Environment Variables

```bash
# Language and feature toggles
export SAYU_ENABLED=false              # Disable Sayu
export SAYU_LANG=en                   # Language (ko | en)
export SAYU_TRAILER=false             # Disable commit trailer

# API Keys (system environment variables)
export SAYU_GEMINI_API_KEY=your-key-here
export SAYU_OPENROUTER_API_KEY=your-key-here    # Optional: for OpenRouter
export SAYU_LLM_PROVIDER=gemini              # LLM provider (gemini | openrouter)
```

## FAQ

### Q: How do I add support for a new AI tool?
A: Create a new collector in `domain/collectors/`:

1. Create new file based on existing collectors (claude.py, cursor.py)
2. Implement `pull_since()` method (collect conversations in time range)
3. Implement `discover()` method (check if tool is installed)
4. Register in `domain/collectors/manager.py`

### Q: How do I change the summary language?
A: Change `language` in `.sayu.yml` or add new language in `i18n/prompts/`

### Q: How do I manage cache buildup?
A: Cache files older than 1 hour are automatically cleaned on commit. For manual cleanup: `rm -rf .sayu/cache/`

### Q: How do I protect sensitive information?
A: Set `privacy.maskSecrets` to `true` in `.sayu.yml` and add regex patterns to `masks`

## Target Users

- Developers using Cursor + Claude for coding
- Teams that value commit history quality
- Anyone who wants to preserve AI conversation context

## Contributing

Issues and PRs are welcome!

## License

MIT
