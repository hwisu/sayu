import { Connector, Event, Config } from '../core/types';
export declare class GitCollector implements Connector {
    id: string;
    private git;
    private repoRoot;
    constructor(repoRoot?: string);
    discover(repoRoot: string): Promise<boolean>;
    pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]>;
    health(): Promise<{
        ok: boolean;
        reason?: string;
    }>;
    redact(event: Event, cfg: Config): Event;
    private parseFileChanges;
    private mapStatus;
    getCurrentCommitContext(): Promise<{
        files: string[];
        diff: string;
        message?: string;
    }>;
    getLastCommit(): Promise<{
        hash: string;
        message: string;
        timestamp: number;
    } | null>;
}
//# sourceMappingURL=git.d.ts.map