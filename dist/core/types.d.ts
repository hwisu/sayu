import { z } from 'zod';
export declare const EventSource: z.ZodEnum<["llm", "editor", "cli", "browser", "git"]>;
export type EventSource = z.infer<typeof EventSource>;
export declare const EventKind: z.ZodEnum<["chat", "edit", "save", "run", "nav", "commit", "test", "bench", "error", "doc"]>;
export type EventKind = z.infer<typeof EventKind>;
export declare const Actor: z.ZodEnum<["user", "assistant", "system"]>;
export type Actor = z.infer<typeof Actor>;
export declare const Range: z.ZodObject<{
    start: z.ZodNumber;
    end: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    start: number;
    end: number;
}, {
    start: number;
    end: number;
}>;
export type Range = z.infer<typeof Range>;
export declare const Event: z.ZodObject<{
    id: z.ZodString;
    ts: z.ZodNumber;
    source: z.ZodEnum<["llm", "editor", "cli", "browser", "git"]>;
    kind: z.ZodEnum<["chat", "edit", "save", "run", "nav", "commit", "test", "bench", "error", "doc"]>;
    repo: z.ZodString;
    cwd: z.ZodString;
    file: z.ZodNullable<z.ZodString>;
    range: z.ZodNullable<z.ZodObject<{
        start: z.ZodNumber;
        end: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        start: number;
        end: number;
    }, {
        start: number;
        end: number;
    }>>;
    actor: z.ZodNullable<z.ZodEnum<["user", "assistant", "system"]>>;
    text: z.ZodString;
    url: z.ZodNullable<z.ZodString>;
    meta: z.ZodDefault<z.ZodRecord<z.ZodString, z.ZodAny>>;
}, "strip", z.ZodTypeAny, {
    id: string;
    ts: number;
    source: "llm" | "editor" | "cli" | "browser" | "git";
    kind: "chat" | "edit" | "save" | "run" | "nav" | "commit" | "test" | "bench" | "error" | "doc";
    repo: string;
    cwd: string;
    file: string | null;
    range: {
        start: number;
        end: number;
    } | null;
    actor: "user" | "assistant" | "system" | null;
    text: string;
    url: string | null;
    meta: Record<string, any>;
}, {
    id: string;
    ts: number;
    source: "llm" | "editor" | "cli" | "browser" | "git";
    kind: "chat" | "edit" | "save" | "run" | "nav" | "commit" | "test" | "bench" | "error" | "doc";
    repo: string;
    cwd: string;
    file: string | null;
    range: {
        start: number;
        end: number;
    } | null;
    actor: "user" | "assistant" | "system" | null;
    text: string;
    url: string | null;
    meta?: Record<string, any> | undefined;
}>;
export type Event = z.infer<typeof Event>;
export declare const ConnectorConfig: z.ZodObject<{
    claude: z.ZodDefault<z.ZodBoolean>;
    cursor: z.ZodDefault<z.ZodBoolean>;
    editor: z.ZodDefault<z.ZodBoolean>;
    cli: z.ZodDefault<z.ZodObject<{
        mode: z.ZodDefault<z.ZodEnum<["zsh-preexec", "atuin", "off"]>>;
    }, "strip", z.ZodTypeAny, {
        mode: "zsh-preexec" | "atuin" | "off";
    }, {
        mode?: "zsh-preexec" | "atuin" | "off" | undefined;
    }>>;
    browser: z.ZodDefault<z.ZodObject<{
        mode: z.ZodDefault<z.ZodEnum<["extension", "activitywatch", "off"]>>;
    }, "strip", z.ZodTypeAny, {
        mode: "off" | "extension" | "activitywatch";
    }, {
        mode?: "off" | "extension" | "activitywatch" | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    editor: boolean;
    cli: {
        mode: "zsh-preexec" | "atuin" | "off";
    };
    browser: {
        mode: "off" | "extension" | "activitywatch";
    };
    claude: boolean;
    cursor: boolean;
}, {
    editor?: boolean | undefined;
    cli?: {
        mode?: "zsh-preexec" | "atuin" | "off" | undefined;
    } | undefined;
    browser?: {
        mode?: "off" | "extension" | "activitywatch" | undefined;
    } | undefined;
    claude?: boolean | undefined;
    cursor?: boolean | undefined;
}>;
export declare const WindowConfig: z.ZodObject<{
    beforeCommitHours: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    beforeCommitHours: number;
}, {
    beforeCommitHours?: number | undefined;
}>;
export declare const FilterConfig: z.ZodObject<{
    domainAllowlist: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    noise: z.ZodDefault<z.ZodObject<{
        graceMinutes: z.ZodDefault<z.ZodNumber>;
        minScore: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        graceMinutes: number;
        minScore: number;
    }, {
        graceMinutes?: number | undefined;
        minScore?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    domainAllowlist: string[];
    noise: {
        graceMinutes: number;
        minScore: number;
    };
}, {
    domainAllowlist?: string[] | undefined;
    noise?: {
        graceMinutes?: number | undefined;
        minScore?: number | undefined;
    } | undefined;
}>;
export declare const SummarizerConfig: z.ZodObject<{
    mode: z.ZodDefault<z.ZodEnum<["rules", "llm", "hybrid"]>>;
    maxLines: z.ZodDefault<z.ZodObject<{
        commit: z.ZodDefault<z.ZodNumber>;
        notes: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        commit: number;
        notes: number;
    }, {
        commit?: number | undefined;
        notes?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    mode: "llm" | "rules" | "hybrid";
    maxLines: {
        commit: number;
        notes: number;
    };
}, {
    mode?: "llm" | "rules" | "hybrid" | undefined;
    maxLines?: {
        commit?: number | undefined;
        notes?: number | undefined;
    } | undefined;
}>;
export declare const PrivacyConfig: z.ZodObject<{
    maskSecrets: z.ZodDefault<z.ZodBoolean>;
    masks: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    maskSecrets: boolean;
    masks: string[];
}, {
    maskSecrets?: boolean | undefined;
    masks?: string[] | undefined;
}>;
export declare const OutputConfig: z.ZodObject<{
    commitTrailer: z.ZodDefault<z.ZodBoolean>;
    gitNotes: z.ZodDefault<z.ZodBoolean>;
    notesRef: z.ZodDefault<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    commitTrailer: boolean;
    gitNotes: boolean;
    notesRef: string;
}, {
    commitTrailer?: boolean | undefined;
    gitNotes?: boolean | undefined;
    notesRef?: string | undefined;
}>;
export declare const Config: z.ZodObject<{
    connectors: z.ZodDefault<z.ZodObject<{
        claude: z.ZodDefault<z.ZodBoolean>;
        cursor: z.ZodDefault<z.ZodBoolean>;
        editor: z.ZodDefault<z.ZodBoolean>;
        cli: z.ZodDefault<z.ZodObject<{
            mode: z.ZodDefault<z.ZodEnum<["zsh-preexec", "atuin", "off"]>>;
        }, "strip", z.ZodTypeAny, {
            mode: "zsh-preexec" | "atuin" | "off";
        }, {
            mode?: "zsh-preexec" | "atuin" | "off" | undefined;
        }>>;
        browser: z.ZodDefault<z.ZodObject<{
            mode: z.ZodDefault<z.ZodEnum<["extension", "activitywatch", "off"]>>;
        }, "strip", z.ZodTypeAny, {
            mode: "off" | "extension" | "activitywatch";
        }, {
            mode?: "off" | "extension" | "activitywatch" | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        editor: boolean;
        cli: {
            mode: "zsh-preexec" | "atuin" | "off";
        };
        browser: {
            mode: "off" | "extension" | "activitywatch";
        };
        claude: boolean;
        cursor: boolean;
    }, {
        editor?: boolean | undefined;
        cli?: {
            mode?: "zsh-preexec" | "atuin" | "off" | undefined;
        } | undefined;
        browser?: {
            mode?: "off" | "extension" | "activitywatch" | undefined;
        } | undefined;
        claude?: boolean | undefined;
        cursor?: boolean | undefined;
    }>>;
    window: z.ZodDefault<z.ZodObject<{
        beforeCommitHours: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        beforeCommitHours: number;
    }, {
        beforeCommitHours?: number | undefined;
    }>>;
    filter: z.ZodDefault<z.ZodObject<{
        domainAllowlist: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
        noise: z.ZodDefault<z.ZodObject<{
            graceMinutes: z.ZodDefault<z.ZodNumber>;
            minScore: z.ZodDefault<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            graceMinutes: number;
            minScore: number;
        }, {
            graceMinutes?: number | undefined;
            minScore?: number | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        domainAllowlist: string[];
        noise: {
            graceMinutes: number;
            minScore: number;
        };
    }, {
        domainAllowlist?: string[] | undefined;
        noise?: {
            graceMinutes?: number | undefined;
            minScore?: number | undefined;
        } | undefined;
    }>>;
    summarizer: z.ZodDefault<z.ZodObject<{
        mode: z.ZodDefault<z.ZodEnum<["rules", "llm", "hybrid"]>>;
        maxLines: z.ZodDefault<z.ZodObject<{
            commit: z.ZodDefault<z.ZodNumber>;
            notes: z.ZodDefault<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            commit: number;
            notes: number;
        }, {
            commit?: number | undefined;
            notes?: number | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        mode: "llm" | "rules" | "hybrid";
        maxLines: {
            commit: number;
            notes: number;
        };
    }, {
        mode?: "llm" | "rules" | "hybrid" | undefined;
        maxLines?: {
            commit?: number | undefined;
            notes?: number | undefined;
        } | undefined;
    }>>;
    privacy: z.ZodDefault<z.ZodObject<{
        maskSecrets: z.ZodDefault<z.ZodBoolean>;
        masks: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        maskSecrets: boolean;
        masks: string[];
    }, {
        maskSecrets?: boolean | undefined;
        masks?: string[] | undefined;
    }>>;
    output: z.ZodDefault<z.ZodObject<{
        commitTrailer: z.ZodDefault<z.ZodBoolean>;
        gitNotes: z.ZodDefault<z.ZodBoolean>;
        notesRef: z.ZodDefault<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        commitTrailer: boolean;
        gitNotes: boolean;
        notesRef: string;
    }, {
        commitTrailer?: boolean | undefined;
        gitNotes?: boolean | undefined;
        notesRef?: string | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    filter: {
        domainAllowlist: string[];
        noise: {
            graceMinutes: number;
            minScore: number;
        };
    };
    connectors: {
        editor: boolean;
        cli: {
            mode: "zsh-preexec" | "atuin" | "off";
        };
        browser: {
            mode: "off" | "extension" | "activitywatch";
        };
        claude: boolean;
        cursor: boolean;
    };
    window: {
        beforeCommitHours: number;
    };
    summarizer: {
        mode: "llm" | "rules" | "hybrid";
        maxLines: {
            commit: number;
            notes: number;
        };
    };
    privacy: {
        maskSecrets: boolean;
        masks: string[];
    };
    output: {
        commitTrailer: boolean;
        gitNotes: boolean;
        notesRef: string;
    };
}, {
    filter?: {
        domainAllowlist?: string[] | undefined;
        noise?: {
            graceMinutes?: number | undefined;
            minScore?: number | undefined;
        } | undefined;
    } | undefined;
    connectors?: {
        editor?: boolean | undefined;
        cli?: {
            mode?: "zsh-preexec" | "atuin" | "off" | undefined;
        } | undefined;
        browser?: {
            mode?: "off" | "extension" | "activitywatch" | undefined;
        } | undefined;
        claude?: boolean | undefined;
        cursor?: boolean | undefined;
    } | undefined;
    window?: {
        beforeCommitHours?: number | undefined;
    } | undefined;
    summarizer?: {
        mode?: "llm" | "rules" | "hybrid" | undefined;
        maxLines?: {
            commit?: number | undefined;
            notes?: number | undefined;
        } | undefined;
    } | undefined;
    privacy?: {
        maskSecrets?: boolean | undefined;
        masks?: string[] | undefined;
    } | undefined;
    output?: {
        commitTrailer?: boolean | undefined;
        gitNotes?: boolean | undefined;
        notesRef?: string | undefined;
    } | undefined;
}>;
export type Config = z.infer<typeof Config>;
export interface Connector {
    id: string;
    discover(repoRoot: string): Promise<boolean>;
    pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]>;
    health(): Promise<{
        ok: boolean;
        reason?: string;
    }>;
    redact?(event: Event, cfg: Config): Event;
}
//# sourceMappingURL=types.d.ts.map