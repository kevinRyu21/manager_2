# 얼굴 인식 라이브러리 설치 가이드

얼굴 등록 관리 기능을 사용하기 위해서는 `face-recognition` 라이브러리가 필요합니다.

## ⚠️ 주의사항

`dlib` 라이브러리는 C++로 작성되어 있어 Windows에서 설치 시 추가 설정이 필요합니다.

## Windows 설치 방법

### 방법 1: 미리 빌드된 wheel 직접 다운로드 (권장, 가장 쉬움)

CMake나 Visual Studio 없이 미리 컴파일된 wheel 파일을 직접 설치합니다.

1. **Python 버전 확인**
   ```powershell
   python --version
   ```
   Python 3.11 또는 3.10인지 확인하세요.

2. **미리 빌드된 dlib wheel 직접 설치**
   
   **옵션 A: Gohlke's Unofficial Windows Binaries (권장)**
   
   https://www.lfd.uci.edu/~gohlke/pythonlibs/#dlib 에서 Python 버전에 맞는 wheel 파일을 다운로드:
   
   ```powershell
   # 예: Python 3.11 64bit인 경우
   # dlib-19.24.2-cp311-cp311-win_amd64.whl 다운로드 후:
   pip install [다운로드한_파일_경로]\dlib-19.24.2-cp311-cp311-win_amd64.whl
   ```
   
   **옵션 B: GitHub에서 미리 빌드된 wheel 검색**
   
   GitHub에서 "dlib wheel windows python 3.11"로 검색하여 사용 가능한 릴리즈를 찾으세요.

3. **face-recognition 설치**
   ```powershell
   pip install face-recognition
   ```

**참고:** 위 링크가 작동하지 않으면, 아래 방법들을 시도하세요.

### 방법 2: Conda 사용 (방법 1이 실패한 경우)

Conda를 사용하면 미리 빌드된 패키지를 쉽게 설치할 수 있습니다.

1. **Miniconda 또는 Anaconda 설치**
   - https://docs.conda.io/en/latest/miniconda.html
   - 또는 https://www.anaconda.com/download

2. **Conda 환경에서 설치**
   ```powershell
   # conda-forge에서 미리 빌드된 패키지 설치
   conda install -c conda-forge dlib
   pip install face-recognition
   ```

### 방법 3: Visual Studio Build Tools 사용 (방법 1, 2가 실패한 경우)

1. **CMake 설치**
   - https://cmake.org/download/ 에서 Windows용 CMake 다운로드
   - 설치 시 **"Add CMake to system PATH"** 옵션 체크 필수!

2. **Visual Studio Build Tools 설치**
   - https://visualstudio.microsoft.com/downloads/ 에서 "Build Tools for Visual Studio" 다운로드
   - 설치 시 "C++ build tools" 워크로드 선택

3. **pip 업데이트**
   ```powershell
   python -m pip install --upgrade pip
   ```

4. **cmake Python 패키지 설치**
   ```powershell
   pip install cmake
   ```

5. **dlib 설치** (시간이 오래 걸릴 수 있음)
   ```powershell
   pip install dlib
   ```

6. **face-recognition 설치**
   ```powershell
   pip install face-recognition
   ```

## Ubuntu/Linux 설치 방법

### ⚠️ 중요: NumPy 버전 충돌 주의

얼굴 인식 기능 사용 시 **NumPy 2.x는 dlib과 호환되지 않습니다**. NumPy 1.26.4를 사용해야 합니다.

1. **시스템 패키지 설치**
   ```bash
   sudo apt-get update
   sudo apt-get install build-essential cmake
   sudo apt-get install libopenblas-dev liblapack-dev
   sudo apt-get install xdotool  # 한글 입력 조합 지원 (선택적)
   ```

2. **NumPy와 OpenCV 버전 조정 (필수)**
   ```bash
   # 기존 NumPy 2.x 및 OpenCV 제거
   pip uninstall numpy opencv-contrib-python opencv-python opencv-python-headless
   
   # 얼굴 인식 호환 버전 설치
   pip install numpy==1.26.4
   pip install opencv-contrib-python==4.9.0.80
   ```

3. **Python 패키지 설치**
   ```bash
   pip install cmake
   pip install dlib  # 컴파일 시간이 매우 오래 걸릴 수 있습니다 (30분~1시간)
   pip install face-recognition
   ```

**참고**: 자세한 NumPy 호환성 문제 해결 방법은 `FACE_RECOGNITION_NUMPY_FIX.md` 파일을 참조하세요.

## 설치 확인

설치가 완료되었는지 확인:

```python
python -c "import face_recognition; print('face_recognition 설치 완료!')"
```

## 문제 해결

### 오류: "CMake is not installed"
- CMake를 설치하고 PATH에 추가했는지 확인
- 새로운 PowerShell/명령 프롬프트 창을 열어 다시 시도

### 오류: "Microsoft Visual C++ 14.0 or greater is required"
- Visual Studio Build Tools를 설치해야 합니다
- 또는 방법 1의 미리 빌드된 wheel을 사용하세요

### 설치가 매우 느림
- `dlib` 컴파일은 시간이 오래 걸릴 수 있습니다 (30분~1시간)
- 미리 빌드된 wheel 사용을 권장합니다

## 빠른 설치 스크립트 (Windows)

아래 스크립트를 `install_face_recognition.bat`로 저장하고 실행하세요:

```batch
@echo off
echo [1/3] pip 업데이트...
python -m pip install --upgrade pip

echo [2/3] cmake 설치...
pip install cmake

echo [3/3] dlib-binary 시도 (미리 빌드된 wheel)...
pip install dlib-binary

if %ERRORLEVEL% NEQ 0 (
    echo dlib-binary 설치 실패. 수동 설치가 필요할 수 있습니다.
    echo Visual Studio Build Tools와 CMake를 설치한 후 다시 시도하세요.
    pause
    exit /b 1
)

echo [4/4] face-recognition 설치...
pip install face-recognition

if %ERRORLEVEL% EQU 0 (
    echo 설치 완료!
) else (
    echo 설치 실패. 로그를 확인하세요.
)

pause
```

