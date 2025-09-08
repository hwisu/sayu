"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Config = exports.OutputConfig = exports.PrivacyConfig = exports.SummarizerConfig = exports.FilterConfig = exports.WindowConfig = exports.ConnectorConfig = exports.Event = exports.Range = exports.Actor = exports.EventKind = exports.EventSource = void 0;
const zod_1 = require("zod");
// 이벤트 소스 타입
exports.EventSource = zod_1.z.enum(['llm', 'editor', 'cli', 'browser', 'git']);
// 이벤트 종류
exports.EventKind = zod_1.z.enum([
    'chat', 'edit', 'save', 'run', 'nav', 'commit',
    'test', 'bench', 'error', 'doc'
]);
// 액터 타입
exports.Actor = zod_1.z.enum(['user', 'assistant', 'system']);
// 범위 정의
exports.Range = zod_1.z.object({
    start: zod_1.z.number(),
    end: zod_1.z.number()
});
// 이벤트 표준 스키마
exports.Event = zod_1.z.object({
    id: zod_1.z.string().uuid(),
    ts: zod_1.z.number(), // epoch milliseconds
    source: exports.EventSource,
    kind: exports.EventKind,
    repo: zod_1.z.string(),
    cwd: zod_1.z.string(),
    file: zod_1.z.string().nullable(),
    range: exports.Range.nullable(),
    actor: exports.Actor.nullable(),
    text: zod_1.z.string(),
    url: zod_1.z.string().nullable(),
    meta: zod_1.z.record(zod_1.z.any()).default({})
});
// 설정 스키마
exports.ConnectorConfig = zod_1.z.object({
    claude: zod_1.z.boolean().default(true),
    cursor: zod_1.z.boolean().default(true),
    editor: zod_1.z.boolean().default(true),
    cli: zod_1.z.object({
        mode: zod_1.z.enum(['zsh-preexec', 'atuin', 'off']).default('zsh-preexec')
    }).default({ mode: 'zsh-preexec' }),
    browser: zod_1.z.object({
        mode: zod_1.z.enum(['extension', 'activitywatch', 'off']).default('off')
    }).default({ mode: 'off' })
});
exports.WindowConfig = zod_1.z.object({
    beforeCommitHours: zod_1.z.number().default(24)
});
exports.FilterConfig = zod_1.z.object({
    domainAllowlist: zod_1.z.array(zod_1.z.string()).default([
        'github.com',
        'developer.mozilla.org',
        'stackoverflow.com'
    ]),
    noise: zod_1.z.object({
        graceMinutes: zod_1.z.number().default(5),
        minScore: zod_1.z.number().default(0.6)
    }).default({ graceMinutes: 5, minScore: 0.6 })
});
exports.SummarizerConfig = zod_1.z.object({
    mode: zod_1.z.enum(['rules', 'llm', 'hybrid']).default('hybrid'),
    maxLines: zod_1.z.object({
        commit: zod_1.z.number().default(12),
        notes: zod_1.z.number().default(25)
    }).default({ commit: 12, notes: 25 })
});
exports.PrivacyConfig = zod_1.z.object({
    maskSecrets: zod_1.z.boolean().default(true),
    masks: zod_1.z.array(zod_1.z.string()).default([
        'AKIA[0-9A-Z]{16}',
        '(?i)authorization:\\s*Bearer\\s+[A-Za-z0-9._-]+'
    ])
});
exports.OutputConfig = zod_1.z.object({
    commitTrailer: zod_1.z.boolean().default(true),
    gitNotes: zod_1.z.boolean().default(true),
    notesRef: zod_1.z.string().default('refs/notes/sayu')
});
exports.Config = zod_1.z.object({
    connectors: exports.ConnectorConfig.default({}),
    window: exports.WindowConfig.default({}),
    filter: exports.FilterConfig.default({}),
    summarizer: exports.SummarizerConfig.default({}),
    privacy: exports.PrivacyConfig.default({}),
    output: exports.OutputConfig.default({})
});
//# sourceMappingURL=types.js.map