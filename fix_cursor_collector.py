#!/usr/bin/env python3
"""Fix for Cursor collector to read from SQLite database"""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any

def find_cursor_conversations(repo_root: str) -> List[Dict[str, Any]]:
    """Find Cursor conversations from workspace SQLite databases"""
    conversations = []
    
    # Find workspace storage directory
    cursor_workspace_base = Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'workspaceStorage'
    
    if not cursor_workspace_base.exists():
        print(f"Cursor workspace storage not found: {cursor_workspace_base}")
        return conversations
    
    # Find workspace for this repo
    workspace_id = None
    for workspace_dir in cursor_workspace_base.iterdir():
        if not workspace_dir.is_dir():
            continue
            
        workspace_json = workspace_dir / 'workspace.json'
        if workspace_json.exists():
            try:
                with open(workspace_json, 'r') as f:
                    data = json.load(f)
                    if 'folder' in data and repo_root in data['folder']:
                        workspace_id = workspace_dir.name
                        break
            except:
                continue
    
    if not workspace_id:
        print(f"No Cursor workspace found for repo: {repo_root}")
        return conversations
    
    print(f"Found workspace: {workspace_id}")
    
    # Read from state.vscdb
    db_path = cursor_workspace_base / workspace_id / 'state.vscdb'
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return conversations
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query for composer data
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
        row = cursor.fetchone()
        
        if row and row[0]:
            composer_data = json.loads(row[0])
            print(f"Found {len(composer_data.get('allComposers', []))} composers")
            
            # Extract conversation info
            for composer in composer_data.get('allComposers', []):
                conversations.append({
                    'id': composer.get('composerId'),
                    'name': composer.get('name', 'Untitled'),
                    'created_at': composer.get('createdAt'),
                    'updated_at': composer.get('lastUpdatedAt'),
                    'type': 'composer'
                })
        
        # Also check for AI generations
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.generations'")
        row = cursor.fetchone()
        
        if row and row[0]:
            generations = json.loads(row[0])
            print(f"Found AI generations data")
        
        conn.close()
        
    except Exception as e:
        print(f"Error reading database: {e}")
        import traceback
        traceback.print_exc()
    
    return conversations

def test_cursor_fix():
    """Test the Cursor collector fix"""
    repo_root = os.getcwd()
    print(f"Testing Cursor collector fix for: {repo_root}")
    
    conversations = find_cursor_conversations(repo_root)
    
    print(f"\nFound {len(conversations)} conversations:")
    for conv in conversations:
        print(f"  - {conv['name']}")
        print(f"    ID: {conv['id']}")
        print(f"    Created: {conv.get('created_at')}")
        print(f"    Updated: {conv.get('updated_at')}")

if __name__ == "__main__":
    test_cursor_fix()