import { Connector, Event, Config } from '../events/types';
import fs from 'fs';
import path from 'path';
import os from 'os';
import readline from 'readline';
import { randomUUID } from 'crypto';

type ClaudeContentBlock = 
  | { type: 'text'; text?: string; cache_control?: { type: string } }
  | { type: 'tool_use'; name: string; input: Record<string, any>; cache_control?: { type: string } }
  | { type: 'tool_result'; content: string | any; cache_control?: { type: string } }
  | { type: 'image'; source: { type: string; media_type: string; data: string }; cache_control?: { type: string } };

interface ClaudeLogEntry {
  parentUuid: string | null;
  userType: string;
  cwd: string;
  sessionId: string;
  type: 'user' | 'assistant' | 'system';
  message: {
    role: string;
    content: string | ClaudeContentBlock[];
  };
  uuid: string;
  timestamp: string;
}

export class ClaudeCollector implements Connector {
  id = 'llm.claude';
  private repoRoot: string;
  private claudeProjectsDir: string;

  constructor(repoRoot?: string) {
    this.repoRoot = repoRoot || process.cwd();
    this.claudeProjectsDir = path.join(os.homedir(), '.claude', 'projects');
  }

  async discover(repoRoot: string): Promise<boolean> {
    // Check if Claude project directory exists for this repo
    const projectDir = this.getProjectDir(repoRoot);
    return fs.existsSync(projectDir);
  }

  async pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]> {
    const events: Event[] = [];
    const projectDir = this.getProjectDir(this.repoRoot);
    
    if (!fs.existsSync(projectDir)) {
      return events;
    }

    // Find JSONL files in project directory
    const files = fs.readdirSync(projectDir)
      .filter(f => f.endsWith('.jsonl'))
      .map(f => path.join(projectDir, f));

    for (const file of files) {
      const fileEvents = await this.parseJSONLFile(file, sinceMs, untilMs);
      events.push(...fileEvents);
    }

    return events.sort((a, b) => a.ts - b.ts);
  }

  private async parseJSONLFile(filePath: string, sinceMs: number, untilMs: number): Promise<Event[]> {
    const events: Event[] = [];
    const fileStream = fs.createReadStream(filePath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    let conversationContext = '';
    let lastUserMessage = '';

    for await (const line of rl) {
      if (!line.trim()) continue;
      
      try {
        const entry: ClaudeLogEntry = JSON.parse(line);
        const entryTime = new Date(entry.timestamp).getTime();
        
        // Check time window
        if (entryTime < sinceMs || entryTime > untilMs) {
          continue;
        }

        // Check if this is for our repo
        if (entry.cwd && !entry.cwd.startsWith(this.repoRoot)) {
          continue;
        }

        // Convert to Event
        if (entry.type === 'user' || entry.type === 'assistant') {
          // Extract text content from array or string
          const contentText = this.extractTextContent(entry.message.content);
          
          const event: Event = {
            id: randomUUID(),
            ts: entryTime,
            source: 'llm',
            kind: 'chat',
            repo: this.repoRoot,
            cwd: entry.cwd || this.repoRoot,
            file: this.extractFileFromContent(contentText),
            range: null,
            actor: entry.type === 'user' ? 'user' : 'assistant',
            text: this.truncateContent(contentText),
            url: null,
            meta: {
              sessionId: entry.sessionId,
              parentUuid: entry.parentUuid,
              uuid: entry.uuid,
              role: entry.message.role,
              fullLength: contentText.length
            }
          };

          // Track conversation flow
          if (entry.type === 'user') {
            lastUserMessage = contentText;
          } else if (entry.type === 'assistant' && lastUserMessage) {
            // Add context about what question this answers
            event.meta.respondsTo = this.extractFirstLine(lastUserMessage);
          }

          events.push(event);
        }
      } catch (error) {
        console.error('Failed to parse Claude log line:', error);
      }
    }

    return events;
  }

  private getProjectDir(repoRoot: string): string {
    // Claude uses path with dashes instead of slashes
    const projectName = repoRoot.replace(/\//g, '-');
    return path.join(this.claudeProjectsDir, projectName);
  }

  private extractTextContent(content: string | Array<{ type: string; text?: string; cache_control?: { type: string } }>): string {
    // Handle array content (Claude Code sends various content types)
    if (Array.isArray(content)) {
      const contentParts: string[] = [];
      
      for (const block of content as ClaudeContentBlock[]) {
        if (block.type === 'text' && block.text) {
          // Regular text content
          contentParts.push(block.text);
        } else if (block.type === 'tool_use') {
          // Tool usage (Bash, Read, Write, etc.)
          const toolDesc = `[Tool: ${block.name}]`;
          if (block.input?.command) {
            contentParts.push(`${toolDesc} ${block.input.command}`);
          } else if (block.input?.file_path) {
            contentParts.push(`${toolDesc} ${block.input.file_path}`);
          } else {
            contentParts.push(toolDesc);
          }
        } else if (block.type === 'image') {
          // Image content
          contentParts.push('[Image content]');
        } else if (block.type === 'tool_result') {
          // Tool results
          const resultPreview = typeof block.content === 'string' 
            ? block.content.substring(0, 100) 
            : '[Tool output]';
          contentParts.push(`[Result: ${resultPreview}...]`);
        }
      }
      
      return contentParts.filter(text => text && text.length > 0).join('\n') || '';
    }
    // Handle string content
    return content || '';
  }

  private extractFileFromContent(content: string): string | null {
    // Try to extract file paths mentioned in the content
    const filePatterns = [
      /`([^`]+\.(ts|js|tsx|jsx|py|java|go|rs|cpp|c|h))`/g,
      /file[:\s]+([^\s]+\.(ts|js|tsx|jsx|py|java|go|rs|cpp|c|h))/gi,
      /\b(src\/[^\s]+\.(ts|js|tsx|jsx|py|java|go|rs|cpp|c|h))\b/g
    ];

    for (const pattern of filePatterns) {
      const match = pattern.exec(content);
      if (match) {
        return match[1];
      }
    }

    return null;
  }

  private truncateContent(content: string, maxLength: number = 500): string {
    if (content.length <= maxLength) {
      return content;
    }
    
    // Try to truncate at sentence boundary
    const truncated = content.substring(0, maxLength);
    const lastPeriod = truncated.lastIndexOf('.');
    const lastNewline = truncated.lastIndexOf('\n');
    
    const cutPoint = Math.max(lastPeriod, lastNewline);
    if (cutPoint > maxLength * 0.7) {
      return truncated.substring(0, cutPoint + 1) + '...';
    }
    
    return truncated + '...';
  }

  private extractFirstLine(content: string): string {
    const lines = content.split('\n');
    const firstLine = lines[0].trim();
    return firstLine.length > 100 
      ? firstLine.substring(0, 100) + '...'
      : firstLine;
  }

  async health(): Promise<{ ok: boolean; reason?: string }> {
    if (!fs.existsSync(this.claudeProjectsDir)) {
      return { ok: false, reason: 'Claude projects directory not found' };
    }
    
    const projectDir = this.getProjectDir(this.repoRoot);
    if (!fs.existsSync(projectDir)) {
      return { ok: false, reason: 'No Claude project for this repository' };
    }
    
    return { ok: true };
  }

  redact(event: Event, cfg: Config): Event {
    if (!cfg.privacy.maskSecrets) {
      return event;
    }

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
}