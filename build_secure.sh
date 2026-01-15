#!/bin/bash
# -*- coding: utf-8 -*-
"""
GARAMe Manager - 보안 빌드 스크립트
Cython 컴파일을 통한 소스코드 보호 빌드
"""

set -e  # 오류 발생 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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
echo "  GARAMe Manager - 보안 빌드"
echo "  Cython 컴파일을 통한 소스코드 보호"
echo "============================================================"
echo ""

# 1. 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "작업 디렉토리: $SCRIPT_DIR"
echo ""

# 2. 가상환경 활성화
if [ -d "venv" ]; then
    log_info "가상환경 활성화 중..."
    source venv/bin/activate
    log_success "가상환경 활성화 완료"
else
    log_error "가상환경이 없습니다. install.sh를 먼저 실행하세요."
    exit 1
fi
echo ""

# 3. Cython 설치 확인
log_info "Cython 설치 확인 중..."
if ! pip show Cython > /dev/null 2>&1; then
    log_warning "Cython이 설치되어 있지 않습니다. 설치 중..."
    pip install Cython
    log_success "Cython 설치 완료"
else
    CYTHON_VERSION=$(pip show Cython | grep Version | cut -d' ' -f2)
    log_success "Cython $CYTHON_VERSION 설치됨"
fi
echo ""

# 4. setuptools 설치 확인
log_info "setuptools 설치 확인 중..."
if ! pip show setuptools > /dev/null 2>&1; then
    log_warning "setuptools가 설치되어 있지 않습니다. 설치 중..."
    pip install setuptools
    log_success "setuptools 설치 완료"
fi
echo ""

# 5. 기존 빌드 파일 정리
log_info "기존 빌드 파일 정리 중..."
if [ -d "build" ]; then
    rm -rf build
    log_success "build 디렉토리 삭제"
fi

# .so 파일 삭제 (재빌드를 위해)
find . -name "*.so" -type f -delete 2>/dev/null || true
log_success "기존 .so 파일 삭제"

# .c 파일 삭제 (중간 파일)
find . -name "*.c" -type f -not -path "./venv/*" -delete 2>/dev/null || true
log_success "기존 .c 파일 삭제"

echo ""

# 6. 백업 생성
log_info "원본 소스코드 백업 중..."
BACKUP_DIR="backup_original_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"

    # src 디렉토리 백업
    if [ -d "src" ]; then
        cp -r src "$BACKUP_DIR/"
    fi

    # 최상위 .py 파일 백업
    for py_file in main.py watchdog.py; do
        if [ -f "$py_file" ]; then
            cp "$py_file" "$BACKUP_DIR/"
        fi
    done

    log_success "백업 완료: $BACKUP_DIR"
else
    log_warning "백업 디렉토리가 이미 존재합니다"
fi
echo ""

# 7. Cython 컴파일 실행
log_info "Cython 컴파일 시작..."
echo ""

if ! python3 setup_cython.py build_ext --inplace; then
    log_error "Cython 컴파일 실패"
    log_info "백업에서 원본 복구가 가능합니다: $BACKUP_DIR"
    exit 1
fi

echo ""
log_success "Cython 컴파일 완료"
echo ""

# 8. 컴파일 결과 확인
log_info "컴파일 결과 확인 중..."
SO_COUNT=$(find . -name "*.so" -type f | wc -l)

if [ "$SO_COUNT" -eq 0 ]; then
    log_error "컴파일된 .so 파일이 없습니다"
    log_info "백업에서 원본 복구가 가능합니다: $BACKUP_DIR"
    exit 1
fi

log_success "컴파일된 모듈: $SO_COUNT 개"
echo ""

# 9. .py 파일 제거 여부 확인
log_warning "원본 .py 파일을 삭제하시겠습니까?"
log_warning "삭제 후에는 백업($BACKUP_DIR)에서만 복구 가능합니다."
echo ""
log_info "계속하려면 'yes'를 입력하세요 (다른 입력 시 취소):"
read -r response

if [ "$response" = "yes" ]; then
    log_info "원본 .py 파일 삭제 중..."

    # src 디렉토리의 .py 파일 삭제 (__init__.py는 유지)
    find src -name "*.py" -type f ! -name "__init__.py" -delete 2>/dev/null || true

    # 최상위 .py 파일 삭제 (main.py, watchdog.py)
    # 주의: main.py는 엔트리포인트이므로 상황에 따라 유지 필요
    for py_file in watchdog.py; do
        if [ -f "$py_file" ]; then
            rm -f "$py_file"
            log_success "삭제: $py_file"
        fi
    done

    log_success "원본 .py 파일 삭제 완료"
else
    log_info ".py 파일을 유지합니다 (Cython 모듈과 함께 사용)"
fi
echo ""

# 10. 중간 파일 정리
log_info "중간 파일 정리 중..."

# .c 파일 삭제
find . -name "*.c" -type f -not -path "./venv/*" -delete 2>/dev/null || true

# build 디렉토리 삭제
if [ -d "build" ]; then
    rm -rf build
fi

log_success "중간 파일 정리 완료"
echo ""

# 11. 컴파일 보고서 생성
REPORT_FILE="compilation_report_$(date +%Y%m%d_%H%M%S).txt"
log_info "컴파일 보고서 생성 중..."

{
    echo "================================================"
    echo "GARAMe Manager - Cython 컴파일 보고서"
    echo "================================================"
    echo ""
    echo "빌드 날짜: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "빌드 디렉토리: $SCRIPT_DIR"
    echo ""
    echo "================================================"
    echo "컴파일된 모듈 (.so 파일)"
    echo "================================================"
    find . -name "*.so" -type f | sort
    echo ""
    echo "총 $SO_COUNT 개 모듈"
    echo ""
    echo "================================================"
    echo "백업 위치"
    echo "================================================"
    echo "$BACKUP_DIR"
    echo ""
} > "$REPORT_FILE"

log_success "보고서 생성: $REPORT_FILE"
echo ""

# 12. 완료
echo "============================================================"
echo "  보안 빌드 완료!"
echo "============================================================"
echo ""
log_success "Cython 컴파일이 성공적으로 완료되었습니다"
echo ""
echo "다음 단계:"
echo "  1. ./run.sh로 프로그램 실행 및 테스트"
echo "  2. 정상 작동 확인 후 백업 디렉토리 보관"
echo "  3. 보고서 확인: $REPORT_FILE"
echo ""
echo "주의사항:"
echo "  - 원본 소스코드는 $BACKUP_DIR에 백업됨"
echo "  - .so 파일은 역컴파일이 매우 어려움"
echo "  - 수정이 필요한 경우 백업에서 복구 후 재컴파일"
echo ""

# 보고서 내용 표시
log_info "컴파일된 모듈 목록:"
find . -name "*.so" -type f | sort
echo ""

log_info "보안 빌드가 완료되었습니다!"
