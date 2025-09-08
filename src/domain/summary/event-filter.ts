import { Event } from '../events/types';
import { TEXT_CONSTANTS } from '../../shared/constants';

export class EventFilter {
  static filterHighValueEvents(events: Event[]): Event[] {
    const highValueEvents: Event[] = [];
    const maxEvents = TEXT_CONSTANTS.MAX_HIGH_VALUE_EVENTS;
    
    for (const event of events.reverse()) {
      if (highValueEvents.length >= maxEvents) break;
      
      const text = event.text;
      const isHighValue = this.isHighValueEvent(event, text);
      
      if (isHighValue) {
        highValueEvents.unshift(event);
      }
    }
    
    return highValueEvents;
  }

  private static isHighValueEvent(event: Event, text: string): boolean {
    if (event.actor === 'user') {
      if (text.startsWith('[Result:') || text.startsWith('[Tool result:')) {
        return false;
      }
      if (text.trim().length === 0) {
        return false;
      }
      return true;
    }
    
    if (event.actor === 'assistant') {
      if (text.startsWith('[Tool:') || text.includes('[Tool:')) {
        return false;
      }
      
      if (text.length < TEXT_CONSTANTS.MIN_RESPONSE_LENGTH) {
        return false;
      }
      
      const lowValuePatterns = [
        /^완료|^성공|^확인|^좋습니다|^네,?\s*$|^알겠습니다/,
        /빌드.*완료|테스트.*완료|설치.*완료/,
        /시간.*초과|제한.*도달/
      ];
      
      for (const pattern of lowValuePatterns) {
        if (pattern.test(text)) {
          return false;
        }
      }
      
      return true;
    }
    
    return false;
  }
}