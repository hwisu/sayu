/**
 * Sayu 시스템 상수 정의
 * Opinionated 기본값들을 여기서 관리
 */

// 시간 관련 상수 (밀리초)
export const TIME_CONSTANTS = {
  COMMIT_WINDOW_HOURS: 24,           // 커밋 전 몇 시간의 이벤트를 수집할지
  GRACE_PERIOD_MINUTES: 5,          // 커밋 전후 여유 시간
  DEFAULT_LOOKBACK_HOURS: 168,      // 기본 일주일 (첫 커밋시)
} as const;

// 텍스트 처리 상수
export const TEXT_CONSTANTS = {
  MAX_CONVERSATION_COUNT: 20,        // LLM 대화 최대 개수
  MAX_CONVERSATION_LENGTH: 800,      // LLM 대화 최대 길이
  MAX_SIMPLIFIED_CONVERSATIONS: 10,  // 간단 모드 대화 개수
  MAX_SIMPLIFIED_LENGTH: 400,        // 간단 모드 대화 길이
  MAX_HIGH_VALUE_EVENTS: 80,         // 고가치 이벤트 최대 개수
  MAX_DIFF_LENGTH: 2000,             // Diff 내용 최대 길이
  MIN_RESPONSE_LENGTH: 50,           // 최소 응답 길이
  MAX_COMMIT_TRAILER_LINES: 12,      // 커밋 트레일러 최대 줄 수
  MAX_LINE_LENGTH: 80,               // 텍스트 줄바꿈 최대 길이
  MAX_RAW_RESPONSE_LENGTH: 2000,     // 원시 응답 최대 길이
  MAX_FILE_DISPLAY: 3,               // 표시할 최대 파일 개수
} as const;

// LLM API 상수
export const LLM_CONSTANTS = {
  TEMPERATURE: 0.1,                  // Gemini 온도
  MAX_OUTPUT_TOKENS: 8192,           // Gemini 최대 토큰
  OPENAI_TEMPERATURE: 0.3,           // OpenAI 온도
  OPENAI_MAX_TOKENS: 1000,           // OpenAI 최대 토큰
  ANTHROPIC_TEMPERATURE: 0.3,        // Anthropic 온도
  ANTHROPIC_MAX_TOKENS: 1000,        // Anthropic 최대 토큰
} as const;

// 필터링 상수
export const FILTER_CONSTANTS = {
  MIN_RELEVANCE_SCORE: 0.6,          // 최소 관련성 점수
  DEFAULT_DOMAIN_ALLOWLIST: [        // 기본 허용 도메인
    'github.com',
    'developer.mozilla.org',
    'stackoverflow.com'
  ],
} as const;

// 기본 보안 마스킹 패턴
export const DEFAULT_SECURITY_MASKS = [
  'AKIA[0-9A-Z]{16}',                      // AWS Access Key
  '(?i)authorization:\\s*Bearer\\s+[A-Za-z0-9._-]+',  // Bearer 토큰
  '(?i)api[_-]?key[\'\"\\s]*[:=][\'\"\\s]*[A-Za-z0-9]{20,}',  // API 키
  '(?i)secret[\'\"\\s]*[:=][\'\"\\s]*[A-Za-z0-9]{10,}',      // Secret
] as const;
