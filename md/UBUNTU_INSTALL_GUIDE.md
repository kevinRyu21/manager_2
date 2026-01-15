# Ubuntu 설치/실행 가이드

## 지원
- Windows 10/11: 동봉 .bat 사용
- Ubuntu 22.04+/24.04+: `run_ubuntu.sh` 사용

## 빠른 시작

### 첫 실행 (설치 및 실행)
```bash
# 프로젝트 디렉토리로 이동
cd "/path/to/GARAMe MANAGER/1.8.7"

# 실행 권한 부여
chmod +x run_ubuntu.sh

# 실행 (최초 1회: 가상환경/의존성 설치, OCR 모델 없으면 1회만 시도 후 즉시 실행)
./run_ubuntu.sh
```

### 이후 실행
```bash
# 가상환경 활성화 후 직접 실행
source ~/venvs/garame/bin/activate
cd "/path/to/GARAMe MANAGER/1.8.7"
python main.py --config config.conf
```

또는 `run_ubuntu.sh`를 다시 실행해도 됩니다 (이미 설치된 경우 바로 실행됩니다).

## 스크립트가 하는 일 (v1.8.8)

1. **deadsnakes PPA 잔재 제거** + `apt update`
2. **시스템 패키지 설치**: `python3-venv python3-dev python3-tk libgl1 libglib2.0-0t64 espeak-ng libasound2t64 libportaudio2 ffmpeg v4l-utils libv4l-0 build-essential cmake libopenblas-dev liblapack-dev xdotool`
   - `python3-dev`: evdev 등 C 확장 모듈 빌드에 필요 (v1.8.8 추가)
3. **가상환경 생성**: `/home/<USER>/venvs/garame` (없으면 생성)
4. **오프라인 모드 자동 감지**: `wheels/` 디렉토리가 있으면 자동으로 오프라인 모드로 설치
5. **카메라 권한 설정**: `video` 그룹에 사용자 자동 추가
6. **Python 패키지 설치**: 
   - 기본: NumPy 1.26.4, OpenCV 4.9.0.80 (얼굴 인식 호환)
   - 오프라인 모드: `wheels/` 디렉토리에서 설치
7. **얼굴 인식 라이브러리 설치** (선택적, `INSTALL_FACE_RECOGNITION=1` 시):
   - NumPy 1.26.4와 OpenCV 4.9.0.80으로 자동 다운그레이드
   - dlib 및 face-recognition 설치
8. **config.conf 생성** (없을 시 `config.conf.example`에서 복사)
9. **OCR 모델 다운로드** (최초 1회만, 모델이 없을 때만)
10. **프로그램 실행**: `main.py --config config.conf` (CPU 호환성 환경 변수 자동 설정)

## 카메라 설정(웹캠)
- 패키지: `v4l-utils libv4l-0` (스크립트에서 자동 설치)
- 권한: 현재 사용자가 `video` 그룹에 속해야 합니다. 스크립트가 자동으로 추가합니다.
  - 반영을 위해 로그아웃/로그인 후 재실행하세요.
- 장치 확인/테스트:
```bash
v4l2-ctl --list-devices
# 예: /dev/video0 장치 확인
ffplay -f v4l2 -i /dev/video0   # 또는 cheese
```
- 앱에서는 OpenCV(V4L2)로 자동 사용됩니다.

## 수동 설치(선택)

### 방법 1: run_ubuntu.sh 사용 (권장)
```bash
cd "/path/to/GARAMe MANAGER/1.8.7"
chmod +x run_ubuntu.sh
./run_ubuntu.sh
```

### 방법 2: install_requirements.py 사용
```bash
cd "/path/to/GARAMe MANAGER/1.8.7"
python3 install_requirements.py
```

### 방법 3: 완전 수동 설치
```bash
# 시스템 패키지 설치
sudo apt update && sudo apt install -y \
  python3-venv python3-tk libgl1 libglib2.0-0t64 espeak-ng \
  libasound2t64 libportaudio2 ffmpeg v4l-utils libv4l-0 \
  build-essential cmake libopenblas-dev liblapack-dev \
  xdotool

# 가상환경 생성 및 활성화
python3 -m venv ~/venvs/garame
source ~/venvs/garame/bin/activate

# pip 업그레이드
python -m pip install --upgrade pip wheel setuptools

# Python 패키지 설치 (기본)
pip install --no-cache-dir \
  Pillow matplotlib "numpy==2.2.6" pyttsx3 opencv-contrib-python==4.12.0.88 \
  psutil pynput keyboard pystray pandas openpyxl scikit-image imageio \
  requests tqdm pathlib2 configparser easyocr

# 얼굴 인식 설치 시 (선택적)
# NumPy와 OpenCV 다운그레이드 필요:
# pip uninstall -y numpy opencv-contrib-python opencv-python opencv-python-headless
# pip install --no-cache-dir "numpy==1.26.4" "opencv-contrib-python==4.9.0.80"
# pip install --no-cache-dir dlib face-recognition

# 프로젝트 디렉토리로 이동
cd "/path/to/GARAMe MANAGER/1.8.7"

# 설정 파일 생성
[ -f config.conf ] || cp config.conf.example config.conf

# OCR 모델 다운로드 (선택적, 최초 1회)
python download_ocr_models.py || true

# 실행
python main.py --config config.conf
```

