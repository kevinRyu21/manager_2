#!/bin/bash
################################################################################
# OpenCV (cv2) 진단 및 수정 스크립트
# PyInstaller 빌드 전에 cv2가 제대로 설치되었는지 확인
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}OpenCV (cv2) 진단 및 수정${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 플랫폼 확인
PLATFORM=$(uname -s)
if [ "$PLATFORM" = "Darwin" ]; then
    echo -e "${YELLOW}⚠️  경고: macOS 환경에서 실행 중입니다.${NC}"
    echo -e "${YELLOW}   PyInstaller 빌드는 Ubuntu Linux에서만 지원됩니다.${NC}"
    echo -e "${YELLOW}   macOS에서 빌드한 실행 파일은 Ubuntu에서 작동하지 않습니다.${NC}"
    echo ""
fi

# 가상환경 활성화
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo -e "${BLUE}[1/5]${NC} 가상환경 활성화 중..."
    source venv/bin/activate
    echo -e "${GREEN}      ✓ 완료${NC}"
else
    echo -e "${RED}[오류]${NC} 가상환경을 찾을 수 없습니다."
    echo -e "${YELLOW}      먼저 install.sh를 실행하세요.${NC}"
    exit 1
fi
echo ""

# opencv 패키지 설치 확인
echo -e "${BLUE}[2/6]${NC} opencv 패키지 설치 확인 중..."
OPENCV_PYTHON_INSTALLED=$(pip list 2>/dev/null | grep -c "opencv-python " || echo "0")
OPENCV_CONTRIB_INSTALLED=$(pip list 2>/dev/null | grep -c "opencv-contrib-python" || echo "0")

# Python 버전 확인
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if [ "$OPENCV_PYTHON_INSTALLED" = "0" ] && [ "$OPENCV_CONTRIB_INSTALLED" = "0" ]; then
    echo -e "${RED}      ✗ opencv 패키지가 설치되지 않음${NC}"
    echo -e "${YELLOW}      opencv-python과 opencv-contrib-python 설치 중...${NC}"

    if [[ "$PYTHON_VERSION" == "3.13" ]]; then
        pip install "opencv-python>=4.10.0,<=4.12.0.88" "opencv-contrib-python>=4.10.0,<=4.12.0.88"
    else
        pip install "opencv-python>=4.9.0,<=4.12.0.88" "opencv-contrib-python>=4.9.0,<=4.12.0.88"
    fi
elif [ "$OPENCV_PYTHON_INSTALLED" = "0" ] || [ "$OPENCV_CONTRIB_INSTALLED" = "0" ]; then
    echo -e "${YELLOW}      ⚠ opencv-python 또는 opencv-contrib-python 중 하나만 설치됨${NC}"
    echo -e "${YELLOW}      둘 다 설치합니다...${NC}"

    if [[ "$PYTHON_VERSION" == "3.13" ]]; then
        pip install "opencv-python>=4.10.0,<=4.12.0.88" "opencv-contrib-python>=4.10.0,<=4.12.0.88"
    else
        pip install "opencv-python>=4.9.0,<=4.12.0.88" "opencv-contrib-python>=4.9.0,<=4.12.0.88"
    fi
else
    echo -e "${GREEN}      ✓ opencv-python과 opencv-contrib-python 모두 설치됨${NC}"
fi
echo ""

# cv2 import 테스트
echo -e "${BLUE}[3/6]${NC} cv2 import 테스트 중..."
if python3 -c "import cv2; print('  ✓ cv2 버전:', cv2.__version__)" 2>/dev/null; then
    CV2_INSTALLED=true
    echo -e "${GREEN}      ✓ cv2 import 성공${NC}"
else
    CV2_INSTALLED=false
    echo -e "${RED}      ✗ cv2 import 실패${NC}"
fi
echo ""

# cv2 바이너리 파일 확인
echo -e "${BLUE}[4/6]${NC} cv2 바이너리 파일 확인 중..."

if [ "$PLATFORM" = "Darwin" ]; then
    # macOS: .dylib 또는 .so 파일 확인
    SO_COUNT=$(find venv/lib/python*/site-packages/cv2 -name "*.so*" -o -name "*.dylib" 2>/dev/null | wc -l | xargs)
    echo -e "      바이너리 파일 개수: ${SO_COUNT} (macOS)"
    echo -e "${YELLOW}      ⚠ macOS 환경: 파일 개수 검증 건너뜀${NC}"
    SO_FILES_OK=true
else
    # Linux: .so 파일 확인
    SO_COUNT=$(find venv/lib/python*/site-packages/cv2 -name "*.so*" 2>/dev/null | wc -l | xargs)
    echo -e "      .so 파일 개수: ${SO_COUNT}"

    # Python 3.13+에서는 cv2.*.so 파일이 1-2개만 있어도 정상 작동
    if [ "$SO_COUNT" -ge 1 ]; then
        echo -e "${GREEN}      ✓ cv2 바이너리 파일 확인됨${NC}"
        SO_FILES_OK=true
    else
        echo -e "${YELLOW}      ⚠ cv2 바이너리 파일 없음${NC}"
        SO_FILES_OK=false
    fi
fi
echo ""

# PyInstaller collect_dynamic_libs 테스트
echo -e "${BLUE}[5/6]${NC} PyInstaller cv2 수집 테스트 중..."

if [ "$PLATFORM" = "Darwin" ]; then
    echo -e "${YELLOW}      ⚠ macOS 환경: PyInstaller 테스트 건너뜀${NC}"
    echo -e "${YELLOW}         (macOS에서 빌드한 실행 파일은 Ubuntu에서 작동하지 않습니다)${NC}"
    COLLECT_OK=true
else
    COLLECT_RESULT=$(python3 -c "
from PyInstaller.utils.hooks import collect_dynamic_libs
import cv2
cv2_libs = collect_dynamic_libs('cv2')
print(len(cv2_libs))
" 2>/dev/null || echo "0")

    echo -e "      collect_dynamic_libs 결과: ${COLLECT_RESULT}개 파일"

    # Python 3.13+에서는 1개 이상이면 충분
    if [ "$COLLECT_RESULT" -ge 1 ]; then
        echo -e "${GREEN}      ✓ PyInstaller cv2 수집 가능${NC}"
        COLLECT_OK=true
    else
        echo -e "${YELLOW}      ⚠ PyInstaller cv2 수집 파일 부족 (계속 진행)${NC}"
        # cv2 import가 성공했다면 수집 실패는 무시 가능
        COLLECT_OK=true
    fi
fi
echo ""

# 종합 판정
echo -e "${BLUE}[6/6]${NC} 종합 판정"
echo ""

if [ "$CV2_INSTALLED" = true ] && [ "$SO_FILES_OK" = true ] && [ "$COLLECT_OK" = true ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ 모든 검사 통과!${NC}"
    echo -e "${GREEN}  cv2가 올바르게 설치되어 있습니다.${NC}"

    if [ "$PLATFORM" = "Darwin" ]; then
        echo -e "${YELLOW}  ⚠️  macOS 환경: PyInstaller 빌드는 Ubuntu에서 진행하세요.${NC}"
    else
        echo -e "${GREEN}  PyInstaller 빌드를 진행할 수 있습니다.${NC}"
    fi

    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ 검사 실패!${NC}"
    echo -e "${RED}  cv2 설치에 문제가 있습니다.${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}자동 수정을 시도하시겠습니까? (y/N)${NC}"
    read -p "> " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}OpenCV 재설치 중...${NC}"

        # Python 버전 확인
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo -e "${YELLOW}  Python 버전: ${PYTHON_VERSION}${NC}"

        # OpenCV 완전 제거
        pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless 2>/dev/null || true

        # Python 버전에 따라 올바른 OpenCV 설치 (opencv-python + opencv-contrib-python 둘 다)
        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            echo -e "${BLUE}  Python 3.13: opencv-python + opencv-contrib-python 4.10+ 설치 중...${NC}"
            pip install "opencv-python>=4.10.0,<=4.12.0.88" "opencv-contrib-python>=4.10.0,<=4.12.0.88"
        else
            echo -e "${BLUE}  Python ${PYTHON_VERSION}: opencv-python + opencv-contrib-python 4.9+ 설치 중...${NC}"
            pip install "opencv-python>=4.9.0,<=4.12.0.88" "opencv-contrib-python>=4.9.0,<=4.12.0.88"
        fi

        echo ""
        echo -e "${BLUE}재검사 중...${NC}"

        # 재검사
        if python3 -c "import cv2; print('✓ cv2 재설치 성공:', cv2.__version__)" 2>/dev/null; then
            echo -e "${GREEN}✓ OpenCV 재설치 성공!${NC}"
            echo ""
            echo -e "${GREEN}이제 PyInstaller 빌드를 진행하세요:${NC}"
            echo -e "${GREEN}  pyinstaller --clean garame_manager.spec${NC}"
            exit 0
        else
            echo -e "${RED}✗ OpenCV 재설치 실패${NC}"
            echo ""
            echo -e "${YELLOW}수동 설치가 필요합니다:${NC}"

            # Python 버전 다시 확인
            PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

            if [[ "$PYTHON_VERSION" == "3.13" ]]; then
                echo -e "${YELLOW}  # Python 3.13용${NC}"
                echo -e "${YELLOW}  pip uninstall -y opencv-python opencv-contrib-python${NC}"
                echo -e "${YELLOW}  pip install 'opencv-contrib-python>=4.12.0'${NC}"
            else
                echo -e "${YELLOW}  # Python ${PYTHON_VERSION}용${NC}"
                echo -e "${YELLOW}  pip uninstall -y opencv-python opencv-contrib-python${NC}"
                echo -e "${YELLOW}  pip install opencv-contrib-python==4.9.0.80${NC}"
            fi
            exit 1
        fi
    else
        echo ""
        echo -e "${YELLOW}수동으로 cv2를 설치하세요:${NC}"

        # Python 버전 확인
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

        echo -e "${YELLOW}  pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless${NC}"
        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            echo -e "${YELLOW}  pip install 'opencv-python>=4.10.0,<=4.12.0.88' 'opencv-contrib-python>=4.10.0,<=4.12.0.88'  # Python 3.13용${NC}"
        else
            echo -e "${YELLOW}  pip install 'opencv-python>=4.9.0,<=4.12.0.88' 'opencv-contrib-python>=4.9.0,<=4.12.0.88'  # Python ${PYTHON_VERSION}용${NC}"
        fi
        exit 1
    fi
fi
