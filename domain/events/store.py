"""Event store for SQLite database operations"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any

from .types import Event, EventRow, EventSource, EventKind, Actor


class EventStore:
    """SQLite-based event storage"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize event store with database"""
        default_path = Path.home() / '.sayu' / 'events.db'
        self.db_path = Path(db_path) if db_path else default_path
        
        # Create directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main events table
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    ts INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    cwd TEXT NOT NULL,
                    file TEXT,
                    range_start INTEGER,
                    range_end INTEGER,
                    actor TEXT,
                    text TEXT NOT NULL,
                    url TEXT,
                    meta TEXT NOT NULL DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_repo_ts ON events(repo, ts);
                CREATE INDEX IF NOT EXISTS idx_events_file_ts ON events(file, ts) WHERE file IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
                CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
            """)
            
            # FTS5 virtual table for full-text search
            conn.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                    text,
                    content='events',
                    content_rowid='rowid'
                );
                
                CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
                    INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
                END;
                
                CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
                    DELETE FROM events_fts WHERE rowid = old.rowid;
                END;
                
                CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE OF text ON events BEGIN
                    UPDATE events_fts SET text = new.text WHERE rowid = new.rowid;
                END;
            """)
    
    def insert(self, event: Event):
        """Insert single event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events (
                    id, ts, source, kind, repo, cwd, file,
                    range_start, range_end, actor, text, url, meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(event.id),
                event.ts,
                event.source.value,
                event.kind.value,
                event.repo,
                event.cwd,
                event.file,
                event.range.start if event.range else None,
                event.range.end if event.range else None,
                event.actor.value if event.actor else None,
                event.text,
                event.url,
                json.dumps(event.meta)
            ))
            conn.commit()
    
    def insert_batch(self, events: List[Event]):
        """Insert multiple events in transaction"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                for event in events:
                    conn.execute("""
                        INSERT INTO events (
                            id, ts, source, kind, repo, cwd, file,
                            range_start, range_end, actor, text, url, meta
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(event.id),
                        event.ts,
                        event.source.value,
                        event.kind.value,
                        event.repo,
                        event.cwd,
                        event.file,
                        event.range.start if event.range else None,
                        event.range.end if event.range else None,
                        event.actor.value if event.actor else None,
                        event.text,
                        event.url,
                        json.dumps(event.meta)
                    ))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def find_by_time_range(self, start_ms: int, end_ms: int) -> List[Event]:
        """Find events by time range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE ts >= ? AND ts <= ?
                ORDER BY ts DESC
            """, (start_ms, end_ms))
            
            rows = cursor.fetchall()
            return [self._row_to_event(row) for row in rows]
    
    def find_by_file(self, file: str, start_ms: int, end_ms: int) -> List[Event]:
        """Find events by file and time range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE file = ? AND ts >= ? AND ts <= ?
                ORDER BY ts DESC
            """, (file, start_ms, end_ms))
            
            rows = cursor.fetchall()
            return [self._row_to_event(row) for row in rows]
    
    def find_by_repo(self, repo: str, start_ms: int, end_ms: int) -> List[Event]:
        """Find events by repository and time range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE repo = ? AND ts >= ? AND ts <= ?
                ORDER BY ts DESC
            """, (repo, start_ms, end_ms))
            
            rows = cursor.fetchall()
            return [self._row_to_event(row) for row in rows]
    
    def get_last_commit_time(self, repo: str) -> Optional[int]:
        """Get timestamp of last commit for repo"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT ts FROM events
                WHERE repo = ? AND source = 'git' AND kind = 'commit'
                ORDER BY ts DESC
                LIMIT 1
            """, (repo,))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    def find_last_commit(self, repo: str) -> Optional[Event]:
        """Find last commit event for repo"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE repo = ? AND source = 'git' AND kind = 'commit'
                ORDER BY ts DESC
                LIMIT 1
            """, (repo,))
            
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None
    
    def search_text(self, query: str, limit: int = 100) -> List[Event]:
        """Full-text search events"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT e.* FROM events e
                JOIN events_fts ON e.rowid = events_fts.rowid
                WHERE events_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            rows = cursor.fetchall()
            return [self._row_to_event(row) for row in rows]
    
    def _row_to_event(self, row: tuple) -> Event:
        """Convert database row to Event object"""
        from .types import Range
        
        # Map row columns by index
        return Event(
            id=row[0],
            ts=row[1],
            source=EventSource(row[2]),
            kind=EventKind(row[3]),
            repo=row[4],
            cwd=row[5],
            file=row[6],
            range=Range(start=row[7], end=row[8]) if row[7] and row[8] else None,
            actor=Actor(row[9]) if row[9] else None,
            text=row[10],
            url=row[11],
            meta=json.loads(row[12] or '{}')
        )