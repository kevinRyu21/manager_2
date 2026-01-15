# GARAMe Manager v1.9.7 변경 사항

## 릴리스 날짜: 2025-12-08

---

## 주요 변경 사항

### 1. PPE 감지 엔진 업그레이드 (YOLOv10 통합)

#### 새로운 PPE 감지 모듈 추가
- **위치**: `src/tcp_monitor/ppe/`
- **모델**: YOLOv10x (SH17 데이터셋 기반, 17개 클래스)
- **모델 파일**: `models/yolo10x.pt` (64MB)

#### 감지 성능 향상
| 항목 | 이전 (v1.9.6) | 현재 (v1.9.7) |
|------|---------------|---------------|
| PPE 모델 | YOLOv8/v11 (분리) | YOLOv10x (통합) |
| 감지 정확도 | ~85% | ~92.7% mAP50 |
| 장갑 감지 | 착용 여부만 | 좌/우 구분, 개수 표시 |
| 색상 분석 | 기본 | HSV 기반 정밀 분석 |

#### 감지 가능 PPE (6종)
1. **헬멧** (helmet) - 색상 분석 포함
2. **보안경** (glasses)
3. **마스크** (mask)
4. **장갑** (gloves) - 좌/우 구분, 개수 카운트
5. **조끼** (vest) - 색상 분석 포함
6. **안전화** (boots)

#### 안전률 계산 (가중치 기반)
```
헬멧: 40% | 조끼: 25% | 장갑: 15% | 보안경: 10% | 마스크: 5% | 안전화: 5%
```

---

### 2. 새로운 모듈 구조

```
src/tcp_monitor/ppe/
├── __init__.py          # 모듈 초기화
├── detector.py          # PPE 감지 엔진 (YOLOv10)
├── color_analyzer.py    # HSV 색상 분석기
└── visualizer.py        # PPE 상태 시각화
```

#### 주요 클래스
- `PPEDetector`: YOLOv10 기반 PPE 감지 (싱글톤)
- `PPEStatus`: PPE 착용 상태 데이터 클래스
- `PersonDetection`: 사람 + PPE 감지 결과
- `ColorAnalyzer`: HSV 기반 색상 분석
- `PPEVisualizer`: 카메라 화면 오버레이

---

### 3. 안전교육 화면 개선

#### 서명 화면 (safety_signature.py)
- YOLOv10 PPE 감지기 자동 로드
- PPE Visualizer로 실시간 상태 표시
- 장갑 개수 표시 추가 (예: "장갑: 착용 (2개)")
- 기존 감지기와 fallback 호환

---

### 4. 설정 파일 변경

#### config.conf [ENV] 섹션 추가 항목
```ini
ppe_model = yolo10x          # PPE 감지 모델 (yolo10x 권장)
ppe_confidence = 0.25        # 감지 신뢰도 임계값
```

---

## 기술 사항

### 의존성
- ultralytics >= 8.0.0
- torch >= 2.0.0
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- Pillow >= 10.0.0

### 호환성
- Python 3.10+
- Ubuntu 24.04/25.04
- PyTorch 2.6+ 호환 (weights_only 패치 포함)

---

## 마이그레이션 가이드

### v1.9.6에서 업그레이드
1. `models/yolo10x.pt` 파일 복사
2. `src/tcp_monitor/ppe/` 디렉토리 복사
3. config.conf 업데이트 (ppe_model, ppe_confidence 추가)

### 기존 기능 호환
- 기존 `safety_detector.py`는 fallback으로 유지
- 환경설정의 PPE 설정은 그대로 사용 가능

---

## 버그 수정

### 5. 갈색 헬멧 흰색 인식 문제 수정
- **문제**: 갈색 헬멧이 흰색으로 잘못 인식됨
- **원인**: 갈색 헬멧의 HSV 특성 (H 넓은 범위, S 30-45 낮은 채도, V 80-92 중간 밝기)이 기존 무채색 판정 로직에 걸림
- **수정 파일**: `src/tcp_monitor/sensor/safety_detector_v2.py`
- **수정 내용**:
  - `_classify_color` 메서드: 갈색 판별 로직 추가 (흰색/회색 판정 전에 먼저 체크)
  - `_get_dominant_color` 메서드: 갈색 마스크 범위 변경, 무채색 범위 조정
  - 색상 우선순위 적용: `['yellow', 'orange', 'brown', 'red', 'green', 'blue', 'white', 'gray', 'black']`

#### 갈색 판별 로직
```python
# 갈색 헬멧 특성: H 넓은 범위, S 20-70 (낮은 채도), V 50-180 (중간 밝기)
if s >= 20 and s <= 70 and v >= 50 and v <= 180:
    return ('brown', '갈색')
```

#### 색상 마스크 범위
```python
'brown': cv2.inRange(hsv, (0, 20, 50), (180, 70, 180)),
'white': cv2.inRange(hsv, (0, 0, 200), (180, 20, 255)),  # S < 20으로 조정
'gray': cv2.inRange(hsv, (0, 0, 70), (180, 20, 200)),    # S < 20으로 조정
```

---

## 추가 버그 수정 (2025-12-10)

### 6. 화면 캡쳐 기능 개선 (GNOME Wayland 호환)
- **문제**: GNOME Wayland 환경에서 화면 캡쳐 시 검은 화면 또는 UI 멈춤 현상
- **원인**:
  - grim: `compositor doesn't support wlr-screencopy-unstable-v1` 오류 (GNOME은 wlr-screencopy 미지원)
  - gnome-screenshot: 5-10초 타임아웃 발생
  - scrot: Wayland에서 검은/손상된 이미지 생성
