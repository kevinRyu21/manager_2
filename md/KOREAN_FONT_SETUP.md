# 그래프 한글 폰트 설정 가이드

## 문제 증상
그래프에서 한글이 네모 박스(`□□□`)로 표시되거나 깨져서 보이는 경우

## 원인
시스템에 한글을 지원하는 폰트가 설치되어 있지 않거나, matplotlib이 한글 폰트를 찾지 못하는 경우

---

## 해결 방법

### Ubuntu/Linux 환경

#### 1. 나눔 폰트 설치 (권장)

```bash
# 나눔고딕 폰트 설치
sudo apt-get update
sudo apt-get install -y fonts-nanum fonts-nanum-coding

# 폰트 캐시 갱신
fc-cache -fv

# matplotlib 캐시 삭제 (중요!)
rm -rf ~/.cache/matplotlib
```

#### 2. Noto Sans CJK 폰트 설치 (대안)

```bash
# Noto Sans CJK 폰트 설치
sudo apt-get install -y fonts-noto-cjk

# 폰트 캐시 갱신
fc-cache -fv

# matplotlib 캐시 삭제
rm -rf ~/.cache/matplotlib
```

#### 3. 설치 확인

```bash
# 시스템에 설치된 한글 폰트 확인
fc-list :lang=ko

# 또는
fc-list | grep -i nanum
```

**예상 출력**:
```
/usr/share/fonts/truetype/nanum/NanumGothic.ttf: NanumGothic:style=Regular
/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf: NanumBarunGothic:style=Regular
```

---

### 매니저 재시작

폰트 설치 후 **반드시 매니저를 재시작**해야 합니다:

```bash
# 매니저 종료
pkill -f "python.*main.py"

# 매니저 시작
cd /path/to/manager/1.9.3
python3 main.py
```

---

## 확인 방법

### 1. 로그 확인

매니저 시작 시 콘솔에서 다음과 같은 메시지를 확인:

```
[그래프] 한글 폰트 설정: NanumGothic
```

또는

```
[그래프 렌더러] 한글 폰트 설정: NanumGothic
```

### 2. 경고 메시지

한글 폰트를 찾지 못한 경우:

```
[그래프 경고] 한글 폰트를 찾을 수 없습니다. DejaVu Sans 사용 (한글 깨짐 가능)
```

이 경고가 보이면 위의 폰트 설치 과정을 다시 확인하세요.

---

## 지원되는 한글 폰트 목록 (우선순위)

1. **NanumGothic** (나눔고딕) - 최우선
2. **NanumBarunGothic** (나눔바른고딕)
3. **Noto Sans CJK KR** (본고딕)
4. **Noto Sans KR**
5. Pretendard
6. Malgun Gothic (맑은 고딕)

---

## Python 스크립트로 폰트 확인

```python
import matplotlib.font_manager as fm

# 시스템의 모든 폰트 목록
families = [f.name for f in fm.fontManager.ttflist]

# 한글 폰트 찾기
korean_fonts = []
for family in families:
    if any(font in family.lower() for font in ['nanum', 'noto', 'gothic']):
        korean_fonts.append(family)

print("시스템에서 찾은 한글 폰트:")
for font in korean_fonts:
    print(f"  - {font}")
```

---

## 문제 해결 (Troubleshooting)

### 문제 1: 폰트 설치 후에도 한글이 깨짐

**해결 방법**:
```bash
# matplotlib 캐시 완전 삭제
rm -rf ~/.cache/matplotlib
rm -rf ~/.matplotlib

# 시스템 폰트 캐시 갱신
sudo fc-cache -fv

# 매니저 완전 재시작
pkill -9 -f "python.*main.py"
sleep 2
cd /path/to/manager/1.9.3
python3 main.py
```

### 문제 2: fc-list에서는 보이는데 그래프에서 안 보임

**원인**: matplotlib 폰트 캐시가 오래된 경우

**해결 방법**:
```bash
# Python에서 폰트 캐시 갱신
python3 << EOF
import matplotlib.font_manager as fm
fm._rebuild()
print("폰트 캐시가 갱신되었습니다.")
EOF

# matplotlib 캐시 삭제
rm -rf ~/.cache/matplotlib

# 매니저 재시작
```

### 문제 3: 권한 문제로 폰트 설치 실패

**해결 방법**:
```bash
# 사용자 폰트 디렉토리에 설치
mkdir -p ~/.fonts

# 나눔 폰트 다운로드 및 설치
cd ~/.fonts
wget https://github.com/naver/nanumfont/releases/download/VER2.5/NanumFont_TTF_ALL.zip
unzip NanumFont_TTF_ALL.zip
rm NanumFont_TTF_ALL.zip

# 폰트 캐시 갱신
fc-cache -fv
```

---

## 자동 설치 스크립트

다음 스크립트를 사용하면 한 번에 모든 작업을 수행할 수 있습니다:

```bash
#!/bin/bash
# 파일명: install_korean_fonts.sh

echo "=== 한글 폰트 설치 시작 ==="

# 나눔 폰트 설치
echo "1. 나눔 폰트 설치 중..."
sudo apt-get update
sudo apt-get install -y fonts-nanum fonts-nanum-coding

# Noto Sans CJK 폰트 설치
echo "2. Noto Sans CJK 폰트 설치 중..."
sudo apt-get install -y fonts-noto-cjk

# 폰트 캐시 갱신
echo "3. 폰트 캐시 갱신 중..."
sudo fc-cache -fv

# matplotlib 캐시 삭제
echo "4. matplotlib 캐시 삭제 중..."
rm -rf ~/.cache/matplotlib
rm -rf ~/.matplotlib

# Python에서 폰트 캐시 갱신
echo "5. Python 폰트 캐시 갱신 중..."
python3 << EOF
import matplotlib.font_manager as fm
fm._rebuild()
print("폰트 캐시가 갱신되었습니다.")
EOF

# 설치 확인
echo ""
echo "=== 설치된 한글 폰트 목록 ==="
fc-list :lang=ko

echo ""
echo "=== 설치 완료 ==="
echo "매니저를 재시작하면 그래프에서 한글이 정상적으로 표시됩니다."
```

**사용 방법**:
```bash
chmod +x install_korean_fonts.sh
./install_korean_fonts.sh
```

---

## 매니저 v1.9.3 개선사항

- **자동 폰트 탐지**: 시스템에 설치된 한글 폰트를 자동으로 찾아 사용
- **우선순위 설정**: Nanum > Noto > Pretendard > Malgun Gothic 순으로 선택
- **상세 로그**: 선택된 폰트 정보를 콘솔에 출력
- **폴백 지원**: 한글 폰트가 없어도 DejaVu Sans로 폴백 (깨짐 가능)

---

## 지원

문제가 계속되면 다음 정보를 포함하여 문의하세요:

1. 운영체제 버전: `lsb_release -a`
2. Python 버전: `python3 --version`
3. 매니저 로그 (시작 시 출력되는 폰트 관련 메시지)
4. 설치된 폰트 목록: `fc-list :lang=ko`

**문의처**: GARAMe 기술지원팀
**이메일**: support@garame.co.kr
