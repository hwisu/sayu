export declare class GitHookManager {
    private repoRoot;
    private hooksDir;
    constructor(repoRoot: string);
    install(): void;
    uninstall(): void;
    private ensureHooksDir;
    private installCommitMsgHook;
    private installPostCommitHook;
    private writeHook;
    private mergeHooks;
    private removeHook;
    static isGitRepo(dir: string): boolean;
    static getRepoRoot(dir?: string): string | null;
}
//# sourceMappingURL=git-hooks.d.ts.map