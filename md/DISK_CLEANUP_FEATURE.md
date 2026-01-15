# 디스크 용량 자동 정리 기능

## 개요

GARAMe Manager v1.9.2부터 **install.sh** 및 **create_distribution.sh** 스크립트에 디스크 용량 자동 정리 기능이 추가되었습니다.

## 적용 파일

1. **install.sh** (v1.9.1, v1.9.2)
2. **create_distribution.sh** (v1.9.2)

---

## install.sh 디스크 정리 기능

### 실행 시점

**설치 시작 전 자동 실행**:
```bash
./install.sh
```

### 정리 항목

#### 1. APT 패키지 캐시 정리
```bash
sudo apt clean           # 다운로드한 .deb 파일 삭제
sudo apt autoclean       # 오래된 패키지 캐시 삭제
sudo apt autoremove -y   # 불필요한 패키지 자동 제거
```

**예상 확보 용량**: 500MB ~ 2GB

#### 2. 임시 파일 정리
```bash
sudo rm -rf /tmp/*           # 시스템 임시 파일
sudo rm -rf /var/tmp/*       # 변수 임시 파일
rm -rf ~/.cache/pip/*        # pip 캐시
```

**예상 확보 용량**: 100MB ~ 500MB

#### 3. 이전 가상환경 삭제
```bash
rm -rf venv/
```

**예상 확보 용량**: 1GB ~ 3GB (이전 설치가 있는 경우)

#### 4. Python 캐시 파일 삭제
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

**예상 확보 용량**: 10MB ~ 100MB

#### 5. 이전 빌드 파일 삭제
```bash
rm -rf build/ dist/ *.egg-info/
```

**예상 확보 용량**: 50MB ~ 500MB

#### 6. 오래된 로그 파일 정리
```bash
find logs -type f -name "*.log" -mtime +30 -delete
```

**조건**: 30일 이상 된 로그 파일만 삭제

**예상 확보 용량**: 10MB ~ 200MB

### 디스크 공간 확인

#### 정리 후 메시지
```
[SUCCESS] 디스크 정리 완료. 사용 가능 공간: 18G
```

#### 최소 공간 요구사항

**15GB 이상 필요**:
- dlib 빌드: 약 5-8GB
- Python 패키지: 약 4-5GB
- 시스템 패키지: 약 1-2GB
- 여유 공간: 약 3-5GB

**15GB 미만인 경우**:
```
[WARNING] 디스크 여유 공간이 부족합니다 (12GB < 15GB)
[WARNING] dlib 빌드 시 디스크 부족으로 실패할 수 있습니다

계속 진행하시겠습니까? (y/n)
```

사용자 선택:
- **y**: 계속 진행 (위험 감수)
- **n**: 설치 중단

### 실행 로그 예시

```bash
$ ./install.sh

=========================================
  GARAMe Manager v1.9.2
  통합 설치 스크립트
  Ubuntu 25 전용
=========================================

[INFO] 디스크 용량 확보 중...
[INFO]   - APT 패키지 캐시 정리 중...
[INFO]   - 임시 파일 정리 중...
[INFO]   - 이전 가상환경 삭제 중...
[INFO]   - Python 캐시 파일 삭제 중...
[INFO]   - 이전 빌드 파일 삭제 중...
[INFO]   - 오래된 로그 파일 정리 중...
[SUCCESS] 디스크 정리 완료. 사용 가능 공간: 18G

[INFO] 설치를 시작합니다...
```

---

## create_distribution.sh 디스크 정리 기능

### 실행 시점

**배포 패키지 생성 전 자동 실행**:
```bash
./create_distribution.sh
```

### 정리 항목

#### 1. 이전 배포 파일 삭제
```bash
rm -rf GARAMe_Manager_*_Distribution
rm -rf GARAMe_Manager_*_Distribution.tar.gz
```

**예상 확보 용량**: 50MB ~ 300MB (이전 배포가 있는 경우)

#### 2. 임시 파일 정리
```bash
rm -rf temp_src_*        # 암호화 임시 파일
rm -rf obfuscated_*      # 암호화 출력 파일
```

**예상 확보 용량**: 10MB ~ 50MB

#### 3. Python 캐시 삭제
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

**예상 확보 용량**: 5MB ~ 30MB

#### 4. pip 캐시 정리
```bash
rm -rf ~/.cache/pip/*
```

**예상 확보 용량**: 100MB ~ 500MB

### 디스크 공간 확인

#### 정리 후 메시지
```
[SUCCESS] 디스크 정리 완료. 사용 가능 공간: 25G
```

#### 최소 공간 요구사항

**5GB 이상 필요**:
- 배포 패키지 크기: 약 1-2GB (압축 전)
- 압축 파일: 약 500MB ~ 1GB
- PyArmor 암호화 임시: 약 1GB
- 여유 공간: 약 2GB

