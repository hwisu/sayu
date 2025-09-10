# Sayu

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=flat&logo=rust&logoColor=white)](https://www.rust-lang.org/)

Capture the "why" behind your code changes from AI conversations.

## Quick Start

```bash
# Build from source
cargo build --release

# Install globally
cargo install --path .

# Initialize in your repo
sayu init

# Set API key (choose one)
export SAYU_GEMINI_API_KEY=your_key

# Or use OpenRouter (recommended for better model access)
export SAYU_OPENROUTER_API_KEY=your_key
export SAYU_LLM_MODEL=anthropic/claude-3.5-haiku  # Optional: specify model

# Commit normally
git commit -m "Fix bug"
```

Your commits will automatically include AI-analyzed context.

## Features

- Collects conversations from Cursor & Claude Desktop
- Adds meaningful context to git commits
- Processes everything locally
- Never blocks commits
- Written in Rust for performance and reliability

## Commands

```bash
sayu --version    # Show version
sayu health       # Check status
sayu init         # Initialize in repository
sayu show -n 5    # Show recent events
sayu uninstall    # Remove from repository
```

## Configuration

`.sayu.yml` (only language is configurable):
```yaml
language: ko    # or en
```

The following settings are now hardcoded defaults:
- `enabled`: always true
- `commitTrailer`: always true
- All connectors: always enabled

Environment variables:
```bash
SAYU_LANG=en                    # Override language
SAYU_DEBUG=true                 # Debug mode

# LLM Configuration
SAYU_OPENROUTER_API_KEY=key     # OpenRouter API key (recommended)
SAYU_GEMINI_API_KEY=key         # Google Gemini API key
SAYU_LLM_MODEL=model_name       # Model to use (default: anthropic/claude-3.5-haiku)
SAYU_LLM_TEMPERATURE=0.7        # Creativity level (0.0-1.0)
SAYU_LLM_MAX_TOKENS=1000        # Maximum tokens
```

Popular OpenRouter models:
- `anthropic/claude-3.5-haiku` - Fast and cost-effective
- `anthropic/claude-3.5-sonnet` - Balanced performance
- `openai/gpt-4o-mini` - Fast and cheap
- `meta-llama/llama-3.1-8b-instruct` - Open source

## Building

```bash
# Development build
cargo build

# Release build (optimized)
cargo build --release

# Run tests
cargo test

# Install locally
cargo install --path .
```

## License

MIT
