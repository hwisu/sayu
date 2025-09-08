import chalk from 'chalk';
import { GitHookManager } from './git-hooks';

export class CliUtils {
  /**
   * Git 레포지토리 확인 유틸리티
   * @returns 레포지토리 루트 경로 또는 프로세스 종료
   */
  static requireGitRepo(): string {
    const repoRoot = GitHookManager.getRepoRoot();
    if (!repoRoot) {
      console.error(chalk.red('❌ Git 저장소가 아닙니다.'));
      process.exit(1);
    }
    return repoRoot;
  }

  /**
   * CLI 명령어 에러 핸들러
   * @param action 액션 이름
   * @param error 에러 객체
   */
  static handleError(action: string, error: unknown): never {
    console.error(chalk.red(`❌ ${action} 실패:`), (error as Error).message);
    process.exit(1);
  }
}

export class TimeUtils {
  /**
   * 밀리초를 사람이 읽기 쉬운 형식으로 변환
   * @param ms 밀리초
   * @returns 포맷된 시간 문자열 (예: "2h 30m", "45m")
   */
  static formatDuration(ms: number): string {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }

  /**
   * 현재 시간과의 차이를 계산
   * @param timestamp 과거 타임스탬프
   * @returns 시간 차이 (밀리초)
   */
  static getTimeSince(timestamp: number): number {
    return Date.now() - timestamp;
  }
}

export class IdGenerator {
  /**
   * 유니크한 ID 생성
   * @returns 타임스탬프 기반 유니크 ID
   */
  static generate(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}