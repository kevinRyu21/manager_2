# 얼굴 등록 관리 기능 수정

## 문제 상황
"설정 → 얼굴등록 관리" 메뉴가 실행되지 않는 문제

## 원인 분석
1. **라이브러리 누락**: 얼굴 등록 관리 기능은 선택적 라이브러리(face-recognition, dlib, opencv)가 필요
2. **에러 메시지 불명확**: 라이브러리 미설치 시 에러 메시지가 설치 방법을 명확히 안내하지 못함
3. **메뉴 라벨 미흡**: 사용자가 추가 설치가 필요한지 사전에 알 수 없음

## 수정 내용

### 1. 에러 메시지 개선 (Ubuntu Linux 전용)

**Before**:
```python
error_msg = (
    f"얼굴 등록 관리 모듈을 불러올 수 없습니다:\n{str(e)}\n\n"
    "필요한 라이브러리가 설치되어 있는지 확인하세요:\n"
    "- face-recognition\n"
    "- dlib\n"
    "- opencv-contrib-python"
)
```

**After** ([app.py:2691-2714](src/tcp_monitor/ui/app.py#L2691-L2714)):
```python
error_msg = (
    "얼굴 등록 관리 기능을 사용하려면 추가 라이브러리 설치가 필요합니다.\n\n"
    f"오류 내용: {error_detail}\n\n"
    "📦 설치 방법 (간편):\n"
    "  1. 터미널을 열고 프로그램 폴더로 이동\n"
    "  2. 다음 명령 실행:\n"
    "     ./install_face_recognition.sh\n"
    "  3. 자동으로 필요한 라이브러리가 설치됩니다\n"
    "  4. 설치 완료 후 프로그램을 재시작하세요\n\n"
    "📦 설치 방법 (수동):\n"
    "  터미널에서 다음 명령을 실행:\n"
    "  pip3 install face-recognition dlib opencv-contrib-python\n\n"
    "⚠️ 참고:\n"
    "  - Ubuntu Linux 전용 프로그램입니다\n"
    "  - 설치에는 5-10분 정도 소요될 수 있습니다\n"
    "  - 인터넷 연결이 필요합니다\n"
    "  - 시스템 패키지: build-essential, cmake 필요"
)
```

### 2. 메뉴 라벨 개선 ([app.py:975-981](src/tcp_monitor/ui/app.py#L975-L981))
**Before**:
```python
self.menu_cfg.add_command(label="얼굴 등록 관리", command=self.manage_face_registration)
```

**After**:
```python
# 얼굴 등록 관리: 라이브러리 설치 여부 확인하여 라벨 변경
try:
    import face_recognition
    face_reg_label = "얼굴 등록 관리"
except ImportError:
    face_reg_label = "얼굴 등록 관리 (라이브러리 설치 필요)"
self.menu_cfg.add_command(label=face_reg_label, command=self.manage_face_registration)
```

## 개선 효과

### 사용자 경험 개선
1. **명확한 안내**: 라이브러리가 설치되지 않았을 때 메뉴 라벨에서 바로 확인 가능
2. **상세한 설치 방법**: 에러 메시지에서 Ubuntu Linux 전용 단계별 설치 방법 제공
3. **자동 설치 스크립트 안내**: `install_face_recognition.sh` 파일을 통한 간편 설치 방법 제시

### 기술적 개선
1. **Import 체크**: 메뉴 생성 시 face_recognition 라이브러리 설치 여부 확인
2. **Ubuntu Linux 전용**: Windows 관련 코드 완전 제거, 순수 Ubuntu 환경 최적화
3. **에러 처리 강화**: ImportError와 일반 Exception을 구분하여 처리

## 사용 방법 (Ubuntu Linux)

### 얼굴 등록 관리 기능 사용하기

#### 1. 관리자 모드 진입
```
메뉴: 설정 → 관리자 모드 진입
비밀번호 입력
```

#### 2. 라이브러리 설치 확인
- 메뉴에서 "얼굴 등록 관리" 또는 "얼굴 등록 관리 (라이브러리 설치 필요)" 확인
- 설치 필요 라벨이 보이면 아래 단계 진행

#### 3. 시스템 패키지 설치 (선행 작업)
```bash
sudo apt update
sudo apt install -y build-essential cmake python3-dev
```

#### 4. 라이브러리 설치 (간편 방법)
```bash
cd ~/Desktop/프로그램/manager/1.9.1
chmod +x install_face_recognition.sh
./install_face_recognition.sh
```

#### 5. 라이브러리 설치 (수동 방법)
```bash
# 가상환경 활성화 (가상환경 사용 시)
source venv/bin/activate

# 라이브러리 설치
pip3 install face-recognition dlib opencv-contrib-python
```

#### 6. 프로그램 재시작
```bash
./run.sh
```

#### 7. 얼굴 등록 관리 실행
```
메뉴: 설정 → 얼굴 등록 관리
정상적으로 창이 열림
```

## 주의사항

### 라이브러리 설치 관련
- **운영체제**: Ubuntu Linux 전용 (Windows 미지원)
- **설치 시간**: 5-10분 소요 (인터넷 속도에 따라)
- **인터넷 연결**: 필수
- **시스템 패키지**: build-essential, cmake 필요
- **Python 버전**: Python 3.8 이상 권장

### 호환성 이슈
- **NumPy 버전**: NumPy 2.x와 dlib 호환성 문제 있음
  - 권장: NumPy 1.26.4 사용
  - 자세한 내용: `FACE_RECOGNITION_NUMPY_FIX.md` 참조

### Ubuntu 버전별 참고사항
- **Ubuntu 20.04**: Python 3.8 기본 제공
- **Ubuntu 22.04**: Python 3.10 기본 제공
- **Ubuntu 24.04**: Python 3.12 기본 제공
- 버전에 따라 dlib 빌드 시간이 다를 수 있음

## 문제 해결

### 설치 중 오류 발생 시

#### 1. CMake 오류
```bash
sudo apt install -y cmake
```

#### 2. Python 헤더 파일 오류
```bash
sudo apt install -y python3-dev
```

#### 3. dlib 컴파일 오류
```bash
sudo apt install -y build-essential
```

#### 4. 메모리 부족 오류
```bash
# swap 메모리 증가 또는 더 많은 RAM 필요
# 최소 2GB RAM 권장
```

## 관련 파일
- [app.py](src/tcp_monitor/ui/app.py) - 메뉴 및 에러 처리
- [face_registration_manager.py](src/tcp_monitor/ui/face_registration_manager.py) - 얼굴 등록 관리 UI
- [install_face_recognition.sh](install_face_recognition.sh) - Ubuntu Linux 자동 설치 스크립트
- [requirements.txt](requirements.txt) - 의존성 목록

## 버전 정보
- 수정 버전: v1.9.1
- 수정 날짜: 2025-01-06
- 수정자: Claude Code
- 플랫폼: Ubuntu Linux 전용

---

Copyright © 2025 GARAMe Project
