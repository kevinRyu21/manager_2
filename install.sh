#!/bin/bash

################################################################################
# GARAMe Manager - 통합 설치 스크립트
# Ubuntu 25 환경 최적화
# 오프라인 환경 지원 (얼굴인식, 문자인식 포함)
################################################################################

set -e  # 오류 발생 시 즉시 중단

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

# 디스크 사용량 추적 로그 파일
DISK_USAGE_LOG="disk_usage_install.log"

# 디스크 사용량 추적 함수
log_disk_usage() {
    local step_name="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "=========================================" | tee -a "$DISK_USAGE_LOG"
    echo "[$timestamp] $step_name" | tee -a "$DISK_USAGE_LOG"
    echo "=========================================" | tee -a "$DISK_USAGE_LOG"

    # 1. 모든 마운트 포인트의 사용량 (df -h)
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "=== 마운트 포인트별 디스크 사용량 ===" | tee -a "$DISK_USAGE_LOG"
    df -h | tee -a "$DISK_USAGE_LOG"

    # 2. 주요 디렉토리별 사용량
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "=== 주요 디렉토리별 사용량 ===" | tee -a "$DISK_USAGE_LOG"

    # / 루트 디렉토리의 1단계 하위 디렉토리
    echo "[ / 루트 디렉토리 하위 ]" | tee -a "$DISK_USAGE_LOG"
    sudo du -sh /* 2>/dev/null | sort -h | tee -a "$DISK_USAGE_LOG" || true

    # /tmp 디렉토리 상세
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ /tmp 임시 디렉토리 ]" | tee -a "$DISK_USAGE_LOG"
    sudo du -sh /tmp 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    if [ -d "/tmp" ]; then
        sudo du -sh /tmp/* 2>/dev/null | sort -h | head -n 20 | tee -a "$DISK_USAGE_LOG" || true
    fi

    # /var 디렉토리 상세
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ /var 디렉토리 ]" | tee -a "$DISK_USAGE_LOG"
    sudo du -sh /var 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    sudo du -sh /var/* 2>/dev/null | sort -h | head -n 20 | tee -a "$DISK_USAGE_LOG" || true

    # /home 디렉토리 상세
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ /home 디렉토리 ]" | tee -a "$DISK_USAGE_LOG"
    sudo du -sh /home 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    if [ -d "/home" ]; then
        sudo du -sh /home/* 2>/dev/null | sort -h | tee -a "$DISK_USAGE_LOG" || true
    fi

    # 현재 사용자 홈 디렉토리의 캐시
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ ~/.cache 디렉토리 ]" | tee -a "$DISK_USAGE_LOG"
    du -sh ~/.cache 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    if [ -d ~/.cache ]; then
        du -sh ~/.cache/* 2>/dev/null | sort -h | head -n 20 | tee -a "$DISK_USAGE_LOG" || true
    fi

    # 현재 작업 디렉토리
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ 현재 디렉토리: $(pwd) ]" | tee -a "$DISK_USAGE_LOG"
    du -sh . 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    du -sh * 2>/dev/null | sort -h | head -n 20 | tee -a "$DISK_USAGE_LOG" || true

    # Python pip 캐시
    echo "" | tee -a "$DISK_USAGE_LOG"
    echo "[ pip 캐시 ]" | tee -a "$DISK_USAGE_LOG"
    du -sh ~/.cache/pip 2>/dev/null | tee -a "$DISK_USAGE_LOG" || echo "pip 캐시 없음" | tee -a "$DISK_USAGE_LOG"

    # 가상환경 (있는 경우)
    if [ -d "venv" ]; then
        echo "" | tee -a "$DISK_USAGE_LOG"
        echo "[ venv 가상환경 ]" | tee -a "$DISK_USAGE_LOG"
        du -sh venv 2>/dev/null | tee -a "$DISK_USAGE_LOG" || true
    fi

    echo "" | tee -a "$DISK_USAGE_LOG"
    log_info "디스크 사용량이 $DISK_USAGE_LOG 에 기록되었습니다"
}

# GPU 감지 변수
HAS_NVIDIA_GPU=false
CUDA_VERSION=""

# NVIDIA GPU 감지 함수
detect_nvidia_gpu() {
    log_info "NVIDIA GPU 감지 중..."

    # 1. nvidia-smi 명령어 확인
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            HAS_NVIDIA_GPU=true

            # CUDA 버전 확인
            CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n 1)
            local gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1)
            local gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -n 1)

            log_success "NVIDIA GPU 감지됨!"
            log_info "  GPU: $gpu_name"
            log_info "  VRAM: $gpu_memory"
            log_info "  드라이버 버전: $CUDA_VERSION"

            # CUDA 툴킷 버전 확인
            if command -v nvcc &> /dev/null; then
                local nvcc_version=$(nvcc --version 2>/dev/null | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
                log_info "  CUDA 툴킷: $nvcc_version"
            else
                log_warning "  CUDA 툴킷이 설치되지 않음 (nvcc 없음)"
                log_info "  GPU 가속을 위해 CUDA 툴킷 설치를 권장합니다:"
                log_info "    sudo apt install nvidia-cuda-toolkit"
            fi
            return 0
        fi
    fi

    # 2. lspci로 NVIDIA GPU 확인 (드라이버 미설치 상태)
    if command -v lspci &> /dev/null; then
        if lspci | grep -i "nvidia" &> /dev/null; then
            log_warning "NVIDIA GPU가 있지만 드라이버가 설치되지 않았습니다"
            log_info "GPU 가속을 위해 NVIDIA 드라이버 설치를 권장합니다:"
            log_info "  sudo apt install nvidia-driver-535"
            log_info "  또는 ubuntu-drivers autoinstall"
        else
            log_info "NVIDIA GPU가 감지되지 않음 (CPU 모드로 설치)"
        fi
    else
        log_info "NVIDIA GPU가 감지되지 않음 (CPU 모드로 설치)"
    fi

    HAS_NVIDIA_GPU=false
    return 1
}

# 배너 출력
print_banner() {
    echo "========================================="
    echo "  GARAMe Manager v2.0.1"
    echo "  통합 설치 스크립트"
    echo "  Ubuntu 18.04+ (GPU 자동 감지 지원)"
    echo "========================================="
    echo ""
}

# 디스크 용량 확보 (설치 전 정리)
cleanup_disk_space() {
    log_info "디스크 용량 확보 중..."

    # 1. APT 캐시 정리
    log_info "  - APT 패키지 캐시 정리 중..."
    sudo apt clean 2>/dev/null || true
    sudo apt autoclean 2>/dev/null || true
    sudo apt autoremove -y 2>/dev/null || true

    # 2. 임시 파일 정리
    log_info "  - 임시 파일 정리 중..."
    sudo rm -rf /tmp/* 2>/dev/null || true
    sudo rm -rf /var/tmp/* 2>/dev/null || true
    rm -rf ~/.cache/pip/* 2>/dev/null || true

    # 3. 이전 가상환경 삭제
    if [ -d "venv" ]; then
        log_info "  - 이전 가상환경 삭제 중..."
        rm -rf venv
    fi

    # 4. Python 캐시 파일 삭제
    log_info "  - Python 캐시 파일 삭제 중..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true

    # 5. 이전 빌드 파일 삭제
    log_info "  - 이전 빌드 파일 삭제 중..."
    rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true

    # 6. 오래된 로그 파일 정리
    if [ -d "logs" ]; then
        log_info "  - 오래된 로그 파일 정리 중..."
        find logs -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
    fi

    # 7. 디스크 용량 확인
    AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
    log_success "디스크 정리 완료. 사용 가능 공간: $AVAILABLE_SPACE"

    # 8. 최소 15GB 확인
    # Linux와 macOS 호환성
    if df -BG . &>/dev/null; then
        # Linux (GNU coreutils)
        AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    else
        # macOS (BSD)
        AVAILABLE_GB=$(df -g . | awk 'NR==2 {print $4}')
    fi

    if [ -n "$AVAILABLE_GB" ] && [ "$AVAILABLE_GB" -lt 10 ]; then
        log_warning "디스크 여유 공간이 부족합니다 (${AVAILABLE_GB}GB < 10GB)"
        log_warning "InsightFace 모델 다운로드 시 실패할 수 있습니다"
        echo ""
        read -p "계속 진행하시겠습니까? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "설치가 취소되었습니다"
            exit 1
        fi
    fi
}

# /tmp 디렉토리 용량 확장
expand_tmp_space() {
    log_info "/tmp 디렉토리 용량 확인 및 확장 중..."

    # 현재 /tmp 마운트 상태 확인
    TMP_MOUNT_INFO=$(df -h /tmp | tail -1)
    TMP_SIZE=$(echo "$TMP_MOUNT_INFO" | awk '{print $2}')
    TMP_USED=$(echo "$TMP_MOUNT_INFO" | awk '{print $3}')
    TMP_AVAIL=$(echo "$TMP_MOUNT_INFO" | awk '{print $4}')
    TMP_USE_PERCENT=$(echo "$TMP_MOUNT_INFO" | awk '{print $5}')

    log_info "현재 /tmp 상태:"
    log_info "  크기: $TMP_SIZE, 사용: $TMP_USED, 여유: $TMP_AVAIL, 사용률: $TMP_USE_PERCENT"

    # /tmp가 tmpfs로 마운트되어 있는지 확인
    if mount | grep -q "tmpfs on /tmp"; then
        log_info "/tmp가 tmpfs로 마운트되어 있습니다. 크기를 8GB로 재마운트합니다..."

        # 기존 tmpfs 재마운트 (8GB)
        set +e  # 일시적으로 오류 시 종료 비활성화
        sudo mount -o remount,size=8G /tmp
        MOUNT_RESULT=$?
        set -e  # 다시 오류 시 종료 활성화

        if [ $MOUNT_RESULT -eq 0 ]; then
            # 재마운트 후 상태 확인
            TMP_MOUNT_INFO=$(df -h /tmp | tail -1)
            TMP_SIZE=$(echo "$TMP_MOUNT_INFO" | awk '{print $2}')
            log_success "/tmp 디렉토리를 8GB로 확장했습니다 (현재 크기: $TMP_SIZE)"
        else
            log_error "/tmp 재마운트 실패"
            log_warning "패키지 빌드 시 디스크 부족으로 실패할 수 있습니다"
        fi
    else
        # tmpfs가 아닌 경우, tmpfs로 새로 마운트
        log_info "/tmp가 tmpfs가 아닙니다. tmpfs로 마운트하여 8GB 할당합니다..."

        # 기존 /tmp 내용 백업
        TMP_BACKUP="/tmp_backup_$(date +%s)"
        set +e  # 일시적으로 오류 시 종료 비활성화
        sudo mkdir -p "$TMP_BACKUP"
        MKDIR_RESULT=$?
        set -e  # 다시 오류 시 종료 활성화

        if [ $MKDIR_RESULT -ne 0 ]; then
            log_warning "백업 디렉토리 생성 실패 (백업 없이 계속)"
        else
            sudo cp -a /tmp/* "$TMP_BACKUP/" 2>/dev/null || true
        fi

        # tmpfs로 마운트 (8GB)
        set +e  # 일시적으로 오류 시 종료 비활성화
        sudo mount -t tmpfs -o size=8G tmpfs /tmp
        MOUNT_RESULT=$?
        set -e  # 다시 오류 시 종료 활성화

        if [ $MOUNT_RESULT -eq 0 ]; then
            # 권한 설정
            sudo chmod 1777 /tmp

            # 백업 복원
            if [ -d "$TMP_BACKUP" ]; then
                sudo cp -a "$TMP_BACKUP"/* /tmp/ 2>/dev/null || true
                sudo rm -rf "$TMP_BACKUP"
            fi

            # 마운트 후 상태 확인
            TMP_MOUNT_INFO=$(df -h /tmp | tail -1)
            TMP_SIZE=$(echo "$TMP_MOUNT_INFO" | awk '{print $2}')
            log_success "/tmp를 tmpfs로 마운트했습니다 (크기: $TMP_SIZE)"
        else
            log_error "/tmp tmpfs 마운트 실패"
            log_warning "기존 /tmp를 계속 사용합니다"

            # 백업 복원
            if [ -d "$TMP_BACKUP" ]; then
                sudo rm -rf "$TMP_BACKUP"
            fi
        fi
    fi

    echo ""
}

# /tmp 복원 (설치 완료 후)
restore_tmp_space() {
    log_info "/tmp 디렉토리 정리 중..."

    # /tmp 임시 파일 정리
    sudo rm -rf /tmp/pip-* /tmp/tmp* /tmp/build-* 2>/dev/null || true

    # tmpfs를 원래 크기로 되돌릴지 확인
    if mount | grep -q "tmpfs on /tmp"; then
        log_info "/tmp가 tmpfs로 마운트되어 있습니다."
        log_info "설치 완료 후 /tmp 크기를 기본값으로 되돌리시겠습니까? (y/n) [기본값: n]"
        read -p "> " -r tmp_restore_response

        if [[ "$tmp_restore_response" =~ ^[Yy]$ ]]; then
            # 기본 크기로 재마운트 (시스템 RAM의 50%, 보통 4GB)
            set +e  # 일시적으로 오류 시 종료 비활성화
            sudo mount -o remount,size=50% /tmp
            RESTORE_RESULT=$?
            set -e  # 다시 오류 시 종료 활성화

            if [ $RESTORE_RESULT -eq 0 ]; then
                log_success "/tmp를 기본 크기로 되돌렸습니다"
            else
                log_warning "/tmp 복원 실패 (무시 가능)"
            fi
        else
            log_info "/tmp를 8GB로 유지합니다"
            log_info "재부팅 시 기본 크기로 복원됩니다"
        fi
    fi

    echo ""
}

# 루트 권한 확인
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "이 스크립트는 일반 사용자 권한으로 실행해야 합니다."
        log_error "sudo를 사용하지 마세요."
        exit 1
    fi
}

# Ubuntu 버전 확인
check_ubuntu_version() {
    log_info "Ubuntu 버전 확인 중..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "OS: $NAME $VERSION"

        if [[ "$NAME" != *"Ubuntu"* ]]; then
            log_warning "Ubuntu가 아닌 것 같습니다. 계속 진행하시겠습니까? (y/n)"
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_warning "OS 정보를 확인할 수 없습니다."
    fi
}

# 시스템 패키지 설치
install_system_packages() {
    log_info "시스템 패키지 업데이트 및 설치 중..."

    # 패키지 목록 업데이트
    set +e  # 일시적으로 오류 시 종료 비활성화
    sudo apt update
    APT_UPDATE_RESULT=$?
    set -e  # 다시 오류 시 종료 활성화

    if [ $APT_UPDATE_RESULT -ne 0 ]; then
        log_warning "apt update 실패 (계속 진행)"
    fi

    # 필수 패키지 설치
    log_info "필수 패키지 설치 중..."

    # 핵심 필수 패키지 (반드시 설치되어야 함)
    REQUIRED_PACKAGES="python3 python3-pip python3-venv python3-dev python3-tk python3-full build-essential cmake pkg-config git wget curl unzip"

    set +e  # 일시적으로 오류 시 종료 비활성화
    sudo apt install -y $REQUIRED_PACKAGES
    APT_INSTALL_RESULT=$?
    set -e  # 다시 오류 시 종료 활성화

    if [ $APT_INSTALL_RESULT -ne 0 ]; then
        log_error "필수 패키지 설치 실패"
        exit 1
    fi

    # OpenCV 및 관련 라이브러리 (필수)
    log_info "OpenCV 및 관련 라이브러리 설치 중..."
    sudo apt install -y \
        libopencv-dev \
        python3-opencv \
        libgtk-3-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev || log_warning "일부 OpenCV 패키지 설치 실패 (계속 진행)"

    # v1.9.8.3-1: InsightFace 사용 (dlib 제거됨)

    # 선택적 패키지 (없어도 됨)
    log_info "선택적 패키지 설치 시도..."
    OPTIONAL_PACKAGES="libboost-all-dev libxvidcore-dev libx264-dev"

    for pkg in $OPTIONAL_PACKAGES; do
        if apt-cache show $pkg > /dev/null 2>&1; then
            sudo apt install -y $pkg > /dev/null 2>&1 || log_warning "$pkg 설치 실패 (무시 가능)"
        else
            log_warning "$pkg 패키지 없음 (무시 가능)"
        fi
    done

    # TTS 음성 패키지 설치 (gTTS 기반 음성 알림)
    log_info "TTS 음성 재생 패키지 설치 중..."
    sudo apt install -y \
        mpg123 \
        ffmpeg || log_warning "TTS 음성 재생 패키지 설치 실패 (계속 진행)"

    # 화면 캡쳐 패키지 설치 (GNOME Wayland 호환)
    log_info "화면 캡쳐 패키지 설치 중..."
    sudo apt install -y \
        flameshot || log_warning "flameshot 설치 실패 (화면 캡쳐 기능 제한될 수 있음)"

    log_success "시스템 패키지 설치 완료"
}

# 한글 폰트 설치
install_korean_fonts() {
    log_info "한글 폰트 설치 중..."

    # 필수 나눔 폰트
    sudo apt install -y fonts-nanum

    # 선택적 폰트 (실패해도 계속)
    for pkg in fonts-nanum-coding fonts-nanum-extra; do
        if apt-cache show $pkg > /dev/null 2>&1; then
            sudo apt install -y $pkg 2>/dev/null || true
        fi
    done

    # 폰트 캐시 갱신
    sudo fc-cache -fv > /dev/null 2>&1 || true

    log_success "한글 폰트 설치 완료"
}

# Python 가상환경 생성
setup_virtual_env() {
    log_info "Python 가상환경 설정 중..."

    VENV_DIR="venv"

    if [ -d "$VENV_DIR" ]; then
        log_info "기존 가상환경을 삭제하고 새로 만듭니다..."
        rm -rf "$VENV_DIR"
    fi

    # 가상환경 생성
    python3 -m venv "$VENV_DIR"

    # 가상환경 활성화
    source "$VENV_DIR/bin/activate"

    # pip 업그레이드
    pip install --upgrade pip setuptools wheel

    log_success "Python 가상환경 생성 완료"
}

# Python 패키지 설치 (온라인)
install_python_packages_online() {
    log_info "Python 패키지 설치 중 (온라인 모드)..."

    source venv/bin/activate

    # GPU 자동 감지 설치 (v1.9.8.3-1: CUDA 12.8 지원)
    if [ "$HAS_NVIDIA_GPU" = true ]; then
        log_info "GPU + CPU 모드로 설치합니다. (NVIDIA GPU 감지됨)"
        log_info "  - GPU 가속 패키지 설치 (onnxruntime-gpu, PyTorch CUDA)"
        log_info "  - CPU 폴백 지원"
    else
        log_info "CPU 모드로 설치합니다. (GPU 미감지)"
        log_info "  - 성능 모드 1, 2 사용 가능"
        log_info "  - 성능 모드 3 (GPU 필요) 사용 시 속도 저하 있을 수 있음"
    fi
    echo ""

    # requirements.txt가 있으면 사용
    if [ -f "requirements.txt" ]; then
        log_info "requirements.txt에서 패키지 설치 중..."
        pip install -r requirements.txt

        # Python 버전별 호환성 처리
        echo ""
        log_info "Python 버전 호환성 확인 중..."
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        log_info "Python 버전: ${PYTHON_VERSION}"

        # numpy 버전 제한 (opencv, ultralytics 호환성)
        # opencv-python <= 4.12.0.88은 numpy < 2.3.0 요구
        # ultralytics 8.3.229는 numpy <= 2.3.4 요구
        log_info ""
        log_info "NumPy 호환 버전 설치 중 (opencv, ultralytics 호환성)..."
        pip install --upgrade "numpy>=2.0.0,<2.3.0" || log_warning "NumPy 설치 실패"

        # OpenCV 설치 (opencv-python과 opencv-contrib-python 모두 설치)
        log_info "  OpenCV 설치 중..."
        pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless 2>/dev/null || true

        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            # Python 3.13: OpenCV 4.10+
            pip install "opencv-python>=4.10.0,<=4.12.0.88" || log_warning "opencv-python 설치 실패"
            pip install "opencv-contrib-python>=4.10.0,<=4.12.0.88" || log_warning "opencv-contrib-python 설치 실패"
        else
            # Python 3.12 이하: OpenCV 4.9+
            pip install "opencv-python>=4.9.0,<=4.12.0.88" || log_warning "opencv-python 설치 실패"
            pip install "opencv-contrib-python>=4.9.0,<=4.12.0.88" || log_warning "opencv-contrib-python 설치 실패"
        fi

        # ml-dtypes (Python 3.13+)
        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            log_info "  ml-dtypes 0.5+ 설치 중..."
            pip install --upgrade "ml-dtypes>=0.5.0" || log_warning "ml-dtypes 업그레이드 실패"
        fi

        echo ""
        log_success "Python ${PYTHON_VERSION} 호환 패키지 설치 완료"

        # 설치된 버전 확인
        log_info "설치된 버전:"
        python3 -c "import numpy; print(f'  NumPy: {numpy.__version__}')" 2>/dev/null || true
        python3 -c "import cv2; print(f'  OpenCV: {cv2.__version__}')" 2>/dev/null || true
        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            python3 -c "import ml_dtypes; print(f'  ml-dtypes: {ml_dtypes.__version__}')" 2>/dev/null || true
        fi
        echo ""

        # ONNX import 테스트
        log_info "ONNX import 테스트 중..."
        if python3 -c "import onnx; print('  ✓ ONNX import 성공')" 2>/dev/null; then
            log_success "ONNX 정상 작동"
        else
            log_warning "ONNX import 실패 - 첫 실행 시 자동으로 수정됩니다"
        fi
        echo ""

        # AI 라이브러리 자동 설치 (v1.9.8.3-1 필수)
        echo ""
        log_info "========================================="
        log_info "AI 라이브러리 자동 설치 중..."
        log_info "========================================="
        echo ""
        log_info "다음 패키지들이 자동으로 설치됩니다:"
        log_info "  • gTTS + pydub (음성 알림 시스템)"
        log_info "  • pytapo + onvif-zeep (IP 카메라 PTZ/ONVIF)"
        log_info "  • InsightFace + ONNX Runtime (얼굴 인식 99.86%)"
        log_info "  • Ultralytics (YOLOv11 PPE 감지 92.7%)"
        log_info "  • PyTorch (ML 프레임워크)"
        log_info "  • opencv-python (Ultralytics 의존성)"
        echo ""

        # gTTS + pydub (음성 알림)
        log_info "[1/7] gTTS + pydub 설치 중 (음성 알림 시스템)..."
        pip install gtts pydub || log_warning "gTTS/pydub 설치 실패"

        # pytapo (Tapo 카메라 PTZ 제어)
        log_info "[2/7] pytapo 설치 중 (Tapo 카메라 PTZ 제어)..."
        pip install pytapo || log_warning "pytapo 설치 실패"

        # onvif-zeep (ONVIF 프로토콜 지원)
        log_info "[3/7] onvif-zeep 설치 중 (IP 카메라 ONVIF 프로토콜)..."
        pip install onvif-zeep || log_warning "onvif-zeep 설치 실패"

        # InsightFace + ONNX Runtime (얼굴 인식)
        log_info "[4/8] InsightFace 설치 중 (얼굴 인식 99.86%)..."
        pip install insightface || log_warning "InsightFace 설치 실패"

        # ONNX Runtime (CPU 필수 + GPU 선택)
        log_info "[5/8] ONNX Runtime 설치 중..."
        # CPU 버전은 항상 설치 (필수)
        log_info "  CPU 버전 설치 중 (필수)..."
        pip install onnxruntime || log_warning "ONNX Runtime CPU 설치 실패"

        # GPU가 있으면 GPU 버전도 추가 설치
        if [ "$HAS_NVIDIA_GPU" = true ]; then
            log_info "  GPU 버전 추가 설치 중..."
            pip install onnxruntime-gpu || log_warning "onnxruntime-gpu 설치 실패 (CPU 버전 사용)"
        fi

        # Ultralytics (YOLOv11 PPE 감지)
        log_info "[6/8] Ultralytics 설치 중 (YOLOv11 PPE 감지 92.7%)..."
        pip install ultralytics || log_warning "Ultralytics 설치 실패"

        # opencv-python (Ultralytics 의존성)
        # opencv-python과 opencv-contrib-python 모두 설치 (Ultralytics 요구)
        log_info "[7/8] opencv-python 설치 확인 중 (Ultralytics 의존성)..."
        if [[ "$PYTHON_VERSION" == "3.13" ]]; then
            pip install "opencv-python>=4.10.0,<=4.12.0.88" || log_warning "opencv-python 설치 실패"
            pip install "opencv-contrib-python>=4.10.0,<=4.12.0.88" || log_warning "opencv-contrib-python 설치 실패"
        else
            pip install "opencv-python>=4.9.0,<=4.12.0.88" || log_warning "opencv-python 설치 실패"
            pip install "opencv-contrib-python>=4.9.0,<=4.12.0.88" || log_warning "opencv-contrib-python 설치 실패"
        fi

        # PyTorch 설치 (CPU 필수 + GPU 선택)
        log_info "[8/8] PyTorch 설치 중 (ML 프레임워크)..."

        # GPU가 있으면 CUDA 버전 설치 (CPU도 호환)
        if [ "$HAS_NVIDIA_GPU" = true ]; then
            log_info "  GPU 버전 설치 중 (PyPI CUDA 자동 감지)..."
            # PyPI에서 시스템 CUDA 버전에 맞는 PyTorch 자동 설치
            pip install torch torchvision || {
                log_warning "PyTorch 자동 설치 실패, CUDA 12.1 시도 중..."
                pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 || {
                    log_warning "PyTorch CUDA 12.1 설치 실패, CUDA 11.8 시도 중..."
                    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 || {
                        log_warning "PyTorch CUDA 설치 실패, CPU 버전으로 대체..."
                        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || \
                            log_warning "PyTorch 설치 실패"
                    }
                }
            }
        else
            # GPU가 없어도 CPU 버전 설치 (필수)
            log_info "  CPU 버전 설치 중..."
            pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || \
                log_warning "PyTorch CPU 설치 실패"
        fi

        log_success "PyTorch 설치 완료 (GPU 없이도 CPU 모드로 실행 가능)"

        echo ""
        log_success "AI 라이브러리 자동 설치 완료"

        # 설치된 AI 라이브러리 확인
        log_info "설치된 AI 라이브러리 버전:"
        python3 -c "import gtts; print(f'  gTTS: {gtts.__version__}')" 2>/dev/null || echo "  gTTS: 설치되지 않음"
        python3 -c "import insightface; print(f'  InsightFace: {insightface.__version__}')" 2>/dev/null || echo "  InsightFace: 설치되지 않음"
        python3 -c "import ultralytics; print(f'  Ultralytics: {ultralytics.__version__}')" 2>/dev/null || echo "  Ultralytics: 설치되지 않음"
        python3 -c "import torch; print(f'  PyTorch: {torch.__version__}')" 2>/dev/null || echo "  PyTorch: 설치되지 않음"
        python3 -c "import onnxruntime; print(f'  ONNX Runtime: {onnxruntime.__version__}')" 2>/dev/null || echo "  ONNX Runtime: 설치되지 않음"
        python3 -c "import cv2; print(f'  opencv-python: {cv2.__version__}')" 2>/dev/null || echo "  opencv-python: 설치되지 않음"
        echo ""

        # GPU 가속 상태 확인
        log_info "GPU 가속 상태:"
        python3 -c "import torch; cuda_available = torch.cuda.is_available(); print(f'  PyTorch CUDA: {\"사용 가능\" if cuda_available else \"사용 불가 (CPU 모드)\"}'); print(f'  CUDA 버전: {torch.version.cuda}' if cuda_available else '')" 2>/dev/null || echo "  PyTorch: 확인 불가"
        python3 -c "
import onnxruntime as ort
providers = ort.get_available_providers()
if 'CUDAExecutionProvider' in providers:
    print('  ONNX Runtime: GPU 가속 가능 (CUDAExecutionProvider)')
else:
    print('  ONNX Runtime: CPU 모드 (CPUExecutionProvider)')
" 2>/dev/null || echo "  ONNX Runtime: 확인 불가"
        echo ""

        # OpenCV 설치 확인 및 재설치 (중요!)
        log_info ""
        log_info "OpenCV 설치 확인 중..."
        if ! python3 -c "import cv2; print('cv2 버전:', cv2.__version__)" 2>/dev/null; then
            log_warning "OpenCV가 설치되지 않았습니다. 재설치 중..."
            pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless 2>/dev/null || true

            if [[ "$PYTHON_VERSION" == "3.13" ]]; then
                pip install "opencv-python>=4.10.0,<=4.12.0.88" "opencv-contrib-python>=4.10.0,<=4.12.0.88" || {
                    log_error "OpenCV 설치 실패!"
                    log_info "PyInstaller 빌드 시 cv2 오류가 발생할 수 있습니다."
                }
            else
                pip install "opencv-python>=4.9.0,<=4.12.0.88" "opencv-contrib-python>=4.9.0,<=4.12.0.88" || {
                    log_error "OpenCV 설치 실패!"
                    log_info "PyInstaller 빌드 시 cv2 오류가 발생할 수 있습니다."
                }
            fi
        else
            log_success "OpenCV 설치 확인 완료"
            python3 -c "import cv2; print('  버전:', cv2.__version__); print('  경로:', cv2.__file__)"
        fi

        # 시스템 cmake 확인 (일부 패키지에 필요)
        log_info ""
        log_info "시스템 도구 확인 중..."
        if ! command -v cmake &> /dev/null; then
            log_warning "시스템 cmake가 설치되지 않았습니다. 설치 중..."
            sudo apt install -y cmake
        fi
        log_success "시스템 도구 확인 완료"
    else
        # 수동으로 필수 패키지 설치
        log_info "필수 패키지 개별 설치 중..."

        # 기본 패키지 (NumPy + OpenCV 포함)
        log_info "NumPy 및 OpenCV 설치 중..."
        # NumPy 버전 제한 (opencv, ultralytics 호환성)
        pip install "numpy>=2.0.0,<2.3.0" || {
            log_error "NumPy 설치 실패"
            exit 1
        }

        # OpenCV 설치
        pip install "opencv-python>=4.9.0,<=4.12.0.88" "opencv-contrib-python>=4.9.0,<=4.12.0.88" pillow || {
            log_error "OpenCV 설치 실패"
            exit 1
        }

        # OpenCV 설치 확인
        if python3 -c "import cv2; print('✓ cv2 설치 성공:', cv2.__version__)" 2>/dev/null; then
            log_success "OpenCV 설치 확인 완료"
        else
            log_error "OpenCV 설치 실패! PyInstaller 빌드가 실패할 수 있습니다."
        fi

        # GUI 및 기타
        pip install configparser
    fi

    log_success "Python 패키지 설치 완료"
}

# Python 패키지 설치 (오프라인)
install_python_packages_offline() {
    log_info "Python 패키지 설치 중 (오프라인 모드)..."

    source venv/bin/activate

    if [ -d "wheels" ] && [ "$(ls -A wheels/*.whl 2>/dev/null)" ]; then
        log_info "로컬 wheels 디렉토리에서 패키지 설치 중..."

        # requirements.txt가 있으면 사용, 없으면 wheels 디렉토리의 모든 패키지 설치
        if [ -f "requirements.txt" ]; then
            pip install --no-index --find-links=wheels -r requirements.txt || {
                log_warning "requirements.txt를 사용한 설치 실패. wheels 직접 설치 시도..."
                pip install --no-index --find-links=wheels wheels/*.whl
            }
        else
            log_info "requirements.txt가 없습니다. wheels 디렉토리의 모든 패키지를 설치합니다..."
            pip install --no-index --find-links=wheels wheels/*.whl
        fi

        log_success "오프라인 패키지 설치 완료"
    else
        log_error "wheels 디렉토리가 없거나 비어있습니다."
        log_info "온라인 설치를 시도합니다..."
        install_python_packages_online
    fi
}


# AI 모델 다운로드 (InsightFace, YOLOv11)
download_ai_models() {
    log_info "AI 모델 확인 중..."

    # v1.9.8.2: 고성능 시스템 최적화
    log_success "AI 모델은 첫 실행 시 자동으로 다운로드됩니다"
    log_info "  - InsightFace (buffalo_l): 고정밀 얼굴 인식 모델 (99.86% 정확도)"
    log_info "  - YOLOv11m: 고정밀 PPE 안전장구 감지 모델 (92.7% mAP50)"
    log_info ""
    log_info "모델 크기 (첫 실행 시 자동 다운로드):"
    log_info "  - buffalo_l: 약 275MB"
    log_info "  - yolo11m.pt: 약 39MB"
}

# 설정 파일 생성
create_config_files() {
    log_info "설정 파일 확인 중..."

    # config.conf가 없으면 기본 설정 파일 복사
    if [ ! -f "config.conf" ]; then
        if [ -f "config.conf.default" ]; then
            log_info "기본 설정 파일 복사 중 (config.conf.default → config.conf)..."
            cp config.conf.default config.conf
            log_success "기본 설정 파일 복사 완료"
        else
            log_warning "config.conf.default 파일이 없습니다. 프로그램 첫 실행 시 자동 생성됩니다."
        fi
    else
        log_info "설정 파일이 이미 존재합니다 (config.conf)"
    fi
}

# 데이터 디렉토리 생성
create_data_directories() {
    log_info "데이터 디렉토리 생성 중..."

    mkdir -p data/faces
    mkdir -p data/backgrounds
    mkdir -p logs
    mkdir -p temp

    log_success "데이터 디렉토리 생성 완료"
}

# 실행 권한 설정
set_permissions() {
    log_info "실행 권한 설정 중..."

    chmod +x run.sh 2>/dev/null || true
    chmod +x *.sh 2>/dev/null || true
    chmod +x main.py 2>/dev/null || true

    log_success "실행 권한 설정 완료"
}

# 시스템 설정 최적화 (화면 보호기, 절전, 알림 비활성화)
optimize_system_settings() {
    log_info "시스템 설정 최적화 중... (화면 보호기, 절전 모드, 시스템 알림 비활성화)"

    # 1. 화면 꺼짐 비활성화
    log_info "  - 화면 자동 꺼짐 비활성화..."
    gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null || \
        log_warning "화면 꺼짐 설정 실패 (무시 가능)"

    # 2. 화면 잠금 비활성화
    log_info "  - 화면 잠금 비활성화..."
    gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null || \
        log_warning "화면 잠금 설정 실패 (무시 가능)"

    # 3. 절전 모드 비활성화 (AC 전원 연결 시)
    log_info "  - 절전 모드 비활성화..."
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' 2>/dev/null || \
        log_warning "절전 모드 설정 실패 (무시 가능)"

    # 4. 화면 밝기 자동 조정 비활성화
    log_info "  - 화면 밝기 자동 조정 비활성화..."
    gsettings set org.gnome.settings-daemon.plugins.power idle-dim false 2>/dev/null || \
        log_warning "화면 밝기 설정 실패 (무시 가능)"

    # 5. 시스템 알림 비활성화
    log_info "  - 시스템 알림 비활성화..."
    gsettings set org.gnome.desktop.notifications show-banners false 2>/dev/null || \
        log_warning "알림 배너 설정 실패 (무시 가능)"

    gsettings set org.gnome.desktop.notifications show-in-lock-screen false 2>/dev/null || \
        log_warning "잠금 화면 알림 설정 실패 (무시 가능)"

    # 6. 업데이트 알림 비활성화 (선택) - sudo 없이 시도
    log_info "  - 자동 업데이트 알림 비활성화 시도..."
    systemctl --user disable update-notifier 2>/dev/null || true

    log_success "시스템 설정 최적화 완료"
    log_info ""
    log_info "최적화된 설정:"
    log_info "  ✓ 화면 자동 꺼짐: 비활성화"
    log_info "  ✓ 화면 잠금: 비활성화"
    log_info "  ✓ 절전 모드: 비활성화"
    log_info "  ✓ 화면 밝기 자동 조정: 비활성화"
    log_info "  ✓ 시스템 알림: 비활성화"
    log_info ""
}

# 자동 시작 설정 (자동 실행)
setup_autostart() {
    log_info "자동 시작 설정 중..."

    if [ -f "setup_autostart.sh" ]; then
        bash setup_autostart.sh
    else
        log_warning "setup_autostart.sh 파일을 찾을 수 없습니다 (선택 사항)"
    fi
}

# 설치 완료 메시지
print_completion_message() {
    echo ""
    echo "========================================="
    echo -e "${GREEN}  설치 완료!${NC}"
    echo "========================================="
    echo ""
    echo "다음 명령어로 프로그램을 실행하세요:"
    echo -e "  ${BLUE}./run.sh${NC}"
    echo ""

    # 실행 파일이 생성되었는지 확인
    if [ -f "./garame_manager" ]; then
        echo "실행 파일 모드로 설치되었습니다:"
        echo -e "  ${GREEN}✓${NC} 실행 파일: ./garame_manager"
        echo -e "  ${BLUE}./run.sh${NC} 실행 시 자동으로 실행 파일 사용"
        echo ""
        echo "또는 실행 파일 직접 실행:"
        echo -e "  ${BLUE}./garame_manager${NC}"
        echo ""
    else
        echo "Python 소스 모드로 설치되었습니다:"
        echo -e "  ${BLUE}./run.sh${NC} 실행 시 가상환경 자동 활성화"
        echo ""
        echo "또는 Python으로 직접 실행:"
        echo -e "  ${BLUE}source venv/bin/activate${NC}"
        echo -e "  ${BLUE}python3 main.py${NC}"
        echo ""
    fi
    echo "자세한 정보는 다음 문서를 참고하세요:"
    echo "  - README.md"
    echo "  - docs/CHANGELOG_v1.9.8.2.md"
    echo ""
}

# PyInstaller 실행 파일 빌드
build_executable() {
    # 실행 파일이 이미 존재하는지 확인 (배포판에 포함된 경우)
    # --onefile 모드: 단일 실행 파일 확인
    if [ -f "./garame_manager" ] && [ -x "./garame_manager" ]; then
        log_success "실행 파일이 이미 존재합니다: ./garame_manager"

        # 파일 크기 확인
        FILE_SIZE=$(du -h ./garame_manager | awk '{print $1}')
        log_info "실행파일 크기: ${FILE_SIZE}"

        # 버전 및 빌드 정보 표시
        if [ -f "VERSION.txt" ]; then
            VERSION=$(cat VERSION.txt | tr -d '[:space:]')
            log_info "버전: v${VERSION}"
        fi

        echo ""
        log_success "PyInstaller 빌드를 건너뜁니다 (이미 빌드됨)"
        log_info "실행 파일 모드로 동작합니다"
        log_info "실행 방법:"
        log_info "  • ./run.sh (권장)"
        log_info "  • ./garame_manager (직접 실행)"
        echo ""
        return
    fi

    log_info "실행 파일 빌드 (선택 사항)"
    echo ""
    log_info "PyInstaller를 사용하여 Python 소스를 단일 실행 파일로 빌드할 수 있습니다."
    log_info "실행 파일 빌드 시 장점:"
    log_info "  • 소스 코드가 바이너리로 포함되어 보호됨"
    log_info "  • 가상환경 활성화 없이 실행 가능"
    log_info "  • 약간 빠른 시작 속도"
    log_info ""
    log_info "실행 파일 빌드 시 단점:"
    log_info "  • 빌드 시간: 5-10분 소요"
    log_info "  • 파일 크기: 약 200-400MB"
    log_info "  • 추가 디스크 공간 필요: 약 1-2GB"
    log_info ""

    read -p "실행 파일을 빌드하시겠습니까? (y/n) [기본값: n] " -r response
    echo ""

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "실행 파일 빌드를 건너뜁니다."
        log_info "Python 소스 모드로 실행됩니다: ./run.sh"
        return
    fi

    log_info "실행 파일 빌드를 시작합니다..."
    echo ""

    # 가상환경 활성화 확인
    if [ -z "$VIRTUAL_ENV" ] && [ -d "venv" ]; then
        log_info "가상환경 활성화 중..."
        source venv/bin/activate
    fi

    # PyInstaller 설치 확인 및 설치
    log_info "PyInstaller 확인 중..."
    if ! command -v pyinstaller &> /dev/null; then
        log_info "PyInstaller가 설치되어 있지 않습니다. 설치 중..."
        pip install pyinstaller || {
            log_error "PyInstaller 설치 실패"
            log_warning "실행 파일 빌드를 건너뜁니다. Python 소스 모드로 실행하세요."
            return
        }
        log_success "PyInstaller 설치 완료"
    else
        log_success "PyInstaller가 이미 설치되어 있습니다"
    fi

    # jaraco 패키지 설치 (pkg_resources 의존성)
    log_info "PyInstaller 의존성 확인 중..."
    pip install jaraco.text jaraco.functools jaraco.context > /dev/null 2>&1 || log_warning "jaraco 패키지 설치 실패 (계속 진행)"

    # .spec 파일 확인
    if [ ! -f "garame_manager.spec" ]; then
        log_error "garame_manager.spec 파일을 찾을 수 없습니다"
        log_warning "실행 파일 빌드를 건너뜁니다"
        return
    fi

    # 이전 빌드 정리
    log_info "이전 빌드 파일 정리 중..."
    rm -rf build/ dist/ 2>/dev/null || true

    # OpenCV (cv2) 검사 (중요!)
    log_info ""
    log_info "OpenCV (cv2) 검사 중..."
    if [ -f "check_cv2.sh" ]; then
        chmod +x check_cv2.sh
        # check_cv2.sh 실행 (자동 수정 포함)
        # exit 0: 검사 통과 또는 자동 수정 성공
        # exit 1: 검사 실패 및 자동 수정 거부/실패
        ./check_cv2.sh
        CV2_CHECK_RESULT=$?

        if [ $CV2_CHECK_RESULT -ne 0 ]; then
            log_warning ""
            log_warning "cv2 검사가 완료되지 않았습니다."
            log_warning "PyInstaller 빌드 시 cv2 오류가 발생할 수 있습니다."
            echo ""
        fi
    else
        # check_cv2.sh가 없으면 간단 검사
        if ! python3 -c "import cv2; print('✓ cv2 확인:', cv2.__version__)" 2>/dev/null; then
            log_error "cv2를 import할 수 없습니다!"
            log_info "OpenCV를 재설치합니다..."
            pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
            pip install opencv-python opencv-contrib-python || {
                log_error "OpenCV 설치 실패!"
                log_warning "빌드를 계속 진행하지만 cv2 오류가 발생할 수 있습니다."
            }
        fi
    fi
    echo ""

    # PyInstaller 빌드 실행
    log_info "실행 파일 빌드 중... (5-10분 소요, 기다려주세요)"
    echo ""

    if pyinstaller --clean garame_manager.spec; then
        # 빌드 성공 확인 (--onefile 모드: dist/garame_manager 단일 파일)
        if [ -f "dist/garame_manager" ]; then
            log_success "실행 파일 빌드 완료!"

            # 실행 권한 설정
            chmod +x dist/garame_manager

            # 파일 크기 확인
            FILE_SIZE=$(du -h dist/garame_manager | awk '{print $1}')
            log_info "실행 파일 크기: ${FILE_SIZE}"

            # dist/garame_manager를 현재 디렉토리로 복사
            log_info "빌드 결과를 현재 디렉토리로 복사 중..."

            # 기존 garame_manager 파일이 있으면 삭제
            if [ -f "./garame_manager" ]; then
                log_info "기존 garame_manager 파일 삭제 중..."
                rm -f ./garame_manager
            fi

            # dist/garame_manager를 현재 디렉토리로 복사
            cp dist/garame_manager ./
            chmod +x ./garame_manager

            log_success "실행 파일이 생성되었습니다: ./garame_manager (크기: $FILE_SIZE)"
            echo ""
            log_info "디렉토리 구조:"
            log_info "  ./garame_manager     # 실행 파일"
            log_info "  ./config.conf        # 설정 파일 (수정 가능)"
            log_info "  ./assets/            # 리소스 파일 (수정 가능)"
            echo ""
            log_info "실행 방법:"
            log_info "  • ./garame_manager (직접 실행)"
            log_info "  • ./run.sh (권장 - 자동으로 올바른 실행 파일 사용)"
            echo ""

            # 임시 빌드 파일 정리
            log_info "빌드 임시 파일 정리 중..."
            rm -rf build/ dist/
            log_success "빌드 임시 파일 정리 완료"
            echo ""
        else
            log_error "실행 파일 빌드는 완료되었으나 dist/garame_manager를 찾을 수 없습니다"
            log_info "dist/ 디렉토리 내용:"
            ls -la dist/ 2>/dev/null || echo "  (dist/ 디렉토리 없음)"
            log_warning "Python 소스 모드로 실행하세요: ./run.sh"
        fi
    else
        log_error "실행 파일 빌드 실패"
        log_warning "Python 소스 모드로 실행하세요: ./run.sh"
        log_info "오류 로그를 확인하세요"
    fi
}

################################################################################
# 메인 실행
################################################################################

main() {
    print_banner
    check_root
    check_ubuntu_version

    # 디스크 사용량 로그 초기화
    echo "GARAMe Manager v2.0.1 설치 - 디스크 사용량 추적 로그" > "$DISK_USAGE_LOG"
    echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')" >> "$DISK_USAGE_LOG"
    echo "" >> "$DISK_USAGE_LOG"

    # 초기 상태 기록
    log_disk_usage "0. 설치 시작 - 초기 상태"

    # 0. 디스크 용량 확보
    cleanup_disk_space
    log_disk_usage "0-1. 디스크 정리 완료"

    # 0-2. /tmp 디렉토리 용량 확장 (패키지 빌드용)
    expand_tmp_space
    log_disk_usage "0-2. /tmp 디렉토리 확장 완료"
    echo ""

    # 0-3. NVIDIA GPU 감지 (GPU 가속 설치 여부 결정)
    echo ""
    detect_nvidia_gpu || true  # GPU가 없어도 계속 진행
    echo ""

    log_info "설치를 시작합니다..."
    echo ""

    # 1. 시스템 패키지 설치
    install_system_packages
    log_disk_usage "1. 시스템 패키지 설치 완료"

    # 2. 한글 폰트 설치
    install_korean_fonts
    log_disk_usage "2. 한글 폰트 설치 완료"

    # 3. Python 가상환경 설정
    setup_virtual_env
    log_disk_usage "3. Python 가상환경 설정 완료"

    # 4. Python 패키지 설치 (자동 온라인 모드)
    log_info "Python 패키지 온라인 설치를 시작합니다..."
    install_python_packages_online
    log_disk_usage "4-1. Python 패키지 온라인 설치 완료"

    # 5. AI 모델 확인
    download_ai_models
    log_disk_usage "5. AI 모델 확인 완료"

    # 6. 설정 파일 생성
    create_config_files
    create_data_directories
    log_disk_usage "6. 설정 파일 및 디렉토리 생성 완료"

    # 7. 권한 설정
    set_permissions
    log_disk_usage "7. 권한 설정 완료"

    # 8. 시스템 설정 최적화 (선택)
    optimize_system_settings
    log_disk_usage "8. 시스템 설정 최적화 완료"

    # 9. 자동 시작 설정 (선택)
    setup_autostart
    log_disk_usage "9. 자동 시작 설정 완료"

    # 10. PyInstaller 실행 파일 빌드 (선택)
    build_executable
    log_disk_usage "10. PyInstaller 빌드 완료"

    # 최종 상태 기록
    log_disk_usage "99. 설치 완료 - 최종 상태"

    # /tmp 디렉토리 복원
    restore_tmp_space

    # 완료 메시지
    print_completion_message

    echo ""
    log_success "디스크 사용량 추적 로그가 저장되었습니다: $DISK_USAGE_LOG"
    log_info "설치 중 디스크 사용량 변화를 확인하려면 다음 명령어를 실행하세요:"
    log_info "  cat $DISK_USAGE_LOG"
}

# 스크립트 실행
main "$@"
