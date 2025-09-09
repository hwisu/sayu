"""Optimized LLM API client using httpx for better performance"""

import json
import os
import time
from typing import Dict, Any, Optional
import httpx

from shared.constants import LLMConstants


class OptimizedLLMApiClient:
    """Optimized LLM API client with httpx and caching"""
    
    # Simple in-memory cache for API responses
    _cache: Dict[str, tuple[str, float]] = {}
    CACHE_TTL = 300  # 5 minutes
    
    @classmethod
    def call_llm(cls, prompt: str, use_cache: bool = True) -> str:
        """Call LLM API with priority order: Gemini -> OpenAI -> Anthropic"""
        # Check cache first
        if use_cache:
            cached_response = cls._get_cached(prompt)
            if cached_response:
                return cached_response
        
        # Make API call
        response = None
        if os.getenv('GEMINI_API_KEY'):
            response = cls._call_gemini(prompt)
        elif os.getenv('OPENAI_API_KEY'):
            response = cls._call_openai(prompt)
        elif os.getenv('ANTHROPIC_API_KEY'):
            response = cls._call_anthropic(prompt)
        else:
            raise ValueError('No LLM API key found')
        
        # Cache the response
        if use_cache and response:
            cls._set_cache(prompt, response)
        
        return response
    
    @classmethod
    def _get_cached(cls, prompt: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        cache_key = hash(prompt)
        if cache_key in cls._cache:
            response, timestamp = cls._cache[cache_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                if os.getenv('SAYU_DEBUG'):
                    print("Using cached LLM response")
                return response
        return None
    
    @classmethod
    def _set_cache(cls, prompt: str, response: str):
        """Cache a response"""
        cache_key = hash(prompt)
        cls._cache[cache_key] = (response, time.time())
    
    @classmethod
    def _call_gemini(cls, prompt: str) -> str:
        """Call Gemini API using httpx"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError('GEMINI_API_KEY not found in environment')
        
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
        
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
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('candidates') and data['candidates'][0]:
                content = data['candidates'][0].get('content')
                if content and content.get('parts') and content['parts'][0]:
                    return content['parts'][0]['text'].strip()
            
            raise ValueError('Invalid Gemini response structure')
    
    @classmethod
    def _call_openai(cls, prompt: str) -> str:
        """Call OpenAI API using httpx"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY not found in environment')
        
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if data.get('choices') and data['choices'][0]:
                return data['choices'][0]['message']['content'].strip()
            
            raise ValueError('Invalid OpenAI response structure')
    
    @classmethod
    def _call_anthropic(cls, prompt: str) -> str:
        """Call Anthropic API using httpx"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError('ANTHROPIC_API_KEY not found in environment')
        
        url = 'https://api.anthropic.com/v1/messages'
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if data.get('content') and data['content'][0]:
                return data['content'][0]['text'].strip()
            
            raise ValueError('Invalid Anthropic response structure')
    
    @classmethod
    def get_available_apis(cls) -> Dict[str, bool]:
        """Get available API keys"""
        return {
            'gemini': bool(os.getenv('GEMINI_API_KEY')),
            'openai': bool(os.getenv('OPENAI_API_KEY')),
            'anthropic': bool(os.getenv('ANTHROPIC_API_KEY'))
        }