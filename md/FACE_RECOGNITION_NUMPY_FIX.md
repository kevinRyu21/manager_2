# 얼굴 인식 기능 - NumPy 호환성 문제 해결

## 문제 설명

얼굴 인식 기능 사용 시 `RuntimeError: Unsupported image type, must be 8bit gray or RGB image.` 오류가 발생할 수 있습니다.

이것은 **NumPy 2.x 버전과 dlib 라이브러리의 호환성 문제**입니다.

## 해결 방법

### 방법 1: NumPy와 OpenCV 버전 조정 (권장)

얼굴 인식 기능 사용 시에는 다음 조합을 사용해야 합니다:
- NumPy 1.26.4
- OpenCV 4.9.0.80 (또는 NumPy 1.x를 지원하는 버전)

```bash
pip uninstall numpy opencv-contrib-python opencv-python opencv-python-headless
pip install numpy==1.26.4
pip install opencv-contrib-python==4.9.0.80
```

또는 requirements.txt 사용:

```bash
pip install -r requirements.txt --force-reinstall
```

**주의**: OpenCV 4.12.0.88은 NumPy >= 2를 요구하므로, 얼굴 인식 기능 사용 시 OpenCV를 4.9.0.80으로 다운그레이드해야 합니다.

### 방법 2: requirements.txt 확인

`requirements.txt` 파일에서 NumPy 버전이 이미 `1.26.4`로 설정되어 있는지 확인하세요:

```
numpy==1.26.4
```

만약 `numpy==2.2.6`으로 되어 있다면, 다음과 같이 수정하세요:

```bash
pip install -r requirements.txt --force-reinstall
```

### 방법 3: 가상환경에서 재설치

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# NumPy 1.26.4 설치
pip install numpy==1.26.4

# 다른 의존성 설치
pip install -r requirements.txt
```

## 확인 방법

설치 후 NumPy 버전 확인:

```bash
python -c "import numpy; print(numpy.__version__)"
```

출력이 `1.26.4` 또는 `1.x.x` 형식이어야 합니다.

## 참고사항

- NumPy 1.26.4는 OpenCV 4.9.0.80과 완전히 호환됩니다
- PaddleOCR은 OpenCV 4.10.0.84와 NumPy >= 2를 요구하므로, 얼굴 인식 기능과 동시 사용 불가
- 얼굴 인식 기능을 사용하지 않는다면 NumPy 2.2.6과 OpenCV 4.12.0.88을 사용해도 됩니다

## PaddleOCR과 얼굴 인식 기능의 충돌

현재 PaddleOCR은 OpenCV 4.10.0.84와 NumPy >= 2를 요구합니다. 하지만 얼굴 인식 기능(dlib)은 NumPy 1.26.4가 필요합니다.

**해결 방법:**
1. **얼굴 인식 기능만 사용** (현재 설정): NumPy 1.26.4 + OpenCV 4.9.0.80, PaddleOCR 비활성화
2. **PaddleOCR만 사용**: NumPy 2.2.6 + OpenCV 4.10.0.84, 얼굴 인식 기능 미사용

두 기능을 동시에 사용할 수 없습니다. 필요한 기능에 따라 선택하세요.

