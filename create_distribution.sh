#!/bin/bash

################################################################################
# GARAMe Manager v1.9.7 - 배포 패키지 생성 스크립트
# Ubuntu 25.10 전용
################################################################################

# set -e는 암호화 실패 시에도 계속 진행하도록 주석 처리

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "========================================="
echo "  GARAMe Manager v1.9.7"
echo "  배포 패키지 생성"
echo "========================================="
echo ""

# 0. 디스크 용량 확보
log_info "디스크 용량 확보 중..."

# 이전 배포 파일 삭제
log_info "  - 이전 배포 파일 삭제 중..."
rm -rf GARAMe_Manager_*_Distribution 2>/dev/null || true
rm -rf GARAMe_Manager_*_Distribution.tar.gz 2>/dev/null || true

# 임시 파일 정리
log_info "  - 임시 파일 정리 중..."
rm -rf temp_src_* obfuscated_* 2>/dev/null || true

# Python 캐시 삭제
log_info "  - Python 캐시 파일 삭제 중..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# pip 캐시 정리
rm -rf ~/.cache/pip/* 2>/dev/null || true

# 디스크 용량 확인
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
log_success "디스크 정리 완료. 사용 가능 공간: $AVAILABLE_SPACE"

# 최소 5GB 확인 (배포 패키지 생성에 필요)
# Linux와 macOS 호환성
if df -BG . &>/dev/null; then
    # Linux (GNU coreutils)
    AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
else
    # macOS (BSD)
    AVAILABLE_GB=$(df -g . | awk 'NR==2 {print $4}')
fi

if [ -n "$AVAILABLE_GB" ] && [ "$AVAILABLE_GB" -lt 5 ]; then
    log_warning "디스크 여유 공간이 부족합니다 (${AVAILABLE_GB}GB < 5GB)"
    log_warning "배포 패키지 생성에 실패할 수 있습니다"
fi

echo ""

# 1. 배포 디렉토리 생성
DIST_DIR="GARAMe_Manager_1.9.7_Ubuntu25_Distribution"
log_info "배포 디렉토리 생성 중: $DIST_DIR"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 2. PyInstaller 실행 파일 빌드 (Ubuntu에서만 실행)
if [ "$(uname -s)" = "Linux" ]; then
    log_info "PyInstaller로 실행 파일 빌드 중..."
    log_info "  (이 작업은 5-10분 소요됩니다)"

    # 가상환경 활성화
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # PyInstaller 설치 확인
    if ! command -v pyinstaller &> /dev/null; then
        log_info "PyInstaller 설치 중..."
        pip install pyinstaller
    fi

    # .spec 파일로 빌드
    if [ -f "garame_manager.spec" ]; then
        pyinstaller --clean garame_manager.spec

        # 빌드 성공 확인 (--onefile 모드: dist/garame_manager 단일 파일)
        if [ -f "dist/garame_manager" ]; then
            log_success "실행 파일 빌드 완료: dist/garame_manager"

            # 실행 파일을 배포 디렉토리로 복사
            cp dist/garame_manager "$DIST_DIR/"
            chmod +x "$DIST_DIR/garame_manager"

            # .spec 파일도 참고용으로 복사
            cp garame_manager.spec "$DIST_DIR/"

            # 파일 크기 표시
            FILE_SIZE=$(du -h dist/garame_manager | cut -f1)
            log_success "실행 파일 크기: $FILE_SIZE"
        else
            log_error "PyInstaller 빌드 실패, 원본 소스 복사로 대체"
            cp -r src "$DIST_DIR/"
            cp main.py "$DIST_DIR/"
        fi
    else
        log_warning "garame_manager.spec 파일이 없습니다. 원본 소스 복사"
        cp -r src "$DIST_DIR/"
        cp main.py "$DIST_DIR/"
    fi

    # 가상환경 비활성화
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
    fi
else
    log_warning "현재 시스템은 $(uname -s)입니다. PyInstaller 빌드는 Ubuntu에서만 지원됩니다."
    log_info "원본 소스 파일을 복사합니다..."
    cp -r src "$DIST_DIR/"
    cp main.py "$DIST_DIR/"
    cp garame_manager.spec "$DIST_DIR/" 2>/dev/null || true
fi

# 리소스 디렉토리 복사
cp -r safety_posters "$DIST_DIR/"
cp -r safety_photos "$DIST_DIR/" 2>/dev/null || true
cp -r assets "$DIST_DIR/" 2>/dev/null || true

# 설정 및 스크립트 파일 복사
cp requirements.txt "$DIST_DIR/"
cp install.sh "$DIST_DIR/"
cp uninstall.sh "$DIST_DIR/"
cp run.sh "$DIST_DIR/"
cp watchdog.py "$DIST_DIR/"
cp config.conf.example "$DIST_DIR/"
cp standard_defaults.conf "$DIST_DIR/"

# 선택적 파일 복사
cp config.conf "$DIST_DIR/" 2>/dev/null || true
cp setup_autostart.sh "$DIST_DIR/" 2>/dev/null || true

# 설명 문서 복사 (md 디렉토리에서)
cp md/README.md "$DIST_DIR/" 2>/dev/null || true
cp VERSION.txt "$DIST_DIR/"
cp md/VERSION_1.9.2_CHANGES.md "$DIST_DIR/" 2>/dev/null || true
cp md/INSTALL_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp md/DISK_SPACE_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp md/DISTRIBUTION_README.md "$DIST_DIR/" 2>/dev/null || true

log_info "소스 파일 복사 완료"

# 3. 오프라인 패키지 다운로드 (cmake 제외)
log_info "오프라인 설치를 위한 패키지 다운로드 중..."
log_info "(이 작업은 시간이 걸릴 수 있습니다)"

mkdir -p "$DIST_DIR/wheels"

if [ -f "requirements.txt" ]; then
    # 가상환경 활성화 (있는 경우)
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # requirements.txt에서 패키지 다운로드
    grep -v "^#" requirements.txt | \
        pip download --dest "$DIST_DIR/wheels" -r /dev/stdin || \
        log_error "일부 패키지 다운로드 실패 (계속 진행)"

    log_info "AI 라이브러리 (InsightFace, YOLOv11, gTTS) 다운로드 완료"
fi

# 4. 오프라인 설치 스크립트 생성
log_info "오프라인 설치 스크립트 생성 중..."

cat > "$DIST_DIR/install_offline.sh" << 'INSTALL_EOF'
#!/bin/bash

################################################################################
# GARAMe Manager v1.9.7 - 오프라인 설치 스크립트
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================="
echo "  GARAMe Manager v1.9.7"
echo "  오프라인 설치"
echo "========================================="
echo ""

# 1. 시스템 패키지 확인
log_info "시스템 패키지 확인 중..."

if ! command -v python3 &> /dev/null; then
    log_error "Python3가 설치되지 않았습니다."
    log_info "다음 명령어로 설치하세요: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    log_error "cmake가 설치되지 않았습니다."
    log_info "다음 명령어로 설치하세요: sudo apt install cmake build-essential"
    exit 1
fi

# 2. Python 가상환경 생성
log_info "Python 가상환경 생성 중..."

if [ -d "venv" ]; then
    log_info "기존 가상환경 삭제..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip setuptools wheel

# 3. 로컬 wheels에서 패키지 설치
log_info "오프라인 패키지 설치 중..."

if [ -d "wheels" ] && [ "$(ls -A wheels/*.whl 2>/dev/null)" ]; then
    pip install --no-index --find-links=wheels -r requirements.txt || \
        log_error "일부 패키지 설치 실패 (계속 진행)"
else
    log_error "wheels 디렉토리가 비어있습니다. 온라인 설치가 필요합니다."
    exit 1
fi

# 4. AI 모델 다운로드 (InsightFace, YOLOv11)
log_info "AI 모델은 첫 실행 시 자동으로 다운로드됩니다."

# 5. 데이터 디렉토리 생성
log_info "데이터 디렉토리 생성 중..."
mkdir -p data/faces data/backgrounds logs temp

# 6. 실행 권한 설정
chmod +x *.sh 2>/dev/null || true
chmod +x main.py 2>/dev/null || true

log_success "설치 완료!"
echo ""
echo "다음 명령어로 실행하세요:"
echo "  ./run.sh"
echo ""

INSTALL_EOF

chmod +x "$DIST_DIR/install_offline.sh"

# 5. 실행 스크립트 생성
log_info "실행 스크립트 생성 중..."

cat > "$DIST_DIR/run.sh" << 'RUN_EOF'
#!/bin/bash

# GARAMe Manager v1.9.7 실행 스크립트

cd "$(dirname "$0")"

# PyInstaller 실행 파일이 있으면 그것을 사용
if [ -f "./garame_manager" ] && [ -x "./garame_manager" ]; then
    echo "실행 파일 모드로 시작합니다..."
    ./garame_manager "$@"
    exit $?
fi

# Python 소스 모드 (가상환경 필요)
if [ ! -d "venv" ]; then
    echo "가상환경이 설치되지 않았습니다."
    echo "먼저 ./install_offline.sh를 실행하세요."
    exit 1
fi

source venv/bin/activate
python3 main.py "$@"

RUN_EOF

chmod +x "$DIST_DIR/run.sh"

# 6. README 생성
log_info "README 생성 중..."

cat > "$DIST_DIR/배포_설치_가이드.md" << 'README_EOF'
# GARAMe Manager v1.9.7 - 배포판 설치 가이드

## 시스템 요구사항

- **OS**: Ubuntu 25.10 (또는 호환 버전)
- **디스크**: 10GB 이상 여유 공간
- **RAM**: 4GB 이상 권장
- **네트워크**: 온라인 연결 (AI 모델 다운로드 시)

## 설치 전 준비

```bash
# 필수 시스템 패키지 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    libopencv-dev git wget curl xdotool
```

## 설치 방법

### 1. 파일 압축 해제

```bash
# 배포 파일을 원하는 위치에 압축 해제
cd ~/바탕화면
tar -xzf GARAMe_Manager_1.9.7_Ubuntu25_Distribution.tar.gz
cd GARAMe_Manager_1.9.7_Ubuntu25_Distribution
```

### 2. 오프라인 설치 실행

```bash
./install_offline.sh
```

**설치 시간**: 약 10-15분

### 3. 프로그램 실행

```bash
./run.sh
```

## 설치 옵션

### 온라인 설치 (wheels 없이)

인터넷 연결이 빠른 경우:

```bash
pip install -r requirements.txt
```

## 문제 해결

### AI 모델 다운로드 실패

```bash
# 인터넷 연결 확인 후 프로그램 재실행
# InsightFace와 YOLOv11 모델은 첫 실행 시 자동 다운로드됩니다
./run.sh
```

### 디스크 공간 부족

```bash
# 임시 파일 정리
sudo apt clean
sudo rm -rf /tmp/*

# 다시 시도
./install_offline.sh
```

## 파일 구조

```
GARAMe_Manager_1.9.7_Ubuntu25_Distribution/
├── garame_manager          # PyInstaller 실행 파일 (400MB)
├── run.sh                  # 실행 스크립트
├── install_offline.sh      # 설치 스크립트 (소스 모드용)
├── requirements.txt        # Python 패키지 목록
├── wheels/                 # 오프라인 패키지 (1-2GB)
├── safety_posters/         # 안전 포스터 이미지
├── assets/                 # 리소스 파일
└── 배포_설치_가이드.md      # 이 파일
```

## 실행 모드

### 실행 파일 모드 (권장)
PyInstaller로 빌드된 실행 파일이 포함된 경우:
```bash
./run.sh
# 또는 직접 실행
./garame_manager
```

### 소스 모드
실행 파일이 없는 경우 (Python 설치 필요):
```bash
./install_offline.sh
./run.sh
```

README_EOF

# 7. 압축
log_info "배포 패키지 압축 중..."

tar -czf "${DIST_DIR}.tar.gz" "$DIST_DIR"

DIST_SIZE=$(du -sh "$DIST_DIR" | cut -f1)
TAR_SIZE=$(du -sh "${DIST_DIR}.tar.gz" | cut -f1)

log_success "배포 패키지 생성 완료!"
echo ""
echo "========================================="
echo "  배포 파일 정보"
echo "========================================="
echo "  디렉토리: $DIST_DIR"
echo "  압축 파일: ${DIST_DIR}.tar.gz"
echo "  디렉토리 크기: $DIST_SIZE"
echo "  압축 파일 크기: $TAR_SIZE"
echo "========================================="
echo ""
echo "Ubuntu 25.10 시스템에 다음과 같이 배포하세요:"
echo "  1. ${DIST_DIR}.tar.gz 파일을 대상 시스템에 복사"
echo "  2. tar -xzf ${DIST_DIR}.tar.gz"
echo "  3. cd $DIST_DIR"
echo "  4. ./install_offline.sh"
echo "  5. ./run.sh"
echo ""
