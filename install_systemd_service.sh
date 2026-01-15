#!/usr/bin/env bash
# GARAMe MANAGER systemd 서비스 설치 스크립트 v1.9.7
#
# 사용법:
#   sudo ./install_systemd_service.sh [사용자명]
#
# 예시:
#   sudo ./install_systemd_service.sh ubuntu
#   sudo ./install_systemd_service.sh  # 현재 사용자로 설치

set -eu

# 사용자 확인
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: 이 스크립트는 root 권한으로 실행해야 합니다."
    echo "사용법: sudo ./install_systemd_service.sh [사용자명]"
    exit 1
fi

# 사용자명 확인
SERVICE_USER="${1:-}"
if [ -z "$SERVICE_USER" ]; then
    # SUDO_USER가 있으면 사용, 없으면 현재 사용자
    SERVICE_USER="${SUDO_USER:-$(who am i | awk '{print $1}')}"
    if [ -z "$SERVICE_USER" ] || [ "$SERVICE_USER" = "root" ]; then
        echo "ERROR: 사용자명을 지정해야 합니다."
        echo "사용법: sudo ./install_systemd_service.sh [사용자명]"
        echo "예시: sudo ./install_systemd_service.sh ubuntu"
        exit 1
    fi
fi

# 사용자 존재 확인
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "ERROR: 사용자 '$SERVICE_USER'가 존재하지 않습니다."
    exit 1
fi

# 프로젝트 디렉토리 확인 (현재 스크립트 위치 기준)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: 프로젝트 디렉토리를 찾을 수 없습니다: $PROJECT_DIR"
    echo "프로젝트 디렉토리 경로를 확인하세요."
    exit 1
fi

# 가상환경 확인
VENV_DIR="/home/$SERVICE_USER/venvs/garame"
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: 가상환경을 찾을 수 없습니다: $VENV_DIR"
    echo "먼저 run.sh를 실행하여 가상환경을 생성하세요."
    exit 1
fi

# 서비스 파일 경로
SERVICE_FILE="/etc/systemd/system/garame-manager@.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SERVICE_FILE="$SCRIPT_DIR/garame-manager.service"

# 서비스 파일 복사
echo "[1/5] 서비스 파일 설치 중..."
if [ ! -f "$SOURCE_SERVICE_FILE" ]; then
    echo "ERROR: 서비스 파일을 찾을 수 없습니다: $SOURCE_SERVICE_FILE"
    exit 1
fi

cp "$SOURCE_SERVICE_FILE" "$SERVICE_FILE"
chmod 644 "$SERVICE_FILE"
echo "✓ 서비스 파일 설치 완료: $SERVICE_FILE"

# 서비스 파일 사용자명 수정
echo "[2/5] 서비스 파일 사용자 설정 중..."
sed -i "s|%i|$SERVICE_USER|g" "$SERVICE_FILE"
echo "✓ 사용자 '$SERVICE_USER'로 설정 완료"

# 프로젝트 디렉토리 경로 확인 및 수정
CURRENT_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$CURRENT_PROJECT_DIR" != "$PROJECT_DIR" ]; then
    echo "[경고] 현재 디렉토리($CURRENT_PROJECT_DIR)와 설정된 프로젝트 디렉토리($PROJECT_DIR)가 다릅니다."
    read -p "현재 디렉토리를 프로젝트 디렉토리로 사용하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PROJECT_DIR="$CURRENT_PROJECT_DIR"
        sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" "$SERVICE_FILE"
        sed -i "s|ExecStart=.*|ExecStart=/bin/bash $PROJECT_DIR/start_manager_service.sh|" "$SERVICE_FILE"
        echo "✓ 프로젝트 디렉토리 업데이트: $PROJECT_DIR"
    else
        # 기본 경로로 실행 스크립트 경로 수정
        sed -i "s|ExecStart=.*|ExecStart=/bin/bash $PROJECT_DIR/start_manager_service.sh|" "$SERVICE_FILE"
    fi
else
    # 실행 스크립트 경로 설정
    sed -i "s|ExecStart=.*|ExecStart=/bin/bash $PROJECT_DIR/start_manager_service.sh|" "$SERVICE_FILE"
fi

# 실행 스크립트 실행 권한 부여
if [ -f "$PROJECT_DIR/start_manager_service.sh" ]; then
    chmod +x "$PROJECT_DIR/start_manager_service.sh"
    echo "✓ 실행 스크립트 권한 설정 완료"
fi

# systemd 재로드
echo "[3/5] systemd 재로드 중..."
systemctl daemon-reload
echo "✓ systemd 재로드 완료"

# 서비스 활성화
SERVICE_NAME="garame-manager@$SERVICE_USER.service"
echo "[4/5] 서비스 활성화 중..."
systemctl enable "$SERVICE_NAME"
echo "✓ 서비스 활성화 완료: $SERVICE_NAME"

# 서비스 시작
echo "[5/5] 서비스 시작 중..."
systemctl start "$SERVICE_NAME"
echo "✓ 서비스 시작 완료"

# 서비스 상태 확인
echo ""
echo "=== 서비스 상태 ==="
systemctl status "$SERVICE_NAME" --no-pager -l

echo ""
echo "=== 설치 완료 ==="
echo "서비스 이름: $SERVICE_NAME"
echo "사용자: $SERVICE_USER"
echo "프로젝트 디렉토리: $PROJECT_DIR"
echo ""
echo "서비스 관리 명령어:"
echo "  서비스 시작:   sudo systemctl start $SERVICE_NAME"
echo "  서비스 중지:   sudo systemctl stop $SERVICE_NAME"
echo "  서비스 재시작: sudo systemctl restart $SERVICE_NAME"
echo "  서비스 상태:   sudo systemctl status $SERVICE_NAME"
echo "  서비스 로그:   sudo journalctl -u $SERVICE_NAME -f"
echo "  서비스 비활성화: sudo systemctl disable $SERVICE_NAME"
echo ""
