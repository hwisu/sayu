import { Connector, Event, Config } from '../core/types';
import { randomUUID } from 'crypto';
import fs from 'fs';
import path from 'path';
import os from 'os';

export class CliCollector implements Connector {
  id = 'cli.shell';
  private repoRoot: string;
  private logPath: string;

  constructor(repoRoot?: string) {
    this.repoRoot = repoRoot || process.cwd();
    this.logPath = path.join(os.homedir(), '.sayu', 'cli.jsonl');
    
    // 로그 디렉토리 생성
    const logDir = path.dirname(this.logPath);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
  }

  async discover(repoRoot: string): Promise<boolean> {
    // zsh hook이 설치되어 있는지 확인
    const hookPath = this.getHookPath();
    return fs.existsSync(hookPath);
  }

  async pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]> {
    const events: Event[] = [];
    
    if (!fs.existsSync(this.logPath)) {
      return events;
    }

    try {
      const content = fs.readFileSync(this.logPath, 'utf-8');
      const lines = content.trim().split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          
          // 시간 범위 확인
          if (entry.ts < sinceMs || entry.ts > untilMs) continue;
          
          // 현재 레포 또는 하위 디렉토리에서 실행된 커맨드만
          if (!this.isRepoRelated(entry.cwd)) continue;
          
          events.push(this.entryToEvent(entry));
        } catch (parseError) {
          // 잘못된 JSON 라인 무시
          continue;
        }
      }
    } catch (error) {
      console.error('CLI log read error:', error);
    }

    return events;
  }

  async health(): Promise<{ ok: boolean; reason?: string }> {
    const hookPath = this.getHookPath();
    
    if (!fs.existsSync(hookPath)) {
      return { ok: false, reason: 'zsh hook not installed' };
    }
    
    // 최근 로그 확인
    if (!fs.existsSync(this.logPath)) {
      return { ok: false, reason: 'no CLI logs found' };
    }
    
    try {
      const stats = fs.statSync(this.logPath);
      const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
      
      if (stats.mtime.getTime() < dayAgo) {
        return { ok: false, reason: 'CLI logs too old' };
      }
      
      return { ok: true };
    } catch {
      return { ok: false, reason: 'unable to check CLI logs' };
    }
  }

  /**
   * zsh hook 설치
   */
  installHook(): void {
    const hookPath = this.getHookPath();
    const hookDir = path.dirname(hookPath);
    
    if (!fs.existsSync(hookDir)) {
      fs.mkdirSync(hookDir, { recursive: true });
    }
    
    const hookContent = this.generateHookScript();
    fs.writeFileSync(hookPath, hookContent, 'utf-8');
    
    // .zshrc에 source 추가
    this.updateZshrc();
  }

  /**
   * zsh hook 제거
   */
  uninstallHook(): void {
    const hookPath = this.getHookPath();
    
    if (fs.existsSync(hookPath)) {
      fs.unlinkSync(hookPath);
    }
    
    // TODO: .zshrc에서 source 라인 제거
  }

  private getHookPath(): string {
    return path.join(os.homedir(), '.sayu', 'zsh-hook.zsh');
  }

  private generateHookScript(): string {
    const logPath = this.logPath;
    
    return `#!/bin/zsh
# Sayu CLI tracking hooks

# 안전한 sayu preexec hook
sayu_preexec() {
  export SAYU_CMD_START=\$(date +%s)
  export SAYU_CMD="\$1"
}

# 안전한 sayu precmd hook  
sayu_precmd() {
  local exit_code=\$?
  
  if [[ -n "\$SAYU_CMD" && -n "\$SAYU_CMD_START" ]]; then
    local end_time=\$(date +%s)
    local duration=\$((end_time - SAYU_CMD_START))
    local cwd="\$PWD"
    local ts_ms=\$((end_time * 1000))
    
    # JSON escape 처리 (안전하게)
    local cmd_safe=\${SAYU_CMD//\\\"/\\\\\\\"}
    cmd_safe=\${cmd_safe//\\\\/\\\\\\\\}
    local cwd_safe=\${cwd//\\\"/\\\\\\\"}
    cwd_safe=\${cwd_safe//\\\\/\\\\\\\\}
    
    # 로그 항목 생성
    local log_entry="{\"ts\":\$ts_ms,\"cmd\":\"\$cmd_safe\",\"exitCode\":\$exit_code,\"duration\":\$duration,\"cwd\":\"\$cwd_safe\"}"
    
    # 로그 파일에 안전하게 추가 (동기적으로, job control 메시지 없음)
    echo "\$log_entry" >> "${logPath}" 2>/dev/null || true
    
    unset SAYU_CMD SAYU_CMD_START
  fi
}

# zsh hook 등록 (안전하게)
autoload -U add-zsh-hook
add-zsh-hook preexec sayu_preexec
add-zsh-hook precmd sayu_precmd
`;
  }

  private updateZshrc(): void {
    const zshrcPath = path.join(os.homedir(), '.zshrc');
    const hookPath = this.getHookPath();
    const sourceLine = `# Sayu CLI tracking\nsource "${hookPath}"\n`;
    
    // .zshrc가 존재하지 않으면 생성
    if (!fs.existsSync(zshrcPath)) {
      fs.writeFileSync(zshrcPath, sourceLine, 'utf-8');
      return;
    }
    
    // 이미 추가되어 있는지 확인
    const content = fs.readFileSync(zshrcPath, 'utf-8');
    if (content.includes(hookPath)) {
      return; // 이미 설치됨
    }
    
    // .zshrc 끝에 추가
    fs.appendFileSync(zshrcPath, '\n' + sourceLine);
  }

  private isRepoRelated(cmdCwd: string): boolean {
    // 현재 레포 또는 하위 디렉토리에서 실행된 커맨드인지 확인
    return cmdCwd.startsWith(this.repoRoot);
  }

  private entryToEvent(entry: any): Event {
    // 커맨드 종류 판단
    const kind = this.categorizeCommand(entry.cmd);
    
    return {
      id: randomUUID(),
      ts: entry.ts,
      source: 'cli',
      kind,
      repo: this.repoRoot,
      cwd: entry.cwd,
      file: null,
      range: null,
      actor: 'user',
      text: entry.cmd,
      url: null,
      meta: {
        exitCode: entry.exitCode,
        duration: entry.duration,
        success: entry.exitCode === 0
      }
    };
  }

  private categorizeCommand(cmd: string): 'test' | 'run' | 'bench' | 'error' {
    const command = cmd.trim().split(' ')[0].toLowerCase();
    
    // 테스트 관련
    if (['npm test', 'yarn test', 'jest', 'pytest', 'go test', 'cargo test'].some(test => cmd.includes(test))) {
      return 'test';
    }
    
    // 빌드 관련
    if (['npm run build', 'yarn build', 'make', 'cargo build', 'go build'].some(build => cmd.includes(build))) {
      return 'run';
    }
    
    // Git 관련
    if (command === 'git') {
      return 'run';
    }
    
    // 벤치마크/성능
    if (['benchmark', 'bench', 'perf'].some(bench => cmd.includes(bench))) {
      return 'bench';
    }
    
    // 에러 발생 시
    if (cmd.includes('error') || cmd.includes('failed')) {
      return 'error';
    }
    
    // 기본값
    return 'run';
  }
}