- **수정 파일**: `src/tcp_monitor/ui/panel_header.py`
- **수정 내용**:
  - flameshot `--raw` 옵션 사용 (가장 빠르고 안정적)
  - 알림 다이얼로그 포커스 문제 해결 (`transient()`, `grab_set()`, `focus_force()`, `lift()`)
  - 파일 저장 경로를 홈 디렉토리의 `Pictures/screenshots/`로 통일

#### 화면 캡쳐 코드
```python
# flameshot full --raw > 파일 (가장 빠름)
with open(filepath, 'wb') as f:
    result = subprocess.run(
        ['flameshot', 'full', '--raw'],
        stdout=f, stderr=subprocess.PIPE, timeout=3
    )
```

#### 알림 다이얼로그 포커스 수정
```python
notification.transient(self.app)  # 부모 창에 종속
notification.grab_set()  # 모달 - 포커스 강제
notification.focus_force()
notification.lift()
```

### 7. 거울보기 모드 제한
- **문제**: 그래프/도면 모드에서 거울보기 시 화면이 비정상적으로 분할됨
- **수정 파일**: `src/tcp_monitor/ui/panel_header.py`
- **수정 내용**: 그래프/도면 모드에서 거울보기 버튼 비활성화
  - 타일 모드: 거울보기 정상 동작
  - 그래프/도면 모드: 거울보기 버튼 `state="disabled"`

#### 모드별 버튼 상태 제어
```python
if current_mode == "card":
    self.mirror_btn.configure(state="normal")
elif current_mode == "graph":
    self.mirror_btn.configure(state="disabled")
elif current_mode == "blueprint":
    self.mirror_btn.configure(state="disabled")
```

### 8. 캡쳐 매니저 미리보기 오류 수정
- **문제**: Canvas 위젯에 `configure(text=...)` 사용 시 오류 발생
- **원인**: Canvas 위젯은 `text` 옵션을 지원하지 않음
- **수정 파일**: `src/tcp_monitor/ui/capture_manager.py`
- **수정 내용**: `create_text()` 메서드 사용으로 변경

```python
# 수정 전 (오류)
self.preview.configure(text=f"미리보기 실패:\n{e}")

# 수정 후
self.preview.delete("all")
self.preview.create_text(self.preview_w//2, self.preview_h//2,
                         text=f"미리보기 실패:\n{e}",
                         fill="#E74C3C", font=("Pretendard", 12))
```

---

## 의존성 추가 (v1.9.7)

### 시스템 패키지
- **flameshot**: GNOME Wayland 환경 화면 캡쳐용
  ```bash
  sudo apt install -y flameshot
  ```

---

## UI/UX 개선 (2025-12-18)

### 9. 거울보기 PPE 패널 아이콘 추가
- **수정 파일**: `src/tcp_monitor/ui/panel.py`
- **수정 내용**:
  - PPE 항목별 이모지 아이콘 추가
    - ⛑ 안전모 (helmet)
    - 🦺 조끼 (vest)
    - 🥽 보안경 (glasses)
    - 🧤 장갑 (gloves)
    - 😷 마스크 (mask)
    - 👢 안전화 (boots)
  - 🛡 타이틀 아이콘, 📊 안전률 아이콘 추가
  - 착용 상태에 따라 아이콘 색상 변경 (녹색/빨간색)

### 10. 카메라 영역 오버레이 제거
- **수정 파일**: `src/tcp_monitor/ui/panel.py`
- **수정 내용**:
  - 카메라 화면에 PPE 상태 오버레이 제거 (좌측 패널로 이동)
  - 카메라 화면에 안전률 표시 제거 (좌측 패널에 표시)
  - 카메라 영역은 순수 영상만 표시

### 11. 사물 인식 패널 폰트 축소
- **수정 파일**: `src/tcp_monitor/ui/panel.py`
- **수정 내용**:
  - 제목 폰트: 22pt → 15pt (30% 감소)
  - 항목 폰트: 18pt → 13pt (30% 감소)
  - 카테고리 폰트: 18pt → 13pt (30% 감소)
  - 하위 항목 폰트: 16pt → 11pt (30% 감소)
  - 패널 폭: 400px → 300px

### 12. 캡쳐 완료 알림창 확장
- **수정 파일**: `src/tcp_monitor/ui/panel_header.py`
- **수정 내용**:
  - 창 높이: 200px → 240px (20% 확장)
  - 확인 버튼 크기 확대 (width: 10→12, height: 1→2)
  - 버튼 폰트: 12pt → 14pt
  - 하단 여백: 10px → 30px

### 13. 환경설정 폰트 크기 조정
- **수정 파일**: `src/tcp_monitor/ui/environment_settings.py`
- **수정 내용**:
  - 전체 폰트 크기 1.5배 확대
  - 스크롤 캔버스 레이아웃 개선

---

## 알려진 이슈
- YOLOv10x 모델 초기 로딩 시 2-3초 소요 (싱글톤으로 1회만 로드)
- GPU 미사용 시 CPU 모드로 자동 전환

---

## 다음 버전 계획
- [ ] 금지 영역 설정 기능 추가
- [ ] PPE 미착용 경보 기능
- [ ] 안전률 통계 리포트
