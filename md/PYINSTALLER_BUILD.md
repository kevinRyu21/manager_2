# PyInstaller 실행 파일 빌드 가이드

## 개요

GARAMe Manager v1.9.2부터 **PyInstaller**를 사용하여 Python 소스 코드를 단일 실행 파일로 빌드할 수 있습니다.

### 장점

1. **소스 보호**: Python 소스 코드가 실행 파일 내부에 포함되어 직접 노출되지 않음
2. **간편한 실행**: Python 인터프리터 없이도 실행 가능 (가상환경 필요 없음)
3. **플랫폼 호환성**: 각 플랫폼에서 빌드하여 완벽한 호환성 확보
4. **리소스 유지**: 이미지, 설정 파일 등은 원본 그대로 유지

### PyArmor와의 차이

| 항목 | PyArmor | PyInstaller |
|------|---------|-------------|
| 소스 보호 | ⭐⭐⭐⭐⭐ 강력한 암호화 | ⭐⭐⭐ 바이너리 포함 |
| 플랫폼 호환성 | ❌ 플랫폼별 빌드 필요 | ✅ 플랫폼별 빌드 필요 |
| 실행 속도 | ⭐⭐⭐⭐ 약간 느림 | ⭐⭐⭐⭐⭐ 빠름 |
| 라이선스 | 💰 Trial 제한 ($99+) | ✅ 무료 (MIT) |
| 파일 크기 | ⭐⭐⭐⭐⭐ 작음 | ⭐⭐ 큼 (100MB+) |
| 역공학 난이도 | ⭐⭐⭐⭐⭐ 매우 어려움 | ⭐⭐⭐ 중간 |

---

## 빌드 과정

### 1. 설치 시 자동 빌드 (Ubuntu)

**install.sh** 스크립트 실행 시 PyInstaller 빌드를 선택할 수 있습니다:

```bash
cd /path/to/GARAMe_Manager_1.9.2
./install.sh
```

#### 설치 과정:

1. **시스템 패키지 설치**: 필수 패키지 설치
2. **Python 가상환경 설정**: venv 생성 및 패키지 설치
3. **PyInstaller 빌드 확인**: 사용자에게 빌드 여부 확인

```
실행 파일 빌드 (선택 사항)

PyInstaller를 사용하여 Python 소스를 단일 실행 파일로 빌드할 수 있습니다.
실행 파일 빌드 시 장점:
  • 소스 코드가 바이너리로 포함되어 보호됨
  • 가상환경 활성화 없이 실행 가능
  • 약간 빠른 시작 속도

실행 파일 빌드 시 단점:
  • 빌드 시간: 5-10분 소요
  • 파일 크기: 약 100-150MB
  • 추가 디스크 공간 필요: 약 1-2GB

실행 파일을 빌드하시겠습니까? (y/n) [기본값: n]
```

4. **자동 PyInstaller 설치**: 미설치 시 자동 설치
5. **실행 파일 빌드**: garame_manager 생성
6. **빌드 파일 정리**: 임시 파일 삭제 여부 확인

#### 빌드 결과:

```bash
# 성공 시
./garame_manager  # 실행 파일 (100-150MB)
./run.sh          # 자동으로 garame_manager 사용
```

### 2. 배포 패키지 생성 시 자동 빌드 (Ubuntu)

**create_distribution.sh** 스크립트가 자동으로 PyInstaller 빌드를 수행합니다:

```bash
cd /path/to/GARAMe_Manager_1.9.2
./create_distribution.sh
```

#### 배포 빌드 과정:

1. **플랫폼 확인**: Linux(Ubuntu)에서만 빌드 진행
2. **가상환경 활성화**: 자동 활성화
3. **PyInstaller 설치 확인**: 없으면 자동 설치 (`pip install pyinstaller`)
4. **garame_manager.spec 파일 사용**: 빌드 설정 로드
5. **실행 파일 생성**: `dist/garame_manager` 생성
6. **배포 디렉토리에 복사**: 실행 파일을 배포 패키지에 포함

#### macOS에서 실행 시:

```
[WARNING] 현재 시스템은 Darwin입니다. PyInstaller 빌드는 Ubuntu에서만 지원됩니다.
[INFO] 원본 소스 파일을 복사합니다...
```

- macOS에서는 빌드를 건너뛰고 원본 소스 복사
- Ubuntu에서 배포 스크립트를 실행해야 실행 파일 빌드

---

## garame_manager.spec 파일

### 파일 구조

```python
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 데이터 파일 수집
datas = [
    ('VERSION.txt', '.'),
]

# Hidden imports
hiddenimports = [
    'PIL', 'tkinter', 'numpy', 'cv2', 'matplotlib',
    'pyttsx3', 'face_recognition', 'dlib',
    'easyocr', 'paddleocr',
]

# src 모듈 수집
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('src.tcp_monitor')

# 실행 파일 설정
exe = EXE(
    ...
    name='garame_manager',
    console=True,  # 콘솔 출력 활성화
    upx=True,      # UPX 압축
)
```

