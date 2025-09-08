"""Collector manager for coordinating all event collectors"""

import os
from typing import List, Optional

from domain.events.types import Event, Config
from domain.events.store_manager import StoreManager
from infra.config.manager import ConfigManager
from domain.git.hooks import GitHookManager
from .git import GitCollector
from .cli import CliCollector
from .cursor import CursorCollector
from .claude import ClaudeCollector


class CollectorManager:
    """Manage all event collectors"""
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize collector manager"""
        self.repo_root = repo_root or GitHookManager.get_repo_root() or os.getcwd()
        self.store = StoreManager.get_store()
        
        # Load configuration
        config_manager = ConfigManager(self.repo_root)
        self.config = config_manager.get()
        
        # Initialize collectors
        self.git_collector = GitCollector(self.repo_root)
        self.cli_collector = CliCollector(self.repo_root)
        self.cursor_collector = CursorCollector(self.repo_root)
        self.claude_collector = ClaudeCollector(self.repo_root)
        
    
    def collect_current_commit(self) -> List[Event]:
        """Collect events for currently staged changes"""
        events = []
        
        # Get current commit context
        git_context = self.git_collector.get_current_commit_context()
        
        # Store diff information if available
        if git_context['diff']:
            from domain.events.types import Event, EventSource, EventKind, Actor
            import uuid
            import time
            
            diff_event = Event(
                id=str(uuid.uuid4()),
                ts=int(time.time() * 1000),
                source=EventSource.GIT,
                kind=EventKind.COMMIT,
                repo=self.repo_root,
                cwd=self.repo_root,
                file=None,
                range=None,
                actor=Actor.USER,
                text=git_context['diff'][:1000],  # Only first 1000 characters
                url=None,
                meta={
                    'type': 'diff',
                    'full_length': len(git_context['diff']),
                    'files': ','.join(git_context['files'])
                }
            )
            
            events.append(diff_event)
            self.store.insert(diff_event)
        
        return events
    
    def collect_since_last_commit(self) -> List[Event]:
        """Collect events since last commit (or last 24 hours as fallback)"""
        import time
        
        now_ms = int(time.time() * 1000)
        
        # Always use last commit time first, then fallback to 24 hours  
        last_commit_time = self.store.get_last_commit_time(self.repo_root)
        if last_commit_time:
            start_time = last_commit_time
            if os.getenv('SAYU_DEBUG'):
                from datetime import datetime
                dt = datetime.fromtimestamp(last_commit_time / 1000)
                print(f"Using last commit time: {dt.strftime('%m-%d %H:%M:%S')}")
        else:
            # Fallback to 24 hours if no commits found
            start_time = now_ms - (24 * 60 * 60 * 1000)
            if os.getenv('SAYU_DEBUG'):
                print("No commit history found, using 24 hours fallback")
        
        all_events = []
        
        # Collect Git events
        try:
            git_events = self.git_collector.pull_since(start_time, now_ms, self.config)
            all_events.extend(git_events)
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Git collector error: {e}")

        # Collect CLI events (if enabled)
        if self.config.connectors.get('cli', {}).get('mode') != 'off':
            try:
                cli_events = self.cli_collector.pull_since(start_time, now_ms, self.config)
                all_events.extend(cli_events)
            except Exception as e:
                if os.getenv('SAYU_DEBUG'):
                    print(f"CLI collector error: {e}")
        
        # Collect Cursor events (if enabled)
        cursor_enabled = self.config.connectors.get('cursor', False)
        if os.getenv('SAYU_DEBUG'):
            print(f"Cursor enabled: {cursor_enabled}")

        if cursor_enabled:
            try:
                if os.getenv('SAYU_DEBUG'):
                    print(f"Cursor time range: {start_time} to {now_ms}")
                cursor_events = self.cursor_collector.pull_since(start_time, now_ms, self.config)
                if os.getenv('SAYU_DEBUG'):
                    print(f"Cursor events collected: {len(cursor_events)}")
                    if cursor_events:
                        print(f"Sample Cursor event: {cursor_events[0].text[:50]}")
                all_events.extend(cursor_events)
            except Exception as e:
                if os.getenv('SAYU_DEBUG'):
                    print(f"Cursor collector error: {e}")
                    import traceback
                    traceback.print_exc()

        # Collect Claude events (if enabled)
        claude_enabled = self.config.connectors.get('claude', False)
        if os.getenv('SAYU_DEBUG'):
            print(f"Claude enabled: {claude_enabled}")

        if claude_enabled:
            try:
                if os.getenv('SAYU_DEBUG'):
                    print(f"Claude time range: {start_time} to {now_ms}")
                claude_events = self.claude_collector.pull_since(start_time, now_ms, self.config)
                if os.getenv('SAYU_DEBUG'):
                    print(f"Claude events collected: {len(claude_events)}")
                    if claude_events:
                        print(f"Sample Claude event: {claude_events[0].text[:50]}")
                all_events.extend(claude_events)
            except Exception as e:
                if os.getenv('SAYU_DEBUG'):
                    print(f"Claude collector error: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Store events in database
        if all_events:
            self.store.insert_batch(all_events)

        # Query all events within time window from DB (sorted by time)
        return self.store.find_by_repo(self.repo_root, start_time, now_ms)

    def health_check(self) -> dict:
        """Check health of all collectors"""
        health = {
            'git': self.git_collector.health(),
            'cli': self.cli_collector.health(),
            'cursor': self.cursor_collector.health(),
            'claude': self.claude_collector.health()
        }
        
        return health
    
    def close(self):
        """Close collector manager and cleanup"""
        # No explicit cleanup needed for current collectors
        pass
