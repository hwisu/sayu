"""In-memory event store for temporary event storage"""

from typing import List, Optional, Dict

from .types import Event, EventSource, EventKind


class InMemoryEventStore:
    """Simple in-memory event storage for current session only"""
    
    def __init__(self):
        """Initialize empty event store"""
        self.events: List[Event] = []
        self._last_commit_times: Dict[str, int] = {}
    
    def insert(self, event: Event):
        """Add single event"""
        self.events.append(event)
        
        # Track last commit time
        if event.source == EventSource.GIT and event.kind == EventKind.COMMIT:
            self._last_commit_times[event.repo] = event.ts
    
    def insert_batch(self, events: List[Event]):
        """Add multiple events"""
        for event in events:
            self.insert(event)
    
    def find_by_time_range(self, start_ms: int, end_ms: int) -> List[Event]:
        """Find events within time range, sorted by timestamp"""
        events = [
            event for event in self.events
            if start_ms <= event.ts <= end_ms
        ]
        # Sort by timestamp (chronological order)
        return sorted(events, key=lambda e: e.ts)
    
    def find_by_repo(self, repo: str, start_ms: int, end_ms: int) -> List[Event]:
        """Find events by repository and time range, sorted by timestamp"""
        events = [
            event for event in self.events
            if event.repo == repo and start_ms <= event.ts <= end_ms
        ]
        # Sort by timestamp (chronological order)
        return sorted(events, key=lambda e: e.ts)
    
    def get_last_commit_time(self, repo: str) -> Optional[int]:
        """Get timestamp of last commit for repo"""
        # First check our cache
        if repo in self._last_commit_times:
            return self._last_commit_times[repo]
        
        # Fall back to searching events
        commit_events = [
            event for event in self.events
            if event.repo == repo 
            and event.source == EventSource.GIT 
            and event.kind == EventKind.COMMIT
        ]
        
        if commit_events:
            return max(event.ts for event in commit_events)
        
        return None
    
    def clear(self):
        """Clear all events (useful for testing)"""
        self.events.clear()
        self._last_commit_times.clear()
    
    def get_event_count(self) -> int:
        """Get total number of events"""
        return len(self.events)
