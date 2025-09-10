"""Sayu system constants and default values"""

from typing import Final

# Time-related constants
DEFAULT_LOOKBACK_HOURS: Final[int] = 24  # Default time window for event collection
CACHE_TTL_SECONDS: Final[int] = 3600  # Cache TTL (1 hour)

# Text processing constants
MAX_CONVERSATION_COUNT: Final[int] = 99  # Maximum conversations to include
MAX_CONVERSATION_LENGTH: Final[int] = 20000  # Maximum length per conversation
MAX_SIMPLIFIED_CONVERSATIONS: Final[int] = 66  # For simplified mode
MAX_SIMPLIFIED_LENGTH: Final[int] = 2000  # For simplified mode
MAX_LINE_LENGTH: Final[int] = 100  # Maximum line length in commit trailer
MAX_RAW_RESPONSE_LENGTH: Final[int] = 10000  # Maximum raw response length

# LLM API constants
LLM_TEMPERATURE: Final[float] = 0.3  # Temperature for LLM generation
LLM_MAX_OUTPUT_TOKENS: Final[int] = 8096  # Maximum output tokens (increased for thinking models)

# Summary formatting constants
SUMMARY_SEPARATOR: Final[str] = '---思惟---\n\n'
SUMMARY_FOOTER: Final[str] = '\n---FIN---'
