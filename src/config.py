"""Configuration management for Sayu."""

import os
from pathlib import Path

import yaml


class Config:
    """Configuration manager."""

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration."""
        self.config_path = config_path or Path.cwd() / ".sayu.yml"
        self.data = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.data, f, default_flow_style=False)

    @property
    def db_path(self) -> Path:
        """Get database path."""
        db_path = self.data.get("db_path", str(Path.home() / ".sayu" / "events.db"))
        # Expand environment variables
        db_path = os.path.expandvars(db_path)
        db_path = os.path.expanduser(db_path)
        return Path(db_path)

    @property
    def default_provider(self) -> str:
        """Get default LLM provider."""
        return self.data.get("default_provider", "openrouter")

    @property
    def timeframe_hours(self) -> int | None:
        """Get default timeframe in hours."""
        return self.data.get("timeframe_hours")

    def get_collector_config(self, name: str) -> dict:
        """Get configuration for a specific collector."""
        return self.data.get("collectors", {}).get(name, {})
