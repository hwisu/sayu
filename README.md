# 사유(Sayu) - 커밋에 '왜'를 남기는 개인 로컬 블랙박스

> "이 변경의 이유"를 LLM 대화 기록으로 자동 추적하는 Git 컨텍스트 수집 도구

## 🎯 목적

시간이 지나면 "왜 이런 변경을 했는지" 배경이 사라집니다. Sayu는 커밋 시점에 **Claude/Cursor LLM 대화 기록**을 자동으로 분석하여 변경의 **의도, 접근법, 맥락**을 구조화된 한글로 기록합니다.

## ✨ 주요 기능

- **🤖 LLM 대화 수집**: Claude, Cursor의 실시간 대화 기록 자동 추출
- **🧠 스마트 필터링**: 효용성 기반으로 중요한 대화만 선별 (93% 노이즈 제거)
- **🇰🇷 한글 컨텍스트**: LLM이 한글로 의도/변경사항/접근법/맥락 분석
- **🔍 대화 과정 분석**: 질문 패턴, 문제 해결 과정, 특이점 자동 감지
- **🛡️ 빈 커밋 검증**: 의미없는 빈 커밋 차단, 설정 변경은 허용
- **🔐 로컬 우선**: 모든 데이터는 로컬 저장 (프라이버시 보호)
- **⚡ Fail-open**: 훅 실패가 커밋을 막지 않음

## 📦 설치

```bash
# 의존성 설치
npm install

# 빌드
npm run build

# 레포지토리에 Sayu 초기화
node dist/cli/index.js init
```

## 🚀 사용법

### 초기화
```bash
# Git 레포지토리에서 실행
sayu init
```

이 명령은:
- `.sayu.yml` 설정 파일 생성
- Git 훅 설치 (commit-msg, post-commit)
- 로컬 SQLite 데이터베이스 초기화 (`~/.sayu/events.db`)

### 상태 확인
```bash
sayu health
```

### 커밋하기
평소처럼 커밋하면 자동으로 LLM 대화 분석 결과가 추가됩니다:

```bash
git add .
git commit -m "Fix authentication bug"
```

결과:
```
Fix authentication bug

---
AI-Context (sayu)
Intent: 사용자 인증 버그 수정을 통해 로그인 실패 문제 해결
Changes: auth.js의 토큰 검증 로직 수정, test/auth.test.js에 새로운 테스트 케이스 추가
Approach: JWT 디코딩 함수의 예외 처리를 개선하고 만료된 토큰 감지 로직 강화
Context: Claude와의 대화에서 토큰 만료 시 에러 처리 방식에 대한 논의와 테스트 케이스 작성 과정 포함
---
```

## 🛠 설정 (.sayu.yml)

```yaml
connectors:
  claude: true      # ✅ Claude 대화 로그 수집 (~/.claude/projects/)
  cursor: true      # ✅ Cursor 대화 DB 수집 (~/Library/Application Support/Cursor/)
  cli:              # ✅ CLI 명령어 추적
    mode: "zsh-preexec"  # "zsh-preexec" | "atuin" | "off"
  git: true         # ✅ Git 이벤트 수집

window:
  beforeCommitHours: 168  # 수집할 시간 범위 (일주일, 금요일→월요일 등 고려)

output:
  commitTrailer: true    # 커밋 메시지에 트레일러 추가
  gitNotes: false       # git notes 생성 (구현 예정)

privacy:
  maskSecrets: false     # 민감 정보 마스킹
  masks: []             # 마스킹할 패턴들
```

## 🔐 API 키 설정 (.env)

LLM 요약 생성을 위해 API 키 중 하나를 설정하세요:

```bash
# Gemini (권장)
GEMINI_API_KEY=your_api_key_here

# 또는 OpenAI
OPENAI_API_KEY=your_api_key_here

# 또는 Anthropic
ANTHROPIC_API_KEY=your_api_key_here
```

## 🏗 아키텍처

```
[LLM Collectors] → [Smart Filter] → [LLM Analysis] → [Git Hooks]
       ↓                ↓              ↓              ↓
Claude/Cursor → Utility-based → Gemini/GPT/Claude → Commit Trailer
    Logs         Selection      Korean Summary      Intent/Changes/
                (93% reduction)   + Process        Approach/Context
                                 Analysis
```

