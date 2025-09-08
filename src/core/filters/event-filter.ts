import { Event } from '../types';
import { TEXT_CONSTANTS } from '../constants';

/**
 * 이벤트 필터링을 담당하는 클래스
 * HookHandlers에서 분리된 책임
 */
export class EventFilter {
  
  static filterHighValueEvents(events: Event[]): Event[] {
    const highValueEvents: Event[] = [];
    const maxEvents = TEXT_CONSTANTS.MAX_HIGH_VALUE_EVENTS;
    
    for (const event of events.reverse()) { // 최신부터 처리
      if (highValueEvents.length >= maxEvents) break;
      
      const text = event.text;
      const isHighValue = this.isHighValueEvent(event, text);
      
      if (isHighValue) {
        highValueEvents.unshift(event); // 원래 순서 유지
      }
    }
    
    return highValueEvents;
  }
  
  private static isHighValueEvent(event: Event, text: string): boolean {
    // 사용자 이벤트는 모두 중요 (길이 무관)
    if (event.actor === 'user') {
      // 도구 결과는 제외 (시스템 메시지)
      if (text.startsWith('[Result:') || text.startsWith('[Tool result:')) {
        return false;
      }
      // 빈 메시지는 제외
      if (text.trim().length === 0) {
        return false;
      }
      // 모든 사용자 메시지는 중요 (짧은 응답도 포함)
      return true;
    }
    
    // 어시스턴트 이벤트 필터링
    if (event.actor === 'assistant') {
      // 도구 사용은 제외
      if (text.startsWith('[Tool:') || text.includes('[Tool:')) {
        return false;
      }
      
      // 매우 짧은 응답은 제외
      if (text.length < TEXT_CONSTANTS.MIN_RESPONSE_LENGTH) {
        return false;
      }
      
      // 단순 확인/완료 메시지는 제외
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