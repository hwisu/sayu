"""Cursor collector for extracting AI conversation data"""

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from domain.events.types import Event, EventSource, EventKind, Actor, Config, Connector


class CursorCollector:
    """Collect AI conversations from Cursor IDE"""
    
    id = 'cursor.ai'
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize Cursor collector"""
        self.repo_root = repo_root or os.getcwd()
        self.cursor_base_path = Path.home() / 'Library' / 'Application Support' / 'Cursor'
        
    def discover(self, repo_root: str) -> bool:
        """Check if Cursor is available and has conversation data"""
        try:
            global_db = self.cursor_base_path / 'User' / 'globalStorage' / 'state.vscdb'
            if not global_db.exists():
                return False
            
            # Check if there are any workspace databases
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            if not workspace_dir.exists():
                return False
                
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            return len(workspace_dbs) > 0
            
        except Exception:
            return False
    
    def pull_since(self, since_ms: int, until_ms: int, cfg: Config) -> List[Event]:
        """Pull Cursor conversation events within time range"""
        events = []
        
        try:
            # Get all workspace databases
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            for db_path in workspace_dbs:
                try:
                    workspace_events = self._extract_from_workspace_db(
                        str(db_path), since_ms, until_ms
                    )
                    events.extend(workspace_events)
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error processing Cursor workspace DB {db_path}: {e}")
                        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cursor collector error: {e}")
        
        return events
    
    def health(self) -> Dict[str, Any]:
        """Health check for Cursor collector"""
        try:
            if not self.discover(self.repo_root):
                return {'ok': False, 'reason': 'Cursor not found or no conversation data'}
            
            # Count available conversations
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            total_conversations = 0
            for db_path in workspace_dbs:
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
                    )
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        data = json.loads(result[0])
                        total_conversations += len(data.get('allComposers', []))
                        
                except Exception:
                    continue
            
            return {
                'ok': True, 
                'conversations': total_conversations,
                'workspaces': len(workspace_dbs)
            }
            
        except Exception as e:
            return {'ok': False, 'reason': str(e)}
    
    def redact(self, event: Event, cfg: Config) -> Event:
        """Redact sensitive information from Cursor event"""
        if not cfg.privacy.maskSecrets:
            return event
        
        # Apply privacy masks
        text = event.text
        for pattern in cfg.privacy.masks:
            import re
            text = re.sub(pattern, '[REDACTED]', text)
        
        return Event(
            id=event.id,
            ts=event.ts,
            source=event.source,
            kind=event.kind,
            repo=event.repo,
            cwd=event.cwd,
            file=event.file,
            range=event.range,
            actor=event.actor,
            text=text,
            url=event.url,
            meta=event.meta
        )
    
    def _extract_from_workspace_db(
        self, db_path: str, since_ms: int, until_ms: int
    ) -> List[Event]:
        """Extract conversation events from a workspace database"""
        events = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get composer data
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
            )
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return events
            
            composer_data = json.loads(result[0])
            all_composers = composer_data.get('allComposers', [])
            
            for composer in all_composers:
                try:
                    # Extract timing information
                    created_at = composer.get('createdAt')
                    updated_at = composer.get('lastUpdatedAt')
                    
                    if not created_at:
                        continue
                    
                    # Check if conversation was created or updated within time range
                    in_creation_range = since_ms <= created_at <= until_ms
                    in_update_range = updated_at and since_ms <= updated_at <= until_ms
                    
                    if not (in_creation_range or in_update_range):
                        continue
                    
                    # Create event for conversation start
                    start_event = Event(
                        id=str(uuid.uuid4()),
                        ts=created_at,
                        source=EventSource.LLM,
                        kind=EventKind.CHAT,
                        repo=self.repo_root,
                        cwd=self.repo_root,
                        file=None,
                        range=None,
                        actor=Actor.USER,
                        text=f"Started Cursor conversation: {composer.get('name', 'Untitled')}",
                        url=None,
                        meta={
                            'composerId': composer.get('composerId'),
                            'type': 'conversation_start',
                            'mode': composer.get('unifiedMode'),
                            'forceMode': composer.get('forceMode'),
                            'tool': 'cursor'
                        }
                    )
                    events.append(start_event)
                    
                    # If conversation was updated, create update event
                    if updated_at and updated_at != created_at and updated_at <= until_ms:
                        update_event = Event(
                            id=str(uuid.uuid4()),
                            ts=updated_at,
                            source=EventSource.LLM,
                            kind=EventKind.CHAT,
                            repo=self.repo_root,
                            cwd=self.repo_root,
                            file=None,
                            range=None,
                            actor=Actor.ASSISTANT,
                            text=f"Cursor conversation updated: {composer.get('name', 'Untitled')}",
                            url=None,
                            meta={
                                'composerId': composer.get('composerId'),
                                'type': 'conversation_update',
                                'mode': composer.get('unifiedMode'),
                                'duration': updated_at - created_at,
                                'tool': 'cursor'
                            }
                        )
                        events.append(update_event)
                        
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error processing composer {composer}: {e}")
                    continue
            
            conn.close()
            
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error reading Cursor workspace DB {db_path}: {e}")
        
        return events
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent conversations for debugging/inspection"""
        conversations = []
        
        try:
            since_ms = int((time.time() - hours * 3600) * 1000)
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            for db_path in workspace_dbs:
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        data = json.loads(result[0])
                        for composer in data.get('allComposers', []):
                            if composer.get('lastUpdatedAt', 0) >= since_ms:
                                conversations.append({
                                    'id': composer.get('composerId'),
                                    'name': composer.get('name'),
                                    'created': composer.get('createdAt'),
                                    'updated': composer.get('lastUpdatedAt'),
                                    'mode': composer.get('unifiedMode'),
                                    'workspace': str(db_path.parent.name)
                                })
                    
                    conn.close()
                    
                except Exception:
                    continue
                    
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error getting recent conversations: {e}")
        
        return sorted(conversations, key=lambda x: x.get('updated', 0), reverse=True)
