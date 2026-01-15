#!/bin/bash
################################################################################
# GARAMe Manager - 빌드 및 패키징 스크립트
# 버전과 빌드 번호를 조합한 디렉토리 생성
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}GARAMe Manager 빌드 및 패키징${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# 버전과 빌드 번호 읽기
if [ ! -f "VERSION.txt" ] || [ ! -f "BUILD.txt" ]; then
    echo -e "${RED}[오류]${NC} VERSION.txt 또는 BUILD.txt 파일이 없습니다."
    exit 1
fi

VERSION=$(cat VERSION.txt | tr -d '[:space:]')
BUILD=$(cat BUILD.txt | tr -d '[:space:]')

echo -e "${BLUE}[정보]${NC} 버전: ${VERSION}"
echo -e "${BLUE}[정보]${NC} 빌드: ${BUILD}"
echo ""

# 배포 디렉토리 이름 생성
DIST_NAME="GARAMe_Manager_v${VERSION}-Build${BUILD}"
DIST_DIR="${DIST_NAME}"

echo -e "${BLUE}[정보]${NC} 배포 디렉토리: ${DIST_DIR}"
echo ""

# 기존 디렉토리 삭제
if [ -d "$DIST_DIR" ]; then
    echo -e "${YELLOW}[경고]${NC} 기존 배포 디렉토리 삭제 중..."
    rm -rf "$DIST_DIR"
fi

# 배포 디렉토리 생성
echo -e "${BLUE}[1/4]${NC} 배포 디렉토리 생성 중..."
mkdir -p "$DIST_DIR"
echo -e "${GREEN}      ✓ 디렉토리 생성 완료${NC}"
echo ""

# PyInstaller 빌드 (Linux에서만)
echo -e "${BLUE}[2/4]${NC} 실행 파일 빌드 중..."

if [ "$(uname -s)" = "Linux" ]; then
    # 가상환경 확인 및 생성
    if [ ! -d "venv" ]; then
        echo -e "${BLUE}      Python 가상환경 생성 중...${NC}"
        python3 -m venv venv || {
            echo -e "${RED}[오류]${NC} 가상환경 생성 실패"
            echo -e "${YELLOW}      다음 명령어를 실행하세요:${NC}"
            echo -e "${YELLOW}      sudo apt install python3-venv${NC}"
            exit 1
        }
    fi

    # 가상환경 활성화
    if [ -f "venv/bin/activate" ]; then
        echo -e "${BLUE}      가상환경 활성화 중...${NC}"
        source venv/bin/activate
    else
        echo -e "${RED}[오류]${NC} 가상환경을 찾을 수 없습니다"
        exit 1
    fi

    # pip 업그레이드
    echo -e "${BLUE}      pip 업그레이드 중...${NC}"
    pip install --upgrade pip setuptools wheel || {
        echo -e "${YELLOW}      pip 업그레이드 실패 (계속 진행)${NC}"
    }

    # PyInstaller 설치 확인
    if ! command -v pyinstaller &> /dev/null; then
        echo -e "${BLUE}      PyInstaller 설치 중...${NC}"
        pip install pyinstaller || {
            echo -e "${RED}[오류]${NC} PyInstaller 설치 실패"
            echo -e "${YELLOW}      수동으로 설치 후 다시 시도하세요:${NC}"
            echo -e "${YELLOW}      source venv/bin/activate${NC}"
            echo -e "${YELLOW}      pip install pyinstaller${NC}"
            exit 1
        }
        echo -e "${GREEN}      ✓ PyInstaller 설치 완료${NC}"
    else
        echo -e "${GREEN}      ✓ PyInstaller 이미 설치됨${NC}"
    fi

    # 빌드
    echo ""
    echo -e "${BLUE}      PyInstaller로 빌드 중... (5-10분 소요)${NC}"
    pyinstaller --clean garame_manager.spec || {
        echo -e "${RED}[오류]${NC} PyInstaller 빌드 실패"
        exit 1
    }

    # 빌드 확인
    if [ -f "dist/garame_manager" ]; then
        echo -e "${GREEN}      ✓ 빌드 완료: dist/garame_manager${NC}"

        # 실행 파일 크기 확인
        FILE_SIZE=$(du -h dist/garame_manager | awk '{print $1}')
        echo -e "${BLUE}      실행파일 크기: ${FILE_SIZE}${NC}"

        # 크기 검증
        SIZE_MB=$(du -m dist/garame_manager | awk '{print $1}')
        if [ "$SIZE_MB" -gt 1024 ]; then
            echo -e "${YELLOW}      ⚠ 경고: 실행파일이 1GB 이상입니다 (${FILE_SIZE})${NC}"
            echo -e "${YELLOW}      정상 범위는 200-400MB 입니다${NC}"
        elif [ "$SIZE_MB" -lt 150 ]; then
            echo -e "${YELLOW}      ⚠ 경고: 실행파일이 너무 작습니다 (${FILE_SIZE})${NC}"
            echo -e "${YELLOW}      cv2 바이너리가 누락되었을 수 있습니다${NC}"
            echo -e "${YELLOW}      정상 범위는 200-400MB 입니다${NC}"
        fi

        # cv2 간단 테스트 (선택적)
        echo ""
        echo -e "${BLUE}      cv2 모듈 포함 여부 확인 중...${NC}"
        if command -v strings &> /dev/null; then
            if strings dist/garame_manager | grep -q "cv2"; then
                echo -e "${GREEN}      ✓ cv2 모듈이 포함된 것으로 보입니다${NC}"
            else
                echo -e "${YELLOW}      ⚠ cv2 모듈이 포함되지 않았을 수 있습니다${NC}"
                echo -e "${YELLOW}      CV2_TROUBLESHOOTING.md를 참조하세요${NC}"
            fi
        fi

        # 배포 디렉토리로 복사
        cp dist/garame_manager "$DIST_DIR/"
        chmod +x "$DIST_DIR/garame_manager"
    else
        echo -e "${RED}[오류]${NC} PyInstaller 빌드 실패"
        exit 1
    fi

    # 가상환경 비활성화
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}      현재 시스템: $(uname -s)${NC}"
    echo -e "${YELLOW}      PyInstaller 빌드는 Ubuntu Linux에서만 지원됩니다${NC}"
    echo -e "${RED}[오류]${NC} 빌드 중단"
    exit 1
