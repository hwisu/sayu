"""Collector manager for coordinating all event collectors"""

import os
from typing import List, Optional

from domain.events.types import Event, Config
from domain.events.store_manager import StoreManager
from infra.config.manager import ConfigManager
from domain.git.hooks import GitHookManager
from .git import GitCollector
from .cli import CliCollector


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
        
        # TODO: Add LLM collectors when implemented
        # self.claude_collector = ClaudeCollector(self.repo_root)
        # self.cursor_collector = CursorCollector(self.repo_root)
    
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
    
    def collect_in_time_window(self, hours: int = 168) -> List[Event]:
        """Collect events within time window (default: 1 week)"""
        import time
        
        now_ms = int(time.time() * 1000)
        since_ms = now_ms - (hours * 60 * 60 * 1000)
        
        # Check last commit time to optimize collection
        last_commit_time = self.store.get_last_commit_time(self.repo_root)
        start_time = last_commit_time or since_ms
        
        all_events = []
        
        # Collect Git events
        try:
            git_events = self.git_collector.pull_since(start_time, now_ms, self.config)
            all_events.extend(git_events)
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Git collector error: {e}")
        
        # Collect CLI events (if enabled)
        if hasattr(self.config.connectors, 'cli') and self.config.connectors.cli.get('mode') != 'off':
            try:
                cli_events = self.cli_collector.pull_since(start_time, now_ms, self.config)
                all_events.extend(cli_events)
            except Exception as e:
                if os.getenv('SAYU_DEBUG'):
                    print(f"CLI collector error: {e}")
        
        # TODO: Collect LLM events when collectors are implemented
        # if self.config.connectors.claude:
        #     try:
        #         claude_events = self.claude_collector.pull_since(start_time, now_ms, self.config)
        #         all_events.extend(claude_events)
        #     except Exception as e:
        #         if os.getenv('SAYU_DEBUG'):
        #             print(f"Claude collector error: {e}")
        
        # Store events in database
        if all_events:
            self.store.insert_batch(all_events)
        
        # Query all events within time window from DB (sorted by time)
        return self.store.find_by_repo(self.repo_root, start_time, now_ms)
    
    def health_check(self) -> dict:
        """Check health of all collectors"""
        health = {
            'git': self.git_collector.health(),
            'cli': self.cli_collector.health()
        }
        
        # TODO: Add LLM collector health checks
        # health['claude'] = self.claude_collector.health()
        # health['cursor'] = self.cursor_collector.health()
        
        return health
    
    def close(self):
        """Close collector manager and cleanup"""
        # No explicit cleanup needed for current collectors
        pass
