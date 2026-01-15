# 리눅스/윈도우 동시 실행 관련 파일 목록

이 문서는 v1.8.4에서 리눅스(Ubuntu)와 윈도우에서 동시 실행 가능하도록 수정한 파일들의 목록입니다.

## 새로 추가된 파일

### 1. Ubuntu 실행 스크립트
- **`run_ubuntu.sh`**
  - Ubuntu에서 한 줄로 설치 및 실행하는 스크립트
  - 가상환경 생성, 시스템 패키지 설치, Python 의존성 설치, 카메라 권한 설정 포함
  - **경로 하드코딩 제거**: 스크립트 위치 기반 자동 감지, 홈 디렉토리 기반 venv 경로

### 2. Ubuntu 설치 가이드
- **`UBUNTU_INSTALL_GUIDE.md`**
  - Ubuntu 22.04+/24.04+에서의 설치 및 실행 방법 가이드
  - 빠른 시작, 스크립트 설명, 수동 설치 방법, 문제 해결 포함

### 3. 크로스 플랫폼 지원 스크립트
- **`sitecustomize.py`**
  - Linux에서 Windows 전용 ctypes 심볼 접근 시 에러 방지용 fallback 제공

## 크로스 플랫폼 코드 수정 파일

### 1. 메인 애플리케이션 (UI 핵심)
- **`src/tcp_monitor/ui/app.py`**
  - **Windows/Linux 구분 추가**: `IS_WINDOWS`, `IS_LINUX` 플래그
  - **ctypes 가드**: `ctypes.windll` 등 Windows 전용 심볼 import 가드 처리
  - **시스템 메시지 차단**: `_patch_messagebox()` 전역 메시지박스 차단/자동응답
  - **시스템 Toplevel 자동 닫기**: `_suppress_system_toplevels()` 루프
  - **화상키보드 OS별 처리**: Windows(OSK/TabTip), Linux(onboard/florence) 분기
  - **팝업 높이 확대**: 모든 다이얼로그 높이 +10% 확대
  - **팝업 포커스 강제**: `-topmost`, `lift()`, `focus_force()`, `grab_set()` 적용
  - **안전교육/도면 메뉴**: 센서 접속 없이도 사용 가능하도록 제한 해제

### 2. 안전교육 (카메라)
- **`src/tcp_monitor/ui/safety_education.py`**
  - **OS 감지**: `platform.system()` 사용하여 Windows/Linux 구분
  - **카메라 백엔드 OS별 처리**: 
    - Windows: `cv2.CAP_DSHOW` (DirectShow)
    - Linux: `cv2.CAP_V4L2` (Video4Linux2)
  - **재시도 로직**: 1차 실패 시 기본 백엔드 → Linux에서 V4L2 명시 재시도
  - **팝업 높이 확대**: 완료/오류 팝업 높이 +10% 추가 확대
  - **팝업 폰트 축소**: 약 30% 축소 (28→20, 24→17 등)

### 3. 패널 헤더
- **`src/tcp_monitor/ui/panel_header.py`**
  - **안전교육/도면 버튼 활성화**: 센서 접속 대기 중에도 사용 가능
  - 접속 대기 중: 안전교육/도면 버튼 활성화, 타일/그래프는 비활성화 유지

### 4. 안전 서명 (화상키보드)
- **`src/tcp_monitor/ui/safety_signature.py`**
  - **화상키보드 크로스 플랫폼 지원 추가**: 
    - Windows: OSK/TabTip (기존 유지)
    - Linux: onboard → florence 순서로 시도
  - **OS 감지**: `platform.system()` 사용하여 Windows/Linux 구분

## 문서 업데이트

### 1. 버전 정보
- **`VERSION.txt`**: 1.8.3 → 1.8.4 업데이트, POSIX 표준 준수 (개행 포함)

### 2. 메인 문서
- **`README.md`**: 
  - 제목: "v1.8.4 (Windows/Linux 통합)" 추가
  - 실행 방법 섹션에 Ubuntu 실행 방법 추가
  - `UBUNTU_INSTALL_GUIDE.md` 참조 링크 추가

### 3. 변경 이력
- **`CHANGELOG.md`**: v1.8.4 섹션 추가
  - Ubuntu 지원 항목
  - 크로스 플랫폼 코드 분리
  - 팝업 UI 개선
  - 시스템 메시지 차단
  - 카메라 백엔드 분리
  - 화상키보드 OS별 처리

## 설정 파일 (크로스 플랫폼 호환)

### 1. 환경 설정
- **`config.conf.example`**: Linux/Windows 모두에서 동작하는 기본 설정 유지

## 변경 사항 요약

### Windows 전용 → 크로스 플랫폼
- ❌ `ctypes.windll` 직접 사용
- ✅ OS 감지 후 Windows에서만 사용, Linux에서는 None 대체

- ❌ `cv2.CAP_DSHOW` (Windows 전용)
- ✅ OS별 백엔드 자동 선택 (Windows: DirectShow, Linux: V4L2)

- ❌ Windows OSK/TabTip만 지원
- ✅ OS별 화상키보드 (Windows: OSK/TabTip, Linux: onboard/florence)

### 기능 개선
- 센서 접속 없이도 안전교육/도면 메뉴 사용 가능
- 시스템 메시지 자동 차단/응답
- 팝업 항상 최상위/포커스 유지
- 팝업 UI 크기/폰트 최적화

## 추가 정리 완료 사항

### 1. 누락된 크로스 플랫폼 지원 추가
- **`src/tcp_monitor/ui/safety_signature.py`**: Linux 화상키보드 지원 추가 (onboard/florence)
  - 기존: Windows OSK/TabTip만 지원
  - 추가: Linux에서 onboard → florence 순서로 시도

### 2. 스크립트 개선
- **`run_ubuntu.sh`**: 하드코딩된 경로를 동적 경로 감지로 변경
  - `PROJECT_DIR`: 스크립트 위치 기반 자동 감지 (`$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)`)
  - `VENV_DIR`: `$HOME/venvs/garame` 사용 (사용자별 경로)

---

**총 10개 파일**이 리눅스/윈도우 동시 실행 작업과 직접 관련되어 있습니다:
1. `run_ubuntu.sh` (새로 추가)
2. `UBUNTU_INSTALL_GUIDE.md` (새로 추가)
3. `sitecustomize.py` (새로 추가)
4. `src/tcp_monitor/ui/app.py` (크로스 플랫폼 수정)
5. `src/tcp_monitor/ui/safety_education.py` (크로스 플랫폼 수정)
6. `src/tcp_monitor/ui/panel_header.py` (크로스 플랫폼 수정)
7. `src/tcp_monitor/ui/safety_signature.py` (크로스 플랫폼 수정)
8. `VERSION.txt` (버전 업데이트)
9. `README.md` (문서 업데이트)
10. `CHANGELOG.md` (문서 업데이트)

**참고**: 이 목록은 v1.8.4 릴리스 기준이며, 이후 버전에서 추가/변경될 수 있습니다.

