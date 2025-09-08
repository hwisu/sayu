#!/bin/bash

# Phase 1 기초 인프라 테스트 스크립트

set -e

echo "=== Phase 1 기초 인프라 검증 시작 ==="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 결과 추적
TESTS_PASSED=0
TESTS_FAILED=0

# 테스트 함수
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# 1. 빌드 테스트
echo "1. TypeScript 빌드 테스트"
if npm run build > /dev/null 2>&1; then
    test_pass "TypeScript 빌드 성공"
else
    test_fail "TypeScript 빌드 실패"
fi

# 2. TypeScript 타입 체크
echo ""
echo "2. TypeScript 타입 체크"
if npm run typecheck > /dev/null 2>&1; then
    test_pass "타입 체크 통과"
else
    test_fail "타입 체크 실패"
fi

# 3. CLI 명령어 테스트
echo ""
echo "3. CLI 명령어 테스트"

# sayu 명령어 존재 확인
if [ -f "dist/cli/index.js" ]; then
    test_pass "CLI 빌드 파일 존재"
    
    # help 명령어 테스트
    if node dist/cli/index.js --help > /dev/null 2>&1; then
        test_pass "sayu --help 명령어 작동"
    else
        test_fail "sayu --help 명령어 실패"
    fi
else
    test_fail "CLI 빌드 파일 없음"
fi

# 4. 테스트 Git 레포 생성
echo ""
echo "4. Git 레포 초기화 테스트"

TEST_DIR="/tmp/sayu-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Git 레포 초기화
git init > /dev/null 2>&1
test_pass "테스트 Git 레포 생성: $TEST_DIR"

# 5. sayu init 테스트
echo ""
echo "5. sayu init 명령어 테스트"

if node "$OLDPWD/dist/cli/index.js" init > /dev/null 2>&1; then
    test_pass "sayu init 실행 성공"
    
    # 설정 파일 생성 확인
    if [ -f ".sayu.yml" ]; then
        test_pass ".sayu.yml 설정 파일 생성됨"
    else
        test_fail ".sayu.yml 설정 파일 생성 실패"
    fi
    
    # Git 훅 설치 확인
    if [ -f ".git/hooks/commit-msg" ]; then
        test_pass "commit-msg 훅 설치됨"
    else
        test_fail "commit-msg 훅 설치 실패"
    fi
    
    if [ -f ".git/hooks/post-commit" ]; then
        test_pass "post-commit 훅 설치됨"
    else
        test_fail "post-commit 훅 설치 실패"
    fi
else
    test_fail "sayu init 실행 실패"
fi

# 6. SQLite DB 생성 확인
echo ""
echo "6. SQLite 데이터베이스 테스트"

if [ -f "$HOME/.sayu/events.db" ]; then
    test_pass "SQLite DB 파일 생성됨"
    
    # DB 테이블 확인
    if sqlite3 "$HOME/.sayu/events.db" ".tables" 2>/dev/null | grep -q "events"; then
        test_pass "events 테이블 존재"
    else
        test_fail "events 테이블 없음"
    fi
    
    if sqlite3 "$HOME/.sayu/events.db" ".tables" 2>/dev/null | grep -q "events_fts"; then
        test_pass "events_fts FTS5 테이블 존재"
    else
        test_fail "events_fts FTS5 테이블 없음"
    fi
else
    test_fail "SQLite DB 파일 생성 실패"
fi

# 7. 설정 파일 파싱 테스트
echo ""
echo "7. 설정 파일 파싱 테스트"

if [ -f ".sayu.yml" ]; then
    # YAML 구문 검증 - node의 js-yaml 사용
    if node -e "const yaml = require('$OLDPWD/node_modules/js-yaml'); const fs = require('fs'); yaml.load(fs.readFileSync('.sayu.yml', 'utf8'))" 2>/dev/null; then
        test_pass "YAML 구문 유효"
    else
        test_fail "YAML 구문 오류"
    fi
    
    # 필수 섹션 확인
    if grep -q "connectors:" .sayu.yml; then
        test_pass "connectors 섹션 존재"
    else
        test_fail "connectors 섹션 없음"
    fi
fi

# 8. sayu health 테스트
echo ""
echo "8. sayu health 명령어 테스트"

if node "$OLDPWD/dist/cli/index.js" health > /dev/null 2>&1; then
    test_pass "sayu health 실행 성공"
else
    test_fail "sayu health 실행 실패"
fi

# 9. Git 훅 Fail-open 테스트
echo ""
echo "9. Git 훅 Fail-open 정책 테스트"

# 테스트 파일 생성
echo "test" > test.txt
git add test.txt

# 훅이 실패해도 커밋이 되는지 확인
if git commit -m "Test commit" > /dev/null 2>&1; then
    test_pass "Fail-open: 훅 실패에도 커밋 성공"
else
    test_fail "Fail-open: 커밋 실패"
fi

# 10. 이벤트 스키마 검증
echo ""
echo "10. 이벤트 스키마 및 타입 시스템"

cd "$OLDPWD"

# TypeScript 타입 테스트 파일 생성
cat > test-types.ts << 'EOF'
import { Event, Config, EventSource, EventKind } from './dist/core/types';

// 이벤트 생성 테스트
const testEvent: Event = {
  id: 'test-uuid',
  ts: Date.now(),
  source: 'git',
  kind: 'commit',
  repo: '/test/repo',
  cwd: '/test/cwd',
  file: null,
  range: null,
  actor: 'user',
  text: 'Test event',
  url: null,
  meta: {}
};

// 설정 생성 테스트
const testConfig: Config = {
  connectors: {
    claude: true,
    cursor: true,
    editor: true,
    cli: { mode: 'zsh-preexec' },
    browser: { mode: 'off' }
  },
  window: { beforeCommitHours: 24 },
  filter: {
    domainAllowlist: ['github.com'],
    noise: { graceMinutes: 5, minScore: 0.6 }
  },
  summarizer: {
    mode: 'hybrid',
    maxLines: { commit: 12, notes: 25 }
  },
  privacy: {
    maskSecrets: true,
    masks: []
  },
  output: {
    commitTrailer: true,
    gitNotes: true,
    notesRef: 'refs/notes/sayu'
  }
};

console.log('Type validation passed');
EOF

if npx tsc test-types.ts --noEmit > /dev/null 2>&1; then
    test_pass "이벤트 스키마 타입 검증 통과"
else
    test_fail "이벤트 스키마 타입 검증 실패"
fi

rm -f test-types.ts

# 정리
rm -rf "$TEST_DIR"

# 결과 요약
echo ""
echo "==================================="
echo "Phase 1 검증 결과"
echo "==================================="
echo -e "${GREEN}통과: $TESTS_PASSED${NC}"
echo -e "${RED}실패: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 1 모든 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}❌ 일부 테스트 실패${NC}"
    exit 1
fi