import { ShellExecutor } from '../shell';

/**
 * Git 관련 정보 수집을 담당하는 클래스
 * HookHandlers에서 분리된 책임
 */
export class GitInfo {
  static getStagedFiles(): string[] {
    try {
      const output = ShellExecutor.gitExec(['diff', '--cached', '--name-only']);
      return output.trim().split('\n').filter(Boolean);
    } catch {
      return [];
    }
  }
  
  static getDiffStats(): string {
    try {
      // 통계와 실제 diff 내용을 모두 포함
      const stat = ShellExecutor.gitExec(['diff', '--cached', '--stat']);
      const diff = ShellExecutor.gitExec(['diff', '--cached']);
      
      if (stat.trim() === '' && diff.trim() === '') {
        return '';
      }
      
      // diff가 너무 길면 처음 N자만 포함
      const MAX_DIFF_LENGTH = 5000;
      const diffContent = diff.length > MAX_DIFF_LENGTH ? 
        diff.substring(0, MAX_DIFF_LENGTH) + '\n...(생략)...' : diff;
      
      return `파일 변경 통계:\n${stat.trim()}\n\n실제 변경 내용:\n${diffContent}`;
    } catch {
      return '';
    }
  }
  
  static hasActualChanges(): boolean {
    try {
      const output = ShellExecutor.gitExec(['diff', '--cached', '--numstat']);
      return output.trim().length > 0;
    } catch {
      return false;
    }
  }
}