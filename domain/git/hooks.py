"""Git hook management for Sayu"""

import os
import subprocess
from pathlib import Path
from typing import Optional


class GitHookManager:
    """Manage Git hooks installation and configuration"""
    
    HOOK_NAMES = ['commit-msg', 'post-commit']
    
    def __init__(self, repo_root: str):
        """Initialize hook manager for repository"""
        self.repo_root = Path(repo_root)
        self.hooks_dir = self.repo_root / '.git' / 'hooks'
    
    def install(self):
        """Install all Sayu hooks"""
        if not self.hooks_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_root}")
        
        for hook_name in self.HOOK_NAMES:
            self._install_hook(hook_name)
    
    def _install_hook(self, hook_name: str):
        """Install a specific hook"""
        hook_path = self.hooks_dir / hook_name
        
        # Create hook script
        hook_content = f"""#!/bin/sh
# Sayu Git Hook - {hook_name}
# Auto-generated, do not edit

# Run Sayu hook handler
if command -v sayu >/dev/null 2>&1; then
    sayu hook {hook_name} "$@"
fi

# Always exit 0 to avoid blocking commits (fail-open)
exit 0
"""
        
        # Write hook file
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        # Make executable
        os.chmod(hook_path, 0o755)
        
        print(f"Installed {hook_name} hook")
    
    def uninstall(self):
        """Remove all Sayu hooks"""
        for hook_name in self.HOOK_NAMES:
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                # Check if it's our hook
                with open(hook_path) as f:
                    if 'Sayu Git Hook' in f.read():
                        hook_path.unlink()
                        print(f"Removed {hook_name} hook")
    
    def check_installed(self) -> bool:
        """Check if hooks are installed"""
        for hook_name in self.HOOK_NAMES:
            hook_path = self.hooks_dir / hook_name
            if not hook_path.exists():
                return False
            
            with open(hook_path) as f:
                if 'Sayu Git Hook' not in f.read():
                    return False
        
        return True
    
    @staticmethod
    def get_repo_root() -> Optional[str]:
        """Get repository root from git"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None