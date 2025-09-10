"""Collector manager for coordinating all event collectors"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Any

from domain.events.store_manager import StoreManager
from infra.config.manager import ConfigManager
from infra.cache.manager import CacheManager, CollectorCache
from domain.git.hooks import GitHookManager
from domain.events.types import Event
from .git import GitCollector
from .cli import CliCollector
from .claude import ClaudeConversationCollector
from .cursor import CursorConversationCollector


class CollectorManager:
    """Manage all event collectors"""
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize collector manager"""
        self.repo_root = repo_root or GitHookManager.get_repo_root() or os.getcwd()
        self.store = StoreManager.get_store()
        
        # Load configuration
        config_manager = ConfigManager(self.repo_root)
        self.config = config_manager.get()
        
        # Initialize cache
        cache_manager = CacheManager(self.repo_root)
        self.cache = CollectorCache(cache_manager)
        
        # Initialize collectors
        self.git_collector = GitCollector(self.repo_root)
        self.cli_collector = CliCollector(self.repo_root)
        self.cursor_collector = CursorConversationCollector(self.repo_root)
        self.claude_collector = ClaudeConversationCollector(self.repo_root)
        
    
    def collect_current_commit(self) -> List[Event]:
        """Collect events for currently staged changes"""
        events = []
        
        # Get current commit context with file diffs
        git_context = self.git_collector.get_current_commit_context()
        
        # Store diff information if available
        if git_context['diff']:
            from domain.events.types import EventSource, EventKind, Actor
            import uuid
            import time
            
            # Create event for overall diff stats
            diff_event = Event(
                ts=int(time.time() * 1000),
                source=EventSource.GIT,
                kind=EventKind.DIFF,
                repo=self.repo_root,
                text=git_context['diff'][:1000],  # Only first 1000 characters
                cwd=self.repo_root,
                actor=Actor.USER,
                meta={
                    'type': 'diff_summary',
                    'full_length': len(git_context['diff']),
                    'files': git_context['files']
                }
            )
            
            events.append(diff_event)
            self.store.insert(diff_event)
            
            # Store individual file diffs
            for file_path, file_diff in git_context.get('file_diffs', {}).items():
                file_event = Event(
                    ts=int(time.time() * 1000),
                    source=EventSource.GIT,
                    kind=EventKind.DIFF,
                    repo=self.repo_root,
                    text=file_diff,
                    cwd=self.repo_root,
                    file=file_path,
                    actor=Actor.USER,
                    meta={
                        'type': 'file_diff',
                        'file': file_path
                    }
                )
                
                events.append(file_event)
                self.store.insert(file_event)
        
        return events
    
    def collect_since_last_commit(self) -> List[Event]:
        """Collect events since last commit (or last 24 hours as fallback)"""
        import time
        
        now_ms = int(time.time() * 1000)
        
        # Check cache first
        cached_time = self.cache.get_last_commit_time(self.repo_root)
        if cached_time:
            start_time = cached_time
            if os.getenv('SAYU_DEBUG'):
                print(f"Using cached last commit time: {cached_time}")
        else:
            # Get last commit time directly from git
            last_commit = self.git_collector.get_last_commit()
            if last_commit and 'timestamp' in last_commit:
                start_time = last_commit['timestamp']
                # Cache the result
                self.cache.set_last_commit_time(self.repo_root, start_time)
                if os.getenv('SAYU_DEBUG'):
                    from datetime import datetime
                    dt = datetime.fromtimestamp(start_time / 1000)
                    print(f"Using last commit time from git: {dt.strftime('%m-%d %H:%M:%S')}")
            else:
                # Fallback to 24 hours if no commits found
                start_time = now_ms - (24 * 60 * 60 * 1000)
                if os.getenv('SAYU_DEBUG'):
                    print("No commit history found, using 24 hours fallback")
        
        all_events = []
        
        # Prepare collector tasks
        collector_tasks = []
        
        # Git collector task
        collector_tasks.append(('git', self.git_collector, True))
        
        # CLI collector task (if enabled)
        if self.config.connectors.get('cli', {}).get('mode') != 'off':
            collector_tasks.append(('cli', self.cli_collector, True))
        
        # Cursor collector task (if enabled)
        cursor_enabled = self.config.connectors.get('cursor', False)
        if os.getenv('SAYU_DEBUG'):
            print(f"Cursor enabled: {cursor_enabled}")
        if cursor_enabled:
            collector_tasks.append(('cursor', self.cursor_collector, True))
        
        # Claude collector task (if enabled)
        claude_enabled = self.config.connectors.get('claude', False)
        if os.getenv('SAYU_DEBUG'):
            print(f"Claude enabled: {claude_enabled}")
        if claude_enabled:
            collector_tasks.append(('claude', self.claude_collector, True))
        
        # Execute collectors in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all collector tasks
            future_to_collector = {}
            for name, collector, enabled in collector_tasks:
                if enabled:
                    future = executor.submit(
                        self._collect_with_error_handling,
                        name, collector, start_time, now_ms
                    )
                    future_to_collector[future] = name
            
            # Collect results as they complete
            for future in as_completed(future_to_collector):
                collector_name = future_to_collector[future]
                try:
                    events = future.result()
                    all_events.extend(events)
                    if os.getenv('SAYU_DEBUG'):
                        print(f"{collector_name} collector returned {len(events)} events")
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"{collector_name} collector error: {e}")
                        import traceback
                        traceback.print_exc()
        
        # Store events in database
        if all_events:
            self.store.insert_batch(all_events)

        # Query all events within time window from DB (sorted by time)
        return self.store.find_by_repo(self.repo_root, start_time, now_ms)
    
    def _collect_with_error_handling(
        self, name: str, collector: Any, start_time: int, end_time: int
    ) -> List[Event]:
        """Execute collector with error handling"""
        try:
            if os.getenv('SAYU_DEBUG'):
                print(f"Starting {name} collector: {start_time} to {end_time}")
            
            events = collector.pull_since(start_time, end_time, self.config)
            
            if os.getenv('SAYU_DEBUG'):
                print(f"{name} collector completed: {len(events)} events")
                if events:
                    print(f"Sample {name} event: {events[0].text[:50]}")
            
            return events
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"{name} collector error in thread: {e}")
                import traceback
                traceback.print_exc()
            return []

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
