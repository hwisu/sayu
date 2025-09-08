import fs from 'fs';
import { CollectorManager } from './collector-manager';
import { ConfigManager } from './config';
import { GitHookManager } from './git-hooks';
import { Event } from './types';

export class HookHandlers {
  // commit-msg 훅 핸들러
  static async handleCommitMsg(commitMsgFile: string): Promise<void> {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) return;

      const config = new ConfigManager(repoRoot).get();
      if (!config.output.commitTrailer) return;

      const collector = new CollectorManager(repoRoot);
      
      // 1. 현재 커밋 컨텍스트 수집
      const currentEvents = await collector.collectCurrentCommit();
      
      // 2. 시간 창 내 관련 이벤트 수집
      const timeWindowEvents = await collector.collectInTimeWindow(
        config.window.beforeCommitHours
      );
      
      // 3. 간단한 요약 생성
      const summary = this.generateSimpleSummary(currentEvents, timeWindowEvents);
      
      // 4. 커밋 메시지에 트레일러 추가
      if (summary) {
        const currentMsg = fs.readFileSync(commitMsgFile, 'utf-8');
        
        // 이미 Sayu 트레일러가 있으면 스킵
        if (currentMsg.includes('AI-Context (sayu)')) {
          return;
        }
        
        const newMsg = currentMsg.trimEnd() + '\n\n' + summary;
        fs.writeFileSync(commitMsgFile, newMsg);
      }
      
      collector.close();
    } catch (error) {
      // Fail-open: 에러 발생해도 커밋은 계속
      console.error('Sayu commit-msg hook error:', error);
    }
  }

  // post-commit 훅 핸들러
  static async handlePostCommit(): Promise<void> {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) return;

      const config = new ConfigManager(repoRoot).get();
      if (!config.output.gitNotes) return;

      // TODO: git notes에 상세 정보 저장
      console.log('Post-commit: Would save detailed notes here');
      
    } catch (error) {
      console.error('Sayu post-commit hook error:', error);
    }
  }

  // 간단한 규칙 기반 요약 생성
  private static generateSimpleSummary(
    currentEvents: Event[], 
    timeWindowEvents: Event[]
  ): string {
    const lines: string[] = [];
    lines.push('---');
    lines.push('AI-Context (sayu)');
    
    // Changed files
    const changedFiles = currentEvents
      .filter(e => e.file && e.kind === 'edit')
      .map(e => e.file);
    
    if (changedFiles.length > 0) {
      const fileList = changedFiles.slice(0, 3).join(', ');
      const more = changedFiles.length > 3 ? ` (+${changedFiles.length - 3} more)` : '';
      lines.push(`What: Modified ${fileList}${more}`);
    }
    
    // Recent commits (context)
    const recentCommits = timeWindowEvents
      .filter(e => e.kind === 'commit' && e.meta?.hash)
      .slice(0, 2);
    
    if (recentCommits.length > 0) {
      lines.push(`Context: ${recentCommits.length} recent commits in last ${this.formatTime(Date.now() - recentCommits[0].ts)}`);
    }
    
    // Test/error events
    const testEvents = timeWindowEvents.filter(e => e.kind === 'test');
    const errorEvents = timeWindowEvents.filter(e => e.kind === 'error');
    
    if (testEvents.length > 0) {
      lines.push(`Tests: ${testEvents.length} test runs`);
    }
    
    if (errorEvents.length > 0) {
      lines.push(`Errors: ${errorEvents.length} errors encountered`);
    }
    
    // Stats
    const totalEvents = currentEvents.length + timeWindowEvents.length;
    lines.push(`Events: ${totalEvents} tracked`);
    lines.push(`Confidence: ★★☆☆ (rule-based)`);
    
    lines.push('---');
    
    return lines.join('\n');
  }

  private static formatTime(ms: number): string {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }
}