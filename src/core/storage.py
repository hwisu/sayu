"""Storage for collected events."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source ON events(source)
            """
            )

    def add_event(self, event: Event) -> None:
        """Add an event to storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO events (timestamp, type, source, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    event.timestamp.isoformat(),
                    event.type.value,
                    event.source,
                    event.content,
                    json.dumps(event.metadata),
                ),
            )

    def add_events(self, events: list[Event]) -> None:
        """Add multiple events to storage, avoiding duplicates."""
        with sqlite3.connect(self.db_path) as conn:
            # Check for existing events to avoid duplicates
            for event in events:
                # Check if this exact event already exists
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE timestamp = ? AND source = ? AND content = ?
                """,
                    (event.timestamp.isoformat(), event.source, event.content),
                )

                if cursor.fetchone()[0] == 0:
                    # Event doesn't exist, add it
                    conn.execute(
                        """
                        INSERT INTO events (timestamp, type, source, content, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            event.timestamp.isoformat(),
                            event.type.value,
                            event.source,
                            event.content,
                            json.dumps(event.metadata),
                        ),
                    )

    def get_events(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        source: str | None = None,
        event_type: EventType | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Get events with optional filters."""
        query = (
            "SELECT timestamp, type, source, content, metadata FROM events WHERE 1=1"
        )
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
                    metadata=json.loads(row[4]) if row[4] else {},
                )
                for row in cursor
            ]

    def get_latest_timestamp(self, source: str | None = None) -> datetime | None:
        """Get the timestamp of the latest event."""
        query = "SELECT MAX(timestamp) FROM events"
        params = []

        if source:
            query += " WHERE source = ?"
            params.append(source)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            result = cursor.fetchone()[0]
            if result:
                # Parse ISO format datetime and make it timezone-naive
                date_str = result
                if "+" in date_str or date_str.endswith("Z"):
                    # Remove timezone info to make it naive
                    date_str = date_str.split("+")[0].split("Z")[0]
                return datetime.fromisoformat(date_str)
            return None

    def clear(self) -> None:
        """Clear all events from storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM events")
