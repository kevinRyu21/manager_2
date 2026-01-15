# 플랫폼별 어댑터 아키텍처

## 개요

GARAMe MANAGER v1.8.7부터 플랫폼별 코드를 어댑터 패턴으로 구조화하여 유지보수성을 향상시켰습니다.

## 디렉토리 구조

```
src/tcp_monitor/platform/
├── __init__.py              # 플랫폼 자동 선택
├── base.py                  # 베이스 클래스 (인터페이스)
├── windows/
│   ├── __init__.py
│   ├── camera.py           # Windows 카메라 백엔드
│   ├── keyboard.py         # Windows 화상 키보드
│   └── system.py           # Windows 시스템 유틸리티
└── linux/
    ├── __init__.py
    ├── camera.py           # Linux 카메라 백엔드
    ├── keyboard.py         # Linux 화상 키보드
    └── system.py           # Linux 시스템 유틸리티
```

## 어댑터 클래스

### 1. CameraBackend
**역할**: 플랫폼별 카메라 백엔드 관리

**메서드**:
- `get_backend()` → `int`: OpenCV 카메라 백엔드 상수 반환
- `get_fallback_backend()` → `int`: 대체 백엔드 반환

**구현**:
- Windows: `cv2.CAP_DSHOW` (DirectShow)
- Linux: `cv2.CAP_V4L2` (Video4Linux2)

### 2. KeyboardManager
**역할**: 플랫폼별 화상 키보드 실행

**메서드**:
- `open_virtual_keyboard(target_widget=None)` → `bool`: 가상 키보드 실행
- `force_korean_ime(target_widget)` → `bool`: 한글 IME 강제 설정 (Windows 전용)

**구현**:
- Windows: OSK → TabTip 순서로 시도
- Linux: onboard → florence 순서로 시도

### 3. SystemUtils
**역할**: 플랫폼별 시스템 유틸리티

**메서드**:
- `open_file(file_path)` → `bool`: 파일을 기본 애플리케이션으로 열기
- `get_window_handle(window)` → `Optional[int]`: 윈도우 핸들 반환 (Windows 전용)
- `block_unauthorized_windows()` → `bool`: 권한 없는 윈도우 차단 (Windows 전용)

**구현**:
- Windows: `os.startfile()` 사용
- Linux: `xdg-open` 사용

## 사용 방법

### 기본 사용

```python
from ...platform import CameraBackend, KeyboardManager, SystemUtils

# 카메라 백엔드
camera_backend = CameraBackend()
backend = camera_backend.get_backend()
camera = cv2.VideoCapture(0, backend)

# 화상 키보드
keyboard_manager = KeyboardManager()
keyboard_manager.open_virtual_keyboard(target_widget)

# 시스템 유틸리티
system_utils = SystemUtils()
system_utils.open_file("/path/to/file")
```

### 플랫폼 자동 선택

`platform/__init__.py`가 현재 플랫폼을 자동으로 감지하여 적절한 구현을 로드합니다:

```python
# 자동으로 Windows 또는 Linux 구현이 선택됨
from ...platform import CameraBackend

# Windows에서 실행 시: WindowsCameraBackend
# Linux에서 실행 시: LinuxCameraBackend
backend = CameraBackend()
```

## 리팩토링된 파일

다음 파일들이 플랫폼 어댑터를 사용하도록 변경되었습니다:

1. **`src/tcp_monitor/ui/safety_education.py`**
   - 카메라 백엔드: `CameraBackend` 사용

2. **`src/tcp_monitor/ui/safety_signature.py`**
   - 화상 키보드: `KeyboardManager` 사용

3. **`src/tcp_monitor/ui/capture_manager.py`**
   - 파일 열기: `SystemUtils` 사용

4. **`src/tcp_monitor/ui/face_registration_manager.py`**
   - 카메라 백엔드: `CameraBackend` 사용

## 장점

1. **코드 단순화**: 플랫폼 분기 로직이 어댑터로 분리되어 메인 코드가 단순해짐
2. **유지보수성 향상**: 플랫폼별 코드가 명확히 분리되어 수정이 용이
3. **테스트 용이**: 각 플랫폼 구현을 독립적으로 테스트 가능
4. **확장성**: 새로운 플랫폼 추가 시 베이스 클래스만 구현하면 됨
5. **재사용성**: 어댑터를 다른 프로젝트에서도 재사용 가능

## 향후 계획

- macOS 지원 추가 (선택적)
- 플랫폼별 단위 테스트 추가
- 더 많은 플랫폼별 기능을 어댑터로 분리

## 참고

- 기존 코드는 하위 호환성을 위해 유지되지만, 새로운 기능은 어댑터 패턴을 사용하는 것을 권장합니다.
- 플랫폼별 특화 기능은 각 플랫폼 디렉토리에 추가하세요.

