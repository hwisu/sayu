#!/usr/bin/env python3
"""Find where Cursor actually stores its data"""

import os
from pathlib import Path

def find_cursor_data():
    """Search for Cursor data directories"""
    print("=== SEARCHING FOR CURSOR DATA ===")
    
    # Common Cursor locations on macOS
    potential_paths = [
        Path.home() / 'Library' / 'Application Support' / 'Cursor',
        Path.home() / 'Library' / 'Application Support' / 'cursor-ai',
        Path.home() / 'Library' / 'Application Support' / 'com.todesktop.230313mzl4w4u92',
        Path.home() / '.cursor',
        Path.home() / '.cursor-ai',
        Path.home() / '.config' / 'Cursor',
        Path.home() / '.config' / 'cursor',
    ]
    
    for path in potential_paths:
        if path.exists():
            print(f"\n✅ Found: {path}")
            
            # List subdirectories
            try:
                subdirs = [p for p in path.iterdir() if p.is_dir()]
                print(f"   Subdirectories: {len(subdirs)}")
                for subdir in subdirs[:10]:  # Show first 10
                    print(f"   - {subdir.name}")
                    
                    # Check for AI/conversation related subdirs
                    ai_related = ['ai', 'conversation', 'chat', 'history', 'logs', 'composer', 'aichat']
                    for ai_dir in ai_related:
                        check_path = subdir / ai_dir
                        if check_path.exists():
                            print(f"     ↳ Found {ai_dir}/")
                            # List some files
                            files = list(check_path.glob('*'))[:5]
                            for f in files:
                                print(f"       - {f.name}")
            except PermissionError:
                print(f"   Permission denied")
        else:
            print(f"❌ Not found: {path}")
    
    # Search for Cursor-related files in common directories
    print("\n=== SEARCHING FOR CURSOR FILES ===")
    
    # Search in Application Support
    app_support = Path.home() / 'Library' / 'Application Support'
    if app_support.exists():
        cursor_dirs = [p for p in app_support.iterdir() if 'cursor' in p.name.lower()]
        if cursor_dirs:
            print(f"\nFound {len(cursor_dirs)} Cursor-related directories in Application Support:")
            for d in cursor_dirs:
                print(f"  - {d.name}")
                
                # Look for AI/chat related files
                for pattern in ['*.json', '*.jsonl', '*.db', '*.sqlite']:
                    files = list(d.rglob(pattern))[:5]
                    if files:
                        print(f"    Found {pattern} files:")
                        for f in files:
                            rel_path = f.relative_to(d)
                            print(f"      - {rel_path}")

def search_for_ai_conversations():
    """Search for AI conversation files in Cursor directories"""
    print("\n=== SEARCHING FOR AI CONVERSATION FILES ===")
    
    cursor_dir = Path.home() / 'Library' / 'Application Support' / 'Cursor'
    if cursor_dir.exists():
        # Search for common AI conversation file patterns
        patterns = [
            '**/ai*.json',
            '**/chat*.json',
            '**/conversation*.json',
            '**/composer*.json',
            '**/*.jsonl',
            '**/history/*.json',
        ]
        
        for pattern in patterns:
            files = list(cursor_dir.glob(pattern))
            if files:
                print(f"\n{pattern}: Found {len(files)} files")
                for f in files[:5]:  # Show first 5
                    rel_path = f.relative_to(cursor_dir)
                    print(f"  - {rel_path} ({f.stat().st_size} bytes)")

if __name__ == "__main__":
    find_cursor_data()
    search_for_ai_conversations()