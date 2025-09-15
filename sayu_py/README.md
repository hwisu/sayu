# Sayu (Python Version)

AI conversation history tracker with timeline visualization.

## Features

- **Claude Code Integration**: Automatically captures conversations via hooks
- **Timeline Visualization**: See your AI interactions over time
- **Timeframe Summarization**: Summarize work sessions using external LLMs
- **Extensible Architecture**: Easy to add new collectors via adapter pattern

## Installation

```bash
# Install in development mode
pip install -e .

# Or install normally
pip install .
```

## Quick Start

```bash
# Initialize in your project
sayu init

# Your Claude Code conversations are now being tracked!

# View recent events
sayu timeline -n 20

# Summarize last 8 hours in 2-hour chunks
sayu summarize --hours 2 --last 8

# Watch for new events in real-time
sayu watch

# Show statistics
sayu stats
```

## Commands

- `sayu init` - Set up Sayu in current directory
- `sayu collect` - Manually collect new events
- `sayu timeline` - Show event timeline
- `sayu summarize` - Summarize events by timeframe
- `sayu watch` - Watch for new events in real-time
- `sayu stats` - Show event statistics
- `sayu clean` - Remove Sayu from project

## Configuration

`.sayu.yml`:
```yaml
db_path: ~/.sayu/events.db
default_provider: claude
timeframe_hours: 2
collectors:
  claude-code:
    enabled: true
```

## Extending with New Collectors

Create a new collector by extending the `Collector` base class:

```python
from sayu.core import Collector, Event, EventType

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
        return []
```

## License

MIT