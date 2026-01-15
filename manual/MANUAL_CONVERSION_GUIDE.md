# 매뉴얼 변환 가이드

GARAMe Manager 사용자 매뉴얼을 다양한 형식으로 변환하는 방법입니다.

## 생성된 파일

### 📄 DOCX 파일 (Word 문서)

#### 1. 기본 버전 (49KB)
```
GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx
```
- 간단한 변환
- 제목, 내용, 리스트 포함

#### 2. 완성본 버전 (358KB) ⭐ **추천**
```
GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx
```
- ✓ **겉표지** (로고 포함, 버전 정보, 날짜)
- ✓ **목차** (자동 생성)
- ✓ **본문** (서식 적용)
- ✓ **스크린샷** (자동 삽입)
- ✓ **페이지 나누기** (섹션 구분)

### 📊 PPTX 파일 (PowerPoint 프레젠테이션)

```
GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx (96KB)
```
- 표지 슬라이드
- 주요 섹션별 슬라이드
- 교육 및 발표용

---

## 🔄 변환 방법

### 방법 1: 완성본 버전 생성 (추천)

**특징**:
- 겉표지 + 목차 + 스크린샷 포함
- 가장 완성도 높은 문서

**실행 명령**:
```bash
cd ~/Desktop/프로그램/manager/1.9.1
python3 convert_manual_enhanced.py
```

**생성 파일**:
- `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx` (358KB)

**처리 시간**: 약 5-10초

---

### 방법 2: 기본 버전 생성

**특징**:
- DOCX + PPTX 동시 생성
- 빠른 변환

**실행 명령**:
```bash
cd ~/Desktop/프로그램/manager/1.9.1
python3 convert_manual.py
```

**생성 파일**:
- `GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx` (49KB)
- `GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx` (96KB)

**처리 시간**: 약 3-5초

---

## 📸 스크린샷 추가 방법

### 자동 삽입

스크린샷은 다음 폴더에서 자동으로 찾아 삽입됩니다:
```
1.9.1/captures/
```

현재 발견된 스크린샷: **9개**

### 수동으로 더 추가하려면

1. **captures 폴더에 이미지 복사**
   ```bash
   cp /path/to/screenshot.png captures/
   ```

2. **파일명 규칙** (선택사항)
   - `capture_메인화면_YYYYMMDD.png`
   - `capture_설정화면_YYYYMMDD.png`
   - `capture_그래프_YYYYMMDD.png`

3. **변환 스크립트 재실행**
   ```bash
   python3 convert_manual_enhanced.py
   ```

스크린샷이 자동으로 해당 섹션에 삽입됩니다!

---

## 🖼️ 로고 변경

현재 사용 중인 로고:
```
assets/GARAMe.png
```

### 다른 로고 사용하기

1. **새 로고 파일 준비** (PNG, JPG)

2. **assets 폴더에 복사**
   ```bash
   cp /path/to/new_logo.png assets/GARAMe.png
   ```

3. **변환 스크립트 재실행**
   ```bash
   python3 convert_manual_enhanced.py
   ```

---

## 🛠️ 커스터마이징

### 겉표지 수정

`convert_manual_enhanced.py` 파일의 `add_cover_page()` 함수 수정:

```python
# 제목 변경
run = title.add_run("GARAMe Manager")  # ← 이 부분 수정

# 부제목 변경
run = subtitle.add_run("사용자 매뉴얼")  # ← 이 부분 수정

# 버전 변경
run = version.add_run("Version 1.9.1")  # ← 이 부분 수정
```

### 색상 테마 변경

```python
# 제목 색상 (현재: #2C3E50 진한 파랑)
run.font.color.rgb = RGBColor(44, 62, 80)

# 부제목 색상 (현재: #34495E 회색 파랑)
run.font.color.rgb = RGBColor(52, 73, 94)
```

---

## 📖 Ubuntu에서 파일 열기

### DOCX 파일

**LibreOffice Writer로 열기**:
```bash
libreoffice --writer GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx
```

또는 파일 매니저에서 더블클릭

### PPTX 파일

**LibreOffice Impress로 열기**:
```bash
libreoffice --impress GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx
```

---

## 🔧 문제 해결

### 라이브러리 오류

**증상**: `ImportError: No module named 'docx'`

**해결**:
```bash
pip3 install python-docx python-pptx pillow
```

### 로고 삽입 오류

**증상**: `⚠️ 로고 삽입 실패`

**해결**:
1. 로고 파일 존재 확인:
   ```bash
   ls assets/GARAMe.png
   ```

2. 권한 확인:
   ```bash
   chmod 644 assets/GARAMe.png
   ```

### 스크린샷 삽입 오류

**증상**: `⚠️ 이미지 삽입 실패`

**해결**:
1. 이미지 파일 확인:
   ```bash
   ls captures/
   ```

2. 이미지 형식 확인 (PNG, JPG만 지원)

3. 파일 크기 확인 (10MB 이하 권장)

---

## 📊 파일 크기 비교

| 파일 | 크기 | 특징 |
|------|------|------|
| 원본 Markdown | 34KB | 소스 파일 |
| 기본 DOCX | 49KB | 간단한 변환 |
| 완성본 DOCX | 358KB | 로고+목차+이미지 |
| PPTX | 96KB | 프레젠테이션 |

---

## 🎨 출력 형식

### DOCX (Word)
- **용도**: 인쇄, 배포, 아카이빙
- **편집**: 가능
- **호환성**: Microsoft Word, LibreOffice Writer

### PPTX (PowerPoint)
- **용도**: 교육, 발표, 설명
- **편집**: 가능
- **호환성**: Microsoft PowerPoint, LibreOffice Impress

---

## 🚀 빠른 시작

### 완성본 매뉴얼 생성 (한 줄 명령)

```bash
cd ~/Desktop/프로그램/manager/1.9.1 && python3 convert_manual_enhanced.py
```

생성된 파일:
```
✓ GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx
  - 겉표지 ✓
  - 목차 ✓
  - 본문 ✓
  - 스크린샷 ✓
```

---

## 📝 변환 스크립트 비교

| 스크립트 | 출력 | 겉표지 | 목차 | 이미지 |
|---------|------|--------|------|--------|
| `convert_manual.py` | DOCX + PPTX | ✗ | ✗ | ✗ |
| `convert_manual_enhanced.py` | DOCX | ✓ | ✓ | ✓ |

**권장**: `convert_manual_enhanced.py` 사용

---

## 📂 파일 구조

```
1.9.1/
├── GARAMe_MANAGER_사용자매뉴얼_v1.9.1.md          # 원본
├── GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx        # 기본 버전
├── GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx  # 완성본 ⭐
├── GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx        # 프레젠테이션
├── convert_manual.py                             # 기본 변환 스크립트
├── convert_manual_enhanced.py                    # 개선 변환 스크립트 ⭐
├── assets/
│   ├── GARAMe.png                                # 로고
│   └── logo.png
└── captures/
    ├── capture_sensor02_20251030_141556.png      # 스크린샷 1
    ├── capture_sensor02_20251030_141607.png      # 스크린샷 2
    └── ... (총 9개)
```

---

## 💡 팁

### 매뉴얼 업데이트 후

1. Markdown 파일 수정
2. 변환 스크립트 실행
3. 새 DOCX 파일 생성 완료!

### 여러 버전 관리

```bash
# 날짜별로 백업
cp GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx \
   backups/manual_$(date +%Y%m%d).docx
```

### PDF 변환

LibreOffice로 PDF 변환:
```bash
libreoffice --headless --convert-to pdf \
  GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx
```

---

Copyright © 2025 GARAMe Project
