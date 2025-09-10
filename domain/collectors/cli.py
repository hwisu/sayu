"""CLI collector for tracking shell commands"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

from domain.events.types import Event, EventSource, EventKind, Actor


class CliCollector:
    """Collect CLI commands from shell history"""
    
    id = 'cli.shell'
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize CLI collector"""
        self.repo_root = repo_root or os.getcwd()
        self.log_path = Path.home() / '.sayu' / 'cli.jsonl'
        
        # Create log directory if needed
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def discover(self, repo_root: str) -> bool:
        """Check if zsh hook is installed"""
        hook_path = self._get_hook_path()
        return hook_path.exists()
    
    def pull_since(self, since_ms: int, until_ms: int, cfg: Any) -> List[Event]:
        """Pull CLI events within time range"""
        events = []
        
        if not self.log_path.exists():
            return events
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        
                        # Check time range
                        if entry['ts'] < since_ms or entry['ts'] > until_ms:
                            continue
                        
                        # Only commands from current repo or subdirectories
                        if not self._is_repo_related(entry['cwd']):
                            continue
                        
                        events.append(self._entry_to_event(entry))
                    except (json.JSONDecodeError, KeyError):
                        # Skip invalid JSON lines
                        continue
        except Exception as e:
            print(f"CLI log read error: {e}")
        
        return events
    
    def health(self) -> Dict[str, Any]:
        """Health check for CLI collector"""
        hook_path = self._get_hook_path()
        
        if not hook_path.exists():
            return {'ok': False, 'reason': 'zsh hook not installed'}
        
        # Check recent logs
        if not self.log_path.exists():
            return {'ok': False, 'reason': 'no CLI logs found'}
        
        try:
            stats = self.log_path.stat()
            day_ago = 24 * 60 * 60  # seconds
            
            if (stats.st_mtime + day_ago) < time.time():
                return {'ok': False, 'reason': 'CLI logs too old'}
            
            return {'ok': True}
        except Exception:
            return {'ok': False, 'reason': 'unable to check CLI logs'}
    
    def redact(self, event: Event, cfg: Any) -> Event:
        """Redact sensitive information from CLI event"""
        # For CLI events, we primarily redact the text field
        text = event.text
        
        # No privacy masking in simplified version
        
        # Create new event with redacted text
        return Event(
            id=event.id,
            ts=event.ts,
            source=event.source,
            kind=event.kind,
            repo=event.repo,
            cwd=event.cwd,
            file=event.file,
            range=event.range,
            actor=event.actor,
            text=text,
            url=event.url,
            meta=event.meta
        )
    
    def install_hook(self):
        """Install zsh CLI tracking hook"""
        hook_path = self._get_hook_path()
        hook_dir = hook_path.parent
        
        # Create hook directory
        hook_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and write hook script
        hook_content = self._generate_hook_script()
        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(hook_content)
        
        # Update .zshrc
        self._update_zshrc()
    
    def uninstall_hook(self):
        """Uninstall zsh CLI tracking hook"""
        hook_path = self._get_hook_path()
        
        if hook_path.exists():
            hook_path.unlink()
        
        # TODO: Remove source line from .zshrc
    
    def _get_hook_path(self) -> Path:
        """Get path to zsh hook script"""
        return Path.home() / '.sayu' / 'zsh-hook.zsh'
    
    def _generate_hook_script(self) -> str:
        """Generate zsh hook script content"""
        log_path = str(self.log_path)
        
        # Use format string to avoid complex escaping
        script = '''#!/bin/zsh
# Sayu CLI tracking hooks

# Safe sayu preexec hook
sayu_preexec() {{
  export SAYU_CMD_START=$(date +%s)
  export SAYU_CMD="$1"
}}

# Safe sayu precmd hook  
sayu_precmd() {{
  local exit_code=$?
  
  if [[ -n "$SAYU_CMD" && -n "$SAYU_CMD_START" ]]; then
    local end_time=$(date +%s)
    local duration=$((end_time - SAYU_CMD_START))
    local cwd="$PWD"
    local ts_ms=$((end_time * 1000))
    
    # JSON escape handling (safely)
    local cmd_safe=${{SAYU_CMD//"/\\"}}
    cmd_safe=${{cmd_safe//\\/\\\\}}
    local cwd_safe=${{cwd//"/\\"}}
    cwd_safe=${{cwd_safe//\\/\\\\}}
    
    # Create log entry
    local log_entry="{{\\"ts\\":$ts_ms,\\"cmd\\":\\"$cmd_safe\\",\\"exitCode\\":$exit_code,\\"duration\\":$duration,\\"cwd\\":\\"$cwd_safe\\"}}"
    
    # Safely append to log file (synchronously, no job control messages)
    echo "$log_entry" >> "{log_path}" 2>/dev/null || true
    
    unset SAYU_CMD SAYU_CMD_START
  fi
}}

# Register zsh hooks (safely)
autoload -U add-zsh-hook
add-zsh-hook preexec sayu_preexec
add-zsh-hook precmd sayu_precmd
'''
        return script.format(log_path=log_path)
    
    def _update_zshrc(self):
        """Update .zshrc to source the hook script"""
        zshrc_path = Path.home() / '.zshrc'
        hook_path = self._get_hook_path()
        source_line = f'# Sayu CLI tracking\nsource "{hook_path}"\n'
        
        # Create .zshrc if it doesn't exist
        if not zshrc_path.exists():
            with open(zshrc_path, 'w', encoding='utf-8') as f:
                f.write(source_line)
            return
        
        # Check if already added
        with open(zshrc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if str(hook_path) in content:
            return  # Already installed
        
        # Append to .zshrc
        with open(zshrc_path, 'a', encoding='utf-8') as f:
            f.write('\n' + source_line)
    
    def _is_repo_related(self, cmd_cwd: str) -> bool:
        """Check if command was run in current repo or subdirectory"""
        return cmd_cwd.startswith(self.repo_root)
    
    def _entry_to_event(self, entry: Dict[str, Any]) -> Event:
        """Convert log entry to Event object"""
        # Categorize command type
        kind = self._categorize_command(entry['cmd'])
        
        return Event(
            id=str(uuid.uuid4()),
            ts=entry['ts'],
            source=EventSource.CLI,
            kind=kind,
            repo=self.repo_root,
            cwd=entry['cwd'],
            file=None,
            range=None,
            actor=Actor.USER,
            text=entry['cmd'],
            url=None,
            meta={
                'exitCode': entry['exitCode'],
                'duration': entry['duration'],
                'success': entry['exitCode'] == 0
            }
        )
    
    def _categorize_command(self, cmd: str) -> EventKind:
        """Categorize command type"""
        command = cmd.strip().split(' ')[0].lower()
        
        # Test related
        test_patterns = ['npm test', 'yarn test', 'jest', 'pytest', 'go test', 'cargo test']
        if any(test in cmd for test in test_patterns):
            return EventKind.TEST
        
        # Build related
        build_patterns = ['npm run build', 'yarn build', 'make', 'cargo build', 'go build']
        if any(build in cmd for build in build_patterns):
            return EventKind.RUN
        
        # Git related
        if command == 'git':
            return EventKind.RUN
        
        # Benchmark/performance
        bench_patterns = ['benchmark', 'bench', 'perf']
        if any(bench in cmd for bench in bench_patterns):
            return EventKind.BENCH
        
        # Error cases
        if 'error' in cmd or 'failed' in cmd:
            return EventKind.ERROR
        
        # Default
        return EventKind.RUN
