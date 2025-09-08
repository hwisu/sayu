import { Connector, Event, Config } from '../events/types';
import Database from 'better-sqlite3';
import path from 'path';
import os from 'os';
import fs from 'fs';
import { randomUUID } from 'crypto';
import crypto from 'crypto';

export class CursorCollector implements Connector {
  id = 'llm.cursor';
  private repoRoot: string;
  private globalDbPath: string;
  private workspaceDbPaths: string[] = [];

  constructor(repoRoot?: string) {
    this.repoRoot = repoRoot || process.cwd();
    this.globalDbPath = this.getCursorGlobalDbPath();
    this.findWorkspaceDatabases();
  }
  
  private getCursorGlobalDbPath(): string {
    const platform = process.platform;
    const home = os.homedir();
    
    switch (platform) {
      case 'darwin': // macOS
        return path.join(home, 'Library/Application Support/Cursor/User/globalStorage/state.vscdb');
      case 'win32': // Windows
        return path.join(home, 'AppData/Roaming/Cursor/User/globalStorage/state.vscdb');
      case 'linux': // Linux
        return path.join(home, '.config/Cursor/User/globalStorage/state.vscdb');
      default:
        // Fallback to Linux path for other Unix-like systems
        return path.join(home, '.config/Cursor/User/globalStorage/state.vscdb');
    }
  }

  private findWorkspaceDatabases(): void {
    const workspaceDir = path.join(
      os.homedir(),
      'Library/Application Support/Cursor/User/workspaceStorage'
    );
    
    if (!fs.existsSync(workspaceDir)) return;
    
    // Find workspace databases that might contain data for this repo
    const dirs = fs.readdirSync(workspaceDir);
    for (const dir of dirs) {
      const dbPath = path.join(workspaceDir, dir, 'state.vscdb');
      const workspaceJsonPath = path.join(workspaceDir, dir, 'workspace.json');
      
      if (fs.existsSync(dbPath) && fs.existsSync(workspaceJsonPath)) {
        try {
          const workspaceData = JSON.parse(fs.readFileSync(workspaceJsonPath, 'utf-8'));
          if (workspaceData.folder && workspaceData.folder.includes(path.basename(this.repoRoot))) {
            this.workspaceDbPaths.push(dbPath);
          }
        } catch (e) {
          // Skip invalid workspace files
        }
      }
    }
  }

  async discover(repoRoot: string): Promise<boolean> {
    return fs.existsSync(this.globalDbPath) || this.workspaceDbPaths.length > 0;
  }

