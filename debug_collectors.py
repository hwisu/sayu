#!/usr/bin/env python3
"""Debug script to check why Cursor and Claude collectors are not finding conversations"""

import os
import json
from pathlib import Path
from domain.collectors.conversation import ClaudeConversationCollector, CursorConversationCollector

# Set debug mode
os.environ['SAYU_DEBUG'] = '1'

def debug_claude_collector():
    """Debug Claude conversation collector"""
    print("\n=== DEBUGGING CLAUDE COLLECTOR ===")
    
    repo_root = os.getcwd()
    print(f"Repository root: {repo_root}")
    print(f"Repository name: {Path(repo_root).name}")
    
    collector = ClaudeConversationCollector(repo_root)
    
    # Check Claude directory
    claude_dir = Path.home() / '.claude'
    print(f"\nClaude directory exists: {claude_dir.exists()}")
    
    if claude_dir.exists():
        print("Claude directory contents:")
        for item in claude_dir.iterdir():
            print(f"  - {item.name}")
            
        projects_dir = claude_dir / 'projects'
        if projects_dir.exists():
            print(f"\nProjects directory contents:")
            for project in projects_dir.iterdir():
                print(f"  - {project.name}")
                if project.is_dir():
                    # List subdirectories
                    for sub in project.iterdir():
                        print(f"    - {sub.name}")
                        if sub.name == 'conversations' and sub.is_dir():
                            for conv in sub.iterdir():
                                print(f"      - {conv.name}")
    
    # Get conversation paths
    print("\nSearching for conversation paths...")
    paths = collector.get_conversation_paths()
    print(f"Found {len(paths)} conversation paths:")
    for path in paths:
        print(f"  - {path}")
        print(f"    Exists: {path.exists()}")
        if path.exists():
            print(f"    Size: {path.stat().st_size} bytes")
            print(f"    Modified: {path.stat().st_mtime}")
    
    # Check health
    health = collector.health()
    print(f"\nCollector health: {json.dumps(health, indent=2)}")

def debug_cursor_collector():
    """Debug Cursor conversation collector"""
    print("\n=== DEBUGGING CURSOR COLLECTOR ===")
    
    repo_root = os.getcwd()
    print(f"Repository root: {repo_root}")
    
    collector = CursorConversationCollector(repo_root)
    
    # Check all potential Cursor paths
    cursor_paths = [
        Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'History',
        Path.home() / '.cursor' / 'History',
        Path.home() / '.config' / 'Cursor' / 'User' / 'History',
    ]
    
    print("\nChecking Cursor paths:")
    for path in cursor_paths:
        print(f"  - {path}")
        print(f"    Exists: {path.exists()}")
        if path.exists():
            print(f"    Contents:")
            for item in path.iterdir():
                print(f"      - {item.name}")
    
    # Also check main Cursor directories
    print("\nChecking main Cursor directories:")
    cursor_main_paths = [
        Path.home() / 'Library' / 'Application Support' / 'Cursor',
        Path.home() / '.cursor',
        Path.home() / '.config' / 'Cursor',
    ]
    
    for path in cursor_main_paths:
        if path.exists():
            print(f"\n{path}:")
            # List immediate subdirectories
            for item in path.iterdir():
                if item.is_dir():
                    print(f"  - {item.name}/")
                else:
                    print(f"  - {item.name}")
    
    # Get conversation paths
    print("\nSearching for conversation paths...")
    paths = collector.get_conversation_paths()
    print(f"Found {len(paths)} conversation paths:")
    for path in paths:
        print(f"  - {path}")
        if path.exists():
            print(f"    Size: {path.stat().st_size} bytes")
    
    # Check health
    health = collector.health()
    print(f"\nCollector health: {json.dumps(health, indent=2)}")

def check_config():
    """Check configuration for collectors"""
    print("\n=== CHECKING CONFIGURATION ===")
    
    from infra.config.manager import ConfigManager
    
    config_manager = ConfigManager(os.getcwd())
    config = config_manager.get()
    
    print(f"Connectors config: {json.dumps(config.connectors, indent=2)}")

if __name__ == "__main__":
    debug_claude_collector()
    debug_cursor_collector()
    check_config()