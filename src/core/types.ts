import { z } from 'zod';

// 이벤트 소스 타입
export const EventSource = z.enum(['llm', 'editor', 'cli', 'browser', 'git']);
export type EventSource = z.infer<typeof EventSource>;

// 이벤트 종류
export const EventKind = z.enum([
  'chat', 'edit', 'save', 'run', 'nav', 'commit', 
  'test', 'bench', 'error', 'doc'
]);
export type EventKind = z.infer<typeof EventKind>;

// 액터 타입
export const Actor = z.enum(['user', 'assistant', 'system']);
export type Actor = z.infer<typeof Actor>;

// 범위 정의
export const Range = z.object({
  start: z.number(),
  end: z.number()
});
export type Range = z.infer<typeof Range>;

// 이벤트 표준 스키마
export const Event = z.object({
  id: z.string().uuid(),
  ts: z.number(), // epoch milliseconds
  source: EventSource,
  kind: EventKind,
  repo: z.string(),
  cwd: z.string(),
  file: z.string().nullable(),
  range: Range.nullable(),
  actor: Actor.nullable(),
  text: z.string(),
  url: z.string().nullable(),
  meta: z.record(z.any()).default({})
});
export type Event = z.infer<typeof Event>;

// 설정 스키마
export const ConnectorConfig = z.object({
  claude: z.boolean().default(true),
  cursor: z.boolean().default(true),
  editor: z.boolean().default(true),
  cli: z.object({
    mode: z.enum(['zsh-preexec', 'atuin', 'off']).default('zsh-preexec')
  }).default({ mode: 'zsh-preexec' }),
  browser: z.object({
    mode: z.enum(['extension', 'activitywatch', 'off']).default('off')
  }).default({ mode: 'off' })
});

export const WindowConfig = z.object({
  beforeCommitHours: z.number().default(24)
});

export const FilterConfig = z.object({
  domainAllowlist: z.array(z.string()).default([
    'github.com',
    'developer.mozilla.org',
    'stackoverflow.com'
  ]),
  noise: z.object({
    graceMinutes: z.number().default(5),
    minScore: z.number().default(0.6)
  }).default({ graceMinutes: 5, minScore: 0.6 })
});

export const SummarizerConfig = z.object({
  mode: z.enum(['rules', 'llm', 'hybrid']).default('hybrid'),
  maxLines: z.object({
    commit: z.number().default(12),
    notes: z.number().default(25)
  }).default({ commit: 12, notes: 25 })
});

export const PrivacyConfig = z.object({
  maskSecrets: z.boolean().default(true),
  masks: z.array(z.string()).default([
    'AKIA[0-9A-Z]{16}',
    '(?i)authorization:\\s*Bearer\\s+[A-Za-z0-9._-]+'
  ])
});

export const OutputConfig = z.object({
  commitTrailer: z.boolean().default(true),
  gitNotes: z.boolean().default(true),
  notesRef: z.string().default('refs/notes/sayu')
});

export const Config = z.object({
  connectors: ConnectorConfig.default({}),
  window: WindowConfig.default({}),
  filter: FilterConfig.default({}),
  summarizer: SummarizerConfig.default({}),
  privacy: PrivacyConfig.default({}),
  output: OutputConfig.default({})
});
export type Config = z.infer<typeof Config>;

// 커넥터 인터페이스
export interface Connector {
  id: string;
  discover(repoRoot: string): Promise<boolean>;
  pullSince(sinceMs: number, untilMs: number, cfg: Config): Promise<Event[]>;
  health(): Promise<{ ok: boolean; reason?: string }>;
  redact?(event: Event, cfg: Config): Event;
}