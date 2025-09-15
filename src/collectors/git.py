"""Git event collector for tracking commits, checkouts, and other git operations."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core import Collector, Event, EventType


class GitCollector(Collector):
    """Collects Git events like commits, checkouts, branches, etc."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize Git collector."""
        self.repo_path = repo_path or Path.cwd()
        self.git_dir = self.repo_path / ".git"
        self.last_commit_hash = None
        self.last_branch = None
    
    @property
    def name(self) -> str:
        """Return collector name."""
        return "git"
    
    def collect(self, since: Optional[datetime] = None) -> List[Event]:
        """Collect Git events since the given timestamp."""
        if not self.git_dir.exists():
            return []
        
        events = []
        
        # Get current branch
        current_branch = self._get_current_branch()
        if current_branch and current_branch != self.last_branch:
            events.append(self._create_branch_event(current_branch))
            self.last_branch = current_branch
        
        # Get recent commits
        commits = self._get_recent_commits(since)
        for commit in commits:
            events.append(self._create_commit_event(commit))
        
        # Get recent checkouts (from reflog)
        checkouts = self._get_recent_checkouts(since)
        for checkout in checkouts:
            events.append(self._create_checkout_event(checkout))
        
        # Get recent merges
        merges = self._get_recent_merges(since)
        for merge in merges:
            events.append(self._create_merge_event(merge))
        
        return events
    
    def setup(self) -> None:
        """Set up Git hooks for automatic event collection."""
        if not self.git_dir.exists():
            return
        
        hooks_dir = self.git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        # Create post-commit hook
        self._create_post_commit_hook(hooks_dir)
        
        # Create post-checkout hook
        self._create_post_checkout_hook(hooks_dir)
        
        # Create post-merge hook
        self._create_post_merge_hook(hooks_dir)
    
    def teardown(self) -> None:
        """Remove Git hooks."""
        if not self.git_dir.exists():
            return
        
        hooks_dir = self.git_dir / "hooks"
        
        # Remove hooks
        for hook_name in ["post-commit", "post-checkout", "post-merge"]:
            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                hook_path.unlink()
    
    def _get_current_branch(self) -> Optional[str]:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        return None
    
    def _get_recent_commits(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent commits."""
        try:
            # Build git log command
            cmd = ["git", "log", "--pretty=format:%H|%an|%ae|%ad|%s", "--date=iso"]
            
            if since:
                cmd.extend(["--since", since.isoformat()])
            else:
                # Get last 10 commits if no since date
                cmd.extend(["-10"])
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'date': parts[3],
                        'message': parts[4]
                    })
            
            return commits
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return []
    
    def _get_recent_checkouts(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent checkouts from reflog."""
        try:
            cmd = ["git", "reflog", "--pretty=format:%H|%gd|%gs|%ad", "--date=iso"]
            
            if since:
                cmd.extend(["--since", since.isoformat()])
            else:
                cmd.extend(["-20"])  # Last 20 reflog entries
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            checkouts = []
            for line in result.stdout.strip().split('\n'):
                if not line or 'checkout:' not in line:
                    continue
                
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    checkouts.append({
                        'hash': parts[0],
                        'ref': parts[1],
                        'message': parts[2],
                        'date': parts[3]
                    })
            
            return checkouts
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return []
    
    def _get_recent_merges(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent merges."""
        try:
            cmd = ["git", "log", "--merges", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
            
            if since:
                cmd.extend(["--since", since.isoformat()])
            else:
                cmd.extend(["-10"])
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            merges = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    merges.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'date': parts[2],
                        'message': parts[3]
                    })
            
            return merges
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return []
    
    def _create_commit_event(self, commit: Dict[str, Any]) -> Event:
        """Create commit event."""
        timestamp = datetime.fromisoformat(commit['date'].replace(' ', 'T'))
        
        content = f"커밋: {commit['message']}"
        if len(commit['message']) > 50:
            content = f"커밋: {commit['message'][:50]}..."
        
        return Event(
            timestamp=timestamp,
            type=EventType.ACTION,
            source="git",
            content=content,
            metadata={
                "action": "commit",
                "hash": commit['hash'],
                "author": commit['author'],
                "email": commit['email'],
                "message": commit['message'],
                "full_message": commit['message']
            }
        )
    
    def _create_checkout_event(self, checkout: Dict[str, Any]) -> Event:
        """Create checkout event."""
        timestamp = datetime.fromisoformat(checkout['date'].replace(' ', 'T'))
        
        # Extract branch name from checkout message
        message = checkout['message']
        if 'checkout: moving from' in message:
            # Extract source and target branches
            parts = message.split('checkout: moving from ')[1].split(' to ')
            if len(parts) == 2:
                source_branch = parts[0]
                target_branch = parts[1]
                content = f"브랜치 변경: {source_branch} → {target_branch}"
            else:
                content = f"체크아웃: {message}"
        else:
            content = f"체크아웃: {message}"
        
        return Event(
            timestamp=timestamp,
            type=EventType.ACTION,
            source="git",
            content=content,
            metadata={
                "action": "checkout",
                "hash": checkout['hash'],
                "ref": checkout['ref'],
                "message": checkout['message']
            }
        )
    
    def _create_merge_event(self, merge: Dict[str, Any]) -> Event:
        """Create merge event."""
        timestamp = datetime.fromisoformat(merge['date'].replace(' ', 'T'))
        
        content = f"머지: {merge['message']}"
        if len(merge['message']) > 50:
            content = f"머지: {merge['message'][:50]}..."
        
        return Event(
            timestamp=timestamp,
            type=EventType.ACTION,
            source="git",
            content=content,
            metadata={
                "action": "merge",
                "hash": merge['hash'],
                "author": merge['author'],
                "message": merge['message']
            }
        )
    
    def _create_branch_event(self, branch: str) -> Event:
        """Create branch change event."""
        return Event(
            timestamp=datetime.now(),
            type=EventType.ACTION,
            source="git",
            content=f"현재 브랜치: {branch}",
            metadata={
                "action": "branch_change",
                "branch": branch
            }
        )
    
    def _create_post_commit_hook(self, hooks_dir: Path) -> None:
        """Create post-commit hook."""
        hook_content = '''#!/bin/sh
# Sayu Git post-commit hook
sayu collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-commit"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
    
    def _create_post_checkout_hook(self, hooks_dir: Path) -> None:
        """Create post-checkout hook."""
        hook_content = '''#!/bin/sh
# Sayu Git post-checkout hook
sayu collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-checkout"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
    
    def _create_post_merge_hook(self, hooks_dir: Path) -> None:
        """Create post-merge hook."""
        hook_content = '''#!/bin/sh
# Sayu Git post-merge hook
sayu collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-merge"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
