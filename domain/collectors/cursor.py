"""Cursor editor conversation collector"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

from domain.events.types import EventSource
from .conversation_base import ConversationCollector


class CursorConversationCollector(ConversationCollector):
    """Collector for Cursor editor conversations"""
    
    def __init__(self, repo_root: str):
        """Initialize collector with repository root"""
        super().__init__(repo_root)
        self._db_path = None
        self._workspace_db_path = None
        self._composers_cache = None
        
    def get_event_source(self) -> EventSource:
        return EventSource.CURSOR
    
    def _get_db_paths(self) -> tuple:
        """Get Cursor database paths"""
        if self._db_path is None:
            # Global state database
            self._db_path = Path.home() / '.config' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb'
            if not self._db_path.exists():
                # Try macOS location
                self._db_path = Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb'
            
            # Workspace-specific database
            workspace_storage = Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'workspaceStorage'
            if not workspace_storage.exists():
                workspace_storage = Path.home() / '.config' / 'Cursor' / 'User' / 'workspaceStorage'
            
            # Find workspace folder for this repo
            if workspace_storage.exists():
                # First try known workspace ID (fallback)
                known_workspace_id = 'c9d4d11cea7f9eaa4212fe4c48c46a55'  # sayu workspace
                known_ws_path = workspace_storage / known_workspace_id / 'state.vscdb'
                
                if known_ws_path.exists():
                    self._workspace_db_path = known_ws_path
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Using known workspace: {known_workspace_id}")
                else:
                    # Search all workspaces to find the one matching our repo
                    repo_name = Path(self.repo_root).name
                    repo_path_abs = os.path.abspath(self.repo_root)
                    
                    for ws_folder in workspace_storage.iterdir():
                        if not ws_folder.is_dir():
                            continue
                            
                        state_db = ws_folder / 'state.vscdb'
                        if not state_db.exists():
                            continue
                        
                        # Quick check - look for composer data with sayu-related content
                        try:
                            import sqlite3
                            conn = sqlite3.connect(str(state_db))
                            cursor = conn.cursor()
                            
                            # Check composer.composerData for repo references
                            cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData' LIMIT 1")
                            result = cursor.fetchone()
                            
                            if result:
                                composer_data = str(result[0])
                                if (repo_name in composer_data or 
                                    'sayu' in composer_data.lower() or
                                    repo_path_abs in composer_data):
                                    self._workspace_db_path = state_db
                                    if os.getenv('SAYU_DEBUG'):
                                        print(f"Found matching workspace: {ws_folder.name} for {repo_name}")
                                    conn.close()
                                    break
                            
                            conn.close()
                            
                        except Exception as e:
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Error checking workspace {ws_folder.name}: {e}")
                            continue
        
        return self._db_path, self._workspace_db_path
    
    def get_conversation_paths(self) -> List[Path]:
        """Get Cursor conversation file paths"""
        # Cursor uses SQLite databases, not files
        # Return database paths for compatibility
        db_path, ws_db_path = self._get_db_paths()
        paths = []
        if db_path and db_path.exists():
            paths.append(db_path)
        if ws_db_path and ws_db_path.exists():
            paths.append(ws_db_path)
        return paths
    
    def parse_conversation_file(self, file_path: Path, start_time_ms: int = 0, end_time_ms: int = 0) -> List[Dict[str, Any]]:
        """Parse Cursor SQLite database for conversations"""
        messages = []
        
        try:
            import sqlite3
            
            # Step 1: Get composer IDs from workspace database
            if not self._composers_cache:
                self._load_composers_from_workspace()
            
            # Step 2: Parse bubbles only from global database
            # Skip if this is workspace database
            if file_path == self._workspace_db_path:
                return messages  # Return empty for workspace DB
            
            # Parse bubbles from global database using composer IDs (within time range)
            if self._composers_cache:
                conn = sqlite3.connect(str(file_path))
                cursor = conn.cursor()
                
                # Filter composers by creation/update time within the time range being queried
                # This should be called with start_time_ms and end_time_ms from pull_since
                relevant_composers = []
                for composer_id, info in self._composers_cache.items():
                    created_at = info.get('createdAt', 0)
                    updated_at = info.get('lastUpdatedAt', 0)
                    
                    # Only include composers that were created or updated after the start time
                    if created_at >= start_time_ms or updated_at >= start_time_ms:
                        relevant_composers.append(composer_id)
                        if os.getenv('SAYU_DEBUG'):
                            from datetime import datetime
                            created_time = datetime.fromtimestamp(created_at / 1000).strftime('%H:%M:%S') if created_at > 0 else 'unknown'
                            updated_time = datetime.fromtimestamp(updated_at / 1000).strftime('%H:%M:%S') if updated_at > 0 else 'unknown'
                            print(f"Including composer {composer_id} (created: {created_time}, updated: {updated_time})")
                
                if os.getenv('SAYU_DEBUG'):
                    print(f"Looking for bubbles for {len(relevant_composers)}/{len(self._composers_cache)} relevant composers")
                
                # Query bubble messages directly by composer ID pattern
                for composer_id in relevant_composers[:10]:  # Limit to avoid too many queries
                    # Find all bubbles for this composer
                    bubble_pattern = f"bubbleId:{composer_id}:%"
                    cursor.execute(
                        "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?",
                        (bubble_pattern,)
                    )
                    
                    bubble_results = cursor.fetchall()
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Found {len(bubble_results)} bubbles for composer {composer_id}")
                    
                    # Parse each bubble
                    for bubble_key, bubble_value in bubble_results:
                        try:
                            # Extract bubble ID from key: bubbleId:composerId:bubbleId
                            parts = bubble_key.split(':')
                            if len(parts) >= 3:
                                bubble_id = parts[2]
                                
                                # Parse bubble directly
                                bubble_data = json.loads(bubble_value)
                                
                                # Extract timestamp - use multiple sources
                                timestamp = bubble_data.get('tokenCountUpUntilHere', 0)
                                if timestamp == 0:
                                    timestamp = bubble_data.get('createdAt', 0)
                                if timestamp == 0:
                                    timestamp = self._composers_cache[composer_id].get('lastUpdatedAt', 0)
                                
                                # Ensure timestamp is in milliseconds
                                if timestamp > 0 and timestamp < 1e10:
                                    timestamp = int(timestamp * 1000)
                                
                                # Extract text content based on bubble type
                                bubble_type = bubble_data.get('type', 0)
                                text = bubble_data.get('text', '')
                                
                                if text and timestamp > 0:
                                    # Determine role based on type (1=user, 2=assistant)
                                    role = 'user' if bubble_type == 1 else 'assistant'
                                    
                                    # Get relevant files
                                    relevant_files = bubble_data.get('relevantFiles', [])
                                    file_path_for_message = None
                                    if relevant_files:
                                        file_path_for_message = relevant_files[0] if isinstance(relevant_files, list) else str(relevant_files)
                                    
                                    messages.append({
                                        'timestamp': timestamp,
                                        'role': role,
                                        'text': text,
                                        'file': file_path_for_message,
                                        'meta': {
                                            'bubble_id': bubble_id,
                                            'composer_id': composer_id,
                                            'composer_name': self._composers_cache[composer_id].get('name', ''),
                                            'bubble_type': bubble_type,
                                            'is_agentic': bubble_data.get('isAgentic', False)
                                        }
                                    })
                                
                        except (json.JSONDecodeError, TypeError, IndexError) as e:
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Error parsing bubble {bubble_key}: {e}")
                            continue
                
                conn.close()
            
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error parsing Cursor database {file_path}: {e}")
        
        return messages
    
    def _load_composers_from_workspace(self):
        """Load composer data from workspace database"""
        if self._workspace_db_path and self._workspace_db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(self._workspace_db_path))
                cursor = conn.cursor()
                
                cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData' LIMIT 1")
                result = cursor.fetchone()
                
                if result:
                    composer_data = json.loads(result[0])
                    self._composers_cache = {}
                    
                    for composer in composer_data.get('allComposers', []):
                        composer_id = composer.get('composerId')
                        if composer_id:
                            self._composers_cache[composer_id] = {
                                'name': composer.get('name', ''),
                                'createdAt': composer.get('createdAt', 0),
                                'lastUpdatedAt': composer.get('lastUpdatedAt', 0)
                            }
                            
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Loaded composer: {composer_id} - {composer.get('name', '')}")
                
                conn.close()
                
            except Exception as e:
                if os.getenv('SAYU_DEBUG'):
                    print(f"Error loading composers from workspace: {e}")
    
    def _parse_bubble(self, cursor, bubble_id: str, composer_id: str) -> List[Dict[str, Any]]:
        """Parse a single bubble for messages"""
        messages = []
        
        # Query patterns for bubble data (based on actual structure)
        patterns = [
            f"bubbleId:{composer_id}:{bubble_id}",  # Most common pattern
            f"bubbleId:{bubble_id}:{composer_id}",
            f"bubbleId:{bubble_id}"
        ]
        
        for pattern in patterns:
            cursor.execute(
                "SELECT value FROM cursorDiskKV WHERE key = ?",
                (pattern,)
            )
            result = cursor.fetchone()
            
            if result:
                try:
                    bubble_data = json.loads(result[0])
                    
                    # Extract timestamp - use multiple sources
                    timestamp = bubble_data.get('tokenCountUpUntilHere', 0)
                    if timestamp == 0:
                        timestamp = bubble_data.get('createdAt', 0)
                    if timestamp == 0 and self._composers_cache and composer_id in self._composers_cache:
                        # Use composer creation time as fallback
                        timestamp = self._composers_cache[composer_id].get('lastUpdatedAt', 0)
                    
                    # Ensure timestamp is in milliseconds
                    if timestamp > 0 and timestamp < 1e10:
                        timestamp = int(timestamp * 1000)
                    
                    # Extract text content based on bubble type
                    bubble_type = bubble_data.get('type', 0)
                    text = bubble_data.get('text', '')
                    
                    if text and timestamp > 0:
                        # Determine role based on type (1=user, 2=assistant)
                        role = 'user' if bubble_type == 1 else 'assistant'
                        
                        # Get relevant files
                        relevant_files = bubble_data.get('relevantFiles', [])
                        file_path = None
                        if relevant_files:
                            file_path = relevant_files[0] if isinstance(relevant_files, list) else str(relevant_files)
                        
                        messages.append({
                            'timestamp': timestamp,
                            'role': role,
                            'text': text,
                            'file': file_path,
                            'meta': {
                                'bubble_id': bubble_id,
                                'composer_id': composer_id,
                                'composer_name': self._composers_cache.get(composer_id, {}).get('name', '') if self._composers_cache else '',
                                'bubble_type': bubble_type,
                                'is_agentic': bubble_data.get('isAgentic', False)
                            }
                        })
                    
                except (json.JSONDecodeError, TypeError) as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error parsing bubble {bubble_id}: {e}")
                    continue
                
                break
        
        return messages
