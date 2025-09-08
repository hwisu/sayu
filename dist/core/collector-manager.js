"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CollectorManager = void 0;
const database_1 = require("./database");
const config_1 = require("./config");
const git_1 = require("../collectors/git");
const git_hooks_1 = require("./git-hooks");
class CollectorManager {
    store;
    config;
    gitCollector;
    repoRoot;
    constructor(repoRoot) {
        this.repoRoot = repoRoot || git_hooks_1.GitHookManager.getRepoRoot() || process.cwd();
        this.store = new database_1.EventStore();
        this.config = new config_1.ConfigManager(this.repoRoot).get();
        this.gitCollector = new git_1.GitCollector(this.repoRoot);
    }
    // 현재 스테이징된 변경사항에 대한 이벤트 수집
    async collectCurrentCommit() {
        const events = [];
        const now = Date.now();
        // Git 컬렉터로 현재 상태 수집
        const gitContext = await this.gitCollector.getCurrentCommitContext();
        // 스테이징된 파일들을 이벤트로 변환
        for (const file of gitContext.files) {
            const event = {
                id: this.generateId(),
                ts: now,
                source: 'git',
                kind: 'edit',
                repo: this.repoRoot,
                cwd: this.repoRoot,
                file: file,
                range: null,
                actor: 'user',
                text: `Staged file: ${file}`,
                url: null,
                meta: {
                    staged: true
                }
            };
            events.push(event);
            this.store.insert(event);
        }
        // diff 정보도 이벤트로 저장
        if (gitContext.diff) {
            const diffEvent = {
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
                    fullLength: gitContext.diff.length
                }
            };
            events.push(diffEvent);
            this.store.insert(diffEvent);
        }
        return events;
    }
    // 시간 범위로 이벤트 수집
    async collectInTimeWindow(hours = 24) {
        const now = Date.now();
        const sinceMs = now - (hours * 60 * 60 * 1000);
        // 마지막 커밋 시간 확인
        const lastCommitTime = this.store.getLastCommitTime(this.repoRoot);
        const startTime = lastCommitTime || sinceMs;
        // Git 이벤트 수집
        const gitEvents = await this.gitCollector.pullSince(startTime, now, this.config);
        // DB에 저장
        if (gitEvents.length > 0) {
            this.store.insertBatch(gitEvents);
        }
        // DB에서 시간 창 내 모든 이벤트 조회
        return this.store.findByRepo(this.repoRoot, startTime, now);
    }
    // 관련 이벤트 검색
    async findRelatedEvents(files, timeWindowMs) {
        const events = [];
        const now = Date.now();
        const startTime = now - timeWindowMs;
        // 각 파일에 대한 이벤트 검색
        for (const file of files) {
            const fileEvents = this.store.findByFile(file, startTime, now);
            events.push(...fileEvents);
        }
        // 레포 전체 이벤트도 포함 (커밋, 테스트 등)
        const repoEvents = this.store.findByRepo(this.repoRoot, startTime, now)
            .filter(e => e.kind === 'commit' || e.kind === 'test' || e.kind === 'error');
        events.push(...repoEvents);
        // 중복 제거 및 시간순 정렬
        const uniqueEvents = Array.from(new Map(events.map(e => [e.id, e])).values());
        return uniqueEvents.sort((a, b) => b.ts - a.ts);
    }
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    close() {
        this.store.close();
    }
}
exports.CollectorManager = CollectorManager;
//# sourceMappingURL=collector-manager.js.map