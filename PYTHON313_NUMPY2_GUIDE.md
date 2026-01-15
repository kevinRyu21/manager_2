# Python 3.13 + NumPy 2.x 호환성 가이드

## ⚠️ Python 3.13 사용 시 주의사항

Python 3.13에서는 다음 패키지들이 NumPy 2.x를 요구합니다:
- `ml-dtypes >= 0.5.0` → **numpy >= 2.1.0** 필요
- `opencv-contrib-python 4.9.x` → **numpy < 2.0** 필요

이로 인해 **패키지 충돌**이 발생합니다.

## 🔧 자동 해결 방법 (권장)

```bash
./fix_onnx_deps.sh
```

이 스크립트는 Python 3.13을 자동 감지하고:
1. NumPy를 2.x로 업그레이드
2. OpenCV를 4.10+로 업그레이드 (NumPy 2.x 지원)
3. ml-dtypes를 0.5+로 업그레이드

## 📋 수동 해결 방법

### 1단계: 가상환경 활성화
```bash
source venv/bin/activate
```

### 2단계: NumPy 2.x 설치
```bash
pip install --upgrade "numpy>=2.0.0"
```

### 3단계: OpenCV 4.10+ 설치 (NumPy 2.x 호환)
```bash
pip uninstall -y opencv-python opencv-contrib-python
pip install "opencv-contrib-python>=4.10.0"
```

### 4단계: ml-dtypes 0.5+ 설치
```bash
pip install --upgrade "ml-dtypes>=0.5.0"
```

### 5단계: 테스트
```bash
python3 -c "import numpy; print('NumPy:', numpy.__version__)"
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "import ml_dtypes; print('ml_dtypes:', ml_dtypes.__version__)"
python3 -c "import onnx; print('ONNX: OK')"
```

## 🐛 오류 예시 및 해결

### 오류 1: NumPy 버전 충돌
```
ERROR: Cannot install -r requirements.txt because these package versions have conflicting dependencies.
ml-dtypes 0.5.0 depends on numpy>=2.1.0; python_version >= "3.13"
```

**해결**: `./fix_onnx_deps.sh` 실행

### 오류 2: float4_e2m1fn 속성 없음
```
AttributeError: module 'ml_dtypes' has no attribute 'float4_e2m1fn'
```

**해결**: `./fix_onnx_deps.sh` 실행

### 오류 3: NumPy 2.x와 OpenCV 4.9 충돌
```
ImportError: numpy.core.multiarray failed to import
```

**해결**: OpenCV를 4.10+로 업그레이드
```bash
pip uninstall -y opencv-python opencv-contrib-python
pip install "opencv-contrib-python>=4.10.0"
```

## 📊 패키지 버전 호환성 표

| Python | NumPy | OpenCV | ml-dtypes | 상태 |
|--------|-------|--------|-----------|------|
| 3.11 | 1.26.4 | 4.9.0.80 | 0.5+ | ✅ OK |
| 3.12 | 1.26.4 | 4.9.0.80 | 0.5+ | ✅ OK |
| 3.13 | 1.26.4 | 4.9.0.80 | 0.5+ | ❌ 충돌 |
| 3.13 | 2.0+ | 4.10+ | 0.5+ | ✅ OK |

## 🎯 권장 설치 방법

### Python 3.11/3.12 사용자
```bash
./install.sh
# NumPy 1.26.4 + OpenCV 4.9.0.80 자동 설치
```

### Python 3.13 사용자
```bash
./install.sh
# 설치 후 다음 실행:
./fix_onnx_deps.sh
# NumPy 2.x + OpenCV 4.10+ 자동 업그레이드
```

## 💡 추가 정보

### requirements.txt 변경사항
```python
# NumPy (Python 버전에 따라 자동 선택)
numpy>=1.26.4  # Python 3.13에서 2.x로 자동 업그레이드

# OpenCV (Python 버전에 따라 자동 선택)
opencv-contrib-python>=4.9.0.80  # Python 3.13에서 4.10+로 자동 업그레이드

# ONNX 의존성
ml-dtypes>=0.5.0  # ONNX float4_e2m1fn 지원
```

### pip 의존성 해결 과정
1. Python 3.13 감지
2. ml-dtypes 0.5+ 설치 시도
3. NumPy 2.1+ 의존성 확인
4. OpenCV 4.9.x와 충돌 감지
5. **해결 필요** → `./fix_onnx_deps.sh` 실행

---

**작성일**: 2025-01-19  
**버전**: v1.9.5  
**대상**: Python 3.13 사용자
