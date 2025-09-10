#!/usr/bin/env python3
"""Debug script to check sayu-specific conversations in Claude"""

import os
import json
from pathlib import Path
from domain.collectors.conversation import ClaudeConversationCollector

# Set debug mode
os.environ['SAYU_DEBUG'] = '1'

def check_sayu_conversations():
    """Check sayu conversations specifically"""
    print("\n=== SAYU CONVERSATIONS IN CLAUDE ===")
    
    repo_root = os.getcwd()
    collector = ClaudeConversationCollector(repo_root)
    
    # Look for sayu project directory
    claude_projects = Path.home() / '.claude' / 'projects'
    sayu_project = claude_projects / '-Users-hwisookim-sayu'
    
    print(f"Sayu project directory: {sayu_project}")
    print(f"Exists: {sayu_project.exists()}")
    
    if sayu_project.exists():
        print("\nSayu conversation files:")
        for file in sorted(sayu_project.iterdir()):
            if file.suffix == '.jsonl':
                print(f"\n  - {file.name}")
                print(f"    Size: {file.stat().st_size} bytes")
                print(f"    Modified: {file.stat().st_mtime}")
                
                # Read first and last few lines to check format
                with open(file, 'r') as f:
                    lines = f.readlines()
                    print(f"    Total lines: {len(lines)}")
                    
                    if lines:
                        # Parse first line
                        try:
                            first_entry = json.loads(lines[0])
                            print(f"    First entry timestamp: {first_entry.get('timestamp', 'N/A')}")
                            print(f"    First entry has message: {'message' in first_entry}")
                        except:
                            print(f"    Failed to parse first line")
                        
                        # Parse last line
                        try:
                            last_entry = json.loads(lines[-1])
                            print(f"    Last entry timestamp: {last_entry.get('timestamp', 'N/A')}")
                            print(f"    Last entry has message: {'message' in last_entry}")
                        except:
                            print(f"    Failed to parse last line")

def test_collector_paths():
    """Test what the collector actually returns for sayu"""
    print("\n=== TESTING COLLECTOR PATH LOGIC ===")
    
    repo_root = os.getcwd()
    print(f"Current repo root: {repo_root}")
    print(f"Repo name from path: {Path(repo_root).name}")
    
    collector = ClaudeConversationCollector(repo_root)
    paths = collector.get_conversation_paths()
    
    sayu_paths = [p for p in paths if 'sayu' in str(p)]
    print(f"\nFound {len(sayu_paths)} sayu-related paths:")
    for path in sayu_paths[:5]:  # Show first 5
        print(f"  - {path}")

def test_parse_recent_conversation():
    """Test parsing a recent conversation file"""
    print("\n=== TESTING RECENT CONVERSATION PARSING ===")
    
    # Find most recent sayu conversation
    claude_projects = Path.home() / '.claude' / 'projects'
    sayu_project = claude_projects / '-Users-hwisookim-sayu'
    
    if sayu_project.exists():
        files = list(sayu_project.glob('*.jsonl'))
        if files:
            # Sort by modification time, get most recent
            most_recent = max(files, key=lambda f: f.stat().st_mtime)
            print(f"Most recent file: {most_recent.name}")
            print(f"Modified: {most_recent.stat().st_mtime}")
            
            collector = ClaudeConversationCollector(os.getcwd())
            try:
                messages = collector.parse_conversation_file(most_recent)
                print(f"Parsed {len(messages)} messages")
                
                if messages:
                    print("\nFirst 3 messages:")
                    for i, msg in enumerate(messages[:3]):
                        print(f"\n  Message {i+1}:")
                        print(f"    Timestamp: {msg['timestamp']}")
                        print(f"    Role: {msg['role']}")
                        print(f"    Text preview: {msg['text'][:100]}...")
            except Exception as e:
                print(f"Error parsing: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    check_sayu_conversations()
    test_collector_paths()
    test_parse_recent_conversation()