"""Environment variable loader with .env file support"""

import os
from pathlib import Path
from typing import Optional


class EnvLoader:
    """Load environment variables from .env file"""
    
    _loaded = False
    
    @classmethod
    def load(cls, repo_root: Optional[str] = None) -> None:
        """Load .env file from repository root"""
        if cls._loaded:
            return
        
        # Find .env file
        if repo_root:
            env_path = Path(repo_root) / '.env'
        else:
            # Try current directory and parent directories
            current = Path.cwd()
            env_path = None
            
            for parent in [current] + list(current.parents):
                potential_env = parent / '.env'
                if potential_env.exists():
                    env_path = potential_env
                    break
                
                # Stop at git root
                if (parent / '.git').exists():
                    break
        
        if env_path and env_path.exists():
            cls._load_env_file(env_path)
            cls._loaded = True
    
    @classmethod
    def _load_env_file(cls, env_path: Path) -> None:
        """Parse and load .env file"""
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Only set if not already in environment
                        # This allows actual env vars to override .env file
                        if key not in os.environ:
                            os.environ[key] = value
                            
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Loaded from .env: {key}")
                                
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Failed to load .env file: {e}")
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with .env file support"""
        # Ensure .env is loaded
        if not cls._loaded:
            cls.load()
        
        return os.getenv(key, default)