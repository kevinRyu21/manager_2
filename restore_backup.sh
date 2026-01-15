#!/bin/bash
# -*- coding: utf-8 -*-
"""
GARAMe Manager - 백업 복구 스크립트
Cython 컴파일 전 원본 소스코드 복구
"""

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "============================================================"
echo "  GARAMe Manager - 백업 복구"
echo "============================================================"
echo ""

# 현재 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 백업 디렉토리 찾기
log_info "백업 디렉토리 검색 중..."
BACKUP_DIRS=($(ls -dt backup_original_* 2>/dev/null || true))

if [ ${#BACKUP_DIRS[@]} -eq 0 ]; then
    log_error "백업 디렉토리를 찾을 수 없습니다"
    exit 1
fi

echo ""
log_info "발견된 백업:"
for i in "${!BACKUP_DIRS[@]}"; do
    echo "  [$i] ${BACKUP_DIRS[$i]}"
done
echo ""

# 백업 선택
if [ ${#BACKUP_DIRS[@]} -eq 1 ]; then
    SELECTED=0
    log_info "백업이 하나만 있습니다: ${BACKUP_DIRS[0]}"
else
    log_info "복구할 백업 번호를 입력하세요 (0-$((${#BACKUP_DIRS[@]}-1))):"
    read -r SELECTED

    if ! [[ "$SELECTED" =~ ^[0-9]+$ ]] || [ "$SELECTED" -ge ${#BACKUP_DIRS[@]} ]; then
        log_error "잘못된 선택입니다"
        exit 1
    fi
fi

BACKUP_DIR="${BACKUP_DIRS[$SELECTED]}"
log_info "선택된 백업: $BACKUP_DIR"
echo ""

# 경고
log_warning "현재 파일들이 백업으로 덮어씌워집니다!"
log_warning "계속하려면 'yes'를 입력하세요:"
read -r response

if [ "$response" != "yes" ]; then
    log_info "복구 취소됨"
    exit 0
fi

# .so 파일 삭제
log_info "컴파일된 .so 파일 삭제 중..."
find . -name "*.so" -type f -delete 2>/dev/null || true
log_success ".so 파일 삭제 완료"

# .c 파일 삭제
log_info "중간 .c 파일 삭제 중..."
find . -name "*.c" -type f -not -path "./venv/*" -delete 2>/dev/null || true
log_success ".c 파일 삭제 완료"

# build 디렉토리 삭제
if [ -d "build" ]; then
    rm -rf build
    log_success "build 디렉토리 삭제"
fi

# 백업 복구
log_info "백업에서 원본 파일 복구 중..."

if [ -d "$BACKUP_DIR/src" ]; then
    cp -r "$BACKUP_DIR/src"/* src/ 2>/dev/null || true
    log_success "src 디렉토리 복구"
fi

for py_file in main.py watchdog.py; do
    if [ -f "$BACKUP_DIR/$py_file" ]; then
        cp "$BACKUP_DIR/$py_file" .
        log_success "$py_file 복구"
    fi
done

echo ""
log_success "복구 완료!"
echo ""
log_info "복구된 백업: $BACKUP_DIR"
log_info "이제 원본 .py 파일로 프로그램을 실행할 수 있습니다"
echo ""
