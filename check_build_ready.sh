#!/bin/bash
################################################################################
# PyInstaller 빌드 준비 상태 확인 스크립트
# Ubuntu Linux 전용
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}PyInstaller 빌드 준비 상태 확인${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 플랫폼 확인
PLATFORM=$(uname -s)
if [ "$PLATFORM" != "Linux" ]; then
    echo -e "${RED}✗ 오류: Linux가 아닌 환경입니다 ($PLATFORM)${NC}"
    echo -e "${YELLOW}  PyInstaller 빌드는 Ubuntu Linux에서만 지원됩니다.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 플랫폼: Linux${NC}"

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ 오류: 가상환경을 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}  먼저 ./install.sh를 실행하세요.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 가상환경: 존재함${NC}"

# 가상환경 활성화
source venv/bin/activate

# Python 버전 확인
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"

# 필수 패키지 확인
echo ""
echo -e "${BLUE}필수 패키지 확인 중...${NC}"

PACKAGES=(
    "numpy"
    "opencv-contrib-python"
    "insightface"
    "onnxruntime"
    "ultralytics"
    "torch"
    "torchvision"
    "gtts"
    "pydub"
    "PIL:Pillow"
    "psutil"
    "pynput"
    "keyboard"
    "pystray"
    "pandas"
    "openpyxl"
    "pyinstaller"
)

ALL_OK=true
for PKG in "${PACKAGES[@]}"; do
    # PKG 형식: "import_name:package_name" 또는 "package_name"
    if [[ $PKG == *":"* ]]; then
        IMPORT_NAME="${PKG%%:*}"
        PACKAGE_NAME="${PKG##*:}"
    else
        IMPORT_NAME="$PKG"
        PACKAGE_NAME="$PKG"
    fi

    if python3 -c "import ${IMPORT_NAME}" 2>/dev/null; then
        VERSION=$(python3 -c "import ${IMPORT_NAME}; print(getattr(${IMPORT_NAME}, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        echo -e "${GREEN}  ✓ ${PACKAGE_NAME}: ${VERSION}${NC}"
    else
        echo -e "${RED}  ✗ ${PACKAGE_NAME}: 설치되지 않음${NC}"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo ""
    echo -e "${RED}✗ 일부 패키지가 설치되지 않았습니다.${NC}"
    echo -e "${YELLOW}  ./install.sh를 실행하여 모든 패키지를 설치하세요.${NC}"
    exit 1
fi

# OpenCV 바이너리 확인
echo ""
echo -e "${BLUE}OpenCV 바이너리 확인 중...${NC}"
./check_cv2.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ OpenCV 설정에 문제가 있습니다.${NC}"
    exit 1
fi

# PyInstaller 버전 확인
echo ""
echo -e "${BLUE}PyInstaller 확인 중...${NC}"
PYINSTALLER_VERSION=$(pyinstaller --version 2>/dev/null || echo "not installed")
if [ "$PYINSTALLER_VERSION" = "not installed" ]; then
    echo -e "${RED}✗ PyInstaller가 설치되지 않았습니다.${NC}"
    echo -e "${YELLOW}  pip install pyinstaller${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PyInstaller: $PYINSTALLER_VERSION${NC}"

# 필수 파일 확인
echo ""
echo -e "${BLUE}필수 파일 확인 중...${NC}"
REQUIRED_FILES=(
    "main.py"
    "garame_manager.spec"
    "VERSION.txt"
    "src"
)

for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -e "$FILE" ]; then
        echo -e "${GREEN}  ✓ $FILE${NC}"
    else
        echo -e "${RED}  ✗ $FILE: 존재하지 않음${NC}"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo ""
    echo -e "${RED}✗ 일부 필수 파일이 없습니다.${NC}"
    exit 1
fi

# 디스크 공간 확인
echo ""
echo -e "${BLUE}디스크 공간 확인 중...${NC}"
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
echo -e "${GREEN}✓ 사용 가능 공간: $AVAILABLE_SPACE${NC}"

# 숫자로 변환하여 5GB 이상 확인
if df -BG . &>/dev/null; then
    # Linux (GNU coreutils)
    AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
else
    # 대체 방법
    AVAILABLE_GB=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
fi

if [ -n "$AVAILABLE_GB" ] && [ "$AVAILABLE_GB" -lt 5 ]; then
    echo -e "${YELLOW}⚠️  경고: 디스크 여유 공간이 부족합니다 (${AVAILABLE_GB}GB < 5GB)${NC}"
    echo -e "${YELLOW}  빌드에 실패할 수 있습니다.${NC}"
fi

# 최종 판정
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ 모든 검사 통과!${NC}"
echo -e "${GREEN}  PyInstaller 빌드를 시작할 수 있습니다.${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}빌드 명령어:${NC}"
echo -e "  ${GREEN}pyinstaller --clean garame_manager.spec${NC}"
echo ""
echo -e "${BLUE}예상 빌드 시간:${NC} 5-10분"
echo -e "${BLUE}예상 빌드 크기:${NC} ~500MB (dist/garame_manager/)"
echo ""

exit 0
