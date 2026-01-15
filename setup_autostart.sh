#!/usr/bin/env bash
# GARAMe MANAGER 자동 시작 설정 도구 (Ubuntu/Linux)
# 
# 사용법:
#   chmod +x setup_autostart.sh
#   ./setup_autostart.sh

set -eu

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 스크립트 위치 기반으로 프로젝트 디렉토리 찾기
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
RUN_SCRIPT="${PROJECT_DIR}/run.sh"

echo "==============================================="
echo "   GARAMe MANAGER 자동 시작 설정 도구 v1.9.8"
echo "==============================================="
echo ""

# 프로젝트 디렉토리 확인
if [ ! -f "${RUN_SCRIPT}" ]; then
    echo -e "${RED}오류: run.sh 파일을 찾을 수 없습니다.${NC}"
    echo "프로젝트 디렉토리: ${PROJECT_DIR}"
    exit 1
fi

# run.sh 실행 권한 확인 및 부여
if [ ! -x "${RUN_SCRIPT}" ]; then
    echo -e "${YELLOW}run.sh에 실행 권한 부여 중...${NC}"
    chmod +x "${RUN_SCRIPT}"
fi

echo "현재 디렉토리: ${PROJECT_DIR}"
echo "실행 스크립트: ${RUN_SCRIPT}"
echo ""

# 메뉴 표시
echo "1. 데스크톱 자동 시작 설정 (~/.config/autostart/)"
echo "2. systemd 사용자 서비스 설정 (~/.config/systemd/user/)"
echo "3. systemd 시스템 서비스 설정 (root 권한 필요)"
echo "4. 모든 자동 시작 설정 제거"
echo "5. systemd 시스템 서비스 제거 (root 권한 필요)"
echo "6. 종료"
echo ""
read -p "선택하세요 [1-6]: " choice

case "$choice" in
    1)
        echo ""
        echo "데스크톱 자동 시작을 설정합니다..."
        
        # ~/.config/autostart 디렉토리 생성
        AUTOSTART_DIR="${HOME}/.config/autostart"
        mkdir -p "${AUTOSTART_DIR}"
        
        # .desktop 파일 생성
        DESKTOP_FILE="${AUTOSTART_DIR}/GARAMe_MANAGER.desktop"

        cat > "${DESKTOP_FILE}" << EOF
[Desktop Entry]
Type=Application
Name=GARAMe MANAGER
Comment=GARAMe MANAGER 자동 실행 (v1.9.7 - Watchdog 모드)
Exec=bash -c 'sleep 5 && cd ${PROJECT_DIR} && ${RUN_SCRIPT} auto'
Path=${PROJECT_DIR}
Terminal=false
Icon=application-x-executable
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
NoDisplay=false
Categories=Utility;Application;System;
EOF

        # 실행 권한 부여
        chmod +x "${RUN_SCRIPT}"
        chmod 644 "${DESKTOP_FILE}"
        
        if [ -f "${DESKTOP_FILE}" ]; then
            echo -e "${GREEN}[성공]${NC} 데스크톱 자동 시작이 설정되었습니다."
            echo "   위치: ${DESKTOP_FILE}"
            echo "   다음 로그인 시 자동으로 실행됩니다."
        else
            echo -e "${RED}[실패]${NC} 데스크톱 파일 생성에 실패했습니다."
        fi
        ;;
        
    2)
        echo ""
        echo "systemd 사용자 서비스를 설정합니다..."
        
        # systemd 사용자 디렉토리 생성
        SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
        mkdir -p "${SYSTEMD_USER_DIR}"
        
        # 서비스 파일 생성
        SERVICE_FILE="${SYSTEMD_USER_DIR}/garame-manager.service"

        cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=GARAMe MANAGER 자동 실행 (v1.9.7 - Watchdog 모드)
