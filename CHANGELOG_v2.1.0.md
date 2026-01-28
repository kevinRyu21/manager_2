# GARAMe MANAGER - 변경 이력 v2.1.0

## v2.1.0 (2026-01-28)

### 🐛 버그 수정 (Python 3.13 호환성)

#### 이미지 로딩 문제 수정
- ✅ **PhotoImage 가비지 컬렉션 문제**: Python 3.13 tkinter에서 이미지가 표시되지 않는 문제 해결
  - 모든 `ImageTk.PhotoImage` 생성 시 명시적 `master` 위젯 파라미터 추가
  - 이미지 참조가 가비지 컬렉션되지 않도록 보장
  - **수정된 파일**:
    - `src/tcp_monitor/ui/panel_header.py` - 메인 로고
    - `src/tcp_monitor/ui/about_dialog.py` - About 다이얼로그 로고
    - `src/tcp_monitor/ui/splash_screen.py` - 시작 화면 로고
    - `src/tcp_monitor/ui/safety_photo_viewer.py` - 안전교육 사진
    - `src/tcp_monitor/ui/capture_manager.py` - 화면 캡쳐 이미지
    - `src/tcp_monitor/ui/fire_alert_panel.py` - 화재 레벨 아이콘

#### 프로그램 종료 오류 수정
- ✅ **Tcl 명령 오류 해결**: `invalid command name "xxx_maintain_focus"` 오류 수정
  - `after()` 콜백 ID 추적 및 destroy 시 취소
  - 종료 시 `destroy()` 대신 `quit() + sys.exit(0)` 사용
  - Python 3.13의 엄격한 Tcl 명령 관리 대응
  - **수정된 파일**:
    - `src/tcp_monitor/ui/panel_header.py` - after 콜백 관리
    - `src/tcp_monitor/ui/app.py` - 종료 처리 개선

#### UI 컴포넌트 문제 수정
- ✅ **5단계 경고 설정 버튼 표시**: 버튼이 생성되지만 보이지 않는 문제 해결
  - 센서 설정 딕셔너리 키에 이모지 추가 (일관성 확보)
  - `ttk.Button` → `tk.Button` 변경 (명시적 색상 지정)
  - KeyError 오류 수정: `"누수 감지"` → `"🚿 누수 감지"`
  - **수정된 파일**:
    - `src/tcp_monitor/ui/alert_settings.py`

- ✅ **panel_tiles.py 호환성**: `update_weather_info` 메서드 호출 전 존재 여부 확인
  - hasattr 체크 추가하여 안전한 메서드 호출
  - **수정된 파일**:
    - `src/tcp_monitor/ui/panel_tiles.py`

### 🎨 UI 개선

#### 화재 레벨 아이콘 개선
- ✅ **맞춤형 화재 레벨 아이콘**: 기존 이모지를 전문 디자인 아이콘으로 교체
  - **레벨 1 (정상)**: 초록색 원 + ✓ 체크마크
  - **레벨 2 (주의)**: 노란색 원 + ⚠ 경고 표시
  - **레벨 3 (경계)**: 주황색 원 + 🔥 작은 불꽃
  - **레벨 4 (경고)**: 빨간색 원 + 🔥 중간 불꽃
  - **레벨 5 (위험)**: 진한 빨간색 원 + 🔥 큰 불꽃
  - 각 아이콘에 레벨 번호 표시 (Lv.1 ~ Lv.5)
  - RGBA 투명 배경 지원 (200x200 PNG)
  - 80x80 크기로 자동 리사이징
  - **생성된 파일**:
    - `assets/fire_level_normal.png`
    - `assets/fire_level_attention.png`
    - `assets/fire_level_caution.png`
    - `assets/fire_level_warning.png`
    - `assets/fire_level_danger.png`

### 🧪 테스트 도구

#### 센서 시뮬레이터 추가
- ✅ **다중 센서 테스트 클라이언트**: 센서 없이 모든 기능 테스트 가능
  - **센서 ID 1-4 동시 접속**: 각 센서 독립적 제어
  - **13가지 시나리오 프리셋**:
    - 정상
    - 화재 레벨1 (주의)
    - 화재 레벨2 (경계)
    - 화재 레벨3 (경고)
    - 화재 레벨4 (위험)
    - CO2 질식 위험
    - CO 중독 위험
    - 산소 부족
    - H2S 황화수소 위험
    - CH4 가연성가스 위험
    - 연기 감지
    - 누수 감지
    - 랜덤
  - **9개 센서 데이터 생성**: CO2, CO, O2, H2S, CH4, 온도, 습도, 연기, 누수
  - **TCP v2.0 프로토콜 지원**: hello 핸드셰이크, sensor_update, 메시지 ID
  - **GUI 컨트롤 패널**:
    - 서버 주소/포트 설정
    - 전송 주기 조절 (기본 1초)
    - 센서별 독립 시나리오 선택
    - 실시간 로그 표시
  - **새 파일**: `sensor_simulator.py`

### 📦 수정된 파일 목록

