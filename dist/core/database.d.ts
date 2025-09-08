import { Event } from './types';
export declare class EventStore {
    private db;
    private insertStmt;
    private searchByTimeStmt;
    private searchByFileStmt;
    private searchByRepoStmt;
    constructor(dbPath?: string);
    private initSchema;
    private prepareStatements;
    insert(event: Event): void;
    insertBatch(events: Event[]): void;
    findByTimeRange(startMs: number, endMs: number): Event[];
    findByFile(file: string, startMs: number, endMs: number): Event[];
    findByRepo(repo: string, startMs: number, endMs: number): Event[];
    searchText(query: string, limit?: number): Event[];
    private rowToEvent;
    getLastCommitTime(repo: string): number | null;
    close(): void;
}
//# sourceMappingURL=database.d.ts.map