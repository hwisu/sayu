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
SAYU_LANG=en          # Override language
SAYU_DEBUG=true       # Debug mode
```

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