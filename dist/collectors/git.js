"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.GitCollector = void 0;
const simple_git_1 = __importDefault(require("simple-git"));
const crypto_1 = require("crypto");
class GitCollector {
    id = 'git.core';
    git;
    repoRoot;
    constructor(repoRoot) {
        this.repoRoot = repoRoot || process.cwd();
        this.git = (0, simple_git_1.default)(this.repoRoot);
    }
    async discover(repoRoot) {
        try {
            await this.git.checkIsRepo();
            return true;
        }
        catch {
            return false;
        }
    }
    async pullSince(sinceMs, untilMs, cfg) {
        const events = [];
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
                // 커밋 이벤트
                events.push({
                    id: (0, crypto_1.randomUUID)(),
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
                // 변경된 파일들
                const diff = await this.git.show([commit.hash, '--name-status']);
                const fileChanges = this.parseFileChanges(diff);
                for (const change of fileChanges) {
                    events.push({
                        id: (0, crypto_1.randomUUID)(),
                        ts: new Date(commit.date).getTime(),
                        source: 'git',
                        kind: 'edit',
                        repo: this.repoRoot,
                        cwd: this.repoRoot,
                        file: change.file,
                        range: null,
                        actor: 'user',
                        text: `${change.status} ${change.file}`,
                        url: null,
                        meta: {
                            commitHash: commit.hash,
                            changeType: change.status,
                            additions: change.additions,
                            deletions: change.deletions
                        }
                    });
                }
            }
            // 현재 스테이징된 변경사항
            const status = await this.git.status();
            const currentTime = Date.now();
            for (const file of status.staged) {
                events.push({
                    id: (0, crypto_1.randomUUID)(),
                    ts: currentTime,
                    source: 'git',
                    kind: 'edit',
                    repo: this.repoRoot,
                    cwd: this.repoRoot,
                    file: file,
                    range: null,
                    actor: 'user',
                    text: `Staged: ${file}`,
                    url: null,
                    meta: {
                        staged: true
                    }
                });
            }
        }
        catch (error) {
            console.error('GitCollector error:', error);
        }
        return events;
    }
    async health() {
        try {
            const isRepo = await this.git.checkIsRepo();
            if (!isRepo) {
                return { ok: false, reason: 'Not a git repository' };
            }
            return { ok: true };
        }
        catch (error) {
            return { ok: false, reason: error.message };
        }
    }
    redact(event, cfg) {
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
    parseFileChanges(diff) {
        const changes = [];
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
    mapStatus(gitStatus) {
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
    async getCurrentCommitContext() {
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
    async getLastCommit() {
        try {
            const log = await this.git.log({ n: 1 });
            if (log.latest) {
                return {
                    hash: log.latest.hash,
                    message: log.latest.message,
                    timestamp: new Date(log.latest.date).getTime()
                };
            }
        }
        catch {
            // 커밋이 없는 경우
        }
        return null;
    }
}
exports.GitCollector = GitCollector;
//# sourceMappingURL=git.js.map