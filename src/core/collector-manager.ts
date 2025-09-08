import { EventStore } from './database';
import { IdGenerator } from './utils';
import { ConfigManager } from './config';
import { GitCollector } from '../collectors/git';
import { ClaudeCollector } from '../collectors/llm-claude';
import { CursorCollector } from '../collectors/llm-cursor';
import { CliCollector } from '../collectors/cli';
import { Event, Config } from './types';
import { GitHookManager } from './git-hooks';

export class CollectorManager {
  private store: EventStore;
  private config: Config;
  private gitCollector: GitCollector;
  private claudeCollector: ClaudeCollector;
  private cursorCollector: CursorCollector;
  private cliCollector: CliCollector;
  private repoRoot: string;

  constructor(repoRoot?: string) {
    this.repoRoot = repoRoot || GitHookManager.getRepoRoot() || process.cwd();
    this.store = new EventStore();
    this.config = new ConfigManager(this.repoRoot).get();
    this.gitCollector = new GitCollector(this.repoRoot);
    this.claudeCollector = new ClaudeCollector(this.repoRoot);
    this.cursorCollector = new CursorCollector(this.repoRoot);
    this.cliCollector = new CliCollector(this.repoRoot);
  }

  // 현재 스테이징된 변경사항에 대한 이벤트 수집
  async collectCurrentCommit(): Promise<Event[]> {
    const events: Event[] = [];
    const now = Date.now();
    
    // Git 컬렉터로 현재 상태 수집
    const gitContext = await this.gitCollector.getCurrentCommitContext();
    
    // 스테이징된 파일들은 이벤트로 저장하지 않음 (중요하지 않음)
    // 대신 hook-handlers에서 파일 목록만 사용
    
    // diff 정보는 저장 (나중에 상세 분석용)
    if (gitContext.diff) {
      const diffEvent: Event = {
        id: this.generateId(),
        ts: now,
        source: 'git',
        kind: 'commit',
        repo: this.repoRoot,
        cwd: this.repoRoot,
        file: null,
        range: null,
        actor: 'user',
        text: gitContext.diff.substring(0, 1000), // 처음 1000자만
        url: null,
        meta: {
          type: 'diff',
          fullLength: gitContext.diff.length,
          files: gitContext.files.join(',')  // 파일 목록은 메타에 저장
        }
      };
      
      events.push(diffEvent);
      this.store.insert(diffEvent);
    }
    
    return events;
  }

  // 시간 범위로 이벤트 수집
  async collectInTimeWindow(hours: number = 168): Promise<Event[]> {
    const now = Date.now();
    const sinceMs = now - (hours * 60 * 60 * 1000);
    
    // 마지막 커밋 시간 확인
    const lastCommitTime = this.store.getLastCommitTime(this.repoRoot);
    const startTime = lastCommitTime || sinceMs;
    
    const allEvents: Event[] = [];
    
    // Git 이벤트 수집
    const gitEvents = await this.gitCollector.pullSince(startTime, now, this.config);
    allEvents.push(...gitEvents);
    
    // Claude 이벤트 수집 (설정에서 활성화된 경우)
    if (this.config.connectors.claude) {
      try {
        const claudeEvents = await this.claudeCollector.pullSince(startTime, now, this.config);
        allEvents.push(...claudeEvents);
      } catch (error) {
        console.error('Claude collector error:', error);
      }
    }
    
    // Cursor 이벤트 수집 (설정에서 활성화된 경우)
    if (this.config.connectors.cursor) {
      try {
        const cursorEvents = await this.cursorCollector.pullSince(startTime, now, this.config);
        allEvents.push(...cursorEvents);
      } catch (error) {
        console.error('Cursor collector error:', error);
      }
    }
    
    // CLI 이벤트 수집 (설정에서 활성화된 경우)
    if (this.config.connectors.cli.mode !== 'off') {
      try {
        const cliEvents = await this.cliCollector.pullSince(startTime, now, this.config);
        allEvents.push(...cliEvents);
      } catch (error) {
        console.error('CLI collector error:', error);
      }
    }
    
    // DB에 저장
    if (allEvents.length > 0) {
      this.store.insertBatch(allEvents);
    }
    
    // DB에서 시간 창 내 모든 이벤트 조회 (시간순 정렬)
    return this.store.findByRepo(this.repoRoot, startTime, now);
  }


  private generateId(): string {
    return IdGenerator.generate();
  }

  close(): void {
    this.store.close();
  }
}