## 얼굴 인식 기능 사용 시 주의사항

얼굴 인식 기능을 사용하려면 `INSTALL_FACE_RECOGNITION=1 ./run_ubuntu.sh`로 실행하세요.

**⚠️ 중요**: 얼굴 인식 기능 사용 시 NumPy 2.x는 dlib과 호환되지 않습니다. 스크립트가 자동으로 NumPy 1.26.4와 OpenCV 4.9.0.80으로 다운그레이드합니다.

## 오프라인 설치

인터넷이 없는 환경에서도 실행 가능합니다:

```bash
# 1. 인터넷이 있는 환경에서 wheel 파일 다운로드
./download_wheels.sh

# 2. wheels/ 디렉토리를 오프라인 환경으로 복사

# 3. 오프라인 설치
./install_offline.sh

# 또는 run_ubuntu.sh가 자동으로 오프라인 모드 감지
./run_ubuntu.sh
```

자세한 내용: `INSTALLATION_AND_TROUBLESHOOTING.md` 참조

## 문제 해결

### Illegal instruction 오류
- `main.py`에 CPU 호환성 환경 변수가 자동 설정됨
- 문제가 계속되면: `CPU_COMPATIBILITY_FIX.md` 참조

### evdev 설치 오류
- `python3-dev` 패키지가 자동 설치됨
- 수동 설치: `sudo apt install -y python3-dev`

자세한 문제 해결: `INSTALLATION_AND_TROUBLESHOOTING.md` 참조

자세한 내용은 `FACE_RECOGNITION_INSTALL_GUIDE.md`와 `FACE_RECOGNITION_NUMPY_FIX.md`를 참조하세요.

## 자동 시작 설정

시스템 시작 시 자동으로 GARAMe MANAGER를 실행하려면:

```bash
chmod +x setup_autostart.sh
./setup_autostart.sh
```

### 옵션 설명

1. **데스크톱 자동 시작 (~/.config/autostart/)**
   - GNOME, KDE 등 데스크톱 환경에서 사용자 로그인 시 자동 실행
   - 가장 간단하고 권장하는 방법
   - 위치: `~/.config/autostart/GARAMe_MANAGER.desktop`

2. **systemd 사용자 서비스 (~/.config/systemd/user/)**
   - 시스템 레벨 서비스로 실행
   - 자동 재시작 기능 포함
   - 서버 환경이나 헤드리스 환경에 적합
   - 관리 명령어:
     ```bash
     # 서비스 시작
     systemctl --user start garame-manager
     
     # 서비스 중지
     systemctl --user stop garame-manager
     
     # 서비스 상태 확인
     systemctl --user status garame-manager
     
     # 서비스 로그 확인
     journalctl --user -u garame-manager -f
     ```

3. **모든 자동 시작 설정 제거**
   - 설정한 모든 자동 시작을 제거

### 수동 설정 방법

#### 데스크톱 자동 시작 (수동)
```bash
# 프로젝트 경로를 실제 경로로 변경하세요
PROJECT_DIR="/path/to/GARAMe MANAGER/1.8.7"
RUN_SCRIPT="${PROJECT_DIR}/run_ubuntu.sh"

mkdir -p ~/.config/autostart
cat > ~/.config/autostart/GARAMe_MANAGER.desktop << EOF
[Desktop Entry]
Type=Application
Name=GARAMe MANAGER
Comment=GARAMe MANAGER 자동 실행
Exec=${RUN_SCRIPT} auto
Path=${PROJECT_DIR}
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod +x ~/.config/autostart/GARAMe_MANAGER.desktop
```

#### systemd 서비스 (수동)
```bash
# 프로젝트 경로를 실제 경로로 변경하세요
PROJECT_DIR="/path/to/GARAMe MANAGER/1.8.7"
RUN_SCRIPT="${PROJECT_DIR}/run_ubuntu.sh"

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/garame-manager.service << EOF
[Unit]
Description=GARAMe MANAGER 자동 실행
After=graphical-session.target

[Service]
Type=simple
ExecStart=${RUN_SCRIPT} auto
WorkingDirectory=${PROJECT_DIR}
Restart=on-failure
RestartSec=10
Environment="DISPLAY=:0"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable garame-manager.service
systemctl --user start garame-manager.service
```

## 참고/문제해결
- SSH는 `ssh -X` 또는 로컬 데스크톱에서 실행
- PaddleOCR 설치는 선택 사항(EasyOCR로 기본 구동)
- 최신 Ubuntu는 `libasound2t64` 사용(구 `libasound2` 대체)
- Linux에서 Windows 전용 기능은 자동 무시되도록 처리됨
- 얼굴 인식 기능과 PaddleOCR은 동시 사용 불가 (NumPy 버전 충돌)
- 자동 시작 설정 후 로그아웃/로그인 또는 재부팅하여 확인
