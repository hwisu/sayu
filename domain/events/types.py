"""Event types and schemas for Sayu"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Literal
import uuid
from datetime import datetime


class EventSource(str, Enum):
    """Event source types"""
    CLAUDE = 'claude'
    CURSOR = 'cursor'
    CLI = 'cli'
    GIT = 'git'


class EventKind(str, Enum):
    """Event kinds"""
    CONVERSATION = 'conversation'
    COMMAND = 'command'
    COMMIT = 'commit'
    DIFF = 'diff'


class Actor(str, Enum):
    """Actor types"""
    USER = 'user'
    ASSISTANT = 'assistant'


@dataclass
class Event:
    """Simplified event schema"""
    source: EventSource
    kind: EventKind
    repo: str
    text: str
    ts: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    actor: Optional[Actor] = None
    file: Optional[str] = None
    cwd: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    
    # Auto-generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# Configuration schemas
@dataclass
class UserConfig:
    """User configuration"""
    enabled: bool = True
    language: Literal['ko', 'en'] = 'ko'
    commitTrailer: bool = True
    connectors: Dict[str, Any] = field(default_factory=lambda: {
        'claude': True,
        'cursor': True,
        'cli': {'mode': 'zsh-preexec'},
        'git': True
    })