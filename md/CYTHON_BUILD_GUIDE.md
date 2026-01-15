# Cython 컴파일 가이드 - 소스코드 보호

GARAMe Manager를 Cython으로 컴파일하여 소스코드를 보호하는 방법을 설명합니다.

## 목차
- [Cython이란?](#cython이란)
- [왜 Cython을 사용하나?](#왜-cython을-사용하나)
- [빌드 과정](#빌드-과정)
- [사용 방법](#사용-방법)
- [문제 해결](#문제-해결)
- [성능 및 보안](#성능-및-보안)

## Cython이란?

**Cython**은 Python 코드를 C 확장 모듈(.so 파일)로 컴파일하는 도구입니다.

### 일반 Python 배포
```
main.py (소스코드 노출)
  ↓
사용자가 텍스트 에디터로 열어서 볼 수 있음
```

### Cython 컴파일 배포
```
main.py
  ↓ Cython 컴파일
main.cpython-310-x86_64-linux-gnu.so (바이너리)
  ↓
역컴파일이 거의 불가능한 기계어 수준의 보호
```

## 왜 Cython을 사용하나?

### 1. 소스코드 보호 🔒
- Python .py 파일은 텍스트 파일로 누구나 읽을 수 있음
- Cython .so 파일은 바이너리로 역컴파일이 매우 어려움
- 알고리즘과 비즈니스 로직 보호

### 2. 무료 솔루션 💰
- **Cython**: 완전 무료, 오픈소스
- **PyArmor**: $69/년 (상업용)
- **기타 상용 도구**: 수십만원~수백만원

### 3. 성능 향상 ⚡
- C 수준으로 최적화됨
- 10-30% 성능 향상 (경우에 따라 더 높음)
- 메모리 사용량 감소

### 4. 배포 용이성 📦
- .so 파일만 배포하면 됨
- .py 파일 삭제 가능
- 패키지 크기 감소

## 빌드 과정

### 단계별 프로세스

```
1. 원본 백업
   ├─ src/**/*.py
   ├─ main.py
   └─ watchdog.py
      ↓
2. Cython 컴파일
   ├─ .py → .c (중간 단계)
   └─ .c → .so (최종 바이너리)
      ↓
3. 원본 .py 삭제 (선택)
      ↓
4. 중간 파일 정리
   └─ .c 파일 삭제
      ↓
5. 배포용 패키지 완성
```

### 컴파일 옵션

[setup_cython.py](setup_cython.py)의 컴파일러 지시어:

```python
compiler_directives = {
    'language_level': "3",           # Python 3 사용
    'embedsignature': False,         # 디버그 정보 제거 (보안)
    'boundscheck': False,            # 배열 경계 검사 비활성화 (성능)
    'wraparound': False,             # 음수 인덱스 비활성화 (성능)
    'initializedcheck': False,       # 초기화 검사 비활성화 (성능)
    'cdivision': True,               # C 나눗셈 사용 (성능)
    'always_allow_keywords': False,  # 키워드 인자 비활성화 (성능)
}
```

**보안 최적화**:
- `embedsignature: False` - 함수 서명 정보 제거
- 디버그 정보 완전 제거
- 소스코드 경로 노출 방지

**성능 최적화**:
- `boundscheck: False` - 배열 접근 속도 향상
- `cdivision: True` - C 수준 나눗셈
- `wraparound: False` - 인덱스 처리 최적화

## 사용 방법

### 1. 빠른 시작

```bash
cd 1.9.1

# Cython 컴파일 실행
./build_secure.sh
```

**실행 과정**:
1. Cython 자동 설치
2. 원본 백업 생성
3. 전체 컴파일
4. .py 파일 삭제 여부 선택
5. 보고서 생성

### 2. 단계별 실행

#### 2.1. 백업 확인
```bash
ls -la backup_original_*
```

#### 2.2. 컴파일만 실행 (삭제 안 함)
```bash
source venv/bin/activate
python3 setup_cython.py build_ext --inplace
```

#### 2.3. .so 파일 확인
```bash
find . -name "*.so" -type f
```

#### 2.4. 테스트 실행
```bash
./run.sh
```

#### 2.5. 문제 없으면 .py 삭제
```bash
# src 디렉토리의 .py 파일 삭제 (__init__.py 제외)
find src -name "*.py" -type f ! -name "__init__.py" -delete

# watchdog.py 삭제
rm -f watchdog.py
```

### 3. 백업 복구

실수로 삭제했거나 수정이 필요한 경우:

```bash
./restore_backup.sh
```

**복구 과정**:
1. 사용 가능한 백업 목록 표시
2. 복구할 백업 선택
3. .so 파일 삭제
4. 원본 .py 파일 복구

## 주의사항

### ⚠️ 반드시 백업하세요

```bash
# 백업 디렉토리는 절대 삭제하지 마세요!
backup_original_20250106_143022/
```

**이유**:
- .so 파일은 수정 불가능
- 버그 수정이나 기능 추가 시 원본 필요
- .so → .py 역컴파일은 거의 불가능

### ⚠️ 엔트리포인트 파일

**main.py는 상황에 따라 유지해야 할 수 있습니다**

일부 시스템에서는:
```bash
python3 main.cpython-310-x86_64-linux-gnu.so  # 작동 안 함
```

대안:
1. main.py를 간단한 래퍼로 유지
2. run.sh에서 .so 파일 직접 실행
3. main.py를 난독화만 적용

### ⚠️ __init__.py 유지

```bash
# __init__.py는 삭제하면 안 됨!
src/tcp_monitor/__init__.py
```

**이유**:
- Python 패키지 구조 유지
- import 문 작동에 필수
- 빈 파일이어도 필요

### ⚠️ 플랫폼 종속성

**컴파일된 .so 파일은 플랫폼별로 다릅니다**:

```
Linux x86_64:   main.cpython-310-x86_64-linux-gnu.so
Linux ARM:      main.cpython-310-aarch64-linux-gnu.so
macOS x86_64:   main.cpython-310-darwin.so
macOS ARM:      main.cpython-310-arm64-darwin.so
Windows:        main.cp310-win_amd64.pyd
```

**배포 시 주의**:
- Ubuntu 25 x64에서 컴파일 → Ubuntu 25 x64에서만 작동
- 다른 플랫폼 지원 시 각각 컴파일 필요
- Python 버전도 정확히 일치해야 함 (3.10, 3.11 등)

## 파일 구조

### 컴파일 전
```
1.9.1/
├── main.py                    # 엔트리포인트
├── watchdog.py                # 와치독
├── src/
│   └── tcp_monitor/
│       ├── __init__.py
│       ├── sensor/
│       │   ├── safety_detector.py
│       │   └── ...
│       └── ui/
│           ├── app.py
│           └── ...
└── venv/
```

### 컴파일 후
```
1.9.1/
├── main.py                    # 엔트리포인트 (선택적 유지)
├── watchdog.cpython-310-x86_64-linux-gnu.so  # 컴파일됨
├── src/
│   └── tcp_monitor/
│       ├── __init__.py        # 유지됨 (필수)
│       ├── sensor/
│       │   ├── __init__.py
│       │   ├── safety_detector.cpython-310-x86_64-linux-gnu.so
│       │   └── ...
│       └── ui/
│           ├── __init__.py
│           ├── app.cpython-310-x86_64-linux-gnu.so
│           └── ...
├── backup_original_20250106_143022/  # 백업 (보관 필수!)
│   ├── main.py
│   ├── watchdog.py
│   └── src/
└── venv/
```

## 성능 및 보안

### 보안 수준

| 방법 | 보호 수준 | 비용 | 역컴파일 난이도 |
|------|----------|------|----------------|
| .py 파일 | ⭐ 없음 | 무료 | 즉시 가능 |
| .pyc 파일 | ⭐⭐ 낮음 | 무료 | 쉬움 (도구 존재) |
| Cython .so | ⭐⭐⭐⭐ 높음 | 무료 | 매우 어려움 |
| PyArmor | ⭐⭐⭐⭐⭐ 매우 높음 | $69/년 | 거의 불가능 |

### Cython 역컴파일 시도 시

```bash
$ strings main.cpython-310-x86_64-linux-gnu.so | less
# 출력: 기계어 코드, 의미 없는 문자열
# Python 로직 파악 거의 불가능
```

**공격자가 볼 수 있는 것**:
- 일부 문자열 리터럴 (예: "Error", "Success")
- 함수 이름 일부 (embedsignature=False로 최소화)
- C 라이브러리 호출

**공격자가 볼 수 없는 것**:
- Python 소스코드
- 알고리즘 로직
- 제어 흐름 (if/else, 루프 등)
- 비즈니스 로직

### 성능 향상

**예상 성능 개선**:
- CPU 집약적 코드: 20-50% 향상
- 일반 코드: 10-30% 향상
- I/O 집약적 코드: 5-15% 향상

**GARAMe Manager 주요 모듈**:
- `safety_detector.py`: 이미지 처리 (30% 향상 예상)
- `face_recognition`: 얼굴 인식 (20% 향상 예상)
- `ui/app.py`: GUI 코드 (10% 향상 예상)

## 문제 해결

### 1. 컴파일 실패

**증상**:
```
error: command 'gcc' failed
```

**해결**:
```bash
# 빌드 도구 설치
sudo apt install -y build-essential python3-dev
```

### 2. import 오류

**증상**:
```python
ModuleNotFoundError: No module named 'tcp_monitor.sensor.safety_detector'
```

**해결**:
```bash
# __init__.py 파일 확인
ls -la src/tcp_monitor/__init__.py
ls -la src/tcp_monitor/sensor/__init__.py

# 없으면 생성
touch src/tcp_monitor/__init__.py
touch src/tcp_monitor/sensor/__init__.py
```

### 3. .so 파일 실행 안 됨

**증상**:
```bash
$ python3 main.cpython-310-x86_64-linux-gnu.so
python3: can't open file 'main.cpython-310-x86_64-linux-gnu.so'
```

**해결**:
```python
# main.py를 간단한 래퍼로 유지
from tcp_monitor.ui.app import main
if __name__ == "__main__":
    main()
```

### 4. 백업 복구

**증상**:
- 실수로 .py 파일 삭제
- 수정 필요

**해결**:
```bash
./restore_backup.sh
```

## 추가 최적화

### 1. 선택적 컴파일

일부 파일만 컴파일하고 싶은 경우 [setup_cython.py](setup_cython.py) 수정:

```python
# 제외할 파일들 추가
exclude_patterns = [
    "test_",
    "setup",
    "build",
    "config",      # 설정 파일 제외
    "constants",   # 상수 파일 제외
]
```

### 2. 최대 보안 모드

더 강력한 보안이 필요한 경우:

```python
compiler_directives = {
    'language_level': "3",
    'embedsignature': False,
    'boundscheck': False,
    'wraparound': False,
    'initializedcheck': False,
    'cdivision': True,
    'always_allow_keywords': False,
    'profile': False,            # 프로파일링 비활성화
    'linetrace': False,          # 라인 추적 비활성화
}
```

### 3. 최대 성능 모드

속도가 최우선인 경우:

```python
ext = Extension(
    module_name,
    [py_file],
    extra_compile_args=["-O3", "-march=native"],  # CPU 최적화
)
```

**주의**: `-march=native`는 현재 CPU에 최적화되지만 다른 CPU에서 작동 안 할 수 있음

## 배포 체크리스트

### 배포 전 확인사항

- [ ] `./build_secure.sh` 실행 완료
- [ ] 백업 디렉토리 생성 확인
- [ ] .so 파일 생성 확인 (`find . -name "*.so"`)
- [ ] `./run.sh`로 정상 작동 확인
- [ ] 모든 기능 테스트 완료
- [ ] 백업을 안전한 곳에 보관
- [ ] compilation_report 확인

### 배포 패키지 구성

```
배포용/
├── 1.9.1/
│   ├── main.py (래퍼)
│   ├── run.sh
│   ├── install.sh
│   ├── src/ (.so 파일들)
│   └── venv/ (선택)
└── README.txt
```

## 라이선스 및 법적 고지

Cython은 Apache License 2.0로 배포되며 상업적 사용이 가능합니다.

**주의사항**:
- 컴파일된 코드도 원본 라이선스를 따릅니다
- GPL 라이브러리 사용 시 주의 필요
- 고객에게 라이선스 정보 제공 권장

## 참고 문서

- [setup_cython.py](setup_cython.py) - Cython 컴파일 설정
- [build_secure.sh](build_secure.sh) - 보안 빌드 스크립트
- [restore_backup.sh](restore_backup.sh) - 백업 복구 스크립트
- [README_INSTALL.md](README_INSTALL.md) - 설치 가이드
- [VERSION_1.9.1_CHANGES.md](VERSION_1.9.1_CHANGES.md) - 버전 변경사항

## 외부 리소스

- [Cython 공식 문서](https://cython.readthedocs.io/)
- [Cython 성능 최적화 가이드](https://cython.readthedocs.io/en/latest/src/userguide/pyrex_differences.html)

---

Copyright © 2025 GARAMe Project
