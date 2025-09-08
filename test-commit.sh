#!/bin/bash

echo "=== Sayu 커밋 훅 테스트 ==="

# 테스트 디렉토리 생성
TEST_DIR="/tmp/sayu-commit-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "테스트 디렉토리: $TEST_DIR"

# Git 레포 초기화
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Sayu 초기화
echo "Sayu 초기화 중..."
node /Users/hwisookim/sayu/dist/cli/index.js init

# 첫 번째 커밋 (베이스라인)
echo "첫 번째 커밋 생성..."
echo "Initial content" > file1.txt
git add file1.txt
git commit -m "Initial commit"

# 두 번째 파일 추가
echo "두 번째 파일 추가 및 커밋..."
echo "Second file" > file2.txt
echo "Modified" >> file1.txt
git add .

# 커밋 (Sayu 훅이 작동해야 함)
git commit -m "Add file2 and modify file1"

echo ""
echo "=== 마지막 커밋 메시지 확인 ==="
git log --format="%B" -n 1

echo ""
echo "=== DB 이벤트 확인 ==="
sqlite3 ~/.sayu/events.db "SELECT source, kind, file, substr(text, 1, 50) as text_preview FROM events WHERE repo = '$TEST_DIR' ORDER BY ts DESC LIMIT 10;"

echo ""
echo "테스트 완료. 정리하려면: rm -rf $TEST_DIR"