"""Configuration management for Sayu"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from domain.events.types import Config, UserConfig
from shared.constants import DEFAULT_SECURITY_MASKS


class ConfigManager:
    """Manage Sayu configuration"""
    
    CONFIG_FILE = '.sayu.yml'
    
    def __init__(self, repo_root: str):
        """Initialize config manager for repository"""
        self.repo_root = Path(repo_root)
        self.user_config = self._load_user_config()
    
    def _load_user_config(self) -> UserConfig:
        """Load user configuration from file"""
        config_path = self.repo_root / self.CONFIG_FILE
        
        raw_config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
        
        # Parse with defaults
        return UserConfig(
            enabled=raw_config.get('enabled', True),
            language=raw_config.get('language', 'ko'),
            commitTrailer=raw_config.get('commitTrailer', True)
        )
    
    def get_user_config(self) -> UserConfig:
        """Get user config with environment overrides"""
        config = UserConfig(
            enabled=self.user_config.enabled,
            language=self.user_config.language,
            commitTrailer=self.user_config.commitTrailer
        )
        
        # Environment variable overrides
        if os.getenv('SAYU_ENABLED') == 'false':
            config.enabled = False
        if os.getenv('SAYU_LANG') in ['en', 'ko']:
            config.language = os.getenv('SAYU_LANG')
        if os.getenv('SAYU_TRAILER') == 'false':
            config.commitTrailer = False
        
        return config
    
    def get(self) -> Config:
        """Get full configuration for backward compatibility"""
        user_config = self.get_user_config()
        
        return Config(
            connectors={
                'claude': True,
                'cursor': True,
                'editor': True,
                'cli': {'mode': 'zsh-preexec'},
                'browser': {'mode': 'off'},
                'git': True
            },
            window={'beforeCommitHours': 24},
            filter={
                'domainAllowlist': [
                    'github.com',
                    'developer.mozilla.org',
                    'stackoverflow.com'
                ],
                'noise': {'graceMinutes': 5, 'minScore': 0.6}
            },
            summarizer={
                'mode': 'hybrid',
                'maxLines': {'commit': 12}
            },
            privacy={
                'maskSecrets': False,
                'masks': list(DEFAULT_SECURITY_MASKS)
            },
            output={
                'commitTrailer': user_config.commitTrailer,
                'gitNotes': False
            }
        )
    
    def get_effective_config(self) -> UserConfig:
        """Get effective user configuration"""
        return self.get_user_config()
    
    def save(self, new_config: Dict[str, Any]):
        """Save updated configuration"""
        # Merge with existing
        merged = {
            'enabled': new_config.get('enabled', self.user_config.enabled),
            'language': new_config.get('language', self.user_config.language),
            'commitTrailer': new_config.get('commitTrailer', self.user_config.commitTrailer)
        }
        
        self.user_config = UserConfig(**merged)
        
        # Write to file
        config_path = self.repo_root / self.CONFIG_FILE
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(merged, f, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def create_default(cls, repo_root: str):
        """Create default configuration file"""
        config_path = Path(repo_root) / cls.CONFIG_FILE
        
        if config_path.exists():
            return
        
        default_content = """# Sayu Configuration
# AI automatically collects your development context

# Enable Sayu (set to false to disable)
enabled: true

# Language setting (ko: Korean, en: English)
language: ko

# Add AI context to commit messages
commitTrailer: true

# Can also be configured via environment variables:
# SAYU_ENABLED=false
# SAYU_LANG=en
# SAYU_TRAILER=false
#
# LLM API keys in .env file:
# GEMINI_API_KEY=your-key
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        
        print(f"Created config at {config_path}")


# Alias for compatibility
SimpleConfigManager = ConfigManager
