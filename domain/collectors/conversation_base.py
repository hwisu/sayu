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
                    # Pass time range to parse_conversation_file for better filtering
                    if hasattr(self, 'parse_conversation_file') and 'start_time_ms' in self.parse_conversation_file.__code__.co_varnames:
                        messages = self.parse_conversation_file(conv_path, start_time_ms, end_time_ms)
                    else:
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
        """Create event from message data - STRICT TOOL FILTERING"""
        import uuid
        
        # STRICT: Skip system messages
        if message.get('role') == 'system':
            return None
        
        # STRICT: Only allow user/assistant roles
        if message.get('role') not in ['user', 'assistant']:
            return None
        
        # STRICT: Check for tool-related roles first
        if message.get('role') in ['tool', 'function', 'tool_use', 'tool_result']:
            return None
        
        # Map role to actor
        actor = Actor.USER if message.get('role') == 'user' else Actor.ASSISTANT
        
        # Extract text content and STRICT tool filtering
        text = message.get('text', '')
        content = message.get('content', '')
        
        # Handle structured content (Claude format) with STRICT tool filtering
        if not text and isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    # STRICT: Skip ALL tool-related types
                    if item.get('type') in ['tool_use', 'tool_result', 'function_call', 'function_result', 'tool_call', 'tool_response']:
                        continue
                    # STRICT: Only include pure text content
                    if item.get('type') == 'text':
                        text_content = item.get('text', '')
                        # Additional tool content check
                        if not self._is_tool_related_content(text_content):
                            text_parts.append(text_content)
            text = '\n'.join(text_parts)
        elif not text and isinstance(content, str):
            # STRICT: Check string content for tool usage
            if not self._is_tool_related_content(content):
                text = content
        elif not text and content:
            # Handle other content types safely
            text = str(content)
        
        # STRICT: Final tool-related content filtering
        if text and self._is_tool_related_content(text):
            return None
        
        # STRICT: Minimum meaningful content length
        if not text or len(text.strip()) < 3:
            return None
        
        # STRICT: Check for tool-related keywords in final text
        tool_keywords = ['tool_use_id', 'function_calls', '<invoke>', 'antml:parameter', 'tool_result']
        if any(keyword in text.lower() for keyword in tool_keywords):
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
    
    def _is_tool_related_content(self, text) -> bool:
        """Check if text content is related to tool usage"""
        if not text:
            return False
        
        # Handle list content (from Claude's structured format)
        if isinstance(text, list):
            # Check each item in the list
            for item in text:
                if isinstance(item, dict):
                    # Skip tool-related items
                    if item.get('type') in ['tool_use', 'tool_result', 'function_call']:
                        return True
                    # Check text content in the item
                    if item.get('type') == 'text':
                        item_text = item.get('text', '')
                        if self._is_tool_related_content(item_text):
                            return True
                elif isinstance(item, str):
                    if self._is_tool_related_content(item):
                        return True
            return False
        
        # Ensure text is a string for the rest of the checks
        if not isinstance(text, str):
            text = str(text)
        
        # Tool-related patterns
        tool_patterns = [
            'tool_use_id', 'function_calls', '<invoke>', 'antml:parameter',
            'tool_result', 'tool_use', 'function_call', 'tool_call', 'tool_response',
            'invoke name=', 'parameter name=', 'tool_call_id', 'function_result',
            'tool_choice', 'tool_usage', 'function_definition', 'tool_definition'
        ]
        
        text_lower = text.lower()
        
        # Check for tool patterns
        for pattern in tool_patterns:
            if pattern in text_lower:
                return True
        
        # Check for JSON-like tool data
        if '{' in text and '}' in text:
            # High density of brackets might indicate tool data
            bracket_count = text.count('{') + text.count('}')
            if bracket_count > len(text) / 20:  # More than 5% brackets
                return True
        
        # Check for XML-like tool tags
        if '<' in text and '>' in text:
            xml_tags = ['<invoke', '<parameter', '<tool', '<function']
            if any(tag in text_lower for tag in xml_tags):
                return True
        
        # Skip very short messages (likely tool artifacts)
        if len(text.strip()) < 10:
            return True
        
        return False
    
    def health(self) -> dict:
        """Check collector health"""
        paths = self.get_conversation_paths()
        accessible = sum(1 for p in paths if p.exists())
        
        return {
            'ok': accessible > 0,
            'reason': f"Found {accessible}/{len(paths)} conversation files",
            'conversations': accessible
        }
