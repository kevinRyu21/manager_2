# GARAMe MANAGER - 변경 이력

## v2.1.0 (2026-01-28)

### 🐛 버그 수정 (Python 3.13 호환성)

#### 이미지 로딩 문제 해결
- ✅ **PhotoImage 가비지 컬렉션**: Python 3.13 tkinter에서 이미지 표시 안되는 문제 해결
  - 모든 ImageTk.PhotoImage에 명시적 master 파라미터 추가
  - 로고, About 다이얼로그, 안전교육 사진, 캡쳐 이미지, 화재 레벨 아이콘 정상 표시

#### 프로그램 종료 개선
- ✅ **Tcl 명령 오류 해결**: `invalid command name` 오류 수정
  - after() 콜백 ID 추적 및 destroy 시 취소
  - quit() + sys.exit(0) 방식으로 종료 처리 개선

#### UI 컴포넌트 수정
- ✅ **5단계 경고 설정 버튼**: KeyError 및 버튼 표시 문제 해결
  - 센서 설정 딕셔너리 키 일관성 확보 (이모지 추가)
  - ttk.Button → tk.Button 변경 (명시적 색상)
- ✅ **panel_tiles.py 호환성**: hasattr 체크 추가

### 🎨 UI 개선

#### 화재 레벨 아이콘
- ✅ **전문 디자인 아이콘 5개 생성**:
  - 레벨 1: 초록색 원 + ✓ (정상)
  - 레벨 2: 노란색 원 + ⚠ (주의)
  - 레벨 3: 주황색 원 + 🔥 (경계)
  - 레벨 4: 빨간색 원 + 🔥 (경고)
  - 레벨 5: 진한 빨간색 원 + 🔥 (위험)
  - RGBA 투명 배경, 80x80 크기, 레벨 번호 표시

### 🧪 테스트 도구

#### 센서 시뮬레이터
- ✅ **다중 센서 테스트 클라이언트** (sensor_simulator.py)
  - 센서 ID 1-4 동시 접속
  - 13가지 시나리오: 정상, 화재 4단계, CO2/CO/O2/H2S/CH4 위험, 연기, 누수, 랜덤
  - 9개 센서 데이터 생성 (CO2, CO, O2, H2S, CH4, 온도, 습도, 연기, 누수)
  - TCP v2.0 프로토콜 완벽 지원
  - GUI 컨트롤 패널 및 실시간 로그

### 📦 수정된 파일
- `src/tcp_monitor/ui/panel_header.py`
- `src/tcp_monitor/ui/about_dialog.py`
- `src/tcp_monitor/ui/splash_screen.py`
- `src/tcp_monitor/ui/safety_photo_viewer.py`
- `src/tcp_monitor/ui/capture_manager.py`
- `src/tcp_monitor/ui/fire_alert_panel.py`
- `src/tcp_monitor/ui/alert_settings.py`
- `src/tcp_monitor/ui/panel_tiles.py`
- `src/tcp_monitor/ui/app.py`

### 📚 문서
- ✅ [CHANGELOG_v2.1.0.md](CHANGELOG_v2.1.0.md) - 상세 변경 이력
- ✅ [docs/SENSOR_SIMULATOR_GUIDE.md](docs/SENSOR_SIMULATOR_GUIDE.md) - 센서 시뮬레이터 완전 가이드 (473줄)
- ✅ README.md - v2.1.0 업데이트

---

## v2.0.1 (2026-01-16)

### 🔧 UI 개선

#### 헤더 패널 개선
- ✅ **시계 표시 형식 변경**: 년도-날짜-시간 형식 (`2026-01-16 12:00:00`)
- ✅ **경고 버튼 텍스트 개선**: `경고 0/0/0` → `주의0/경계0/심각0` (의미 명확화)
- ✅ **불쾌지수 시인성 개선**: 레벨별 배경색+글자색 조합으로 가독성 향상
  - DI ≥ 80: 흰색 글자 + 빨간 배경
  - DI ≥ 75: 흰색 글자 + 주황 배경
  - DI ≥ 68: 어두운 글자 + 노란 배경
  - DI < 68: 흰색 글자 + 초록 배경
