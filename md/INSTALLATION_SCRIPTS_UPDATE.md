# 설치 및 실행 스크립트 개선 사항

**버전**: v1.9.1
**날짜**: 2025년 11월 6일
**대상**: Ubuntu Linux 전용

---

## 📋 목차

1. [개선 사항 요약](#개선-사항-요약)
2. [install.sh 변경 사항](#installsh-변경-사항)
3. [run.sh 변경 사항](#runsh-변경-사항)
4. [사용 방법](#사용-방법)
5. [문제 해결](#문제-해결)

---

## 🎯 개선 사항 요약

### 해결된 문제들

#### 1. **Root 권한 관련 설치 중단 문제**
- **기존 문제**: 설치 중 root 권한이 필요할 때마다 중단되고 권한 오류 발생
- **해결 방법**: 스크립트 시작 시 한 번만 sudo 암호 입력, 백그라운드에서 세션 유지

#### 2. **Tkinter 모듈 누락 문제**
- **기존 문제**: run.sh 실행 시 tkinter 모듈이 없다는 오류로 프로그램 중단
- **해결 방법**:
  - install.sh에서 python3-tk 자동 설치 및 검증
  - run.sh에서 실행 전 tkinter 확인 및 명확한 오류 메시지 제공

#### 3. **한글 입력 지원 부재**
- **기존 문제**: 우분투에서 한글 입력 불가
- **해결 방법**: iBus 한글 입력기 자동 설치 옵션 추가

#### 4. **SSH 원격 접속 기능 부재**
- **기존 문제**: 원격 접속 설정이 수동으로 필요
- **해결 방법**: OpenSSH 서버 자동 설치 및 설정 옵션 추가

#### 5. **데스크탑 바로가기 부재**
- **기존 문제**: 프로그램 실행 시 매번 터미널에서 스크립트 실행 필요
- **해결 방법**: 데스크탑 아이콘 및 애플리케이션 메뉴 바로가기 자동 생성

---

## 📝 install.sh 변경 사항

### 1. Sudo 권한 관리 시스템 추가

**위치**: 54-75행

```bash
check_sudo_access() {
    log_info "관리자 권한이 필요한 작업이 있습니다."
    log_info "비밀번호를 입력하세요:"

    # sudo 권한 확인 및 캐싱
    sudo -v

    if [ $? -ne 0 ]; then
        log_error "관리자 권한을 얻을 수 없습니다."
        exit 1
    fi

    # 백그라운드에서 sudo 세션 유지 (5분마다 갱신)
    while true; do
        sudo -n true
        sleep 300
        kill -0 "$" 2>/dev/null || exit
    done 2>/dev/null &

    log_success "관리자 권한 확인 완료"
}
```

**특징**:
- 스크립트 시작 시 한 번만 암호 입력
- 백그라운드에서 sudo 세션 자동 갱신 (5분마다)
- 설치 중 권한 요청으로 중단되지 않음

---

### 2. Tkinter 패키지 추가 및 검증

#### 필수 패키지 목록 업데이트 (108행)

```bash
REQUIRED_PACKAGES="python3 python3-pip python3-venv python3-dev python3-tk build-essential cmake pkg-config git wget curl unzip"
```

**추가됨**: `python3-tk`

#### Tkinter 설치 검증 추가 (117-128행)

```bash
# Tkinter 추가 확인 및 설치
log_info "Tkinter 확인 중..."
if ! python3 -c "import tkinter" 2>/dev/null; then
    log_warning "Tkinter가 제대로 설치되지 않았습니다. 추가 설치 시도 중..."
    sudo apt install -y python3-tk tk-dev
fi

if python3 -c "import tkinter" 2>/dev/null; then
    log_success "Tkinter 설치 확인 완료"
else
    log_error "Tkinter 설치 실패 - 프로그램 실행이 불가능할 수 있습니다"
fi
```

**특징**:
- python3-tk 설치 후 실제로 import 가능한지 검증
- 실패 시 추가 설치 시도
- 최종 실패 시 명확한 경고 메시지

---

### 3. 한글 입력기 설정 기능

**위치**: 184-232행

```bash
setup_korean_input() {
    log_info "한글 입력기 설정을 하시겠습니까? (y/n)"
    log_info "(iBus 한글 입력기가 설치되고 활성화됩니다)"
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "한글 입력기 설정을 건너뜁니다"
        return
    fi

    log_info "한글 입력기 설치 중..."

    # iBus 및 한글 입력기 설치
    sudo apt install -y ibus ibus-hangul

    # iBus 설정
    log_info "iBus 설정 중..."

    # iBus를 기본 입력기로 설정
    im-config -n ibus 2>/dev/null || true

    # 환경 변수 설정
    cat >> ~/.bashrc << 'EOF'

# iBus 한글 입력기 설정
export GTK_IM_MODULE=ibus
export QT_IM_MODULE=ibus
export XMODIFIERS=@im=ibus
EOF

    # 현재 세션에도 적용
    export GTK_IM_MODULE=ibus
    export QT_IM_MODULE=ibus
    export XMODIFIERS=@im=ibus

    # iBus 데몬 재시작
    killall ibus-daemon 2>/dev/null || true
    sleep 1
    ibus-daemon -drx &

    log_success "한글 입력기 설치 완료"
    log_info ""
    log_info "한글 입력 사용 방법:"
    log_info "  1. Shift + Space 또는 한/영 키로 한글/영문 전환"
    log_info "  2. 시스템 재시작 후 적용됩니다"
    log_info "  3. 또는 지금 로그아웃 후 다시 로그인하세요"
    log_info ""
}
```

**특징**:
- 선택적 설치 (y/n 확인)
- iBus 한글 입력기 자동 설치
- 환경 변수 자동 설정 (.bashrc에 추가)
- 현재 세션과 향후 세션 모두 지원
- 사용 방법 안내 포함

---

### 4. SSH 서버 설정 기능

**위치**: 234-279행

```bash
setup_ssh_server() {
    log_info "SSH 서버를 설치하고 활성화하시겠습니까? (y/n)"
    log_info "(원격 접속이 가능해집니다)"
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "SSH 서버 설정을 건너뜁니다"
        return
    fi

    log_info "SSH 서버 설치 중..."

    # OpenSSH 서버 설치
    sudo apt install -y openssh-server

    # SSH 서비스 활성화 및 시작
    sudo systemctl enable ssh
    sudo systemctl start ssh

    # 방화벽 설정 (UFW가 활성화된 경우)
    if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
        log_info "방화벽에서 SSH 포트 허용 중..."
        sudo ufw allow ssh
    fi

    # SSH 상태 확인
    if sudo systemctl is-active --quiet ssh; then
        log_success "SSH 서버 활성화 완료"

        # IP 주소 확인
        IP_ADDR=$(hostname -I | awk '{print $1}')

        log_info ""
        log_info "SSH 접속 정보:"
        log_info "  IP 주소: $IP_ADDR"
        log_info "  포트: 22"
        log_info "  사용자: $USER"
        log_info ""
        log_info "원격 접속 명령:"
        log_info "  ssh $USER@$IP_ADDR"
        log_info ""
    else
        log_error "SSH 서버 시작 실패"
    fi
}
```

**특징**:
- 선택적 설치 (y/n 확인)
- OpenSSH 서버 자동 설치
- systemctl로 자동 시작 및 부팅 시 자동 실행 설정
- UFW 방화벽 자동 설정 (활성화된 경우)
- 접속 정보 자동 표시 (IP 주소, 사용자명 등)

---

### 5. Main 함수 업데이트

**위치**: 570-588행

```bash
# sudo 권한 미리 확인 (비밀번호 한 번만 입력)
check_sudo_access

check_ubuntu_version

log_info "설치를 시작합니다..."
echo ""

# 1. 시스템 패키지 설치
install_system_packages

# 2. 한글 폰트 설치
install_korean_fonts

# 3. 한글 입력기 설정 (선택)
setup_korean_input

# 4. SSH 서버 설정 (선택)
setup_ssh_server
```

**변경 사항**:
1. 맨 처음 `check_sudo_access()` 호출로 권한 확보
2. 한글 입력기 설정 추가
3. SSH 서버 설정 추가

---

### 5. 데스크탑 바로가기 생성 기능

**위치**: 538-615행

```bash
create_desktop_shortcut() {
    log_info "데스크탑 바로가기를 생성하시겠습니까? (y/n)"
    log_info "(데스크탑 및 애플리케이션 메뉴에 추가됩니다)"
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "데스크탑 바로가기 생성을 건너뜁니다"
        return
    fi

    log_info "데스크탑 바로가기 생성 중..."

    SCRIPT_DIR="$(pwd)"
    DESKTOP_DIR="$HOME/Desktop"
    APPLICATIONS_DIR="$HOME/.local/share/applications"

    # 데스크탑 디렉토리 확인
    if [ ! -d "$DESKTOP_DIR" ]; then
        log_warning "데스크탑 디렉토리를 찾을 수 없습니다: $DESKTOP_DIR"
        log_info "애플리케이션 메뉴에만 추가합니다"
        DESKTOP_DIR=""
    fi

    # 아이콘 파일 확인
    ICON_PATH=""
    if [ -f "$SCRIPT_DIR/assets/GARAMe.png" ]; then
        ICON_PATH="$SCRIPT_DIR/assets/GARAMe.png"
    elif [ -f "$SCRIPT_DIR/assets/logo.png" ]; then
        ICON_PATH="$SCRIPT_DIR/assets/logo.png"
    else
        log_warning "아이콘 파일을 찾을 수 없습니다 (기본 아이콘 사용)"
    fi

    # .desktop 파일 내용 생성
    DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=GARAMe Manager
Comment=GARAMe 통합 모니터링 관리 시스템 v1.9.1
Exec=$SCRIPT_DIR/run.sh
Path=$SCRIPT_DIR
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Application;
StartupNotify=true"

    # 데스크탑에 바로가기 생성
    if [ -n "$DESKTOP_DIR" ]; then
        DESKTOP_FILE="$DESKTOP_DIR/GARAMe_Manager.desktop"
        echo "$DESKTOP_CONTENT" > "$DESKTOP_FILE"
        chmod +x "$DESKTOP_FILE"

        # GNOME 환경에서 신뢰할 수 있는 앱으로 설정
        if command -v gio &> /dev/null; then
            gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
        fi

        log_success "데스크탑 바로가기 생성 완료"
    fi

    # 애플리케이션 메뉴에 추가
    mkdir -p "$APPLICATIONS_DIR"
    APP_FILE="$APPLICATIONS_DIR/GARAMe_Manager.desktop"
    echo "$DESKTOP_CONTENT" > "$APP_FILE"
    chmod +x "$APP_FILE"

    log_success "애플리케이션 메뉴에 추가 완료"

    echo ""
    log_info "실행 방법:"
    if [ -n "$DESKTOP_DIR" ]; then
        log_info "  • 데스크탑 아이콘 더블클릭"
    fi
    log_info "  • 애플리케이션 메뉴 > 유틸리티 > GARAMe Manager"
    log_info "  • 터미널: ./run.sh"
    echo ""
}
```

**특징**:
- 선택적 설치 (y/n 확인)
- 데스크탑에 바로가기 (.desktop 파일) 생성
- 애플리케이션 메뉴에 자동 등록
- 아이콘 파일 자동 탐지 (assets/GARAMe.png 또는 logo.png)
- GNOME에서 신뢰할 수 있는 앱으로 자동 설정
- 실행 방법 3가지 안내

---

### 6. Main 함수 업데이트

**위치**: 695-702행

```bash
# 10. 시스템 설정 최적화 (선택)
optimize_system_settings

# 11. 자동 시작 설정 (선택)
setup_autostart

# 12. 데스크탑 바로가기 생성 (선택)
create_desktop_shortcut
```

**변경 사항**:
- 데스크탑 바로가기 생성 추가 (설치 마지막 단계)

---

### 7. 설치 완료 메시지 업데이트

**위치**: 617-642행

```bash
print_completion_message() {
    echo ""
    echo "========================================="
    echo -e "${GREEN}  설치 완료!${NC}"
    echo "========================================="
    echo ""
    echo "프로그램 실행 방법:"
    echo -e "  ${BLUE}1. 데스크탑 아이콘 더블클릭${NC} (설치된 경우)"
    echo -e "  ${BLUE}2. 애플리케이션 메뉴 > 유틸리티 > GARAMe Manager${NC} (설치된 경우)"
    echo -e "  ${BLUE}3. 터미널 명령: ./run.sh${NC}"
    # ...
}
```

**변경 사항**:
- 실행 방법을 우선순위별로 정리 (데스크탑 아이콘 우선)
- 데스크탑 아이콘 설치 여부 안내 추가

---

## 🏃 run.sh 변경 사항

### 1. Tkinter 모듈 확인 기능 추가

**위치**: 100-123행

```bash
# Tkinter 확인
check_tkinter() {
    log_info "Tkinter 모듈 확인 중..."

    # 가상환경에서 tkinter 확인
    if ! python3 -c "import tkinter" 2>/dev/null; then
        log_error "Tkinter 모듈을 찾을 수 없습니다!"
        log_error "GARAMe Manager는 GUI 프로그램으로 Tkinter가 필수입니다."
        echo ""
        log_info "해결 방법:"
        log_info "  1. install.sh를 다시 실행하세요:"
        log_info "     ./install.sh"
        log_info ""
        log_info "  2. 또는 수동으로 설치하세요:"
        log_info "     sudo apt update"
        log_info "     sudo apt install -y python3-tk"
        log_info ""
        log_info "  3. 설치 후 이 스크립트를 다시 실행하세요."
        echo ""
        exit 1
    fi

    log_success "Tkinter 모듈 확인 완료"
}
```

**특징**:
- 실행 전 tkinter import 가능 여부 확인
- 실패 시 명확한 오류 메시지와 해결 방법 제시
- 자동 설치 방법과 수동 설치 방법 모두 안내
- 프로그램 크래시 대신 graceful exit

---

### 2. Main 함수 업데이트

**위치**: 335-342행

```bash
# 가상환경 활성화
activate_virtual_env

# Tkinter 확인
check_tkinter

# 환경 설정
setup_environment
```

**변경 사항**:
- 가상환경 활성화 직후 tkinter 확인 추가
- 환경 설정 전에 필수 모듈 검증

---

## 📖 사용 방법

### 1. 처음 설치하기

```bash
# 1. 설치 스크립트 실행
./install.sh

# 2. 관리자 암호 입력 (한 번만)
# [sudo] password for user: ********

# 3. 한글 입력기 설치 여부 선택
# 한글 입력기 설정을 하시겠습니까? (y/n)
y  # 또는 n

# 4. SSH 서버 설치 여부 선택
# SSH 서버를 설치하고 활성화하시겠습니까? (y/n)
y  # 또는 n

# 5. 설치 완료 대기
```

---

### 2. 프로그램 실행하기

```bash
# 일반 실행
./run.sh

# Watchdog 모드 (자동 재시작)
./run.sh -w

# 백그라운드 실행
./run.sh -b

# 디버그 모드
./run.sh -d

# 프로그램 종료
./run.sh -s
```

---

### 3. 한글 입력 사용하기

설치 후:
1. 시스템 재시작 또는 로그아웃 후 재로그인
2. GARAMe Manager 실행
3. **Shift + Space** 또는 **한/영 키**로 전환
4. 텍스트 입력 필드에서 한글 입력 가능

---

### 4. SSH 원격 접속하기

설치 후 표시된 정보 사용:

```bash
# 원격 컴퓨터에서 접속
ssh user@192.168.1.100  # 예시 IP

# 파일 전송 (SCP)
scp file.txt user@192.168.1.100:~/
```

---

### 5. 데스크탑 아이콘 사용하기

설치 후:
1. 데스크탑에서 **GARAMe_Manager.desktop** 아이콘 확인
2. 아이콘 더블클릭하여 프로그램 실행
3. 또는 애플리케이션 메뉴에서 검색
   - 활동(Activities) > "GARAMe" 검색
   - 또는 애플리케이션 > 유틸리티 > GARAMe Manager

---

### 6. 수동으로 데스크탑 아이콘 생성하기

install.sh에서 건너뛴 경우:

```bash
# 독립 실행 스크립트 사용
./create_desktop_icon.sh

# 또는 install.sh 다시 실행 시 선택
./install.sh
# ... (다른 단계는 건너뛰기)
# 데스크탑 바로가기 생성 단계에서 y 선택
```

---

## 🔧 문제 해결

### Tkinter 모듈 오류

**증상**:
```
[ERROR] Tkinter 모듈을 찾을 수 없습니다!
```

**해결 방법 1** (권장):
```bash
./install.sh
```

**해결 방법 2** (수동):
```bash
sudo apt update
sudo apt install -y python3-tk
```

---

### 한글 입력이 안 됨

**증상**: 한글 입력 시 영문으로만 입력됨

**해결 방법**:
1. 로그아웃 후 재로그인
2. 또는 시스템 재시작
3. Shift + Space로 한글 모드 전환 확인

**수동 설정**:
```bash
# iBus 설치
sudo apt install -y ibus ibus-hangul

# iBus 데몬 재시작
killall ibus-daemon
ibus-daemon -drx &

# 시스템 재로그인
```

---

### SSH 접속이 안 됨

**증상**: Connection refused 오류

**해결 방법**:
```bash
# SSH 서비스 상태 확인
sudo systemctl status ssh

# SSH 서비스 시작
sudo systemctl start ssh

# 부팅 시 자동 시작 설정
sudo systemctl enable ssh

# 방화벽 설정 (UFW 사용 시)
sudo ufw allow ssh
```

---

### Root 권한 오류

**증상**: 설치 중 권한 오류로 중단

**해결 방법**:
```bash
# 업데이트된 스크립트 사용
./install.sh

# 처음에 암호 입력 후 자동 진행됨
```

---

### 데스크탑 아이콘이 작동하지 않음

**증상**: 아이콘 더블클릭 시 아무 반응 없음

**해결 방법 1** (신뢰 설정):
```bash
# GNOME에서 신뢰할 수 있는 앱으로 설정
gio set ~/Desktop/GARAMe_Manager.desktop metadata::trusted true
chmod +x ~/Desktop/GARAMe_Manager.desktop
```

**해결 방법 2** (수동 실행 권한):
```bash
# 데스크탑 파일에 실행 권한 부여
chmod +x ~/Desktop/GARAMe_Manager.desktop
chmod +x ~/.local/share/applications/GARAMe_Manager.desktop
```

**해결 방법 3** (재생성):
```bash
# 아이콘 재생성
./create_desktop_icon.sh
```

---

## 📊 설치 스크립트 실행 순서

```
install.sh 시작
     ↓
sudo 권한 확인 (암호 입력 - 1회)
     ↓
Ubuntu 버전 확인
     ↓
시스템 패키지 설치 (python3-tk 포함)
     ↓
Tkinter 검증
     ↓
한글 폰트 설치
     ↓
한글 입력기 설정 (선택)
     ↓
SSH 서버 설정 (선택)
     ↓
Python 가상환경 생성
     ↓
Python 라이브러리 설치
     ↓
설정 파일 생성
     ↓
시스템 설정 최적화 (선택)
     ↓
자동 시작 설정 (선택)
     ↓
데스크탑 바로가기 생성 (선택) ⭐ NEW
     ↓
설치 완료
```

---

## 📊 실행 스크립트 실행 순서

```
run.sh 시작
     ↓
Python 확인
     ↓
가상환경 확인
     ↓
실행 중인 프로세스 확인
     ↓
가상환경 활성화
     ↓
Tkinter 모듈 확인 ⭐ NEW
     ↓
환경 변수 설정
     ↓
로그 정리 (선택)
     ↓
프로그램 실행 (모드별)
```

---

## 🎯 개선 효과

### Before (이전)

❌ 설치 중 권한 오류로 중단
❌ run.sh 실행 시 tkinter 오류로 크래시
❌ 한글 입력 불가
❌ SSH 수동 설정 필요
❌ 터미널에서만 프로그램 실행 가능
❌ 오류 메시지 불명확

### After (개선 후)

✅ 한 번의 암호 입력으로 완전 자동 설치
✅ 실행 전 tkinter 확인 및 명확한 오류 안내
✅ 한글 입력기 자동 설정 (선택)
✅ SSH 서버 원클릭 설치 (선택)
✅ 데스크탑 아이콘 및 앱 메뉴 바로가기 자동 생성 (선택)
✅ 상세한 오류 메시지 및 해결 방법 제시

---

## 📝 변경 사항 체크리스트

### install.sh
- [x] Sudo 권한 관리 시스템 추가
- [x] python3-tk 패키지 추가
- [x] Tkinter 설치 검증 추가
- [x] 한글 입력기 설정 기능 추가
- [x] SSH 서버 설정 기능 추가
- [x] 데스크탑 바로가기 생성 기능 추가
- [x] Main 함수에 새 기능 통합
- [x] 설치 완료 메시지 업데이트

### run.sh
- [x] Tkinter 모듈 확인 함수 추가
- [x] Main 함수에 tkinter 확인 추가
- [x] 명확한 오류 메시지 및 해결 방법 제공

### 독립 스크립트
- [x] create_desktop_icon.sh 생성

---

## 🚀 배포 전 테스트 항목

### install.sh 테스트
- [ ] 우분투 22.04에서 실행
- [ ] 우분투 24.04에서 실행
- [ ] 우분투 25.10에서 실행
- [ ] Sudo 권한 확인 정상 작동
- [ ] python3-tk 설치 확인
- [ ] 한글 입력기 설정 (y 선택)
- [ ] SSH 서버 설정 (y 선택)
- [ ] 데스크탑 바로가기 생성 (y 선택)
- [ ] 설치 완료 후 run.sh 실행

### run.sh 테스트
- [ ] Tkinter 있을 때 정상 실행
- [ ] Tkinter 없을 때 오류 메시지 확인
- [ ] 일반 모드 실행
- [ ] Watchdog 모드 실행
- [ ] 백그라운드 모드 실행
- [ ] 프로그램 종료 기능

### 데스크탑 아이콘 테스트
- [ ] 데스크탑에 아이콘 생성 확인
- [ ] 애플리케이션 메뉴에 등록 확인
- [ ] 아이콘 더블클릭으로 실행
- [ ] 애플리케이션 메뉴에서 실행
- [ ] GNOME 신뢰 설정 확인
- [ ] 아이콘 이미지 표시 확인

### 통합 테스트
- [ ] 한글 입력 정상 작동
- [ ] SSH 원격 접속 정상 작동
- [ ] 자동 시작 설정 정상 작동
- [ ] 로그 파일 생성 확인
- [ ] 모든 실행 방법 테스트 (아이콘/메뉴/터미널)

---

**버전**: v1.9.1
**최종 업데이트**: 2025년 11월 6일
**플랫폼**: Ubuntu Linux 22.04/24.04/25.10+ 지원

Copyright © 2025 GARAMe Project
