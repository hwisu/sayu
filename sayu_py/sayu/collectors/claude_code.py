"""Claude Code hook collector."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core import Collector, Event, EventType


class ClaudeCodeCollector(Collector):
    """Collector for Claude Code conversations via hooks."""
    
    def __init__(self, hook_dir: Optional[Path] = None):
        """
        Initialize collector.
        
        Args:
            hook_dir: Directory to store hook scripts
        """
        self.hook_dir = hook_dir or Path.home() / ".sayu" / "hooks"
        self.event_file = self.hook_dir / "events.jsonl"
        
    def setup(self) -> None:
        """Set up Claude Code hooks."""
        self.hook_dir.mkdir(parents=True, exist_ok=True)
        
        # Create hook script
        hook_script = self.hook_dir / "claude_code_hook.py"
        hook_script.write_text(self._get_hook_script())
        hook_script.chmod(0o755)
        
        # Create .claude/settings.json in home directory for user-level hooks
        settings_dir = Path.home() / ".claude"
        settings_dir.mkdir(exist_ok=True)
        settings_path = settings_dir / "settings.json"
        
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": str(hook_script)
                            }
                        ]
                    }
                ],
                "Stop": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": str(hook_script)
                            }
                        ]
                    }
                ]
            }
        }
        
        if settings_path.exists():
            # Merge with existing settings
            existing = json.loads(settings_path.read_text())
            existing.setdefault("hooks", {}).update(settings["hooks"])
            settings = existing
        
        settings_path.write_text(json.dumps(settings, indent=2))
        
    def teardown(self) -> None:
        """Remove Claude Code hooks."""
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            if "hooks" in settings:
                settings["hooks"].pop("UserPromptSubmit", None)
                settings["hooks"].pop("Stop", None)
                if not settings["hooks"]:
                    del settings["hooks"]
            
            if settings:
                settings_path.write_text(json.dumps(settings, indent=2))
            else:
                settings_path.unlink()
    
    def collect(self, since: Optional[datetime] = None) -> List[Event]:
        """Collect events from Claude Code hooks."""
        if not self.event_file.exists():
            return []
        
        events = []
        with open(self.event_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    
                    if since and timestamp <= since:
                        continue
                    
                    event = Event(
                        timestamp=timestamp,
                        type=EventType.CONVERSATION,
                        source=self.name,
                        content=data["content"],
                        metadata=data.get("metadata", {})
                    )
                    events.append(event)
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    continue
        
        return events
    
    @property
    def name(self) -> str:
        """Return collector name."""
        return "claude-code"
    
    def _get_hook_script(self) -> str:
        """Generate hook script content."""
        return f'''#!/usr/bin/env python3
"""Claude Code hook script for Sayu."""

import json
import sys
from datetime import datetime
from pathlib import Path

def main():
    # Read hook data from stdin
    try:
        hook_data = json.loads(sys.stdin.read())
    except:
        return
    
    # Extract hook event type
    hook_event = hook_data.get("hook_event_name", "")
    
    # Process based on hook type
    if hook_event == "UserPromptSubmit":
        # Extract user prompt from the data
        content = hook_data.get("prompt", "")
        metadata = {{"type": "user", "hook": hook_event}}
    elif hook_event == "Stop":
        # Extract assistant response - need to read from transcript
        transcript_path = hook_data.get("transcript_path", "")
        if transcript_path and Path(transcript_path).exists():
            # Read last assistant message from transcript
            with open(transcript_path, "r") as f:
                transcript = f.read()
                # Simple extraction - find last Assistant: block
                if "Assistant:" in transcript:
                    content = transcript.split("Assistant:")[-1].strip()
                    content = content.split("Human:")[0].strip() if "Human:" in content else content
                else:
                    return
        else:
            return
        metadata = {{"type": "assistant", "hook": hook_event}}
    else:
        return
    
    # Create event
    event = {{
        "timestamp": datetime.now().isoformat(),
        "content": content[:1000],  # Limit content length
        "metadata": metadata
    }}
    
    # Append to events file
    event_file = Path("{self.event_file}")
    event_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(event_file, "a") as f:
        f.write(json.dumps(event) + "\\n")

if __name__ == "__main__":
    main()
'''