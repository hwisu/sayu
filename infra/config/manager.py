"""Configuration management for Sayu"""

import os
from pathlib import Path
from typing import Dict, Any
import yaml

from domain.events.types import UserConfig


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
            commitTrailer=raw_config.get('commitTrailer', True),
            connectors=raw_config.get('connectors', {
                'claude': True,
                'cursor': True,
                'cli': {'mode': 'zsh-preexec'},
                'git': True
            })
        )
    
    def get(self) -> UserConfig:
        """Get configuration with environment overrides"""
        config = UserConfig(
            enabled=self.user_config.enabled,
            language=self.user_config.language,
            commitTrailer=self.user_config.commitTrailer,
            connectors=self.user_config.connectors.copy()
        )
        
        # System environment variable overrides
        if os.getenv('SAYU_ENABLED') == 'false':
            config.enabled = False
        if os.getenv('SAYU_LANG') in ['en', 'ko']:
            config.language = os.getenv('SAYU_LANG')
        if os.getenv('SAYU_TRAILER') == 'false':
            config.commitTrailer = False
        
        return config
    
    @classmethod
    def create_default(cls, repo_root: str):
        """Create default configuration file"""
        config_path = Path(repo_root) / cls.CONFIG_FILE
        
        if config_path.exists():
            return
        
        default_content = """# Sayu Configuration
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

language: ko              # 언어 설정 (ko, en)
commitTrailer: true       # 커밋 메시지에 AI 분석 추가

connectors:
  claude: true            # Claude Desktop 대화 수집
  cursor: true            # Cursor 편집기 대화 수집
  cli:
    mode: "zsh-preexec"   # CLI 명령어 수집 (off로 비활성화)

# 환경 변수로도 설정 가능:
# SAYU_ENABLED=false
# SAYU_LANG=en
# SAYU_TRAILER=false
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        
        print(f"Created config at {config_path}")