- ✅ **거울보기 → 장구점검**: 버튼 텍스트 변경 (안전장구점검 기능 명확화)
- ✅ **캡쳐 버튼 텍스트 추가**: `📸` → `📸캡쳐`

#### 센서전체보기 기능
- ✅ **센서전체보기 버튼**: 2개 이상 센서 접속 시에만 활성화
- ✅ **화재패널 스타일 적용**: 다크 테마 센서 카드 디자인
- ✅ **분할 레이아웃**: 2개 센서 2분할, 3-4개 센서 4분할

#### 종료 다이얼로그
- ✅ **불쾌지수 10번 클릭 종료**: 7번 → 10번으로 변경
- ✅ **종료 확인 다이얼로그 추가**: "프로그램을 종료하시겠습니까?" 확인/취소

### 🐛 버그 수정
- ✅ **장구점검 끄기 오류 수정**: `_tkinter.TclError: window isn't packed` 오류 해결
- ✅ **장구점검 레이아웃 개선**: 좌우 패널 크기 동일하게 (width=280)

### 📦 수정된 파일
- `src/tcp_monitor/ui/panel_header.py` - 헤더 UI 개선, 종료 다이얼로그
- `src/tcp_monitor/ui/panel.py` - 장구점검 오류 수정, 레이아웃 개선
- `src/tcp_monitor/ui/panel_all_sensors_view.py` - 화재패널 스타일 적용

---

## v2.0.0 (2026-01-15)

### 🚀 신규 기능

#### 화재 감시 5단계 경보 시스템 (신규 모듈)
- ✅ **5단계 화재 경보 체계**: 정상(🟢) → 관심(🟡) → 주의(🟠) → 경계(🔴) → 위험(🟣)
- ✅ **다중 센서 융합**: 8개 센서(온도, 습도, CO, CO₂, O₂, H₂S, CH₄, 연기) 통합 분석
- ✅ **Dempster-Shafer 증거 이론**: 학술 논문 기반 센서 데이터 융합 알고리즘
  - 참고: MDPI 2014 "Multi-Sensor Building Fire Alarm with D-S Theory"
  - 개선된 Murphy's Rule 적용 (높은 충돌 상황 처리)
  - 시간적 연속성 고려한 평활화
- ✅ **퍼지 멤버십 함수**: 센서별 비선형 화재 확률 변환
- ✅ **센서 조합 규칙**: 연기+CO, 온도상승률+온도 등 6가지 조합 패턴 감지
- ✅ **오경보 방지**: 연속 3회 이상 경보 시에만 상위 단계 발생
- ✅ **화재 감지 서비스**: 센서 데이터 → 화재 감지 → UI 연동 통합 서비스

#### AI 기반 적응형 임계값 자동 조정
- ✅ **설치 환경 자동 학습**: 설치 후 7~30일 데이터 수집 및 분석
- ✅ **환경 프로파일 자동 감지**: 사무실/공장/주방/지하시설/창고/전기실
- ✅ **Welford's Algorithm**: O(1) 메모리로 온라인 통계 계산
- ✅ **Reservoir Sampling**: 백분위수 근사 계산
- ✅ **안전 마진 적용**: 표준값 ±30% 범위 내 자동 조정
- ✅ **검증 및 롤백**: 적응 결과 검증, 문제 시 자동 롤백
- ✅ **SQLite 저장**: 통계 및 임계값 이력 영구 저장

#### TCP 프로토콜 v2.0
- ✅ **양방향 통신**: 센서 → 매니저 뿐만 아니라 매니저 → 센서 방향 통신 지원
  - `hello/hello_ack`: 연결 핸드셰이크
  - `heartbeat_ack`: 하트비트 응답
  - `sensor_ack`: 센서 데이터 수신 확인