### 주요 설정

1. **datas**: 실행 파일에 포함할 데이터 파일
   - VERSION.txt (버전 정보)
   - EasyOCR, PaddleOCR 데이터 (자동 수집)

2. **hiddenimports**: 동적 import되는 모듈
   - GUI: tkinter, PIL
   - 데이터: numpy, cv2, matplotlib
   - 얼굴인식: face_recognition, dlib
   - OCR: easyocr, paddleocr
   - TTS: pyttsx3

3. **excludes**: 불필요한 모듈 제외
   - PyQt5, PyQt6, PySide2, PySide6
   - wx, django, flask, tornado

4. **UPX 압축**: 파일 크기 감소 (약 30-50%)

---

## 빌드 결과

### 배포 패키지 구조

```
GARAMe_Manager_1.9.2_Ubuntu25_Distribution/
├── garame_manager          # 실행 파일 (100MB+)
├── garame_manager.spec     # 빌드 설정 (참고용)
├── assets/                 # 이미지 리소스
│   ├── GARAMe.png
│   ├── GARAMe1.png
│   ├── logo.ico
│   ├── logo.png
│   └── uplus.png
├── safety_posters/         # 안전 포스터
├── safety_photos/          # 안전 사진
├── config.conf.example     # 설정 예제
├── standard_defaults.conf  # 기본 설정
├── install.sh              # 설치 스크립트
├── run.sh                  # 실행 스크립트
├── VERSION.txt             # 버전 정보
└── README.md               # 설명서
```

### 파일 크기

| 항목 | 크기 |
|------|------|
| garame_manager (실행 파일) | 100-150MB |
| assets/ | ~1MB |
| safety_posters/ | ~10MB |
| 기타 설정/문서 | ~1MB |
| **전체 (압축 전)** | **~120MB** |
| **전체 (tar.gz)** | **~50-60MB** |

---

## 실행 방법

### 1. 일반 실행

```bash
./run.sh
```

**run.sh**가 자동으로 실행 파일 우선 사용:

```bash
# PyInstaller 빌드 실행 파일이 있으면 우선 사용
if [ -f "garame_manager" ]; then
    log_info "실행 파일 모드: ./garame_manager"
    ./garame_manager "$@"
# 없으면 Python으로 실행
elif [ -f "main.py" ]; then
    log_info "Python 모드: python3 main.py"
    python3 main.py "$@"
fi
```

### 2. 직접 실행

```bash
# 실행 파일 직접 실행
./garame_manager

# 또는 설정 파일 지정
./garame_manager --config config.conf
```

### 3. Watchdog 모드

```bash
./run.sh -w
# 또는
./run.sh --watchdog
```

### 4. 백그라운드 모드

```bash
./run.sh -b
# 또는
./run.sh --background
```

---

## 설치 과정

### Ubuntu 25.10에서 설치

#### 1. 배포 패키지 압축 해제

```bash
tar -xzf GARAMe_Manager_1.9.2_Ubuntu25_Distribution.tar.gz
cd GARAMe_Manager_1.9.2_Ubuntu25_Distribution
```

#### 2. 설치 스크립트 실행

```bash
./install.sh
```

**설치 중 실행 파일 빌드 선택**:
- `y` 선택: PyInstaller로 실행 파일 빌드 (권장)
  - PyInstaller 자동 설치
  - 5-10분 소요
  - 소스 보호 + 빠른 실행

- `n` 선택: Python 소스 모드
  - 빠른 설치
  - 가상환경 필요

#### 3. 실행

```bash
./run.sh
```

**자동 모드 선택**:
- 실행 파일이 있으면: `./garame_manager` 실행
- 없으면: `python3 main.py` 실행 (가상환경 자동 활성화)

---

## 트러블슈팅

### 문제 1: 실행 파일이 없음

**증상**:
```
[INFO] Python 모드: python3 main.py
```

**원인**:
- macOS에서 배포 스크립트 실행
- Ubuntu에서 빌드 실패

**해결**:
```bash
# Ubuntu에서 수동 빌드
cd /path/to/GARAMe_Manager_1.9.2
source venv/bin/activate
pip install pyinstaller
pyinstaller garame_manager.spec

# 생성된 실행 파일 확인
ls -lh dist/garame_manager
```

### 문제 2: ImportError 발생

**증상**:
```
ImportError: No module named 'xxx'
```

**원인**: hiddenimports에 누락된 모듈

**해결**: garame_manager.spec 수정
```python
hiddenimports = [
    # 기존 모듈...
    'xxx',  # 누락된 모듈 추가
]
```

재빌드:
```bash
pyinstaller --clean garame_manager.spec
```

### 문제 3: 실행 파일이 너무 큼