  async pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]> {
    const events: Event[] = [];
    
    // Extract from workspace databases
    for (const dbPath of this.workspaceDbPaths) {
      try {
        const db = new Database(dbPath, { readonly: true });
        
        // Get prompts from workspace
        const promptsRow = db.prepare(
          "SELECT value FROM ItemTable WHERE key = 'aiService.prompts'"
        ).get() as any;
        
        if (promptsRow?.value) {
          const prompts = JSON.parse(promptsRow.value.toString());
          events.push(...this.promptsToEvents(prompts, sinceMs, untilMs));
        }
        
        // Get generations metadata
        const generationsRow = db.prepare(
          "SELECT value FROM ItemTable WHERE key = 'aiService.generations'"
        ).get() as any;
        
        if (generationsRow?.value) {
          const generations = JSON.parse(generationsRow.value.toString());
          events.push(...this.generationsToEvents(generations, sinceMs, untilMs));
        }
        
        // Get editor activity data
        const editorActivity = this.extractEditorActivity(db, sinceMs, untilMs);
        events.push(...editorActivity);
        
        db.close();
      } catch (error) {
        console.error(`Failed to read Cursor workspace DB ${dbPath}:`, error);
      }
    }
    
    // Extract from global database (composer data)
    try {
      const globalDb = new Database(this.globalDbPath, { readonly: true });
      
      // Get recent composer data
      const composerKeys = globalDb.prepare(
        "SELECT key FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
      ).all() as any[];
      
      for (const row of composerKeys.slice(-10)) { // Last 10 composers
        try {
          const dataRow = globalDb.prepare(
            "SELECT value FROM cursorDiskKV WHERE key = ?"
          ).get(row.key) as any;
          
          if (dataRow?.value) {
            const composerData = JSON.parse(dataRow.value.toString());
            const composerEvent = this.composerToEvent(composerData, row.key);
            if (composerEvent && composerEvent.ts >= sinceMs && composerEvent.ts <= untilMs) {
              events.push(composerEvent);
            }
          }
        } catch (e) {
          // Skip invalid composer data
        }
      }
      
      globalDb.close();
    } catch (error) {
      console.error('Failed to read Cursor global DB:', error);
    }
    
    return events.sort((a, b) => a.ts - b.ts);
  }

  private promptsToEvents(prompts: any[], sinceMs: number, untilMs: number): Event[] {
    if (!Array.isArray(prompts)) return [];
    
    return prompts
      .map((prompt, index) => {
        // Estimate timestamp (prompts don't have timestamps, use index-based estimation)
        const estimatedTime = untilMs - (prompts.length - index) * 60000; // 1 minute apart
        
        if (estimatedTime < sinceMs || estimatedTime > untilMs) return null;
        
        return {
          id: randomUUID(),
          ts: estimatedTime,
          source: 'llm' as const,
          kind: 'chat' as const,
          repo: this.repoRoot,
          cwd: this.repoRoot,
          file: null,
          range: null,
          actor: 'user' as const,
          text: prompt.text || '',
          url: null,
          meta: {
            tool: 'cursor',
            commandType: prompt.commandType
          }
        } as Event;
      })
      .filter(e => e !== null) as Event[];
  }

  private generationsToEvents(generations: any[], sinceMs: number, untilMs: number): Event[] {
    if (!Array.isArray(generations)) return [];
    
    return generations
      .filter(gen => gen.unixMs >= sinceMs && gen.unixMs <= untilMs)
      .map(gen => ({
        id: randomUUID(),
        ts: gen.unixMs,
        source: 'llm' as const,
        kind: 'chat' as const,
        repo: this.repoRoot,
        cwd: this.repoRoot,
        file: null,
        range: null,
        actor: 'assistant' as const,
        text: gen.textDescription || `[${gen.type} generation]`,
        url: null,
        meta: {
          tool: 'cursor',
          type: gen.type,
          generationUUID: gen.generationUUID
        }
      } as Event));
  }

  private composerToEvent(composerData: any, key: string): Event | null {
    if (!composerData.createdAt) return null;
    
    // Extract basic info from composer
    const composerId = key.replace('composerData:', '');
    const text = composerData.text || composerData.richText || '[Cursor composer session]';
    
    return {
      id: randomUUID(),
      ts: composerData.createdAt,
      source: 'llm' as const,
      kind: 'chat' as const,
      repo: this.repoRoot,
      cwd: this.repoRoot,
      file: null,
      range: null,
      actor: 'user' as const,
      text: text.substring(0, 500),
      url: null,
      meta: {
        tool: 'cursor',
        composerId,
        mode: composerData.unifiedMode || 'unknown',
        hasContext: !!(composerData.context && Object.keys(composerData.context).length > 0)
      }
    };
  }

  /**
   * Extract additional editor activity from workspace database
   */
  private extractEditorActivity(db: Database.Database, sinceMs: number, untilMs: number): Event[] {
    const events: Event[] = [];
    
    try {
      // Get recently opened files
      const editorMementoRow = db.prepare(
        "SELECT value FROM ItemTable WHERE key LIKE 'memento/workbench.editors%'"
      ).get() as any;
      
      if (editorMementoRow?.value) {
        const editorData = JSON.parse(editorMementoRow.value.toString());
        if (editorData.editors && Array.isArray(editorData.editors)) {
          // Create an event for opened files context
          const openedFiles = editorData.editors
            .map((editor: any) => editor.resource?.path || editor.resource)
            .filter((path: string) => path && path.includes(this.repoRoot))
            .slice(0, 10); // Recent 10 files
          
          if (openedFiles.length > 0) {
            events.push({
              id: randomUUID(),
              ts: untilMs - 30000, // Estimate 30 seconds ago
              source: 'editor' as const,
              kind: 'edit' as const,
              repo: this.repoRoot,
              cwd: this.repoRoot,
              file: null,
              range: null,
              actor: 'user' as const,
              text: `최근 작업 파일들: ${openedFiles.map((f: string) => path.basename(f)).join(', ')}`,
              url: null,
              meta: {
                tool: 'cursor',
                type: 'editor_context',
                fileCount: openedFiles.length,
                files: openedFiles
              }
            } as Event);
          }
        }
      }

      // Get notepad data for quick notes/thoughts
      const notepadRow = db.prepare(
        "SELECT value FROM ItemTable WHERE key = 'notepadData'"
      ).get() as any;
      
      if (notepadRow?.value) {
        const notepadData = JSON.parse(notepadRow.value.toString());
        if (notepadData.notepads && Object.keys(notepadData.notepads).length > 0) {
          // Create events for active notepads
          Object.entries(notepadData.notepads).forEach(([notepadId, notepad]: [string, any]) => {
            if (notepad.text && notepad.text.trim().length > 0) {
              events.push({
                id: randomUUID(),
                ts: untilMs - 60000, // Estimate 1 minute ago
                source: 'editor' as const,
                kind: 'note' as const,
                repo: this.repoRoot,
                cwd: this.repoRoot,
                file: null,
                range: null,
                actor: 'user' as const,
                text: `노트패드 내용: ${notepad.text.substring(0, 300)}`,
                url: null,
                meta: {
                  tool: 'cursor',
                  type: 'notepad',
                  notepadId
                }
              } as Event);
            }
          });
        }
      }

      // Get workspace configuration changes
      const allRows = db.prepare("SELECT key, value FROM ItemTable WHERE key LIKE '%config%' OR key LIKE '%setting%'").all() as any[];
      
      if (allRows.length > 0) {
        const configChanges = allRows.map(row => row.key).join(', ');
        events.push({
          id: randomUUID(),
          ts: untilMs - 120000, // Estimate 2 minutes ago
          source: 'editor' as const,
          kind: 'config' as const,
          repo: this.repoRoot,
          cwd: this.repoRoot,
          file: null,
          range: null,
          actor: 'user' as const,
          text: `워크스페이스 설정 활동: ${configChanges}`,
          url: null,
          meta: {
            tool: 'cursor',
            type: 'workspace_config',
            configCount: allRows.length
          }
        } as Event);
      }
      
    } catch (error) {
      console.error('Error extracting editor activity:', error);
    }
    
    return events.filter(e => e.ts >= sinceMs && e.ts <= untilMs);
  }

  async health(): Promise<{ ok: boolean; reason?: string }> {
    if (!fs.existsSync(this.globalDbPath)) {
      return { ok: false, reason: 'Cursor not installed or database not found' };
    }
    
    try {
      const db = new Database(this.globalDbPath, { readonly: true });
      db.close();
      return { ok: true };
    } catch (error) {
      return { ok: false, reason: `Cannot access Cursor database: ${error}` };
    }
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
