#!/usr/bin/env python3
"""Sayu background daemon for real-time event collection"""

import os
import sys
import time
import signal
import logging
import json
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from queue import Queue, Empty
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from domain.events.store_manager import StoreManager
from domain.events.types import Event, EventSource, EventKind, Actor
from domain.collectors.manager import CollectorManager
from shared.utils import CliUtils
from infra.config.manager import ConfigManager


class SayuDaemon:
    """Background daemon for continuous event collection"""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.config_manager = ConfigManager(repo_root)
        self.config = self.config_manager.get_user_config()
        self.store = StoreManager.get_store()
        self.collector_manager = CollectorManager(repo_root)
        
        # State management
        self.running = False
        self.event_queue = Queue()
        self.last_collection = {}
        
        # Setup logging
        self.setup_logging()
        
        # Setup PID file
        self.pid_file = Path.home() / '.sayu' / f'sayud_{self._get_repo_hash()}.pid'
        self.pid_file.parent.mkdir(exist_ok=True)
        
    def _get_repo_hash(self) -> str:
        """Get unique hash for repository"""
        import hashlib
        return hashlib.md5(self.repo_root.encode()).hexdigest()[:8]
    
    def setup_logging(self):
        """Setup daemon logging"""
        log_dir = Path.home() / '.sayu' / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'sayud_{self._get_repo_hash()}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if os.getenv('SAYU_DEBUG') else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger('sayud')
    
    def start(self):
        """Start the daemon"""
        # Check if already running
        if self.is_running():
            self.logger.warning(f"Daemon already running for {self.repo_root}")
            return False
        
        # Write PID file
        self.pid_file.write_text(str(os.getpid()))
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
        self.running = True
        self.logger.info(f"Starting Sayu daemon for {self.repo_root}")
        
        # Start collector threads
        threads = [
            threading.Thread(target=self._collect_loop, name="collector"),
            threading.Thread(target=self._process_loop, name="processor"),
            threading.Thread(target=self._watch_files, name="watcher"),
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the daemon"""
        self.running = False
        self.logger.info("Stopping Sayu daemon")
        
        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def is_running(self) -> bool:
        """Check if daemon is already running"""
        if not self.pid_file.exists():
            return False
        
        try:
            pid = int(self.pid_file.read_text())
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError):
            # Process doesn't exist, clean up stale PID file
            self.pid_file.unlink()
            return False
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}")
        self.stop()
    
    def _collect_loop(self):
        """Main collection loop - runs periodically"""
        while self.running:
            try:
                # Collect from each source with rate limiting
                self._collect_cursor_events()
                time.sleep(5)  # Check Cursor every 5 seconds
                
                self._collect_claude_events() 
                time.sleep(5)  # Check Claude every 5 seconds
                
                self._collect_git_events()
                time.sleep(2)  # Check Git every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
                time.sleep(10)  # Back off on error
    
    def _collect_cursor_events(self):
        """Collect Cursor events incrementally"""
        try:
            # Get last collected timestamp
            last_ts = self.last_collection.get('cursor', 0)
            
            # Collect only new events
            events = self.collector_manager.cursor_collector.collect()
            new_events = [e for e in events if e.ts > last_ts]
            
            if new_events:
                self.logger.info(f"Found {len(new_events)} new Cursor events")
                for event in new_events:
                    self.event_queue.put(event)
                
                # Update last collection timestamp
                self.last_collection['cursor'] = max(e.ts for e in new_events)
                
        except Exception as e:
            self.logger.error(f"Cursor collection error: {e}")
    
    def _collect_claude_events(self):
        """Collect Claude events incrementally"""
        try:
            # Get last collected timestamp
            last_ts = self.last_collection.get('claude', 0)
            
            # Collect only new events
            events = self.collector_manager.claude_collector.collect()
            new_events = [e for e in events if e.ts > last_ts]
            
            if new_events:
                self.logger.info(f"Found {len(new_events)} new Claude events")
                for event in new_events:
                    self.event_queue.put(event)
                
                # Update last collection timestamp
                self.last_collection['claude'] = max(e.ts for e in new_events)
                
        except Exception as e:
            self.logger.error(f"Claude collection error: {e}")
    
    def _collect_git_events(self):
        """Collect Git events incrementally"""
        try:
            # Check for new commits
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%at'],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                check=False
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                if len(parts) == 2:
                    commit_hash = parts[0]
                    timestamp = int(parts[1]) * 1000
                    
                    last_commit = self.last_collection.get('git_commit', '')
                    if commit_hash != last_commit:
                        # New commit detected
                        self.logger.info(f"New commit detected: {commit_hash[:8]}")
                        self.last_collection['git_commit'] = commit_hash
                        
                        # Collect git events
                        events = self.collector_manager.git_collector.collect()
                        for event in events:
                            self.event_queue.put(event)
                            
        except Exception as e:
            self.logger.error(f"Git collection error: {e}")
    
    def _watch_files(self):
        """Watch for file changes in the repository"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class FileChangeHandler(FileSystemEventHandler):
                def __init__(self, daemon):
                    self.daemon = daemon
                    self.last_event = {}
                
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    
                    # Debounce events (same file within 1 second)
                    now = time.time()
                    if event.src_path in self.last_event:
                        if now - self.last_event[event.src_path] < 1:
                            return
                    self.last_event[event.src_path] = now
                    
                    # Skip non-code files
                    path = Path(event.src_path)
                    if path.suffix not in ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.cpp', '.c', '.h']:
                        return
                    
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in path.parts):
                        return
                    
                    # Create file change event
                    file_event = Event(
                        source=EventSource.FILE,
                        kind=EventKind.EDIT,
                        repo=self.daemon.repo_root,
                        cwd=str(path.parent),
                        text=f"Modified: {path.name}",
                        actor=Actor.USER,
                        meta={'file': str(path), 'action': 'modified'}
                    )
                    
                    self.daemon.event_queue.put(file_event)
                    self.daemon.logger.debug(f"File modified: {path}")
            
            observer = Observer()
            handler = FileChangeHandler(self)
            observer.schedule(handler, self.repo_root, recursive=True)
            observer.start()
            
            while self.running:
                time.sleep(1)
            
            observer.stop()
            observer.join()
            
        except ImportError:
            self.logger.warning("watchdog not installed, file watching disabled")
            self.logger.info("Install with: pip install watchdog")
        except Exception as e:
            self.logger.error(f"File watching error: {e}")
    
    def _process_loop(self):
        """Process events from queue and store them"""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Get events from queue with timeout
                try:
                    event = self.event_queue.get(timeout=1)
                    batch.append(event)
                except Empty:
                    pass
                
                # Flush batch if needed
                now = time.time()
                should_flush = (
                    len(batch) >= 10 or  # Batch size limit
                    (len(batch) > 0 and now - last_flush > 5)  # Time limit
                )
                
                if should_flush and batch:
                    self.logger.info(f"Storing {len(batch)} events")
                    for event in batch:
                        try:
                            self.store.insert(event)
                        except Exception as e:
                            self.logger.error(f"Failed to store event: {e}")
                    
                    batch.clear()
                    last_flush = now
                    
            except Exception as e:
                self.logger.error(f"Processing error: {e}")
                time.sleep(1)
    
    def get_status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return {
            'running': self.running,
            'pid': os.getpid(),
            'repo': self.repo_root,
            'queue_size': self.event_queue.qsize(),
            'last_collection': self.last_collection,
            'uptime': self._get_uptime()
        }
    
    def _get_uptime(self) -> str:
        """Get daemon uptime"""
        if not self.pid_file.exists():
            return "Not running"
        
        start_time = self.pid_file.stat().st_mtime
        uptime_seconds = time.time() - start_time
        
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def main():
    """Main entry point for daemon"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sayu background daemon')
    parser.add_argument('command', choices=['start', 'stop', 'status', 'restart'],
                        help='Daemon command')
    parser.add_argument('--repo', default='.', help='Repository path')
    
    args = parser.parse_args()
    
    # Get repository root
    repo_root = os.path.abspath(args.repo)
    if not os.path.exists(os.path.join(repo_root, '.git')):
        print(f"Error: {repo_root} is not a git repository")
        sys.exit(1)
    
    daemon = SayuDaemon(repo_root)
    
    if args.command == 'start':
        if daemon.is_running():
            print(f"Daemon already running for {repo_root}")
        else:
            print(f"Starting daemon for {repo_root}...")
            # Fork to background
            if os.fork() == 0:
                # Child process
                os.setsid()
                daemon.start()
            else:
                # Parent process
                time.sleep(1)
                if daemon.is_running():
                    print("Daemon started successfully")
                else:
                    print("Failed to start daemon")
    
    elif args.command == 'stop':
        if daemon.is_running():
            pid = int(daemon.pid_file.read_text())
            os.kill(pid, signal.SIGTERM)
            print(f"Stopping daemon (PID: {pid})...")
            time.sleep(1)
            if not daemon.is_running():
                print("Daemon stopped")
            else:
                print("Failed to stop daemon")
        else:
            print("Daemon not running")
    
    elif args.command == 'status':
        if daemon.is_running():
            pid = int(daemon.pid_file.read_text())
            print(f"Daemon running (PID: {pid})")
            print(f"Repository: {repo_root}")
            print(f"Uptime: {daemon._get_uptime()}")
        else:
            print("Daemon not running")
    
    elif args.command == 'restart':
        if daemon.is_running():
            pid = int(daemon.pid_file.read_text())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        
        print(f"Starting daemon for {repo_root}...")
        if os.fork() == 0:
            os.setsid()
            daemon.start()
        else:
            time.sleep(1)
            if daemon.is_running():
                print("Daemon restarted successfully")


if __name__ == '__main__':
    main()