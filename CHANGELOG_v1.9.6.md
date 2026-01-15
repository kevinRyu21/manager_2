# GARAMe Manager v1.9.6 변경 사항

## 2025-11-27 업데이트

### 안전교육 화면 개선

#### 1. 안전교육 화면에서 메뉴 비활성화
- **파일**: `src/tcp_monitor/ui/safety_education.py`, `src/tcp_monitor/ui/app.py`
- 안전교육 화면 표시 시 "설정", "보기" 메뉴 비활성화
- 안전교육 닫을 때 메뉴 다시 활성화
- `self.menubar` 속성 추가하여 메뉴바 접근 가능하도록 수정

#### 2. 이전/다음 버튼 가시성 개선
- **파일**: `src/tcp_monitor/ui/safety_education.py`
- 버튼 글자색: 흰색 → 검정색 (#000000)
- 배경색: 더 밝은 파란색 (#5DADE2)
- 폰트 크기: 14 → 16
- 버튼 크기: width=12, height=2

#### 3. 카메라 공유 및 리소스 관리 개선
- **파일**: `src/tcp_monitor/ui/safety_education.py`, `src/tcp_monitor/ui/safety_signature.py`
- 안전교육 카메라를 서명 화면에서 공유하여 빠른 시작
- 안전교육 닫을 때 카메라 해제 후 거울보기 버튼 자동 활성화
- `_update_mirror_buttons_after_close()` 함수 추가

### 얼굴 촬영 및 서명 화면 개선

#### 4. 얼굴 인식 기능 수정
- **파일**: `src/tcp_monitor/ui/safety_signature.py`
- `detect_all(frame, use_background=False)` → `detect_all(frame)` 수정 (잘못된 파라미터 제거)
- 안전교육의 SafetyEquipmentDetector 공유하여 얼굴 인식 정확도 향상
- 디버그 로그 추가 (use_insightface, face_recognition_enabled, face_db, face_app 상태 출력)
- **미등록 얼굴 촬영 버튼 활성화**: 미등록/미인식 얼굴도 촬영 버튼 활성화 (주황색 버튼)
  - 등록된 얼굴: 녹색 버튼 "📷 촬영 (이름)"
  - 미등록 얼굴: 주황색 버튼 "📷 촬영 (미등록 얼굴)"

### 보기 메뉴 기능 추가 및 수정

#### 5. 보기 메뉴에 화면 전환 기능 추가
- **파일**: `src/tcp_monitor/ui/app.py`
- 🪞 거울보기, 📊 타일 보기, 📈 그래프 보기, 🗺️ 도면 보기 메뉴 추가
- `_get_current_panel()` 함수 수정: 탭 프레임에서 직접 SensorPanel 찾기
- 올바른 메서드 호출: `switch_to_card_mode()`, `switch_to_graph_mode()`, `switch_to_blueprint_mode()`

#### 6. 거울보기 버튼 동기화
- **파일**: `src/tcp_monitor/ui/panel.py`
- 보기 메뉴에서 거울보기 활성화 시 헤더 버튼 텍스트 "거울끄기"로 변경
- 거울보기 비활성화 시 헤더 버튼 텍스트 "거울보기"로 복원

### 설치 스크립트 개선

#### 7. GPU 가속 옵션 제거
- **파일**: `install.sh`
- 설치 시 GPU 가속 선택 질문 제거
- CPU 모드로만 설치 (코드에서 GPU 미사용)
- 불필요한 PyTorch GPU 버전 및 onnxruntime-gpu 설치 제거

#### 8. 배포 스크립트 PyInstaller 빌드 수정
- **파일**: `create_distribution.sh`
- **문제**: spec 파일이 `--onefile` 모드인데 스크립트가 `--onedir` 모드(디렉토리) 기대
- **수정**: `dist/garame_manager` 단일 파일 확인으로 변경
- run.sh 개선: PyInstaller 실행 파일 있으면 자동 사용, 없으면 Python 소스 모드

### 해시 체인 무결성 검증 시스템 (특허 관련)

#### 9. IntegrityManager 모듈 구현
- **파일**: `src/tcp_monitor/utils/integrity_manager.py` (신규)
- **특허 청구항**: 1(f), 6(g), 9 관련
- SHA-256 기반 해시 체인 구현 (블록체인 유사 구조)
- 기능:
  - `calculate_file_hash()`: 개별 파일 해시 계산
  - `calculate_combined_hash()`: 여러 파일의 통합 해시
  - `calculate_chain_hash()`: 체인 해시 (통합해시 + 이전체인해시)
  - `add_record()`: 새 기록 추가 및 체인 연결
  - `verify_record()`: 단일 기록 무결성 검증
  - `verify_chain()`: 체인 연속성 검증
  - `verify_all()`: 전체 시스템 검증
  - `create_export_archive()`: 기간별 반출 ZIP 생성

#### 10. 안전교육 기록 해시 체인 연동
- **파일**: `src/tcp_monitor/ui/safety_education.py`, `src/tcp_monitor/ui/safety_signature.py`
- **특허 청구항**: 2 관련
- 안전교육 완료 시 자동으로:
  - 메타데이터 JSON 생성 (이름, 안전장구, 교육정보, 타임스탬프)
  - 해시 체인에 기록 등록
  - .hash 파일에 체인 정보 포함
- 서명 화면에서 안전장구 착용 정보 수집 및 전달

#### 11. 무결성 검증 UI
- **파일**: `src/tcp_monitor/ui/integrity_verification.py` (신규)
- **특허 청구항**: 9 관련
- 관리자 메뉴 > "보기" > "무결성 검증"
- 기능:
  - 전체/최근/오류 기록 검증
  - 실시간 진행률 표시
  - 상세 결과 Treeview (통과/실패/누락/체인오류)
  - 결과 JSON 저장

#### 12. 기록 반출 UI
- **파일**: `src/tcp_monitor/ui/export_archive.py` (신규)
- **특허 청구항**: 3, 7 관련
- 관리자 메뉴 > "보기" > "기록 반출"
- 기능:
  - 기간 선택 (시작일~종료일)
  - 빠른 선택 (오늘/7일/30일/이번달/전체)
  - 반출 목적, 반출자 기록
  - ZIP 아카이브 생성:
    - `records/`: 이미지+메타데이터 파일
    - `chain_verification/`: 해시체인, 검증보고서, 독립검증도구
    - `export_manifest.json`: 반출 정보

### 사람 감지 영역 개선

#### 13. 사람 감지 박스 크기 문제 해결
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`
- **문제**: PPE 모델(ppe_helmet_vest.pt)이 헬멧/조끼 영역만 감지하여 person_box가 너무 작음
  - 머리 끝까지 도달하지 않음 (얼굴 위에서 끝남)
  - 손을 인식하지 못함
  - 몸통만 인식하는 것처럼 보임
- **원인**: PPE 전용 모델은 안전장비 감지에 최적화되어 사람 전체 바운딩 박스를 제공하지 않음
- **해결**: YOLO 기본 모델(yolo11n.pt)을 보조 모델로 추가하여 사람 전체 감지
  - `get_shared_yolo_person_model()` 함수 추가: 사람 감지 전용 기본 모델 로드
  - `_is_small_person_box()` 함수 추가: person_box가 너무 작은지 판단
  - PPE 모델의 person_box가 없거나 작으면 기본 모델로 사람 전체 감지
  - 더 큰 박스로 교체하여 머리 끝부터 발끝까지 표시
- **코드**:
```python
# 사람 감지 보조 모델 (PPE 모델이 person을 감지하지 못한 경우)
if self.yolo_person_model and (ppe_detections['person'] is None or
                                self._is_small_person_box(ppe_detections['person'], h, w)):
    person_results = self.yolo_person_model(frame, classes=[0])  # person만 감지
    # 가장 큰 사람 박스 사용
```

### 변경된 파일 목록 (11.27)
1. `src/tcp_monitor/ui/app.py` - menubar 속성 추가, 보기 메뉴 기능 추가, 무결성 검증/반출 메뉴 추가
2. `src/tcp_monitor/ui/safety_education.py` - 메뉴 비활성화, 해시 체인 연동, 메타데이터 JSON 생성
3. `src/tcp_monitor/ui/safety_signature.py` - 얼굴 인식 수정, 안전장구 정보 수집 기능 추가
4. `src/tcp_monitor/ui/panel.py` - 거울보기 버튼 동기화
5. `src/tcp_monitor/sensor/safety_detector.py` - 사람 감지 보조 모델 추가
6. `src/tcp_monitor/utils/integrity_manager.py` - **신규** 해시 체인 무결성 관리 모듈
7. `src/tcp_monitor/ui/integrity_verification.py` - **신규** 무결성 검증 대화상자
8. `src/tcp_monitor/ui/export_archive.py` - **신규** 기록 반출 대화상자
9. `install.sh` - GPU 가속 옵션 제거, CPU 모드 전용
10. `create_distribution.sh` - PyInstaller --onefile 모드 지원, run.sh 개선

---

## 2025-11-25 업데이트

### 주요 수정 사항

#### 1. YOLO 모델 로드 문제 해결 (PyTorch 2.6+ 호환)
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`
- **문제**: PyTorch 2.6+ 버전에서 `weights_only=True` 기본값으로 인해 YOLO 모델 로드 실패
  - 오류: `WeightsUnpickler error: Unsupported global: GLOBAL torch.nn.modules.container.Sequential`
- **해결**:
  - `torch.load` 함수를 임시로 패치하여 `weights_only=False`로 모델 로드
  - 모델 로드 완료 후 원래 `torch.load` 복원
- **코드**:
```python
def get_shared_yolo_model():
    # PyTorch 2.6+ weights_only 문제 해결: 임시로 기본값 변경
    original_load = torch.load
    torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
    # 모델 로드...
    torch.load = original_load  # 복원
```

#### 2. 카메라 시작 속도 최적화
- **파일**: `src/tcp_monitor/sensor/safety_detector.py`, `safety_detector_v2.py`, `main.py`
- **문제**: 카메라 실행 시 InsightFace 모델 5개를 순차적으로 로드하여 느림
- **해결**:
  - InsightFace `det_size`를 (640, 640) → (320, 320)으로 변경 (빠른 감지)
  - `allowed_modules=['detection', 'recognition']` 설정으로 불필요한 모델 제외 (5개 → 3개)
  - `preload_models_async()` 함수 추가: 앱 시작 시 백그라운드에서 모델 미리 로드
- **결과**: 카메라 시작 시간 대폭 단축

#### 3. 센서 접속 시 탭 포커싱 복구
- **파일**: `src/tcp_monitor/ui/app.py`
- **문제**: 센서 접속 시 해당 탭으로 자동 포커싱이 작동하지 않음
- **해결**:
  - 기존: `_focus_first_connected_tab()` 함수로 모든 패널 순회
  - 변경: 현재 접속한 패널(`p.master`)로 직접 탭 선택
  - heartbeat(빈 데이터)와 실제 데이터 모두에서 탭 포커싱 처리
- **코드**:
```python
# 새로 접속한 센서 탭으로 자동 포커싱
try:
    self.nb.select(p.master)
    print(f"[탭 포커싱] 접속된 센서 탭 '{key}' 선택됨")
except Exception as e:
    print(f"[센서 접속] 탭 포커싱 오류: {e}")
```

#### 4. 배경학습 기능 제거
- **삭제된 파일**: `src/tcp_monitor/ui/background_learning_dialog.py`
- **수정된 파일**:
  - `src/tcp_monitor/ui/environment_settings.py` - 배경학습 버튼 및 함수 제거
  - `src/tcp_monitor/ui/panel.py` - 배경학습 인식률 표시 제거
  - `src/tcp_monitor/ui/app.py` - 전역 배경학습 변수 제거
  - `src/tcp_monitor/sensor/safety_detector.py` - use_background 파라미터 및 bg_subtractor 제거
  - `src/tcp_monitor/sensor/safety_detector_v2.py` - 동일 수정
- **사유**:
  - 배경학습 기능이 실제로 구현되지 않았음 (`use_background` 파라미터가 전달되지만 실제 감지 로직에서 사용되지 않음)
  - YOLO + InsightFace 기반 AI 감지가 배경 분리 없이도 정확하게 동작
  - 불필요한 UI 복잡성 제거

#### 5. 헬멧 색상 감지 정확도 개선
- **문제**: 헬멧 색상이 조끼 색상으로 잘못 표시됨
- **원인**: YOLO가 감지한 헬멧 bbox에 상체(조끼) 영역이 포함됨
- **해결**: 헬멧 bbox의 상단 60%만 사용하여 색상 추출
- **코드**:
```python
# 헬멧 색상 감지 (bbox의 상단 60%만 사용)
helmet_bbox = xyxy.copy()
helmet_height = helmet_bbox[3] - helmet_bbox[1]
helmet_bbox[3] = helmet_bbox[1] + helmet_height * 0.6  # 상단 60%만
color_info = self._detect_color(frame, helmet_bbox)
```

#### 6. 마스크 감지 기능 추가
- **문제**: 기존 `ppe_helmet_vest.pt` 모델에 마스크 클래스 없음
- **해결**: `ppe_yolov8m.pt` 보조 모델을 사용하여 마스크 감지
- **구현**:
  - `get_shared_yolo_mask_model()` 함수 추가: 마스크 전용 모델 로드
  - 메인 모델 (헬멧/조끼) + 보조 모델 (마스크) 병행 사용
  - UI에 '마스크' 항목 추가 (헬멧, 조끼 다음)
- **코드**:
```python
# 마스크 보조 모델로 마스크 감지
if self.has_mask_model and self.yolo_mask_model:
    mask_results = self.yolo_mask_model(frame, conf=0.30)
    # 마스크 감지 처리...
```

#### 7. 저사양 시스템 성능 최적화
- **대상 시스템**: Intel Celeron N5095 (4코어 2.0GHz), 16GB RAM, 내장 GPU
- **YOLO 최적화**:
  - 추론 해상도: 640 → 320 (4배 속도 향상)
  - 기존 모델별 크기 조정 로직 제거, 일괄 320 적용
- **InsightFace 최적화**:
  - 모델: `buffalo_l` → `buffalo_sc` (경량 모델, 2배 빠름)
  - 감지 크기: 320x320 → 256x256
  - 실행 모드: CUDA/CPU 혼합 → CPU 전용 (`ctx_id=-1`)
  - Provider: `CPUExecutionProvider` 전용
- **예상 효과**: CPU 추론 속도 약 3~5배 향상

### 기술적 세부사항

#### InsightFace 최적화 설정 (저사양)
```python
_shared_insightface_app = FaceAnalysis(
    name='buffalo_sc',  # 경량 모델
    providers=['CPUExecutionProvider'],  # CPU 전용
    allowed_modules=['detection', 'recognition']
)
_shared_insightface_app.prepare(ctx_id=-1, det_size=(256, 256), det_thresh=0.5)  # CPU 모드
```

#### 백그라운드 모델 사전 로드
```python
def preload_models_async():
    """모델을 백그라운드에서 미리 로드 (앱 시작 시 호출)"""
    def _preload():
        print("[PreLoad] 모델 사전 로드 시작...")
        get_shared_yolo_model()
        get_shared_insightface_app()
        print("[PreLoad] 모델 사전 로드 완료")

    thread = threading.Thread(target=_preload, daemon=True)
    thread.start()
    return thread
```

### 변경된 파일 목록
1. `VERSION.txt` - 1.9.5 → 1.9.6
2. `main.py` - 버전 주석 업데이트, 모델 사전 로드 호출 추가
3. `setup_cython.py` - 버전 업데이트
4. `install_requirements.py` - 버전 업데이트
5. `src/tcp_monitor/sensor/safety_detector.py` - YOLO 로드 수정, InsightFace 최적화, 배경학습 제거
6. `src/tcp_monitor/sensor/safety_detector_v2.py` - 동일 수정
7. `src/tcp_monitor/ui/app.py` - 탭 포커싱 수정, 배경학습 변수 제거
8. `src/tcp_monitor/ui/panel.py` - 배경학습 인식률 표시 제거
9. `src/tcp_monitor/ui/environment_settings.py` - 배경학습 버튼 제거
10. `src/tcp_monitor/ui/background_learning_dialog.py` - 삭제됨

### 의존성
- Python 3.13+
- PyTorch 2.6+ (weights_only 패치 적용)
- InsightFace (얼굴 인식)
- Ultralytics YOLOv8/11 (PPE 감지)
- OpenCV (카메라/영상 처리)
- Pillow (한글 텍스트 렌더링)

### 알려진 제한사항
- PyTorch 2.6+ 버전에서 `weights_only=False`로 모델을 로드하므로, 신뢰할 수 있는 모델 파일만 사용 권장
- GPU 가속은 CUDA 12.1+ 필요
