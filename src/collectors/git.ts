import { Connector, Event, Config } from '../core/types';
import simpleGit, { SimpleGit } from 'simple-git';
import { randomUUID } from 'crypto';
import { execSync } from 'child_process';

export class GitCollector implements Connector {
  id = 'git.core';
  private git: SimpleGit;
  private repoRoot: string;

  constructor(repoRoot?: string) {
    this.repoRoot = repoRoot || process.cwd();
    this.git = simpleGit(this.repoRoot);
  }

  async discover(repoRoot: string): Promise<boolean> {
    try {
      await this.git.checkIsRepo();
      return true;
    } catch {
      return false;
    }
  }

  async pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]> {
    // Git collector는 이제 커밋만 저장 (편집 이벤트 제외)
    const events: Event[] = [];
    
    try {
      // 시간 범위 내 커밋 가져오기
      const sinceDate = new Date(sinceMs).toISOString();
      const untilDate = new Date(untilMs).toISOString();
      
      const log = await this.git.log({
        '--since': sinceDate,
        '--until': untilDate,
        '--no-merges': null
      });

      for (const commit of log.all) {
        // 커밋 이벤트만 저장
        events.push({
          id: randomUUID(),
          ts: new Date(commit.date).getTime(),
          source: 'git',
          kind: 'commit',
          repo: this.repoRoot,
          cwd: this.repoRoot,
          file: null,
          range: null,
          actor: 'user',
          text: commit.message,
          url: null,
          meta: {
            hash: commit.hash,
            author: commit.author_name,
            email: commit.author_email,
            refs: commit.refs
          }
        });
        
        // 파일 변경 이벤트는 더 이상 저장하지 않음
        // 필요시 커밋 메타데이터에서 확인 가능
      }

      // 편집 이벤트 저장 제거

    } catch (error) {
      console.error('GitCollector error:', error);
    }

    return events;
  }

  async health(): Promise<{ ok: boolean; reason?: string }> {
    try {
      const isRepo = await this.git.checkIsRepo();
      if (!isRepo) {
        return { ok: false, reason: 'Not a git repository' };
      }
      return { ok: true };
    } catch (error) {
      return { ok: false, reason: (error as Error).message };
    }
  }

  redact(event: Event, cfg: Config): Event {
    if (!cfg.privacy.maskSecrets) {
      return event;
    }

    // 민감정보 마스킹
    let text = event.text;
    for (const pattern of cfg.privacy.masks) {
      const regex = new RegExp(pattern, 'g');
      text = text.replace(regex, '[REDACTED]');
    }

    return {
      ...event,
      text
    };
  }

  private parseFileChanges(diff: string): Array<{
    file: string;
    status: string;
    additions?: number;
    deletions?: number;
  }> {
    const changes: Array<{
      file: string;
      status: string;
      additions?: number;
      deletions?: number;
    }> = [];

    const lines = diff.split('\n');
    for (const line of lines) {
      const match = line.match(/^([AMD])\t(.+)$/);
      if (match) {
        const [, status, file] = match;
        changes.push({
          file,
          status: this.mapStatus(status)
        });
      }
    }

    return changes;
  }

  private mapStatus(gitStatus: string): string {
    switch (gitStatus) {
      case 'A': return 'added';
      case 'M': return 'modified';
      case 'D': return 'deleted';
      case 'R': return 'renamed';
      case 'C': return 'copied';
      default: return gitStatus.toLowerCase();
    }
  }

  // 현재 커밋 중인 파일들 가져오기
  async getCurrentCommitContext(): Promise<{
    files: string[];
    diff: string;
    message?: string;
  }> {
    const status = await this.git.status();
    const staged = status.staged;
    
    let diff = '';
    if (staged.length > 0) {
      diff = await this.git.diff(['--cached']);
    }

    return {
      files: staged,
      diff
    };
  }

  // 마지막 커밋 정보 가져오기
  async getLastCommit(): Promise<{
    hash: string;
    message: string;
    timestamp: number;
  } | null> {
    try {
      const log = await this.git.log({ n: 1 });
      if (log.latest) {
        return {
          hash: log.latest.hash,
          message: log.latest.message,
          timestamp: new Date(log.latest.date).getTime()
        };
      }
    } catch {
      // 커밋이 없는 경우
    }
    return null;
  }
}