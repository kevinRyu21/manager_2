#!/usr/bin/env bash
# GARAMe MANAGER systemd 서비스 제거 스크립트 v1.9.7
#
# 사용법:
#   sudo ./uninstall_systemd_service.sh [사용자명]
#
# 예시:
#   sudo ./uninstall_systemd_service.sh ubuntu
#   sudo ./uninstall_systemd_service.sh  # 현재 사용자로 제거

set -eu

# 사용자 확인
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: 이 스크립트는 root 권한으로 실행해야 합니다."
    echo "사용법: sudo ./uninstall_systemd_service.sh [사용자명]"
    exit 1
fi

# 사용자명 확인
SERVICE_USER="${1:-}"
if [ -z "$SERVICE_USER" ]; then
    # SUDO_USER가 있으면 사용, 없으면 현재 사용자
    SERVICE_USER="${SUDO_USER:-$(who am i | awk '{print $1}')}"
    if [ -z "$SERVICE_USER" ] || [ "$SERVICE_USER" = "root" ]; then
        echo "ERROR: 사용자명을 지정해야 합니다."
        echo "사용법: sudo ./uninstall_systemd_service.sh [사용자명]"
        echo "예시: sudo ./uninstall_systemd_service.sh ubuntu"
        exit 1
    fi
fi

# 사용자 존재 확인
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "ERROR: 사용자 '$SERVICE_USER'가 존재하지 않습니다."
    exit 1
fi

SERVICE_NAME="garame-manager@$SERVICE_USER.service"
SERVICE_FILE="/etc/systemd/system/garame-manager@.service"

# 서비스 중지
echo "[1/4] 서비스 중지 중..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl stop "$SERVICE_NAME"
    echo "✓ 서비스 중지 완료"
else
    echo "✓ 서비스가 이미 중지되어 있습니다"
fi

# 서비스 비활성화
echo "[2/4] 서비스 비활성화 중..."
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl disable "$SERVICE_NAME"
    echo "✓ 서비스 비활성화 완료"
else
    echo "✓ 서비스가 이미 비활성화되어 있습니다"
fi

# 서비스 파일 제거
echo "[3/4] 서비스 파일 제거 중..."
if [ -f "$SERVICE_FILE" ]; then
    rm -f "$SERVICE_FILE"
    echo "✓ 서비스 파일 제거 완료: $SERVICE_FILE"
else
    echo "✓ 서비스 파일이 이미 제거되었습니다"
fi

# systemd 재로드
echo "[4/4] systemd 재로드 중..."
systemctl daemon-reload
echo "✓ systemd 재로드 완료"

echo ""
echo "=== 제거 완료 ==="
echo "서비스 '$SERVICE_NAME'가 제거되었습니다."
echo ""
