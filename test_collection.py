#!/usr/bin/env python3
"""Test the actual collection process for Claude and Cursor"""

import os
import time
from domain.collectors.manager import CollectorManager

# Set debug mode
os.environ['SAYU_DEBUG'] = '1'

def test_collection():
    """Test the collection process"""
    print("=== TESTING COLLECTION PROCESS ===")
    
    # Initialize collector manager
    manager = CollectorManager()
    
    # Check configuration
    print(f"\nConfiguration:")
    print(f"  Claude enabled: {manager.config.connectors.get('claude', False)}")
    print(f"  Cursor enabled: {manager.config.connectors.get('cursor', False)}")
    
    # Test health check first
    print("\n=== HEALTH CHECK ===")
    health = manager.health_check()
    for collector, status in health.items():
        print(f"\n{collector}:")
        print(f"  OK: {status.get('ok', False)}")
        print(f"  Reason: {status.get('reason', 'N/A')}")
        if 'conversations' in status:
            print(f"  Conversations: {status['conversations']}")
    
    # Test collection with a specific time range (last 24 hours)
    print("\n=== TESTING COLLECTION (LAST 24 HOURS) ===")
    
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (24 * 60 * 60 * 1000)  # 24 hours ago
    
    # Test Claude collector directly
    print("\n--- Claude Collector ---")
    claude_events = manager.claude_collector.pull_since(start_ms, now_ms, manager.config)
    print(f"Found {len(claude_events)} Claude events")
    if claude_events:
        print(f"First event:")
        print(f"  Time: {claude_events[0].ts}")
        print(f"  Actor: {claude_events[0].actor}")
        print(f"  Text preview: {claude_events[0].text[:100]}...")
    
    # Test Cursor collector directly
    print("\n--- Cursor Collector ---")
    cursor_events = manager.cursor_collector.pull_since(start_ms, now_ms, manager.config)
    print(f"Found {len(cursor_events)} Cursor events")
    
    # Test the main collection method
    print("\n=== TESTING MAIN COLLECTION METHOD ===")
    all_events = manager.collect_since_last_commit()
    print(f"Total events collected: {len(all_events)}")
    
    # Group by source
    by_source = {}
    for event in all_events:
        source = event.source.value
        by_source[source] = by_source.get(source, 0) + 1
    
    print("\nEvents by source:")
    for source, count in by_source.items():
        print(f"  {source}: {count}")

def check_config_file():
    """Check if config file exists and has correct settings"""
    print("\n=== CHECKING CONFIG FILE ===")
    
    config_files = [
        '.sayu/config.yaml',
        '.sayu.yaml',
        'sayu.yaml'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\nFound config file: {config_file}")
            with open(config_file, 'r') as f:
                content = f.read()
                print("Content:")
                print(content)
            break
    else:
        print("No config file found")

if __name__ == "__main__":
    check_config_file()
    test_collection()