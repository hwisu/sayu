"""Abstract collector interface and event model."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class EventType(Enum):
    """Types of events that can be collected."""
    CONVERSATION = "conversation"
    ACTION = "action"
    FILE_EDIT = "file_edit"
    COMMAND = "command"


@dataclass
class Event:
    """Represents a collected event."""
    timestamp: datetime
    type: EventType
    source: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=EventType(data["type"]),
            source=data["source"],
            content=data["content"],
            metadata=data.get("metadata", {})
        )


class Collector(ABC):
    """Abstract base class for event collectors."""
    
    @abstractmethod
    def collect(self, since: Optional[datetime] = None) -> List[Event]:
        """
        Collect events since the given timestamp.
        
        Args:
            since: Only collect events after this timestamp
            
        Returns:
            List of collected events
        """
        pass
    
    @abstractmethod
    def setup(self) -> None:
        """
        Set up the collector (e.g., register hooks).
        """
        pass
    
    @abstractmethod
    def teardown(self) -> None:
        """
        Clean up the collector (e.g., unregister hooks).
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this collector."""
        pass