#### UI 컴포넌트
- `src/tcp_monitor/ui/panel_header.py` - 이미지 로딩, after 콜백 관리
- `src/tcp_monitor/ui/about_dialog.py` - 로고 이미지 master 파라미터
- `src/tcp_monitor/ui/splash_screen.py` - 로고 이미지 master 파라미터
- `src/tcp_monitor/ui/safety_photo_viewer.py` - 사진 이미지 master 파라미터
- `src/tcp_monitor/ui/capture_manager.py` - 캡쳐 이미지 master 파라미터
- `src/tcp_monitor/ui/fire_alert_panel.py` - 화재 레벨 아이콘 로딩 및 표시
- `src/tcp_monitor/ui/alert_settings.py` - 5단계 설정 버튼 수정
- `src/tcp_monitor/ui/panel_tiles.py` - 메서드 호출 안전성
- `src/tcp_monitor/ui/app.py` - 종료 처리 개선

#### 애셋
- `assets/fire_level_normal.png` - 레벨 1 아이콘 (신규)
- `assets/fire_level_attention.png` - 레벨 2 아이콘 (신규)
- `assets/fire_level_caution.png` - 레벨 3 아이콘 (신규)
- `assets/fire_level_warning.png` - 레벨 4 아이콘 (신규)
- `assets/fire_level_danger.png` - 레벨 5 아이콘 (신규)

#### 테스트 도구
- `sensor_simulator.py` - 다중 센서 시뮬레이터 (신규)

#### 버전 정보
- `VERSION.txt` - 2.0.1 → 2.1.0

### 🔧 기술 세부사항

#### Python 3.13 tkinter 변경사항 대응
Python 3.13에서 tkinter의 Tcl/Tk 인터페이스가 강화되어 더 엄격한 메모리 관리와 명령 생명주기 관리가 필요합니다.

**주요 변경사항:**
1. **PhotoImage 생명주기**:
   - `master` 위젯을 명시하지 않으면 전역 Tk 인스턴스에 연결
   - 위젯 삭제 시 이미지도 함께 정리되어야 하므로 명시적 master 필요

2. **Tcl 명령 정리**:
   - `after()` 콜백이 위젯 삭제 후에도 남아있으면 오류 발생
   - 모든 after 호출은 ID를 저장하고 destroy 시 취소 필요

3. **ttk 위젯 스타일**:
   - 일부 환경에서 ttk.Button의 배경색이 제대로 표시되지 않음
   - tk.Button으로 대체하여 명시적 색상 제어

### 📝 사용법 변경사항

#### 센서 시뮬레이터 사용법
```bash
# Manager 실행
cd /home/garam/다운로드/manager_2-2.1.0
python3 main.py

# 별도 터미널에서 시뮬레이터 실행
python3 sensor_simulator.py

# 시뮬레이터 GUI에서:
# 1. 서버 주소: 127.0.0.1, 포트: 9000 확인
# 2. 각 센서(1-4)에서 시나리오 선택
# 3. "연결" 버튼 클릭
# 4. "전송 시작" 버튼 클릭
```

### 🔍 테스트 시나리오 예시

**시나리오 1: 화재 진행 단계 테스트**
- 센서 1: "정상" → 일정 시간 후 → "화재 레벨1 (주의)"
- 모든 화재 레벨의 UI 표시 및 경보 확인

**시나리오 2: 다중 위험 동시 발생**
- 센서 1: "화재 레벨3 (경고)"
- 센서 2: "CO2 질식 위험"
- 센서 3: "누수 감지"
- 센서 4: "정상"

**시나리오 3: 가스 누출 테스트**
- 센서 1: "CH4 가연성가스 위험"
- 센서 2: "H2S 황화수소 위험"
- 가스 경보 및 안전 조치 메시지 확인

### 🚀 업그레이드 가이드

**2.0.1에서 2.1.0으로 업그레이드:**

1. **백업 생성**
   ```bash
   cp -r manager_2-main manager_2-backup
   ```

2. **새 버전 복사**
   ```bash
   cp -r manager_2-2.1.0/* manager_2-main/
   ```

3. **의존성 확인** (변경사항 없음)
   ```bash
   cd manager_2-main
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **실행 및 테스트**
   ```bash
   python3 main.py
   ```

### ⚠️ 알려진 이슈

1. **TK 작은 창 깜빡임**: 프로그램 종료 시 TK 창이 잠시 나타났다 사라짐 (기능적 문제 없음)
2. **5단계 설정 버튼**: 창 크기에 따라 스크롤이 필요할 수 있음

### 📊 호환성

- **Python**: 3.10+ (3.13 완전 지원)
- **OS**: Linux (Ubuntu 20.04+), Windows 10/11
- **센서 프로토콜**: TCP v1.0, v2.0 모두 지원
- **이전 버전**: v2.0.x 설정 파일 호환

---

## 다음 버전 계획 (v2.2.0)

### 계획된 기능
- 🔄 자동 업데이트 시스템
- 📧 이메일/SMS 알림
- 🌐 웹 대시보드
- 📱 모바일 앱 연동
- 🔐 사용자 권한 관리
- 📈 장기 통계 리포트

---

**작성일**: 2026-01-28
**작성자**: GARAMe Development Team
**문의**: support@garame.co.kr
