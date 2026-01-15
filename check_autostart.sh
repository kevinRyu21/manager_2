#!/usr/bin/env bash
# GARAMe MANAGER 자동 시작 상태 확인 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  GARAMe MANAGER 자동 시작 상태 확인"
echo "=========================================="
echo ""

# 현재 사용자
CURRENT_USER=$(whoami)
echo "현재 사용자: $CURRENT_USER"
echo ""

# 1. Desktop Autostart 확인
echo "=== 1. Desktop Autostart 설정 확인 ==="
DESKTOP_FILE="${HOME}/.config/autostart/GARAMe_MANAGER.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    echo -e "${GREEN}✓ Desktop Autostart 설정됨${NC}"
    echo "  파일 위치: $DESKTOP_FILE"
    echo "  파일 내용:"
    cat "$DESKTOP_FILE" | sed 's/^/    /'
else
    echo -e "${YELLOW}✗ Desktop Autostart 설정 안 됨${NC}"
fi
echo ""

# 2. systemd 사용자 서비스 확인
echo "=== 2. systemd 사용자 서비스 확인 ==="
USER_SERVICE_FILE="${HOME}/.config/systemd/user/garame-manager.service"
if [ -f "$USER_SERVICE_FILE" ]; then
    echo -e "${GREEN}✓ systemd 사용자 서비스 파일 존재${NC}"
    echo "  파일 위치: $USER_SERVICE_FILE"

    # 서비스 활성화 상태 확인
    if systemctl --user is-enabled garame-manager.service &>/dev/null; then
        echo -e "${GREEN}✓ 서비스 활성화됨 (부팅 시 자동 시작)${NC}"
    else
        echo -e "${YELLOW}✗ 서비스 비활성화됨 (부팅 시 자동 시작 안 됨)${NC}"
    fi

    # 서비스 실행 상태 확인
    if systemctl --user is-active garame-manager.service &>/dev/null; then
        echo -e "${GREEN}✓ 서비스 실행 중${NC}"
    else
        echo -e "${YELLOW}✗ 서비스 중지됨${NC}"
    fi
else
    echo -e "${YELLOW}✗ systemd 사용자 서비스 설정 안 됨${NC}"
fi
echo ""

# 3. systemd 시스템 서비스 확인 (root)
echo "=== 3. systemd 시스템 서비스 확인 ==="
SYSTEM_SERVICE_NAME="garame-manager@${CURRENT_USER}.service"
if systemctl list-unit-files | grep -q "$SYSTEM_SERVICE_NAME"; then
    echo -e "${GREEN}✓ systemd 시스템 서비스 등록됨${NC}"
    echo "  서비스 이름: $SYSTEM_SERVICE_NAME"

    # 서비스 활성화 상태 확인
    if sudo systemctl is-enabled "$SYSTEM_SERVICE_NAME" &>/dev/null; then
        echo -e "${GREEN}✓ 서비스 활성화됨 (부팅 시 자동 시작)${NC}"
    else
        echo -e "${YELLOW}✗ 서비스 비활성화됨 (부팅 시 자동 시작 안 됨)${NC}"
    fi

    # 서비스 실행 상태 확인
    if sudo systemctl is-active "$SYSTEM_SERVICE_NAME" &>/dev/null; then
        echo -e "${GREEN}✓ 서비스 실행 중${NC}"
        echo ""
        echo "  서비스 상태:"
        sudo systemctl status "$SYSTEM_SERVICE_NAME" --no-pager -l | sed 's/^/    /'
    else
        echo -e "${YELLOW}✗ 서비스 중지됨${NC}"
    fi
else
    echo -e "${YELLOW}✗ systemd 시스템 서비스 설정 안 됨${NC}"
fi
echo ""

# 4. 실행 중인 프로세스 확인
echo "=== 4. 실행 중인 프로세스 확인 ==="

# Watchdog 확인
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG_PID_FILE="${PROJECT_DIR}/watchdog.pid"

