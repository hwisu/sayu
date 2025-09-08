"""Event filtering for high-value events"""

import re
from typing import List

from events.types import Event
from shared.constants import TextConstants


class EventFilter:
    """Filter events to identify high-value content"""
    
    @staticmethod
    def filter_high_value_events(events: List[Event]) -> List[Event]:
        """Filter events to get high-value ones"""
        high_value_events = []
        max_events = TextConstants.MAX_HIGH_VALUE_EVENTS
        
        # Reverse to process most recent first, then reverse back
        for event in reversed(events):
            if len(high_value_events) >= max_events:
                break
            
            text = event.text
            if EventFilter._is_high_value_event(event, text):
                high_value_events.insert(0, event)  # Insert at beginning to maintain order
        
        return high_value_events
    
    @staticmethod
    def _is_high_value_event(event: Event, text: str) -> bool:
        """Determine if an event is high-value"""
        if event.actor and event.actor.value == 'user':
            # Skip result/tool outputs
            if text.startswith('[Result:') or text.startswith('[Tool result:'):
                return False
            
            # Skip empty content
            if not text.strip():
                return False
            
            return True
        
        if event.actor and event.actor.value == 'assistant':
            # Skip tool calls
            if text.startswith('[Tool:') or '[Tool:' in text:
                return False
            
            # Skip short responses
            if len(text) < TextConstants.MIN_RESPONSE_LENGTH:
                return False
            
            # Skip low-value patterns
            low_value_patterns = [
                re.compile(r'^완료|^성공|^확인|^좋습니다|^네,?\s*$|^알겠습니다'),
                re.compile(r'빌드.*완료|테스트.*완료|설치.*완료'),
                re.compile(r'시간.*초과|제한.*도달')
            ]
            
            for pattern in low_value_patterns:
                if pattern.search(text):
                    return False
            
            return True
        
        return False
