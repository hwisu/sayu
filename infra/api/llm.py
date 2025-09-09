"""LLM API client for Sayu"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from shared.constants import (
    LLM_TEMPERATURE, LLM_MAX_OUTPUT_TOKENS
)
from shared.utils import ShellExecutor


class LLMApiClient:
    """LLM API client supporting Gemini only"""
    
    @classmethod
    def call_llm(cls, prompt: str) -> str:
        """Call LLM API (Gemini only)"""
        if os.getenv('GEMINI_API_KEY'):
            return cls._call_gemini(prompt)
        
        raise ValueError('GEMINI_API_KEY not found')
    
    @classmethod
    def get_available_apis(cls) -> Dict[str, bool]:
        """Get available API keys"""
        return {
            'gemini': bool(os.getenv('GEMINI_API_KEY'))
        }
    
    
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
                "temperature": LLM_TEMPERATURE,
                "maxOutputTokens": LLM_MAX_OUTPUT_TOKENS,
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
                '-H', f'x-goog-api-key: {api_key}',
                '-d', f'@{temp_file}',
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
            ]
            
            result = ShellExecutor.run(cmd, ccheck=True)
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
