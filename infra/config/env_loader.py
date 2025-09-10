"""System environment variable access only"""

import os
from typing import Optional


class EnvLoader:
    """Access system environment variables only - no .env file support"""
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get system environment variable only"""
        return os.getenv(key, default)