- ✅ **시간 동기화**: NTP 스타일 시간 동기화 프로토콜
  - `time_sync_request/time_sync_response`
- ✅ **설정 동기화**: 매니저 설정을 센서에 전송
  - `config_request/config_response`: 센서가 설정 요청
  - `config_push`: 매니저가 설정 푸시

#### 신규 센서 지원 (v2.0)
- ✅ **CH4 (메탄/가연성 가스)**: %LEL 단위, 5단계 경보
- ✅ **Smoke (연기 센서)**: % 단위, 5단계 경보
- ✅ **ext_input (외부 접점 입력)**: 5V~24V DC 접점 신호

#### 보안 기능
- ✅ **TLS/SSL 암호화**: TLS 1.2+ 지원 (선택적)
- ✅ **HMAC-SHA256 서명**: 메시지 무결성 검증 (선택적)
- ✅ **메시지 ID (UUID)**: 메시지 추적 및 중복 감지
- ✅ **시퀀스 번호**: 메시지 순서 검증

#### 세션 관리
- ✅ **ClientSession 클래스**: 연결 상태, 프로토콜 버전, 펌웨어 버전 추적
- ✅ **`get_connected_sensors()`**: 연결된 센서 목록 조회 API

#### UI 개편
- ✅ **그래프 모드 제거**: 동적 타일 레이아웃으로 대체
- ✅ **동적 타일 그리드**: 접속된 센서 수에 따라 자동 레이아웃 조정 (1x1 ~ 4x4)
- ✅ **화재 경보 패널**: 좌측 사이드바에 실시간 화재 상태 표시
  - 5단계 경보 시각화 (아이콘, 색상, 텍스트)
  - 화재 확률 프로그레스 바
  - 센서별 상태 표시
  - AI 학습 상태 표시
- ✅ **화재 경보 다이얼로그**: 레벨 3(주의) 이상 시 전체화면 긴급 경고
  - 경보음 자동 재생
  - 119 긴급 연락 버튼
  - ESC 키로 닫기
- ✅ **도면 화재 위치 표시**: 화재 발생 시 도면에 경보 배너 오버레이

### 🔧 기술적 개선
- ✅ **v1.x 역호환**: v1.x 센서와의 완전한 호환성 유지
- ✅ **자동 버전 감지**: 메시지 내용으로 프로토콜 버전 자동 감지
- ✅ **센서 데이터 정규화**: v1 → v2 데이터 변환 (lel → ch4)

### 📦 신규/수정 파일

#### 화재 감시 모듈 (신규)
- `src/tcp_monitor/fire/` - 화재 감시 모듈 디렉토리
- `src/tcp_monitor/fire/__init__.py` - 모듈 초기화 및 export
- `src/tcp_monitor/fire/models.py` - 데이터 모델 (SensorReading, FireDetectionResult 등)
- `src/tcp_monitor/fire/dempster_shafer.py` - D-S 증거 조합기
- `src/tcp_monitor/fire/fuzzy.py` - 퍼지 멤버십 함수
- `src/tcp_monitor/fire/detector.py` - 화재 감지기 (FireDetector, MultiSensorFireDetector)
- `src/tcp_monitor/fire/adaptive.py` - AI 적응형 임계값 시스템
- `src/tcp_monitor/fire/fire_service.py` - 화재 감지 서비스 (UI 연동)
- `src/tcp_monitor/fire/standard_defaults.conf` - 표준 설정값 (국가 기준)

#### UI 모듈 (신규/수정)
- `src/tcp_monitor/ui/fire_alert_panel.py` - 화재 경보 좌측 사이드바 패널
- `src/tcp_monitor/ui/fire_alert_dialog.py` - 화재 경보 긴급 다이얼로그
- `src/tcp_monitor/ui/panel_dynamic_tiles.py` - 동적 타일 그리드
- `src/tcp_monitor/ui/panel_header.py` - 그래프 버튼 제거
- `src/tcp_monitor/ui/panel_blueprint_view.py` - 화재 위치 표시 기능 추가

