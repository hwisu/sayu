"""Shared utilities for Sayu"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class CliUtils:
    """CLI utility functions"""
    
    @staticmethod
    def require_git_repo() -> str:
        """Ensure we're in a git repository and return root"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            print("❌ Not in a Git repository")
            print("Run 'git init' or navigate to a Git repository")
            sys.exit(1)
    
    @staticmethod
    def handle_error(context: str, error: Exception) -> None:
        """Handle CLI errors with nice formatting"""
        print(f"❌ Error during {context}:")
        print(str(error))
        
        if os.getenv('SAYU_DEBUG'):
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def get_git_root() -> Optional[str]:
        """Get git repository root, return None if not in repo"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    @staticmethod
    def get_current_branch() -> str:
        """Get current git branch name"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return 'unknown'
    
    @staticmethod
    def get_staged_files() -> List[str]:
        """Get list of staged files"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            )
            files = result.stdout.strip().split('\n')
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    @staticmethod
    def get_diff_stats() -> Dict[str, Any]:
        """Get statistics about staged changes"""
        try:
            # Get diff stat
            result = subprocess.run(
                ['git', 'diff', '--cached', '--stat'],
                capture_output=True,
                text=True,
                check=True
            )
            stat_output = result.stdout.strip()
            
            # Get numstat for detailed counts
            result = subprocess.run(
                ['git', 'diff', '--cached', '--numstat'],
                capture_output=True,
                text=True,
                check=True
            )
            
            total_additions = 0
            total_deletions = 0
            file_changes = []
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        additions = int(parts[0]) if parts[0] != '-' else 0
                        deletions = int(parts[1]) if parts[1] != '-' else 0
                        filename = parts[2]
                        
                        total_additions += additions
                        total_deletions += deletions
                        file_changes.append({
                            'file': filename,
                            'additions': additions,
                            'deletions': deletions
                        })
            
            return {
                'files_changed': len(file_changes),
                'additions': total_additions,
                'deletions': total_deletions,
                'file_changes': file_changes,
                'stat_output': stat_output
            }
        except subprocess.CalledProcessError:
            return {
                'files_changed': 0,
                'additions': 0,
                'deletions': 0,
                'file_changes': [],
                'stat_output': ''
            }
    
    @staticmethod
    def wrap_text(text: str, width: int = 80) -> str:
        """Wrap text to specified width"""
        import textwrap
        return textwrap.fill(text, width=width, break_long_words=False)


class ProgressTracker:
    """Track and display progress for long-running operations"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.start_time = time.time()
        self.last_step_time = self.start_time
        
    def step(self, message: str, emoji: str = "⚙️") -> None:
        """Display a progress step with timing"""
        if not self.enabled:
            return
            
        current_time = time.time()
        step_duration = current_time - self.last_step_time
        total_duration = current_time - self.start_time
        
        # Format timing info
        if step_duration > 0.1:  # Only show if took more than 100ms
            timing = f" ({step_duration:.1f}s)"
        else:
            timing = ""
            
        # Print with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {emoji} {message}{timing}", file=sys.stderr)
        
        self.last_step_time = current_time
    
    def finish(self, message: str = "Complete") -> None:
        """Display final timing"""
        if not self.enabled:
            return
            
        total_duration = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ {message} (total: {total_duration:.1f}s)", file=sys.stderr)

