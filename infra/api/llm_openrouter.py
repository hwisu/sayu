"""OpenRouter LLM API client"""

import os
import json
from typing import Dict, List, Optional, Any
import httpx

from shared.constants import LLM_MAX_OUTPUT_TOKENS


class OpenRouterClient:
    """OpenRouter API client for LLM operations"""

    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter client"""
        self.api_key = api_key or os.getenv('SAYU_OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. "
                "Set SAYU_OPENROUTER_API_KEY environment variable or pass api_key parameter"
            )
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.site_url = os.getenv('SAYU_OPENROUTER_SITE_URL', 'https://github.com/hwisu/sayu')
        self.app_name = os.getenv('SAYU_OPENROUTER_APP_NAME', 'Sayu')
    
    def generate_summary(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = LLM_MAX_OUTPUT_TOKENS,
        temperature: float = 0.3
    ) -> Optional[str]:
        """Generate summary using OpenRouter API"""
        
        # Use model from parameter, env, or fallback to claude-3-haiku
        if not model:
            model = os.getenv('SAYU_OPENROUTER_MODEL', 'anthropic/claude-3-haiku')
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
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
                    
                    # Debug logging
                    if os.getenv('SAYU_DEBUG'):
                        print(f"[DEBUG] OpenRouter response type: {type(content)}")
                        print(f"[DEBUG] OpenRouter response content: {content}")
                    
                    # Handle case where content might be a list
                    if isinstance(content, list):
                        # Join list elements if it's a list
                        content = ' '.join(str(item) for item in content)
                        print(f"⚠️ Warning: OpenRouter returned list instead of string, converted to: {content[:100]}...")
                    
                    # Ensure content is a string
                    if not isinstance(content, str):
                        content = str(content)
                    
                    return content.strip()
                
                return None
                
        except httpx.HTTPStatusError as e:
            print(f"OpenRouter API HTTP Error: {e.response.status_code}")
            
            # Always print detailed error info for debugging
            try:
                error_body = e.response.json()
                print(f"Error details: {json.dumps(error_body, indent=2)}")
            except:
                print(f"Error response: {e.response.text}")
            
            if e.response.status_code == 401:
                print("Error: Invalid OpenRouter API key")
            elif e.response.status_code == 429:
                print("Error: Rate limit exceeded")
            elif e.response.status_code == 402:
                print("Error: Insufficient credits")
            elif e.response.status_code == 400:
                print("Error: Bad request - check model name and parameters")
            elif e.response.status_code == 404:
                print(f"Error: Model not found - '{model}'")
            
            return None
            
        except httpx.ConnectError as e:
            print(f"OpenRouter API Connection Error: Unable to connect to {url}")
            print(f"Details: {e}")
            return None
            
        except httpx.TimeoutException as e:
            print(f"OpenRouter API Timeout: Request took longer than 30 seconds")
            return None
            
        except Exception as e:
            print(f"OpenRouter API error: {type(e).__name__}: {e}")
            import traceback
            if os.getenv('SAYU_DEBUG'):
                traceback.print_exc()
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
