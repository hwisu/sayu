"""Internationalization (i18n) system for Sayu"""

import os
from typing import Literal, Any, Dict, Callable

from .prompts.ko import ko_prompts
from .prompts.en import en_prompts
from .outputs.ko import ko_outputs
from .outputs.en import en_outputs

SupportedLanguage = Literal['ko', 'en']


class I18nManager:
    """Internationalization manager for Sayu"""
    
    _instance: 'I18nManager' = None
    
    def __init__(self):
        """Initialize i18n manager"""
        # Get language from environment or default to 'ko'
        env_lang = os.getenv('SAYU_LANG', '').lower()
        self.current_language: SupportedLanguage = 'en' if env_lang == 'en' else 'ko'
    
    @classmethod
    def get_instance(cls) -> 'I18nManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_language(self) -> SupportedLanguage:
        """Get current language"""
        return self.current_language
    
    def set_language(self, lang: SupportedLanguage):
        """Set current language"""
        self.current_language = lang
    
    def get_prompts(self) -> Dict[str, Callable]:
        """Get prompt templates for current language"""
        return ko_prompts if self.current_language == 'ko' else en_prompts
    
    def get_outputs(self) -> Dict[str, Any]:
        """Get output templates for current language"""
        return ko_outputs if self.current_language == 'ko' else en_outputs
    
    def get_main_analysis_prompt(
        self, 
        conversations: str, 
        staged_files: list, 
        diff_stats: str, 
        process_analysis: str
    ) -> str:
        """Get main analysis prompt"""
        prompts = self.get_prompts()
        return prompts['main_analysis'](conversations, staged_files, diff_stats, process_analysis)
    
    def get_simplified_analysis_prompt(
        self, 
        conversations: str, 
        staged_files: list, 
        diff_stats: str
    ) -> str:
        """Get simplified analysis prompt"""
        prompts = self.get_prompts()
        return prompts['simplified_analysis'](conversations, staged_files, diff_stats)


# Global instance access function
def i18n() -> I18nManager:
    """Get global i18n instance"""
    return I18nManager.get_instance()