After=graphical-session.target network-online.target
Wants=graphical-session.target network-online.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 10
ExecStart=${RUN_SCRIPT} auto
WorkingDirectory=${PROJECT_DIR}
Restart=on-failure
RestartSec=15
Environment="DISPLAY=:0"
Environment="XAUTHORITY=${HOME}/.Xauthority"
Environment="XDG_RUNTIME_DIR=/run/user/%U"
Environment="AUTOSTART=true"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

        # 실행 권한 부여
        chmod +x "${RUN_SCRIPT}"

        # 서비스 활성화
        systemctl --user daemon-reload
        systemctl --user enable garame-manager.service
        
        if systemctl --user is-enabled garame-manager.service > /dev/null 2>&1; then
            echo -e "${GREEN}[성공]${NC} systemd 사용자 서비스가 설정되었습니다."
            echo "   위치: ${SERVICE_FILE}"
            echo "   서비스를 시작하려면: systemctl --user start garame-manager"
            echo "   서비스 상태 확인: systemctl --user status garame-manager"
        else
            echo -e "${RED}[실패]${NC} systemd 서비스 설정에 실패했습니다."
        fi
        ;;
        
    3)
        echo ""
        echo "systemd 시스템 서비스를 설정합니다..."
        echo ""

        # root 권한 확인
        if [ "$EUID" -ne 0 ]; then
            echo -e "${RED}오류: 이 옵션은 root 권한이 필요합니다.${NC}"
            echo "다음 명령으로 실행하세요:"
            echo "  sudo ./install_systemd_service.sh"
            exit 1
        fi

        # install_systemd_service.sh 실행
        if [ -f "${PROJECT_DIR}/install_systemd_service.sh" ]; then
            "${PROJECT_DIR}/install_systemd_service.sh"
        else
            echo -e "${RED}오류: install_systemd_service.sh 파일을 찾을 수 없습니다.${NC}"
            exit 1
        fi
        ;;

    4)
        echo ""
        echo "모든 자동 시작 설정을 제거합니다..."

        # 데스크톱 자동 시작 제거
        DESKTOP_FILE="${HOME}/.config/autostart/GARAMe_MANAGER.desktop"
        if [ -f "${DESKTOP_FILE}" ]; then
            rm -f "${DESKTOP_FILE}"
            echo -e "${GREEN}[완료]${NC} 데스크톱 자동 시작을 제거했습니다."
        fi

        # systemd 사용자 서비스 제거
        SERVICE_FILE="${HOME}/.config/systemd/user/garame-manager.service"
        if [ -f "${SERVICE_FILE}" ]; then
            systemctl --user stop garame-manager.service 2>/dev/null || true
            systemctl --user disable garame-manager.service 2>/dev/null || true
            rm -f "${SERVICE_FILE}"
            systemctl --user daemon-reload
            echo -e "${GREEN}[완료]${NC} systemd 사용자 서비스를 제거했습니다."
        fi

        # systemd 시스템 서비스 제거 안내
        CURRENT_USER=$(whoami)
        if systemctl list-unit-files 2>/dev/null | grep -q "garame-manager@"; then
            echo ""
            echo -e "${YELLOW}[주의]${NC} systemd 시스템 서비스가 발견되었습니다."
            echo "시스템 서비스를 제거하려면 다음을 선택하세요:"
            echo "  메뉴 옵션 5: systemd 시스템 서비스 제거"
            echo "또는 직접 실행:"
            echo "  sudo ./uninstall_systemd_service.sh"
        fi

        echo ""
        echo "사용자 레벨 자동 시작 설정이 모두 제거되었습니다."
        ;;

    5)
        echo ""
        echo "systemd 시스템 서비스를 제거합니다..."
        echo ""

        # root 권한 확인
        if [ "$EUID" -ne 0 ]; then
            echo -e "${RED}오류: 이 옵션은 root 권한이 필요합니다.${NC}"
            echo "다음 명령으로 실행하세요:"
            echo "  sudo ./uninstall_systemd_service.sh"
            exit 1
        fi

        # uninstall_systemd_service.sh 실행
        if [ -f "${PROJECT_DIR}/uninstall_systemd_service.sh" ]; then
            "${PROJECT_DIR}/uninstall_systemd_service.sh"
        else
            echo -e "${RED}오류: uninstall_systemd_service.sh 파일을 찾을 수 없습니다.${NC}"
            exit 1
        fi
        ;;

    6)
        echo "종료합니다."
        exit 0
        ;;

    *)
        echo ""
        echo -e "${YELLOW}잘못된 선택입니다. 1-6 중에서 선택해주세요.${NC}"
        exit 1
        ;;
esac

echo ""
echo "작업이 완료되었습니다."