if [ -f "$WATCHDOG_PID_FILE" ]; then
    WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")
    if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ Watchdog 실행 중 (PID: $WATCHDOG_PID)${NC}"
    else
        echo -e "${RED}✗ Watchdog PID 파일 있지만 프로세스 없음 (PID: $WATCHDOG_PID)${NC}"
    fi
else
    # ps로 확인
    if ps aux | grep -v grep | grep -q "python.*watchdog.py"; then
        WATCHDOG_PID=$(pgrep -f "python.*watchdog.py" | head -n 1)
        echo -e "${YELLOW}⚠ Watchdog 실행 중이지만 PID 파일 없음 (PID: $WATCHDOG_PID)${NC}"
    else
        echo -e "${RED}✗ Watchdog 실행 안 됨${NC}"
    fi
fi

# Manager 확인
if ps aux | grep -v grep | grep -q "python.*main.py"; then
    MANAGER_PID=$(pgrep -f "python.*main.py" | head -n 1)
    echo -e "${GREEN}✓ Manager 실행 중 (PID: $MANAGER_PID)${NC}"
else
    echo -e "${RED}✗ Manager 실행 안 됨${NC}"
fi
echo ""

# 5. 권장 사항
echo "=== 5. 권장 사항 ==="
echo ""

# 설정된 자동 시작 방법 개수 확인
AUTOSTART_COUNT=0
if [ -f "$DESKTOP_FILE" ]; then
    AUTOSTART_COUNT=$((AUTOSTART_COUNT + 1))
fi
if [ -f "$USER_SERVICE_FILE" ] && systemctl --user is-enabled garame-manager.service &>/dev/null; then
    AUTOSTART_COUNT=$((AUTOSTART_COUNT + 1))
fi
if systemctl list-unit-files | grep -q "$SYSTEM_SERVICE_NAME" && sudo systemctl is-enabled "$SYSTEM_SERVICE_NAME" &>/dev/null; then
    AUTOSTART_COUNT=$((AUTOSTART_COUNT + 1))
fi

if [ $AUTOSTART_COUNT -eq 0 ]; then
    echo -e "${YELLOW}⚠ 자동 시작이 설정되지 않았습니다.${NC}"
    echo ""
    echo "자동 시작을 설정하려면:"
    echo "  1. Desktop Autostart: ./setup_autostart.sh"
    echo "  2. systemd 시스템 서비스: sudo ./install_systemd_service.sh"
elif [ $AUTOSTART_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ 자동 시작이 올바르게 설정되었습니다.${NC}"
    echo ""
    echo "컴퓨터 부팅 시 GARAMe MANAGER가 자동으로 시작됩니다."
else
    echo -e "${RED}⚠ 경고: 여러 자동 시작 방법이 동시에 설정되어 있습니다!${NC}"
    echo ""
    echo "중복 실행을 방지하기 위해 하나만 남기고 나머지를 제거하세요:"
    echo ""
    if [ -f "$DESKTOP_FILE" ]; then
        echo "  - Desktop Autostart 제거: rm -f $DESKTOP_FILE"
    fi
    if [ -f "$USER_SERVICE_FILE" ] && systemctl --user is-enabled garame-manager.service &>/dev/null; then
        echo "  - systemd 사용자 서비스 제거:"
        echo "      systemctl --user stop garame-manager.service"
        echo "      systemctl --user disable garame-manager.service"
        echo "      rm -f $USER_SERVICE_FILE"
    fi
    if systemctl list-unit-files | grep -q "$SYSTEM_SERVICE_NAME" && sudo systemctl is-enabled "$SYSTEM_SERVICE_NAME" &>/dev/null; then
        echo "  - systemd 시스템 서비스 제거:"
        echo "      sudo systemctl stop $SYSTEM_SERVICE_NAME"
        echo "      sudo systemctl disable $SYSTEM_SERVICE_NAME"
        echo "      sudo rm -f /etc/systemd/system/garame-manager@.service"
    fi
    echo ""
    echo "또는 setup_autostart.sh의 '3. 모든 자동 시작 설정 제거'를 사용하세요."
fi
echo ""

echo "=========================================="
echo "확인 완료"
echo "=========================================="
