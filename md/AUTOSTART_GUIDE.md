# GARAMe MANAGER 자동 시작 설정 가이드

## 개요

GARAMe MANAGER를 Ubuntu 시스템 부팅 시 자동으로 시작하도록 설정하는 방법을 안내합니다.

---

## 자동 시작 방법 비교

| 방법 | 설명 | 장점 | 단점 | 권장 대상 |
|------|------|------|------|-----------|
| **Desktop Autostart** | `~/.config/autostart/` 사용 | 설정 간단, GUI 로그인 후 실행 | 시스템 서비스보다 늦게 시작 | 개인 사용자 |
| **systemd 사용자 서비스** | `~/.config/systemd/user/` 사용 | 사용자 권한으로 실행, 로그 관리 용이 | 사용자 세션 필요 | 개인 사용자, 개발 환경 |
| **systemd 시스템 서비스** | `/etc/systemd/system/` 사용 | 시스템 레벨 관리, 안정적 | root 권한 필요 | 서버, 프로덕션 환경 |

**⚠ 중요: 하나의 방법만 선택하여 사용하세요. 여러 방법을 동시에 사용하면 중복 실행됩니다!**

---

## 방법 1: Desktop Autostart (가장 간단)

### 설정 방법

```bash
cd /path/to/garami_manager/1.9.0
./setup_autostart.sh
# 메뉴에서 "1. 데스크톱 자동 시작 설정" 선택
```

### 생성되는 파일

- `~/.config/autostart/GARAMe_MANAGER.desktop`

### 동작 방식

1. GUI 로그인 후 자동으로 실행
2. `run.sh auto` 스크립트 실행
3. Watchdog + Manager 시작

### 확인 방법

```bash
ls -la ~/.config/autostart/GARAMe_MANAGER.desktop
cat ~/.config/autostart/GARAMe_MANAGER.desktop
```

### 제거 방법

```bash
rm ~/.config/autostart/GARAMe_MANAGER.desktop
```

---

## 방법 2: systemd 사용자 서비스

### 설정 방법

```bash
cd /path/to/garami_manager/1.9.0
./setup_autostart.sh
# 메뉴에서 "2. systemd 사용자 서비스 설정" 선택
```

### 생성되는 파일

- `~/.config/systemd/user/garame-manager.service`

### 서비스 관리 명령어

```bash
# 서비스 시작
systemctl --user start garame-manager

# 서비스 중지
systemctl --user stop garame-manager

# 서비스 재시작
systemctl --user restart garame-manager

# 서비스 상태 확인
systemctl --user status garame-manager

# 서비스 로그 확인
journalctl --user -u garame-manager -f

# 부팅 시 자동 시작 활성화
systemctl --user enable garame-manager

# 부팅 시 자동 시작 비활성화
systemctl --user disable garame-manager
```

### 확인 방법

```bash
systemctl --user is-enabled garame-manager
systemctl --user is-active garame-manager
```

### 제거 방법

```bash
systemctl --user stop garame-manager
systemctl --user disable garame-manager
rm ~/.config/systemd/user/garame-manager.service
systemctl --user daemon-reload
```

---

## 방법 3: systemd 시스템 서비스 (권장)

### 설정 방법

```bash
cd /path/to/garami_manager/1.9.0

# sudo 권한 필요
sudo ./install_systemd_service.sh [사용자명]

# 예시: ubuntu 사용자로 설치
sudo ./install_systemd_service.sh ubuntu

# 현재 사용자로 설치 (SUDO_USER 자동 감지)
sudo ./install_systemd_service.sh
```

### 생성되는 파일

- `/etc/systemd/system/garame-manager@.service` (템플릿 파일)

### 서비스 관리 명령어

```bash
# 서비스 이름: garame-manager@사용자명.service
# 예시: garame-manager@ubuntu.service

# 서비스 시작
sudo systemctl start garame-manager@ubuntu

# 서비스 중지
sudo systemctl stop garame-manager@ubuntu

# 서비스 재시작
sudo systemctl restart garame-manager@ubuntu

# 서비스 상태 확인
sudo systemctl status garame-manager@ubuntu

# 서비스 로그 확인
sudo journalctl -u garame-manager@ubuntu -f

# 부팅 시 자동 시작 활성화
sudo systemctl enable garame-manager@ubuntu

# 부팅 시 자동 시작 비활성화
sudo systemctl disable garame-manager@ubuntu
```

### 확인 방법

```bash
sudo systemctl is-enabled garame-manager@ubuntu
sudo systemctl is-active garame-manager@ubuntu
```

### 제거 방법

```bash
cd /path/to/garami_manager/1.9.0
sudo ./uninstall_systemd_service.sh
```

또는 수동 제거:

```bash
sudo systemctl stop garame-manager@ubuntu
sudo systemctl disable garame-manager@ubuntu
sudo rm /etc/systemd/system/garame-manager@.service
sudo systemctl daemon-reload
```

---

## 자동 시작 상태 확인

### 확인 스크립트 실행

```bash
cd /path/to/garami_manager/1.9.0
./check_autostart.sh
```

이 스크립트는 다음을 확인합니다:

1. Desktop Autostart 설정 여부
2. systemd 사용자 서비스 상태
3. systemd 시스템 서비스 상태
4. 실행 중인 Watchdog 및 Manager 프로세스
5. 중복 설정 경고

