import fs from 'fs';
import path from 'path';
import { ShellExecutor } from './shell';

export class GitHookManager {
  private repoRoot: string;
  private hooksDir: string;

  constructor(repoRoot: string) {
    this.repoRoot = repoRoot;
    this.hooksDir = path.join(repoRoot, '.git', 'hooks');
  }

  install(): void {
    this.ensureHooksDir();
    this.installCommitMsgHook();
    this.installPostCommitHook();
  }

  uninstall(): void {
    this.removeHook('commit-msg');
    this.removeHook('post-commit');
  }

  private ensureHooksDir(): void {
    if (!fs.existsSync(this.hooksDir)) {
      fs.mkdirSync(this.hooksDir, { recursive: true });
    }
  }

  private installCommitMsgHook(): void {
    const hookPath = path.join(this.hooksDir, 'commit-msg');
    const hookContent = `#!/bin/sh
# Sayu commit-msg hook
# Fail-open: 훅 실패가 커밋을 막지 않음

set +e  # 에러가 발생해도 계속 진행

# 커밋 메시지 파일 경로
COMMIT_MSG_FILE="$1"

# Sayu 실행 경로 찾기 (글로벌 설치 우선, 로컬 개발 환경 폴백)
SAYU_CMD=""
if command -v sayu >/dev/null 2>&1; then
  SAYU_CMD="sayu"
elif [ -f "${this.repoRoot}/dist/cli/index.js" ]; then
  SAYU_CMD="node ${this.repoRoot}/dist/cli/index.js"
else
  echo "Warning: Sayu not found, skipping commit-msg hook" >&2
  exit 0
fi

# Sayu 실행 (트레일러 추가)
$SAYU_CMD hook commit-msg "$COMMIT_MSG_FILE" 2>/dev/null || true

# 항상 성공 반환 (Fail-open)
exit 0
`;

    this.writeHook(hookPath, hookContent);
  }

  private installPostCommitHook(): void {
    const hookPath = path.join(this.hooksDir, 'post-commit');
    const hookContent = `#!/bin/sh
# Sayu post-commit hook

set +e  # 에러가 발생해도 계속 진행

# Sayu 실행 경로 찾기 (글로벌 설치 우선, 로컬 개발 환경 폴백)
SAYU_CMD=""
if command -v sayu >/dev/null 2>&1; then
  SAYU_CMD="sayu"
elif [ -f "${this.repoRoot}/dist/cli/index.js" ]; then
  SAYU_CMD="node ${this.repoRoot}/dist/cli/index.js"
else
  echo "Warning: Sayu not found, skipping post-commit hook" >&2
  exit 0
fi

# Sayu 실행
$SAYU_CMD hook post-commit 2>/dev/null || true

# 항상 성공 반환
exit 0
`;

    this.writeHook(hookPath, hookContent);
  }

  private writeHook(hookPath: string, content: string): void {
    // 기존 훅이 있으면 백업
    if (fs.existsSync(hookPath)) {
      const backupPath = `${hookPath}.sayu-backup`;
      if (!fs.existsSync(backupPath)) {
        fs.copyFileSync(hookPath, backupPath);
        console.log(`Backed up existing hook to ${path.basename(backupPath)}`);
      }
      
      // Sayu 훅이 이미 설치되어 있는지 확인
      const existingContent = fs.readFileSync(hookPath, 'utf-8');
      if (existingContent.includes('Sayu')) {
        console.log(`Sayu hook already installed: ${path.basename(hookPath)}`);
        return;
      }

      // 기존 훅과 병합
      const mergedContent = this.mergeHooks(existingContent, content);
      fs.writeFileSync(hookPath, mergedContent);
    } else {
      fs.writeFileSync(hookPath, content);
    }

    // 실행 권한 부여
    fs.chmodSync(hookPath, '755');
    console.log(`Installed hook: ${path.basename(hookPath)}`);
  }

  private mergeHooks(existing: string, newHook: string): string {
    // 기존 훅의 shebang 라인 제거
    const existingLines = existing.split('\n');
    const existingWithoutShebang = existingLines
      .filter(line => !line.startsWith('#!'))
      .join('\n');

    // 새 훅과 병합
    return `${newHook}\n\n# === Original hook below ===\n${existingWithoutShebang}`;
  }

  private removeHook(hookName: string): void {
    const hookPath = path.join(this.hooksDir, hookName);
    const backupPath = `${hookPath}.sayu-backup`;

    if (!fs.existsSync(hookPath)) {
      return;
    }

    const content = fs.readFileSync(hookPath, 'utf-8');
    
    // Sayu 훅이 포함되어 있는지 확인
    if (!content.includes('Sayu')) {
      console.log(`No Sayu hook found in ${hookName}`);
      return;
    }

    // 백업이 있으면 복원
    if (fs.existsSync(backupPath)) {
      fs.copyFileSync(backupPath, hookPath);
      fs.unlinkSync(backupPath);
      console.log(`Restored original ${hookName} hook`);
    } else {
      // 백업이 없으면 삭제
      fs.unlinkSync(hookPath);
      console.log(`Removed ${hookName} hook`);
    }
  }

  static isGitRepo(dir: string): boolean {
    try {
      ShellExecutor.gitExec(['rev-parse', '--git-dir'], { 
        cwd: dir, 
        stdio: 'ignore' 
      });
      return true;
    } catch {
      return false;
    }
  }

  static getRepoRoot(dir: string = process.cwd()): string | null {
    try {
      const root = ShellExecutor.gitExec(['rev-parse', '--show-toplevel'], {
        cwd: dir
      }).trim();
      return root;
    } catch {
      return null;
    }
  }
}
