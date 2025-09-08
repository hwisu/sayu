"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.HookHandlers = void 0;
const fs_1 = __importDefault(require("fs"));
const collector_manager_1 = require("./collector-manager");
const config_1 = require("./config");
const git_hooks_1 = require("./git-hooks");
class HookHandlers {
    // commit-msg 훅 핸들러
    static async handleCommitMsg(commitMsgFile) {
        try {
            const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
            if (!repoRoot)
                return;
            const config = new config_1.ConfigManager(repoRoot).get();
            if (!config.output.commitTrailer)
                return;
            const collector = new collector_manager_1.CollectorManager(repoRoot);
            // 1. 현재 커밋 컨텍스트 수집
            const currentEvents = await collector.collectCurrentCommit();
            // 2. 시간 창 내 관련 이벤트 수집
            const timeWindowEvents = await collector.collectInTimeWindow(config.window.beforeCommitHours);
            // 3. 간단한 요약 생성
            const summary = this.generateSimpleSummary(currentEvents, timeWindowEvents);
            // 4. 커밋 메시지에 트레일러 추가
            if (summary) {
                const currentMsg = fs_1.default.readFileSync(commitMsgFile, 'utf-8');
                // 이미 Sayu 트레일러가 있으면 스킵
                if (currentMsg.includes('AI-Context (sayu)')) {
                    return;
                }
                const newMsg = currentMsg.trimEnd() + '\n\n' + summary;
                fs_1.default.writeFileSync(commitMsgFile, newMsg);
            }
            collector.close();
        }
        catch (error) {
            // Fail-open: 에러 발생해도 커밋은 계속
            console.error('Sayu commit-msg hook error:', error);
        }
    }
    // post-commit 훅 핸들러
    static async handlePostCommit() {
        try {
            const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
            if (!repoRoot)
                return;
            const config = new config_1.ConfigManager(repoRoot).get();
            if (!config.output.gitNotes)
                return;
            // TODO: git notes에 상세 정보 저장
            console.log('Post-commit: Would save detailed notes here');
        }
        catch (error) {
            console.error('Sayu post-commit hook error:', error);
        }
    }
    // 간단한 규칙 기반 요약 생성
    static generateSimpleSummary(currentEvents, timeWindowEvents) {
        const lines = [];
        lines.push('---');
        lines.push('AI-Context (sayu)');
        // Changed files
        const changedFiles = currentEvents
            .filter(e => e.file && e.kind === 'edit')
            .map(e => e.file);
        if (changedFiles.length > 0) {
            const fileList = changedFiles.slice(0, 3).join(', ');
            const more = changedFiles.length > 3 ? ` (+${changedFiles.length - 3} more)` : '';
            lines.push(`What: Modified ${fileList}${more}`);
        }
        // Recent commits (context)
        const recentCommits = timeWindowEvents
            .filter(e => e.kind === 'commit' && e.meta?.hash)
            .slice(0, 2);
        if (recentCommits.length > 0) {
            lines.push(`Context: ${recentCommits.length} recent commits in last ${this.formatTime(Date.now() - recentCommits[0].ts)}`);
        }
        // Test/error events
        const testEvents = timeWindowEvents.filter(e => e.kind === 'test');
        const errorEvents = timeWindowEvents.filter(e => e.kind === 'error');
        if (testEvents.length > 0) {
            lines.push(`Tests: ${testEvents.length} test runs`);
        }
        if (errorEvents.length > 0) {
            lines.push(`Errors: ${errorEvents.length} errors encountered`);
        }
        // Stats
        const totalEvents = currentEvents.length + timeWindowEvents.length;
        lines.push(`Events: ${totalEvents} tracked`);
        lines.push(`Confidence: ★★☆☆ (rule-based)`);
        lines.push('---');
        return lines.join('\n');
    }
    static formatTime(ms) {
        const hours = Math.floor(ms / (1000 * 60 * 60));
        const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }
}
exports.HookHandlers = HookHandlers;
//# sourceMappingURL=hook-handlers.js.map