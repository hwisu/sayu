"""LLM API client for Sayu using httpx with caching"""

import hashlib
import json
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
    CACHE_TTL = 300  # 5 minutes
    
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
        
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
        
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
        
        headers = {
            'x-goog-api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('candidates') and data['candidates'][0]:
                content = data['candidates'][0].get('content')
                if content and content.get('parts') and content['parts'][0]:
                    return content['parts'][0]['text'].strip()
            
            raise ValueError('Invalid Gemini response structure')
    
    
    
    @classmethod
    def get_available_apis(cls) -> Dict[str, bool]:
        """Get available API keys"""
        return {
            'gemini': bool(os.getenv('SAYU_GEMINI_API_KEY'))
        }
