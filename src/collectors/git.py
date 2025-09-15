"""Git event collector for tracking commits, checkouts, and other git operations."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core import Collector, Event, EventType


class GitCollector(Collector):
    """Collects Git events like commits, checkouts, branches, etc."""
    
    def __init__(self, repo_path: Optional[Path] = None, commit_range: Optional[str] = None):
        """Initialize Git collector."""
        self.repo_path = repo_path or Path.cwd()
        self.git_dir = self.repo_path / ".git"
        self.last_commit_hash = None
        self.last_branch = None
        self.commit_range = commit_range  # e.g., "HEAD~1..HEAD", "abc123..def456"
        self.seen_commit_hashes = set()  # Track already processed commits to avoid duplicates
    
    @property
    def name(self) -> str:
        """Return collector name."""
        return "git"
    
    def collect(self, since: Optional[datetime] = None) -> List[Event]:
        """Collect Git events since the given timestamp."""
        if not self.git_dir.exists():
            return []

        # Make since timezone-naive if it's timezone-aware
        if since and since.tzinfo is not None:
            since = since.replace(tzinfo=None)

        events = []
        processed_hashes = set()  # Track commits processed in this collection

        # Get current branch
        current_branch = self._get_current_branch()
        if current_branch and current_branch != self.last_branch:
            events.append(self._create_branch_event(current_branch))
            self.last_branch = current_branch

        # Get recent commits
        commits = self._get_recent_commits(since)
        for commit in commits:
            # Skip if we've already processed this commit
            if commit['hash'] in self.seen_commit_hashes or commit['hash'] in processed_hashes:
                continue

            # Skip auto-generated summary commits
            if 'Collecting events since last commit' in commit['message']:
                continue

            events.append(self._create_commit_event(commit))
            processed_hashes.add(commit['hash'])

        # Get recent checkouts (from reflog)
        checkouts = self._get_recent_checkouts(since)
        for checkout in checkouts:
            # Skip if this is a duplicate checkout for same hash
            if checkout['hash'] in processed_hashes:
                continue
            events.append(self._create_checkout_event(checkout))
            processed_hashes.add(checkout['hash'])

        # Get recent merges (skip if already in commits)
        merges = self._get_recent_merges(since)
        for merge in merges:
            if merge['hash'] not in processed_hashes:
                events.append(self._create_merge_event(merge))
                processed_hashes.add(merge['hash'])

        # Update seen commits for next collection
        self.seen_commit_hashes.update(processed_hashes)

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
    
    def _get_last_commit_time(self) -> Optional[datetime]:
        """Get the timestamp of the last commit."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%ad", "--date=iso"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                date_str = result.stdout.strip()
                # Remove timezone info and normalize format
                if '+' in date_str:
                    date_str = date_str.split('+')[0].strip()
                elif date_str.endswith('Z'):
                    date_str = date_str[:-1].strip()
                # Replace space with T for ISO format
                if ' ' in date_str:
                    date_str = date_str.replace(' ', 'T')
                return datetime.fromisoformat(date_str)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        return None
    
    def _get_commit_time(self, commit_ref: str) -> Optional[datetime]:
        """Get the timestamp of a specific commit."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%ad", "--date=iso", commit_ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                date_str = result.stdout.strip()
                # Remove timezone info and normalize format
                if '+' in date_str:
                    date_str = date_str.split('+')[0].strip()
                elif date_str.endswith('Z'):
                    date_str = date_str[:-1].strip()
                # Replace space with T for ISO format
                if ' ' in date_str:
                    date_str = date_str.replace(' ', 'T')
                return datetime.fromisoformat(date_str)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        return None
    
    def _get_recent_commits(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent commits."""
        try:
            # Build git log command
            cmd = ["git", "log", "--pretty=format:%H|%an|%ae|%ad|%s", "--date=iso"]
            
            # Use commit range if specified
            if self.commit_range:
                cmd.append(self.commit_range)
            elif since:
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
        # Parse ISO format datetime and make it timezone-naive
        date_str = commit['date']
        if '+' in date_str:
            date_str = date_str.split('+')[0].strip()
        elif date_str.endswith('Z'):
            date_str = date_str[:-1].strip()
        if ' ' in date_str:
            date_str = date_str.replace(' ', 'T')
        timestamp = datetime.fromisoformat(date_str)
        
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
        # Parse ISO format datetime and make it timezone-naive
        date_str = checkout['date']
        if '+' in date_str:
            date_str = date_str.split('+')[0].strip()
        elif date_str.endswith('Z'):
            date_str = date_str[:-1].strip()
        if ' ' in date_str:
            date_str = date_str.replace(' ', 'T')
        timestamp = datetime.fromisoformat(date_str)
        
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
        # Parse ISO format datetime and make it timezone-naive
        date_str = merge['date']
        if '+' in date_str:
            date_str = date_str.split('+')[0].strip()
        elif date_str.endswith('Z'):
            date_str = date_str[:-1].strip()
        if ' ' in date_str:
            date_str = date_str.replace(' ', 'T')
        timestamp = datetime.fromisoformat(date_str)
        
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
        # Try to find sayu in PATH or use pipx default location
        import shutil
        sayu_path = shutil.which('sayu')
        if not sayu_path:
            # Use pipx default location
            home = Path.home()
            sayu_path = home / '.local' / 'bin' / 'sayu'
            if not sayu_path.exists():
                sayu_path = 'sayu'  # Fallback to PATH
            else:
                sayu_path = str(sayu_path)

        hook_content = f'''#!/bin/sh
# Sayu Git post-commit hook
{sayu_path} collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-commit"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

    def _create_post_checkout_hook(self, hooks_dir: Path) -> None:
        """Create post-checkout hook."""
        # Try to find sayu in PATH or use pipx default location
        import shutil
        sayu_path = shutil.which('sayu')
        if not sayu_path:
            # Use pipx default location
            home = Path.home()
            sayu_path = home / '.local' / 'bin' / 'sayu'
            if not sayu_path.exists():
                sayu_path = 'sayu'  # Fallback to PATH
            else:
                sayu_path = str(sayu_path)

        hook_content = f'''#!/bin/sh
# Sayu Git post-checkout hook
{sayu_path} collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-checkout"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

    def _create_post_merge_hook(self, hooks_dir: Path) -> None:
        """Create post-merge hook."""
        # Try to find sayu in PATH or use pipx default location
        import shutil
        sayu_path = shutil.which('sayu')
        if not sayu_path:
            # Use pipx default location
            home = Path.home()
            sayu_path = home / '.local' / 'bin' / 'sayu'
            if not sayu_path.exists():
                sayu_path = 'sayu'  # Fallback to PATH
            else:
                sayu_path = str(sayu_path)

        hook_content = f'''#!/bin/sh
# Sayu Git post-merge hook
{sayu_path} collect >/dev/null 2>&1 || true
'''
        hook_path = hooks_dir / "post-merge"
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
