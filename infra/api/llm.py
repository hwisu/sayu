"""LLM API client for Sayu using httpx with caching"""

import hashlib
import os
import time
from typing import Dict, Any, Optional, Tuple

import httpx

from shared.constants import (
    LLM_TEMPERATURE, LLM_MAX_OUTPUT_TOKENS
)


class LLMApiClient:
    """LLM API client with httpx and caching"""
    
    # Simple in-memory cache for API responses
    _cache: Dict[str, Tuple[str, float]] = {}
    CACHE_TTL = 600  # 10 minutes - longer cache for better performance
    
    @classmethod
    def call_llm(cls, prompt: str, use_cache: bool = True) -> str:
        """Call LLM API (Gemini only)"""
        # Check cache first
        if use_cache:
            cached_response = cls._get_cached(prompt)
            if cached_response:
                return cached_response
        
        # Make API call
        if not os.getenv('SAYU_GEMINI_API_KEY'):
            raise ValueError('SAYU_GEMINI_API_KEY not found')
        
        response = cls._call_gemini(prompt)
        
        # Cache the response
        if use_cache and response:
            cls._set_cache(prompt, response)
        
        return response
    
    @classmethod
    def _get_cached(cls, prompt: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        cache_key = cls._generate_cache_key(prompt)
        if cache_key in cls._cache:
            response, timestamp = cls._cache[cache_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                if os.getenv('SAYU_DEBUG'):
                    print("Using cached LLM response")
                return response
        return None
    
    @classmethod
    def _set_cache(cls, prompt: str, response: str) -> None:
        """Cache a response"""
        cache_key = cls._generate_cache_key(prompt)
        cls._cache[cache_key] = (response, time.time())
    
    @classmethod
    def _generate_cache_key(cls, prompt: str) -> str:
        """Generate stable cache key using MD5 hash"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    @classmethod
    def _call_gemini(cls, prompt: str) -> str:
        """Call Gemini API using httpx"""
        api_key = os.getenv('SAYU_GEMINI_API_KEY')
        if not api_key:
            raise ValueError('SAYU_GEMINI_API_KEY not found in environment')
        
        # Log prompt size
        print(f"[Sayu] Sending prompt to LLM (length: {len(prompt)} chars)")
        if os.getenv('SAYU_DEBUG'):
            print(f"[DEBUG] First 500 chars of prompt: {prompt[:500]}...")
        
        # Use faster model if available
        model = os.getenv('SAYU_GEMINI_MODEL', 'gemini-2.5-flash')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        
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
                "responseMimeType": "application/json",
                "topP": 0.8,
                "topK": 20
            }
        }
        
        headers = {
            'x-goog-api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        with httpx.Client(timeout=30.0) as client:  # Increased timeout for LLM responses
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Debug logging to see the actual response structure
            if os.getenv('SAYU_DEBUG'):
                import json
                print(f"[DEBUG] Gemini response: {json.dumps(data, indent=2)[:500]}...")
            
            if data.get('candidates') and data['candidates'][0]:
                candidate = data['candidates'][0]
                
                # Check if the model hit token limit or other issues
                finish_reason = candidate.get('finishReason', '')
                if finish_reason == 'MAX_TOKENS':
                    # Return empty response when hitting token limit
                    return ''
                
                content = candidate.get('content')
                if content and content.get('parts'):
                    # Handle both list and single part responses
                    parts = content['parts']
                    if isinstance(parts, list) and parts:
                        text = parts[0].get('text', '')
                        if text:
                            return text.strip()
                    
                    # If no text in parts but model responded, return empty
                    return ''
            
            # More detailed error with response structure
            import json
            error_msg = f'Invalid Gemini response structure. Response: {json.dumps(data, indent=2)[:500]}...'
            raise ValueError(error_msg)
    
    
    
    @classmethod
    def get_available_apis(cls) -> Dict[str, bool]:
        """Get available API keys"""
        return {
            'gemini': bool(os.getenv('SAYU_GEMINI_API_KEY'))
        }
