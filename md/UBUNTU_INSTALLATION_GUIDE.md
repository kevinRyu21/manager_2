# Ubuntu 설치 가이드 - GARAMe Manager 최적화

GARAMe Manager를 위한 Ubuntu 25.10 설치 가이드입니다.

## 목차
- [Ubuntu 설치 옵션](#ubuntu-설치-옵션)
- [필수 설정](#필수-설정)
- [권장 설정](#권장-설정)
- [설치 후 확인](#설치-후-확인)

## Ubuntu 설치 옵션

### 1. Ubuntu 버전 선택
- **권장**: Ubuntu 25.10 (Questing Quokka) Desktop
- **대안**: Ubuntu 24.04 LTS, 22.04 LTS

### 2. 설치 유형

#### 일반 설치 (권장)
```
Installation Type: Normal Installation
```

**포함 항목**:
- 웹 브라우저 (Firefox)
- 오피스 소프트웨어 (LibreOffice)
- 유틸리티 프로그램
- 미디어 플레이어
- 게임 (제거 가능)

**장점**:
- GARAMe Manager 개발/관리에 필요한 도구 포함
- 추가 설정 최소화

#### 최소 설치 (선택)
```
Installation Type: Minimal Installation
```

**포함 항목**:
- 웹 브라우저만
- 기본 유틸리티만

**장점**:
- 디스크 공간 절약
- 시스템 리소스 절약

**단점**:
- 추가 패키지 수동 설치 필요

### 3. 기타 옵션

#### ✅ 반드시 선택
```
[✓] Download updates while installing Ubuntu
    (Ubuntu 설치 중 업데이트 다운로드)

[✓] Install third-party software for graphics and Wi-Fi hardware
    (그래픽 및 Wi-Fi 하드웨어용 서드파티 소프트웨어 설치)
```

**이유**:
- 최신 보안 패치 적용
- 그래픽 드라이버 (NVIDIA, AMD 등)
- 무선 네트워크 드라이버
- 멀티미디어 코덱

#### 디스크 파티션
```
Installation type: Erase disk and install Ubuntu (권장)
```

**전문가용** (선택):
```
Something else (수동 파티션)
  - / (root): 50GB 이상
  - /home: 남은 공간
  - swap: RAM 크기와 동일 (8GB 이상이면 선택사항)
```

### 4. 사용자 계정 설정

```
Your name: [사용자 이름]
Your computer's name: [컴퓨터 이름]
Pick a username: [로그인 ID]
Choose a password: [비밀번호]

[✓] Log in automatically (자동 로그인 - 권장)
```

**자동 로그인 권장 이유**:
- GARAMe Manager 자동 시작 설정 시 편리
- 재부팅 후 자동 실행 가능
- 전용 모니터링 시스템에 적합

## 필수 설정

### 1. 시스템 언어 및 입력

#### 한글 입력기 설치
```bash
sudo apt update
sudo apt install -y ibus-hangul
```

#### 입력기 설정
```
Settings → Region & Language → Input Sources
  → + 버튼 클릭 → Korean → Korean (Hangul) → Add
```

### 2. 시스템 업데이트
```bash
sudo apt update
sudo apt upgrade -y
```

### 3. 카메라 권한 설정
```bash
# 현재 사용자를 video 그룹에 추가
sudo usermod -a -G video $USER

# 재로그인 또는 재부팅
sudo reboot
```

## 권장 설정

### 1. 화면 보호기 및 절전 비활성화

GARAMe Manager는 24시간 모니터링 시스템이므로 화면 보호기와 절전 기능을 비활성화해야 합니다.

#### GUI 설정
```
Settings (설정)
  → Power (전원)
    → Screen Blank: Never (화면 끄기: 안 함)
    → Automatic Suspend: Off (자동 절전: 끄기)

  → Privacy (개인정보)
    → Screen Lock (화면 잠금)
      → Automatic Screen Lock: Off (자동 화면 잠금: 끄기)
```

#### 명령줄 설정 (자동)
```bash
# 화면 꺼짐 비활성화
gsettings set org.gnome.desktop.session idle-delay 0

# 화면 잠금 비활성화
gsettings set org.gnome.desktop.screensaver lock-enabled false

# 절전 모드 비활성화
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'

# 화면 밝기 자동 조정 비활성화
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false
```

**참고**: `install.sh` 스크립트가 이 설정을 자동으로 수행합니다.

### 2. 시스템 알림 비활성화

모니터링 화면에 방해가 되는 시스템 알림을 비활성화합니다.

#### GUI 설정
```
Settings (설정)
  → Notifications (알림)
    → Do Not Disturb: On (방해 금지 모드: 켜기)

    각 앱별로 알림 끄기:
    → Software Updater: Off
    → System: Off
```

#### 명령줄 설정 (자동)
```bash
# 알림 표시 비활성화
gsettings set org.gnome.desktop.notifications show-banners false

# 잠금 화면 알림 비활성화
gsettings set org.gnome.desktop.notifications show-in-lock-screen false
```

**참고**: `install.sh` 스크립트가 이 설정을 자동으로 수행합니다.

### 3. 자동 업데이트 비활성화 (선택)

모니터링 중 예기치 않은 재부팅을 방지합니다.

```bash
# 자동 업데이트 비활성화
sudo systemctl disable unattended-upgrades
sudo systemctl stop unattended-upgrades
```

**주의**: 보안 업데이트를 수동으로 정기적으로 실행해야 합니다.

### 4. 방화벽 설정

```bash
# 방화벽 활성화 (권장)
sudo ufw enable

# TCP 포트 5000 허용 (GARAMe Manager 기본 포트)
sudo ufw allow 5000/tcp

# 상태 확인
sudo ufw status
```

### 5. 시간 동기화 설정

```bash
# NTP 시간 동기화 활성화
sudo timedatectl set-ntp true

# 시간대 설정 (한국)
sudo timedatectl set-timezone Asia/Seoul

# 확인
timedatectl
```

## 추가 최적화 설정

### 1. GNOME 확장 비활성화 (성능 향상)

```bash
# 불필요한 GNOME 확장 비활성화
gnome-extensions disable ubuntu-appindicators@ubuntu.com
gnome-extensions disable ubuntu-dock@ubuntu.com
```

### 2. 부팅 시 불필요한 서비스 비활성화

```bash
# Bluetooth 비활성화 (사용하지 않는 경우)
sudo systemctl disable bluetooth

# CUPS (프린터 서비스) 비활성화 (사용하지 않는 경우)
sudo systemctl disable cups
sudo systemctl disable cups-browsed
```

### 3. 스왑 설정 최적화

```bash
# 스왑 사용률 낮추기 (RAM이 충분한 경우)
sudo sysctl vm.swappiness=10

# 영구 적용
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
```

## 설치 후 확인

### 1. 시스템 정보 확인
```bash
# Ubuntu 버전
lsb_release -a

# 커널 버전
uname -r

# 메모리
free -h

# 디스크
df -h
```

### 2. 카메라 확인
```bash
# 카메라 장치 확인
ls -l /dev/video*

# 카메라 테스트 (cheese 사용)
sudo apt install -y cheese
cheese
```

### 3. 필수 패키지 확인
```bash
# Python 버전
python3 --version

# pip 버전
pip3 --version

# Git 버전
git --version

# OpenCV 확인
python3 -c "import cv2; print(cv2.__version__)"
```

## GARAMe Manager 설치

시스템 설정이 완료되면 GARAMe Manager를 설치합니다.

```bash
# 프로젝트 디렉토리로 이동
cd ~/Desktop/프로그램/manager/1.9.1

# 실행 권한 부여
chmod +x install.sh run.sh

# 설치 (시스템 설정 포함)
./install.sh

# 실행
./run.sh
```

## 자동 시작 설정

부팅 시 GARAMe Manager를 자동으로 실행합니다.

```bash
cd ~/Desktop/프로그램/manager/1.9.1
./setup_autostart.sh
```

**옵션 선택**:
1. 사용자 자동 시작 (권장) - 로그인 시 자동 실행
2. systemd 시스템 서비스 - 부팅 시 자동 실행
3. systemd 사용자 서비스 - 로그인 시 자동 실행

## 문제 해결

### 카메라 인식 안 됨
```bash
# 카메라 드라이버 재설치
sudo apt install -y v4l-utils
v4l2-ctl --list-devices

# 권한 확인
sudo usermod -a -G video $USER
sudo reboot
```

### 한글 입력 안 됨
```bash
# ibus-hangul 재설치
sudo apt remove --purge ibus-hangul
sudo apt install -y ibus-hangul
ibus restart

# 입력기 설정
im-config -n ibus
```

### 화면 보호기가 계속 켜짐
```bash
# 수동으로 다시 비활성화
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
```

### 자동 업데이트 알림 계속 뜸
```bash
# 알림 완전 비활성화
sudo systemctl disable update-notifier
sudo apt remove --purge update-notifier
```

## 권장 하드웨어 사양

### 최소 사양
- CPU: 듀얼코어 2.0 GHz
- RAM: 4GB
- 디스크: 50GB
- 카메라: 640x480 이상

### 권장 사양
- CPU: 쿼드코어 2.5 GHz 이상
- RAM: 8GB 이상
- 디스크: 100GB SSD
- 카메라: 1280x720 (HD) 이상
- 그래픽: OpenGL 3.3 지원

### 다중 카메라 모니터링
- CPU: 옥타코어 3.0 GHz 이상
- RAM: 16GB 이상
- 디스크: 256GB SSD
- 카메라: 1920x1080 (Full HD) 이상
- 그래픽: 전용 GPU 권장

## 참고 문서

- [README_INSTALL.md](README_INSTALL.md) - 설치 및 실행 가이드
- [VERSION_1.9.1_CHANGES.md](VERSION_1.9.1_CHANGES.md) - 버전 변경 사항
- [KOREAN_FONT_INSTALL.md](KOREAN_FONT_INSTALL.md) - 한글 폰트 설치
- [BACKGROUND_LEARNING_FEATURE.md](BACKGROUND_LEARNING_FEATURE.md) - 배경 학습 기능

## 라이선스

Copyright © 2025 GARAMe Project
