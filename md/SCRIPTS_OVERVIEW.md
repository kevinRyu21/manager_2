# GARAMe Manager 1.9.1 - 스크립트 개요

이 문서는 GARAMe Manager v1.9.1의 모든 스크립트와 사용 방법을 정리한 참고 자료입니다.

## 📋 목차
- [설치 스크립트](#설치-스크립트)
- [실행 스크립트](#실행-스크립트)
- [보안 빌드 스크립트](#보안-빌드-스크립트)
- [시스템 설정 스크립트](#시스템-설정-스크립트)
- [유틸리티 스크립트](#유틸리티-스크립트)
- [빠른 참조](#빠른-참조)

---

## 설치 스크립트

### install.sh ⭐ 통합 설치 스크립트
**용도**: GARAMe Manager 전체 설치 및 환경 설정

**기능**:
- 시스템 패키지 자동 설치 (Python, OpenCV, 빌드 도구)
- 한글 폰트 자동 설치
- Python 가상환경 생성
- Python 패키지 설치 (온라인/오프라인 선택)
- 얼굴 인식 라이브러리 설치 (dlib, face-recognition)
- 문자 인식 라이브러리 설치 (Tesseract OCR)
- 시스템 설정 최적화 (화면 보호기, 절전, 알림 비활성화)
- 설정 파일 및 데이터 디렉토리 생성

**사용법**:
```bash
chmod +x install.sh
./install.sh
```

**옵션**:
- 온라인 설치 (y) - 인터넷에서 패키지 다운로드
- 오프라인 설치 (n) - 로컬 wheels 디렉토리에서 설치
- 시스템 최적화 (y/n) - 화면 보호기 등 비활성화
- 자동 시작 설정 (y/n)

**관련 문서**: [README_INSTALL.md](README_INSTALL.md)

---

### install_korean_font.sh
**용도**: 한글 폰트 설치 (install.sh에서 자동 호출됨)

**기능**:
- 나눔 폰트 설치 (필수)
- 추가 나눔 폰트 설치 (선택)

**사용법**:
```bash
./install_korean_font.sh
```

**관련 문서**: [KOREAN_FONT_INSTALL.md](KOREAN_FONT_INSTALL.md)

---

## 실행 스크립트

### run.sh ⭐ 통합 실행 스크립트
**용도**: GARAMe Manager 실행 (다양한 모드 지원)

**사용법**:
```bash
# 일반 모드
./run.sh

# Watchdog 모드 (자동 재시작)
./run.sh -w

# 백그라운드 모드
./run.sh -b

# 디버그 모드
./run.sh -d

# 중지
./run.sh -s

# 도움말
./run.sh -h
```

**옵션**:
- `-w, --watchdog` - Watchdog 모드 (크래시 시 자동 재시작)
- `-b, --background` - 백그라운드 실행
- `-d, --debug` - 디버그 모드 (자세한 로그)
- `-s, --stop` - 프로그램 중지
- `-h, --help` - 도움말 표시

**관련 문서**: [README_INSTALL.md](README_INSTALL.md)

---

## 보안 빌드 스크립트

### build_secure.sh ⭐ Cython 보안 빌드
**용도**: Python 소스코드를 C 확장 모듈(.so)로 컴파일하여 보호

**기능**:
- Cython 자동 설치
- 원본 소스코드 자동 백업 (타임스탬프 포함)
- .py → .so 컴파일
- 원본 .py 파일 삭제 (선택)
- 중간 파일 자동 정리 (.c, build/)
- 컴파일 보고서 생성

**사용법**:
```bash
./build_secure.sh
```

**실행 과정**:
1. 가상환경 활성화
2. Cython 설치 확인/설치
3. 기존 빌드 파일 정리
4. 원본 백업 생성 (`backup_original_YYYYMMDD_HHMMSS/`)
5. Cython 컴파일 실행
6. .py 파일 삭제 여부 확인 (사용자 입력: "yes")
7. 중간 파일 정리
8. 보고서 생성 (`compilation_report_YYYYMMDD_HHMMSS.txt`)

**출력 파일**:
- `backup_original_YYYYMMDD_HHMMSS/` - 원본 백업
- `*.so` - 컴파일된 바이너리 파일
- `compilation_report_*.txt` - 컴파일 보고서

**관련 문서**:
- [CYTHON_README.md](CYTHON_README.md) - 빠른 가이드
- [CYTHON_BUILD_GUIDE.md](CYTHON_BUILD_GUIDE.md) - 완벽 가이드

---

### setup_cython.py
**용도**: Cython 컴파일 설정 (build_secure.sh에서 자동 호출됨)

**기능**:
- 컴파일할 Python 파일 자동 검색
- Extension 모듈 생성
- 컴파일러 지시어 설정 (보안 + 성능)

**수동 사용법** (고급):
```bash
source venv/bin/activate
python3 setup_cython.py build_ext --inplace
```

**컴파일러 옵션**:
```python
compiler_directives = {
    'language_level': "3",           # Python 3
    'embedsignature': False,         # 디버그 정보 제거
    'boundscheck': False,            # 성능 향상
    'wraparound': False,             # 성능 향상
    'cdivision': True,               # C 나눗셈
}
```

**제외 패턴**:
- `test_*` - 테스트 파일
- `setup*` - 설정 스크립트
- `build` - 빌드 디렉토리

---

### restore_backup.sh
**용도**: Cython 컴파일 전 원본 소스코드 복구

**기능**:
- 사용 가능한 백업 목록 표시
- 선택적 백업 복구
- .so 파일 자동 삭제
- .c 파일 자동 삭제
- build 디렉토리 정리

**사용법**:
```bash
./restore_backup.sh
```

**실행 과정**:
1. 백업 디렉토리 검색
2. 백업 목록 표시
3. 복구할 백업 선택
4. 확인 (사용자 입력: "yes")
5. .so, .c 파일 삭제
6. 원본 .py 파일 복구

---

## 시스템 설정 스크립트

### setup_autostart.sh
**용도**: 부팅/로그인 시 GARAMe Manager 자동 시작 설정

**기능**:
- 사용자 자동 시작 설정
- systemd 시스템 서비스 설정
- systemd 사용자 서비스 설정

**사용법**:
```bash
./setup_autostart.sh
```

**옵션 선택**:
1. **사용자 자동 시작** (권장) - `~/.config/autostart/`에 .desktop 파일 생성
2. **systemd 시스템 서비스** - 부팅 시 자동 실행
3. **systemd 사용자 서비스** - 로그인 시 자동 실행

**제거 방법**:
- 옵션 1: `rm ~/.config/autostart/garame-manager.desktop`
- 옵션 2: `sudo systemctl disable garame-manager.service`
- 옵션 3: `systemctl --user disable garame-manager.service`

---

## 유틸리티 스크립트

### check_dependencies.py
**용도**: 의존성 패키지 확인

**사용법**:
```bash
source venv/bin/activate
python3 check_dependencies.py
```

---

## 빠른 참조

### 🚀 첫 설치 (3단계)
```bash
cd 1.9.1
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### 🔒 보안 빌드 (배포용)
```bash
./build_secure.sh
# .py 삭제 확인: yes
./run.sh  # 테스트
```

### 🔄 백업 복구
```bash
./restore_backup.sh
# 백업 선택: 0
# 확인: yes
```

### ⚙️ 자동 시작 설정
```bash
./setup_autostart.sh
# 옵션 선택: 1 (사용자 자동 시작)
```

### 📊 상태 확인
```bash
# 가상환경 확인
ls -la venv/

# .so 파일 확인
find . -name "*.so" -type f

# 백업 확인
ls -la backup_original_*/

# 실행 중인 프로세스 확인
ps aux | grep garame
```

---

## 스크립트 의존성 다이어그램

```
install.sh
  ├─> install_korean_font.sh
  ├─> setup_autostart.sh (선택)
  └─> optimize_system_settings() (내부 함수)

run.sh
  └─> venv/bin/activate

build_secure.sh
  ├─> venv/bin/activate
  └─> setup_cython.py

restore_backup.sh
  └─> (독립적)

setup_autostart.sh
  └─> (독립적)
```

---

## 파일 구조 (스크립트 관련)

```
1.9.1/
├── install.sh                    # 통합 설치
├── run.sh                        # 통합 실행
├── setup_autostart.sh            # 자동 시작 설정
├── install_korean_font.sh        # 한글 폰트 설치
│
├── build_secure.sh               # Cython 빌드
├── setup_cython.py               # Cython 설정
├── restore_backup.sh             # 백업 복구
│
├── check_dependencies.py         # 의존성 확인
│
├── README_INSTALL.md             # 설치 가이드
├── UBUNTU_INSTALLATION_GUIDE.md  # Ubuntu 설치 가이드
├── CYTHON_README.md              # Cython 빠른 가이드
├── CYTHON_BUILD_GUIDE.md         # Cython 완벽 가이드
└── SCRIPTS_OVERVIEW.md           # 이 문서
```

---

## 문제 해결 체크리스트

### 설치 실패
```bash
# 1. 시스템 패키지 수동 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 2. 권한 확인
chmod +x install.sh run.sh

# 3. 로그 확인
./install.sh 2>&1 | tee install.log
```

### 실행 실패
```bash
# 1. 가상환경 확인
source venv/bin/activate
python3 --version

# 2. 의존성 확인
python3 check_dependencies.py

# 3. 디버그 모드
./run.sh -d
```

### Cython 컴파일 실패
```bash
# 1. 빌드 도구 설치
sudo apt install -y build-essential python3-dev

# 2. Cython 재설치
source venv/bin/activate
pip install --upgrade Cython

# 3. 수동 컴파일 테스트
python3 setup_cython.py build_ext --inplace
```

---

## 추가 리소스

### 문서
- [VERSION_1.9.1_CHANGES.md](VERSION_1.9.1_CHANGES.md) - 버전 변경 사항
- [KOREAN_FONT_INSTALL.md](KOREAN_FONT_INSTALL.md) - 한글 폰트 가이드
- [BACKGROUND_LEARNING_FEATURE.md](BACKGROUND_LEARNING_FEATURE.md) - 배경 학습 기능

### 디렉토리
- `src/` - Python 소스코드
- `venv/` - Python 가상환경
- `backup_original_*/` - 원본 백업
- `wheels/` - 오프라인 설치용 패키지

---

## 라이선스

Copyright © 2025 GARAMe Project

---

**버전**: 1.9.1
**최종 업데이트**: 2025-11-06
