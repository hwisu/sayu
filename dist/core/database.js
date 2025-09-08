"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.EventStore = void 0;
const better_sqlite3_1 = __importDefault(require("better-sqlite3"));
const path_1 = __importDefault(require("path"));
const os_1 = __importDefault(require("os"));
const fs_1 = __importDefault(require("fs"));
class EventStore {
    db;
    insertStmt;
    searchByTimeStmt;
    searchByFileStmt;
    searchByRepoStmt;
    constructor(dbPath) {
        const defaultPath = path_1.default.join(os_1.default.homedir(), '.sayu', 'events.db');
        const finalPath = dbPath || defaultPath;
        // 디렉토리 생성
        const dir = path_1.default.dirname(finalPath);
        if (!fs_1.default.existsSync(dir)) {
            fs_1.default.mkdirSync(dir, { recursive: true });
        }
        this.db = new better_sqlite3_1.default(finalPath);
        this.initSchema();
        this.prepareStatements();
    }
    initSchema() {
        // 메인 이벤트 테이블
        this.db.exec(`
      CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        ts INTEGER NOT NULL,
        source TEXT NOT NULL,
        kind TEXT NOT NULL,
        repo TEXT NOT NULL,
        cwd TEXT NOT NULL,
        file TEXT,
        range_start INTEGER,
        range_end INTEGER,
        actor TEXT,
        text TEXT NOT NULL,
        url TEXT,
        meta TEXT NOT NULL DEFAULT '{}'
      );

      CREATE INDEX IF NOT EXISTS idx_events_repo_ts ON events(repo, ts);
      CREATE INDEX IF NOT EXISTS idx_events_file_ts ON events(file, ts) WHERE file IS NOT NULL;
      CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
      CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
    `);
        // FTS5 가상 테이블
        this.db.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
        text,
        content='events',
        content_rowid='rowid'
      );

      CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
        INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
      END;

      CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
        DELETE FROM events_fts WHERE rowid = old.rowid;
      END;

      CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE OF text ON events BEGIN
        UPDATE events_fts SET text = new.text WHERE rowid = new.rowid;
      END;
    `);
    }
    prepareStatements() {
        this.insertStmt = this.db.prepare(`
      INSERT INTO events (
        id, ts, source, kind, repo, cwd, file, 
        range_start, range_end, actor, text, url, meta
      ) VALUES (
        @id, @ts, @source, @kind, @repo, @cwd, @file,
        @range_start, @range_end, @actor, @text, @url, @meta
      )
    `);
        this.searchByTimeStmt = this.db.prepare(`
      SELECT * FROM events 
      WHERE ts >= ? AND ts <= ? 
      ORDER BY ts DESC
    `);
        this.searchByFileStmt = this.db.prepare(`
      SELECT * FROM events 
      WHERE file = ? AND ts >= ? AND ts <= ?
      ORDER BY ts DESC
    `);
        this.searchByRepoStmt = this.db.prepare(`
      SELECT * FROM events 
      WHERE repo = ? AND ts >= ? AND ts <= ?
      ORDER BY ts DESC
    `);
    }
    insert(event) {
        const row = {
            id: event.id,
            ts: event.ts,
            source: event.source,
            kind: event.kind,
            repo: event.repo,
            cwd: event.cwd,
            file: event.file,
            range_start: event.range?.start ?? null,
            range_end: event.range?.end ?? null,
            actor: event.actor,
            text: event.text,
            url: event.url,
            meta: JSON.stringify(event.meta)
        };
        this.insertStmt.run(row);
    }
    insertBatch(events) {
        const transaction = this.db.transaction((events) => {
            for (const event of events) {
                this.insert(event);
            }
        });
        transaction(events);
    }
    findByTimeRange(startMs, endMs) {
        const rows = this.searchByTimeStmt.all(startMs, endMs);
        return rows.map(this.rowToEvent);
    }
    findByFile(file, startMs, endMs) {
        const rows = this.searchByFileStmt.all(file, startMs, endMs);
        return rows.map(this.rowToEvent);
    }
    findByRepo(repo, startMs, endMs) {
        const rows = this.searchByRepoStmt.all(repo, startMs, endMs);
        return rows.map(this.rowToEvent);
    }
    searchText(query, limit = 100) {
        const stmt = this.db.prepare(`
      SELECT e.* FROM events e
      JOIN events_fts ON e.rowid = events_fts.rowid
      WHERE events_fts MATCH ?
      ORDER BY rank
      LIMIT ?
    `);
        const rows = stmt.all(query, limit);
        return rows.map(this.rowToEvent);
    }
    rowToEvent(row) {
        return {
            id: row.id,
            ts: row.ts,
            source: row.source,
            kind: row.kind,
            repo: row.repo,
            cwd: row.cwd,
            file: row.file,
            range: row.range_start && row.range_end
                ? { start: row.range_start, end: row.range_end }
                : null,
            actor: row.actor,
            text: row.text,
            url: row.url,
            meta: JSON.parse(row.meta || '{}')
        };
    }
    getLastCommitTime(repo) {
        const stmt = this.db.prepare(`
      SELECT MAX(ts) as last_ts FROM events 
      WHERE repo = ? AND kind = 'commit'
    `);
        const row = stmt.get(repo);
        return row?.last_ts || null;
    }
    close() {
        this.db.close();
    }
}
exports.EventStore = EventStore;
//# sourceMappingURL=database.js.map