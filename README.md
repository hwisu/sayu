# Sayu

AI conversation history tracker with timeline visualization and Git integration.

## Features

- **Claude Code Integration**: Automatically captures Claude Code conversations
- **Git Integration**: Track commits and correlate with AI sessions
- **Timeline Visualization**: View your AI interactions and commits over time
- **AI-Powered Summaries**: Summarize work sessions using LLMs (OpenAI, OpenRouter, or custom)
- **Extensible Architecture**: Easy to add new collectors via adapter pattern

## Installation

```bash
# Clone the repository
git clone https://github.com/hwisu/sayu
cd sayu

# Install with pip (Python 3.12+)
pip install -e .

# Or use pipx for isolated installation
pipx install -e .
```

## Quick Start

```bash
# Initialize in your project
sayu init

# Collect events manually
sayu collect

# View recent events
sayu timeline -n 20

# Summarize since last commit (short alias: sslc)
sayu sslc

# Or use the full command
sayu summarize-since-last-commit

# Summarize with custom timeframe
sayu summarize --hours 2 --last 8

# Show diff between commits
sayu diff HEAD~2..HEAD
```

## Commands

### Core Commands
- `sayu init` - Initialize Sayu in current directory
- `sayu collect` - Manually collect events from all sources
- `sayu timeline` - Show event timeline with options:
  - `-n, --last N` - Show last N events
  - `-s, --source` - Filter by source (claude-code, git)
  - `-v, --verbose` - Show full content

### Summarization Commands
- `sayu summarize` - Summarize events within timeframes
  - `-h, --hours` - Timeframe size in hours
  - `--last N` - Look back N hours
  - `--since-commit` - Use last commit as reference (default)
  - `--structured` - Use structured output format

- `sayu sslc` / `sayu summarize-since-last-commit` - Quick summary since last commit
  - `-e, --engine` - Custom LLM engine command

- `sayu diff [COMMIT_RANGE]` - Show events between commits
  - Examples:
    - `sayu diff` - Since last commit
    - `sayu diff HEAD~1..HEAD` - Between last 2 commits
    - `sayu diff abc123..def456` - Between specific commits

### Other Commands
- `sayu stats` - Show statistics about collected events
- `sayu watch` - Watch for new events in real-time
- `sayu git-hook` - Set up Git hooks for automatic collection
- `sayu clean` - Remove Sayu from project

## Configuration

`.sayu.yml`:
```yaml
collectors:
  claude-code:
    enabled: true
  git:
    enabled: true
db_path: $HOME/.sayu/events.db
default_provider: openrouter  # or openai, custom
timeframe_hours: 2
```

### LLM Providers

Sayu supports multiple LLM providers for summarization:

1. **OpenRouter** (default):
   - Set `OPENROUTER_API_KEY` environment variable
   - Uses Claude 3.5 Sonnet by default

2. **OpenAI**:
   - Set `OPENAI_API_KEY` environment variable
   - Uses GPT-4o by default

3. **Custom**:
   - Use `-e` flag with any command that accepts stdin/stdout
   - Example: `sayu sslc -e "ollama run llama2"`

## Environment Variables

- `OPENROUTER_API_KEY` - API key for OpenRouter
- `OPENAI_API_KEY` - API key for OpenAI
- `SAYU_STRUCTURED_OUTPUT=true` - Enable structured output format for summaries

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Extending with Custom Collectors

Create a new collector by extending the `Collector` base class:

```python
from sayu.core import Collector, Event, EventType
from datetime import datetime

class MyCollector(Collector):
    @property
    def name(self):
        return "my-source"

    def setup(self):
        # Set up hooks or watchers
        pass

    def teardown(self):
        # Clean up
        pass

    def collect(self, since=None):
        # Return list of Event objects
        return [
            Event(
                type=EventType.OTHER,
                source=self.name,
                content="Event content",
                metadata={"key": "value"},
                timestamp=datetime.now()
            )
        ]
```

## Project Structure

```
sayu/
├── src/
│   ├── cli.py              # Command-line interface
│   ├── config.py            # Configuration management
│   ├── core/
│   │   ├── collector.py    # Base collector interface
│   │   └── storage.py      # SQLite storage
│   ├── collectors/
│   │   ├── claude_code.py  # Claude Code collector
│   │   └── git.py          # Git collector
│   ├── engine/
│   │   └── summarizer.py   # LLM summarization
│   └── visualizer/
│       └── timeline.py     # Timeline visualization
├── pyproject.toml           # Package configuration
└── .sayu.yml               # User configuration
```

## License

MIT