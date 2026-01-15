# 📸 매뉴얼 스크린샷 가이드

## 생성된 파일 비교

### 📄 DOCX 파일 3종

| 파일명 | 크기 | 특징 | 용도 |
|--------|------|------|------|
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx` | 49KB | 기본 변환 | 간단한 문서 |
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx` | 358KB | 겉표지+목차+이미지 1개 | 일반 배포용 |
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx` | **3.4MB** ⭐ | **21개 스크린샷 포함** | **최종 완성본** |

---

## ⭐ 최종본 (3.4MB) - 권장!

### 포함 내용
✅ **겉표지** (로고 + 버전 정보)  
✅ **목차** (자동 생성)  
✅ **본문** (서식 적용)  
✅ **스크린샷 21개** (각 섹션에 자동 배치)  
✅ **부록: 화면 캡처 모음** (전체 스크린샷 모음)

### 스크린샷 배치

**본문에 삽입된 스크린샷** (19개):
- 센서 모니터링 화면 (4장)
- 메인 화면 구성 (2장)
- 안전교육 관리 (4장)
- 포스터 관리 (1장)
- 얼굴 인식 시스템 (5장)
- 도면 관리 (1장)
- 기타 (2장)

**부록에 모든 스크린샷 수록** (21개 전체)

---

## 📂 추출된 스크린샷

### 저장 위치
```
/Users/cyber621/Desktop/develop/garam/garami_manager/1.9.1/screenshots/
```

### 파일 목록 (21개)
```
screenshot_01.png - 첫 프로그램 실행시 센서 접속 대기 화면
screenshot_02.png - 센서 접속시 메인 화면
screenshot_03.png - 메인 화면 상세
screenshot_04.png - 센서 모니터링 화면
screenshot_05.png - 거울보기 모드
screenshot_06.png - 센서 통신 끊김 화면
screenshot_07.png - 센서 임계값 설정화면
screenshot_08.png - 안전교육 화면
screenshot_09.png - 안전교육 확인 화면
screenshot_10.png - 안전교육 포스터 관리 화면
screenshot_11.png - 도면관리 화면
screenshot_12.png - 얼굴 인식 시스템
screenshot_13.png - 안전장구 감지
screenshot_14.png - 접근 제어
screenshot_15.png - 도면 보기
screenshot_16.png - 오늘 경고 내역 보기 화면
screenshot_17.png - 그래프 보기
screenshot_18.png - 도면으로 보기 화면
screenshot_19.png - 환경설정
screenshot_20.png - 데이터 관리
screenshot_21.png - 추가 기능
```

---

## 🔄 재생성 방법

### 최종본 다시 만들기

```bash
cd ~/Desktop/프로그램/manager/1.9.1
python3 extract_screenshots_and_update_manual.py
```

**처리 시간**: 약 5-10초  
**결과**: `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx` (3.4MB)

---

## 📖 파일 열기 (Ubuntu)

### LibreOffice Writer로 열기
```bash
libreoffice --writer GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx
```

또는 파일 매니저에서 더블클릭

---

## 🎨 스크린샷 추가/변경

### 새 스크린샷 추가하기

1. **스크린샷 촬영** (Ubuntu에서 프로그램 실행)
   ```bash
   gnome-screenshot
   # 또는
   Ctrl + Alt + PrtScn
   ```

2. **screenshots 폴더에 저장**
   ```bash
   cp /path/to/new_screenshot.png screenshots/screenshot_22.png
   ```

3. **스크립트 수정** (선택사항)
   
   `extract_screenshots_and_update_manual.py` 파일의 `screenshot_mapping` 수정:
   ```python
   screenshot_mapping = {
       '새로운 기능': ['screenshot_22.png'],  # ← 추가
       '메인 화면': ['screenshot_02.png', 'screenshot_03.png'],
       # ...
   }
   ```

4. **매뉴얼 재생성**
   ```bash
   python3 extract_screenshots_and_update_manual.py
   ```

---

## 🔧 스크린샷 매핑 커스터마이징

### 현재 매핑 규칙

| 키워드 | 스크린샷 |
|--------|----------|
| `첫 프로그램 실행` | screenshot_01.png |
| `메인 화면` | screenshot_02.png, screenshot_03.png |
| `센서 모니터링` | screenshot_02.png, screenshot_04.png |
| `거울 모드` | screenshot_05.png |
| `센서 통신 끊김` | screenshot_06.png |
| `임계값 설정` | screenshot_07.png |
| `안전교육` | screenshot_08.png, screenshot_09.png |
| `포스터 관리` | screenshot_10.png |
| `도면 관리` | screenshot_11.png |
| `얼굴 인식` | screenshot_12.png |
| `안전장구 감지` | screenshot_13.png |
| `접근 제어` | screenshot_14.png |
| `도면 보기` | screenshot_15.png |
| `환경설정` | screenshot_16.png |

**자동 매칭**: 매뉴얼의 섹션 제목에 키워드가 포함되면 해당 스크린샷이 자동으로 삽입됩니다.

---

## 📊 매뉴얼 버전 비교 요약

### 기본 버전 (49KB)
```
✓ 제목, 내용
✗ 겉표지
✗ 목차
✗ 이미지
```

### 완성본 버전 (358KB)
```
✓ 제목, 내용
✓ 겉표지 (로고)
✓ 목차
✓ 이미지 1개
```

### 최종본 버전 (3.4MB) ⭐ **권장**
```
✓ 제목, 내용
✓ 겉표지 (로고)
✓ 목차
✓ 이미지 21개 (본문 배치)
✓ 부록 (전체 스크린샷 모음)
```

---

## 💡 팁

### PDF 변환
```bash
libreoffice --headless --convert-to pdf \
  GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx
```

### 파일 크기 줄이기
이미지 품질을 낮추려면:
1. LibreOffice로 DOCX 열기
2. 이미지 우클릭 → 압축
3. 저장

---

## 📝 3가지 스크립트 비교

| 스크립트 | 출력 | 겉표지 | 목차 | 이미지 | 처리시간 |
|---------|------|--------|------|--------|---------|
| `convert_manual.py` | DOCX + PPTX | ✗ | ✗ | ✗ | 3초 |
| `convert_manual_enhanced.py` | DOCX | ✓ | ✓ | 1개 | 5초 |
| `extract_screenshots_and_update_manual.py` | DOCX | ✓ | ✓ | **21개** | 10초 |

**최종 배포용**: `extract_screenshots_and_update_manual.py` 사용 권장!

---

## 🚀 빠른 명령

### 최종본 생성 (한 줄)
```bash
cd ~/Desktop/프로그램/manager/1.9.1 && python3 extract_screenshots_and_update_manual.py
```

### 스크린샷 확인
```bash
ls -lh screenshots/
```

### 매뉴얼 열기
```bash
libreoffice --writer GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx
```

---

Copyright © 2025 GARAMe Project
