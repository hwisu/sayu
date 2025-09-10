"""Event types and schemas for Sayu"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Protocol, Any, Literal
import uuid
from datetime import datetime


class EventSource(str, Enum):
    """Event source types"""
    LLM = 'llm'
    EDITOR = 'editor'
    CLI = 'cli'
    BROWSER = 'browser'
    GIT = 'git'
    FILE = 'file'  # File system events


class EventKind(str, Enum):
    """Event kinds"""
    CHAT = 'chat'
    EDIT = 'edit'
    SAVE = 'save'
    RUN = 'run'
    NAV = 'nav'
    COMMIT = 'commit'
    TEST = 'test'
    BENCH = 'bench'
    ERROR = 'error'
    DOC = 'doc'
    NOTE = 'note'
    CONFIG = 'config'


class Actor(str, Enum):
    """Actor types"""
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


@dataclass
class Range:
    """Code range definition"""
    start: int
    end: int


@dataclass
class Event:
    """Standard event schema"""
    source: EventSource
    kind: EventKind
    repo: str
    cwd: str
    text: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    file: Optional[str] = None
    range: Optional[Range] = None
    actor: Optional[Actor] = None
    url: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, **kwargs) -> Event:
        """Create event with current timestamp if not provided"""
        if 'ts' not in kwargs:
            kwargs['ts'] = int(datetime.now().timestamp() * 1000)
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        return cls(**kwargs)


# Configuration schemas
@dataclass
class ConnectorConfig:
    """Connector configuration"""
    claude: bool = True
    cursor: bool = True
    editor: bool = True
    cli: Dict[str, str] = field(default_factory=lambda: {'mode': 'zsh-preexec'})
    git: bool = True



@dataclass
class PrivacyConfig:
    """Privacy configuration"""
    maskSecrets: bool = False
    masks: List[str] = field(default_factory=lambda: [
        r'AKIA[0-9A-Z]{16}',
        r'(?i)authorization:\s*Bearer\s+[A-Za-z0-9._-]+'
    ])


@dataclass
class OutputConfig:
    """Output configuration"""
    commitTrailer: bool = True


@dataclass
class Config:
    """Main configuration"""
    connectors: ConnectorConfig = field(default_factory=ConnectorConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


class Connector(Protocol):
    """Connector interface protocol"""
    id: str
    
    def discover(self, repo_root: str) -> bool:
        """Check if connector is available for this repo"""
        ...
    
    def pull_since(self, since_ms: int, until_ms: int, cfg: Config) -> List[Event]:
        """Pull events in time range"""
        ...
    
    def health(self) -> Dict[str, Any]:
        """Health check"""
        ...
    
    def redact(self, event: Event, cfg: Config) -> Event:
        """Redact sensitive information from event"""
        ...


@dataclass
class EventRow:
    """Database row representation"""
    id: str
    ts: int
    source: str
    kind: str
    repo: str
    cwd: str
    file: Optional[str] = None
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    actor: Optional[str] = None
    text: str = ""
    url: Optional[str] = None
    meta: Optional[str] = None


@dataclass
class LLMSummaryResponse:
    """LLM summary response"""
    intent: Optional[str] = None
    what_changed: Optional[str] = None
    conversation_flow: Optional[str] = None


@dataclass
class UserConfig:
    """Simplified user configuration"""
    enabled: bool = True
    language: Literal['ko', 'en'] = 'ko'
    commitTrailer: bool = True
