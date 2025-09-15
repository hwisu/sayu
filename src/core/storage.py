"""Storage for collected events."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .collector import Event, EventType


class Storage:
    """SQLite-based storage for events."""
    
    def __init__(self, db_path: Path):
        """Initialize storage with database path."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source ON events(source)
            """)
    
    def add_event(self, event: Event) -> None:
        """Add an event to storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events (timestamp, type, source, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.type.value,
                event.source,
                event.content,
                json.dumps(event.metadata)
            ))
    
    def add_events(self, events: List[Event]) -> None:
        """Add multiple events to storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT INTO events (timestamp, type, source, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (
                    event.timestamp.isoformat(),
                    event.type.value,
                    event.source,
                    event.content,
                    json.dumps(event.metadata)
                )
                for event in events
            ])
    
    def get_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        source: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get events with optional filters."""
        query = "SELECT timestamp, type, source, content, metadata FROM events WHERE 1=1"
        params = []
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if event_type:
            query += " AND type = ?"
            params.append(event_type.value)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                Event(
                    timestamp=datetime.fromisoformat(row[0]),
                    type=EventType(row[1]),
                    source=row[2],
                    content=row[3],
                    metadata=json.loads(row[4]) if row[4] else {}
                )
                for row in cursor
            ]
    
    def get_latest_timestamp(self, source: Optional[str] = None) -> Optional[datetime]:
        """Get the timestamp of the latest event."""
        query = "SELECT MAX(timestamp) FROM events"
        params = []
        
        if source:
            query += " WHERE source = ?"
            params.append(source)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            result = cursor.fetchone()[0]
            return datetime.fromisoformat(result) if result else None
    
    def clear(self) -> None:
        """Clear all events from storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM events")