#### 문서
- `docs/화재감시_5단계경보_개발계획서.md` - 개발 계획서 (학술 논문 참조)

#### TCP 프로토콜 v2.0
- `src/tcp_monitor/network/protocol.py` - v2.0 프로토콜 정의 (신규)
- `src/tcp_monitor/network/server.py` - TcpServer v2.0 업그레이드
- `src/tcp_monitor/network/__init__.py` - 모듈 export 업데이트
- `src/tcp_monitor/config/manager.py` - TLS/HMAC/신규센서 설정 추가
- `config.conf.example` - v2.0 설정 예제
- `VERSION.txt` - 2.0.0

---

## v1.9.8.4 (2026-01-07)

### 🚀 신규 기능

#### 센서 탭 닫기 버튼
- ✅ **탭 ✕ 표시**: 연결 끊김 상태의 탭에 "✕" 표시 추가
- ✅ **탭 닫기 방법 3가지**:
  - ✕ 클릭: 탭 우측 끝의 ✕ 영역 클릭 시 바로 닫기
  - 우클릭: 컨텍스트 메뉴 → "탭 닫기" (확인 대화상자 표시)
  - 중클릭(휠 클릭): 바로 닫기 (확인 없음)
- ✅ **안전 조치**: 연결된 탭은 닫을 수 없음 (연결 끊김 상태만 닫기 가능)
- ✅ **헤더 탭 삭제 버튼 제거**: 기존 패널 헤더의 "탭 삭제" 버튼 제거 (탭 자체에서 닫기로 통합)

### 🐛 버그 수정

#### 카메라 고급 설정 다이얼로그 문제 해결
- ✅ **messagebox 표시 안됨 문제 해결**: 중첩 모달 다이얼로그에서 messagebox가 표시되지 않던 문제 수정
- ✅ **커스텀 다이얼로그로 대체**: Tkinter messagebox 대신 커스텀 Toplevel 다이얼로그 사용
- ✅ **적용/저장/초기화 확인 다이얼로그**: 버튼 클릭 시 확인 메시지 정상 표시
- ✅ **다크 테마 적용**: 앱 테마에 맞는 커스텀 다이얼로그 디자인

#### 화면 떨림 문제 해결
- ✅ **고급설정 다이얼로그 떨림 수정**: `bind_all` → `bind`로 변경하여 전역 이벤트 바인딩 제거

### 🔧 기술적 개선
- ✅ **app.py**: 탭 클릭/우클릭/중클릭 이벤트 핸들러 추가
  - `_on_tab_click()`: ✕ 영역 클릭 감지
  - `_on_tab_right_click()`: 우클릭 컨텍스트 메뉴
  - `_on_tab_middle_click()`: 중클릭 바로 닫기
  - `_close_tab_with_confirm()`: 확인 후 닫기
- ✅ **app.py**: `_update_tab_title()` 수정 - 연결 끊김 시 "(연결 끊김) ✕" 표시
- ✅ **camera_advanced_settings.py**: `_show_message()` 커스텀 다이얼로그로 완전 재구현
- ✅ **panel_header.py**: 탭 삭제 버튼 및 관련 코드 제거

### 📦 수정된 파일
- `src/tcp_monitor/ui/app.py` - 탭 닫기 이벤트 핸들러, 탭 제목 ✕ 표시
- `src/tcp_monitor/ui/camera_advanced_settings.py` - 커스텀 메시지 다이얼로그
- `src/tcp_monitor/ui/panel_header.py` - 탭 삭제 버튼 제거

---

## v1.9.8.3-1 (2026-01-06)

### 🚀 신규 기능

#### 라이선스 키 시스템
- ✅ **하드웨어 바인딩**: 머신 UUID, MAC 주소, 디스크 시리얼, CPU 정보 기반 바인딩
- ✅ **키 형식**: TYPE-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (33자)
- ✅ **라이선스 타입**:
  - TRIAL: 테스트 키 (기본 7일)
  - TIMED: 기간 제한 키 (일수 지정)
  - PERPT: 영구 키
  - VERSN: 버전 제한 키
