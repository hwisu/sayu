import { EventStore } from './store';

/**
 * EventStore 싱글톤 매니저
 * 여러 곳에서 EventStore를 생성하는 대신 단일 인스턴스를 재사용
 */
export class StoreManager {
  private static instance: EventStore | null = null;

  /**
   * EventStore 인스턴스 가져오기
   * @returns EventStore 인스턴스
   */
  static getInstance(): EventStore {
    if (!this.instance) {
      this.instance = new EventStore();
    }
    return this.instance;
  }

  /**
   * 일시적으로 EventStore를 사용하고 바로 닫기
   * @param callback EventStore를 사용할 콜백 함수
   * @returns 콜백 함수의 반환값
   */
  static async withStore<T>(
    callback: (store: EventStore) => T | Promise<T>
  ): Promise<T> {
    const store = new EventStore();
    try {
      return await callback(store);
    } finally {
      store.close();
    }
  }

  /**
   * 상태 체크용 - DB 연결 테스트
   * @returns DB 연결 성공 여부
   */
  static checkConnection(): boolean {
    try {
      const store = new EventStore();
      store.close();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 인스턴스 정리
   */
  static cleanup(): void {
    if (this.instance) {
      this.instance.close();
      this.instance = null;
    }
  }
}