**증상**: garame_manager 파일이 200MB 이상

**해결**:
```bash
# UPX 압축 활성화 확인 (garame_manager.spec)
exe = EXE(
    ...
    upx=True,  # ← 이 옵션 확인
)

# UPX 설치 (없는 경우)
sudo apt install upx-ucl

# 재빌드
pyinstaller --clean garame_manager.spec
```

### 문제 4: 권한 오류

**증상**:
```
Permission denied: ./garame_manager
```

**해결**:
```bash
chmod +x garame_manager
./garame_manager
```

### 문제 5: 라이브러리 충돌

**증상**:
```
version `GLIBC_X.XX' not found
```

**원인**: 다른 Ubuntu 버전에서 빌드한 실행 파일

**해결**: 대상 시스템에서 직접 빌드
```bash
# Ubuntu 25.10에서 빌드
./create_distribution.sh
```

---

## 성능 비교

### 실행 속도

| 모드 | 시작 시간 | 메모리 사용 |
|------|----------|------------|
| Python | ~3-5초 | ~200MB |
| PyInstaller | ~2-3초 | ~250MB |

### 디스크 사용량

| 모드 | 디스크 사용 |
|------|------------|
| Python 소스 + venv | ~2GB |
| PyInstaller 실행 파일 | ~150MB |

---

## 보안 고려사항

### PyInstaller 보안 수준

1. **기본 보호**: 소스 코드가 바이너리로 컴파일되어 텍스트 에디터로 볼 수 없음
2. **역공학 가능**: pyinstxtractor 등의 도구로 추출 가능
3. **추가 보호 필요**: 중요한 로직은 추가 암호화 필요

### 추가 보호 방법

#### 1. UPX 압축
```python
exe = EXE(
    ...
    upx=True,  # UPX 압축으로 추출 난이도 증가
)
```

#### 2. Strip 심볼
```python
exe = EXE(
    ...
    strip=True,  # 디버그 심볼 제거
)
```

#### 3. 중요 데이터 암호화
```python
# config.conf, 데이터베이스 등은 별도 암호화
import cryptography.fernet

key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"sensitive data")
```

---

## FAQ

### Q1: macOS에서 빌드한 실행 파일을 Ubuntu에서 사용할 수 있나요?

**A**: 아니요. PyInstaller는 플랫폼별로 빌드해야 합니다.
- macOS 빌드 → macOS에서만 실행
- Ubuntu 빌드 → Ubuntu에서만 실행

### Q2: 실행 파일과 Python 소스를 함께 배포할 수 있나요?

**A**: 네, 가능합니다. run.sh가 자동으로 실행 파일 우선 사용:
```bash
if [ -f "garame_manager" ]; then
    ./garame_manager  # 실행 파일 우선
elif [ -f "main.py" ]; then
    python3 main.py   # 없으면 Python
fi
```

### Q3: 실행 파일 크기를 줄일 수 있나요?

**A**: 네, 여러 방법이 있습니다:
1. UPX 압축 활성화 (upx=True)
2. 불필요한 모듈 제외 (excludes 리스트)
3. onefile 대신 onedir 사용 (초기 압축 풀기 시간 단축)

### Q4: 가상환경이 필요한가요?

**A**:
- **PyInstaller 빌드 시**: 네, 필요합니다
- **실행 파일 실행 시**: 아니요, 불필요합니다

### Q5: 실행 파일에 설정 파일도 포함되나요?

**A**: 아니요. 다음은 실행 파일 외부에 유지됩니다:
- config.conf (설정)
- assets/ (이미지)
- safety_posters/, safety_photos/ (리소스)
- logs/ (로그)

---

## 버전별 변경사항

### v1.9.2 (2025-11-11)

- ✅ PyInstaller 빌드 기능 추가
- ✅ garame_manager.spec 파일 생성
- ✅ create_distribution.sh에 자동 빌드 통합
- ✅ run.sh에 실행 파일 우선 사용 로직 추가
- ✅ Ubuntu 전용 빌드 (플랫폼 체크)

### v1.9.1 이전

- ❌ PyInstaller 빌드 기능 없음
- 원본 소스 배포만 지원

---

## 관련 문서

- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - 설치 가이드
- [PYARMOR_LICENSE_ISSUE.md](PYARMOR_LICENSE_ISSUE.md) - PyArmor 암호화 이슈
- [VERSION_1.9.2_CHANGES.md](VERSION_1.9.2_CHANGES.md) - v1.9.2 변경사항
- [DISK_CLEANUP_FEATURE.md](DISK_CLEANUP_FEATURE.md) - 디스크 정리 기능

---

## 참고 링크

- **PyInstaller 공식 문서**: https://pyinstaller.org/
- **PyInstaller GitHub**: https://github.com/pyinstaller/pyinstaller
- **UPX 압축**: https://upx.github.io/
