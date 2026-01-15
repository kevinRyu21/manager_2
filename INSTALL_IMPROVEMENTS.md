# GARAMe Manager v1.9.5 - 설치 개선 사항

## 개요

이 문서는 install.sh와 run.sh에 추가된 개선 사항을 설명합니다. 이제 Python 3.13 환경에서 자동으로 올바른 패키지 버전을 설치하고, PyInstaller --onedir 모드로 빌드된 실행 파일을 올바르게 인식합니다.

## 1. Python 3.13 자동 호환성 처리

### 문제점

Python 3.13 환경에서 다음과 같은 패키지 버전 충돌이 발생했습니다:

```
ERROR: Cannot install -r requirements.txt because these package versions have conflicting dependencies.
  ml-dtypes 0.5.0 depends on numpy>=2.1.0; python_version >= "3.13"
  opencv-contrib-python 4.9.0.80 depends on numpy>=1.26.0
```

**원인**:
- Python 3.13에서 ml-dtypes 0.5+ 는 NumPy 2.x 필요
- OpenCV 4.9.x는 NumPy 1.x만 지원
- 두 요구사항이 서로 충돌

**기존 해결 방법**:
- install.sh 실행 후 수동으로 fix_onnx_deps.sh 실행 필요
- 사용자가 추가 단계를 수행해야 함

### 해결 방법

install.sh가 자동으로 Python 버전을 감지하고 올바른 패키지를 설치합니다.

#### 코드 위치
**파일**: `install.sh`
**함수**: `install_python_packages_online()`
**라인**: 449-494

#### 로직 흐름

```bash
# 1. Python 버전 확인
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# 2. Python 3.13인 경우 자동 업그레이드
if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    # NumPy 2.x 설치
    pip install --upgrade "numpy>=2.0.0"

    # OpenCV 4.10+ 설치 (NumPy 2.x 지원)
    pip uninstall -y opencv-python opencv-contrib-python
    pip install "opencv-contrib-python>=4.10.0"

    # ml-dtypes 0.5+ 설치
    pip install --upgrade "ml-dtypes>=0.5.0"

    # ONNX import 테스트
    python3 -c "import onnx; print('✓ ONNX import 성공')"
fi

# 3. Python 3.11/3.12인 경우 현재 버전 유지
else
    log_success "Python ${PYTHON_VERSION}: NumPy 1.26.4 + OpenCV 4.9.x 유지"
fi
```

#### 설치 출력 예시

**Python 3.13 환경**:
```
[INFO] Python 버전 호환성 확인 중...
[INFO] Python 버전: 3.13

[INFO] Python 3.13 감지: NumPy 2.x + OpenCV 4.10+ 자동 업그레이드
[INFO] (Python 3.13에서는 ml-dtypes 0.5+ 요구사항으로 NumPy 2.x가 필요합니다)

[INFO]   NumPy 2.x 설치 중...
[INFO]   OpenCV 4.10+ 설치 중...
[INFO]   ml-dtypes 0.5+ 설치 중...

[SUCCESS] Python 3.13 호환 패키지 업그레이드 완료

[INFO] 설치된 버전:
  NumPy: 2.2.6
  OpenCV: 4.12.0.88
  ml-dtypes: 0.5.4

[INFO] ONNX import 테스트 중...
  ✓ ONNX import 성공
[SUCCESS] ONNX 정상 작동
```

**Python 3.11/3.12 환경**:
```
[INFO] Python 버전 호환성 확인 중...
[INFO] Python 버전: 3.12
[SUCCESS] Python 3.12: NumPy 1.26.4 + OpenCV 4.9.x 유지
```

#### 버전 호환성 표

| Python | NumPy | OpenCV | ml-dtypes | ONNX | 상태 |
|--------|-------|--------|-----------|------|------|
| 3.11 | 1.26.4 | 4.9.0.80 | 0.5+ | ✅ | 자동 유지 |
| 3.12 | 1.26.4 | 4.9.0.80 | 0.5+ | ✅ | 자동 유지 |
| 3.13 | 2.2.6+ | 4.10+ | 0.5+ | ✅ | **자동 업그레이드** |

### 장점

1. **수동 개입 불필요**: fix_onnx_deps.sh 실행 필요 없음
2. **즉시 실행 가능**: install.sh 완료 후 바로 run.sh 실행 가능
3. **명확한 피드백**: 설치된 버전과 업그레이드 과정 표시
4. **ONNX 검증**: 설치 직후 ONNX import 테스트로 확인

---

## 2. PyInstaller --onedir 모드 지원

### 문제점

