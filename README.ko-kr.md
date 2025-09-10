# Sayu - 커밋에 '왜'를 남기는 AI 코딩 컨텍스트

> AI 대화에서 코드 변경의 이유를 자동으로 캡처합니다

[English](README.md)

## Sayu란?

Sayu는 AI 코딩 어시스턴트(Cursor, Claude)와의 대화를 분석하여 git 커밋에 의미 있는 컨텍스트를 자동으로 추가합니다.

## 주요 기능

- **AI 대화 수집**: Cursor와 Claude Desktop의 대화를 자동으로 수집
- **스마트 필터링**: 현재 저장소와 관련된 대화만 선별
- **빠른 처리**: 커밋 시 2-3초 내에 컨텍스트 생성
- **프라이버시 우선**: 모든 데이터 로컬 처리, 영구 저장 없음
- **안전한 실패**: 오류 발생해도 커밋 차단하지 않음

## 설치

```bash
# pipx로 설치 (권장)
pipx install sayu

# 또는 pip로 설치
pip install sayu

# 저장소에서 초기화
sayu init
```

## 사용법

### 1. 초기화
```bash
# Git 저장소에서 실행
sayu init
```

다음 작업이 수행됩니다:
- Git 훅 설치 (commit-msg, post-commit)
- 설정 파일 생성 (`.sayu.yml`)

### 2. API 키 설정

환경 변수로 API 키 설정:

```bash
# Gemini API 키 (권장)
export SAYU_GEMINI_API_KEY=your_api_key_here

# 또는 OpenRouter API 키
export SAYU_OPENROUTER_API_KEY=your_api_key_here
export SAYU_LLM_PROVIDER=openrouter
```

### 3. 평소처럼 커밋

```bash
git add .
git commit -m "인증 버그 수정"
```

결과:
```
인증 버그 수정

---思惟---

의도:
  JWT 토큰 검증 로직을 수정하여 로그인 실패 문제 해결

변경사항:
  auth.js 토큰 디코딩 부분의 예외 처리 개선
  test/auth.test.js에 만료된 토큰 테스트 케이스 추가

대화 흐름:
  Claude와 토큰 만료 시 오류 처리 방법 논의
  더 세밀한 예외 처리 필요성 확인
  테스트 구현 중 여러 엣지 케이스 발견 및 수정
---FIN---
```

## 명령어

```bash
# 시스템 상태 확인
sayu health

# 스테이지된 변경사항의 AI 컨텍스트 미리보기
sayu preview

# CLI 추적 설치/제거 (zsh)
sayu collector cli-install
sayu collector cli-uninstall
```

## 설정 (.sayu.yml)

```yaml
# Sayu 설정
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

language: ko              # 언어 설정 (ko, en)
commitTrailer: true       # 커밋 메시지에 AI 분석 추가

connectors:
  claude: true            # Claude Desktop 대화 수집
  cursor: true            # Cursor 편집기 대화 수집
  cli:
    mode: "zsh-preexec"   # CLI 명령어 수집 (또는 "off")

# 환경 변수로도 설정 가능:
# SAYU_ENABLED=false
# SAYU_LANG=en
# SAYU_TRAILER=false
```

## 환경 변수

```bash
# 기본 설정
export SAYU_ENABLED=false              # Sayu 비활성화
export SAYU_LANG=en                    # 언어 (ko | en)
export SAYU_TRAILER=false              # 커밋 트레일러 비활성화

# LLM 설정
export SAYU_GEMINI_API_KEY=your-key    # Gemini API 키
export SAYU_OPENROUTER_API_KEY=your-key # OpenRouter API 키
export SAYU_LLM_PROVIDER=gemini        # LLM 제공자 (gemini | openrouter)
export SAYU_OPENROUTER_MODEL=anthropic/claude-3-haiku  # OpenRouter 모델

# 디버그
export SAYU_DEBUG=true                 # 디버그 로깅 활성화
```

## FAQ

### Q: 데이터는 어디에 저장되나요?
A: Sayu는 인메모리 저장소만 사용합니다. 대화는 커밋 시에만 수집되고 처리 후 즉시 삭제됩니다. 영구 데이터베이스는 생성되지 않습니다.

### Q: 새로운 AI 도구 지원을 추가하려면?
A: `domain/collectors/conversation.py`의 `ConversationCollector`를 확장하여 새 컬렉터를 만들면 됩니다.

### Q: 요약 언어를 변경하려면?
A: `.sayu.yml`의 `language`를 변경하거나 `SAYU_LANG` 환경 변수를 설정하세요.

### Q: Sayu를 일시적으로 비활성화하려면?
A: `SAYU_ENABLED=false` 설정하거나 git commit 시 `--no-verify` 사용

### Q: LLM API가 실패하면?
A: Sayu는 안전하게 실패합니다. LLM이 실패해도 커밋은 정상적으로 진행되며 대체 메시지가 표시됩니다.

## 프라이버시 & 보안

- 모든 처리가 로컬에서 수행됨
- 설정된 LLM API로만 데이터 전송
- 대화 내용의 영구 저장이나 로깅 없음
- API 키는 환경 변수로만 읽음

## 문제 해결

```bash
# 디버그 모드로 상세 로그 확인
export SAYU_DEBUG=true
git commit -m "test"

# 컬렉터 작동 확인
sayu health

# LLM 연결 테스트
sayu preview
```

## 라이선스

MIT