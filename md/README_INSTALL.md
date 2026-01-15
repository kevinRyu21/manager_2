# GARAMe Manager v1.9.1 - 설치 및 실행 가이드

Ubuntu 25 환경에 최적화된 통합 설치 및 실행 가이드입니다.

## 목차
- [빠른 시작](#빠른-시작)
- [상세 설치 가이드](#상세-설치-가이드)
- [실행 방법](#실행-방법)
- [오프라인 설치](#오프라인-설치)
- [문제 해결](#문제-해결)

## 빠른 시작

### 1. 설치 (최초 1회)
```bash
cd 1.9.1
chmod +x install.sh run.sh
./install.sh
```

### 2. 실행
```bash
./run.sh
```

끝! 이제 GARAMe Manager가 실행됩니다.

## 상세 설치 가이드

### 시스템 요구사항
- **OS**: Ubuntu 25.04 (22.04, 24.04도 지원)
- **Python**: 3.10 이상
- **RAM**: 최소 4GB (8GB 권장)
- **저장공간**: 최소 2GB
- **카메라**: USB 웹캠 또는 내장 카메라

### 설치 과정

#### 1단계: 파일 다운로드
```bash
# Git으로 다운로드
git clone https://github.com/your-repo/garami_manager.git
cd garami_manager/1.9.1

# 또는 압축 파일 다운로드 후 압축 해제
unzip garami_manager-1.9.1.zip
cd 1.9.1
```

#### 2단계: 설치 스크립트 실행
```bash
chmod +x install.sh
./install.sh
```

설치 스크립트는 다음 작업을 자동으로 수행합니다:

1. **시스템 패키지 설치**
   - Python 3 및 필수 라이브러리
   - OpenCV 및 컴퓨터 비전 라이브러리
   - 한글 폰트 (나눔 폰트)

2. **Python 가상환경 생성**
   - `venv` 디렉토리에 생성
   - pip, setuptools, wheel 최신 버전 설치

3. **Python 패키지 설치**
   - **얼굴 인식**: dlib, face-recognition
   - **문자 인식**: pytesseract, tesseract-ocr
   - **GUI**: tkinter, opencv-python, pillow
   - **기타**: numpy, configparser 등

4. **모델 및 데이터 다운로드**
   - Tesseract 한글 언어 데이터
   - OpenCV Haar Cascade 모델 (자동 포함)
   - 얼굴 인식 모델 (face-recognition에 포함)

5. **설정 파일 생성**
   - config.ini (기본 설정)
   - 데이터 디렉토리 생성

#### 3단계: 설치 확인
```bash
source venv/bin/activate
python3 -c "import cv2, face_recognition, pytesseract; print('모든 패키지 설치 완료!')"
```

## 실행 방법

### 기본 실행
```bash
./run.sh
```

### Watchdog 모드 (자동 재시작)
```bash
./run.sh --watchdog
# 또는
./run.sh -w
```

### 백그라운드 실행
```bash
./run.sh --background
# 또는
./run.sh -b
```

### 디버그 모드
```bash
./run.sh --debug
# 또는
./run.sh -d
```

### 프로그램 종료
```bash
./run.sh --stop
# 또는
./run.sh -s
```

### 도움말
```bash
./run.sh --help
# 또는
./run.sh -h
```

## 오프라인 설치

인터넷 연결이 없는 환경에서도 설치 가능합니다.

### 1. 온라인 환경에서 패키지 다운로드
```bash
# 다른 컴퓨터에서 실행 (인터넷 연결 필요)
./download_wheels.sh
```

이 명령은 `wheels/` 디렉토리에 모든 필요한 패키지를 다운로드합니다.

### 2. wheels 디렉토리와 함께 파일 전송
```bash
# USB 또는 다른 방법으로 전체 디렉토리 복사
cp -r 1.9.0 /path/to/usb/
```

### 3. 오프라인 환경에서 설치
```bash
cd 1.9.0
./install.sh
# "온라인 설치를 진행하시겠습니까? (y/n)"에서 'n' 입력
```

## 자동 시작 설정

부팅 시 자동으로 GARAMe Manager를 실행하려면:

```bash
./setup_autostart.sh
```

자동 시작 방법 선택:
1. **사용자 자동 시작** (권장)
   - 로그인 시 자동 실행
   - 사용자 권한으로 실행

2. **systemd 시스템 서비스**
   - 부팅 시 자동 실행
   - root 권한으로 실행

3. **systemd 사용자 서비스**
   - 로그인 시 자동 실행
   - 사용자 권한으로 실행

## 디렉토리 구조

```
1.9.1/
├── install.sh              # 통합 설치 스크립트
├── run.sh                  # 통합 실행 스크립트
├── main.py                 # 메인 프로그램
├── watchdog.py             # 자동 재시작 감시 프로그램
├── config.ini              # 설정 파일
├── requirements.txt        # Python 패키지 목록
│
├── venv/                   # Python 가상환경 (설치 후 생성)
├── data/                   # 데이터 디렉토리
│   ├── faces/              # 등록된 얼굴 데이터
│   └── backgrounds/        # 배경 학습 데이터
├── logs/                   # 로그 파일
├── wheels/                 # 오프라인 패키지 (선택)
│
├── src/                    # 소스 코드
│   └── tcp_monitor/
│       ├── ui/             # UI 모듈
│       ├── sensor/         # 센서 및 감지 모듈
│       └── ...
│
└── docs/                   # 문서
    ├── VERSION_1.9.1_CHANGES.md
    ├── KOREAN_FONT_INSTALL.md
    ├── BACKGROUND_LEARNING_FEATURE.md
    └── ...
```

## 주요 기능

### 1. 얼굴 인식 (오프라인)
- dlib 기반 얼굴 감지 및 인식
- 로컬에서 모든 처리 수행
- 인터넷 연결 불필요

### 2. 문자 인식 (오프라인)
- Tesseract OCR 엔진
- 한글 + 영문 지원
- 로컬에서 모든 처리 수행

### 3. 안전 장구 감지
- OpenCV Haar Cascade
- 안전모, 보안경, 장갑, 안전화 감지
- 실시간 처리

### 4. 배경 학습
- 3초 카운트다운 후 10장 자동 촬영
- 전역 배경 데이터 공유
- 인식률 70-80% 향상

## 문제 해결

### 문제 1: Python3를 찾을 수 없습니다
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 문제 2: 한글이 네모 박스로 표시됨
```bash
./install_korean_font.sh
# 또는
sudo apt install -y fonts-nanum
sudo fc-cache -fv
```

### 문제 3: 카메라를 열 수 없습니다
```bash
# 카메라 장치 확인
ls -l /dev/video*

# 권한 확인
sudo usermod -a -G video $USER

# 재로그인 또는 재부팅
```

### 문제 4: face-recognition 설치 실패
```bash
# dlib 수동 설치
sudo apt install -y build-essential cmake libopenblas-dev liblapack-dev
pip install dlib
pip install face-recognition
```

### 문제 5: 가상환경 활성화 오류
```bash
# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 로그 확인

### 실행 로그
```bash
tail -f logs/manager_*.log
```

### Watchdog 로그
```bash
tail -f logs/watchdog.log
```

### 에러 로그
```bash
grep -i error logs/*.log
```

## 업데이트

### 프로그램 업데이트
```bash
git pull origin main
./install.sh  # 필요한 경우에만
./run.sh
```

### Python 패키지 업데이트
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 제거

### 프로그램만 제거
```bash
rm -rf venv data logs temp
```

### 완전 제거 (설정 포함)
```bash
# 자동 시작 제거
./setup_autostart.sh  # 옵션 4 선택

# 디렉토리 삭제
cd ..
rm -rf 1.9.1
```

## 추가 정보

- **버전 변경 사항**: [VERSION_1.9.1_CHANGES.md](VERSION_1.9.1_CHANGES.md)
- **한글 폰트 설치**: [KOREAN_FONT_INSTALL.md](KOREAN_FONT_INSTALL.md)
- **배경 학습 기능**: [BACKGROUND_LEARNING_FEATURE.md](BACKGROUND_LEARNING_FEATURE.md)

## 지원

문제가 발생하면:
1. 로그 파일 확인
2. README 문제 해결 섹션 참조
3. 이슈 리포트 제출

## 라이선스

Copyright © 2025 GARAMe Project
