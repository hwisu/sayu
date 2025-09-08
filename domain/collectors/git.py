"""Git collector for repository events"""

import json
import os
import subprocess
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from domain.events.types import Event, EventSource, EventKind, Actor, Config, Connector
from infra.shell.executor import ShellExecutor


class GitCollector:
    """Collect Git repository events"""
    
    id = 'git.core'
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize Git collector"""
        self.repo_root = repo_root or os.getcwd()
    
    def discover(self, repo_root: str) -> bool:
        """Check if this is a git repository"""
        try:
            result = ShellExecutor.git_exec(
                ['rev-parse', '--git-dir'], 
                cwd=repo_root, 
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def pull_since(self, since_ms: int, until_ms: int, cfg: Config) -> List[Event]:
        """Pull git events within time range"""
        events = []
        
        try:
            # Convert timestamps to ISO format
            since_date = datetime.fromtimestamp(since_ms / 1000).isoformat()
            until_date = datetime.fromtimestamp(until_ms / 1000).isoformat()
            
            # Get commits in time range
            result = ShellExecutor.git_exec([
                'log',
                '--since', since_date,
                '--until', until_date,
                '--no-merges',
                '--format=%H|%s|%an|%ae|%at|%P'
            ], cwd=self.repo_root, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 5:
                            commit_hash = parts[0]
                            message = parts[1]
                            author = parts[2]
                            email = parts[3]
                            timestamp = int(parts[4]) * 1000  # Convert to milliseconds
                            parents = parts[5] if len(parts) > 5 else ''
                            
                            event = Event(
                                id=str(uuid.uuid4()),
                                ts=timestamp,
                                source=EventSource.GIT,
                                kind=EventKind.COMMIT,
                                repo=self.repo_root,
                                cwd=self.repo_root,
                                file=None,
                                range=None,
                                actor=Actor.USER,
                                text=message,
                                url=None,
                                meta={
                                    'hash': commit_hash,
                                    'author': author,
                                    'email': email,
                                    'parents': parents.split() if parents else []
                                }
                            )
                            
                            events.append(event)
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"GitCollector error: {e}")
        
        return events
    
    def health(self) -> Dict[str, Any]:
        """Health check for git collector"""
        try:
            if self.discover(self.repo_root):
                return {'ok': True}
            else:
                return {'ok': False, 'reason': 'Not a git repository'}
        except Exception as e:
            return {'ok': False, 'reason': str(e)}
    
    def redact(self, event: Event, cfg: Config) -> Event:
        """Redact sensitive information from git event"""
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
    
    def get_current_commit_context(self) -> Dict[str, Any]:
        """Get current commit context (staged files and diff)"""
        try:
            # Get staged files
            result = ShellExecutor.git_exec(
                ['diff', '--cached', '--name-only'], 
                cwd=self.repo_root,
                check=False
            )
            
            staged_files = []
            if result.returncode == 0 and result.stdout.strip():
                staged_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            
            # Get diff
            diff = ''
            if staged_files:
                diff_result = ShellExecutor.git_exec(
                    ['diff', '--cached'], 
                    cwd=self.repo_root,
                    check=False
                )
                if diff_result.returncode == 0:
                    diff = diff_result.stdout
            
            return {
                'files': staged_files,
                'diff': diff
            }
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error getting commit context: {e}")
            return {
                'files': [],
                'diff': ''
            }
    
    def get_last_commit(self) -> Optional[Dict[str, Any]]:
        """Get last commit information"""
        try:
            result = ShellExecutor.git_exec(
                ['log', '-1', '--format=%H|%s|%at'], 
                cwd=self.repo_root,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    return {
                        'hash': parts[0],
                        'message': parts[1],
                        'timestamp': int(parts[2]) * 1000  # Convert to milliseconds
                    }
        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error getting last commit: {e}")
        
        return None
    
    def _parse_file_changes(self, diff: str) -> List[Dict[str, Any]]:
        """Parse git diff to extract file changes"""
        changes = []
        
        lines = diff.split('\n')
        for line in lines:
            # Parse status lines like "A\tfile.py" or "M\tfile.py"
            if '\t' in line and len(line.split('\t')) >= 2:
                parts = line.split('\t')
                status = parts[0]
                filename = parts[1]
                
                changes.append({
                    'file': filename,
                    'status': self._map_status(status)
                })
        
        return changes
    
    def _map_status(self, git_status: str) -> str:
        """Map git status characters to readable names"""
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied'
        }
        return status_map.get(git_status, git_status.lower())
