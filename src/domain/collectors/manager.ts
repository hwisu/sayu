import { EventStore } from '../events/store';
import { IdGenerator } from '../../shared/utils';
import { ConfigManager } from '../../infra/config/manager';
import { GitCollector } from './git';
import { ClaudeCollector } from './llm-claude';
import { CursorCollector } from './llm-cursor';
import { CliCollector } from './cli';
import { Event, Config } from '../events/types';
import { GitHookManager } from '../git/hooks';

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

  // Collect events for currently staged changes
  async collectCurrentCommit(): Promise<Event[]> {
    const events: Event[] = [];
    const now = Date.now();
    
    // Collect current state with Git collector
    const gitContext = await this.gitCollector.getCurrentCommitContext();
    
    // Don't store staged files as events (not important)
    // Instead, only use file list in hook-handlers
    
    // Store diff information (for detailed analysis later)
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
        text: gitContext.diff.substring(0, 1000), // Only first 1000 characters
        url: null,
        meta: {
          type: 'diff',
          fullLength: gitContext.diff.length,
          files: gitContext.files.join(',')  // Store file list in meta
        }
      };
      
      events.push(diffEvent);
      this.store.insert(diffEvent);
    }
    
    return events;
  }

  // Collect events within time range
  async collectInTimeWindow(hours: number = 168): Promise<Event[]> {
    const now = Date.now();
    const sinceMs = now - (hours * 60 * 60 * 1000);
    
    // Check last commit time
    const lastCommitTime = this.store.getLastCommitTime(this.repoRoot);
    const startTime = lastCommitTime || sinceMs;
    
    const allEvents: Event[] = [];
    
    // Collect Git events
    const gitEvents = await this.gitCollector.pullSince(startTime, now, this.config);
    allEvents.push(...gitEvents);
    
    // Collect Claude events (if enabled in config)
    if (this.config.connectors.claude) {
      try {
        const claudeEvents = await this.claudeCollector.pullSince(startTime, now, this.config);
        allEvents.push(...claudeEvents);
      } catch (error) {
        console.error('Claude collector error:', error);
      }
    }
    
    // Collect Cursor events (if enabled in config)
    if (this.config.connectors.cursor) {
      try {
        const cursorEvents = await this.cursorCollector.pullSince(startTime, now, this.config);
        allEvents.push(...cursorEvents);
      } catch (error) {
        console.error('Cursor collector error:', error);
      }
    }
    
    // Collect CLI events (if enabled in config)
    if (this.config.connectors.cli.mode !== 'off') {
      try {
        const cliEvents = await this.cliCollector.pullSince(startTime, now, this.config);
        allEvents.push(...cliEvents);
      } catch (error) {
        console.error('CLI collector error:', error);
      }
    }
    
    // Store in database
    if (allEvents.length > 0) {
      this.store.insertBatch(allEvents);
    }
    
    // Query all events within time window from DB (sorted by time)
    return this.store.findByRepo(this.repoRoot, startTime, now);
  }


  private generateId(): string {
    return IdGenerator.generate();
  }

  close(): void {
    this.store.close();
  }
}
