"""Sayu system constants and default values"""

from typing import Final

# Configurable constants
MAX_CONVERSATION_COUNT: Final[int] = 99  # Maximum conversations to include
MAX_CONVERSATION_LENGTH: Final[int] = 20000  # Maximum length per conversation
LLM_TEMPERATURE: Final[float] = 0.3  # Temperature for LLM generation
LLM_MAX_OUTPUT_TOKENS: Final[int] = 20000  # Maximum output tokens (increased for thinking models)
