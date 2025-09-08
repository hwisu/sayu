import { Event, Config } from '../events/types';
import { ClaudeCollector } from './llm-claude';
import { CursorCollector } from './llm-cursor';
import { CliCollector } from './cli';
import { ErrorHandler } from '../../shared/error-handler';

/**
 * 이벤트 수집을 담당하는 클래스
 * HookHandlers에서 분리된 책임
 */
export class EventCollector {
  private repoRoot: string;
  
  constructor(repoRoot: string) {
    this.repoRoot = repoRoot;
  }
  
  async collectLLMEvents(sinceMs: number, untilMs: number, config: Config): Promise<Event[]> {
    const llmEvents: Event[] = [];
    
    // Claude 이벤트 수집
    const claudeEvents = await this.collectClaudeEvents(sinceMs, untilMs, config);
    llmEvents.push(...claudeEvents);
    
    // Cursor 이벤트 수집
    const cursorEvents = await this.collectCursorEvents(sinceMs, untilMs, config);
    llmEvents.push(...cursorEvents);
    
    // CLI 이벤트 수집
    const cliEvents = await this.collectCliEvents(sinceMs, untilMs, config);
    llmEvents.push(...cliEvents);
    
    return llmEvents;
  }
  
  private async collectClaudeEvents(sinceMs: number, untilMs: number, config: Config): Promise<Event[]> {
    try {
      const collector = new ClaudeCollector(this.repoRoot);
      return await collector.pullSince(sinceMs, untilMs, config);
    } catch (error) {
      if (process.env.SAYU_DEBUG === 'true') {
        ErrorHandler.handle(error, {
          operation: 'claude-collection',
          recoverable: true
        });
      }
      return [];
    }
  }
  
  private async collectCursorEvents(sinceMs: number, untilMs: number, config: Config): Promise<Event[]> {
    try {
      const collector = new CursorCollector(this.repoRoot);
      return await collector.pullSince(sinceMs, untilMs, config);
    } catch (error) {
      if (process.env.SAYU_DEBUG === 'true') {
        ErrorHandler.handle(error, {
          operation: 'cursor-collection',
          recoverable: true
        });
      }
      return [];
    }
  }
  
  private async collectCliEvents(sinceMs: number, untilMs: number, config: Config): Promise<Event[]> {
    try {
      const collector = new CliCollector(this.repoRoot);
      return await collector.pullSince(sinceMs, untilMs, config);
    } catch (error) {
      if (process.env.SAYU_DEBUG === 'true') {
        ErrorHandler.handle(error, {
          operation: 'cli-collection',
          recoverable: true
        });
      }
      return [];
    }
  }
}