"""Git hook handlers for Sayu"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from shared.utils import CliUtils
from infra.config.manager import ConfigManager
from domain.events.store_manager import StoreManager
from infra.api.llm import LLMApiClient


class HookHandlers:
    """Handle git hook events"""
    
    @staticmethod
    def handle_commit_msg(msg_file: str):
        """Handle commit-msg hook"""
        try:
            repo_root = CliUtils.get_git_root()
            if not repo_root:
                return
            
            # Load config
            config_manager = ConfigManager(repo_root)
            config = config_manager.get_user_config()
            
            if not config.enabled:
                return
            
            # Read commit message
            with open(msg_file, 'r') as f:
                original_msg = f.read()
            
            # Skip if already has AI context
            if 'AI-Context (sayu)' in original_msg:
                return
            
            # Get staged files and diff
            staged_files = CliUtils.get_staged_files()
            if not staged_files:
                return  # Nothing staged
            
            diff_stats = CliUtils.get_diff_stats()
            
            # Generate AI summary
            try:
                summary = LLMApiClient.generate_summary(
                    repo_root=repo_root,
                    staged_files=staged_files,
                    diff_stats=diff_stats,
                    language=config.language
                )
                
                if summary and config.commitTrailer:
                    # Append AI context to commit message
                    enhanced_msg = f"{original_msg.rstrip()}\n\n---\nAI-Context (sayu)\n{summary}\n---\n"
                    
                    with open(msg_file, 'w') as f:
                        f.write(enhanced_msg)
                        
            except Exception as e:
                # Fail silently - don't block commit
                if os.getenv('SAYU_DEBUG'):
                    print(f"Summary generation failed: {e}")
                    
        except Exception as e:
            # Fail-open: Never block commits
            if os.getenv('SAYU_DEBUG'):
                print(f"Hook error: {e}")
    
    @staticmethod
    def handle_post_commit():
        """Handle post-commit hook"""
        try:
            repo_root = CliUtils.get_git_root()
            if not repo_root:
                return
            
            # Store commit event
            store = StoreManager.get_store()
            
            # Get commit info
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%s|%an|%ae|%at'],
                capture_output=True,
                text=True,
                check=True
            )
            
            parts = result.stdout.strip().split('|')
            if len(parts) >= 5:
                commit_hash = parts[0]
                subject = parts[1]
                author = parts[2]
                email = parts[3]
                timestamp = int(parts[4]) * 1000  # Convert to milliseconds
                
                from domain.events.types import Event, EventSource, EventKind
                
                event = Event(
                    source=EventSource.GIT,
                    kind=EventKind.COMMIT,
                    repo=repo_root,
                    cwd=os.getcwd(),
                    text=f"{commit_hash[:8]}: {subject}",
                    ts=timestamp,
                    meta={
                        'hash': commit_hash,
                        'author': author,
                        'email': email
                    }
                )
                
                store.insert(event)
                
        except Exception as e:
            # Fail silently
            if os.getenv('SAYU_DEBUG'):
                print(f"Post-commit error: {e}")
    
    @staticmethod
    def preview_context(repo_root: str):
        """Preview AI context without modifying commit"""
        try:
            # Get staged files and diff
            staged_files = CliUtils.get_staged_files()
            if not staged_files:
                print("No files staged for commit")
                return
            
            diff_stats = CliUtils.get_diff_stats()
            
            print(f"\nStaged files ({len(staged_files)}):")
            for f in staged_files[:10]:
                print(f"  - {f}")
            if len(staged_files) > 10:
                print(f"  ... and {len(staged_files) - 10} more")
            
            print(f"\nChanges: +{diff_stats['additions']} -{diff_stats['deletions']}")
            
            # Try to generate summary
            config_manager = ConfigManager(repo_root)
            config = config_manager.get_user_config()
            
            try:
                summary = LLMApiClient.generate_summary(
                    repo_root=repo_root,
                    staged_files=staged_files,
                    diff_stats=diff_stats,
                    language=config.language
                )
                
                if summary:
                    print("\n--- AI Context Preview ---")
                    print(summary)
                    print("---")
                else:
                    print("\nNo AI context generated")
                    
            except Exception as e:
                print(f"\nFailed to generate AI context: {e}")
                
        except Exception as e:
            print(f"Preview error: {e}")
