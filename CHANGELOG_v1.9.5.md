# GARAMe Manager v1.9.5 변경 사항

## 2024-11-24 업데이트 (PPE 모델 추가)

### PPE 전용 YOLO 모델 다운로드 및 적용
- **파일**: `models/ppe_yolov8m.pt` (51MB)
- **출처**: Hugging Face - keremberke/yolov8m-protective-equipment-detection
- **감지 항목**:
  - 헬멧(Helmet) ✓
  - 장갑(Glove) ✓
  - 보안경/고글(Goggles) ✓
  - 안전화(Shoes) ✓
  - 마스크(Mask) ✓
  - 조끼(Vest) - Legacy 색상 분석 사용 (모델에 없음)

### 동적 PPE 클래스 매핑
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **변경**: 하드코딩된 클래스 ID → 모델에서 동적으로 클래스 이름 파싱
- **장점**: 다른 PPE 모델로 교체해도 자동으로 클래스 매핑

### AI 추론 성능 최적화 (백그라운드 스레드)
- **파일**: `src/tcp_monitor/ui/panel.py`
- **변경**:
  - AI 추론을 메인 스레드 → 백그라운드 스레드로 분리
  - 15프레임마다 AI 추론 (약 2fps)
  - UI 블로킹 없이 실시간 카메라 영상 표시
- **결과**: 카메라 화면 끊김 현상 해결

### PPE 상태 화면 표시 추가
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **변경**: `draw_results()` 함수에 PPE 상태 표시 추가
- **표시 항목** (좌측 상단):
  - 헬멧: O/X
  - 조끼: O/X
  - 보안경: O/X
  - 장갑: O/X
  - 안전화: O/X
- 착용 시 녹색(O), 미착용 시 빨간색(X)

---

## 2024-11-23 업데이트

### 주요 수정 사항

#### 1. 카메라 버퍼링 문제 해결
- **파일**: `src/tcp_monitor/ui/panel.py`
- **문제**: 카메라 화면이 정지하거나 지연되는 현상
- **해결**: `grab()` 메서드로 오래된 프레임을 버퍼에서 제거 후 최신 프레임만 읽도록 수정

#### 2. 한글 폰트 출력 문제 해결 (????)
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **문제**: 얼굴 인식 결과의 한글 이름이 `????`로 표시
- **해결**: `cv2.putText()` → PIL 기반 `_put_korean_text()` 메서드로 교체
- NanumGothic 폰트를 사용하여 한글 텍스트 렌더링

#### 3. 안전교육 서명 다이얼로그 누락 문제 해결
- **파일**: `src/tcp_monitor/ui/safety_signature.py` (신규 생성)
- **문제**: 안전교육에서 "얼굴촬영 및 서명 확인" 버튼 클릭 시 무반응
- **해결**: `SafetySignatureDialog` 클래스 구현
  - 얼굴 촬영 기능 (카메라 활성화 시)
  - 서명 캔버스 (마우스/터치 서명)
  - 얼굴 인식 연동 (이름 자동 인식)

#### 4. 카메라 충돌 (Device busy) 해결
- **파일**: `src/tcp_monitor/ui/safety_education.py`
- **문제**: 거울보기와 안전교육이 동시에 카메라를 열려고 해서 충돌
- **해결**:
  - 안전교육 시작 시 거울보기 카메라를 먼저 해제
  - 안전교육 종료 시 거울보기 카메라 자동 재시작

#### 5. YOLO 모델 중복 로드 문제 해결
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **문제**: YOLO 모델이 4번 로드되어 메모리 낭비 및 로딩 지연
- **해결**: `get_shared_yolo_model()` 싱글톤 함수 추가
  - YOLO 모델이 한 번만 로드됨
  - InsightFace도 동일하게 싱글톤 패턴 적용

#### 6. 소속(department) 표시 추가
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **문제**: 얼굴 인식 시 소속이 표시되지 않음
- **해결**: `department` 필드 표시 추가 (소속이 있으면 소속, 없으면 사원번호 표시)

### 기술적 세부사항

#### 한글 텍스트 렌더링
```python
def _put_korean_text(self, frame, text, position, color=(0, 255, 0), font_size=24):
    """PIL을 사용하여 한글 텍스트를 프레임에 그리기"""
    # BGR -> RGB 변환
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(pil_img)
    # NanumGothic 폰트 사용
    font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", font_size)
    draw.text(position, text, font=font, fill=rgb_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
```

#### 카메라 버퍼 비우기
```python
# 버퍼 비우기: 오래된 프레임 제거 (버퍼링 방지)
for _ in range(2):
    self.mirror_camera.grab()
# 최신 프레임 읽기
ret, frame = self.mirror_camera.read()
```

#### 모델 싱글톤 패턴
```python
_shared_yolo_model = None
_shared_yolo_initialized = False

def get_shared_yolo_model():
    global _shared_yolo_model, _shared_yolo_initialized
    if _shared_yolo_initialized:
        return _shared_yolo_model
    _shared_yolo_initialized = True
    # 모델 로드...
    return _shared_yolo_model
```

### 의존성
- Python 3.13+
- InsightFace (얼굴 인식)
- Ultralytics YOLOv11 (객체 감지)
- OpenCV (카메라/영상 처리)
- Pillow (한글 텍스트 렌더링)
- gTTS (음성 알림)

### 알려진 제한사항
- PPE 전용 YOLO 모델이 없으면 기본 YOLO 모델 사용 (객체 인식 정확도 낮음)
- GPU 가속은 CUDA 12.1 필요
