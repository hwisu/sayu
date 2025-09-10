"""Store manager for event storage"""

from .memory_store import InMemoryEventStore


class StoreManager:
    """Manages singleton event store instance"""
    
    _instance = None
    
    @classmethod
    def get_store(cls) -> InMemoryEventStore:
        """Get or create store instance"""
        if cls._instance is None:
            cls._instance = InMemoryEventStore()
        return cls._instance
    
    @classmethod
    def clear(cls):
        """Clear the store (useful for testing)"""
        if cls._instance:
            cls._instance.clear()
    
    @classmethod
    def check_connection(cls):
        """Check store connectivity (compatibility method)"""
        # In-memory store is always available
        cls.get_store()
        return True