"""Minimal summary generator for fallback cases"""

from typing import List

from domain.events.types import Event
from shared.constants import MAX_FILE_DISPLAY


class MinimalSummaryGenerator:
    """Generate minimal summaries when LLM is unavailable"""
    
    @staticmethod
    def generate(llm_events: List[Event], staged_files: List[str], diff_stats: str) -> str:
        """Generate minimal summary"""
        lines = []
        lines.append('---')
        lines.append('Thought---')
        
        # File information
        if staged_files:
            file_list = ', '.join(staged_files[:MAX_FILE_DISPLAY])
            more = f" (+{len(staged_files) - MAX_FILE_DISPLAY} more)" if len(staged_files) > MAX_FILE_DISPLAY else ""
            lines.append(f"Files: {file_list}{more}")
        
        # Event information
        if llm_events:
            # Extract tools from meta
            tools = set()
            for event in llm_events:
                if event.meta and 'tool' in event.meta:
                    tools.add(event.meta['tool'])
            
            tool_list = ', '.join(tools) if tools else 'unknown'
            lines.append(f"Events: {len(llm_events)} LLM interactions ({tool_list})")
        else:
            lines.append("Events: Code changes only")
        
        lines.append('---')
        
        return '\n'.join(lines)
