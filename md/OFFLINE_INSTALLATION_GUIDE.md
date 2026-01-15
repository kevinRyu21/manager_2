# 오프라인 설치 가이드

GARAMe Manager를 인터넷 연결 없이 설치하는 방법입니다.

## 📋 목차
- [개요](#개요)
- [사전 준비](#사전-준비)
- [온라인 환경에서 준비](#온라인-환경에서-준비)
- [오프라인 환경에서 설치](#오프라인-환경에서-설치)
- [문제 해결](#문제-해결)

---

## 개요

### 오프라인 설치가 필요한 경우
- 인터넷 연결이 없는 환경
- 보안상 외부 네트워크 차단된 환경
- 대역폭 절약이 필요한 경우
- 여러 대의 PC에 동일하게 설치할 경우

### 준비 과정
```
온라인 환경 (PC A)          오프라인 환경 (PC B)
     ↓                              ↓
패키지 다운로드             →    USB/네트워크로 전송
     ↓                              ↓
wheels 디렉토리             →    오프라인 설치
```

---

## 사전 준비

### 필요한 것
1. **온라인 환경의 PC** (패키지 다운로드용)
   - Ubuntu 25.10 (또는 동일 버전)
   - Python 3.13
   - 인터넷 연결

2. **USB 드라이브 또는 네트워크 공유**
   - 최소 2GB 이상 (안전하게 5GB 권장)

3. **오프라인 환경의 PC** (설치 대상)
   - Ubuntu 25.10 (온라인 환경과 동일 버전 권장)
   - Python 3.13 (온라인 환경과 동일 버전)

**중요**: Python 버전과 Ubuntu 버전이 온라인/오프라인 환경에서 **반드시 동일**해야 합니다!

---

## 온라인 환경에서 준비

### 방법 1: 자동 다운로드 스크립트 (권장) ⭐

#### 1. 프로젝트 디렉토리로 이동
```bash
cd ~/Desktop/프로그램/manager/1.9.1
```

#### 2. 다운로드 스크립트 실행
```bash
chmod +x download_all_wheels.sh
./download_all_wheels.sh
```

**실행 과정**:
```
[1/5] 빌드 도구 다운로드 중...
  - pip, wheel, setuptools, Cython

[2/5] requirements.txt 패키지 다운로드 중...
  - Pillow, matplotlib, numpy, opencv 등

[3/5] 의존성 패키지 다운로드 중...
  - 재귀적으로 모든 의존성 다운로드

[4/5] 추가 필수 패키지 다운로드 중...
  - torch, torchvision 등

[5/5] 중복 파일 제거 중...
  - .tar.gz → .whl 우선
```

**다운로드 시간**: 약 10-30분 (인터넷 속도에 따라)

**다운로드 결과**:
```
wheels/
├── Cython-3.0.11-cp313-cp313-manylinux_2_17_x86_64.whl
├── numpy-1.26.4-cp313-cp313-manylinux_2_17_x86_64.whl
├── opencv_contrib_python-4.9.0.80-cp37-abi3-manylinux_2_17_x86_64.whl
├── torch-2.9.0-cp313-cp313-linux_x86_64.whl
├── ... (200-300개 파일)
└── torchvision-0.24.0-cp313-cp313-linux_x86_64.whl
```

**요약 파일**: `wheels_download_summary_YYYYMMDD_HHMMSS.txt`

#### 3. 다운로드 확인
```bash
# 파일 개수 확인
ls wheels/ | wc -l

# 총 크기 확인
du -sh wheels/

# 요약 파일 확인
cat wheels_download_summary_*.txt
```

---

### 방법 2: 수동 다운로드

필요한 경우 수동으로 다운로드할 수 있습니다:

```bash
cd ~/Desktop/프로그램/manager/1.9.1
mkdir -p wheels

# 빌드 도구
pip3 download -d wheels Cython setuptools wheel

# 모든 패키지 + 의존성
pip3 download -r requirements.txt -d wheels
```

---

### 방법 3: 빠른 업데이트 (기존 wheels 있을 때)

이미 wheels 디렉토리가 있고 누락된 패키지만 추가하려면:

```bash
chmod +x update_wheels.sh
./update_wheels.sh
```

---

## 오프라인 환경에서 설치

### 1. 파일 전송

#### USB 사용
```bash
# 온라인 PC에서
cp -r ~/Desktop/프로그램/manager/1.9.1 /media/usb/

# 오프라인 PC에서
cp -r /media/usb/1.9.1 ~/Desktop/프로그램/manager/
```

#### 네트워크 공유 사용
```bash
# 온라인 PC에서
scp -r ~/Desktop/프로그램/manager/1.9.1 user@offline-pc:~/Desktop/프로그램/manager/
```

#### 압축하여 전송 (용량 절약)
```bash
# 온라인 PC에서
cd ~/Desktop/프로그램/manager
tar -czf 1.9.1_offline.tar.gz 1.9.1/

# 오프라인 PC에서
tar -xzf 1.9.1_offline.tar.gz
```

---

### 2. 시스템 패키지 설치

오프라인 PC에서도 시스템 패키지는 **반드시 온라인으로 설치**해야 합니다.

**일회성 온라인 연결**이 가능한 경우:
```bash
cd ~/Desktop/프로그램/manager/1.9.1
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential cmake libopenblas-dev liblapack-dev
```

**완전 오프라인**인 경우:
- Ubuntu 설치 미디어의 패키지 사용
- 또는 다른 PC에서 .deb 파일 다운로드하여 전송

---

### 3. 오프라인 설치 실행

```bash
cd ~/Desktop/프로그램/manager/1.9.1

# 설치 스크립트 실행
chmod +x install.sh
./install.sh
```

**질문 응답**:
```
온라인 설치를 진행하시겠습니까? (y/n): n
시스템 설정을 최적화하시겠습니까? (y/n): y
자동 시작 설정을 하시겠습니까? (y/n): y
```

**설치 과정**:
1. ✓ 시스템 패키지 확인
2. ✓ 한글 폰트 설치
3. ✓ 가상환경 생성
4. ✓ wheels 디렉토리에서 Python 패키지 설치
5. ✓ 설정 파일 생성
6. ✓ 시스템 최적화 (화면 보호기 비활성화 등)

---

### 4. 실행

```bash
./run.sh
```

정상적으로 프로그램이 실행되어야 합니다!

---

## 문제 해결

### 1. "Could not find a version that satisfies the requirement" 오류

**원인**: wheels 디렉토리에 패키지가 없음

**해결**:
```bash
# 온라인 PC에서 다시 다운로드
./download_all_wheels.sh

# 특정 패키지만 추가
pip3 download -d wheels 패키지명
```

### 2. "No matching distribution found" 오류

**원인**: Python 버전 불일치

**확인**:
```bash
# 온라인 PC
python3 --version

# 오프라인 PC
python3 --version
```

**해결**: Python 버전을 동일하게 맞추기

### 3. 설치는 되는데 실행 오류

**원인**: 시스템 패키지 누락

**해결**:
```bash
# 필수 시스템 패키지 설치
sudo apt install -y libgl1 libglib2.0-0 ffmpeg v4l-utils
```

### 4. wheels 디렉토리가 너무 큼

**원인**: 중복 파일 또는 불필요한 파일

**해결**:
```bash
cd wheels

# .tar.gz 파일 제거 (.whl 있는 경우)
for tarfile in *.tar.gz; do
    PKG_NAME=$(echo "$tarfile" | sed 's/-[0-9].*//')
    if ls ${PKG_NAME}-*.whl 1> /dev/null 2>&1; then
        rm -f "$tarfile"
    fi
done

# 크기 확인
du -sh .
```

### 5. torch/torchvision이 너무 큼 (GPU 미사용 시)

**CPU 전용 버전 다운로드**:
```bash
# 온라인 PC에서
pip3 download torch torchvision --index-url https://download.pytorch.org/whl/cpu -d wheels/
```

크기 비교:
- GPU 버전: ~2GB
- CPU 전용: ~200MB

---

## 디스크 공간 요구사항

### wheels 디렉토리
- **최소**: 1.5GB
- **권장**: 3GB (여유 공간 포함)

### 설치 후
- **프로그램**: 500MB
- **venv**: 2GB
- **데이터**: 500MB (로그, 캡처 등)
- **총**: 약 3GB

---

## 버전 관리

### wheels 디렉토리 백업

나중에 재사용하기 위해 백업:

```bash
# 날짜별 백업
cp -r wheels wheels_backup_$(date +%Y%m%d)

# 압축 백업
tar -czf wheels_backup_$(date +%Y%m%d).tar.gz wheels/
```

### 버전 정보 기록

`wheels_version_info.txt` 생성:
```bash
{
    echo "다운로드 날짜: $(date)"
    echo "Python 버전: $(python3 --version)"
    echo "Ubuntu 버전: $(lsb_release -d)"
    echo "파일 개수: $(ls -1 wheels/ | wc -l)"
    echo "총 크기: $(du -sh wheels/)"
} > wheels_version_info.txt
```

---

## 체크리스트

### 온라인 환경 준비
- [ ] Ubuntu 버전 확인
- [ ] Python 버전 확인
- [ ] `download_all_wheels.sh` 실행
- [ ] 다운로드 완료 확인 (요약 파일)
- [ ] wheels 디렉토리 크기 확인 (2GB 이상)
- [ ] USB/네트워크 전송 준비

### 오프라인 환경 설치
- [ ] 파일 전송 완료
- [ ] Ubuntu 버전 동일 확인
- [ ] Python 버전 동일 확인
- [ ] 시스템 패키지 설치
- [ ] `./install.sh` 실행 (n 선택)
- [ ] 설치 완료 확인
- [ ] `./run.sh` 실행 테스트

---

## 참고 문서

- [README_INSTALL.md](README_INSTALL.md) - 일반 설치 가이드
- [VERSION_1.9.1_CHANGES.md](VERSION_1.9.1_CHANGES.md) - 버전 변경사항
- [UBUNTU_INSTALLATION_GUIDE.md](UBUNTU_INSTALLATION_GUIDE.md) - Ubuntu 최적화

---

## FAQ

**Q: wheels 디렉토리를 여러 PC에 재사용할 수 있나요?**
A: Python 버전과 Ubuntu 버전이 동일하면 재사용 가능합니다.

**Q: 일부 패키지만 온라인 설치하고 싶어요.**
A: 불가능합니다. install.sh는 전체 온라인 또는 전체 오프라인만 지원합니다.

**Q: macOS/Windows에서 다운로드한 wheels를 Ubuntu에서 사용할 수 있나요?**
A: 불가능합니다. OS와 아키텍처가 동일해야 합니다.

**Q: 오프라인 설치 후 업데이트하려면?**
A: 온라인 환경에서 새 버전의 wheels를 다운로드하여 다시 전송해야 합니다.

---

Copyright © 2025 GARAMe Project
