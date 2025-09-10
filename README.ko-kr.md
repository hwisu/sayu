# Sayu

AI 대화에서 코드 변경의 "왜"를 자동으로 캡처합니다.

## 빠른 시작

```bash
# pipx로 설치
pipx install git+https://github.com/yourusername/sayu.git

# 저장소에서 초기화
sayu init

# API 키 설정 (하나 선택)
export SAYU_GEMINI_API_KEY=your_key

# 또는 OpenRouter 사용
export SAYU_OPENROUTER_API_KEY=your_key
export SAYU_LLM_PROVIDER=openrouter
export SAYU_OPENROUTER_MODEL=anthropic/claude-3-haiku

# 평소처럼 커밋
git commit -m "버그 수정"
```

커밋에 AI가 분석한 컨텍스트가 자동으로 추가됩니다.

## 기능

- Cursor & Claude Desktop 대화 수집
- git 커밋에 의미있는 컨텍스트 추가
- 모든 처리는 로컬에서
- 커밋을 절대 차단하지 않음

## 명령어

```bash
sayu health   # 상태 확인
sayu preview  # AI 컨텍스트 미리보기
```

## 설정

`.sayu.yml`:
```yaml
language: ko          # 또는 en
commitTrailer: true
connectors:
  claude: true
  cursor: true
```

환경 변수:
```bash
SAYU_ENABLED=false    # 일시 비활성화
SAYU_DEBUG=true       # 디버그 모드
```

## 라이선스

MIT