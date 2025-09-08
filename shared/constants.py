"""Sayu system constants and default values"""

from typing import Final, List

# Time-related constants (in milliseconds/hours/minutes)
class TimeConstants:
    COMMIT_WINDOW_HOURS: Final[int] = 24
    GRACE_PERIOD_MINUTES: Final[int] = 5
    DEFAULT_LOOKBACK_HOURS: Final[int] = 168  # One week

# Text processing constants
class TextConstants:
    MAX_CONVERSATION_COUNT: Final[int] = 20
    MAX_CONVERSATION_LENGTH: Final[int] = 800
    MAX_SIMPLIFIED_CONVERSATIONS: Final[int] = 10
    MAX_SIMPLIFIED_LENGTH: Final[int] = 400
    MAX_HIGH_VALUE_EVENTS: Final[int] = 80
    MAX_DIFF_LENGTH: Final[int] = 2000
    MIN_RESPONSE_LENGTH: Final[int] = 50
    MAX_COMMIT_TRAILER_LINES: Final[int] = 12
    MAX_LINE_LENGTH: Final[int] = 80
    MAX_RAW_RESPONSE_LENGTH: Final[int] = 2000
    MAX_FILE_DISPLAY: Final[int] = 3

# LLM API constants
class LLMConstants:
    TEMPERATURE: Final[float] = 0.1
    MAX_OUTPUT_TOKENS: Final[int] = 8192
    OPENAI_TEMPERATURE: Final[float] = 0.3
    OPENAI_MAX_TOKENS: Final[int] = 1000
    ANTHROPIC_TEMPERATURE: Final[float] = 0.3
    ANTHROPIC_MAX_TOKENS: Final[int] = 1000

# Filtering constants
class FilterConstants:
    MIN_RELEVANCE_SCORE: Final[float] = 0.6
    DEFAULT_DOMAIN_ALLOWLIST: Final[List[str]] = [
        'github.com',
        'developer.mozilla.org',
        'stackoverflow.com'
    ]

# Default security masking patterns
DEFAULT_SECURITY_MASKS: Final[List[str]] = [
    r'AKIA[0-9A-Z]{16}',  # AWS Access Key
    r'(?i)authorization:\s*Bearer\s+[A-Za-z0-9._-]+',  # Bearer token
    r'(?i)api[_-]?key[\'"\\s]*[:=][\'"\\s]*[A-Za-z0-9]{20,}',  # API key
    r'(?i)secret[\'"\\s]*[:=][\'"\\s]*[A-Za-z0-9]{10,}',  # Secret
]