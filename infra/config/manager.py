"""Configuration management for Sayu"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from domain.events.types import Config, UserConfig
from shared import constants


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
        
        # System environment variable overrides (always take precedence)
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
        
        # Load full config from .sayu.yml if exists
        config_path = self.repo_root / self.CONFIG_FILE
        raw_config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f) or {}
            except Exception:
                pass
        
        return Config(
            connectors=raw_config.get('connectors', {
                'claude': True,
                'cursor': True,
                'editor': True,
                'cli': {'mode': 'zsh-preexec'},
                'git': True
            }),
            privacy=raw_config.get('privacy', {
                'maskSecrets': False,
                'masks': list(constants.DEFAULT_SECURITY_MASKS)
            }),
            output=raw_config.get('output', {
                'commitTrailer': user_config.commitTrailer
            })
        )
    
    def get_effective_config(self) -> UserConfig:
        """Get effective user configuration"""
        return self.get_user_config()
    
    def get_constants(self) -> Dict[str, Any]:
        """Get constants - no longer overridable via config"""
        # Return hardcoded constants
        return {
            'DEFAULT_LOOKBACK_HOURS': constants.DEFAULT_LOOKBACK_HOURS,
            'MAX_COMMIT_TRAILER_LINES': constants.MAX_COMMIT_TRAILER_LINES,
            'CACHE_TTL_SECONDS': constants.CACHE_TTL_SECONDS,
            'COLLECTOR_TIMEOUT_MS': constants.COLLECTOR_TIMEOUT_MS,
            'MAX_CONVERSATION_COUNT': constants.MAX_CONVERSATION_COUNT,
            'MAX_CONVERSATION_LENGTH': constants.MAX_CONVERSATION_LENGTH,
            'MAX_SIMPLIFIED_CONVERSATIONS': constants.MAX_SIMPLIFIED_CONVERSATIONS,
            'MAX_SIMPLIFIED_LENGTH': constants.MAX_SIMPLIFIED_LENGTH,
            'MAX_HIGH_VALUE_EVENTS': constants.MAX_HIGH_VALUE_EVENTS,
            'MIN_RESPONSE_LENGTH': constants.MIN_RESPONSE_LENGTH,
            'MAX_RAW_RESPONSE_LENGTH': constants.MAX_RAW_RESPONSE_LENGTH,
            'MAX_FILE_DISPLAY': constants.MAX_FILE_DISPLAY,
            'MAX_LINE_LENGTH': constants.MAX_LINE_LENGTH,
            'LLM_TEMPERATURE': constants.LLM_TEMPERATURE,
            'LLM_MAX_OUTPUT_TOKENS': constants.LLM_MAX_OUTPUT_TOKENS,
            'SUMMARY_SEPARATOR': constants.SUMMARY_SEPARATOR,
            'SUMMARY_FOOTER': constants.SUMMARY_FOOTER
        }
    
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
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

connectors:
  claude: true
  cursor: true
  editor: true
  cli:
    mode: "zsh-preexec"   # or "atuin" | "off"

privacy:
  maskSecrets: true       # 민감정보 마스킹 여부
  masks:                  # 추가 마스킹 패턴 (정규식)
    - "AKIA[0-9A-Z]{16}"  # AWS Access Key
    - "(?i)authorization:\\s*Bearer\\s+[A-Za-z0-9._-]+"

output:
  commitTrailer: true     # 커밋 메시지에 트레일러 추가

# 환경 변수로도 설정 가능:
# SAYU_ENABLED=false
# SAYU_LANG=en
# SAYU_TRAILER=false
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        
        print(f"Created config at {config_path}")


# Alias for compatibility
SimpleConfigManager = ConfigManager
