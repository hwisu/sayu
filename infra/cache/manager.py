"""Simple caching mechanism for Sayu"""

import hashlib
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
    
    def clear(self) -> None:
        """Clear all cache files"""
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cache clear error: {e}")
    
    def cleanup_old_cache(self, max_age_seconds: int = 86400) -> int:
        """Remove cache files older than max_age_seconds (default: 24 hours)
        
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        current_time = time.time()
        
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                try:
                    # Check file modification time
                    if current_time - cache_file.stat().st_mtime > max_age_seconds:
                        cache_file.unlink()
                        cleaned += 1
                except (OSError, IOError):
                    # Skip files that can't be accessed
                    continue
                    
            if os.getenv('SAYU_DEBUG') and cleaned > 0:
                print(f"Cleaned up {cleaned} old cache files")
                
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cache cleanup error: {e}")
                
        return cleaned


class CollectorCache:
    """Specialized cache for collector operations"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    def get_last_commit_time(self, repo_root: str) -> Optional[int]:
        """Get cached last commit time"""
        # Use stable hash for consistent cache keys across runs
        cache_key = f"last_commit_time_{self._stable_hash(repo_root)}"
        return self.cache.get(cache_key, ttl=60)
    
    def set_last_commit_time(self, repo_root: str, timestamp: int) -> None:
        """Cache last commit time"""
        cache_key = f"last_commit_time_{self._stable_hash(repo_root)}"
        self.cache.set(cache_key, timestamp)
    
    def _stable_hash(self, value: str) -> str:
        """Create a stable hash that's consistent across Python runs"""
        return hashlib.md5(value.encode()).hexdigest()[:16]
    
    def get_file_paths(self, collector: str) -> Optional[Dict[str, Any]]:
        """Get cached file paths for collector"""
        return self.cache.get(f"file_paths_{collector}", ttl=600)
    
    def set_file_paths(self, collector: str, paths: Dict[str, Any]):
        """Cache file paths for collector"""
        self.cache.set(f"file_paths_{collector}", paths)