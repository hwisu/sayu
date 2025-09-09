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

### 2. Set API Key (.env)

Add one of these API keys:

```bash
# Gemini (recommended - fast and affordable)
GEMINI_API_KEY=your_api_key_here

# Or OpenAI
OPENAI_API_KEY=your_api_key_here

# Or Anthropic
ANTHROPIC_API_KEY=your_api_key_here
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
# Data sources
connectors:
  claude: true      # Claude Desktop conversations
  cursor: true      # Cursor conversations
  cli:              # Terminal commands
    mode: "off"     # "zsh-preexec" | "off"

# Time window for data collection (hours)
window:
  beforeCommitHours: 168  # One week

# Add context to commit messages
commitTrailer: true

# Language
language: "en"  # "ko" | "en"

# Privacy
privacy:
  maskSecrets: true
  masks: []  # Regex patterns to redact
```

## Configurable Constants

Edit values in `shared/constants.py`:

### Time Settings
- `COMMIT_WINDOW_HOURS`: 24 (hours to look back from commit)
- `DEFAULT_LOOKBACK_HOURS`: 168 (default collection period)
- `CACHE_TTL_SECONDS`: 300 (cache validity)

### Text Processing
- `MAX_CONVERSATION_COUNT`: 20 (max conversations)
- `MAX_CONVERSATION_LENGTH`: 800 (max length per conversation)
- `MAX_DIFF_LENGTH`: 2000 (max diff length)
- `MIN_RESPONSE_LENGTH`: 50 (min response length)

### LLM Settings
- `LLM_TEMPERATURE`: 0.1 (lower = more consistent)
- `LLM_MAX_OUTPUT_TOKENS`: 8192 (max output tokens)

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