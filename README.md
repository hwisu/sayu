# Sayu - AI와 함께한 코딩 과정을 자동으로 기록

> Cursor와 Claude로 코딩할 때 나눈 대화를 분석해 커밋 메시지에 자동으로 추가

## 왜 Sayu가 필요한가요?

AI와 함께 코딩하면서 "이 코드를 왜 이렇게 짰더라?" 하고 까먹은 적 있나요? 
Sayu는 여러분이 Cursor나 Claude와 나눈 대화를 분석해서, 코드 변경의 맥락을 커밋 메시지에 자동으로 추가합니다.

## 주요 기능

- **🤖 AI 대화 자동 수집**: Cursor와 Claude Desktop의 대화 내용을 자동으로 가져옵니다
- **🧠 스마트 필터링**: 중요한 대화만 추려냅니다 (노이즈 93% 제거)
- **⚡ 빠른 분석**: 커밋할 때 2-3초 안에 AI가 대화 내용을 요약합니다
- **🔐 프라이버시**: 모든 데이터는 로컬에만 저장됩니다
- **🛡️ 안전한 동작**: 문제가 생겨도 커밋은 막지 않습니다

## 설치

```bash
# pipx로 설치 (추천)
pipx install sayu

# 또는 pip로 설치
pip install sayu

# 저장소에서 Sayu 초기화
sayu init
```

## 사용법

### 1. 초기화
```bash
# Git 저장소에서 실행
sayu init
```

이 명령어는:
- Git 훅을 설치합니다 (commit-msg, post-commit)
- 로컬 데이터베이스를 만듭니다 (`~/.sayu/events.db`)
- 기본 설정 파일을 생성합니다 (`.sayu.yml`)

### 2. API 키 설정 (.env)

다음 중 하나의 API 키를 설정하세요:

```bash
# Gemini (추천 - 빠르고 저렴)
GEMINI_API_KEY=your_api_key_here

# 또는 OpenAI
OPENAI_API_KEY=your_api_key_here

# 또는 Anthropic
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 평소처럼 커밋하기

```bash
git add .
git commit -m "인증 버그 수정"
```

자동으로 이런 커밋 메시지가 만들어집니다:
```
인증 버그 수정

---
AI-Context (sayu)

Intent:
  JWT 토큰 검증 로직의 버그를 수정하여 로그인 실패 문제 해결

Changes:
  auth.js의 토큰 디코딩 예외 처리 개선
  test/auth.test.js에 만료된 토큰 테스트 케이스 추가

Context:
  Claude와 토큰 만료 시 에러 처리 방식에 대해 논의했고, 
  예외 처리를 더 세밀하게 만들어야 한다는 결론을 내림.
  테스트 코드 작성 과정에서 여러 엣지 케이스를 발견하고 수정함.
---
```

## 명령어

```bash
# 시스템 상태 확인
sayu health

# 현재 변경사항의 AI 컨텍스트 미리보기
sayu preview

# CLI 트래킹 설치/제거 (zsh)
sayu collector cli-install
sayu collector cli-uninstall
```

## 설정 (.sayu.yml)

```yaml
# 어떤 도구에서 대화를 수집할지
connectors:
  claude: true      # Claude Desktop 대화 수집
  cursor: true      # Cursor 대화 수집
  cli:              # 터미널 명령어 수집
    mode: "off"     # "zsh-preexec" | "off"

# 얼마나 과거의 대화를 볼지 (시간 단위)
window:
  beforeCommitHours: 168  # 일주일 (금요일→월요일 고려)

# 커밋 메시지에 추가할지
commitTrailer: true

# 언어 설정
language: "ko"  # "ko" | "en"

# 개인정보 보호
privacy:
  maskSecrets: true
  masks: []  # 숨길 패턴들
```

## 설정 가능한 상수들

`shared/constants.py`에서 다음 값들을 조정할 수 있습니다:

### 시간 관련
- `COMMIT_WINDOW_HOURS`: 24 (커밋 시점 기준 몇 시간 전까지 볼지)
- `DEFAULT_LOOKBACK_HOURS`: 168 (기본 수집 기간, 1주일)
- `CACHE_TTL_SECONDS`: 300 (캐시 유효 시간)

### 텍스트 처리
- `MAX_CONVERSATION_COUNT`: 20 (최대 대화 수)
- `MAX_CONVERSATION_LENGTH`: 800 (대화당 최대 길이)
- `MAX_DIFF_LENGTH`: 2000 (diff 최대 길이)
- `MIN_RESPONSE_LENGTH`: 50 (최소 응답 길이)

### LLM API
- `LLM_TEMPERATURE`: 0.1 (창의성 수준, 낮을수록 일관성 높음)
- `LLM_MAX_OUTPUT_TOKENS`: 8192 (최대 출력 토큰)

## FAQ

### Q: 새로운 AI 도구 (예: GitHub Copilot)의 대화도 수집하고 싶어요
A: `domain/collectors/` 폴더에 새 수집기를 만드세요:

1. 기존 수집기 (claude.py, cursor.py) 참고해서 새 파일 생성
2. `pull_since()` 메서드 구현 (시간 범위 내 대화 수집)
3. `discover()` 메서드 구현 (도구가 설치됐는지 확인)
4. `domain/collectors/manager.py`에 새 수집기 등록

### Q: 다른 언어로 요약받고 싶어요
A: `.sayu.yml`에서 `language`를 변경하거나, `i18n/prompts/`에 새 언어 추가

### Q: 캐시가 너무 많이 쌓여요
A: 커밋할 때마다 1시간 이상된 캐시는 자동 정리됩니다. 수동으로 정리하려면 `rm -rf .sayu/cache/`

### Q: 민감한 정보가 커밋 메시지에 들어갈까 걱정돼요
A: `.sayu.yml`의 `privacy.maskSecrets`를 `true`로 설정하고, `masks`에 정규식 패턴 추가

## 타겟 사용자

- **Cursor + Claude**로 코딩하는 개발자
- AI와의 대화 내용을 기록으로 남기고 싶은 팀
- 커밋 히스토리의 품질을 중요하게 생각하는 팀

## 기여하기

이슈와 PR은 언제나 환영합니다!

## 라이선스

MIT