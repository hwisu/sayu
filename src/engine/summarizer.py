"""Summarization engine using external LLM commands."""

import os
import subprocess
from datetime import timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from openai import OpenAI
from ..core import Event


class LLMProvider(Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class Summarizer:
    """Summarize events using external LLM commands."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENROUTER):
        """Initialize summarizer with LLM provider."""
        self.provider = provider
        self.openrouter_client = None
        
        if provider == LLMProvider.OPENROUTER:
            api_key = os.getenv("SAYU_OPENROUTER_API_KEY")
            if api_key:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                )
    
    def summarize_timeframe(
        self,
        events: List[Event],
        timeframe: timedelta,
        command: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Summarize events within timeframes.
        
        Args:
            events: List of events to summarize
            timeframe: Duration of each timeframe
            command: Custom command to use for summarization
            
        Returns:
            List of summaries with timeframe info
        """
        if not events:
            return []
        
        # Sort events by timestamp (make all timezone-naive for comparison)
        def get_naive_timestamp(event):
            timestamp = event.timestamp
            if timestamp.tzinfo is not None:
                return timestamp.replace(tzinfo=None)
            return timestamp
        
        sorted_events = sorted(events, key=get_naive_timestamp)
        
        # Group events by timeframe
        timeframes = []
        current_frame = []
        frame_start = sorted_events[0].timestamp
        
        for event in sorted_events:
            # Make timestamps timezone-naive for comparison
            event_timestamp = event.timestamp
            if event_timestamp.tzinfo is not None:
                event_timestamp = event_timestamp.replace(tzinfo=None)
            
            if event_timestamp - frame_start <= timeframe:
                current_frame.append(event)
            else:
                if current_frame:
                    timeframes.append({
                        "start": frame_start,
                        "end": current_frame[-1].timestamp,
                        "events": current_frame
                    })
                current_frame = [event]
                frame_start = event_timestamp
        
        # Add last frame
        if current_frame:
            timeframes.append({
                "start": frame_start,
                "end": current_frame[-1].timestamp,
                "events": current_frame
            })
        
        # Summarize each timeframe
        summaries = []
        for frame in timeframes:
            summary = self._summarize_events(
                frame["events"],
                command=command
            )
            summaries.append({
                "start": frame["start"],
                "end": frame["end"],
                "event_count": len(frame["events"]),
                "summary": summary
            })
        
        return summaries
    
    def summarize_all(
        self,
        events: List[Event],
        command: Optional[str] = None
    ) -> str:
        """Summarize all events together."""
        return self._summarize_events(events, command=command)
    
    def _summarize_events(
        self,
        events: List[Event],
        command: Optional[str] = None
    ) -> str:
        """Summarize a list of events using LLM."""
        if not events:
            return "No events to summarize."
        
        # Prepare context
        context = self._prepare_context(events)
        
        # Use OpenRouter if configured
        if self.provider == LLMProvider.OPENROUTER and self.openrouter_client:
            return self._summarize_with_openrouter(context)
        
        # Build command for CLI-based providers
        if command:
            cmd = command.replace("{context}", context)
        else:
            cmd = self._get_default_command(context)
        
        # Execute command
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _prepare_context(self, events: List[Event]) -> str:
        """Prepare context from events for LLM."""
        lines = []
        
        for event in events:
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            source = event.source
            
            # Format based on event metadata
            if event.metadata.get("type") == "user":
                prefix = "User:"
            elif event.metadata.get("type") == "assistant":
                prefix = "Assistant:"
            else:
                prefix = f"{source}:"
            
            lines.append(f"[{timestamp}] {prefix} {event.content[:500]}")
        
        return "\\n".join(lines)
    
    def _summarize_with_openrouter(self, context: str) -> str:
        """Summarize using OpenRouter API."""
        try:
            model = os.getenv("SAYU_LLM_MODEL", "openai/gpt-4o-mini")
            
            completion = self.openrouter_client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/hwisu/sayu",
                    "X-Title": "Sayu - AI Conversation Tracker",
                },
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes work sessions. Provide concise, clear summaries focusing on what was accomplished."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this work session:\n\n{context}"
                    }
                ],
                max_tokens=500,
                temperature=0.7,
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            return f"Error using OpenRouter: {str(e)}"
    
    def _get_default_command(self, context: str) -> str:
        """Get default command for provider."""
        # Escape single quotes in context
        escaped_context = context.replace("'", "'\"'\"'")
        
        if self.provider == LLMProvider.CLAUDE:
            return f"claude -c 'Summarize this work session:\\n{escaped_context}'"
        elif self.provider == LLMProvider.GEMINI:
            return f"gemini -p 'Summarize this work session:\\n{escaped_context}'"
        elif self.provider == LLMProvider.OPENROUTER:
            return "echo 'OpenRouter provider requires API key'"
        else:
            return f"echo 'No default command for {self.provider}'"