### 수동 확인 방법

```bash
# Desktop Autostart
ls -la ~/.config/autostart/GARAMe_MANAGER.desktop

# systemd 사용자 서비스
systemctl --user is-enabled garame-manager

# systemd 시스템 서비스
sudo systemctl is-enabled garame-manager@$(whoami)

# 실행 중인 프로세스
ps aux | grep -E "(watchdog.py|main.py)" | grep -v grep

# PID 파일 확인
cat watchdog.pid 2>/dev/null
```

---

## 문제 해결

### 문제 1: 자동 시작되지 않음

**원인:**
- 서비스가 비활성화되어 있음
- 경로가 잘못됨
- 실행 권한 없음

**해결:**

```bash
# 1. 서비스 활성화 확인
sudo systemctl is-enabled garame-manager@ubuntu

# 2. 경로 확인
cat /etc/systemd/system/garame-manager@.service | grep ExecStart

# 3. 실행 권한 확인
ls -la start_manager_service.sh run.sh

# 4. 실행 권한 부여
chmod +x start_manager_service.sh run.sh
```

### 문제 2: 중복 실행됨

**원인:**
- 여러 자동 시작 방법이 동시에 설정됨

**해결:**

```bash
# 확인 스크립트 실행
./check_autostart.sh

# 중복 설정 제거
./setup_autostart.sh
# 메뉴에서 "3. 모든 자동 시작 설정 제거" 선택

# 그 후 원하는 방법 하나만 다시 설정
```

### 문제 3: 서비스가 실패함

**원인:**
- 가상환경 경로 오류
- Python 버전 문제
- 권한 문제

**해결:**

```bash
# 1. 서비스 로그 확인
sudo journalctl -u garame-manager@ubuntu -n 50 --no-pager

# 2. 가상환경 확인
ls -la ~/venvs/garame/bin/python

# 3. 수동 실행 테스트
cd /path/to/garami_manager/1.9.0
./run.sh

# 4. 서비스 재시작
sudo systemctl restart garame-manager@ubuntu
```

### 문제 4: X 서버 접근 오류

**원인:**
- DISPLAY 환경 변수 설정 오류
- XAUTHORITY 권한 문제

**해결:**

[start_manager_service.sh](start_manager_service.sh#L38-L103)에서 자동으로 처리하지만, 문제 발생 시:

```bash
# 1. DISPLAY 확인
echo $DISPLAY

# 2. XAUTHORITY 확인
echo $XAUTHORITY
ls -la $XAUTHORITY

# 3. xhost 권한 부여
xhost +local:

# 4. 서비스 환경 변수 확인
sudo systemctl show garame-manager@ubuntu -p Environment
```

---

## 권장 설정

### 개인 PC / 개발 환경

**Desktop Autostart 또는 systemd 사용자 서비스 권장**

- 설정 간단
- 사용자 권한으로 실행
- GUI 접근 용이

### 서버 / 프로덕션 환경

**systemd 시스템 서비스 권장**

- 안정적인 관리
- 시스템 레벨 로그
- 재시작 정책 적용
- 다중 사용자 지원

---

## 자동 시작 동작 흐름

### 시스템 부팅 시

1. **부팅 시작**
2. **systemd 초기화**
3. **graphical.target 도달** (GUI 환경 준비)
4. **garame-manager 서비스 시작**
   - [start_manager_service.sh](start_manager_service.sh) 실행
   - 가상환경 활성화
   - 환경 변수 설정 (DISPLAY, XAUTHORITY 등)
   - 이전 신호 파일 정리
   - Watchdog PID 확인 및 시작
   - Manager 실행
5. **Watchdog 백그라운드 실행**
   - 트레이 아이콘으로 숨김 (GUI 있으면)
   - 또는 최소화 (트레이 아이콘 없으면)
6. **Manager 전체화면 실행**
   - 포커스 유지
   - 센서 모니터링 시작

---

## 추가 정보

### 서비스 재시작 정책

[garame-manager.service:27](garame-manager.service#L27):
```
Restart=on-failure
```

- **정상 종료 (exit code 0)**: 재시작하지 않음
- **비정상 종료 (exit code ≠ 0)**: 10초 후 자동 재시작
- **최대 재시작 횟수**: 5분 내 5회

### 로그 확인

```bash
# 실시간 로그
sudo journalctl -u garame-manager@ubuntu -f

# 최근 50줄
sudo journalctl -u garame-manager@ubuntu -n 50

# 특정 날짜
sudo journalctl -u garame-manager@ubuntu --since "2025-11-05"

# 와치독 로그
cat logs/watchdog.log

# 매니저 로그
ls -la logs/
```

---

## 참고 문서

- [SYSTEMD_SERVICE_GUIDE.md](SYSTEMD_SERVICE_GUIDE.md): systemd 서비스 상세 가이드
- [run.sh](run.sh): 실행 스크립트
- [start_manager_service.sh](start_manager_service.sh): systemd 실행 스크립트
- [watchdog.py](watchdog.py): Watchdog 프로그램
- [VERSION_1.9.0_CHANGES.md](VERSION_1.9.0_CHANGES.md): v1.9.0 변경 사항

---

**작성일**: 2025-11-05
**버전**: 1.9.0
