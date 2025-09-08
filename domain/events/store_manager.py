"""Store manager singleton for event database"""

from pathlib import Path
from .store import EventStore


class StoreManager:
    """Singleton manager for event store"""
    
    _instance = None
    
    @classmethod
    def get_store(cls) -> EventStore:
        """Get or create event store instance"""
        if cls._instance is None:
            cls._instance = EventStore()
        return cls._instance
    
    @classmethod
    def check_connection(cls):
        """Check database connection"""
        store = cls.get_store()
        # Test connection by attempting a query
        try:
            store.find_by_time_range(0, 1)
            return True
        except Exception as e:
            raise ConnectionError(f"Database connection failed: {e}")