fi

echo ""

# 필수 파일 및 디렉토리 복사
echo -e "${BLUE}[3/4]${NC} 필수 파일 및 디렉토리 복사 중..."

# 버전 정보 파일
echo -e "${BLUE}      버전 정보...${NC}"
cp VERSION.txt "$DIST_DIR/"
cp BUILD.txt "$DIST_DIR/"
cp VERSION_INFO.json "$DIST_DIR/"
cp CHANGELOG_BUILD.md "$DIST_DIR/"

# 설정 파일
echo -e "${BLUE}      설정 파일...${NC}"
cp config.conf.example "$DIST_DIR/"
cp standard_defaults.conf "$DIST_DIR/"
cp config.conf "$DIST_DIR/" 2>/dev/null || echo -e "${YELLOW}      config.conf 없음 (기본값 사용)${NC}"

# 스크립트
echo -e "${BLUE}      스크립트...${NC}"
cp install.sh "$DIST_DIR/"
cp uninstall.sh "$DIST_DIR/"
cp run.sh "$DIST_DIR/"
cp watchdog.py "$DIST_DIR/"
cp check_cv2.sh "$DIST_DIR/" 2>/dev/null || echo -e "${YELLOW}      check_cv2.sh 없음 (선택 사항)${NC}"

# 스크립트 실행 권한 설정
chmod +x "$DIST_DIR/install.sh"
chmod +x "$DIST_DIR/uninstall.sh"
chmod +x "$DIST_DIR/run.sh"
chmod +x "$DIST_DIR/check_cv2.sh" 2>/dev/null || true

# PyInstaller 설정
cp garame_manager.spec "$DIST_DIR/"

# 요구사항
cp requirements.txt "$DIST_DIR/"

# 문서
echo -e "${BLUE}      문서...${NC}"
cp README.md "$DIST_DIR/" 2>/dev/null || true
cp md/INSTALL_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp md/DISK_SPACE_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp CV2_TROUBLESHOOTING.md "$DIST_DIR/" 2>/dev/null || true

# 필수 디렉토리 (리소스)
echo -e "${BLUE}      리소스 디렉토리...${NC}"
cp -r safety_posters "$DIST_DIR/"
cp -r safety_photos "$DIST_DIR/" 2>/dev/null || mkdir -p "$DIST_DIR/safety_photos"
cp -r assets "$DIST_DIR/" 2>/dev/null || mkdir -p "$DIST_DIR/assets"

