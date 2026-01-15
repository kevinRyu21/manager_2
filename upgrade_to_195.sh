#!/bin/bash
################################################################################
# GARAMe Manager v1.9.5 업그레이드 스크립트
# - 버전 문자열 통일
# - safety_detector_v2 활성화
# - 불필요한 코드 정리
################################################################################

set -e

echo "=========================================="
echo "GARAMe Manager v1.9.5 업그레이드 시작"
echo "=========================================="
echo ""

# 현재 디렉토리 확인
if [ ! -f "VERSION.txt" ]; then
    echo "ERROR: VERSION.txt를 찾을 수 없습니다."
    echo "1.9.5 디렉토리에서 실행하세요."
    exit 1
fi

# 1. 버전 문자열 업데이트
echo "[1/6] 버전 문자열 v1.9.5로 업데이트 중..."

# garame_manager.spec
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' garame_manager.spec 2>/dev/null || true

# run.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' run.sh 2>/dev/null || true

# install.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' install.sh 2>/dev/null || true

# uninstall.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' uninstall.sh 2>/dev/null || true

# setup_cython.py
sed -i '' 's/version="1\.9\.[0-4]"/version="1.9.5"/g' setup_cython.py 2>/dev/null || true

# setup_autostart.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' setup_autostart.sh 2>/dev/null || true

# create_distribution.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' create_distribution.sh 2>/dev/null || true

# install_systemd_service.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' install_systemd_service.sh 2>/dev/null || true

# uninstall_systemd_service.sh
sed -i '' 's/v1\.9\.[0-4]/v1.9.5/g' uninstall_systemd_service.sh 2>/dev/null || true

echo "✓ 버전 문자열 업데이트 완료"
echo ""

# 2. safety_detector.py를 safety_detector_v2.py로 교체
echo "[2/6] safety_detector를 InsightFace+YOLOv11 버전으로 교체 중..."

if [ -f "src/tcp_monitor/sensor/safety_detector_v2.py" ]; then
    # 기존 파일 백업
    if [ -f "src/tcp_monitor/sensor/safety_detector.py" ]; then
        mv src/tcp_monitor/sensor/safety_detector.py src/tcp_monitor/sensor/safety_detector.py.old_face_recognition
        echo "  - 구버전 백업: safety_detector.py.old_face_recognition"
    fi

    # v2를 메인으로 복사
    cp src/tcp_monitor/sensor/safety_detector_v2.py src/tcp_monitor/sensor/safety_detector.py
    echo "  - InsightFace+YOLOv11 버전 활성화"
    echo "✓ safety_detector 교체 완료"
else
    echo "  ⚠ safety_detector_v2.py를 찾을 수 없습니다. 건너뜁니다."
fi
echo ""

# 3. requirements.txt에서 obsolete 주석 제거
echo "[3/6] requirements.txt 정리 중..."

# dlib 관련 주석 제거
sed -i '' '/기존 dlib 기반 face_recognition/d' requirements.txt 2>/dev/null || true
sed -i '' '/install.sh에서 필요 시 설치/d' requirements.txt 2>/dev/null || true

echo "✓ requirements.txt 정리 완료"
echo ""

# 4. config.ini에서 obsolete 섹션 제거
echo "[4/6] config.ini에서 obsolete 섹션 제거 중..."

if [ -f "config.ini" ]; then
    # [ocr] 섹션 제거
    sed -i '' '/\[ocr\]/,/^$/d' config.ini 2>/dev/null || true
    echo "  - [ocr] 섹션 제거"
fi

echo "✓ config.ini 정리 완료"
echo ""

# 5. 모든 .sh 파일 개행문자 변환 및 실행 권한
echo "[5/6] 모든 .sh 파일 최적화 중..."

for file in *.sh; do
    if [ -f "$file" ]; then
        # 개행 문자 변환
        sed -i '' 's/\r$//' "$file" 2>/dev/null || true
        # 실행 권한 부여
        chmod +x "$file"
    fi
done

echo "✓ .sh 파일 최적화 완료"
echo ""

# 6. garame_manager.spec에서 dlib 제거
echo "[6/6] garame_manager.spec에서 obsolete hiddenimports 제거 중..."

if [ -f "garame_manager.spec" ]; then
    # dlib 제거
    sed -i '' "/'dlib',/d" garame_manager.spec 2>/dev/null || true
    # face_recognition 제거 (v1.9.5에서는 InsightFace 사용)
    sed -i '' "/'face_recognition',/d" garame_manager.spec 2>/dev/null || true
    echo "  - dlib, face_recognition hiddenimports 제거"
fi

echo "✓ spec 파일 정리 완료"
echo ""

echo "=========================================="
echo "v1.9.5 업그레이드 완료!"
echo "=========================================="
echo ""
echo "변경사항:"
echo "  ✓ 모든 파일의 버전을 v1.9.5로 통일"
echo "  ✓ InsightFace + YOLOv11 활성화"
echo "  ✓ dlib/face_recognition 제거"
echo "  ✓ OCR 관련 설정 제거"
echo "  ✓ requirements.txt 및 spec 파일 정리"
echo "  ✓ 모든 .sh 파일 최적화"
echo ""
echo "다음 단계:"
echo "  1. 변경사항 확인: git diff"
echo "  2. 테스트 실행: python3 main.py"
echo "  3. 빌드: ./install.sh"
echo ""
