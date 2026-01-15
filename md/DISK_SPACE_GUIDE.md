# GARAMe Manager 1.9.1 - 디스크 용량 가이드

## 설치 전 필수 확인사항

### 1. 필요한 디스크 용량

| 항목 | 위치 | 필요 용량 | 설명 |
|------|------|-----------|------|
| **시스템 패키지** | `/var/cache/apt/` | 1GB | apt 패키지 다운로드 캐시 |
| **빌드 임시 파일** | `/tmp/` | 2-3GB | dlib 컴파일 시 임시 파일 |
| **Python 가상환경** | `./venv/` | 3-4GB | Python 패키지 설치 |
| **여유 공간** | - | 2GB | 안전 마진 |
| **총 필요 용량** | - | **10GB** | **최소 요구사항** |
| **권장 용량** | - | **15-20GB** | 안정적 설치 |

---

## 설치 전 디스크 확인 및 정리

### 1단계: 현재 디스크 상태 확인

```bash
# 전체 파티션 확인
df -h

# 주요 디렉토리 용량 확인
df -h / /tmp /var

# 예상 출력:
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda1        50G   35G   13G  73% /
# tmpfs           2.0G  1.0M  2.0G   1% /tmp
```

**필수**: `/` (루트 파티션)에 최소 **10GB** 여유 공간 필요

---

### 2단계: 디스크 공간 확보 (용량 부족 시)

#### A. APT 패키지 캐시 정리 (1-3GB 확보)

```bash
# 다운로드된 패키지 아카이브 삭제
sudo apt clean

# 불필요한 패키지 제거
sudo apt autoremove -y

# 오래된 커널 제거 (선택)
sudo apt autoremove --purge -y
```

#### B. 시스템 로그 정리 (500MB-2GB 확보)

```bash
# 7일 이전 로그 삭제
sudo journalctl --vacuum-time=7d

# 또는 크기 제한
sudo journalctl --vacuum-size=100M

# 압축된 로그 파일 삭제
sudo rm -f /var/log/*.gz
sudo rm -f /var/log/*.old
sudo rm -f /var/log/*.[0-9]
```

#### C. /tmp 디렉토리 정리 (수백 MB 확보)

```bash
# 임시 파일 삭제
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*
```

#### D. 스냅 패키지 정리 (Ubuntu 스냅 사용 시)

```bash
# 오래된 스냅 버전 제거
sudo snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
    sudo snap remove "$snapname" --revision="$revision"
done
```

#### E. Docker 이미지 정리 (Docker 사용 시)

```bash
# 사용하지 않는 이미지 삭제
sudo docker system prune -a -f
```

---

### 3단계: 공간 확보 확인

```bash
# 정리 후 다시 확인
df -h /

# 필요한 공간이 확보되었는지 확인
# Avail 컬럼이 10GB 이상이면 OK
```

---

## install.sh 실행 시 옵션 선택

### 질문 1: 온라인 설치 선택

```
온라인 설치를 진행하시겠습니까? (y/n)
(n을 선택하면 오프라인 모드로 설치합니다)
```

**권장**: `y` 입력 (온라인 모드)
- 필요한 패키지만 설치하여 용량 절약

---

### 질문 2: 얼굴 인식 기능 설치 (중요!)

```
얼굴 인식 기능을 설치하시겠습니까? (y/n)
(dlib 빌드에 30분~1시간 정도 소요될 수 있습니다)
```

**디스크 용량에 따른 선택**:

| 여유 공간 | 권장 선택 | 설명 |
|-----------|-----------|------|
| **15GB 이상** | `y` | 얼굴 인식 포함 전체 설치 |
| **10-15GB** | `n` | 얼굴 인식 제외 (3-4GB 절약) |
| **10GB 미만** | `n` | 필수! 공간 부족으로 설치 실패 가능 |

---

## 설치 중 에러 발생 시 대응

### 에러 1: "No space left on device"

```bash
# 1. 설치 중단 (Ctrl+C)

# 2. 임시 파일 정리
sudo rm -rf /tmp/*

# 3. APT 캐시 정리
sudo apt clean

# 4. 다시 설치 시도
./install.sh
```

---

### 에러 2: dlib 빌드 중 디스크 부족

```bash
# 1. 설치 중단 (Ctrl+C)

# 2. venv 삭제 (처음부터 다시)
rm -rf venv

# 3. /tmp 정리
sudo rm -rf /tmp/*

# 4. 재시도 (얼굴 인식 제외)
./install.sh
# 얼굴 인식 질문에 'n' 입력
```

---

## 빠른 설치 가이드 (용량 제한 환경)

```bash
# 1. 디스크 정리 (한 번에 실행)
sudo apt clean && \
sudo apt autoremove -y && \
sudo journalctl --vacuum-time=7d && \
sudo rm -rf /tmp/* /var/tmp/*

# 2. 공간 확인
df -h /

# 3. 설치 실행
cd /path/to/manager/1.9.1
./install.sh

# 4. 질문 응답:
#    - 온라인 설치: y
#    - 얼굴 인식: n (디스크 용량 부족 시)
```

---

## 설치 후 공간 확보

설치 완료 후에도 공간이 필요하면:

```bash
# pip 캐시 삭제
rm -rf ~/.cache/pip

# 빌드 임시 파일 삭제
sudo rm -rf /tmp/*
```

---

## 최소 설치 옵션 (극한의 용량 절약)

얼굴 인식 없이 최소 기능만 설치:

```bash
# 1. 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 2. 필수 패키지만 설치
pip install --no-cache-dir opencv-python pillow configparser

# 3. Tesseract OCR (문자 인식만)
sudo apt install -y tesseract-ocr tesseract-ocr-kor
pip install --no-cache-dir pytesseract
```

**필요 용량**: 약 **5GB**

---

## 문제 해결 체크리스트

설치 전:
- [ ] `df -h /` 실행하여 10GB 이상 여유 확인
- [ ] `sudo apt clean` 실행
- [ ] `sudo journalctl --vacuum-time=7d` 실행
- [ ] `/tmp` 디렉토리 정리

설치 중:
- [ ] 온라인 설치 선택 (y)
- [ ] 얼굴 인식 제외 (n) - 디스크 부족 시

설치 실패 시:
- [ ] `rm -rf venv` 실행
- [ ] `sudo rm -rf /tmp/*` 실행
- [ ] 다시 `./install.sh` 실행

---

## 요약

### 디스크 용량 부족 시 즉시 실행할 명령어

```bash
# 원라이너 (한 줄로 실행)
sudo apt clean && sudo apt autoremove -y && sudo journalctl --vacuum-time=7d && sudo rm -rf /tmp/* && df -h /
```

### 설치 시 선택사항

```
온라인 설치: y
얼굴 인식 설치: n (디스크 10GB 이하 시)
```

이렇게 하면 **최소 5-8GB 확보**되어 안정적으로 설치됩니다!
