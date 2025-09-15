"""Configuration management for Sayu."""

import os
from pathlib import Path
from typing import Optional

import yaml


class Config:
    """Configuration manager."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.config_path = config_path or Path.cwd() / ".sayu.yml"
        self.data = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.data, f, default_flow_style=False)
    
    @property
    def db_path(self) -> Path:
        """Get database path."""
        return Path(self.data.get("db_path", Path.home() / ".sayu" / "events.db"))
    
    @property
    def default_provider(self) -> str:
        """Get default LLM provider."""
        return self.data.get("default_provider", "openrouter")
    
    @property
    def timeframe_hours(self) -> int:
        """Get default timeframe in hours."""
        return self.data.get("timeframe_hours", 2)
    
    def get_collector_config(self, name: str) -> dict:
        """Get configuration for a specific collector."""
        return self.data.get("collectors", {}).get(name, {})