# 런타임 생성 디렉토리 (빈 디렉토리)
echo -e "${BLUE}      런타임 디렉토리...${NC}"
mkdir -p "$DIST_DIR/face_db"
mkdir -p "$DIST_DIR/blueprints"
mkdir -p "$DIST_DIR/blueprint_data"
mkdir -p "$DIST_DIR/captures"
mkdir -p "$DIST_DIR/logs"
mkdir -p "$DIST_DIR/data"
mkdir -p "$DIST_DIR/temp"

# 선택적 디렉토리
cp -r manual "$DIST_DIR/" 2>/dev/null || true

echo -e "${GREEN}      ✓ 파일 복사 완료${NC}"
echo ""

# README 생성
echo -e "${BLUE}[4/4]${NC} 배포 README 생성 중..."

cat > "$DIST_DIR/README_DISTRIBUTION.txt" << EOF
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              GARAMe MANAGER 배포 패키지                      ║
║                                                              ║
║              버전: ${VERSION}                                    ║
║              빌드: ${BUILD}                                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 패키지 내용
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 실행 파일: garame_manager
✅ 설정 파일: config.conf.example, standard_defaults.conf
✅ 스크립트: install.sh, run.sh, uninstall.sh
✅ 리소스: safety_posters/, safety_photos/, assets/
✅ 데이터: face_db/, blueprints/, captures/, logs/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 빠른 시작 (Ubuntu 25.10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 이 디렉토리를 우분투 컴퓨터에 복사

2. 실행 권한 부여:
   chmod +x garame_manager
   chmod +x *.sh

3. 의존성 설치 (최초 1회만):
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv \\
       libopencv-dev cmake build-essential \\
       libgtk-3-0 libgstreamer1.0-0 espeak

4. Python 패키지 설치:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

5. 실행:
   ./garame_manager

   또는

   ./run.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 시스템 요구사항
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

운영체제: Ubuntu 25.10 (또는 호환 버전)
메모리: 최소 4GB RAM
디스크: 최소 2GB 여유 공간
Python: 3.11 이상
카메라: USB 카메라 (얼굴 인식 기능 사용 시)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 문제 해결
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: 실행 파일이 실행되지 않아요
A: chmod +x garame_manager 로 실행 권한을 부여하세요

Q: "library not found" 오류가 나요
A: sudo apt install libopencv-dev libgtk-3-0 실행

Q: 얼굴 인식이 안 돼요
A: requirements.txt 설치 확인 및 카메라 연결 확인

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 지원
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

문의: support@garame.co.kr
문서: INSTALL_GUIDE.md 참조

EOF

echo -e "${GREEN}      ✓ README 생성 완료${NC}"
echo ""

# 완료
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}빌드 및 패키징 완료!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""

# 디렉토리 크기 확인
DIST_SIZE=$(du -sh "$DIST_DIR" | awk '{print $1}')
echo -e "${BLUE}배포 디렉토리:${NC} ${DIST_DIR}"
echo -e "${BLUE}전체 크기:${NC} ${DIST_SIZE}"
echo ""

# 디렉토리 내용 요약
FILE_COUNT=$(find "$DIST_DIR" -type f | wc -l)
DIR_COUNT=$(find "$DIST_DIR" -type d | wc -l)
echo -e "${BLUE}파일 수:${NC} ${FILE_COUNT}"
echo -e "${BLUE}디렉토리 수:${NC} ${DIR_COUNT}"
echo ""

echo -e "${GREEN}✓${NC} 이 디렉토리를 다른 우분투 컴퓨터에 복사하면 실행 가능합니다"
echo -e "${GREEN}✓${NC} README_DISTRIBUTION.txt 파일을 참조하세요"
echo ""

# 압축 옵션 제공
read -p "배포 패키지를 tar.gz로 압축하시겠습니까? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ARCHIVE_NAME="${DIST_NAME}.tar.gz"
    echo -e "${BLUE}압축 중: ${ARCHIVE_NAME}${NC}"
    tar -czf "$ARCHIVE_NAME" "$DIST_DIR/"

    ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | awk '{print $1}')
    echo -e "${GREEN}✓ 압축 완료: ${ARCHIVE_NAME} (${ARCHIVE_SIZE})${NC}"

    # SHA256 체크섬 생성
    shasum -a 256 "$ARCHIVE_NAME" > "${ARCHIVE_NAME}.sha256"
    echo -e "${GREEN}✓ SHA256 체크섬: ${ARCHIVE_NAME}.sha256${NC}"
fi

echo ""
echo -e "${GREEN}모든 작업이 완료되었습니다!${NC}"
echo ""
