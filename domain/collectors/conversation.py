"""Base conversation collector for Claude and Cursor"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from domain.events.types import Event, EventSource, EventKind, Actor


class ConversationCollector(ABC):
    """Base class for conversation-based collectors (Claude, Cursor, etc.)"""
    
    def __init__(self, repo_root: str):
        """Initialize collector with repository root"""
        self.repo_root = repo_root
    
    @abstractmethod
    def get_event_source(self) -> EventSource:
        """Get the event source type"""
        pass
    
    @abstractmethod
    def get_conversation_paths(self) -> List[Path]:
        """Get paths to conversation files"""
        pass
    
    @abstractmethod
    def parse_conversation_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a conversation file and return list of messages"""
        pass
    
    def pull_since(self, start_time_ms: int, end_time_ms: int, config: Any) -> List[Event]:
        """Pull events from conversation files within time range"""
        events = []
        
        try:
            for conv_path in self.get_conversation_paths():
                if not conv_path.exists():
                    continue
                
                # Check if file was modified within time range
                file_mtime = int(conv_path.stat().st_mtime * 1000)
                if file_mtime < start_time_ms:
                    continue
                
                try:
                    messages = self.parse_conversation_file(conv_path)
                    
                    # Convert messages to events
                    for msg in messages:
                        if start_time_ms <= msg['timestamp'] <= end_time_ms:
                            event = self._create_event(msg)
                            if event:
                                events.append(event)
                
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error parsing {conv_path}: {e}")
                    continue
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"{self.get_event_source().value} collector error: {e}")
        
        return events
    
    def _create_event(self, message: Dict[str, Any]) -> Optional[Event]:
        """Create event from message data"""
        import uuid
        
        # Skip system messages
        if message.get('role') == 'system':
            return None
        
        # Map role to actor
        actor = Actor.USER if message.get('role') == 'user' else Actor.ASSISTANT
        
        # Extract text content
        text = message.get('text', '')
        if not text and isinstance(message.get('content'), list):
            # Handle structured content
            text_parts = []
            for item in message['content']:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            text = '\n'.join(text_parts)
        
        if not text:
            return None
        
        return Event(
            ts=message['timestamp'],
            source=self.get_event_source(),
            kind=EventKind.CONVERSATION,
            repo=self.repo_root,
            text=text[:5000],  # Limit text length
            cwd=self.repo_root,
            file=message.get('file'),
            actor=actor,
            meta=message.get('meta', {})
        )
    
    def health(self) -> dict:
        """Check collector health"""
        paths = self.get_conversation_paths()
        accessible = sum(1 for p in paths if p.exists())
        
        return {
            'ok': accessible > 0,
            'reason': f"Found {accessible}/{len(paths)} conversation files",
            'conversations': accessible
        }


class ClaudeConversationCollector(ConversationCollector):
    """Collector for Claude Desktop conversations"""
    
    def get_event_source(self) -> EventSource:
        return EventSource.CLAUDE
    
    def get_conversation_paths(self) -> List[Path]:
        """Get Claude conversation file paths"""
        claude_projects = Path.home() / '.claude' / 'projects'
        if not claude_projects.exists():
            return []
        
        # Find conversation files that might be related to this repo
        conversation_files = []
        
        # Check direct project folder
        repo_name = Path(self.repo_root).name
        project_path = claude_projects / repo_name / 'conversations' / 'default.jsonl'
        if project_path.exists():
            conversation_files.append(project_path)
        
        # Also check for any JSONL files in the projects directory
        for jsonl_file in claude_projects.rglob('*.jsonl'):
            if jsonl_file not in conversation_files:
                conversation_files.append(jsonl_file)
        
        return conversation_files
    
    def parse_conversation_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse Claude JSONL conversation file"""
        messages = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Extract message data
                    if 'message' in entry:
                        msg_data = entry['message']
                        timestamp = entry.get('timestamp', 0)
                        
                        # Convert timestamp if needed
                        if isinstance(timestamp, str):
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            timestamp = int(dt.timestamp() * 1000)
                        elif timestamp < 1e10:  # Likely in seconds
                            timestamp = int(timestamp * 1000)
                        
                        messages.append({
                            'timestamp': timestamp,
                            'role': msg_data.get('role', 'user'),
                            'text': msg_data.get('content', ''),
                            'content': msg_data.get('content'),
                            'meta': {
                                'conversation_id': entry.get('conversation_id'),
                                'message_id': entry.get('id')
                            }
                        })
                
                except json.JSONDecodeError:
                    continue
        
        return messages


class CursorConversationCollector(ConversationCollector):
    """Collector for Cursor editor conversations"""
    
    def get_event_source(self) -> EventSource:
        return EventSource.CURSOR
    
    def get_conversation_paths(self) -> List[Path]:
        """Get Cursor conversation file paths"""
        # Cursor doesn't persist conversation history in accessible files
        # Return empty list for now
        return []
    
    def parse_conversation_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse Cursor conversation file"""
        messages = []
        
        try:
            # Try to parse as JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Handle different Cursor file formats
                if isinstance(data, dict) and 'messages' in data:
                    # Standard format with messages array
                    for msg in data['messages']:
                        timestamp = msg.get('timestamp', 0)
                        if timestamp < 1e10:  # Convert to milliseconds if needed
                            timestamp = int(timestamp * 1000)
                        
                        messages.append({
                            'timestamp': timestamp,
                            'role': msg.get('role', 'user'),
                            'text': msg.get('content', ''),
                            'content': msg.get('content'),
                            'file': msg.get('file'),
                            'meta': {
                                'conversation_id': data.get('id'),
                                'message_id': msg.get('id')
                            }
                        })
                
                elif isinstance(data, list):
                    # Direct array of messages
                    for msg in data:
                        if isinstance(msg, dict):
                            timestamp = msg.get('timestamp', 0)
                            if timestamp < 1e10:
                                timestamp = int(timestamp * 1000)
                            
                            messages.append({
                                'timestamp': timestamp,
                                'role': msg.get('role', 'user'),
                                'text': msg.get('content', ''),
                                'content': msg.get('content'),
                                'file': msg.get('file'),
                                'meta': {'message_id': msg.get('id')}
                            })
        
        except json.JSONDecodeError:
            # Try JSONL format
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        msg = json.loads(line)
                        timestamp = msg.get('timestamp', 0)
                        if timestamp < 1e10:
                            timestamp = int(timestamp * 1000)
                        
                        messages.append({
                            'timestamp': timestamp,
                            'role': msg.get('role', 'user'),
                            'text': msg.get('content', ''),
                            'content': msg.get('content'),
                            'file': msg.get('file'),
                            'meta': {'message_id': msg.get('id')}
                        })
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error parsing Cursor file {file_path}: {e}")
        
        return messages