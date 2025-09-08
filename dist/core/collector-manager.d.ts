import { Event } from './types';
export declare class CollectorManager {
    private store;
    private config;
    private gitCollector;
    private repoRoot;
    constructor(repoRoot?: string);
    collectCurrentCommit(): Promise<Event[]>;
    collectInTimeWindow(hours?: number): Promise<Event[]>;
    findRelatedEvents(files: string[], timeWindowMs: number): Promise<Event[]>;
    private generateId;
    close(): void;
}
//# sourceMappingURL=collector-manager.d.ts.map