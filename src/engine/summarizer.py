"""Summarization engine using external LLM commands."""

import os
import subprocess
from datetime import timedelta
from enum import Enum
from typing import Any

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
        events: list[Event],
        timeframe: timedelta,
        command: str | None = None,
        structured: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Summarize events within timeframes.

        Args:
            events: List of events to summarize
            timeframe: Duration of each timeframe
            command: Custom command to use for summarization
            structured: Use structured output format if available

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
                    timeframes.append(
                        {
                            "start": frame_start,
                            "end": current_frame[-1].timestamp,
                            "events": current_frame,
                        }
                    )
                current_frame = [event]
                frame_start = event_timestamp

        # Add last frame
        if current_frame:
            timeframes.append(
                {
                    "start": frame_start,
                    "end": current_frame[-1].timestamp,
                    "events": current_frame,
                }
            )

        # Summarize each timeframe
        summaries = []
        for frame in timeframes:
            summary = self._summarize_events(
                frame["events"], command=command, structured=structured
            )
            summaries.append(
                {
                    "start": frame["start"],
                    "end": frame["end"],
                    "event_count": len(frame["events"]),
                    "summary": summary,
                }
            )

        return summaries

    def summarize_all(
        self,
        events: list[Event],
        command: str | None = None,
        structured: bool = False,
    ) -> str:
        """Summarize all events together."""
        return self._summarize_events(events, command=command, structured=structured)

    def _summarize_events(
        self,
        events: list[Event],
        command: str | None = None,
        structured: bool = False,
    ) -> str:
        """Summarize a list of events using LLM."""
        if not events:
            return "No events to summarize."

        # Prepare context
        context = self._prepare_context(events)

        # Use OpenRouter if configured
        if self.provider == LLMProvider.OPENROUTER and self.openrouter_client:
            return self._summarize_with_openrouter(context, structured=structured)

        # Build command for CLI-based providers
        if command:
            cmd = command.replace("{context}", context)
        else:
            cmd = self._get_default_command(context)

        # Execute command
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    def _prepare_context(self, events: list[Event]) -> str:
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

    def _summarize_with_openrouter(self, context: str, structured: bool = False) -> str:
        """Summarize using OpenRouter API."""
        try:
            model = os.getenv("SAYU_LLM_MODEL", "openai/gpt-4o-mini")

            # Check if we should use structured output
            use_structured = (
                structured
                and os.getenv("SAYU_STRUCTURED_OUTPUT", "false").lower() == "true"
            )

            if use_structured:
                # Use structured output with simpler schema
                completion = self.openrouter_client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://github.com/hwisu/sayu",
                        "X-Title": "Sayu - AI Conversation Tracker",
                    },
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Summarize work sessions in JSON format with: title (brief), tasks (3 items max with ✅/🔄/❌ prefix), summary (2-3 sentences).",
                        },
                        {
                            "role": "user",
                            "content": f"Summarize this session (max 3 tasks):\n\n{context}",
                        },
                    ],
                    max_tokens=500,  # Enough for git commit message
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

                # Get the response
                import json

                response_message = completion.choices[0].message

                # Try to parse JSON from content if parsed is not available
                if hasattr(response_message, "parsed") and response_message.parsed:
                    result = response_message.parsed
                else:
                    # Try to parse from content
                    try:
                        result = json.loads(response_message.content)
                    except Exception:
                        # Return raw content if not JSON
                        return response_message.content

                # Format structured output as readable text
                if result:
                    lines = []
                    lines.append(f"**{result.get('title', 'Session Summary')}**\n")

                    if result.get("tasks"):
                        lines.append("**Main Tasks:**")
                        for task in result["tasks"][:3]:  # Limit to 3 tasks
                            lines.append(f"  {task}")

                    if result.get("summary"):
                        lines.append(f"\n{result['summary']}")

                    return "\n".join(lines)
                else:
                    return response_message.content
            else:
                # Regular unstructured output
                completion = self.openrouter_client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://github.com/hwisu/sayu",
                        "X-Title": "Sayu - AI Conversation Tracker",
                    },
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that summarizes work sessions concisely. Focus on what was accomplished.",
                        },
                        {
                            "role": "user",
                            "content": f"Create a brief summary (2-3 lines) for this work session:\n\n{context}",
                        },
                    ],
                    max_tokens=500,
                    temperature=0.7,
                )

                if completion and completion.choices and len(completion.choices) > 0:
                    result = completion.choices[0].message.content
                    if result:
                        return result

                return "Summary generation failed"

        except Exception as e:
            import traceback

            return f"Error using OpenRouter: {str(e)}\n{traceback.format_exc()}"

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
