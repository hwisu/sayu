"""Safe shell command executor for Sayu"""

import re
import subprocess
from typing import List, Dict, Any, Optional, Union


class ShellExecutor:
    """Safely execute shell commands with proper validation and escaping"""
    
    @staticmethod
    def run(
        command: Union[str, List[str]], 
        **kwargs
    ) -> subprocess.CompletedProcess:
        """Execute command safely using subprocess.run"""
        # Default options for safety
        defaults = {
            'capture_output': True,
            'text': True,
            'check': False,
            'shell': False  # Never use shell by default
        }
        defaults.update(kwargs)
        
        # Convert string command to list if needed
        if isinstance(command, str):
            command = command.split()
        
        # Validate command
        ShellExecutor._validate_command(command[0])
        
        return subprocess.run(command, **defaults)
    
    @staticmethod
    def git_exec(args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Execute git commands safely"""
        # Git commands are executed without shell
        command = ['git'] + args
        
        defaults = {
            'capture_output': True,
            'text': True,
            'check': True,
            'shell': False
        }
        defaults.update(kwargs)
        
        return subprocess.run(command, **defaults)
    
    @staticmethod
    def run_sync(command: Union[str, List[str]], **kwargs) -> str:
        """Execute command synchronously and return stdout"""
        result = ShellExecutor.run(command, **kwargs)
        
        if result.returncode != 0 and kwargs.get('check', False):
            raise subprocess.CalledProcessError(
                result.returncode, 
                command, 
                result.stdout, 
                result.stderr
            )
        
        return result.stdout
    
    @staticmethod
    async def run_async(command: Union[str, List[str]], **kwargs) -> str:
        """Execute command asynchronously"""
        import asyncio
        
        # Convert string command to list if needed
        if isinstance(command, str):
            command = command.split()
        
        # Validate command
        ShellExecutor._validate_command(command[0])
        
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0 and kwargs.get('check', False):
            raise subprocess.CalledProcessError(
                proc.returncode, command, stdout, stderr
            )
        
        return stdout.decode() if stdout else ''
    
    @staticmethod
    def escape_shell_arg(arg: str) -> str:
        """Escape shell arguments to prevent injection"""
        if not arg:
            return "''"
        
        # Remove any existing quotes
        arg = re.sub(r'["\']', '', arg)
        
        # Escape special characters
        arg = re.sub(r'([\\$`!])', r'\\\1', arg)
        
        # Wrap in single quotes
        return f"'{arg}'"
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """Validate and sanitize file paths"""
        # Remove any attempts at path traversal
        path = re.sub(r'\.\.', '', path)
        
        # Remove any shell metacharacters
        path = re.sub(r'[;&|<>$`\\]', '', path)
        
        return path
    
    @staticmethod
    def _validate_command(command: str) -> None:
        """Validate command to prevent path traversal and injection"""
        if '..' in command or '/' in command:
            raise ValueError(f"Invalid command: {command}")
        
        # Check for dangerous characters
        dangerous_chars = ['&', ';', '|', '<', '>', '$', '`', '\\']
        if any(char in command for char in dangerous_chars):
            raise ValueError(f"Command contains dangerous characters: {command}")
    
    @staticmethod
    def check_command_exists(command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            result = subprocess.run(
                ['which', command], 
                capture_output=True, 
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
