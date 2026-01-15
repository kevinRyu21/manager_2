#!/bin/bash
# -*- coding: utf-8 -*-
"""
GARAMe Manager - 오프라인 설치용 패키지 다운로드 스크립트
모든 Python 패키지를 wheels 디렉토리에 다운로드합니다.
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
echo "  GARAMe Manager - 오프라인 패키지 다운로드"
echo "  모든 Python 패키지를 wheels 디렉토리에 저장"
echo "============================================================"
echo ""

# 현재 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WHEELS_DIR="${SCRIPT_DIR}/wheels"

# 인터넷 연결 확인
log_info "인터넷 연결 확인 중..."
if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    log_error "인터넷 연결이 필요합니다"
    exit 1
fi
log_success "인터넷 연결 확인 완료"
echo ""

# wheels 디렉토리 생성
log_info "wheels 디렉토리 준비 중..."
mkdir -p "$WHEELS_DIR"
log_success "wheels 디렉토리: $WHEELS_DIR"
echo ""

# Python 버전 확인
log_info "Python 버전 확인 중..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
log_info "Python 버전: $PYTHON_VERSION"
echo ""

# pip 업그레이드
log_info "pip 업그레이드 중..."
python3 -m pip install --upgrade pip wheel setuptools
log_success "pip 업그레이드 완료"
echo ""

# 1. 기본 빌드 도구 다운로드
log_info "[1/5] 빌드 도구 다운로드 중..."
echo ""

BUILD_TOOLS=(
    "pip"
    "wheel"
    "setuptools"
    "Cython>=0.29.34,<3.1"
)

for tool in "${BUILD_TOOLS[@]}"; do
    log_info "  다운로드: $tool"
    pip3 download "$tool" -d "$WHEELS_DIR" 2>&1 | grep -v "Requirement already satisfied" || true
done

log_success "빌드 도구 다운로드 완료"
echo ""

# 2. requirements.txt 패키지 다운로드
log_info "[2/5] requirements.txt 패키지 다운로드 중..."
log_info "  (시간이 오래 걸릴 수 있습니다...)"
echo ""

if [ -f "requirements.txt" ]; then
    pip3 download -r requirements.txt -d "$WHEELS_DIR" --no-deps 2>&1 | tee download.log
    log_success "requirements.txt 패키지 다운로드 완료"
else
    log_error "requirements.txt 파일이 없습니다"
    exit 1
fi
echo ""

# 3. 의존성 패키지 다운로드
log_info "[3/5] 의존성 패키지 다운로드 중..."
log_info "  (모든 의존성을 재귀적으로 다운로드합니다...)"
echo ""

pip3 download -r requirements.txt -d "$WHEELS_DIR" 2>&1 | tee -a download.log
log_success "의존성 패키지 다운로드 완료"
echo ""

# 4. 특별히 필요한 패키지 추가 다운로드
log_info "[4/5] 추가 필수 패키지 다운로드 중..."
echo ""

ADDITIONAL_PACKAGES=(
    "numpy==1.26.4"
    "opencv-contrib-python==4.9.0.80"
    "torch"
    "torchvision"
)

for pkg in "${ADDITIONAL_PACKAGES[@]}"; do
    log_info "  다운로드: $pkg"
    pip3 download "$pkg" -d "$WHEELS_DIR" 2>&1 | grep -v "Requirement already satisfied" || true
done

log_success "추가 패키지 다운로드 완료"
echo ""

# 5. 중복 제거 및 정리
log_info "[5/5] 중복 파일 제거 중..."
echo ""

# 파일 개수 확인
TOTAL_FILES=$(ls -1 "$WHEELS_DIR" | wc -l)
log_info "  총 파일 개수: $TOTAL_FILES"

# 중복 제거 (같은 패키지의 여러 버전이 있을 수 있음 - 최신 버전만 유지)
cd "$WHEELS_DIR"

# .tar.gz 파일 대신 .whl 파일 우선
log_info "  .tar.gz 파일 중 .whl이 있는 항목 제거 중..."
for tarfile in *.tar.gz 2>/dev/null; do
    if [ -f "$tarfile" ]; then
        PKG_NAME=$(echo "$tarfile" | sed 's/-[0-9].*//')
        if ls ${PKG_NAME}-*.whl 1> /dev/null 2>&1; then
            log_info "    제거: $tarfile (.whl 존재)"
            rm -f "$tarfile"
        fi
    fi
done

cd "$SCRIPT_DIR"

FINAL_FILES=$(ls -1 "$WHEELS_DIR" | wc -l)
log_success "정리 완료: $FINAL_FILES 개 파일"
echo ""

# 다운로드 결과 요약
log_info "다운로드 요약 생성 중..."
SUMMARY_FILE="wheels_download_summary_$(date +%Y%m%d_%H%M%S).txt"

{
    echo "============================================================"
    echo "GARAMe Manager - 오프라인 패키지 다운로드 요약"
    echo "============================================================"
    echo ""
    echo "다운로드 날짜: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Python 버전: $PYTHON_VERSION"
    echo "다운로드 디렉토리: $WHEELS_DIR"
    echo ""
    echo "============================================================"
    echo "다운로드된 파일 목록 (총 $FINAL_FILES 개)"
    echo "============================================================"
    ls -lh "$WHEELS_DIR" | tail -n +2
    echo ""
    echo "============================================================"
    echo "패키지 이름별 정렬"
    echo "============================================================"
    ls -1 "$WHEELS_DIR" | sort
    echo ""
    echo "============================================================"
    echo "총 크기"
    echo "============================================================"
    du -sh "$WHEELS_DIR"
    echo ""
} > "$SUMMARY_FILE"

log_success "요약 파일 생성: $SUMMARY_FILE"
echo ""

# 디스크 사용량 확인
WHEELS_SIZE=$(du -sh "$WHEELS_DIR" | awk '{print $1}')

echo "============================================================"
echo "  다운로드 완료!"
echo "============================================================"
echo ""
log_success "모든 패키지 다운로드 완료"
echo ""
echo "다운로드 정보:"
echo "  - 총 파일 개수: $FINAL_FILES"
echo "  - 총 크기: $WHEELS_SIZE"
echo "  - 저장 위치: $WHEELS_DIR"
echo "  - 요약 파일: $SUMMARY_FILE"
echo ""
echo "다음 단계:"
echo "  1. 오프라인 환경으로 wheels 디렉토리 복사"
echo "  2. ./install.sh 실행"
echo "  3. 오프라인 설치 선택 (n)"
echo ""
log_info "요약 파일 내용:"
cat "$SUMMARY_FILE"
echo ""