- ✅ **키 생성기**: 암호 보호된 관리자용 CLI/GUI 프로그램
  - 첫 실행 시 암호 설정 (SHA-256 해시 저장)
  - 3회 인증 실패 시 프로그램 종료
- ✅ **하드웨어 ID 수집**: IP 주소 제외, 고정된 값만 사용
  - /etc/machine-id (OS 설치 시 생성)
  - MAC 주소 (네트워크 카드)
  - 디스크 시리얼 번호
  - CPU 모델명

### 🐛 버그 수정

#### IP 카메라 COCO 사물 감지 안됨 문제 해결 (핵심 수정)
- ✅ **성능 모드 설정 타이밍 수정**: `set_performance_mode()`가 백그라운드 스레드에서 호출되어 COCO 모델이 모드 2(비활성화)로 초기화되던 문제 수정
- ✅ **동기적 모드 설정**: `main.py`에서 `preload_models_async()` 호출 전에 `set_performance_mode()`를 동기적으로 먼저 호출
- ✅ **COCO 80클래스 감지 복구**: 자동차, 동물, 가구 등 사물이 정상적으로 감지됨 (수정 전: 1개 → 수정 후: 40+개)
- ✅ **IP 카메라 고해상도 프레임 처리 개선**: 2K 이상 해상도에서 imgsz=1920 사용, 원본 프레임으로 직접 추론

#### 카메라 전환 즉시 적용
- ✅ **카메라 설정 즉시 적용**: 거울보기 실행 중 카메라 변경 시 재시작 없이 자동 적용
- ✅ **`_apply_camera_change()` 메서드 추가**: 카메라 설정 저장 시 자동 호출

#### IP 카메라 ↔ USB 카메라 전환 문제 해결
- ✅ **카메라 전환 시 PPE 감지 유지**: IP 카메라에서 USB 카메라로 전환 시 사물 인식이 안되던 문제 수정
- ✅ **PPEDetector 싱글톤 리셋**: 카메라 전환 시 `reset_instance()` 메서드로 감지기 재초기화
- ✅ **_ip_camera_url 초기화**: USB 카메라 전환 시 IP 카메라 URL 상태 정리
- ✅ **is_ip 플래그 오류 수정**: 카메라 전환 후에도 is_ip=True로 유지되던 문제 해결

#### UI 개선
- ✅ **IP 카메라 하단 텍스트 제거**: YOLO/얼굴인식 모듈명 출력 제거
- ✅ **USB 카메라 Score 표시 제거**: 순간 표시되던 Score 텍스트 제거
- ✅ **Unknown 얼굴 텍스트 제거**: 미등록 얼굴에 UNKNOWN 표시 제거
- ✅ **카메라 리셋 버튼 이동**: 환경설정 → 카메라 설정으로 이동

#### PyTorch GPU 지원
- ✅ **CUDA 12.8 지원**: PyTorch GPU 버전 (2.9.1+cu128) 설치
- ✅ **RTX 3060 GPU 인식**: NVIDIA GPU 정상 감지

### 🔧 기술적 개선
- ✅ **main.py**: `set_performance_mode()` 동기 호출 추가 (라인 122-125)
- ✅ **PPEDetector.reset_instance()**: 싱글톤 인스턴스 리셋 메서드 추가
- ✅ **_restart_mirror_camera()**: 카메라 재시작 시 감지기 및 IP URL 초기화
- ✅ **_connect_ip_camera()**: IP 카메라 연결 시 기존 감지기 정리
- ✅ **_start_mirror_camera()**: USB 카메라 시작 시 _ip_camera_url = None 설정
- ✅ **AI 스레드 디버그 로깅**: 프레임 파이프라인 추적 로그 추가
- ✅ **detect_objects_coco()**: IP 카메라 고해상도 프레임 최적화 (imgsz=1920, 원본 프레임 사용)
- ✅ **camera_settings.py**: `_apply_camera_change()` 메서드 추가 (카메라 즉시 적용)

