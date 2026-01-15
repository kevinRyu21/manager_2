# GARAMe Manager v1.9.5 - PyInstaller 빌드 가이드

## 🎯 빌드 환경 요구사항

### 필수 사항
- **OS**: Ubuntu 25.10 (또는 호환 Linux 배포판)
- **Python**: 3.10 이상
- **디스크**: 최소 5GB 여유 공간
- **RAM**: 4GB 이상 권장

⚠️ **중요**: macOS에서 빌드한 실행 파일은 Ubuntu에서 작동하지 않습니다!

## 📋 빌드 전 준비

### 1. 의존성 설치

```bash
# 시스템 패키지 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    libopencv-dev git wget curl xdotool

# 프로젝트 디렉토리로 이동
cd /path/to/garame/manager/1.9.5

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치 (GPU 또는 CPU 모드 선택)
./install.sh
```

### 2. 빌드 준비 상태 확인

```bash
# 모든 의존성이 올바르게 설치되었는지 확인
./check_build_ready.sh
```

다음 항목이 모두 통과해야 합니다:
- ✅ 플랫폼: Linux
- ✅ 가상환경: 존재함
- ✅ Python 버전 확인
- ✅ 필수 패키지 설치 (InsightFace, YOLOv11, PyTorch 등)
- ✅ OpenCV 바이너리 확인
- ✅ PyInstaller 설치
- ✅ 필수 파일 존재
- ✅ 디스크 여유 공간

## 🔨 빌드 실행

### 1. OpenCV 확인 (선택사항)

```bash
# OpenCV 설치 상태 확인
./check_cv2.sh
```

문제가 있으면 자동 수정을 선택하세요.

### 2. PyInstaller 빌드

```bash
# .spec 파일로 빌드 (권장)
pyinstaller --clean garame_manager.spec
```

**빌드 시간**: 5-10분 (시스템 성능에 따라 다름)

### 3. 빌드 결과 확인

```bash
# 빌드 성공 확인
ls -lh dist/garame_manager/garame_manager

# 빌드 디렉토리 크기 확인
du -sh dist/garame_manager
```

예상 크기: **~500MB**

## 📁 빌드 결과 구조

```
dist/garame_manager/
├── garame_manager          # 실행 파일 (메인)
├── _internal/              # 의존성 라이브러리
│   ├── cv2/               # OpenCV
│   ├── numpy/             # NumPy
│   ├── torch/             # PyTorch
│   ├── onnxruntime/       # ONNX Runtime (InsightFace)
│   ├── ultralytics/       # YOLOv11
│   └── ...
├── VERSION.txt
├── config.conf.example
├── standard_defaults.conf
└── safety_posters/
```

## 🧪 빌드 테스트

### 1. 기본 실행 테스트

```bash
# 빌드된 실행 파일 테스트
./dist/garame_manager/garame_manager --version
```

### 2. 전체 기능 테스트

```bash
# 실제 환경과 동일하게 테스트
cd dist/garame_manager
./garame_manager
```

다음 기능을 확인하세요:
- ✅ 얼굴 인식 (InsightFace)
- ✅ PPE 감지 (YOLOv11)
- ✅ 음성 알림 (gTTS)
- ✅ 한글 입력 (xdotool)
- ✅ GUI 표시 (Tkinter)

## 📦 배포 패키지 생성

### 1. 배포 디렉토리 생성

```bash
# 자동 배포 패키지 생성 (권장)
./create_distribution.sh
```

이 스크립트는:
1. PyInstaller 빌드 실행
2. 필요한 파일 복사 (설정, 리소스, 스크립트)
3. 오프라인 패키지 다운로드 (wheels/)
4. 압축 파일 생성 (.tar.gz)

### 2. 배포 패키지 구조

```
GARAMe_Manager_1.9.5_Ubuntu25_Distribution/
├── garame_manager/         # PyInstaller 빌드 (~500MB)
├── garame_manager.sh       # 실행 스크립트
├── install_offline.sh      # 오프라인 설치 스크립트
├── requirements.txt        # Python 패키지 목록
├── wheels/                 # 오프라인 패키지 (1-2GB)
├── safety_posters/
├── config.conf.example
├── standard_defaults.conf
└── 배포_설치_가이드.md
```

### 3. 배포 패키지 크기

| 항목 | 크기 | 설명 |
|------|------|------|
| garame_manager/ | ~500MB | PyInstaller 빌드 |
| wheels/ | 1-2GB | Python 패키지 (오프라인 설치용) |
| 전체 압축 | 1.5-2.5GB | .tar.gz 형식 |

## 🐛 문제 해결

### OpenCV 바이너리 오류

