# GARAMe Manager v1.9.5 - 문제 해결 가이드

## 🐛 일반적인 오류 및 해결 방법

### 1. ONNX ml_dtypes 오류

#### 증상
```
AttributeError: module 'ml_dtypes' has no attribute 'float4_e2m1fn'
```

#### 원인
- `ml-dtypes` 패키지 버전이 너무 낮음
- ONNX가 `ml-dtypes >= 0.5.0` 필요

#### 해결 방법

**방법 1: 자동 수정 스크립트 (권장)**
```bash
./fix_onnx_deps.sh
```

**방법 2: 수동 수정**
```bash
source venv/bin/activate
pip install --upgrade "ml-dtypes>=0.5.0"
```

**방법 3: 전체 재설치**
```bash
rm -rf venv
./install.sh
```

---

### 2. OpenCV (cv2) import 오류

#### 증상
```
ImportError: libopencv_xxx.so: cannot open shared object file
```

#### 해결 방법
```bash
./check_cv2.sh
# "y"를 눌러 자동 수정

# 또는 수동 재설치:
source venv/bin/activate
pip uninstall -y opencv-python opencv-contrib-python
pip install opencv-contrib-python==4.9.0.80
```

---

### 3. PyTorch CUDA 오류 (GPU 모드)

#### 증상
```
RuntimeError: CUDA not available
```

#### 원인
- NVIDIA GPU가 없거나 CUDA가 설치되지 않음
- GPU 모드로 설치했지만 CUDA 드라이버 문제

#### 해결 방법

**CPU 모드로 전환**
```bash
source venv/bin/activate
pip uninstall -y torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

**CUDA 설치 확인**
```bash
nvidia-smi
# CUDA가 표시되지 않으면 드라이버 설치 필요
```

---

### 4. NumPy 버전 충돌

#### 증상
```
ValueError: numpy.dtype size changed
```

#### 원인
- NumPy 2.x가 설치됨 (OpenCV와 호환 안 됨)

#### 해결 방법
```bash
source venv/bin/activate
pip uninstall -y numpy
pip install "numpy==1.26.4"
```

---

### 5. 디스크 공간 부족

#### 증상
```
OSError: [Errno 28] No space left on device
```

#### 해결 방법
```bash
# pip 캐시 정리
pip cache purge

# Python 캐시 정리
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# /tmp 정리
sudo rm -rf /tmp/*

# 불필요한 패키지 제거
sudo apt autoremove
sudo apt clean
```

---

### 6. 한글 입력 조합 안 됨

#### 증상
- 자음과 모음이 따로 입력됨 (예: "ㄱㅏㄹㅏㅁ" 대신 "가람")

#### 원인
- `xdotool`이 설치되지 않음

#### 해결 방법
```bash
sudo apt update
sudo apt install -y xdotool
```

---

### 7. gTTS 음성 재생 안 됨

#### 증상
- 음성 알림이 재생되지 않음

#### 원인
- 오디오 재생 도구가 없음 (`mpg123` 또는 `ffplay`)

#### 해결 방법
```bash
# mpg123 설치 (권장)
sudo apt install -y mpg123

# 또는 ffmpeg 설치
sudo apt install -y ffmpeg
```

---

### 8. InsightFace 모델 다운로드 실패

#### 증상
```
urllib.error.URLError: <urlopen error [Errno 111] Connection refused>
```

#### 원인
- 인터넷 연결 문제
- 방화벽 차단

#### 해결 방법
```bash
# 인터넷 연결 확인
ping -c 3 google.com

# 프록시 설정 (필요시)
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080

# 프로그램 재실행
./run.sh
```

---

### 9. PyInstaller 빌드 실패

#### 증상
```
ModuleNotFoundError: No module named 'xxx'
```

#### 원인
- `garame_manager.spec`의 `hiddenimports`에 모듈 누락

#### 해결 방법
```bash
# .spec 파일 편집
nano garame_manager.spec

# hiddenimports에 누락된 모듈 추가
hiddenimports = [
    # 기존 항목...
    'xxx',  # 누락된 모듈 추가
]

# 재빌드
pyinstaller --clean garame_manager.spec
```

---

### 10. 프로그램이 너무 느림

#### 증상
- 첫 실행 시 매우 느림 (1-2분 대기)

#### 원인
- AI 모델 자동 다운로드 중 (InsightFace buffalo_l, YOLOv11)
- 정상적인 현상

#### 해결 방법
- 첫 실행 시에만 발생
- 두 번째 실행부터는 빠름 (~3-5초)
- 인터넷 연결이 빠를수록 다운로드 시간 단축

---

## 🔍 로그 확인 방법

### 최근 로그 파일 확인
```bash
ls -lt logs/ | head -5
```

### 로그 내용 확인
```bash
cat logs/manager_YYYYMMDD_HHMMSS.log
```

### 오류만 필터링
```bash
grep -i error logs/manager_*.log
```

---

## 📞 추가 지원

위의 방법으로 해결되지 않는 경우:

1. **로그 파일 수집**
   ```bash
   tar -czf garame_debug.tar.gz logs/ disk_usage_install.log
   ```

2. **시스템 정보 수집**
   ```bash
   python3 --version > system_info.txt
   pip list >> system_info.txt
   df -h >> system_info.txt
   ```

3. **이슈 리포트**
   - GitHub Issues에 `garame_debug.tar.gz` 및 `system_info.txt` 첨부
   - 오류 메시지 전문 복사

---

**작성일**: 2025-01-19  
**버전**: v1.9.5  
**대상 OS**: Ubuntu 25.10
