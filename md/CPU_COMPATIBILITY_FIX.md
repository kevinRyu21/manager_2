# CPU 호환성 문제 해결 가이드

## 문제 설명

`Illegal instruction (core dumped)` 오류는 NumPy나 PyTorch가 현재 CPU에서 지원하지 않는 고급 명령어(AVX, AVX2, FMA 등)를 사용하려고 할 때 발생합니다.

## 해결 방법

### 방법 1: 환경 변수 설정 (자동 적용됨)

`main.py`에 이미 환경 변수가 설정되어 있습니다. 프로그램을 다시 실행해보세요:

```bash
./run_ubuntu.sh
```

### 방법 2: NumPy 재설치 (권장)

CPU 호환성 문제가 계속되면 NumPy를 호환 가능한 버전으로 재설치하세요:

```bash
source ~/venvs/garame/bin/activate

# NumPy 재설치
pip uninstall -y numpy
pip install numpy==1.26.4 --no-binary numpy

# 또는 일반 빌드로 재설치
pip install numpy==1.26.4
```

### 방법 3: CPU 호환성 스크립트 실행

```bash
./fix_cpu_compatibility.sh
```

### 방법 4: EasyOCR NNPACK 문제 해결 (서명 인식 시)

서명 인식 과정에서 EasyOCR 사용 시 NNPACK 경고와 Illegal instruction 오류가 발생할 수 있습니다.

**자동 해결됨**: v1.8.8에서 자동으로 처리됩니다
- `main.py`와 `safety_signature.py`에 NNPACK 비활성화 환경 변수 설정
- PyTorch 백엔드에서 NNPACK 비활성화
- EasyOCR 초기화 시 경고 무시

**수동 해결** (문제가 계속될 경우):

1. **PaddleOCR 사용** (권장):
   - 환경설정 → OCR 엔진 → PaddleOCR 선택
   - 또는 `config.conf`에서:
     ```
     [ENV]
     ocr_engine = paddle
     ```

2. **PyTorch CPU-only 재설치**:
   ```bash
   source ~/venvs/garame/bin/activate
   pip uninstall -y torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```

### 방법 5: PyTorch 재설치 (CPU-only)

EasyOCR을 계속 사용하려면 PyTorch를 CPU-only 버전으로 재설치:

```bash
source ~/venvs/garame/bin/activate

# PyTorch 제거
pip uninstall -y torch torchvision

# CPU-only PyTorch 재설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## 확인 방법

설치 후 테스트:

```bash
source ~/venvs/garame/bin/activate
python -c "import numpy as np; print('NumPy:', np.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
```

## 추가 정보

- CPU 정보 확인: `cat /proc/cpuinfo | grep flags`
- NumPy 버전 확인: `python -c "import numpy; print(numpy.__version__)"`
- PyTorch 버전 확인: `python -c "import torch; print(torch.__version__)"`

## 참고

- `main.py`에 환경 변수가 자동으로 설정되어 CPU 호환성 문제를 최소화합니다
- 문제가 계속되면 방법 2 또는 방법 4를 시도하세요