### 📦 수정/추가된 파일
- `main.py` - 성능 모드 동기 설정 추가
- `src/tcp_monitor/ppe/detector.py` - reset_instance() 메서드 추가
- `src/tcp_monitor/ui/panel.py` - 카메라 전환 로직 개선, 디버그 로깅 추가
- `src/tcp_monitor/sensor/safety_detector.py` - Unknown 텍스트/Score 표시 제거
- `src/tcp_monitor/ui/camera_settings.py` - 카메라 리셋 버튼 추가
- `src/tcp_monitor/ui/environment_settings.py` - 카메라 리셋 버튼 제거
- `requirements.txt` - PyTorch GPU 버전 설치 안내
- `src/tcp_monitor/license/` - 라이선스 모듈 (신규)
  - `hardware_id.py` - 하드웨어 ID 생성
  - `key_validator.py` - 키 검증
  - `license_manager.py` - 라이선스 관리
- `tools/license_generator/` - 키 생성기 (신규)
  - `generator.py` - CLI 키 생성기
  - `gui.py` - GUI 키 생성기

---

## v1.9.8.3 (2025-01-05)

### 🐛 버그 수정

#### PPE 감지 오탐지 수정
- ✅ **보안경 오탐지 해결**: face-guard가 glasses로 잘못 매핑되어 미착용시에도 착용으로 표시되던 문제 수정
- ✅ **조끼 오탐지 해결**: medical-suit, safety-suit가 vest로 잘못 매핑되어 미착용시에도 착용으로 표시되던 문제 수정
- ✅ **모델 우선순위 변경**: YOLOv10 모델을 우선 사용하도록 변경 (SH17 모델 비활성화)

#### CPU 모드 설치 수정
- ✅ **GPU 미감지 시 설치 중단 문제 해결**: `detect_nvidia_gpu` 함수 반환값이 1일 때 `set -e`로 인해 스크립트가 종료되던 문제 수정
- ✅ **CPU 전용 환경 지원**: GPU가 없어도 정상적으로 설치 진행

#### PyInstaller 빌드 수정
- ✅ **dill 패키지 누락 해결**: YOLO 모델 로딩 시 "No module named 'dill'" 오류 수정
- ✅ **hiddenimports 추가**: garame_manager.spec에 dill 패키지 추가

### 🔧 기술적 개선
- ✅ **PPE 감지 원인 분석**: SH17 학습 모델의 17개 클래스 중 일부가 PPE 아이템으로 잘못 매핑되는 문제 확인
  - `face-guard` → `glasses` (오탐지 원인)
  - `medical-suit` → `vest` (오탐지 원인)
  - `safety-suit` → `vest` (오탐지 원인)

### 📦 수정된 파일
- `src/tcp_monitor/ppe/detector.py` - 모델 우선순위 변경
- `install.sh` - GPU 감지 실패 시에도 계속 진행
- `garame_manager.spec` - dill hiddenimport 추가

---

## v1.9.8.2 (2024-12-24)

### 🚀 주요 기능

#### 안전화 감지 개선
- ✅ **듀얼 모델 구조**: 메인 PPE 모델 + 안전화 전용 모델
- ✅ **construction-ppe.pt**: YOLOv10n 기반 안전화 감지 모델 (5.5MB)
- ✅ **슬리퍼 오인식 해결**: 일반 신발/슬리퍼를 안전화로 인식하는 문제 수정

#### PTZ 카메라 제어 개선
- ✅ **다중 인증 방식**: 4가지 인증 방식 자동 시도 (신형/구형 펌웨어 호환)
- ✅ **계정 분리**: RTSP 로컬 계정과 PTZ Tapo 클라우드 계정 분리
- ✅ **PTZ 테스트 버튼**: 카메라 설정에서 PTZ 연결 테스트 기능