**5GB 미만인 경우**:
```
[WARNING] 디스크 여유 공간이 부족합니다 (3GB < 5GB)
[WARNING] 배포 패키지 생성에 실패할 수 있습니다
```

**참고**: 경고만 표시하고 계속 진행 (배포는 작은 용량으로도 가능)

### 실행 로그 예시

```bash
$ ./create_distribution.sh

=========================================
  GARAMe Manager v1.9.2
  배포 패키지 생성
=========================================

[INFO] 디스크 용량 확보 중...
[INFO]   - 이전 배포 파일 삭제 중...
[INFO]   - 임시 파일 정리 중...
[INFO]   - Python 캐시 파일 삭제 중...
[SUCCESS] 디스크 정리 완료. 사용 가능 공간: 25G

[INFO] 배포 디렉토리 생성 중: GARAMe_Manager_1.9.2_Ubuntu25_Distribution
```

---

## 수동 디스크 정리

### 추가 정리가 필요한 경우

#### 1. 저널 로그 정리
```bash
sudo journalctl --vacuum-time=7d    # 7일 이상 된 로그
sudo journalctl --vacuum-size=500M  # 500MB 이상 로그
```

**예상 확보 용량**: 500MB ~ 2GB

#### 2. Docker 정리 (Docker 사용 시)
```bash
docker system prune -a --volumes
```

**예상 확보 용량**: 1GB ~ 10GB

#### 3. snap 패키지 정리
```bash
sudo snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
    sudo snap remove "$snapname" --revision="$revision"
done
```

**예상 확보 용량**: 500MB ~ 2GB

#### 4. 오래된 커널 정리
```bash
sudo apt autoremove --purge
```

**예상 확보 용량**: 200MB ~ 1GB

#### 5. 썸네일 캐시 정리
```bash
rm -rf ~/.cache/thumbnails/*
```

**예상 확보 용량**: 50MB ~ 500MB

---

## 디스크 용량 확인 명령어

### 전체 디스크 사용량
```bash
df -h
```

출력 예시:
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   32G   18G  65% /
```

### 현재 디렉토리 용량
```bash
du -sh .
```

출력 예시:
```
1.5G    .
```

### 하위 디렉토리별 용량 (정렬)
```bash
du -h --max-depth=1 . | sort -hr
```

출력 예시:
```
1.5G    .
800M    ./venv
500M    ./src
200M    ./logs
```

### 큰 파일 찾기 (100MB 이상)
```bash
find . -type f -size +100M -exec ls -lh {} \; | awk '{print $9 ": " $5}'
```

---

## 트러블슈팅

### 문제 1: 디스크 공간 부족으로 설치 실패

**증상**:
```
[ERROR] No space left on device
```

**해결**:
1. 수동 디스크 정리 실행
2. 불필요한 파일 삭제
3. 다른 파티션으로 이동

### 문제 2: 임시 파일 삭제 권한 오류

**증상**:
```
rm: cannot remove '/tmp/...': Permission denied
```

**해결**:
```bash
sudo rm -rf /tmp/*
```

### 문제 3: venv 삭제 실패

**증상**:
```
rm: cannot remove 'venv/...': Device or resource busy
```

**해결**:
```bash
# 가상환경 비활성화
deactivate

# venv 삭제
rm -rf venv
```

---

## 버전별 변경사항

### v1.9.2 (2025-11-11)
- ✅ install.sh에 디스크 정리 기능 추가
- ✅ create_distribution.sh에 디스크 정리 기능 추가
- ✅ 15GB 최소 공간 확인 추가
- ✅ 사용자 확인 프롬프트 추가

### v1.9.1 (2025-11-10)
- ✅ install.sh에 디스크 정리 기능 추가

### v1.9.0 이전
- ❌ 디스크 정리 기능 없음

---

## 요약

| 스크립트 | 정리 시점 | 최소 공간 | 예상 확보 |
|---------|----------|----------|----------|
| install.sh | 설치 시작 전 | 15GB | 1GB ~ 5GB |
| create_distribution.sh | 배포 생성 전 | 5GB | 200MB ~ 1GB |

**자동 정리 항목**:
- ✅ APT 캐시
- ✅ 임시 파일
- ✅ Python 캐시
- ✅ 이전 가상환경
- ✅ 이전 빌드 파일
- ✅ 오래된 로그 (30일+)
- ✅ 이전 배포 패키지

**수동 정리 필요**:
- ⚠️ 저널 로그
- ⚠️ Docker 이미지
- ⚠️ snap 패키지
- ⚠️ 오래된 커널

---

## 관련 문서

- [DISK_SPACE_GUIDE.md](DISK_SPACE_GUIDE.md) - 디스크 공간 관리 가이드
- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - 설치 가이드
- [VERSION_1.9.2_CHANGES.md](VERSION_1.9.2_CHANGES.md) - v1.9.2 변경사항
