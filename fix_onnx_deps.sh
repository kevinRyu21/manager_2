#!/bin/bash
################################################################################
# ONNX 의존성 수정 스크립트
# ml_dtypes 버전 호환성 문제 해결
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}ONNX 의존성 수정${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 가상환경 활성화
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo -e "${BLUE}[1/3]${NC} 가상환경 활성화 중..."
    source venv/bin/activate
    echo -e "${GREEN}      ✓ 완료${NC}"
else
    echo -e "${RED}[오류]${NC} 가상환경을 찾을 수 없습니다."
    echo -e "${YELLOW}      먼저 ./install.sh를 실행하세요.${NC}"
    exit 1
fi
echo ""

# Python 및 현재 버전 확인
echo -e "${BLUE}[2/4]${NC} 현재 환경 확인 중..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${YELLOW}  Python 버전: ${PYTHON_VERSION}${NC}"
echo -e "${YELLOW}  현재 NumPy 버전:${NC}"
pip show numpy 2>/dev/null | grep Version || echo "  설치되지 않음"
echo -e "${YELLOW}  현재 ml-dtypes 버전:${NC}"
pip show ml-dtypes 2>/dev/null | grep Version || echo "  설치되지 않음"
echo ""

# Python 3.13 전용 처리
echo -e "${BLUE}[3/4]${NC} 의존성 업그레이드 중..."

if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    echo -e "${YELLOW}  Python 3.13 감지: NumPy 2.x + OpenCV 4.10+ 업그레이드${NC}"
    echo ""

    # NumPy 2.x 업그레이드
    echo -e "${BLUE}  NumPy 2.x 설치 중...${NC}"
    pip install --upgrade "numpy>=2.0.0"

    # OpenCV 4.10+ 업그레이드 (NumPy 2.x 지원)
    echo -e "${BLUE}  OpenCV 4.10+ 설치 중...${NC}"
    pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
    pip install "opencv-contrib-python>=4.10.0"

    # ml-dtypes 업그레이드
    echo -e "${BLUE}  ml-dtypes 0.5+ 설치 중...${NC}"
    pip install --upgrade "ml-dtypes>=0.5.0"
else
    echo -e "${YELLOW}  Python ${PYTHON_VERSION}: ml-dtypes만 업그레이드 (NumPy 1.26.4 유지)${NC}"
    pip install --upgrade "ml-dtypes>=0.5.0"
fi

echo ""
echo -e "${GREEN}✓ 의존성 업그레이드 완료${NC}"
echo ""

# 새 버전 확인
echo -e "${BLUE}[4/4]${NC} 업그레이드된 버전 확인"
echo -e "${GREEN}  NumPy:${NC}"
pip show numpy | grep Version
echo -e "${GREEN}  OpenCV:${NC}"
pip show opencv-contrib-python | grep Version
echo -e "${GREEN}  ml-dtypes:${NC}"
pip show ml-dtypes | grep Version
echo ""

# 테스트
echo -e "${BLUE}ONNX import 테스트 중...${NC}"
if python3 -c "import onnx; print('✓ ONNX import 성공')" 2>/dev/null; then
    echo -e "${GREEN}✓ ONNX 정상 작동${NC}"
else
    echo -e "${RED}✗ ONNX import 실패${NC}"
    echo -e "${YELLOW}  다음 명령으로 재설치하세요:${NC}"
    echo -e "${YELLOW}    pip install --upgrade onnx${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ 수정 완료!${NC}"
echo -e "${GREEN}  이제 ./run.sh를 실행하세요.${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""

exit 0