#### 성능 설정 UI 개선
- ✅ **폰트 최적화**: 25% 크기 축소로 컴팩트한 UI
- ✅ **다이얼로그 높이**: 940px로 조정

### 🐛 버그 수정
- ✅ **PPE 모델 정리**: `ppe_detect.pt` → `yolo_coco_80.pt` (잘못된 이름 수정)
- ✅ **PTZ 인증 실패**: "Invalid authentication data" 오류 해결

### 🔧 기술적 개선
- ✅ pytapo 공식 해결책 적용 (admin + 클라우드 비밀번호)
- ✅ PPE 감지기 듀얼 모델 지원

---

## v1.9.8 (2024-12-23)

### 🚀 주요 기능

#### 카메라 설정 시스템 개편
- ✅ **설정-카메라 설정** 메뉴 추가
- ✅ **USB 카메라 관리**: 연결된 USB 카메라 목록 조회 및 선택
- ✅ **IP 카메라 지원**: RTSP/HTTP/HTTPS 프로토콜 IP 카메라 연결
  - Tapo C211 등 IP 카메라 지원
  - 연결 테스트 기능 (실시간 결과 표시)
  - IP 카메라 추가/편집/삭제 관리
- ✅ **화면 반전 설정**: 환경설정에서 카메라 설정으로 이동

#### 센서 접속 시 카메라 자동 종료
- ✅ 센서 접속 시 거울보기 자동 종료
- ✅ 자동으로 타일 화면 전환

#### 거울보기 UI 개선
- ✅ 카메라 선택 드롭다운 제거 (설정에서 관리)
- ✅ 현재 선택된 카메라 이름 표시
- ✅ 사물 인식 바운딩 박스 표시

### 🐛 버그 수정
- ✅ **IP 카메라 연결 오류**: `NoneType` 오류 수정
- ✅ **RTSP 연결 안정성**: FFmpeg 백엔드 사용, 타임아웃 10초로 증가

### 🔧 기술적 개선
- ✅ IP 카메라 목록 즉시 저장 (추가/편집/삭제 시)
- ✅ 연결 테스트 백그라운드 실행 (UI 블로킹 방지)

---

## v1.9.7 (2025-12-08 ~ 2025-12-18)

### 🚀 주요 업그레이드

#### PPE 감지 엔진 업그레이드 (YOLOv10 통합)
- ✅ **YOLOv10x**: SH17 데이터셋 기반 17개 클래스 감지
- ✅ **감지 정확도**: ~92.7% mAP50 (기존 대비 향상)
- ✅ **장갑 감지 개선**: 좌/우 구분, 개수 표시
- ✅ **색상 분석**: HSV 기반 헬멧/조끼 색상 정밀 분석

#### 감지 가능 PPE (6종)
1. 헬멧 (helmet) - 색상 분석 포함
2. 보안경 (glasses)
3. 마스크 (mask)
4. 장갑 (gloves) - 좌/우 구분
5. 조끼 (vest) - 색상 분석 포함
6. 안전화 (boots)

### 🎨 UI/UX 개선 (2025-12-18)
- ✅ **PPE 패널 아이콘 추가**: ⛑🦺🥽🧤😷👢 이모지 아이콘으로 직관적 표시
- ✅ **카메라 오버레이 제거**: 카메라 영역은 순수 영상만, PPE/안전률은 좌측 패널 표시
- ✅ **사물 인식 패널 폰트 30% 축소**: 가독성 개선
- ✅ **캡쳐 완료 창 20% 확장**: 버튼 가시성 향상
- ✅ **환경설정 폰트 1.5배 확대**: 가독성 개선

### 🐛 버그 수정
- ✅ **갈색 헬멧 흰색 인식 문제 수정**: 갈색 헬멧이 흰색으로 잘못 인식되는 문제 해결
  - 갈색 판별 로직 추가 (HSV: S 20-70, V 50-180)
  - 색상 우선순위 적용 (갈색 > 흰색/회색)
  - 무채색 범위 조정 (갈색과 겹치지 않도록)
