"""LLM provider factory for Sayu"""

import os
from typing import Optional
from enum import Enum
from pathlib import Path


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    GEMINI = 'gemini'
    OPENROUTER = 'openrouter'


class LLMFactory:
    """Factory for creating LLM clients based on provider"""
    
    _env_loaded = False
    
    @classmethod
    def _load_env(cls):
        """Load .env file if it exists"""
        if cls._env_loaded:
            return
        
        # Import here to avoid circular dependency
        from infra.config.env_loader import EnvLoader
        cls._env_loaded = True
    
    @staticmethod
    def create_client(provider: Optional[str] = None):
        """Create LLM client based on provider setting"""
        
        # Load .env file
        LLMFactory._load_env()
        
        # Get provider from parameter, env, or default
        if not provider:
            provider = os.getenv('SAYU_LLM_PROVIDER', LLMProvider.GEMINI)
        
        provider = provider.lower()
        
        if provider == LLMProvider.GEMINI:
            from infra.api.llm import LLMApiClient
            return LLMApiClient()
            
        elif provider == LLMProvider.OPENROUTER:
            from infra.api.llm_openrouter import OpenRouterClient
            return OpenRouterClient()
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def call_llm(prompt: str, provider: Optional[str] = None, model: Optional[str] = None) -> Optional[str]:
        """Unified interface for calling any LLM provider"""
        
        # Load .env file
        LLMFactory._load_env()
        
        provider = provider or os.getenv('SAYU_LLM_PROVIDER', LLMProvider.GEMINI)
        provider = provider.lower()
        
        try:
            if provider == LLMProvider.GEMINI:
                from infra.api.llm import LLMApiClient
                return LLMApiClient.call_llm(prompt)
                
            elif provider == LLMProvider.OPENROUTER:
                from infra.api.llm_openrouter import OpenRouterClient
                client = OpenRouterClient()
                
                # Use model from parameter, env, or default
                model = model or os.getenv('SAYU_OPENROUTER_MODEL', 'anthropic/claude-3-haiku')
                
                return client.generate_summary(prompt, model=model)
                
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            print(f"[Sayu] LLM call failed: {type(e).__name__}: {e}")
            if os.getenv('SAYU_DEBUG'):
                import traceback
                traceback.print_exc()
            return None