```bash
# 증상: cv2.so 파일을 찾을 수 없음
# 해결:
./check_cv2.sh
# "y"를 눌러 자동 수정

# 또는 수동 재설치:
pip uninstall -y opencv-python opencv-contrib-python
pip install opencv-contrib-python==4.9.0.80
```

### PyInstaller 빌드 실패

```bash
# 증상: "No module named 'xxx'" 오류
# 해결: hiddenimports에 모듈 추가

# garame_manager.spec 편집
hiddenimports = [
    # 기존 항목...
    'xxx',  # 누락된 모듈 추가
]

# 재빌드
pyinstaller --clean garame_manager.spec
```

### 디스크 공간 부족

```bash
# 임시 파일 정리
rm -rf build dist *.pyc __pycache__
pip cache purge

# Python 캐시 삭제
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### 실행 파일이 느림

```bash
# 증상: 첫 실행 시 매우 느림
# 원인: AI 모델 다운로드 중 (InsightFace, YOLOv11)
# 해결: 인터넷 연결 확인, 두 번째 실행부터는 빠름
```

## 📊 빌드 최적화 비교

### v1.9.4 (dlib) vs v1.9.5 (InsightFace)

| 항목 | v1.9.4 | v1.9.5 | 개선율 |
|------|--------|--------|--------|
| 빌드 모드 | --onefile | --onedir | - |
| 빌드 크기 | 4.1GB | 500MB | **88% 감소** |
| 설치 시간 | 45-80분 | 10-15분 | **78% 단축** |
| 디스크 요구 | 15GB | 10GB | **33% 감소** |
| 얼굴 인식 정확도 | 99.38% | 99.86% | **+0.48%** |
| PPE 감지 정확도 | ~70% | 92.7% | **+22.7%** |

### .spec 파일 최적화

#### 제외된 대용량 파일
- `*.onnx` - InsightFace 모델 (buffalo_l 등)
- `*.pt` - YOLOv11 weights
- `*.pth` - PyTorch 모델
- `*.pkl` - Pickle 모델

→ 이 모델들은 첫 실행 시 자동 다운로드

#### 제외된 불필요한 패키지
- PyQt5/6, PySide2/6, wx (GUI 프레임워크)
- django, flask, fastapi (웹 프레임워크)
- jupyter, IPython (개발 도구)
- pytest, unittest (테스트 도구)
- dlib, face_recognition (v1.9.4 레거시)

## 🚀 빌드 워크플로우 (전체)

```bash
# 1. 저장소 클론 (Ubuntu 환경)
git clone https://github.com/your-repo/garame.git
cd garame/manager/1.9.5

# 2. 의존성 설치
./install.sh
# CPU 또는 GPU 모드 선택

# 3. 빌드 준비 확인
./check_build_ready.sh

# 4. OpenCV 확인 (선택)
./check_cv2.sh

# 5. PyInstaller 빌드
pyinstaller --clean garame_manager.spec

# 6. 빌드 테스트
./dist/garame_manager/garame_manager --version

# 7. 배포 패키지 생성
./create_distribution.sh

# 8. 배포
# GARAMe_Manager_1.9.5_Ubuntu25_Distribution.tar.gz 파일을
# 대상 Ubuntu 시스템에 복사
```

## 📝 추가 정보

### GPU 가속 빌드

```bash
# GPU 모드로 설치 시:
./install.sh
# GPU 사용? y

# PyInstaller는 설치된 패키지 그대로 사용
# onnxruntime-gpu, PyTorch CUDA 버전 포함
```

### CPU 전용 빌드 (기본)

```bash
# CPU 모드로 설치 시:
./install.sh
# GPU 사용? n (또는 Enter)

# PyInstaller는 설치된 패키지 그대로 사용
# onnxruntime (CPU), PyTorch CPU 버전 포함
```

### 크로스 플랫폼 주의사항

⚠️ **절대 하지 말아야 할 것**:
- macOS에서 빌드하여 Ubuntu에서 실행 ❌
- Ubuntu에서 빌드하여 macOS에서 실행 ❌
- Windows에서 빌드하여 Ubuntu에서 실행 ❌

✅ **올바른 방법**:
- Ubuntu에서 빌드 → Ubuntu에서 실행 ✅

## 🔗 관련 문서

- [INSTALL_GUIDE.md](md/INSTALL_GUIDE.md) - 사용자 설치 가이드
- [GPU_INSTALLATION_GUIDE.md](GPU_INSTALLATION_GUIDE.md) - GPU 설치 가이드
- [BUILD_SIZE_OPTIMIZATION.md](BUILD_SIZE_OPTIMIZATION.md) - 빌드 최적화 가이드
- [CHANGELOG.md](CHANGELOG.md) - 변경 이력

---

**작성일**: 2025-01-19  
**버전**: v1.9.5  
**대상 OS**: Ubuntu 25.10
