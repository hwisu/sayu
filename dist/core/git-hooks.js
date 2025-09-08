"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.GitHookManager = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const child_process_1 = require("child_process");
class GitHookManager {
    repoRoot;
    hooksDir;
    constructor(repoRoot) {
        this.repoRoot = repoRoot;
        this.hooksDir = path_1.default.join(repoRoot, '.git', 'hooks');
    }
    install() {
        this.ensureHooksDir();
        this.installCommitMsgHook();
        this.installPostCommitHook();
    }
    uninstall() {
        this.removeHook('commit-msg');
        this.removeHook('post-commit');
    }
    ensureHooksDir() {
        if (!fs_1.default.existsSync(this.hooksDir)) {
            fs_1.default.mkdirSync(this.hooksDir, { recursive: true });
        }
    }
    installCommitMsgHook() {
        const hookPath = path_1.default.join(this.hooksDir, 'commit-msg');
        const hookContent = `#!/bin/sh
# Sayu commit-msg hook
# Fail-open: 훅 실패가 커밋을 막지 않음

set +e  # 에러가 발생해도 계속 진행

# 커밋 메시지 파일 경로
COMMIT_MSG_FILE="$1"

# Sayu 실행 (트레일러 추가)
node /Users/hwisookim/sayu/dist/cli/index.js hook commit-msg "$COMMIT_MSG_FILE" 2>/dev/null || true

# 항상 성공 반환 (Fail-open)
exit 0
`;
        this.writeHook(hookPath, hookContent);
    }
    installPostCommitHook() {
        const hookPath = path_1.default.join(this.hooksDir, 'post-commit');
        const hookContent = `#!/bin/sh
# Sayu post-commit hook
# git notes에 상세 카드 저장

set +e  # 에러가 발생해도 계속 진행

# Sayu 실행 (notes 생성)
node /Users/hwisookim/sayu/dist/cli/index.js hook post-commit 2>/dev/null || true

# 항상 성공 반환
exit 0
`;
        this.writeHook(hookPath, hookContent);
    }
    writeHook(hookPath, content) {
        // 기존 훅이 있으면 백업
        if (fs_1.default.existsSync(hookPath)) {
            const backupPath = `${hookPath}.sayu-backup`;
            if (!fs_1.default.existsSync(backupPath)) {
                fs_1.default.copyFileSync(hookPath, backupPath);
                console.log(`Backed up existing hook to ${path_1.default.basename(backupPath)}`);
            }
            // Sayu 훅이 이미 설치되어 있는지 확인
            const existingContent = fs_1.default.readFileSync(hookPath, 'utf-8');
            if (existingContent.includes('Sayu')) {
                console.log(`Sayu hook already installed: ${path_1.default.basename(hookPath)}`);
                return;
            }
            // 기존 훅과 병합
            const mergedContent = this.mergeHooks(existingContent, content);
            fs_1.default.writeFileSync(hookPath, mergedContent);
        }
        else {
            fs_1.default.writeFileSync(hookPath, content);
        }
        // 실행 권한 부여
        fs_1.default.chmodSync(hookPath, '755');
        console.log(`Installed hook: ${path_1.default.basename(hookPath)}`);
    }
    mergeHooks(existing, newHook) {
        // 기존 훅의 shebang 라인 제거
        const existingLines = existing.split('\n');
        const existingWithoutShebang = existingLines
            .filter(line => !line.startsWith('#!'))
            .join('\n');
        // 새 훅과 병합
        return `${newHook}\n\n# === Original hook below ===\n${existingWithoutShebang}`;
    }
    removeHook(hookName) {
        const hookPath = path_1.default.join(this.hooksDir, hookName);
        const backupPath = `${hookPath}.sayu-backup`;
        if (!fs_1.default.existsSync(hookPath)) {
            return;
        }
        const content = fs_1.default.readFileSync(hookPath, 'utf-8');
        // Sayu 훅이 포함되어 있는지 확인
        if (!content.includes('Sayu')) {
            console.log(`No Sayu hook found in ${hookName}`);
            return;
        }
        // 백업이 있으면 복원
        if (fs_1.default.existsSync(backupPath)) {
            fs_1.default.copyFileSync(backupPath, hookPath);
            fs_1.default.unlinkSync(backupPath);
            console.log(`Restored original ${hookName} hook`);
        }
        else {
            // 백업이 없으면 삭제
            fs_1.default.unlinkSync(hookPath);
            console.log(`Removed ${hookName} hook`);
        }
    }
    static isGitRepo(dir) {
        try {
            (0, child_process_1.execSync)('git rev-parse --git-dir', {
                cwd: dir,
                stdio: 'ignore'
            });
            return true;
        }
        catch {
            return false;
        }
    }
    static getRepoRoot(dir = process.cwd()) {
        try {
            const root = (0, child_process_1.execSync)('git rev-parse --show-toplevel', {
                cwd: dir,
                encoding: 'utf-8'
            }).trim();
            return root;
        }
        catch {
            return null;
        }
    }
}
exports.GitHookManager = GitHookManager;
//# sourceMappingURL=git-hooks.js.map