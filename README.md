# Sayu

Capture the "why" behind your code changes from AI conversations.

## Quick Start

```bash
# Install with pipx
pipx install git+https://github.com/yourusername/sayu.git

# Initialize in your repo
sayu init

# Set API key (choose one)
export SAYU_GEMINI_API_KEY=your_key

# Or use OpenRouter
export SAYU_OPENROUTER_API_KEY=your_key
export SAYU_LLM_PROVIDER=openrouter
export SAYU_OPENROUTER_MODEL=anthropic/claude-3-haiku

# Commit normally
git commit -m "Fix bug"
```

Your commits will automatically include AI-analyzed context.

## Features

- Collects conversations from Cursor & Claude Desktop
- Adds meaningful context to git commits
- Processes everything locally
- Never blocks commits

## Commands

```bash
sayu health   # Check status
sayu preview  # Preview AI context
```

## Configuration

`.sayu.yml`:
```yaml
language: en          # or ko
commitTrailer: true
connectors:
  claude: true
  cursor: true
```

Environment variables:
```bash
SAYU_ENABLED=false    # Disable temporarily
SAYU_DEBUG=true       # Debug mode
```

## License

MIT