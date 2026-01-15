# Ubuntu 한글 폰트 설치 가이드

## 문제 증상

거울보기나 안전교육 화면에서 한글이 **네모 박스(□□□)**로 표시되는 문제가 발생합니다.

### 원인
- Ubuntu 시스템에 한글 폰트가 설치되어 있지 않음
- OpenCV의 기본 폰트는 한글을 지원하지 않음
- PIL/Pillow도 한글 폰트가 없으면 네모 박스로 표시

## 해결 방법

### 1. 나눔 폰트 설치 (권장)

```bash
sudo apt update
sudo apt install -y fonts-nanum

# 추가 패키지 (선택 사항, Ubuntu 버전에 따라 없을 수 있음)
sudo apt install -y fonts-nanum-coding fonts-nanum-extra 2>/dev/null || true
```

**참고**: Ubuntu 25에서는 `fonts-nanum-coding`과 `fonts-nanum-extra` 패키지가 없을 수 있습니다. `fonts-nanum`만 설치해도 한글 표시에는 문제가 없습니다.

### 2. 폰트 캐시 갱신

```bash
sudo fc-cache -fv
```

### 3. 설치 확인

```bash
fc-list | grep -i nanum
```

**예상 출력**:
```
/usr/share/fonts/truetype/nanum/NanumGothic.ttf: NanumGothic:style=Regular
/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf: NanumGothic:style=Bold
/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf: NanumBarunGothic:style=Regular
...
```

### 4. 프로그램 재시작

```bash
# 프로그램 종료 후 다시 실행
./run.sh
```

## 다른 한글 폰트 설치 (선택 사항)

### 은 글꼴 (Un Fonts)
```bash
sudo apt install -y fonts-unfonts-core
```

### 한글 글꼴 (Baekmuk)
```bash
sudo apt install -y fonts-baekmuk
```

### D2Coding (개발자 전용 폰트)
```bash
sudo apt install -y fonts-d2coding
```

## 프로그램에서 사용하는 폰트 경로

프로그램은 다음 경로에서 한글 폰트를 찾습니다 (순서대로 검색):

1. `/usr/share/fonts/truetype/nanum/NanumGothic.ttf` (나눔고딕)
2. `/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf` (나눔바른고딕)
3. `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` (DejaVu Sans - 한글 제한적 지원)

위 경로 중 하나라도 존재하면 정상적으로 한글이 표시됩니다.

## 수동 폰트 설치 (인터넷 연결 없을 때)

### 1. 폰트 파일 다운로드

다른 컴퓨터에서 나눔 폰트를 다운로드:
- https://hangeul.naver.com/font (나눔 폰트 공식 사이트)

### 2. 폰트 파일 복사

```bash
# 시스템 폰트 디렉토리 생성
sudo mkdir -p /usr/share/fonts/truetype/nanum

# 폰트 파일 복사 (다운로드한 .ttf 파일들을)
sudo cp NanumGothic*.ttf /usr/share/fonts/truetype/nanum/

# 권한 설정
sudo chmod 644 /usr/share/fonts/truetype/nanum/*.ttf
```

### 3. 폰트 캐시 갱신

```bash
sudo fc-cache -fv
```

## 문제 해결

### 폰트 설치 후에도 네모 박스가 나오는 경우

#### 1. 폰트 경로 확인
```bash
ls -la /usr/share/fonts/truetype/nanum/
```

#### 2. 프로그램 로그 확인
프로그램 실행 시 다음 로그를 확인:
```
한글 폰트 로드 성공: /usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

또는:
```
경고: 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다 (한글이 네모 박스로 표시될 수 있음)
```

#### 3. PIL/Pillow 설치 확인
```bash
python3 -c "from PIL import Image, ImageFont, ImageDraw; print('PIL 사용 가능')"
```

**오류 발생 시**:
```bash
pip3 install Pillow
```

#### 4. 폰트 파일 권한 확인
```bash
ls -la /usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

권한이 `-rw-r--r--` (644)가 아니면:
```bash
sudo chmod 644 /usr/share/fonts/truetype/nanum/*.ttf
```

## 빠른 해결 스크립트

다음 내용을 `install_korean_font.sh` 파일로 저장:

```bash
#!/bin/bash

echo "=== 한글 폰트 설치 시작 ==="

# 1. 시스템 업데이트
echo "1. 시스템 업데이트 중..."
sudo apt update

# 2. 나눔 폰트 설치
echo "2. 나눔 폰트 설치 중..."
sudo apt install -y fonts-nanum fonts-nanum-coding fonts-nanum-extra

# 3. 폰트 캐시 갱신
echo "3. 폰트 캐시 갱신 중..."
sudo fc-cache -fv

# 4. 설치 확인
echo "4. 설치 확인..."
if fc-list | grep -q "NanumGothic"; then
    echo "✓ 나눔 폰트 설치 성공!"
    fc-list | grep -i nanum
else
    echo "✗ 나눔 폰트 설치 실패"
    exit 1
fi

echo ""
echo "=== 한글 폰트 설치 완료 ==="
echo "프로그램을 재시작하면 한글이 정상적으로 표시됩니다."
```

실행:
```bash
chmod +x install_korean_font.sh
./install_korean_font.sh
```

## Ubuntu 버전별 참고사항

### Ubuntu 25.04
```bash
# Ubuntu 25에서는 fonts-nanum만 제공됨
sudo apt install -y fonts-nanum
```

### Ubuntu 22.04/24.04 (이전 버전)
```bash
# 이전 버전에서는 추가 패키지도 사용 가능
sudo apt install -y fonts-nanum fonts-nanum-coding fonts-nanum-extra
```

**중요**: `fonts-nanum` 패키지만으로도 충분합니다. `fonts-nanum-coding`과 `fonts-nanum-extra`는 선택 사항이며, Ubuntu 25에서는 제공되지 않을 수 있습니다.

## 관련 파일

- [src/tcp_monitor/sensor/safety_detector.py](src/tcp_monitor/sensor/safety_detector.py) - 한글 폰트 로딩 로직

## 참고 링크

- 나눔 폰트 공식 사이트: https://hangeul.naver.com/font
- Ubuntu 한글 환경 설정: https://help.ubuntu.com/community/Locale

## 버전 정보

- **작성 날짜**: 2025-11-06
- **작성자**: Claude Code
- **적용 버전**: v1.9.0+
