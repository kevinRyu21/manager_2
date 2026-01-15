# GARAMe MANAGER 1.8.8 설치 및 문제 해결 가이드

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [Ubuntu 설치 가이드](#ubuntu-설치-가이드)
3. [오프라인 설치](#오프라인-설치)
4. [문제 해결](#문제-해결)
5. [주요 변경사항 (v1.8.8)](#주요-변경사항-v188)

---

## 🚀 빠른 시작

### Ubuntu/Linux

```bash
# 1. 프로젝트 디렉토리로 이동
cd /path/to/GARAMe\ MANAGER/1.8.8

# 2. 실행 권한 부여
chmod +x run_ubuntu.sh

# 3. 실행 (자동 설치 및 실행)
./run_ubuntu.sh
```

### 인터넷이 없는 환경 (오프라인)

```bash
# 1. 인터넷이 있는 환경에서 wheel 파일 다운로드
./download_wheels.sh

# 2. 오프라인 환경으로 wheels/ 디렉토리 복사

# 3. 오프라인 설치
./install_offline.sh

# 또는 run_ubuntu.sh가 자동으로 오프라인 모드 감지
./run_ubuntu.sh
```

---

## 📦 Ubuntu 설치 가이드

### 자동 설치 (권장)

```bash
./run_ubuntu.sh
```

스크립트가 자동으로:
- 시스템 패키지 설치 (python3-dev 포함)
- 가상환경 생성 (`~/venvs/garame`)
- Python 패키지 설치
- 카메라 권한 설정
- OCR 모델 다운로드 (최초 1회)
- 프로그램 실행

### 얼굴 인식 기능 설치

```bash
INSTALL_FACE_RECOGNITION=1 ./run_ubuntu.sh
```

자동으로:
- NumPy 1.26.4로 다운그레이드
- OpenCV 4.9.0.80으로 다운그레이드
- dlib 및 face-recognition 설치

### 수동 설치

```bash
# 1. 시스템 패키지 설치
sudo apt update
sudo apt install -y \
  python3-venv python3-dev python3-tk libgl1 libglib2.0-0t64 espeak-ng \
  libasound2t64 libportaudio2 ffmpeg \
  v4l-utils libv4l-0 \
  build-essential cmake libopenblas-dev liblapack-dev \
  xdotool

# 2. 가상환경 생성
python3 -m venv ~/venvs/garame
source ~/venvs/garame/bin/activate

# 3. pip 업그레이드
pip install --upgrade pip wheel setuptools

# 4. Python 패키지 설치
pip install --no-cache-dir \
  Pillow matplotlib "numpy==1.26.4" pyttsx3 opencv-contrib-python==4.9.0.80 \
  psutil pynput keyboard pystray pandas openpyxl scikit-image imageio \
  requests tqdm pathlib2 configparser easyocr \
  opencv-python-headless==4.9.0.80

# 5. 얼굴 인식 (선택적)
pip install --no-cache-dir dlib face-recognition

# 6. 실행
cd /path/to/GARAMe\ MANAGER/1.8.8
python main.py --config config.conf
```

---

## 💾 오프라인 설치

### 1단계: 인터넷이 있는 환경에서 준비

```bash
# wheel 파일 다운로드
./download_wheels.sh

# 얼굴 인식 포함하려면
DOWNLOAD_FACE_RECOGNITION=1 ./download_wheels.sh
```

다운로드된 파일:
- `wheels/` 디렉토리에 모든 Python 패키지 wheel 파일

### 2단계: 오프라인 환경으로 복사

```bash
# wheels/ 디렉토리를 USB나 네트워크로 복사
cp -r wheels/ /path/to/offline/computer/
```

### 3단계: 오프라인 환경에서 설치

```bash
# 방법 1: install_offline.sh 사용
./install_offline.sh

# 방법 2: run_ubuntu.sh 자동 감지 (wheels/ 디렉토리가 있으면 자동으로 오프라인 모드)
./run_ubuntu.sh
```

---

## 🔧 문제 해결

### 1. evdev 빌드 오류: `Python.h: No such file or directory`

**문제**: `python3-dev` 패키지가 설치되지 않음

**해결**:
```bash
sudo apt install -y python3-dev
pip install evdev
```

또는 `run_ubuntu.sh`를 실행하면 자동으로 설치됩니다.

---

### 2. Illegal instruction (core dumped)

**문제**: NumPy/PyTorch가 CPU에서 지원하지 않는 명령어 사용

**해결 방법 1** (권장): 프로그램에 이미 환경 변수 설정되어 있음
```bash
# main.py에 자동 설정됨, 그냥 실행
./run_ubuntu.sh
```

**해결 방법 2**: NumPy 재설치
```bash
source ~/venvs/garame/bin/activate
pip uninstall -y numpy
pip install numpy==1.26.4
```

**해결 방법 3**: CPU 호환성 스크립트 실행
```bash
./fix_cpu_compatibility.sh
```

**해결 방법 4**: PaddleOCR 사용 (PyTorch 문제 회피)
- 환경설정 → OCR 엔진 → PaddleOCR 선택
- 또는 `config.conf`에서 `ocr_engine = paddle`

**서명 인식 시 EasyOCR NNPACK 오류**:
- v1.8.8에서 자동으로 해결됨
- NNPACK 비활성화 및 경고 무시 처리
- 문제가 계속되면 PaddleOCR 사용 권장

자세한 내용: `CPU_COMPATIBILITY_FIX.md` 참조

---

### 3. 얼굴 인식 기능 사용 시 NumPy 버전 오류

**문제**: NumPy 2.x는 dlib과 호환되지 않음

**해결**:
```bash
source ~/venvs/garame/bin/activate
pip uninstall -y numpy opencv-contrib-python opencv-python opencv-python-headless
pip install "numpy==1.26.4" "opencv-contrib-python==4.9.0.80" "opencv-python-headless==4.9.0.80"
```

또는 `INSTALL_FACE_RECOGNITION=1 ./run_ubuntu.sh`로 실행

자세한 내용: `FACE_RECOGNITION_NUMPY_FIX.md` 참조

---

### 4. 현재상태 문구 크기 설정이 반영되지 않음

**해결됨**: v1.8.8에서 수정됨
- 문자 크기 조절 화면에서 실시간으로 저장 및 적용
- 현재상태 문구 크기 설정이 즉시 반영됨

---

### 5. 서명 인식 설정이 작동하지 않음

**해결됨**: v1.8.8에서 수정됨
- 환경설정에서 서명 인식 설정을 "사용"으로 체크하면
- 안전교육 과정에서 실제로 서명 인식 과정을 거침
- 인식 결과 확인 및 편집 화면이 통합됨

---

### 6. 카메라 접근 권한 오류

**해결**:
```bash
# video 그룹에 사용자 추가
sudo usermod -aG video $USER

# 로그아웃 후 다시 로그인 필요
```

또는 `run_ubuntu.sh`가 자동으로 처리합니다.

---

### 7. 오프라인 모드에서 패키지 설치 실패

**확인사항**:
1. `wheels/` 디렉토리가 프로젝트 폴더에 있는지 확인
2. wheel 파일이 제대로 다운로드되었는지 확인
3. `install_offline.sh` 실행 권한 확인: `chmod +x install_offline.sh`

---

## ✨ 주요 변경사항 (v1.8.8)

### 기능 개선

1. **문자 크기 조절 실시간 반영**
   - 현재상태 문구 크기 설정이 즉시 저장 및 적용됨
   - 모든 패널에 실시간으로 반영

2. **서명 인식 기능 개선**
   - 환경설정에서 서명 인식 설정이 실제로 작동
   - 서명 인식 결과 확인 및 편집 화면 통합
   - 화상키보드 통합 (화면 문구 편집과 동일한 키보드)

3. **오프라인 실행 지원**
   - `download_wheels.sh`: wheel 파일 다운로드
   - `install_offline.sh`: 오프라인 설치
   - `run_ubuntu.sh`: 자동 오프라인 모드 감지

4. **CPU 호환성 개선**
   - Illegal instruction 오류 방지
   - 환경 변수 자동 설정
   - CPU 호환성 문제 해결 스크립트 제공

### 버그 수정

1. **evdev 설치 오류 수정**
   - `python3-dev` 패키지 자동 설치

2. **프리뷰 업데이트 오류 수정**
   - `NoneType` 오류 해결

3. **표시 문구 편집 저장 개선**
   - 예외 처리 추가
   - 실시간 반영 보장

---

## 📚 관련 문서

- `UBUNTU_INSTALL_GUIDE.md`: Ubuntu 설치 상세 가이드
- `CPU_COMPATIBILITY_FIX.md`: CPU 호환성 문제 해결
- `FACE_RECOGNITION_INSTALL_GUIDE.md`: 얼굴 인식 설치 가이드
- `FACE_RECOGNITION_NUMPY_FIX.md`: NumPy 호환성 문제 해결
- `OCR_INSTALL_GUIDE.md`: OCR 설치 가이드
- `CROSS_PLATFORM_GUIDE.md`: 크로스 플랫폼 가이드

---

## 🆘 지원

문제가 계속되면:

1. 로그 파일 확인: `logs/run/run_*.log`
2. Python 버전 확인: `python3 --version`
3. 가상환경 확인: `source ~/venvs/garame/bin/activate && python --version`
4. 패키지 버전 확인: `pip list | grep -E "(numpy|opencv|torch)"`

---

## 📝 버전 정보

- **버전**: 1.8.8
- **최종 업데이트**: 2025-11-04
- **Python 버전**: 3.8 이상 (권장: 3.11-3.13)
- **주요 의존성**:
  - NumPy: 1.26.4 (얼굴 인식 사용 시) 또는 2.2.6
  - OpenCV: 4.9.0.80 (얼굴 인식 사용 시) 또는 4.12.0.88
  - EasyOCR: 1.6.0 이상

---

**마지막 업데이트**: 2025-11-04

