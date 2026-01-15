# GPU 가속 설치 가이드

GARAMe MANAGER v1.9.5는 NVIDIA GPU를 사용한 AI 가속을 지원합니다.

## 📋 목차

1. [GPU vs CPU 비교](#gpu-vs-cpu-비교)
2. [GPU 요구사항](#gpu-요구사항)
3. [설치 방법](#설치-방법)
4. [GPU 가속 확인](#gpu-가속-확인)
5. [문제 해결](#문제-해결)

---

## 🎯 GPU vs CPU 비교

### GPU 가속 사용 시
- ✅ **얼굴 인식**: 약 5~10배 빠름
- ✅ **PPE 감지**: 약 3~5배 빠름
- ✅ **다중 센서**: 동시 처리 성능 향상
- ⚠️ **요구사항**: NVIDIA GPU + CUDA 필요

### CPU 모드
- ✅ **호환성**: 모든 시스템에서 작동
- ✅ **안정성**: 추가 드라이버 불필요
- ⚠️ **성능**: GPU 대비 느림
- ✅ **권장**: GPU가 없는 경우

---

## 💻 GPU 요구사항

### 하드웨어
- **GPU**: NVIDIA GeForce/Quadro/Tesla 시리즈
- **최소**: GTX 1050 Ti 이상
- **권장**: RTX 2060 이상
- **VRAM**: 4GB 이상 (권장: 6GB 이상)

### 소프트웨어
- **CUDA**: 11.8 이상 (권장: 12.x)
- **cuDNN**: 8.6 이상
- **NVIDIA Driver**: 최신 버전

---

## 🔧 설치 방법

### 방법 1: 설치 스크립트 사용 (권장)

설치 중 GPU 옵션 선택:

```bash
./install.sh

# 또는
python3 install_requirements.py
```

**설치 과정 중 질문**:
```
GPU 가속을 사용하시겠습니까? (y/n, 기본값: n):
```

- **n (기본값)**: CPU 모드로 설치
- **y**: GPU 가속 모드로 설치

### 방법 2: 수동 설치

#### Step 1: CUDA 설치 확인

```bash
# CUDA 버전 확인
nvcc --version

# NVIDIA Driver 확인
nvidia-smi
```

**CUDA가 없으면**:
```bash
# NVIDIA 공식 사이트에서 CUDA Toolkit 다운로드
# https://developer.nvidia.com/cuda-downloads

# Ubuntu 예시 (CUDA 12.x)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
sudo apt update
sudo apt install cuda
```

#### Step 2: 기본 패키지 설치

```bash
cd /Users/cyber621/Desktop/develop/garam/manager/1.9.5

# 가상환경 활성화
source venv/bin/activate

# 기본 패키지 설치
pip install -r requirements.txt
```

#### Step 3: GPU 가속 패키지 설치

```bash
# CPU 버전 제거
pip uninstall onnxruntime

# GPU 버전 설치
pip install onnxruntime-gpu>=1.16.0
```

---

## ✅ GPU 가속 확인

### 프로그램 실행 후 로그 확인

```bash
./run.sh
```

**GPU 가속 활성화 시 로그**:
```
[AI] GPU 감지: NVIDIA GeForce RTX 3080
[AI] CUDA 가속 활성화
[AI] ONNX Runtime GPU Provider: CUDAExecutionProvider
```

**CPU 모드 로그**:
```
[AI] CPU 모드로 실행
[AI] ONNX Runtime CPU Provider: CPUExecutionProvider
```

### Python에서 확인

```bash
python3 -c "import onnxruntime as ort; print('Available providers:', ort.get_available_providers())"
```

**GPU 가속 활성화 시**:
```
Available providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

**CPU 모드**:
```
Available providers: ['CPUExecutionProvider']
```

---

## 🔍 문제 해결

### 1. GPU가 감지되지 않음

**증상**:
```
[AI] GPU를 찾을 수 없습니다. CPU 모드로 실행합니다.
```

**해결 방법**:

```bash
# NVIDIA Driver 확인
nvidia-smi

# 출력 없으면 드라이버 재설치
sudo ubuntu-drivers autoinstall
sudo reboot

# CUDA 확인
nvcc --version

# onnxruntime-gpu 재설치
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu>=1.16.0
```

### 2. CUDA 버전 불일치

**증상**:
```
RuntimeError: CUDA version mismatch
```

**해결 방법**:

```bash
# CUDA 버전 확인
nvcc --version
nvidia-smi  # Driver가 지원하는 최대 CUDA 버전 확인

# 호환되는 onnxruntime-gpu 버전 설치
# CUDA 11.x
pip install onnxruntime-gpu==1.16.0

# CUDA 12.x
pip install onnxruntime-gpu==1.17.0
```

### 3. 메모리 부족 오류

**증상**:
```
CUDA out of memory
```

**해결 방법**:

1. **배치 크기 줄이기**: config.conf 수정
2. **CPU 모드로 전환**:
   ```bash
   pip uninstall onnxruntime-gpu
   pip install onnxruntime>=1.16.0
   ```
3. **GPU 메모리 정리**:
   ```bash
   nvidia-smi  # 프로세스 확인
   sudo fuser -v /dev/nvidia*  # GPU 사용 프로세스 확인
   ```

### 4. GPU가 있지만 CPU 모드로 설치한 경우

**GPU 가속으로 전환**:

```bash
# 1. onnxruntime (CPU) 제거
pip uninstall onnxruntime

# 2. onnxruntime-gpu 설치
pip install onnxruntime-gpu>=1.16.0

# 3. 프로그램 재실행
./run.sh
```

### 5. CPU 모드로 돌아가고 싶은 경우

```bash
# 1. onnxruntime-gpu 제거
pip uninstall onnxruntime-gpu

# 2. onnxruntime (CPU) 설치
pip install onnxruntime>=1.16.0

# 3. 프로그램 재실행
./run.sh
```

---

## 📊 성능 비교 (예시)

| 작업 | CPU (i7-10700) | GPU (RTX 3060) | 향상 |
|------|---------------|----------------|------|
| 얼굴 인식 (1명) | 50ms | 8ms | **6.3x** |
| 얼굴 인식 (10명) | 180ms | 25ms | **7.2x** |
| PPE 감지 (1프레임) | 80ms | 20ms | **4.0x** |
| PPE 감지 (실시간) | 12 FPS | 50 FPS | **4.2x** |

---

## 🎯 권장 사항

### GPU 가속 권장 케이스
- ✅ 다중 센서 (5개 이상) 동시 모니터링
- ✅ 실시간 얼굴 인식 + PPE 감지 동시 사용
- ✅ 고해상도 카메라 (1080p 이상) 사용
- ✅ NVIDIA GPU 보유

### CPU 모드 권장 케이스
- ✅ 단일 또는 소수 센서 (1~3개)
- ✅ GPU가 없는 환경
- ✅ 낮은 해상도 카메라 (720p 이하)
- ✅ 안정성 우선

---

## 📞 추가 도움말

- **CUDA 설치 가이드**: https://docs.nvidia.com/cuda/cuda-installation-guide-linux/
- **ONNX Runtime GPU**: https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html
- **NVIDIA Driver**: https://www.nvidia.com/Download/index.aspx

---

**버전**: GARAMe MANAGER v1.9.5
**업데이트**: 2025-11-18
