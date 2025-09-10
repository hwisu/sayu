#!/usr/bin/env python3
"""Explore Cursor SQLite database structure"""

import os
import sqlite3
import json
from pathlib import Path

def explore_cursor_db():
    """Explore Cursor database structure"""
    # Find workspace
    cursor_workspace_base = Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'workspaceStorage'
    workspace_id = 'c9d4d11cea7f9eaa4212fe4c48c46a55'  # sayu workspace
    
    db_path = cursor_workspace_base / workspace_id / 'state.vscdb'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all keys that might contain conversation data
    print("=== ALL KEYS IN DATABASE ===")
    cursor.execute("SELECT key FROM ItemTable WHERE key LIKE '%composer%' OR key LIKE '%ai%' OR key LIKE '%generation%' OR key LIKE '%conversation%' OR key LIKE '%chat%' OR key LIKE '%message%'")
    
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
    
    # Check aiService.generations structure
    print("\n=== AI SERVICE GENERATIONS ===")
    cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.generations'")
    row = cursor.fetchone()
    if row and row[0]:
        try:
            data = json.loads(row[0])
            print(f"Type: {type(data)}")
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                # Sample a generation
                for key in list(data.keys())[:2]:
                    print(f"\nGeneration {key}:")
                    gen = data[key]
                    for k, v in gen.items():
                        if k == 'messages':
                            print(f"  {k}: {len(v)} messages")
                        elif isinstance(v, str) and len(v) > 100:
                            print(f"  {k}: {v[:100]}...")
                        else:
                            print(f"  {k}: {v}")
        except Exception as e:
            print(f"Error parsing: {e}")
    
    # Check composer data structure in detail
    print("\n=== COMPOSER DATA STRUCTURE ===")
    cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
    row = cursor.fetchone()
    if row and row[0]:
        data = json.loads(row[0])
        # Check if there are message stores
        if 'composerMessageStores' in data:
            print(f"Found composerMessageStores with {len(data['composerMessageStores'])} entries")
            for composer_id, messages in list(data['composerMessageStores'].items())[:1]:
                print(f"\nComposer {composer_id}:")
                print(f"  Messages: {len(messages)}")
                if messages:
                    print(f"  First message sample: {json.dumps(messages[0], indent=2)[:500]}...")
    
    conn.close()

if __name__ == "__main__":
    explore_cursor_db()