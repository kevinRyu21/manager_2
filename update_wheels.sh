#!/bin/bash
# -*- coding: utf-8 -*-
"""
GARAMe Manager - wheels 디렉토리 업데이트 (빠른 버전)
누락된 패키지만 추가로 다운로드합니다.
"""

set -e

echo "============================================================"
echo "  wheels 디렉토리 업데이트"
echo "============================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WHEELS_DIR="${SCRIPT_DIR}/wheels"
mkdir -p "$WHEELS_DIR"

echo "[INFO] Python 버전: $(python3 --version)"
echo "[INFO] wheels 디렉토리: $WHEELS_DIR"
echo ""

# 필수 빌드 도구 다운로드
echo "[1/3] 빌드 도구 다운로드..."
pip3 download -d "$WHEELS_DIR" Cython setuptools wheel

echo ""
echo "[2/3] requirements.txt 다운로드 (의존성 포함)..."
pip3 download -r requirements.txt -d "$WHEELS_DIR"

echo ""
echo "[3/3] 중복 제거 (.whl 우선)..."
cd "$WHEELS_DIR"
for tarfile in *.tar.gz 2>/dev/null; do
    if [ -f "$tarfile" ]; then
        PKG_NAME=$(echo "$tarfile" | sed 's/-[0-9].*//')
        if ls ${PKG_NAME}-*.whl 1> /dev/null 2>&1; then
            echo "  제거: $tarfile"
            rm -f "$tarfile"
        fi
    fi
done

echo ""
echo "============================================================"
echo "  완료!"
echo "============================================================"
echo ""
echo "다운로드 정보:"
echo "  - 총 파일: $(ls -1 "$WHEELS_DIR" | wc -l) 개"
echo "  - 크기: $(du -sh "$WHEELS_DIR" | awk '{print $1}')"
echo ""
