#!/usr/bin/env python3
"""Performance test for Sayu collectors"""

import time
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domain.collectors.manager import CollectorManager
from infra.api.llm import LLMApiClient
from infra.api.llm_optimized import OptimizedLLMApiClient


def time_collector_sequential():
    """Test sequential collector execution"""
    print("\n=== Testing Sequential Collectors ===")
    
    manager = CollectorManager()
    
    # Temporarily disable parallel execution for comparison
    start = time.time()
    
    # Simulate sequential collection
    now_ms = int(time.time() * 1000)
    start_time = now_ms - (24 * 60 * 60 * 1000)
    
    events = []
    
    # Git collector
    t1 = time.time()
    try:
        git_events = manager.git_collector.pull_since(start_time, now_ms, manager.config)
        events.extend(git_events)
    except:
        pass
    print(f"Git collector: {time.time() - t1:.2f}s")
    
    # CLI collector
    t1 = time.time()
    try:
        cli_events = manager.cli_collector.pull_since(start_time, now_ms, manager.config)
        events.extend(cli_events)
    except:
        pass
    print(f"CLI collector: {time.time() - t1:.2f}s")
    
    # Cursor collector
    if manager.config.connectors.get('cursor', False):
        t1 = time.time()
        try:
            cursor_events = manager.cursor_collector.pull_since(start_time, now_ms, manager.config)
            events.extend(cursor_events)
        except:
            pass
        print(f"Cursor collector: {time.time() - t1:.2f}s")
    
    # Claude collector
    if manager.config.connectors.get('claude', False):
        t1 = time.time()
        try:
            claude_events = manager.claude_collector.pull_since(start_time, now_ms, manager.config)
            events.extend(claude_events)
        except:
            pass
        print(f"Claude collector: {time.time() - t1:.2f}s")
    
    total_time = time.time() - start
    print(f"\nTotal sequential time: {total_time:.2f}s")
    print(f"Total events collected: {len(events)}")
    
    return total_time


def time_collector_parallel():
    """Test parallel collector execution"""
    print("\n=== Testing Parallel Collectors ===")
    
    manager = CollectorManager()
    
    start = time.time()
    events = manager.collect_since_last_commit()
    total_time = time.time() - start
    
    print(f"\nTotal parallel time: {total_time:.2f}s")
    print(f"Total events collected: {len(events)}")
    
    return total_time


def test_llm_performance():
    """Test LLM API performance"""
    print("\n=== Testing LLM API Performance ===")
    
    test_prompt = "Test prompt for performance measurement. What is 2+2?"
    
    # Test old implementation (if available)
    if hasattr(LLMApiClient, 'call_llm'):
        print("\nTesting original LLM client:")
        start = time.time()
        try:
            response = LLMApiClient.call_llm(test_prompt)
            print(f"Time: {time.time() - start:.2f}s")
            print(f"Response length: {len(response)} chars")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test optimized implementation
    print("\nTesting optimized LLM client:")
    
    # First call (no cache)
    start = time.time()
    try:
        response = OptimizedLLMApiClient.call_llm(test_prompt, use_cache=False)
        first_call_time = time.time() - start
        print(f"First call (no cache): {first_call_time:.2f}s")
    except Exception as e:
        print(f"Error: {e}")
        first_call_time = None
    
    # Second call (with cache)
    if first_call_time:
        start = time.time()
        response = OptimizedLLMApiClient.call_llm(test_prompt, use_cache=True)
        cached_time = time.time() - start
        print(f"Cached call: {cached_time:.2f}s")
        print(f"Speedup: {first_call_time / cached_time:.1f}x")


def test_cache_performance():
    """Test cache performance"""
    print("\n=== Testing Cache Performance ===")
    
    from infra.cache.manager import CacheManager
    
    cache = CacheManager(os.getcwd())
    
    # Test write performance
    start = time.time()
    for i in range(100):
        cache.set(f"test_key_{i}", {"data": f"value_{i}", "timestamp": time.time()})
    write_time = time.time() - start
    print(f"Write 100 items: {write_time:.3f}s ({write_time/100*1000:.1f}ms per item)")
    
    # Test read performance
    start = time.time()
    for i in range(100):
        value = cache.get(f"test_key_{i}")
    read_time = time.time() - start
    print(f"Read 100 items: {read_time:.3f}s ({read_time/100*1000:.1f}ms per item)")
    
    # Cleanup
    cache.clear()


def main():
    """Run all performance tests"""
    print("Sayu Performance Test")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test collectors
    seq_time = time_collector_sequential()
    par_time = time_collector_parallel()
    
    if seq_time and par_time:
        speedup = seq_time / par_time
        print(f"\n=== Collector Performance Summary ===")
        print(f"Sequential: {seq_time:.2f}s")
        print(f"Parallel: {par_time:.2f}s")
        print(f"Speedup: {speedup:.2f}x")
    
    # Test LLM
    test_llm_performance()
    
    # Test cache
    test_cache_performance()
    
    print("\n" + "=" * 50)
    print("Performance test completed")


if __name__ == "__main__":
    main()