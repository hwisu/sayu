"""LLM API client for Sayu"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from shared.constants import LLMConstants
from shared.utils import ShellExecutor


class LLMApiClient:
    """LLM API client supporting Gemini, OpenAI, and Anthropic"""
    
    @classmethod
    def call_llm(cls, prompt: str) -> str:
        """Call LLM API with priority order: Gemini -> OpenAI -> Anthropic"""
        if os.getenv('GEMINI_API_KEY'):
            return cls._call_gemini(prompt)
        elif os.getenv('OPENAI_API_KEY'):
            return cls._call_openai(prompt)
        elif os.getenv('ANTHROPIC_API_KEY'):
            return cls._call_anthropic(prompt)
        
        raise ValueError('No LLM API key found')
    
    @classmethod
    def get_available_apis(cls) -> Dict[str, bool]:
        """Get available API keys"""
        return {
            'gemini': bool(os.getenv('GEMINI_API_KEY')),
            'openai': bool(os.getenv('OPENAI_API_KEY')),
            'anthropic': bool(os.getenv('ANTHROPIC_API_KEY'))
        }
    
    @classmethod
    def generate_summary(
        cls, 
        repo_root: str, 
        staged_files: List[str], 
        diff_stats: Dict[str, Any], 
        language: str = 'ko'
    ) -> Optional[str]:
        """Generate AI summary for commit context"""
        try:
            # Import i18n here to avoid circular imports
            from i18n import i18n
            
            # Build prompt using i18n templates
            i18n_manager = i18n()
            i18n_manager.set_language(language)
            
            # Get file list string
            files_str = ', '.join(staged_files[:10])
            if len(staged_files) > 10:
                files_str += f' and {len(staged_files) - 10} more files'
            
            # Create simple prompt for commit summary
            prompt = f"""Analyze the following code changes and provide a brief summary in {language}:

Files changed: {files_str}
Changes: +{diff_stats['additions']} -{diff_stats['deletions']} lines

Please provide a concise summary of what was changed and why, in {language}.
Format the response as a brief description suitable for a git commit message trailer.
"""
            
            # Call LLM
            response = cls.call_llm(prompt)
            
            # Clean and validate response
            if response and len(response.strip()) > 10:
                return response.strip()
            
            return None
            
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Summary generation error: {e}")
            return None
    
    @classmethod
    def _call_gemini(cls, prompt: str) -> str:
        """Call Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError('GEMINI_API_KEY not found in environment')
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": LLMConstants.TEMPERATURE,
                "maxOutputTokens": LLMConstants.MAX_OUTPUT_TOKENS,
                "candidateCount": 1,
                "responseMimeType": "application/json"
            }
        }
        
        # Use temporary file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file = f.name
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                '-H', 'Content-Type: application/json',
                '-d', f'@{temp_file}',
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
            ]
            
            result = ShellExecutor.run(cmd, check=True)
            response = json.loads(result.stdout)
            
            if response.get('candidates') and response['candidates'][0]:
                content = response['candidates'][0].get('content')
                if content and content.get('parts') and content['parts'][0]:
                    return content['parts'][0]['text'].strip()
            
            raise ValueError('Invalid Gemini response structure')
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    @classmethod
    def _call_openai(cls, prompt: str) -> str:
        """Call OpenAI API"""
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError('OPENAI_API_KEY not found in environment')
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": LLMConstants.OPENAI_MAX_TOKENS,
            "temperature": LLMConstants.OPENAI_TEMPERATURE
        }
        
        # Use temporary file for payload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file = f.name
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                'https://api.openai.com/v1/chat/completions',
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Bearer {api_key}',
                '-d', f'@{temp_file}'
            ]
            
            result = ShellExecutor.run(cmd, check=True)
            response = json.loads(result.stdout)
            
            if response.get('choices') and response['choices'][0]:
                return response['choices'][0]['message']['content'].strip()
            
            raise ValueError('Invalid OpenAI response')
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    @classmethod
    def _call_anthropic(cls, prompt: str) -> str:
        """Call Anthropic API"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            raise ValueError('ANTHROPIC_API_KEY not found in environment')
        
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": LLMConstants.ANTHROPIC_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": LLMConstants.ANTHROPIC_TEMPERATURE
        }
        
        # Use temporary file for payload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file = f.name
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                'https://api.anthropic.com/v1/messages',
                '-H', 'Content-Type: application/json',
                '-H', f'x-api-key: {api_key}',
                '-H', 'anthropic-version: 2023-06-01',
                '-d', f'@{temp_file}'
            ]
            
            result = ShellExecutor.run(cmd, check=True)
            response = json.loads(result.stdout)
            
            if response.get('content') and response['content'][0]:
                return response['content'][0]['text'].strip()
            
            raise ValueError('Invalid Anthropic response')
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
