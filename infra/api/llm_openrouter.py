"""OpenRouter LLM API client"""

import os
import json
from typing import Dict, List, Optional, Any
import httpx

from shared.constants import DEFAULT_MODEL, DEFAULT_MAX_TOKENS


class OpenRouterClient:
    """OpenRouter API client for LLM operations"""
    
    # Popular models on OpenRouter
    MODELS = {
        'claude-3-opus': 'anthropic/claude-3-opus',
        'claude-3-sonnet': 'anthropic/claude-3-sonnet-20240229',
        'claude-3-haiku': 'anthropic/claude-3-haiku-20240307',
        'gpt-4-turbo': 'openai/gpt-4-turbo',
        'gpt-3.5-turbo': 'openai/gpt-3.5-turbo',
        'mixtral-8x7b': 'mistralai/mixtral-8x7b-instruct',
        'llama-3-70b': 'meta-llama/llama-3-70b-instruct',
        'gemini-pro': 'google/gemini-pro',
        'deepseek-coder': 'deepseek/deepseek-coder-33b-instruct',
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter client"""
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key parameter"
            )
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.site_url = os.getenv('OPENROUTER_SITE_URL', 'https://github.com/sayu')
        self.app_name = os.getenv('OPENROUTER_APP_NAME', 'Sayu')
    
    def generate_summary(
        self,
        prompt: str,
        model: str = 'claude-3-haiku',  # Fast and cheap default
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.3
    ) -> Optional[str]:
        """Generate summary using OpenRouter API"""
        
        # Map short model names to full OpenRouter model IDs
        model_id = self.MODELS.get(model, model)
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes git commits and development context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract content from response
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    return content.strip()
                
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Error: Invalid OpenRouter API key")
            elif e.response.status_code == 429:
                print("Error: Rate limit exceeded")
            elif e.response.status_code == 402:
                print("Error: Insufficient credits")
            else:
                print(f"HTTP error: {e.response.status_code}")
                if os.getenv('SAYU_DEBUG'):
                    print(f"Response: {e.response.text}")
            return None
            
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"OpenRouter API error: {e}")
            return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models on OpenRouter"""
        url = f"{self.base_url}/models"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                return data.get('data', [])
                
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Failed to list models: {e}")
            return []
    
    def get_usage(self) -> Optional[Dict[str, Any]]:
        """Get current usage and credits"""
        # Note: This endpoint might require additional setup
        # OpenRouter doesn't have a direct usage endpoint in v1 API
        # You would need to track usage locally or use their dashboard
        return None
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate OpenRouter API key"""
        try:
            client = OpenRouterClient(api_key=api_key)
            # Try to list models as a validation check
            models = client.list_models()
            return len(models) > 0
        except Exception:
            return False