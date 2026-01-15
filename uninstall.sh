#!/bin/bash

################################################################################
# GARAMe Manager v1.9.7 - 제거 스크립트
# Ubuntu 25.10 전용
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 배너 출력
print_banner() {
    echo "========================================="
    echo "  GARAMe Manager v1.9.7"
    echo "  제거 스크립트"
    echo "  Ubuntu 25 전용"
    echo "========================================="
    echo ""
}

# 제거 확인
confirm_uninstall() {
    log_warning "GARAMe Manager를 완전히 제거합니다."
    echo ""
    log_info "제거될 항목:"
    echo "  - 프로그램 파일 (실행 파일, Python 소스)"
    echo "  - Python 가상환경 (venv)"
    echo "  - 설정 파일 (config.conf)"
    echo "  - 로그 파일 (logs/)"
    echo "  - 임시 파일"
    echo "  - 자동 시작 설정"
    echo ""
    log_warning "다음 항목은 보존됩니다:"
    echo "  - 데이터 파일 (data/faces, data/backgrounds)"
    echo "  - 안전 포스터 (safety_posters/)"
    echo "  - 사진 데이터 (safety_photos/)"
    echo ""

    read -p "정말로 제거하시겠습니까? (yes/no): " -r response

    if [[ ! "$response" =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "제거가 취소되었습니다."
        exit 0
    fi

    echo ""
    log_info "제거를 시작합니다..."
    echo ""
}

# 실행 중인 프로세스 종료
stop_running_processes() {
    log_info "1. 실행 중인 프로세스 종료 중..."

    # Manager 프로세스 종료
    if pgrep -f "garame_manager" > /dev/null 2>&1; then
        log_info "  - garame_manager 프로세스 종료 중..."
        pkill -f "garame_manager" || true
        sleep 2
        log_success "  - garame_manager 종료 완료"
    fi

    if pgrep -f "python.*main.py" > /dev/null 2>&1; then
        log_info "  - Python main.py 프로세스 종료 중..."
        pkill -f "python.*main.py" || true
        sleep 2
        log_success "  - Python main.py 종료 완료"
    fi

    # Watchdog 프로세스 종료
    if pgrep -f "watchdog.py" > /dev/null 2>&1; then
        log_info "  - Watchdog 프로세스 종료 중..."
        pkill -f "watchdog.py" || true
        sleep 2
        log_success "  - Watchdog 종료 완료"
    fi

    log_success "모든 프로세스 종료 완료"
    echo ""
}

# 자동 시작 설정 제거
remove_autostart() {
    log_info "2. 자동 시작 설정 제거 중..."

    # systemd 서비스 제거
    SERVICE_FILE="$HOME/.config/systemd/user/garame-manager.service"
    if [ -f "$SERVICE_FILE" ]; then
        log_info "  - systemd 서비스 중지 중..."
        systemctl --user stop garame-manager.service 2>/dev/null || true
        systemctl --user disable garame-manager.service 2>/dev/null || true

        log_info "  - systemd 서비스 파일 삭제 중..."
        rm -f "$SERVICE_FILE"

        systemctl --user daemon-reload 2>/dev/null || true
        log_success "  - systemd 서비스 제거 완료"
    fi

    # Desktop autostart 파일 제거
    AUTOSTART_FILE="$HOME/.config/autostart/garame-manager.desktop"
    if [ -f "$AUTOSTART_FILE" ]; then
        log_info "  - Desktop autostart 파일 삭제 중..."
        rm -f "$AUTOSTART_FILE"
        log_success "  - Desktop autostart 제거 완료"
    fi

    log_success "자동 시작 설정 제거 완료"
    echo ""
}

# 프로그램 파일 제거
remove_program_files() {
    log_info "3. 프로그램 파일 제거 중..."

    # 실행 파일
    if [ -f "garame_manager" ]; then
        log_info "  - 실행 파일 삭제 중..."
        rm -f garame_manager
        log_success "  - garame_manager 삭제 완료"
    fi

    # Python 소스
    if [ -f "main.py" ]; then
        log_info "  - main.py 삭제 중..."
        rm -f main.py
    fi

    if [ -d "src" ]; then
        log_info "  - src 디렉토리 삭제 중..."
        rm -rf src
    fi

    # watchdog 파일
    if [ -f "watchdog.py" ]; then
        log_info "  - watchdog.py 삭제 중..."
        rm -f watchdog.py
    fi

    log_success "프로그램 파일 제거 완료"
    echo ""
}

# 가상환경 제거
remove_virtual_env() {
    log_info "4. Python 가상환경 제거 중..."

    if [ -d "venv" ]; then
        log_info "  - venv 디렉토리 삭제 중..."
        rm -rf venv
        log_success "  - 가상환경 제거 완료"
    else
        log_info "  - 가상환경이 없습니다"
    fi

    echo ""
}

# 설정 파일 제거
remove_config_files() {
    log_info "5. 설정 파일 제거 중..."

    # config.conf
    if [ -f "config.conf" ]; then
        log_info "  - config.conf 삭제 중..."
        rm -f config.conf
    fi

    # .spec 파일
    if [ -f "garame_manager.spec" ]; then
        log_info "  - garame_manager.spec 삭제 중..."
        rm -f garame_manager.spec
    fi

    log_success "설정 파일 제거 완료"
    echo ""
}

# 로그 및 임시 파일 제거
remove_logs_and_temp() {
    log_info "6. 로그 및 임시 파일 제거 중..."

    # 로그 디렉토리
    if [ -d "logs" ]; then
        log_info "  - logs 디렉토리 삭제 중..."
        rm -rf logs
    fi

    # 임시 파일
    log_info "  - 임시 파일 삭제 중..."
    rm -f *.log 2>/dev/null || true
    rm -f *.signal 2>/dev/null || true
    rm -f *.pid 2>/dev/null || true

    # Python 캐시
    log_info "  - Python 캐시 삭제 중..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true

    # 빌드 디렉토리
    if [ -d "build" ]; then
        rm -rf build
    fi
    if [ -d "dist" ]; then
        rm -rf dist
    fi

    # 임시 디렉토리
    rm -rf temp 2>/dev/null || true

    log_success "로그 및 임시 파일 제거 완료"
    echo ""
}

# 데이터 파일 제거 여부 확인
remove_data_files_optional() {
    log_info "7. 데이터 파일 처리 중..."

    echo ""
    log_warning "다음 데이터 파일들을 제거할 수 있습니다:"

    if [ -d "data" ]; then
        echo "  - data/ (얼굴 인식 데이터, 배경 이미지)"
        DATA_SIZE=$(du -sh data 2>/dev/null | awk '{print $1}')
        echo "    크기: $DATA_SIZE"
    fi

    if [ -d "safety_posters" ]; then
        echo "  - safety_posters/ (안전 포스터 이미지)"
        POSTER_SIZE=$(du -sh safety_posters 2>/dev/null | awk '{print $1}')
        echo "    크기: $POSTER_SIZE"
    fi

    if [ -d "safety_photos" ]; then
        echo "  - safety_photos/ (사진 데이터)"
        PHOTO_SIZE=$(du -sh safety_photos 2>/dev/null | awk '{print $1}')
        echo "    크기: $PHOTO_SIZE"
    fi

    echo ""
    read -p "데이터 파일도 삭제하시겠습니까? (y/n) [기본값: n]: " -r data_response

    if [[ "$data_response" =~ ^[Yy]$ ]]; then
        log_info "  - 데이터 파일 삭제 중..."

        if [ -d "data" ]; then
            rm -rf data
            log_success "  - data 디렉토리 삭제 완료"
        fi

        if [ -d "safety_posters" ]; then
            rm -rf safety_posters
            log_success "  - safety_posters 디렉토리 삭제 완료"
        fi

        if [ -d "safety_photos" ]; then
            rm -rf safety_photos
            log_success "  - safety_photos 디렉토리 삭제 완료"
        fi
    else
        log_info "  - 데이터 파일을 보존합니다"
    fi

    echo ""
}

# 스크립트 파일 제거
remove_scripts() {
    log_info "8. 스크립트 파일 제거 중..."

    # 실행 스크립트
    rm -f run.sh 2>/dev/null || true
    rm -f install.sh 2>/dev/null || true
    rm -f setup_autostart.sh 2>/dev/null || true

    # requirements.txt
    rm -f requirements.txt 2>/dev/null || true

    # 예제 설정 파일
    rm -f config.conf.example 2>/dev/null || true
    rm -f standard_defaults.conf 2>/dev/null || true

    log_success "스크립트 파일 제거 완료"
    echo ""
}

# 문서 파일 제거
remove_documentation() {
    log_info "9. 문서 파일 제거 중..."

    # README 및 VERSION
    rm -f README.md 2>/dev/null || true
    rm -f VERSION.txt 2>/dev/null || true

    # md 디렉토리
    if [ -d "md" ]; then
        rm -rf md
        log_success "  - md 디렉토리 삭제 완료"
    fi

    # 기타 문서
    rm -f *.md 2>/dev/null || true

    log_success "문서 파일 제거 완료"
    echo ""
}

# assets 디렉토리 제거
remove_assets() {
    log_info "10. assets 디렉토리 제거 중..."

    if [ -d "assets" ]; then
        rm -rf assets
        log_success "  - assets 디렉토리 삭제 완료"
    fi

    echo ""
}

# 완료 메시지
print_completion_message() {
    echo ""
    echo "========================================="
    log_success "GARAMe Manager 제거 완료!"
    echo "========================================="
    echo ""

    # 남은 파일 확인
    REMAINING_FILES=$(ls -A 2>/dev/null | wc -l)

    if [ "$REMAINING_FILES" -gt 0 ]; then
        log_info "현재 디렉토리에 남은 파일:"
        ls -lh
        echo ""
        log_info "디렉토리를 완전히 삭제하려면:"
        log_info "  cd .."
        log_info "  rm -rf $(basename $(pwd))"
    else
        log_success "모든 파일이 제거되었습니다!"
        log_info "상위 디렉토리로 이동하여 디렉토리를 삭제할 수 있습니다:"
        log_info "  cd .."
        log_info "  rmdir $(basename $(pwd))"
    fi

    echo ""
}

################################################################################
# 메인 실행
################################################################################

main() {
    print_banner
    confirm_uninstall

    stop_running_processes
    remove_autostart
    remove_program_files
    remove_virtual_env
    remove_config_files
    remove_logs_and_temp
    remove_data_files_optional
    remove_scripts
    remove_documentation
    remove_assets

    print_completion_message
}

# 스크립트 실행
main "$@"