- ✅ **화면 캡쳐 GNOME Wayland 호환**: flameshot `--raw` 옵션 사용
  - grim/gnome-screenshot/scrot 호환성 문제 해결
  - 알림 다이얼로그 포커스 문제 수정
- ✅ **거울보기 모드 제한**: 그래프/도면 모드에서 거울보기 버튼 비활성화
- ✅ **캡쳐 매니저 미리보기 오류**: Canvas 위젯 `create_text()` 사용으로 수정

### 🔧 기술적 개선
- ✅ 새로운 PPE 모듈 구조 (`src/tcp_monitor/ppe/`)
- ✅ 안전률 가중치 계산 시스템
- ✅ PyTorch 2.6+ 호환성 유지

### 📦 의존성 추가
- ✅ **flameshot**: GNOME Wayland 환경 화면 캡쳐용

자세한 내용은 [CHANGELOG_v1.9.7.md](CHANGELOG_v1.9.7.md) 참조

---

## v1.9.6 (2025-11-27)

### 주요 변경
- ✅ 안전교육 화면 개선 (메뉴 비활성화, 버튼 가시성)
- ✅ 해시 체인 무결성 검증 시스템 (특허 관련)
- ✅ 사람 감지 영역 개선 (YOLO 기본 모델 보조)
- ✅ GPU 가속 옵션 제거 (CPU 모드 전용)

자세한 내용은 [CHANGELOG_v1.9.6.md](CHANGELOG_v1.9.6.md) 참조

---

## v1.9.5 (2025-11-18)

### 🚀 주요 업그레이드

#### AI 모델 업그레이드
- ✅ **InsightFace** (v0.7.3+): 얼굴 인식 정확도 99.86% (ArcFace 알고리즘)
  - 기존 face_recognition (dlib) → InsightFace로 완전 교체
  - GPU 가속 지원 (ONNX Runtime)
  - 2D/3D 얼굴 분석

- ✅ **YOLOv11** (Ultralytics 8.3.0+): PPE 안전장구 감지 92.7% mAP50
  - 안전모, 보안경, 장갑, 안전화, 조끼 실시간 감지
  - CPU/GPU 모드 자동 전환

#### 음성 알림 개선
- ✅ **gTTS** (Google Text-to-Speech): 자연스러운 한국어 여성 목소리
  - 기존 pyttsx3 → gTTS로 교체
  - 음성 캐싱으로 빠른 재생
  - mpg123/ffplay fallback 지원

### 🗑️ 제거된 기능
- ❌ **dlib/face_recognition**: InsightFace로 완전 대체
- ❌ **OCR 기능**: 사용하지 않아 제거
- ❌ **pyttsx3**: gTTS로 대체

### 🔧 기술적 개선
- ✅ NumPy 1.26.4 고정 (InsightFace, Ultralytics 호환성)
- ✅ OpenCV 4.9.0.80 고정 (NumPy 1.x 호환)
- ✅ GPU 설치 옵션 추가 (onnxruntime-gpu)
- ✅ Ubuntu Linux 25.10 지원
- ✅ Python 3.13 호환성 개선
- ✅ PyInstaller 빌드 최적화: --onefile → --onedir (4.1GB → 500MB, 88% 감소)

### 📝 문서 개선
- ✅ GPU 설치 가이드 추가
- ✅ 모든 버전 문자열 v1.9.5로 통일
- ✅ 불필요한 문서 정리

### 🐛 버그 수정
- ✅ check_cv2.sh에서 opencv 버전 고정 (NumPy 2.x 설치 방지)
- ✅ 모든 .sh 파일 개행문자 Unix 형식으로 통일
- ✅ main.py에서 OCR 자동 설치 코드 제거

---

## 이전 버전

이전 버전의 변경 이력은 git log를 참조하세요.
