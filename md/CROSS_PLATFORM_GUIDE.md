# GARAMe MANAGER 1.8.6 크로스 플랫폼 설치 가이드

이 문서는 Windows와 Ubuntu/Linux에서 GARAMe MANAGER를 설치하고 실행하는 방법을 설명합니다.

## 지원 플랫폼

- **Windows**: Windows 10, Windows 11
- **Linux**: Ubuntu 20.04 이상, Debian 기반 배포판

## 필수 요구사항

### 공통 요구사항
- Python 3.8 이상 (권장: Python 3.11)
- 인터넷 연결 (최초 설치 시)
- 최소 4GB RAM
- 약 2GB 디스크 공간

### Windows 추가 요구사항
- Visual C++ Build Tools (dlib 설치 시 필요, 선택적)
  - 다운로드: https://visualstudio.microsoft.com/downloads/

### Ubuntu/Debian 추가 요구사항
- build-essential
- cmake
- libopenblas-dev
- liblapack-dev
- xdotool (한글 입력 조합 지원, 선택적)

## 설치 방법

### 방법 1: 자동 설치 (권장)

#### Windows
```powershell
# 1. Python 가상환경 생성 (선택적, 권장)
python -m venv .venv
.venv\Scripts\activate

# 2. 자동 설치 스크립트 실행
python install_requirements.py
```

#### Ubuntu/Debian
```bash
# 방법 1: run_ubuntu.sh 사용 (가장 권장)
cd "/path/to/GARAMe MANAGER/1.8.7"
chmod +x run_ubuntu.sh
./run_ubuntu.sh

# 방법 2: install_requirements.py 사용
# 1. 시스템 패키지 설치 (필수)
sudo apt-get update
sudo apt-get install -y build-essential cmake
sudo apt-get install -y libopenblas-dev liblapack-dev
sudo apt-get install -y xdotool  # 한글 입력 조합 지원 (선택적)

# 2. Python 가상환경 생성 (선택적, 권장)
python3 -m venv .venv
source .venv/bin/activate

# 3. 자동 설치 스크립트 실행
python3 install_requirements.py
```

### 방법 2: 수동 설치

#### 1. 기본 패키지 설치
```bash
# Windows
pip install -r requirements.txt

# Ubuntu/Debian
pip3 install -r requirements.txt
```

#### 2. OCR 모델 다운로드
```bash
# Windows
python download_ocr_models.py

# Ubuntu/Debian
python3 download_ocr_models.py
```

#### 3. 얼굴 인식 라이브러리 설치 (선택적)

**Windows:**
```powershell
pip install cmake
pip install dlib
pip install face-recognition
```

**Ubuntu/Debian:**

**⚠️ 중요**: 얼굴 인식 기능 사용 시 NumPy 2.x는 dlib과 호환되지 않습니다. NumPy 1.26.4를 사용해야 합니다.

**방법 1: run_ubuntu.sh 사용 (가장 권장)**
```bash
INSTALL_FACE_RECOGNITION=1 ./run_ubuntu.sh
```
스크립트가 자동으로 NumPy 1.26.4와 OpenCV 4.9.0.80으로 다운그레이드하고 dlib을 설치합니다.

**방법 2: install_requirements.py 사용**
```bash
python3 install_requirements.py
# 얼굴 인식 설치 질문에 'y' 입력
```

**방법 3: 수동 설치**
```bash
# 1. 시스템 패키지 설치
sudo apt-get install build-essential cmake
sudo apt-get install libopenblas-dev liblapack-dev
sudo apt-get install xdotool  # 한글 입력 조합 지원 (선택적)

# 2. NumPy와 OpenCV 다운그레이드 (필수)
pip3 uninstall -y numpy opencv-contrib-python opencv-python opencv-python-headless
pip3 install numpy==1.26.4
pip3 install opencv-contrib-python==4.9.0.80

# 3. 얼굴 인식 라이브러리 설치
pip3 install cmake
pip3 install dlib  # 컴파일 시간이 매우 오래 걸릴 수 있음 (30분~1시간)
pip3 install face-recognition
```

## 실행 방법

### Windows
```powershell
# 가상환경 활성화 (사용한 경우)
.venv\Scripts\activate

# 프로그램 실행
python main.py
```

### Ubuntu/Debian
```bash
# 가상환경 활성화 (사용한 경우)
source .venv/bin/activate

# 프로그램 실행
python3 main.py

# 또는 실행 권한 부여 후
chmod +x run_ubuntu.sh
./run_ubuntu.sh
```

## 플랫폼별 차이점

### 카메라 백엔드
- **Windows**: DirectShow (CAP_DSHOW) 우선 사용, 실패 시 MSMF
- **Ubuntu/Linux**: V4L2 (CAP_V4L2) 우선 사용

### 파일 경로
- 모든 경로는 `os.path.join()` 사용으로 자동 처리
- 슬래시/백슬래시 차이는 자동 변환

### 얼굴 인식 데이터베이스
- Windows/Linux 모두 동일한 SQLite 데이터베이스 사용
- 기본 위치: `프로젝트루트/face_db/faces.db`

## 문제 해결

### Windows에서 dlib 설치 실패
1. Visual C++ Build Tools 설치 확인
2. Visual Studio Installer에서 "C++ 빌드 도구" 선택
3. 재시도: `pip install dlib`

### Ubuntu에서 dlib 설치 실패
1. 시스템 패키지 확인:
   ```bash
   sudo apt-get install build-essential cmake libopenblas-dev liblapack-dev
   ```
2. pip 업그레이드:
   ```bash
   pip3 install --upgrade pip
   ```
3. 재시도: `pip3 install dlib`

### 카메라가 인식되지 않는 경우
1. **Windows**:
   - 장치 관리자에서 카메라 확인
   - 다른 프로그램에서 카메라 사용 중인지 확인
   - DirectShow 드라이버 설치 확인

2. **Ubuntu**:
   ```bash
   # 카메라 디바이스 확인
   ls -l /dev/video*
   
   # 권한 확인
   groups $USER
   
   # video 그룹에 사용자 추가 (필요시)
   sudo usermod -a -G video $USER
   # 로그아웃 후 재로그인 필요
   ```

### OCR 모델 다운로드 실패
- 인터넷 연결 확인
- 방화벽 설정 확인
- 수동 다운로드: `download_ocr_models.py` 참고

## 실행 파일 생성 (선택적)

### Windows
```powershell
# PyInstaller 설치
pip install pyinstaller

# 실행 파일 생성
python -m PyInstaller GARAMe_MANAGER_1.8.6.spec
```

### Ubuntu
```bash
# PyInstaller 설치
pip3 install pyinstaller

# 실행 파일 생성
python3 -m PyInstaller GARAMe_MANAGER_1.8.6.spec
```

## 추가 정보

- 자세한 설치 정보: `WINDOWS11_INSTALL_GUIDE.md`, `UBUNTU_INSTALL_GUIDE.md`
- OCR 설치: `OCR_INSTALL_GUIDE.md`
- 크로스 플랫폼 파일: `LINUX_WINDOWS_CROSSPLATFORM_FILES.md`

## 지원

문제가 발생하면:
1. 로그 파일 확인: `logs/run/`
2. 시스템 요구사항 확인
3. 모든 의존성 재설치 시도

