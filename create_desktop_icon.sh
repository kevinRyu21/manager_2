#!/bin/bash

################################################################################
# GARAMe Manager - 데스크탑 아이콘 생성 스크립트
# Ubuntu 22.04/24.04/25.10+ 지원
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

# 스크립트 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$HOME/Desktop"

log_info "데스크탑 아이콘 생성 스크립트"
echo ""

# 데스크탑 디렉토리 확인
if [ ! -d "$DESKTOP_DIR" ]; then
    log_error "데스크탑 디렉토리를 찾을 수 없습니다: $DESKTOP_DIR"
    exit 1
fi

# 아이콘 파일 확인
ICON_PATH=""
if [ -f "$SCRIPT_DIR/assets/GARAMe.png" ]; then
    ICON_PATH="$SCRIPT_DIR/assets/GARAMe.png"
    log_success "아이콘 파일 발견: $ICON_PATH"
elif [ -f "$SCRIPT_DIR/assets/logo.png" ]; then
    ICON_PATH="$SCRIPT_DIR/assets/logo.png"
    log_success "아이콘 파일 발견: $ICON_PATH"
else
    log_warning "아이콘 파일을 찾을 수 없습니다"
    log_info "기본 아이콘을 사용합니다"
fi

# .desktop 파일 생성
DESKTOP_FILE="$DESKTOP_DIR/GARAMe_Manager.desktop"

log_info "데스크탑 바로가기 생성 중..."

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=GARAMe Manager
Comment=GARAMe 통합 모니터링 관리 시스템
Exec=$SCRIPT_DIR/run.sh
Path=$SCRIPT_DIR
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Application;
StartupNotify=true
EOF

# 실행 권한 부여
chmod +x "$DESKTOP_FILE"

log_success "데스크탑 바로가기 생성 완료: $DESKTOP_FILE"

# GNOME 환경에서 신뢰할 수 있는 앱으로 설정
if command -v gio &> /dev/null; then
    log_info "신뢰할 수 있는 앱으로 설정 중..."
    gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
    log_success "신뢰 설정 완료"
fi

# 애플리케이션 메뉴에도 추가
APPLICATIONS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPLICATIONS_DIR"

APP_FILE="$APPLICATIONS_DIR/GARAMe_Manager.desktop"

cp "$DESKTOP_FILE" "$APP_FILE"
chmod +x "$APP_FILE"

log_success "애플리케이션 메뉴에도 추가되었습니다"

echo ""
log_info "완료! 다음 위치에서 GARAMe Manager를 실행할 수 있습니다:"
log_info "  1. 데스크탑 아이콘: $DESKTOP_DIR/GARAMe_Manager.desktop"
log_info "  2. 애플리케이션 메뉴: 유틸리티 > GARAMe Manager"
echo ""
log_info "데스크탑 아이콘을 더블클릭하여 프로그램을 실행하세요"
echo ""
