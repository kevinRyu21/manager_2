# GARAMe MANAGER systemd 서비스 설치 가이드

Ubuntu에서 GARAMe MANAGER와 Watchdog를 systemd 서비스로 자동 시작하는 방법입니다.

## 사전 준비

1. **프로젝트 설치 완료**
   - `run.sh`를 실행하여 프로젝트와 가상환경이 설치되어 있어야 합니다.
   - 가상환경 경로: `~/venvs/garame`

2. **프로젝트 디렉토리 확인**
   - 기본 경로: `/home/[사용자명]/Desktop/프로그램/manager/1.8.9`
   - 다른 경로에 설치한 경우 설치 스크립트에서 경로를 수정할 수 있습니다.

## 설치 방법

### 1. 자동 설치 (권장)

```bash
# 사용자명 지정 (예: ubuntu)
sudo ./install_systemd_service.sh ubuntu

# 또는 현재 사용자로 설치
sudo ./install_systemd_service.sh
```

설치 스크립트는 다음 작업을 수행합니다:
- systemd 서비스 파일 복사 (`/etc/systemd/system/garame-manager@.service`)
- 사용자명 및 경로 설정
- 서비스 활성화 및 시작

### 2. 수동 설치

#### 2.1 서비스 파일 복사

```bash
sudo cp garame-manager.service /etc/systemd/system/garame-manager@.service
```

#### 2.2 서비스 파일 수정

`/etc/systemd/system/garame-manager@.service` 파일을 열어 다음 항목을 수정:

```ini
# 사용자명 변경 (예: ubuntu)
User=ubuntu
Group=ubuntu

# 프로젝트 디렉토리 경로 변경
WorkingDirectory=/home/ubuntu/Desktop/프로그램/manager/1.8.9

# 가상환경 경로 변경
Environment="PATH=/home/ubuntu/venvs/garame/bin:..."
ExecStart=/bin/bash /home/ubuntu/Desktop/프로그램/manager/1.8.9/start_manager_service.sh
```

#### 2.3 systemd 재로드 및 서비스 활성화

```bash
sudo systemctl daemon-reload
sudo systemctl enable garame-manager@ubuntu.service
sudo systemctl start garame-manager@ubuntu.service
```

## 서비스 관리

### 서비스 상태 확인

```bash
sudo systemctl status garame-manager@ubuntu.service
```

### 서비스 시작/중지/재시작

```bash
# 시작
sudo systemctl start garame-manager@ubuntu.service

# 중지
sudo systemctl stop garame-manager@ubuntu.service

# 재시작
sudo systemctl restart garame-manager@ubuntu.service
```

### 서비스 로그 확인

```bash
# 실시간 로그
sudo journalctl -u garame-manager@ubuntu.service -f

# 최근 로그 (100줄)
sudo journalctl -u garame-manager@ubuntu.service -n 100

# 오늘 로그
sudo journalctl -u garame-manager@ubuntu.service --since today
```

### 서비스 비활성화 (부팅 시 자동 시작 안 함)

```bash
sudo systemctl disable garame-manager@ubuntu.service
```

## 제거 방법

### 자동 제거

```bash
sudo ./uninstall_systemd_service.sh ubuntu
```

### 수동 제거

```bash
# 서비스 중지 및 비활성화
sudo systemctl stop garame-manager@ubuntu.service
sudo systemctl disable garame-manager@ubuntu.service

# 서비스 파일 제거
sudo rm /etc/systemd/system/garame-manager@.service

# systemd 재로드
sudo systemctl daemon-reload
```

## 문제 해결

### 1. 서비스가 시작되지 않음

```bash
# 서비스 상태 확인
sudo systemctl status garame-manager@ubuntu.service

# 상세 로그 확인
sudo journalctl -u garame-manager@ubuntu.service -n 50
```

**일반적인 원인:**
- 프로젝트 디렉토리 경로 오류
- 가상환경 경로 오류
- Python 패키지 미설치
- DISPLAY 환경 변수 오류

### 2. GUI가 표시되지 않음

GUI 애플리케이션이므로 X11 디스플레이 접근이 필요합니다.

**확인 사항:**
- `DISPLAY=:0` 환경 변수가 설정되어 있는지 확인
- 사용자가 X 세션에 로그인되어 있는지 확인
- `XAUTHORITY` 경로가 올바른지 확인

**해결 방법:**
```bash
# X11 포워딩 활성화 (필요한 경우)
xhost +local:
```

### 3. 권한 오류

```bash
# 서비스 파일 권한 확인
ls -l /etc/systemd/system/garame-manager@.service

# 실행 스크립트 권한 확인
ls -l /home/ubuntu/Desktop/프로그램/manager/1.8.9/start_manager_service.sh
chmod +x /home/ubuntu/Desktop/프로그램/manager/1.8.9/start_manager_service.sh
```

### 4. Watchdog가 중복 실행됨

`start_manager_service.sh` 스크립트가 자동으로 중복 실행을 방지합니다.
수동으로 실행 중인 Watchdog를 종료하려면:

```bash
pkill -f "python.*watchdog.py"
```

## 서비스 설정 상세

### 서비스 파일 구조

```ini
[Unit]
Description=GARAMe MANAGER - Sensor Monitoring System with Watchdog
After=network.target display-manager.service
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Desktop/프로그램/manager/1.8.9
ExecStart=/bin/bash /home/ubuntu/Desktop/프로그램/manager/1.8.9/start_manager_service.sh
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
```

### 주요 설정 설명

- **After=network.target**: 네트워크가 준비된 후 시작
- **After=display-manager.service**: 디스플레이 매니저가 시작된 후 시작
- **Restart=always**: 항상 자동 재시작
- **RestartSec=10**: 재시작 전 10초 대기
- **WantedBy=graphical.target**: 그래픽 세션이 시작될 때 자동 시작

## 보안 고려사항

- 서비스는 **사용자 계정**으로 실행됩니다 (root가 아님)
- `ProtectSystem=strict`: 시스템 파일 보호
- `ProtectHome=read-only`: 홈 디렉토리 읽기 전용
- `ReadWritePaths`: 프로젝트 디렉토리만 쓰기 가능

## 참고

- 서비스 로그는 `journalctl`로 확인할 수 있습니다.
- 시스템 재부팅 시 자동으로 서비스가 시작됩니다.
- 서비스를 수동으로 중지해도 재부팅 시 다시 시작됩니다 (비활성화하지 않는 한).


