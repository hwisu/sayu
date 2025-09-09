"""
Claude Desktop conversation collector

Extracts conversation data from Claude Desktop's project files stored in ~/.claude/projects/
"""

import os
import json
import uuid
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.events.types import Event, EventSource, EventKind, Actor


class ClaudeCollector:
    """Collector for Claude Desktop conversation data"""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.claude_projects_path = Path.home() / '.claude' / 'projects'
    
    def discover(self) -> Dict[str, Any]:
        """Discover Claude projects and conversation files"""
        discovery_info = {
            'projects_path': str(self.claude_projects_path),
            'projects': [],
            'total_conversations': 0,
            'accessible': False
        }
        
        if not self.claude_projects_path.exists():
            discovery_info['error'] = 'Claude projects directory not found'
            return discovery_info
        
        try:
            projects = list(self.claude_projects_path.iterdir())
            discovery_info['accessible'] = True
            
            for project_dir in projects:
                if project_dir.is_dir():
                    jsonl_files = list(project_dir.glob('*.jsonl'))
                    project_info = {
                        'name': project_dir.name,
                        'path': str(project_dir),
                        'conversation_files': len(jsonl_files),
                        'total_size': sum(f.stat().st_size for f in jsonl_files)
                    }
                    discovery_info['projects'].append(project_info)
                    discovery_info['total_conversations'] += len(jsonl_files)
        
        except Exception as e:
            discovery_info['error'] = str(e)
        
        return discovery_info
    
    def pull_since(
        self, since_ms: int, until_ms: int, config: Optional[Dict[str, Any]] = None
    ) -> List[Event]:
        """Pull Claude conversation events within time range"""
        events = []
        
        if not self.claude_projects_path.exists():
            if os.getenv('SAYU_DEBUG'):
                print("Claude projects directory not found")
            return events
        
        try:
            # Scan all project directories
            for project_dir in self.claude_projects_path.iterdir():
                if project_dir.is_dir():
                    project_events = self._extract_from_project(
                        project_dir, since_ms, until_ms
                    )
                    events.extend(project_events)
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error scanning Claude projects: {e}")
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.ts)
        
        if os.getenv('SAYU_DEBUG'):
            print(f"Claude collector found {len(events)} events")
        
        return events
    
    def _extract_from_project(
        self, project_path: Path, since_ms: int, until_ms: int
    ) -> List[Event]:
        """Extract conversation events from a Claude project directory"""
        events = []
        
        try:
            # Find all JSONL files in project
            jsonl_files = list(project_path.glob('*.jsonl'))
            
            for jsonl_file in jsonl_files:
                file_events = self._parse_jsonl_file(jsonl_file, since_ms, until_ms)
                events.extend(file_events)
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error processing Claude project {project_path.name}: {e}")
        
        return events
    
    def _parse_jsonl_file(
        self, jsonl_file: Path, since_ms: int, until_ms: int
    ) -> List[Event]:
        """Parse a Claude JSONL conversation file"""
        events = []
        
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    if isinstance(data, dict):
                        event = self._create_event_from_message(data, jsonl_file.name)
                        
                        if event and since_ms <= event.ts <= until_ms:
                            events.append(event)
                
                except json.JSONDecodeError as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"JSON parse error in {jsonl_file.name} line {line_num}: {e}")
                    continue
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error processing line {line_num} in {jsonl_file.name}: {e}")
                    continue
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error reading JSONL file {jsonl_file}: {e}")
        
        return events
    
    def _create_event_from_message(
        self, data: Dict[str, Any], filename: str
    ) -> Optional[Event]:
        """Create Event from Claude message data"""
        try:
            # Extract timestamp (ISO format)
            timestamp = data.get('timestamp')
            if not timestamp:
                return None
            
            # Parse ISO timestamp to milliseconds
            timestamp_ms = self._parse_iso_timestamp(timestamp)
            if not timestamp_ms:
                return None
            
            # Extract message type and content
            msg_type = data.get('type', 'unknown')
            message_content = data.get('message', {})
            
            # Extract text content from message structure
            text_content = self._extract_text_content(message_content)
            if not text_content or len(text_content.strip()) < 5:
                return None
            
            # Determine actor based on type
            actor = Actor.USER if msg_type == 'user' else Actor.ASSISTANT
            
            # Extract session and UUID info
            session_id = data.get('sessionId', '')
            message_uuid = data.get('uuid', '')
            
            # Extract project context
            cwd = data.get('cwd', '')
            git_branch = data.get('gitBranch', '')
            
            # Determine the actual repository from cwd
            # Only use conversations from valid git repos
            actual_repo = self._determine_repo_from_cwd(cwd)
            if not actual_repo:
                # Skip conversations not in a git repository
                if os.getenv('SAYU_DEBUG'):
                    print(f"Skipping conversation - no valid git repo found for cwd: {cwd}")
                return None
            
            # Create event
            event = Event(
                id=str(uuid.uuid4()),
                ts=timestamp_ms,
                source=EventSource.LLM,
                kind=EventKind.CHAT,
                repo=actual_repo,
                cwd=cwd or actual_repo,
                file=None,
                range=None,
                actor=actor,
                text=text_content[:2000],  # Limit text length
                url=None,
                meta={
                    'tool': 'claude',
                    'type': msg_type,
                    'sessionId': session_id,
                    'messageUuid': message_uuid,
                    'filename': filename,
                    'gitBranch': git_branch,
                    'source_table': 'claude_jsonl'
                }
            )
            
            return event
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error creating event from Claude message: {e}")
            return None
    
    def _parse_iso_timestamp(self, timestamp: str) -> Optional[int]:
        """Parse ISO timestamp to milliseconds"""
        try:
            if isinstance(timestamp, str):
                # Handle ISO format like "2025-09-05T04:20:06.640Z"
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return int(dt.timestamp() * 1000)
            elif isinstance(timestamp, (int, float)):
                # Handle numeric timestamp
                return int(timestamp) if timestamp > 1000000000000 else int(timestamp * 1000)
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Timestamp parsing error: {e}")
        
        return None
    
    def _determine_repo_from_cwd(self, cwd: str) -> str:
        """Determine repository root from working directory"""
        if not cwd:
            return None  # Return None instead of self.repo_root
        
        # Try to find git root from cwd
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            repo_path = result.stdout.strip()
            
            # Only return the repo if it exists and is a directory
            if repo_path and os.path.isdir(repo_path):
                return repo_path
            return None
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            # If not a git repo, git not found, or cwd doesn't exist
            # Return None to indicate this conversation is not from a git repo
            return None
    
    def _extract_text_content(self, message_data: Dict[str, Any]) -> str:
        """Extract text content from Claude message structure"""
        if not isinstance(message_data, dict):
            return ""
        
        # Get content array
        content = message_data.get('content', [])
        if not isinstance(content, list):
            return ""
        
        # Extract text from content items
        text_parts = []
        
        for item in content:
            if isinstance(item, dict):
                item_type = item.get('type', '')
                
                if item_type == 'text':
                    # Regular text content
                    text = item.get('text', '')
                    if text:
                        text_parts.append(text)
                
                elif item_type == 'tool_use':
                    # Tool usage - include tool name and brief description
                    tool_name = item.get('name', 'unknown_tool')
                    tool_input = item.get('input', {})
                    
                    if isinstance(tool_input, dict) and tool_input:
                        # Extract meaningful info from tool input
                        if 'command' in tool_input:
                            text_parts.append(f"[Tool: {tool_name}] {tool_input['command']}")
                        elif 'pattern' in tool_input:
                            text_parts.append(f"[Tool: {tool_name}] pattern: {tool_input['pattern']}")
                        else:
                            text_parts.append(f"[Tool: {tool_name}] used")
                    else:
                        text_parts.append(f"[Tool: {tool_name}] used")
                
                elif item_type == 'tool_result':
                    # Tool result - include brief content
                    tool_id = item.get('tool_use_id', 'unknown')
                    result_content = item.get('content', '')
                    
                    if isinstance(result_content, str) and result_content:
                        # Limit tool result content length
                        limited_content = result_content[:200] + '...' if len(result_content) > 200 else result_content
                        text_parts.append(f"[Tool Result] {limited_content}")
        
        return ' '.join(text_parts)
    
    def health(self) -> Dict[str, Any]:
        """Check Claude collector health and accessibility"""
        health_info = {
            'ok': False,
            'reason': '',
            'projects': 0,
            'conversations': 0
        }
        
        try:
            if not self.claude_projects_path.exists():
                health_info['reason'] = 'Claude projects directory not found'
                return health_info
            
            projects = list(self.claude_projects_path.iterdir())
            project_dirs = [p for p in projects if p.is_dir()]
            
            total_conversations = 0
            for project_dir in project_dirs:
                jsonl_files = list(project_dir.glob('*.jsonl'))
                total_conversations += len(jsonl_files)
            
            health_info.update({
                'ok': True,
                'projects': len(project_dirs),
                'conversations': total_conversations
            })
        
        except Exception as e:
            health_info['reason'] = f'Error accessing Claude data: {e}'
        
        return health_info
    
    def redact(self, event: Event) -> Event:
        """Redact sensitive information from Claude event"""
        # Create copy of event with redacted sensitive data
        redacted_text = event.text
        
        # Redact patterns that might contain sensitive info
        import re
        
        # Redact file paths (keep only filename)
        redacted_text = re.sub(r'/[^/\s]+(/[^/\s]+)+/([^/\s]+)', r'***/\2', redacted_text)
        
        # Redact API keys and tokens
        redacted_text = re.sub(r'["\']?[a-zA-Z0-9_-]*api[_-]?key[_-]?["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+["\']?', 
                              'api_key: ***', redacted_text, flags=re.IGNORECASE)
        
        # Redact email addresses
        redacted_text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                              '***@***.***', redacted_text)
        
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
            text=redacted_text,
            url=event.url,
            meta=event.meta
        )