### 🔄 처리 과정
1. **수집**: Claude JSONL, Cursor SQLite에서 대화 추출
2. **필터링**: 도구 사용, 확인 메시지 등 저효용 이벤트 제거
3. **분석**: LLM이 대화 패턴, 문제 해결 과정, 특이점 분석
4. **요약**: 한글로 구조화된 Intent/Changes/Approach/Context 생성

## 📁 프로젝트 구조

```
sayu/
├── src/
│   ├── core/           # 핵심 모듈
│   │   ├── types.ts              # 타입 정의
│   │   ├── database.ts           # SQLite 이벤트 스토어
│   │   ├── config.ts             # 설정 관리
│   │   ├── git-hooks.ts          # Git 훅 관리
│   │   ├── hook-handlers.ts      # 🔥 메인 로직 (LLM 요약, 필터링)
│   │   ├── collector-manager.ts  # 수집기 통합 관리
│   │   └── utils.ts              # 유틸리티
│   ├── collectors/     # 이벤트 수집기
│   │   ├── git.ts               # Git 이벤트
│   │   ├── llm-claude.ts        # 🤖 Claude 대화 (JSONL)
│   │   └── llm-cursor.ts        # 🤖 Cursor 대화 (SQLite)
│   └── cli/           # CLI 명령어
│       └── index.ts             # CLI 진입점
├── dist/              # 빌드 출력
├── .env               # API 키 설정
└── .sayu.yml          # 프로젝트 설정
```

## 🔍 데이터 소스

### LLM 대화 수집
- **Claude**: `~/.claude/projects/{repo}/` JSONL 파일
- **Cursor**: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

### 로컬 DB 저장
이벤트는 `~/.sayu/events.db`에 저장됩니다:

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  ts INTEGER,           -- 타임스탬프
  source TEXT,          -- 'git', 'llm'
  kind TEXT,            -- 'commit', 'chat'
  repo TEXT,            -- 레포지토리 경로
  cwd TEXT,             -- 작업 디렉토리
  file TEXT,            -- 관련 파일
  range TEXT,           -- 코드 범위
  actor TEXT,           -- 'user', 'assistant'
  text TEXT,            -- 이벤트 내용
  url TEXT,             -- URL (있는 경우)
  meta TEXT             -- JSON 메타데이터
);
```

## 🧪 테스트

```bash
# 빌드
npm run build

# 현재 변경사항 미리보기
sayu preview

# 시스템 상태 확인
sayu health

# CLI 추적 관리
sayu cli install    # zsh hook 설치
sayu cli uninstall  # zsh hook 제거
```

## 📝 로드맵

- [x] **Phase 1**: 기초 인프라 (DB, Git 훅, 설정)
- [x] **Phase 2**: Git 수집기 및 규칙 기반 요약  
- [x] **Phase 3**: LLM 수집기 (Claude, Cursor) ✨
- [x] **Phase 4**: 지능형 LLM 요약 (Gemini/GPT/Claude) ✨
- [x] **Phase 5**: 스마트 필터링 & 한글 응답 ✨
- [x] **Phase 6**: 대화 과정 분석 & 특이점 감지 ✨
- [ ] **Phase 7**: CLI/Editor 수집기
- [ ] **Phase 8**: 브라우저 활동 수집
- [ ] **Phase 9**: Git notes 통합

## ⚡ 성능 특징

- **93% 노이즈 제거**: 1200개 이벤트 → 80개 핵심 이벤트로 필터링
- **실시간 처리**: 커밋당 2-3초 내 LLM 분석 완료
- **메모리 효율**: 최대 2시간 범위로 제한, 과도한 데이터 수집 방지
- **안전한 실패**: API 실패 시 간소화된 요약으로 대체

## 🎯 사용자 타겟

- **macOS + Cursor + Claude** 사용자에게 최적화
- 한국어 개발팀/개발자
- LLM 기반 개발 워크플로우 사용자
- 커밋 히스토리 품질을 중시하는 팀

## 🤝 기여

PR과 이슈 환영합니다!

## 📄 라이선스

MIT
