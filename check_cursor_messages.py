#!/usr/bin/env python3
"""Check for Cursor message storage"""

import os
import sqlite3
import json
from pathlib import Path

def check_all_cursor_storage():
    """Check all possible Cursor storage locations"""
    # Find workspace
    cursor_workspace_base = Path.home() / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'workspaceStorage'
    workspace_id = 'c9d4d11cea7f9eaa4212fe4c48c46a55'  # sayu workspace
    
    db_path = cursor_workspace_base / workspace_id / 'state.vscdb'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get ALL keys to understand structure
    print("=== CHECKING ALL COMPOSER-RELATED KEYS ===")
    cursor.execute("SELECT key, LENGTH(value) as size FROM ItemTable WHERE key LIKE '%composer%' OR key LIKE 'workbench.panel.composerChatViewPane%' ORDER BY key")
    
    for row in cursor.fetchall():
        print(f"Key: {row[0]}, Size: {row[1]} bytes")
        
        # Check specific composer chat view panes
        if 'composerChatViewPane' in row[0]:
            cursor.execute(f"SELECT value FROM ItemTable WHERE key = '{row[0]}'")
            value_row = cursor.fetchone()
            if value_row and value_row[0]:
                try:
                    data = json.loads(value_row[0])
                    print(f"  Type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())[:5]}")
                        if 'messages' in data:
                            print(f"  Messages: {len(data['messages'])}")
                    elif isinstance(data, list) and len(data) > 0:
                        print(f"  List length: {len(data)}")
                        if isinstance(data[0], dict) and 'messages' in data[0]:
                            print(f"  First item has messages: {len(data[0]['messages'])}")
                except:
                    print(f"  Could not parse JSON")
    
    # Check composer.composerData in detail
    print("\n=== COMPOSER DATA DETAILED ===")
    cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
    row = cursor.fetchone()
    if row and row[0]:
        data = json.loads(row[0])
        print(f"Keys in composerData: {list(data.keys())}")
        
        # Check if messages are stored elsewhere
        for key in data.keys():
            if 'message' in key.lower() or 'store' in key.lower():
                print(f"\n{key}:")
                value = data[key]
                if isinstance(value, dict):
                    print(f"  Dict with {len(value)} entries")
                    # Show first entry
                    if value:
                        first_key = list(value.keys())[0]
                        print(f"  First key: {first_key}")
                        first_value = value[first_key]
                        if isinstance(first_value, list):
                            print(f"    List with {len(first_value)} items")
                            if first_value and isinstance(first_value[0], dict):
                                print(f"    First item keys: {list(first_value[0].keys())}")
                elif isinstance(value, list):
                    print(f"  List with {len(value)} items")
    
    conn.close()

if __name__ == "__main__":
    check_all_cursor_storage()