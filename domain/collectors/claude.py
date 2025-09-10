"""Claude Desktop conversation collector"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

from domain.events.types import EventSource
from .conversation_base import ConversationCollector


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
        
        # Claude uses escaped paths as folder names  
        # e.g., /Users/hwisookim/sayu becomes -Users-hwisookim-sayu
        repo_path_abs = os.path.abspath(self.repo_root)
        escaped_path = repo_path_abs.replace('/', '-')
        # Keep the leading dash for Claude project folder naming convention
        
        project_folder = claude_projects / escaped_path
        if project_folder.exists():
            # Get all JSONL files in this project folder
            conversation_files.extend(project_folder.glob('*.jsonl'))
            if os.getenv('SAYU_DEBUG'):
                print(f"Found Claude project folder: {project_folder}")
                print(f"JSONL files: {len(conversation_files)}")
        else:
            if os.getenv('SAYU_DEBUG'):
                print(f"Claude project folder not found: {project_folder}")
                # List available project folders for debugging
                if claude_projects.exists():
                    available = [f.name for f in claude_projects.iterdir() if f.is_dir()]
                    print(f"Available projects: {available[:5]}")  # Show first 5
        
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
