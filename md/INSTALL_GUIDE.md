# GARAMe Manager v1.9.2 - 자동 설치 가이드

## 특징

이 버전의 `install.sh`는 **완전 자동 설치**를 지원합니다.
- ✅ 사용자 질문 없음 (모두 자동 yes)
- ✅ 얼굴 인식 자동 설치
- ✅ 시스템 최적화 자동 실행
- ✅ cmake 충돌 문제 해결

## 빠른 시작

```bash
cd ~/바탕화면/1.9.1
./install.sh
```

그냥 실행하면 끝! 모든 과정이 자동으로 진행됩니다.

---

## 설치 과정 (자동 진행)

### 1. 시스템 패키지 설치
- Python 3, pip, venv, build-essential
- cmake (시스템 패키지)
- OpenCV 관련 라이브러리
- dlib 빌드를 위한 의존성

### 2. 한글 폰트 설치
- fonts-nanum
- fonts-nanum-extra

### 3. Python 가상환경 생성
- 기존 venv 자동 삭제 후 재생성
- pip, setuptools, wheel 최신 버전 설치

### 4. Python 패키지 설치
- requirements.txt 기반 설치
- **얼굴 인식 자동 설치**:
  - 시스템 cmake 확인 (없으면 자동 설치)
  - dlib 빌드 (30분~1시간 소요)
  - face-recognition 설치

### 5. Tesseract OCR 설정
- 한글 언어 데이터 다운로드

### 6. 설정 파일 및 디렉토리 생성
- config.ini (기본 설정)
- data/, logs/ 디렉토리

### 7. 시스템 최적화 (자동)
- 화면 자동 꺼짐 비활성화
- 화면 잠금 비활성화
- 절전 모드 비활성화
- 시스템 알림 비활성화

### 8. 자동 시작 설정 (자동)
- setup_autostart.sh 실행 (있는 경우)

---

## 설치 시간

| 항목 | 시간 |
|------|------|
| 시스템 패키지 | 5-10분 |
| Python 패키지 | 5-10분 |
| **dlib 빌드** | **30-60분** ⏱️ |
| 기타 설정 | 2-3분 |
| **총 소요 시간** | **약 45-80분** |

---

## 디스크 용량 요구사항

| 항목 | 용량 |
|------|------|
| 시스템 패키지 | 1GB |
| Python 가상환경 | 4-5GB |
| 빌드 임시 파일 | 2-3GB (설치 후 삭제됨) |
| **최소 여유 공간** | **10GB** |
| **권장 여유 공간** | **15GB** |

---

## 주요 변경사항 (이전 버전 대비)

### ✅ 자동화된 항목

1. **가상환경 재생성**: 기존 venv 삭제 여부 묻지 않고 자동 삭제
2. **온라인 설치**: 온라인/오프라인 선택 없이 자동 온라인 모드
3. **얼굴 인식 설치**: y/n 선택 없이 자동 설치
4. **시스템 최적화**: y/n 선택 없이 자동 실행
5. **자동 시작 설정**: y/n 선택 없이 자동 설정

### 🔧 기술적 개선사항

1. **cmake 충돌 해결**:
   - requirements.txt에서 `cmake` 패키지 제거
   - 시스템 cmake만 사용 (dlib 빌드 시 충돌 방지)

2. **시스템 cmake 자동 설치**:
   ```bash
   if ! command -v cmake &> /dev/null; then
       sudo apt install -y cmake
   fi
   ```

3. **에러 핸들링 개선**:
   - dlib 설치 실패 시 경고만 표시하고 계속 진행
   - 선택적 패키지 설치 실패 시 무시

---

## 설치 후 실행

### 방법 1: run.sh 사용 (권장)

```bash
./run.sh
```

### 방법 2: Python 직접 실행

```bash
source venv/bin/activate
python3 main.py
```

---

## 문제 해결

### dlib 빌드 실패

**증상**: `Building wheel for dlib (pyproject.toml) ... error`

**해결 방법**:

```bash
# 1. cmake 확인
which cmake
cmake --version

# 2. 빌드 도구 재설치
sudo apt install -y build-essential cmake libopenblas-dev liblapack-dev

# 3. 가상환경 재생성 후 재시도
rm -rf venv
./install.sh
```

### 디스크 용량 부족

**증상**: `No space left on device`

**해결 방법**:

```bash
# APT 캐시 정리
sudo apt clean && sudo apt autoremove -y

# 로그 정리
sudo journalctl --vacuum-time=7d

# 임시 파일 삭제
sudo rm -rf /tmp/*

# 다시 시도
./install.sh
```

### 권한 오류

**증상**: `Permission denied`

**해결 방법**:

```bash
# 실행 권한 추가
chmod +x install.sh

# 재실행
./install.sh
```

---

## 설치 로그 확인

설치 중 에러 발생 시 로그를 확인하세요:

```bash
# 설치 스크립트 실행하면서 로그 저장
./install.sh 2>&1 | tee install.log
```

---

## Ubuntu 버전 호환성

| Ubuntu 버전 | 상태 | 비고 |
|-------------|------|------|
| Ubuntu 25.10 | ✅ 테스트 완료 | |
| Ubuntu 24.04 LTS | ✅ 지원 | |
| Ubuntu 22.04 LTS | ✅ 지원 | |
| Ubuntu 20.04 LTS | ⚠️ 부분 지원 | Python 3.8+ 필요 |

---

## 추가 정보

- [DISK_SPACE_GUIDE.md](DISK_SPACE_GUIDE.md) - 디스크 용량 상세 가이드
- [VERSION_1.9.0_CHANGES.md](VERSION_1.9.0_CHANGES.md) - 버전 변경 사항
- [README.md](README.md) - 프로그램 사용 설명서

---

## 요약

```bash
# 한 줄 명령어
cd ~/바탕화면/1.9.1 && ./install.sh

# 설치 완료 후
./run.sh
```

**모든 과정이 자동으로 진행됩니다!** ☕ 커피 한 잔 하고 오세요 (약 1시간 소요)
