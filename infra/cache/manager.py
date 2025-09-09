"""Simple caching mechanism for Sayu"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional


class CacheManager:
    """Manage simple file-based cache"""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.cache_dir = Path(repo_root) / '.sayu' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get cached value if not expired"""
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if cache is expired
            if time.time() - data['timestamp'] > ttl:
                cache_file.unlink()  # Delete expired cache
                return None
            
            return data['value']
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cache read error for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Set cache value"""
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            data = {
                'timestamp': time.time(),
                'value': value
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cache write error for {key}: {e}")
    
    def clear(self):
        """Clear all cache files"""
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cache clear error: {e}")


class CollectorCache:
    """Specialized cache for collector operations"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    def get_last_commit_time(self, repo_root: str) -> Optional[int]:
        """Get cached last commit time"""
        return self.cache.get(f"last_commit_time_{hash(repo_root)}", ttl=60)
    
    def set_last_commit_time(self, repo_root: str, timestamp: int):
        """Cache last commit time"""
        self.cache.set(f"last_commit_time_{hash(repo_root)}", timestamp)
    
    def get_file_paths(self, collector: str) -> Optional[Dict[str, Any]]:
        """Get cached file paths for collector"""
        return self.cache.get(f"file_paths_{collector}", ttl=600)
    
    def set_file_paths(self, collector: str, paths: Dict[str, Any]):
        """Cache file paths for collector"""
        self.cache.set(f"file_paths_{collector}", paths)