**garame_manager.spec 설정**:
```python
exe = EXE(
    exclude_binaries=True,  # --onedir 모드
)

coll = COLLECT(
    exe,
    a.binaries,
    name='garame_manager',  # dist/garame_manager/ 디렉토리 생성
)
```

**빌드 결과**:
```
dist/
└── garame_manager/           # 디렉토리
    ├── garame_manager        # 실행 파일
    ├── libopencv_*.so        # OpenCV 라이브러리
    ├── libnumpy_*.so         # NumPy 라이브러리
    └── ...                   # 기타 의존성 파일
```

**기존 스크립트 동작**:
```bash
# install.sh (잘못된 검사)
if [ -f "dist/garame_manager" ]; then  # ❌ 디렉토리를 파일로 검사
    cp dist/garame_manager ./garame_manager
fi

# run.sh (잘못된 검사)
if [ -f "garame_manager" ]; then      # ❌ 디렉토리를 파일로 검사
    ./garame_manager
fi
```

**결과**: "실행파일은 안 생겼는데" (executable wasn't created)

### 해결 방법

두 스크립트를 --onedir 모드 디렉토리 구조에 맞게 수정했습니다.

#### install.sh 수정 사항

##### 1) build_executable() - 기존 빌드 확인 (Lines 767-805)

**Before**:
```bash
if [ -f "./garame_manager" ] && [ -x "./garame_manager" ]; then
    log_success "실행 파일이 이미 존재합니다: ./garame_manager"
    FILE_SIZE=$(du -h ./garame_manager | awk '{print $1}')
fi
```

**After**:
```bash
# --onedir 모드 확인
if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
    log_success "실행 파일이 이미 존재합니다: ./garame_manager/garame_manager (--onedir 모드)"
    DIR_SIZE=$(du -sh garame_manager | awk '{print $1}')
    log_info "실행 디렉토리 크기: ${DIR_SIZE}"
    log_info "실행 방법:"
    log_info "  • ./run.sh (권장)"
    log_info "  • ./garame_manager/garame_manager (직접 실행)"
# --onefile 모드 확인 (이전 버전 호환성)
elif [ -f "./garame_manager" ] && [ -x "./garame_manager" ]; then
    log_success "실행 파일이 이미 존재합니다: ./garame_manager (--onefile 모드)"
fi
```

##### 2) build_executable() - 빌드 성공 처리 (Lines 885-945)

**Before**:
```bash
if [ -f "dist/garame_manager" ]; then
    cp dist/garame_manager ./garame_manager
    chmod +x ./garame_manager

    read -p "빌드 임시 파일(build/, dist/)을 삭제하시겠습니까? (y/n)"
    if [[ ! "$response" =~ ^[Nn]$ ]]; then
        rm -rf build/ dist/
    fi
fi
```

**After**:
```bash
if [ -d "dist/garame_manager" ] && [ -f "dist/garame_manager/garame_manager" ]; then
    log_success "실행 파일 빌드 완료! (--onedir 모드)"

    chmod +x dist/garame_manager/garame_manager

    # 전체 디렉토리 크기 확인
    DIR_SIZE=$(du -sh dist/garame_manager | awk '{print $1}')
    log_info "빌드 디렉토리 크기: ${DIR_SIZE}"

    # 기존 garame_manager/ 디렉토리가 있으면 삭제
    if [ -d "garame_manager" ]; then
        rm -rf garame_manager
    fi

    # dist/garame_manager/를 현재 디렉토리로 이동
    mv dist/garame_manager ./

    log_success "실행 파일 디렉토리가 생성되었습니다: ./garame_manager/ (크기: $DIR_SIZE)"

    log_info "디렉토리 구조 (--onedir 모드):"
    log_info "  ./garame_manager/           # 실행 파일 디렉토리"
    log_info "  ./garame_manager/garame_manager  # 메인 실행 파일"
    log_info "  ./garame_manager/*.so       # 공유 라이브러리들"

    # 임시 빌드 파일 자동 정리 (사용자 프롬프트 제거)
    rm -rf build/ dist/
    log_success "빌드 임시 파일 정리 완료"

    log_info "참고: run.sh는 자동으로 garame_manager/ 디렉토리를 인식합니다"
else
    log_error "실행 파일 빌드는 완료되었으나 dist/garame_manager/garame_manager를 찾을 수 없습니다"
    log_info "dist/ 디렉토리 내용:"
    ls -la dist/ 2>/dev/null || echo "  (dist/ 디렉토리 없음)"
fi
```

#### run.sh 수정 사항

5개 위치에서 --onedir 모드 지원 추가:

##### 1) run_normal() - 일반 실행 (Lines 322-330)

```bash
# PyInstaller 빌드 실행 파일이 있으면 우선 사용
# --onedir 모드: garame_manager/ 디렉토리 확인
if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
    log_info "실행 파일 모드 (--onedir): ./garame_manager/garame_manager"
    ./garame_manager/garame_manager "$@"
# --onefile 모드: 단일 실행 파일 확인 (이전 버전 호환성)
elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
    log_info "실행 파일 모드 (--onefile): ./garame_manager"
    ./garame_manager "$@"
# Python 모드
elif [ -f "main.py" ]; then
    log_info "Python 모드: python3 main.py"
    python3 main.py "$@"
fi
```

##### 2) run_with_watchdog() - Watchdog 자동 시작 모드 (Lines 180-184, 212-216)

```bash
# Manager가 없으면 시작
if ! pgrep -f "garame_manager\|python.*main.py" > /dev/null; then
    if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
        nohup ./garame_manager/garame_manager --config config.conf > logs/manager_*.log 2>&1 &
    elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        nohup ./garame_manager --config config.conf > logs/manager_*.log 2>&1 &
    elif [ -f "main.py" ]; then
        nohup python3 main.py --config config.conf > logs/manager_*.log 2>&1 &
    fi
fi
```

##### 3) run_with_watchdog() - Manager 프로그램 시작 (Lines 250-281)

```bash
if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
    log_info "Manager 프로그램 시작 중 (실행 파일 모드 --onedir)..."
    LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"
    nohup ./garame_manager/garame_manager --config config.conf > "$LOG_FILE" 2>&1 &
    MANAGER_PID=$!
    sleep 3

    if pgrep -f "garame_manager" > /dev/null; then
        log_success "Manager 프로그램 시작 완료"
    else
        log_error "Manager 프로그램 시작 실패"
        log_error "로그 파일을 확인하세요: $LOG_FILE"
        tail -n 10 "$LOG_FILE"
    fi
elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
    # --onefile 모드
    ...
elif [ -f "main.py" ]; then
    # Python 모드
    ...
fi
```

##### 4) run_background() - 백그라운드 실행 (Lines 419-426)

```bash
if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
    log_info "실행 파일 모드로 시작 (--onedir)..."
    nohup ./garame_manager/garame_manager > "$LOG_FILE" 2>&1 &
    MANAGER_PID=$!
elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
    log_info "실행 파일 모드로 시작 (--onefile)..."
    nohup ./garame_manager > "$LOG_FILE" 2>&1 &
    MANAGER_PID=$!
elif [ -f "main.py" ]; then
    # Python 모드
    ...
fi
```

##### 5) run_debug() - 디버그 모드 (Lines 464-469)

```bash
if [ -d "garame_manager" ] && [ -f "garame_manager/garame_manager" ]; then
    log_info "실행 파일 모드 (디버그 --onedir)..."
    ./garame_manager/garame_manager
elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
    log_info "실행 파일 모드 (디버그 --onefile)..."
    ./garame_manager
elif [ -f "main.py" ]; then
    # Python 모드
    ...
fi
```

### 디렉토리 구조 비교

#### --onefile 모드 (이전 버전)
```
GARAMe_Manager_1.9.5/
├── garame_manager          # 단일 실행 파일 (4.1GB)
├── run.sh
├── config.conf
└── ...
```

#### --onedir 모드 (현재 버전)
```
GARAMe_Manager_1.9.5/
├── garame_manager/         # 실행 파일 디렉토리 (500MB)
│   ├── garame_manager      # 메인 실행 파일
│   ├── libopencv_*.so      # OpenCV 라이브러리
│   ├── libnumpy_*.so       # NumPy 라이브러리
│   ├── libonnxruntime.so   # ONNX Runtime
│   ├── libtorch_*.so       # PyTorch
│   └── ...                 # 기타 의존성
├── run.sh
├── config.conf
└── ...
```

### 실행 방법

#### 직접 실행
```bash
# --onedir 모드
./garame_manager/garame_manager

# --onefile 모드 (이전 버전)
./garame_manager
```

#### run.sh 사용 (권장)
```bash
# 자동으로 올바른 실행 파일 감지
./run.sh                    # 일반 실행
./run.sh -w                 # Watchdog 모드
./run.sh -b                 # 백그라운드 모드
./run.sh -d                 # 디버그 모드
```

### 장점

1. **88% 크기 감소**: 4.1GB → 500MB
2. **빠른 시작 속도**: 단일 파일 압축 해제 불필요
3. **모듈화된 구조**: 라이브러리 파일 개별 관리 가능
4. **디버깅 용이**: 개별 .so 파일 확인 가능
5. **하위 호환성**: --onefile 모드도 여전히 지원

---

## 3. 설치 가이드

### 요구사항

- **OS**: Ubuntu 25.10 (또는 호환 버전)
- **Python**: 3.11, 3.12, 3.13
- **디스크**: 10GB 이상 여유 공간
- **RAM**: 4GB 이상 권장

### 설치 방법

```bash
# 1. 소스 압축 해제
cd ~/바탕화면
tar -xzf garame_manager_1.9.5.tar.gz
cd garame_manager_1.9.5

# 2. 설치 (Python 3.13 자동 감지 포함)
./install.sh

# 3. PyInstaller 빌드 (선택 - 프롬프트에서 'y' 선택)
# - Python 3.13: NumPy 2.x + OpenCV 4.10+ 자동 설치됨
# - --onedir 모드: ./garame_manager/ 디렉토리 생성

# 4. 실행
./run.sh
```

### 설치 중 출력 예시 (Python 3.13)

```
========================================
  GARAMe Manager v1.9.5
  Ubuntu 25.10 설치 스크립트
========================================

[INFO] Python 패키지 설치 중 (온라인 모드)...
[INFO] GPU 가속을 사용하시겠습니까? (y/n, 기본값: n): n
[INFO] [선택] CPU 모드로 설치합니다.

[INFO] requirements.txt에서 패키지 설치 중...
...

[INFO] Python 버전 호환성 확인 중...
[INFO] Python 버전: 3.13

[INFO] Python 3.13 감지: NumPy 2.x + OpenCV 4.10+ 자동 업그레이드
[INFO] (Python 3.13에서는 ml-dtypes 0.5+ 요구사항으로 NumPy 2.x가 필요합니다)

[INFO]   NumPy 2.x 설치 중...
[INFO]   OpenCV 4.10+ 설치 중...
[INFO]   ml-dtypes 0.5+ 설치 중...

[SUCCESS] Python 3.13 호환 패키지 업그레이드 완료

[INFO] 설치된 버전:
  NumPy: 2.2.6
  OpenCV: 4.12.0.88
  ml-dtypes: 0.5.4

[INFO] ONNX import 테스트 중...
  ✓ ONNX import 성공
[SUCCESS] ONNX 정상 작동

...

[INFO] 실행 파일을 빌드하시겠습니까? (y/n) [기본값: n] y

[INFO] 실행 파일 빌드 중... (5-10분 소요, 기다려주세요)
...
[SUCCESS] 실행 파일 빌드 완료! (--onedir 모드)
[INFO] 빌드 디렉토리 크기: 500M

[SUCCESS] 실행 파일 디렉토리가 생성되었습니다: ./garame_manager/ (크기: 500M)

[INFO] 디렉토리 구조 (--onedir 모드):
  ./garame_manager/           # 실행 파일 디렉토리
  ./garame_manager/garame_manager  # 메인 실행 파일
  ./garame_manager/*.so       # 공유 라이브러리들

[INFO] 실행 방법:
  • ./garame_manager/garame_manager (직접 실행)
  • ./run.sh (권장 - 자동으로 올바른 실행 파일 사용)

[SUCCESS] 빌드 임시 파일 정리 완료

[INFO] 참고: run.sh는 자동으로 garame_manager/ 디렉토리를 인식합니다
```

### 실행 예시

```bash
# run.sh가 자동으로 --onedir 모드 인식
$ ./run.sh

=========================================
  GARAMe Manager v1.9.5
  실행 스크립트
=========================================

[INFO] 가상환경 활성화 중...
[SUCCESS] 가상환경 활성화 완료
[SUCCESS] 환경 변수 설정 완료
[INFO] 프로그램 실행 중...
[INFO] 실행 파일 모드 (--onedir): ./garame_manager/garame_manager

GARAMe Manager v1.9.5 시작...
```

---

## 4. 문제 해결

### Python 3.13 환경에서 ONNX 오류

**증상**:
```
AttributeError: module 'ml_dtypes' has no attribute 'float4_e2m1fn'
```

**해결 방법**:
```bash
# 자동 수정 스크립트 실행 (설치 시 이미 자동 실행됨)
./fix_onnx_deps.sh
```

**또는 수동 설치**:
```bash
source venv/bin/activate
pip install --upgrade "numpy>=2.0.0"
pip uninstall -y opencv-python opencv-contrib-python
pip install "opencv-contrib-python>=4.10.0"
pip install --upgrade "ml-dtypes>=0.5.0"
```

### PyInstaller 빌드가 완료되었으나 실행 파일이 없음

**증상**:
```
[ERROR] 실행 파일 빌드는 완료되었으나 dist/garame_manager/garame_manager를 찾을 수 없습니다
```

**확인 방법**:
```bash
# dist/ 디렉토리 내용 확인
ls -la dist/

# 기대하는 출력 (--onedir 모드)
dist/
└── garame_manager/
    ├── garame_manager
    ├── libopencv_*.so
    └── ...
```

**해결 방법**:
```bash
# 1. OpenCV 재설치
source venv/bin/activate
pip uninstall -y opencv-python opencv-contrib-python
pip install opencv-contrib-python>=4.9.0.80

# 2. check_cv2.sh 실행
./check_cv2.sh

# 3. PyInstaller 재빌드
pyinstaller --clean garame_manager.spec
```

### run.sh가 실행 파일을 찾지 못함

**증상**:
```
[ERROR] 실행 파일(garame_manager) 또는 main.py를 찾을 수 없습니다.
```

**확인 방법**:
```bash
# 디렉토리 구조 확인
ls -la

# --onedir 모드 확인
ls -la garame_manager/
```

**해결 방법**:
```bash
# garame_manager/ 디렉토리가 있으면
chmod +x garame_manager/garame_manager
./run.sh

# 없으면 Python 모드로 실행
source venv/bin/activate
python3 main.py
```

---

## 5. 변경 사항 요약

### install.sh

| 기능 | Before | After |
|-----|--------|-------|
| Python 3.13 호환성 | ❌ 수동 fix_onnx_deps.sh 필요 | ✅ 자동 감지 및 업그레이드 |
| PyInstaller 빌드 확인 | `if [ -f "garame_manager" ]` | `if [ -d "garame_manager" ]` |
| 빌드 결과 이동 | `cp dist/garame_manager ./` | `mv dist/garame_manager ./` |
| 빌드 정리 프롬프트 | ✅ 사용자에게 물어봄 | ❌ 자동 정리 |

### run.sh

| 함수 | 변경 사항 |
|-----|----------|
| `run_normal()` | --onedir 모드 우선 확인 추가 |
| `run_with_watchdog()` | 3곳에 --onedir 모드 지원 추가 |
| `run_background()` | --onedir 모드 지원 추가 |
| `run_debug()` | --onedir 모드 지원 추가 |

### 파일 수정 통계

- **install.sh**: +47 lines, -5 lines
- **run.sh**: +121 lines, -47 lines
- **총**: +168 lines, -52 lines

---

## 6. 테스트 체크리스트

### Python 버전별 테스트

- [ ] **Python 3.11**: NumPy 1.26.4 + OpenCV 4.9.x 유지
- [ ] **Python 3.12**: NumPy 1.26.4 + OpenCV 4.9.x 유지
- [ ] **Python 3.13**: NumPy 2.x + OpenCV 4.10+ 자동 업그레이드
- [ ] **ONNX import**: 모든 Python 버전에서 성공

### PyInstaller 빌드 테스트

- [ ] `pyinstaller --clean garame_manager.spec` 성공
- [ ] `dist/garame_manager/` 디렉토리 생성 확인
- [ ] `dist/garame_manager/garame_manager` 실행 파일 확인
- [ ] `./garame_manager/` 디렉토리로 이동 확인
- [ ] `./garame_manager/garame_manager` 실행 권한 확인

### run.sh 실행 모드 테스트

- [ ] `./run.sh` (일반 모드) 실행
- [ ] `./run.sh -w` (Watchdog 모드) 실행
- [ ] `./run.sh -b` (백그라운드 모드) 실행
- [ ] `./run.sh -d` (디버그 모드) 실행
- [ ] `./run.sh -s` (프로그램 종료) 실행

### 호환성 테스트

- [ ] --onedir 빌드 후 실행
- [ ] --onefile 빌드 후 실행 (이전 버전 호환성)
- [ ] Python 모드 실행 (빌드 없이)

---

## 7. 참고 문서

- [PYTHON313_NUMPY2_GUIDE.md](PYTHON313_NUMPY2_GUIDE.md): Python 3.13 + NumPy 2.x 호환성 가이드
- [BUILD_GUIDE.md](BUILD_GUIDE.md): PyInstaller 빌드 가이드
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): 문제 해결 가이드
- [fix_onnx_deps.sh](fix_onnx_deps.sh): ONNX 의존성 수동 수정 스크립트

---

## 8. 라이센스

GARAMe Manager v1.9.5
Copyright (c) 2024
License: Proprietary

---

**생성일**: 2025-11-19
**버전**: v1.9.5
**작성자**: Claude Code
