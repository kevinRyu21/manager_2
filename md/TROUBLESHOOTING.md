# GARAMe Manager v1.9.2 - 문제 해결 가이드

## 목차
1. [설치 중 오류](#설치-중-오류)
2. [실행 중 오류](#실행-중-오류)
3. [자동 시작 문제](#자동-시작-문제)
4. [디스크 공간 문제](#디스크-공간-문제)

---

## 설치 중 오류

### 1. `ModuleNotFoundError: No module named 'tkinter'`

**증상**:
```
Traceback (most recent call last):
  File "/path/to/main.py", line 7, in <module>
    import tkinter as tk
ModuleNotFoundError: No module named 'tkinter'
```

**원인**:
- Python3 tkinter 패키지가 시스템에 설치되지 않음
- Ubuntu 25.10에서 python3-tk가 기본 설치되지 않음

**해결 방법**:
```bash
# tkinter 시스템 패키지 설치
sudo apt update
sudo apt install -y python3-tk python3-full

# 설치 확인
python3 -c "import tkinter; print('tkinter OK')"
```

**완전 재설치**:
```bash
# 1. 가상환경 삭제
rm -rf venv

# 2. install.sh 다시 실행
./install.sh
```

---

### 2. `error: externally-managed-environment`

**증상**:
```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
```

**원인**:
- Ubuntu 25.10은 시스템 Python을 보호하기 위해 외부 패키지 설치를 제한
- 가상환경을 사용해야 함

**해결 방법**:
```bash
# ❌ 직접 pip 사용하지 마세요
pip install -r requirements.txt  # 실패!

# ✅ 올바른 방법: install.sh 사용
./install.sh

# 또는 수동으로 가상환경 사용
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. 디스크 공간 부족

**증상**:
```
[WARNING] 디스크 여유 공간이 부족합니다 (5GB < 15GB)
[ERROR] dlib 빌드 실패: disk full
```

**해결 방법**:

#### 방법 1: 디스크 사용량 확인
```bash
# 설치 로그 확인
cat disk_usage_install.log

# 주요 디렉토리 확인
df -h
sudo du -sh /* | sort -h
```

#### 방법 2: 디스크 정리
```bash
# APT 캐시 정리
sudo apt clean
sudo apt autoclean
sudo apt autoremove -y

# 임시 파일 정리
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# pip 캐시 정리
rm -rf ~/.cache/pip/*

# 이전 빌드 파일 정리
cd ~/바탕화면/GARAMe_Manager_1.9.2_Ubuntu25_Distribution
rm -rf build/ dist/ venv/
```

#### 방법 3: /tmp 디렉토리 용량 확장 (자동)

**install.sh가 자동으로 수행**:
- 설치 시작 시 /tmp를 자동으로 8GB로 확장
- dlib 빌드 과정에서 필요한 충분한 공간 확보
- 설치 완료 후 기본 크기로 복원 옵션 제공

```bash
# install.sh 실행 시 자동으로 수행됨
./install.sh

# [INFO] /tmp 디렉토리 용량 확인 및 확장 중...
# [SUCCESS] /tmp 디렉토리를 8GB로 확장했습니다
```

**수동 확장 (필요 시)**:
```bash
# tmpfs로 마운트된 경우 (재부팅 시 초기화됨)
sudo mount -o remount,size=8G /tmp

# 영구적으로 확장하려면 /etc/fstab 편집
# tmpfs   /tmp   tmpfs   defaults,size=8G   0 0
```

**확인**:
```bash
# /tmp 크기 확인
df -h | grep /tmp

# 설치 로그에서 /tmp 확장 확인
grep "/tmp 디렉토리 확장" disk_usage_install.log
```

#### 방법 4: 마운트 포인트 확인
```bash
# 마운트 포인트별 사용량 확인
df -h

# /tmp가 별도 마운트라면 크기 확인
mount | grep /tmp
```

자세한 내용은 [DISK_SPACE_GUIDE.md](DISK_SPACE_GUIDE.md) 참조

---

## 실행 중 오류

### 1. 프로그램이 시작되지 않음

**증상**:
```bash
$ ./run.sh
[ERROR] 실행 파일(garame_manager) 또는 main.py를 찾을 수 없습니다.
```

**해결 방법**:
```bash
# 1. 파일 존재 확인
ls -lh garame_manager main.py

# 2. 없으면 설치 다시 실행
./install.sh

# 3. PyInstaller 빌드 선택
# 설치 중 "실행 파일을 빌드하시겠습니까? (y/n)" → y 선택
```

---

### 2. 가상환경 활성화 실패

**증상**:
```bash
$ ./run.sh
[ERROR] 가상환경이 설치되지 않았습니다.
```

**해결 방법**:
```bash
# 1. install.sh 실행
./install.sh

# 2. 수동으로 가상환경 생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. 카메라 접근 권한 오류

**증상**:
```
[ERROR] 카메라를 열 수 없습니다: /dev/video0
[WARNING] Permission denied
```

**해결 방법**:
```bash
# 1. 사용자를 video 그룹에 추가
sudo usermod -aG video $USER

# 2. 로그아웃 후 다시 로그인
# 또는 재부팅

# 3. 권한 확인
groups | grep video
ls -l /dev/video*
```

---

## 자동 시작 문제

### 1. watchdog.py가 배포판에 없음

**증상**:
```bash
$ ./run.sh
[WARNING] watchdog.py 파일을 찾을 수 없습니다.
[INFO] 일반 모드로 실행합니다...
```

**원인**:
- 이전 배포판에는 watchdog.py가 포함되지 않았음
- v1.9.2 이후 버전에는 포함됨

**해결 방법**:
```bash
# 1. 최신 배포판 다운로드
# GARAMe_Manager_1.9.2_Ubuntu25_Distribution.tar.gz

# 2. 압축 해제 후 파일 확인
tar -xzf GARAMe_Manager_1.9.2_Ubuntu25_Distribution.tar.gz
cd GARAMe_Manager_1.9.2_Ubuntu25_Distribution
ls -lh watchdog.py

# 3. 설치
./install.sh

# 4. Watchdog 모드로 실행
./run.sh -w
```

---

### 2. 자동 시작이 작동하지 않음

**증상**:
- 컴퓨터 재부팅 후 프로그램이 자동으로 시작되지 않음

**해결 방법**:

#### systemd 서비스 확인
```bash
# 서비스 상태 확인
systemctl --user status garame-manager.service

# 서비스 로그 확인
journalctl --user -u garame-manager.service -n 50

# 서비스 재시작
systemctl --user restart garame-manager.service
```

#### 자동 시작 재설정
```bash
# 1. setup_autostart.sh 실행
./setup_autostart.sh

# 2. systemd 활성화 선택
# "systemd를 사용하여 자동 시작 설정하시겠습니까? (y/n)" → y

# 3. 서비스 활성화 확인
systemctl --user is-enabled garame-manager.service
```

#### Desktop Autostart 확인
```bash
# autostart 파일 확인
cat ~/.config/autostart/garame-manager.desktop

# 파일이 없으면 재생성
./setup_autostart.sh
```

---

### 3. Watchdog가 Manager를 재시작하지 않음

**증상**:
- Manager 프로그램이 종료되어도 자동으로 재시작되지 않음

**해결 방법**:

#### Watchdog 로그 확인
```bash
# 로그 파일 확인
cat logs/watchdog.log

# 실시간 로그 확인
tail -f logs/watchdog.log
```

#### Watchdog 설정 확인
```bash
# config.conf에서 WATCHDOG 설정 확인
cat config.conf | grep -A 10 "\[WATCHDOG\]"

# 최대 재시작 횟수 확인
# max_restart_count = 10  (기본값)
# restart_delay = 5       (기본값)
```

#### Watchdog 재시작
```bash
# Watchdog 종료
pkill -f watchdog.py

# Watchdog 다시 시작
./run.sh -w
```

---

## 디스크 공간 문제

### 디스크 사용량 추적 로그 확인

**설치 중 디스크 사용량**:
```bash
# 설치 시 생성된 로그 확인
cat disk_usage_install.log

# 특정 단계별 사용량 확인
grep "시스템 패키지 설치 완료" -A 20 disk_usage_install.log
grep "Python 패키지 온라인 설치 완료" -A 20 disk_usage_install.log
```

**로그 구조**:
```
[2025-11-11 10:30:00] 0. 설치 시작 - 초기 상태
=========================================
=== 마운트 포인트별 디스크 사용량 ===
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   45G   50G  48% /
/dev/sda2        20G   15G    4G  79% /tmp
tmpfs           8.0G  1.2G  6.8G  15% /dev/shm

[ / 루트 디렉토리 하위 ]
12G     /usr
8.5G    /var
5.2G    /home
...
```

**주요 확인 사항**:
1. 각 마운트 포인트의 사용률
2. /tmp 디렉토리 크기 (dlib 빌드 시 사용)
3. ~/.cache/pip 캐시 크기
4. venv 가상환경 크기

자세한 내용은 [DISK_SPACE_GUIDE.md](DISK_SPACE_GUIDE.md) 참조

---

## 추가 지원

### 로그 파일 위치
```
logs/
├── manager_YYYYMMDD_HHMMSS.log  # Manager 실행 로그
├── watchdog.log                  # Watchdog 로그
└── install.log                   # 설치 로그 (있는 경우)

disk_usage_install.log            # 디스크 사용량 추적 로그
```

### 환경 정보 수집
```bash
# 시스템 정보
uname -a
lsb_release -a

# Python 버전
python3 --version

# 설치된 패키지
dpkg -l | grep python3

# 디스크 사용량
df -h
du -sh venv/
```

### 제거 및 재설치
```bash
# 완전 제거
./uninstall.sh

# 재설치
./install.sh
```

---

**문서 버전**: v1.9.2
**최종 수정**: 2025-11-11
