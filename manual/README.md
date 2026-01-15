# 📚 GARAMe Manager 매뉴얼 폴더

이 폴더에는 GARAMe Manager 사용자 매뉴얼과 관련된 모든 파일이 포함되어 있습니다.

## 📄 매뉴얼 파일

### 원본 파일
- **GARAMe_MANAGER_사용자매뉴얼_v1.9.1.md** (34KB)
  - Markdown 원본 파일
  - 수정 및 업데이트용

### DOCX 파일 (Word 문서)

| 파일명 | 크기 | 설명 | 용도 |
|--------|------|------|------|
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx` | 49KB | 기본 변환 | 빠른 미리보기 |
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx` | 358KB | 겉표지+목차+이미지 1개 | 일반 배포용 |
| `GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx` | 3.4MB | **21개 스크린샷 포함** | **최종 배포용** ⭐ |

### PPTX 파일 (PowerPoint)
- **GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx** (96KB)
  - 프레젠테이션 및 교육용

---

## 📸 스크린샷

**screenshots/** 폴더에 21개의 화면 캡처가 포함되어 있습니다.

```
screenshots/
├── screenshot_01.png  - 센서 접속 대기 화면
├── screenshot_02.png  - 메인 화면
├── screenshot_03.png  - 메인 화면 상세
├── screenshot_04.png  - 센서 모니터링
├── screenshot_05.png  - 거울보기 모드
├── screenshot_06.png  - 통신 끊김 화면
├── screenshot_07.png  - 임계값 설정
├── screenshot_08.png  - 안전교육 화면
├── screenshot_09.png  - 안전교육 확인
├── screenshot_10.png  - 포스터 관리
├── screenshot_11.png  - 도면 관리
├── screenshot_12.png  - 얼굴 인식
├── screenshot_13.png  - 안전장구 감지
├── screenshot_14.png  - 접근 제어
├── screenshot_15.png  - 도면 보기
├── screenshot_16.png  - 경고 내역
├── screenshot_17.png  - 그래프 보기
├── screenshot_18.png  - 도면으로 보기
├── screenshot_19.png  - 환경설정
├── screenshot_20.png  - 데이터 관리
└── screenshot_21.png  - 추가 기능
```

---

## 🔧 변환 스크립트

### 1. convert_manual.py
**기본 변환 스크립트**
```bash
python3 convert_manual.py
```
- 출력: DOCX + PPTX
- 겉표지: ✗
- 목차: ✗
- 이미지: ✗
- 처리 시간: ~3초

### 2. convert_manual_enhanced.py
**개선 변환 스크립트**
```bash
python3 convert_manual_enhanced.py
```
- 출력: DOCX (완성본)
- 겉표지: ✓
- 목차: ✓
- 이미지: 1개
- 처리 시간: ~5초

### 3. extract_screenshots_and_update_manual.py ⭐ **권장**
**최종 변환 스크립트**
```bash
python3 extract_screenshots_and_update_manual.py
```
- 출력: DOCX (최종본)
- 겉표지: ✓
- 목차: ✓
- 이미지: 21개 (자동 배치)
- 부록: 전체 스크린샷 모음
- 처리 시간: ~10초

---

## 📖 가이드 문서

### MANUAL_CONVERSION_GUIDE.md
매뉴얼 변환 방법 및 커스터마이징 가이드
- 변환 스크립트 사용법
- 겉표지 수정 방법
- 색상 테마 변경
- 문제 해결

### SCREENSHOTS_README.md
스크린샷 관리 및 매핑 가이드
- 파일 비교표
- 스크린샷 추가 방법
- 매핑 규칙 설명
- 버전별 특징

---

## 🚀 빠른 시작

### 매뉴얼 보기 (Ubuntu)
```bash
# LibreOffice Writer로 열기
libreoffice --writer GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx

# 또는 파일 매니저에서 더블클릭
```

### 매뉴얼 재생성
```bash
# 최종본 생성 (21개 스크린샷 포함)
python3 extract_screenshots_and_update_manual.py

# 완성본 생성 (1개 스크린샷 포함)
python3 convert_manual_enhanced.py

# 기본 버전 생성 (DOCX + PPTX)
python3 convert_manual.py
```

### PDF 변환
```bash
libreoffice --headless --convert-to pdf \
  GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx
```

---

## 📂 폴더 구조

```
manual/
├── 📄 GARAMe_MANAGER_사용자매뉴얼_v1.9.1.md              원본 Markdown
├── 📄 GARAMe_MANAGER_사용자매뉴얼_v1.9.1.docx            기본 DOCX
├── 📄 GARAMe_MANAGER_사용자매뉴얼_v1.9.1_완성본.docx     완성본 DOCX
├── 📄 GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx     최종본 DOCX ⭐
├── 📊 GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx            프레젠테이션
├── 🔧 convert_manual.py                                 기본 변환 스크립트
├── 🔧 convert_manual_enhanced.py                        개선 변환 스크립트
├── 🔧 extract_screenshots_and_update_manual.py          최종 변환 스크립트 ⭐
├── 📚 MANUAL_CONVERSION_GUIDE.md                        변환 가이드
├── 📚 SCREENSHOTS_README.md                             스크린샷 가이드
├── 📚 README.md                                         이 파일
└── 📁 screenshots/                                      스크린샷 폴더 (21개)
```

---

## 🎯 추천 파일

### 최종 배포용
**GARAMe_MANAGER_사용자매뉴얼_v1.9.1_최종본.docx** (3.4MB)
- ✅ 겉표지 (로고 + 버전 정보)
- ✅ 목차 자동 생성
- ✅ 본문 완벽 서식
- ✅ 스크린샷 21개 포함
- ✅ 부록: 전체 화면 모음

### 프레젠테이션용
**GARAMe_MANAGER_사용자매뉴얼_v1.9.1.pptx** (96KB)
- 교육 및 발표용
- 주요 섹션별 슬라이드

---

## 💡 팁

### 매뉴얼 업데이트 시
1. `GARAMe_MANAGER_사용자매뉴얼_v1.9.1.md` 파일 수정
2. 변환 스크립트 실행
3. 새로운 DOCX 파일 자동 생성

### 스크린샷 추가 시
1. 새 스크린샷을 `screenshots/` 폴더에 저장
2. `extract_screenshots_and_update_manual.py` 실행
3. 자동으로 매뉴얼에 삽입됨

### 백업 방법
```bash
# 날짜별 백업
tar -czf manual_backup_$(date +%Y%m%d).tar.gz manual/

# 또는
cp -r manual/ manual_backup_$(date +%Y%m%d)/
```

---

## 🔄 작업 흐름

```
Markdown 작성
     ↓
변환 스크립트 실행
     ↓
DOCX/PPTX 생성
     ↓
배포 또는 인쇄
```

---

## 📞 지원

문제가 발생하면:
1. `MANUAL_CONVERSION_GUIDE.md` 문제 해결 섹션 참조
2. `SCREENSHOTS_README.md` FAQ 섹션 확인
3. Python 라이브러리 재설치:
   ```bash
   pip3 install python-docx python-pptx pillow
   ```

---

## 📋 체크리스트

### 매뉴얼 생성 시
- [ ] Markdown 원본 최신 버전 확인
- [ ] 스크린샷 21개 모두 존재 확인
- [ ] 로고 파일 (assets/GARAMe.png) 확인
- [ ] 변환 스크립트 실행
- [ ] 생성된 DOCX 파일 확인
- [ ] 겉표지, 목차, 이미지 검증
- [ ] PDF 변환 (필요시)

### 배포 전
- [ ] 최종본 DOCX 파일 확인
- [ ] 스크린샷 품질 확인
- [ ] 오타 및 서식 검토
- [ ] 버전 정보 확인 (v1.9.1)
- [ ] 파일명 최종 확인

---

**버전**: v1.9.1
**최종 업데이트**: 2025년 11월 6일
**플랫폼**: Ubuntu Linux 전용

Copyright © 2025 GARAMe Project
