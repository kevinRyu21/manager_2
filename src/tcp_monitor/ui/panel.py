"""
센서 패널 UI 클래스

센서 데이터를 표시하는 3x2 그리드 타일과 상세 그래프를 제공합니다.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading

from ..utils.helpers import SENSOR_KEYS
from ..sensor.alerts import AlertManager
from .panel_header import PanelHeader
from .panel_tiles import PanelTiles

# 새로운 PPE 감지 모듈 (YOLOv10 기반)
PPE_DETECTOR_AVAILABLE = False
try:
    from ..ppe import PPEDetector, PPEVisualizer, PPEStatus
    PPE_DETECTOR_AVAILABLE = True
except ImportError:
    PPEDetector = None
    PPEVisualizer = None
    PPEStatus = None

# Tapo PTZ 제어 모듈
TAPO_PTZ_AVAILABLE = False
try:
    from ..sensor.tapo_ptz import TapoPTZController, PYTAPO_AVAILABLE
    TAPO_PTZ_AVAILABLE = PYTAPO_AVAILABLE
except ImportError:
    TapoPTZController = None
    TAPO_PTZ_AVAILABLE = False

# 화재 감지 모듈
FIRE_MODULE_AVAILABLE = False
try:
    from ..fire import FireDetector, FireAlertLevel, SensorReading
    from .fire_alert_panel import FireAlertPanel
    from .fire_alert_dialog import FireAlertManager
    FIRE_MODULE_AVAILABLE = True
except ImportError:
    FireDetector = None
    FireAlertLevel = None
    SensorReading = None
    FireAlertPanel = None
    FireAlertManager = None


class SensorPanel(ttk.Frame):
    """
    - 헤더: 로고/제목/시계, 우측 컨트롤(문구-/문구+/타일-/타일+/전체화면/종료)
    - 3x2 타일: 자동 스케일 + 스케일 팩터 적용
    - 상세 그래프: 플리커 최소화, 한글 폰트
    """

    def __init__(self, master, sid_key, app):
        super().__init__(master)
        self.app = app
        self.sid_key = sid_key
        self.mode = "main"
        self.view_mode = "card"  # "card", "graph", "blueprint"
        self.data = {}
        self.alert_manager = AlertManager(app.cfg)
        # 전역 스피커 상태 적용 (패널 재생성 시 상태 유지)
        if hasattr(app, 'global_voice_alert_enabled') and not app.global_voice_alert_enabled:
            self.alert_manager.disable_tts()

        # SID 추출 (sid_key 형식: "sid@ip" 또는 "sid#peer" 또는 "sid")
        if "@" in sid_key:
            self.sid = sid_key.split("@")[0]
        elif "#" in sid_key:
            self.sid = sid_key.split("#")[0]
        else:
            self.sid = sid_key

        # Peer는 app.states에서 가져옴 (포트 번호 포함된 원본)
        state = app.states.get(sid_key, {})
        self.peer = state.get("peer", "")

        # 접속 상태 관리
        self._connection_status = "waiting"
        self._last_values = {}  # 마지막 수신 값 저장
        self._last_std_texts = {}  # 마지막 기준 텍스트 저장
        self._last_ok_states = {}  # 마지막 정상 상태 저장

        # 상단 헤더
        self.header = PanelHeader(self, sid_key, app)
        self.header.pack(side="top", fill="x", padx=12, pady=(12, 8))

        # 통신 상태 메시지 (초기에는 숨김)
        self.status_msg_label = tk.Label(self, text="", justify="center",
                                         font=("Pretendard", 14, "bold"), bg="#FF6B6B", fg="#FFFFFF",
                                         relief="raised", bd=3, height=2)
        # pack은 하지 않고 필요할 때만 표시

        # 안내 문구
        self.msg_label = tk.Label(self, text=self._fmt_text(app.cfg.value_text), justify="left",
                                 font=("Pretendard", 12), bg="#F0F8FF", fg="#2C3E50", relief="raised", bd=2)
        self.msg_label.pack(side="top", fill="x", padx=15, pady=(0, 8))
        self._apply_header_font()

        # 3x2 그리드 (타일 뷰)
        self.tiles_container = PanelTiles(self, app, self._show_detail)
        self.tiles_container.pack(side="top", fill="both", expand=True, padx=12, pady=12)

        # 그래프 뷰 컨테이너 (지연 생성)
        self.graph_view = None

        # 도면 뷰 컨테이너 (지연 생성)
        self.blueprint_view = None

        # 상세 오버레이는 첫 클릭 시 지연 생성
        self.overlay = None

        # 거울보기 카메라 관련
        self.mirror_camera = None
        self.mirror_camera_label = None
        self.mirror_flip_var = None  # 좌우 반전 설정값 (환경설정에서 읽음)
        self.mirror_mode_active = False
        self.available_cameras = []  # 사용 가능한 카메라 목록 [(index, name), ...]
        self.selected_camera_index = 0  # 선택된 카메라 인덱스
        self.camera_combo = None  # 카메라 선택 콤보박스
        self.safety_detector = None  # 안전장구 감지기 (fallback)
        self.safety_detection_enabled = True  # 안전장구 감지 활성화 여부
        self.mirror_frame_count = 0  # 프레임 카운터 (디버깅용)

        # 새로운 PPE 감지기 (YOLOv10 기반)
        self.ppe_detector = None
        self.ppe_visualizer = None
        self._ppe_status_cache = None  # 캐시된 PPE 상태
        self._ppe_detections_cache = None  # 캐시된 PPE 감지 결과 (바운딩 박스용)

        # 얼굴 인식 결과 캐시 (박스 표시용)
        self._face_results_cache = None  # 얼굴 인식 결과 {'faces': [], 'recognized_faces': []}

        # 일반 사물 인식 결과 캐시 (COCO 클래스)
        self._detected_objects_cache = []  # [{'class': str, 'class_kr': str, 'confidence': float, 'bbox': [...]}, ...]

        # ID 추적 관련 (마스크/얼굴 돌림 시 유지)
        self._tracked_persons = {}  # {track_id: {'name': str, 'bbox': (x1,y1,x2,y2), 'last_seen': time, 'confidence': float, 'center': (cx, cy)}}
        self._next_track_id = 1
        self._track_iou_threshold = 0.15  # 추적 IOU 임계값 (낮춰서 더 유연하게)
        self._track_timeout = None  # 타임아웃 없음 - 한번 인식하면 영구 추적
        self._track_center_dist_threshold = 200  # 중심점 거리 임계값 (픽셀) - 더 유연하게

        # 인식률 표시 관련
        self.mirror_stats_frame = None  # 인식률 표시 프레임
        self.mirror_normal_accuracy_label = None  # 인식률 레이블
        self.mirror_normal_accuracy = 0.0  # 인식률

        # AI 추론 백그라운드 스레드 관련
        self._ai_thread = None
        self._ai_thread_running = False
        self._ai_frame_queue = None  # 프레임 큐
        self._ai_result_lock = threading.Lock()  # 결과 동기화용 락

        # PTZ (Pan-Tilt-Zoom) 제어 관련
        self._ptz_controller = None  # TapoPTZController 인스턴스
        self._ptz_panel = None  # PTZ 컨트롤 패널 (UI)
        self._ptz_status_label = None  # PTZ 상태 레이블

        # 화재 감지 관련
        self.fire_detector = None
        self.fire_alert_panel = None
        self.fire_alert_manager = None
        self._init_fire_detection()

        # 초기 접속대기 상태 표시
        self._show_waiting_status()

        # 그래프 데이터 사전 로딩 버퍼
        self._graph_prefetched_data = None
        # 초기 사전 로딩 시도 (UI 준비 후 백그라운드에서 1회)
        self.after(300, self._prefetch_graph_data_async)
        
        # 카메라 준비 상태 확인 (백그라운드 스레드)
        self.after(500, self._check_camera_availability)

    def _fmt_text(self, t):
        """텍스트 포맷팅"""
        return "\n".join([p.strip() for p in (t or "").replace("\\n", "\n").split(",") if p.strip()])

    def _apply_header_font(self):
        """헤더 폰트 적용"""
        base = 12
        scale = self.app.header_scale.get()
        sz = max(10, int(base * scale))
        try:
            self.msg_label.configure(font=("Pretendard", sz))
        except Exception:
            pass

    def _show_waiting_status(self):
        """접속대기 상태 표시"""
        self._connection_status = "waiting"
        self.header.set_connection_status("waiting")
        self.tiles_container.set_connection_status("waiting")

    def _show_disconnected_status(self):
        """통신 끊김 상태 표시 - 마지막 값을 회색으로 표시"""
        self._connection_status = "disconnected"
        self.header.set_connection_status("disconnected")

        # 통신 끊김 메시지 표시
        self.status_msg_label.configure(text="⚠️ 통신 끊김 - 센서와의 연결이 끊어졌습니다 ⚠️")
        self.status_msg_label.pack(side="top", fill="x", padx=15, pady=(0, 8), after=self.header)

        # 타일을 회색으로 변경하되, 마지막 값은 유지
        for k in SENSOR_KEYS:
            last_value = self._last_values.get(k, "--")
            last_std = self._last_std_texts.get(k, "데이터 없음")
            # 회색 상태로 표시 (disconnected 모드)
            self.tiles_container.apply_gas_box_disconnected(k, last_value, last_std)

    def _show_detail(self, key):
        """상세 보기 표시"""
        # 오버레이가 없으면 지연 생성
        if self.overlay is None:
            from .panel_overlay import PanelOverlay
            self.overlay = PanelOverlay(self.tiles_container, self.app.logs, self.sid, self.peer, self._on_overlay_close)

        self.mode = "detail"
        self.overlay.show(key)

    def _on_overlay_close(self):
        """오버레이 닫기"""
        self.mode = "main"

    def switch_to_card_mode(self):
        """타일 모드로 전환"""
        if self.view_mode == "card":
            return

        # 다른 뷰 숨기기
        if self.graph_view:
            self.graph_view.pack_forget()
        if self.blueprint_view:
            self.blueprint_view.pack_forget()

        # 타일 표시
        self.tiles_container.pack(side="top", fill="both", expand=True, padx=12, pady=12)
        self.view_mode = "card"

        # 버튼 상태 업데이트
        self.header.update_mode_buttons("card")

    def switch_to_graph_mode(self):
        """그래프 모드로 전환"""
        if self.view_mode == "graph":
            return

        # 그래프 기능이 비활성화되어 있으면 실행 안 함
        try:
            graph_enabled = bool(self.app.cfg.env.get("graph_enabled", True))
            if not graph_enabled:
                print("[Panel] 그래프 기능이 비활성화되어 있습니다.")
                return
        except Exception:
            pass

        # 먼저 다른 패널의 그래프를 타일 모드로 전환 (단일 그래프 정책 적용)
        try:
            if hasattr(self.app, 'enforce_graph_view_policy'):
                self.app.enforce_graph_view_policy(self.sid_key)
        except Exception as e:
            print(f"[Panel] Error enforcing graph policy: {e}")

        # 다른 뷰 숨기기
        self.tiles_container.pack_forget()
        if self.blueprint_view:
            self.blueprint_view.pack_forget()

        # 그래프 뷰 컨테이너 생성 (최초 1회)
        if self.graph_view is None:
            from .panel_graph_view import PanelGraphView
            self.graph_view = PanelGraphView(self, self.app.logs, self.sid, self.peer, self.app.cfg)

        # 그래프 표시
        self.graph_view.pack(side="top", fill="both", expand=True, padx=12, pady=12)
        # 로딩 메시지 즉시 표시
        self._show_graph_loading()
        # 데이터 로딩을 백그라운드로 보내 UI 멈춤 방지
        threading.Thread(target=self._load_and_render_graph, daemon=True).start()
        self.view_mode = "graph"

        # 버튼 상태 업데이트
        self.header.update_mode_buttons("graph")
        # 그래프 동시 보기 정책 적용 (다른 패널 그래프 자동 해제)
        try:
            if hasattr(self.app, 'enforce_graph_view_policy'):
                self.app.enforce_graph_view_policy(self.sid_key)
        except Exception:
            pass

    def _load_and_render_graph(self):
        # 사전 로드된 데이터가 있으면 사용, 없으면 바로 조회
        data = None
        try:
            data = self._graph_prefetched_data
        except Exception:
            data = None
        if data is None:
            try:
                data = self.app.logs.get_sensor_history_hours(self.sid, self.peer, hours=1)
            except Exception:
                data = None
        # UI 스레드에서 실제 렌더링 처리
        self.after(0, lambda d=data: (self.graph_view.update_graphs(d), self._hide_graph_loading()))

    def _prefetch_graph_data_async(self):
        # 백그라운드에서 최초 데이터 한 번만 당겨와 캐시
        def _worker():
            try:
                data = self.app.logs.get_sensor_history_hours(self.sid, self.peer, hours=1)
                self._graph_prefetched_data = data
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _show_graph_loading(self):
        # 중복 생성 방지
        if hasattr(self, '_graph_loading') and self._graph_loading is not None:
            return
        self._graph_loading = tk.Label(self, text="그래프 데이터 로딩중", bg="#34495E", fg="#FFFFFF",
                                       font=("Pretendard", 80, "bold"))
        self._graph_loading.place(relx=0.5, rely=0.5, anchor="center")

    def _hide_graph_loading(self):
        if hasattr(self, '_graph_loading') and self._graph_loading is not None:
            try:
                self._graph_loading.destroy()
            finally:
                self._graph_loading = None

    def switch_to_blueprint_mode(self):
        """도면 모드로 전환"""
        if self.view_mode == "blueprint":
            return

        # 다른 뷰 숨기기
        self.tiles_container.pack_forget()
        if self.graph_view:
            self.graph_view.pack_forget()

        # 도면 뷰 컨테이너 생성 (최초 1회)
        if self.blueprint_view is None:
            from .panel_blueprint_view import PanelBlueprintView
            self.blueprint_view = PanelBlueprintView(self, self, self.app)

        # 도면 표시
        self.blueprint_view.pack(side="top", fill="both", expand=True, padx=12, pady=12)
        self.view_mode = "blueprint"

        # 버튼 상태 업데이트
        self.header.update_mode_buttons("blueprint")

    def show_safety_education(self):
        """안전 교육 화면 표시 (오버레이)"""
        from .safety_education import SafetyEducationDialog
        # self (SensorPanel의 프레임)를 parent로 전달, app도 전달하여 탭 숨기기 가능
        dialog = SafetyEducationDialog(self, self.app.cfg, app=self.app)
        dialog.show()

    def _get_today_stats_text(self, key):
        """오늘 통계 텍스트 생성 (LogManager에서) - 줄바꿈으로 출력"""
        stats = self.app.logs.get_today_stats(self.sid, self.peer, key)

        if not stats:
            return "오늘 통계:\n최저/평균/최고: - / - / -"

        mn = stats["min"]
        mx = stats["max"]
        avg = stats["avg"]

        # 포맷팅 (o2, temperature, humidity는 소수점 1자리, 나머지는 정수)
        if key in ("o2", "temperature", "humidity"):
            fmt = lambda x: f"{x:.1f}"
        else:
            fmt = lambda x: f"{x:.0f}"

        return f"오늘 통계:\n최저/평균/최고: {fmt(mn)} / {fmt(avg)} / {fmt(mx)}"

    def update_data(self, d):
        """센서 데이터 업데이트"""
        # 접속 상태를 연결됨으로 변경 (재연결 포함)
        # 연결 상태는 app.py의 on_data()에서 처리됨 (중복 제거)
        # 이 메서드는 검증된 데이터 업데이트만 담당

        self.data.update(d or {})

        # 데이터가 실제로 변경된 키만 처리
        changed_keys = set(d.keys()) if d else set()

        for k in changed_keys:
            if k not in SENSOR_KEYS:
                continue

            v = self.data.get(k)
            if v is None:
                continue

            # 가연성가스와 연기는 더미 센서이므로 접속 대기 상태로 표시
            if k in ["lel", "smoke"]:
                self.tiles_container.apply_gas_box(k, "--", "센서 연결 대기중...", True)
                continue

            # 5단계 경보 레벨 확인
            alert_level = self.alert_manager.get_alert_level(k, v)
            fv = float(v)
            
            # 경보 메시지와 색상 가져오기
            alert_msg = self.alert_manager.alert_messages[alert_level]
            alert_color = self.alert_manager.alert_colors[alert_level]

            # 포맷팅 및 표준 텍스트 생성 (5단계 시스템)
            if k == "co2":
                value_str = f"{fv:.0f}"
                std_text = f"기준: {self.app.cfg.std.get('co2_normal_max', 1000):.0f} ppm  {alert_msg}"
            elif k == "h2s":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('h2s_normal_max', 5):.1f} ppm  {alert_msg}"
            elif k == "co":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('co_normal_max', 9):.1f} ppm  {alert_msg}"
            elif k == "o2":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('o2_normal_min', 19.5):.1f}~{self.app.cfg.std.get('o2_normal_max', 23.0):.1f}%  {alert_msg}"
            elif k == "temperature":
                value_str = f"{fv:.1f}"
                std_text = f"권장: {self.app.cfg.std.get('temp_normal_min', 18):.0f}~{self.app.cfg.std.get('temp_normal_max', 28):.0f}℃  {alert_msg}"
            elif k == "humidity":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('hum_normal_min', 40):.0f}~{self.app.cfg.std.get('hum_normal_max', 60):.0f}%  {alert_msg}"
            elif k == "lel":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('lel_normal_max', 10):.1f}%  {alert_msg}"
            elif k == "smoke":
                value_str = f"{fv:.1f}"
                std_text = f"기준: {self.app.cfg.std.get('smoke_normal_max', 0):.1f} ppm  {alert_msg}"
            else:  # water
                value_str = "정상" if fv == 0 else "누수감지"
                # 누수는 2단계 시스템: 정상(1) 또는 심각(5)
                water_alert_level = 1 if fv == 0 else 5
                water_alert_msg = self.alert_manager.alert_messages[water_alert_level]
                water_alert_color = self.alert_manager.alert_colors[water_alert_level]
                std_text = f"상태: {'정상' if fv == 0 else '누수 감지됨'}  {water_alert_msg}"
                # 누수 센서는 별도 경보 레벨과 색상 사용
                alert_level = water_alert_level
                alert_color = water_alert_color

            # 마지막 값 저장 (통신 끊김 시 사용)
            self._last_values[k] = value_str
            self._last_std_texts[k] = std_text
            self._last_ok_states[k] = (alert_level <= 2)  # 정상 또는 관심

            # 5단계 색상으로 타일 업데이트
            self.tiles_container.apply_gas_box_with_color(k, value_str, std_text, alert_color, skip_autoscale=True, alert_level=alert_level)

            # 헤더 업데이트 (온습도)
            if k == "temperature":
                self.header.update_temperature(value_str)
            elif k == "humidity":
                self.header.update_humidity(value_str)

        # 통계는 1초마다만 업데이트 (매 데이터마다 업데이트 안함)
        now = time.time()
        if not hasattr(self, '_last_stats_update'):
            self._last_stats_update = 0

        if now - self._last_stats_update > 1.0:
            self._last_stats_update = now
            for k in SENSOR_KEYS:
                if self.data.get(k) is not None:
                    stat_text = self._get_today_stats_text(k)
                    self.tiles_container.update_stat(k, stat_text)

        # 그래프 뷰 실시간 업데이트 (5초마다)
        if not hasattr(self, '_last_graph_update'):
            self._last_graph_update = 0

        if self.view_mode == "graph" and self.graph_view is not None:
            if now - self._last_graph_update > 5.0:
                self._last_graph_update = now
                self.graph_view.update_graphs()

        # 도면 뷰 실시간 업데이트 (1초마다)
        if not hasattr(self, '_last_blueprint_update'):
            self._last_blueprint_update = 0

        if self.view_mode == "blueprint" and self.blueprint_view is not None:
            if now - self._last_blueprint_update > 1.0:
                self._last_blueprint_update = now
                self.blueprint_view.refresh_display()

        # 알림 상태 변화 확인 (변경된 키만) - 5단계 시스템
        if self._connection_status == "connected":
            for k in changed_keys:
                if k not in SENSOR_KEYS:
                    continue
                v = self.data.get(k)
                if v is not None:
                    alert_level = self.alert_manager.get_alert_level(k, v)
                    is_alarm = (alert_level >= 3)  # 주의(3) 이상이면 알림
                    if self.alert_manager.check_alarm_state_change(k, is_alarm):
                        # 헤더의 음성 경보 상태 확인
                        voice_enabled = getattr(self.header, 'voice_alert_enabled', True)
                        print(f"센서 이벤트 발생: {k}={v}, alert_level={alert_level}, voice_enabled={voice_enabled}")
                        # 오늘 경고 카운트 기록 및 헤더 갱신
                        try:
                            # 패널 키 기반 집계 + DB 영구 저장
                            self.app.record_alert(self.sid_key, self.sid, self.peer, k, alert_level, v)
                            if hasattr(self.header, 'update_alert_count'):
                                self.header.update_alert_count()
                        except Exception:
                            pass
                        self.alert_manager.speak_alert(k, v, voice_enabled)

        # 상세 화면 업데이트 (오버레이가 생성되어 있을 때만)
        if self.mode == "detail" and self.overlay:
            self.overlay.update()

        # 화재 감지 업데이트
        self._update_fire_detection()

    def _init_fire_detection(self):
        """화재 감지 시스템 초기화"""
        if not FIRE_MODULE_AVAILABLE:
            print("[Fire] 화재 감지 모듈을 사용할 수 없습니다")
            return

        try:
            # 화재 감지기 초기화
            self.fire_detector = FireDetector()
            print("[Fire] 화재 감지기 초기화 완료")

            # 화재 경보 다이얼로그 관리자 초기화
            self.fire_alert_manager = FireAlertManager(self.app)
            print("[Fire] 화재 경보 관리자 초기화 완료")

        except Exception as e:
            print(f"[Fire] 화재 감지 시스템 초기화 실패: {e}")
            self.fire_detector = None
            self.fire_alert_manager = None

    def _create_fire_panel(self):
        """화재 패널 UI 생성 (좌측 사이드바)"""
        if not FIRE_MODULE_AVAILABLE or FireAlertPanel is None:
            return

        try:
            # 화재 패널 생성 (좌측에 배치)
            self.fire_alert_panel = FireAlertPanel(self, self.app, width=280)
            # 타일 컨테이너 왼쪽에 배치
            self.fire_alert_panel.pack(side="left", fill="y", padx=(0, 10), before=self.tiles_container)
            print("[Fire] 화재 경보 패널 UI 생성 완료")
        except Exception as e:
            print(f"[Fire] 화재 경보 패널 생성 실패: {e}")
            self.fire_alert_panel = None

    def show_fire_panel(self):
        """화재 패널 표시"""
        if self.fire_alert_panel is None:
            self._create_fire_panel()
        elif not self.fire_alert_panel.winfo_ismapped():
            self.fire_alert_panel.pack(side="left", fill="y", padx=(0, 10), before=self.tiles_container)

    def hide_fire_panel(self):
        """화재 패널 숨기기"""
        if self.fire_alert_panel is not None and self.fire_alert_panel.winfo_ismapped():
            self.fire_alert_panel.pack_forget()

    def toggle_fire_panel(self):
        """화재 패널 토글"""
        if self.fire_alert_panel is None or not self.fire_alert_panel.winfo_ismapped():
            self.show_fire_panel()
        else:
            self.hide_fire_panel()

    def _update_fire_detection(self):
        """화재 감지 업데이트 - 센서 데이터로 화재 확률 계산"""
        if not FIRE_MODULE_AVAILABLE or self.fire_detector is None:
            return

        # 현재 센서 데이터로 SensorReading 생성
        try:
            from datetime import datetime
            reading = SensorReading(
                sensor_id=self.sid,
                timestamp=datetime.now(),
                temperature=self.data.get('temperature'),
                humidity=self.data.get('humidity'),
                co=self.data.get('co'),
                co2=self.data.get('co2'),
                o2=self.data.get('o2'),
                smoke=self.data.get('smoke'),
                h2s=self.data.get('h2s'),
                ch4=self.data.get('lel')  # lel은 ch4로 매핑
            )

            # 화재 감지 수행
            result = self.fire_detector.detect(reading)

            # 화재 패널 업데이트
            if self.fire_alert_panel is not None:
                # 경보 발생 센서 목록 (sensor_contributions에서 기여도가 높은 센서)
                triggered = []
                if result.sensor_contributions:
                    # 기여도가 0.1 이상인 센서를 경보 발생 센서로 표시
                    triggered = [k for k, v in result.sensor_contributions.items() if v >= 0.1]

                self.fire_alert_panel.update_fire_status(
                    level=result.alert_level.value if hasattr(result.alert_level, 'value') else result.alert_level,
                    probability=result.fire_probability,
                    triggered_sensors=triggered,
                    sensor_values={
                        'temperature': self.data.get('temperature'),
                        'humidity': self.data.get('humidity'),
                        'co': self.data.get('co'),
                        'co2': self.data.get('co2'),
                        'o2': self.data.get('o2'),
                        'smoke': self.data.get('smoke'),
                    }
                )

            # 경보 레벨 3(주의) 이상이면 다이얼로그 표시
            level_value = result.alert_level.value if hasattr(result.alert_level, 'value') else result.alert_level
            if level_value >= 3 and self.fire_alert_manager is not None:
                triggered = []
                if result.sensor_contributions:
                    triggered = [k for k, v in result.sensor_contributions.items() if v >= 0.1]
                self.fire_alert_manager.show_fire_alert(
                    level=level_value,
                    probability=result.fire_probability,
                    triggered_sensors=triggered,
                    sensor_values={
                        'temperature': self.data.get('temperature'),
                        'humidity': self.data.get('humidity'),
                        'co': self.data.get('co'),
                        'co2': self.data.get('co2'),
                        'o2': self.data.get('o2'),
                        'smoke': self.data.get('smoke'),
                    },
                    location=f"{self.sid} ({self.peer})"
                )

        except Exception as e:
            # 센서 데이터 부족 등 오류는 조용히 무시 (디버깅용 출력)
            # print(f"[Fire] 화재 감지 업데이트 오류: {e}")
            pass

    def refresh_alert_thresholds(self):
        """경보 임계값 실시간 적용"""
        try:
            # 경보 관리자에 새로운 임계값 적용
            if hasattr(self, 'alert_manager'):
                self.alert_manager.refresh_thresholds()
            # 타일 우측 기준값 라벨 갱신
            if hasattr(self, 'tiles_container') and hasattr(self.tiles_container, 'refresh_thresholds'):
                self.tiles_container.refresh_thresholds()
            print(f"패널 {self.sid_key}의 경보 임계값이 새로고침되었습니다.")
        except Exception as e:
            print(f"패널 {self.sid_key} 경보 임계값 새로고침 오류: {e}")

    def on_water_alert(self, alert_type, message, alert_level):
        """누수 알림 처리"""
        if alert_type == "water_leak_alert":
            # 누수 감지 시 즉시 경보 (헤더의 음성 경보 상태 확인)
            voice_enabled = getattr(self.header, 'voice_alert_enabled', True)
            print(f"누수 알림 발생: alert_type={alert_type}, voice_enabled={voice_enabled}")
            self.alert_manager.speak_alert("water", 1, voice_enabled)
            # 탭 색상 변경을 위해 앱에 알림
            if hasattr(self.app, 'set_tab_alert'):
                self.app.set_tab_alert(self.sid_key, True)
        elif alert_type == "water_normal_alert":
            # 누수 해제 시 탭 색상 복원
            if hasattr(self.app, 'set_tab_alert'):
                self.app.set_tab_alert(self.sid_key, False)
    
    def show_mirror_view(self):
        """거울보기 모드 활성화 - 카메라 화면을 타일 영역 전체에 표시"""
        if self.mirror_mode_active:
            return

        self.mirror_mode_active = True

        # 헤더 버튼 텍스트 동기화
        if hasattr(self, 'header') and hasattr(self.header, 'mirror_btn'):
            self.header.mirror_mode = True
            self.header.mirror_btn.configure(text="거울끄기", bg="#F44336")

        # 최신 프레임 저장 변수 초기화
        self.mirror_last_frame = None

        # 타일 컨테이너 숨기기
        self.tiles_container.pack_forget()

        # 화재 패널 숨기기 (거울보기 중에는 표시 안 함)
        if hasattr(self, 'fire_alert_panel') and self.fire_alert_panel:
            self.fire_alert_panel.pack_forget()

        # 인식률 프레임 생성
        if self.mirror_stats_frame is None:
            self.mirror_stats_frame = tk.Frame(self, bg="#2C3E50", height=40)

            # 왼쪽: 인식률 레이블
            self.mirror_normal_accuracy_label = tk.Label(
                self.mirror_stats_frame,
                text="인식률: 0.0%",
                font=("Pretendard", 13, "bold"),
                bg="#2C3E50",
                fg="#E74C3C",
                padx=10,
                pady=5
            )
            self.mirror_normal_accuracy_label.pack(side="left", padx=(15, 10))

            # 화면 반전 설정값 읽기 (카메라 설정에서 저장된 값 사용)
            flip_value = True  # 기본값
            if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                flip_value = self.app.cfg.camera.get("flip_horizontal", True)
            self.mirror_flip_var = tk.BooleanVar(value=flip_value)

            # 화면 반전 체크박스
            self.mirror_flip_checkbox = tk.Checkbutton(
                self.mirror_stats_frame,
                text="🔄 화면반전",
                variable=self.mirror_flip_var,
                font=("Pretendard", 11),
                bg="#2C3E50",
                fg="#FFFFFF",
                selectcolor="#34495E",
                activebackground="#2C3E50",
                activeforeground="#FFFFFF"
            )
            self.mirror_flip_checkbox.pack(side="left", padx=(5, 20))

            # 카메라 이름 표시 (오른쪽) - 설정은 설정-카메라에서 함
            try:
                camera_info_label = tk.Label(
                    self.mirror_stats_frame,
                    text="📷 " + self._get_current_camera_name(),
                    font=("Pretendard", 11),
                    bg="#2C3E50",
                    fg="#AAAAAA"
                )
                camera_info_label.pack(side="right", padx=(0, 15))
                self.mirror_camera_info_label = camera_info_label
            except Exception as e:
                print(f"[카메라] 정보 레이블 생성 오류: {e}")

        else:
            # 거울보기 재실행 시 카메라 설정에서 화면 반전 값 다시 읽기
            flip_value = True  # 기본값
            if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                flip_value = self.app.cfg.camera.get("flip_horizontal", True)
            if self.mirror_flip_var is not None:
                self.mirror_flip_var.set(flip_value)
            # 카메라 이름도 업데이트
            if hasattr(self, 'mirror_camera_info_label'):
                try:
                    self.mirror_camera_info_label.configure(text="📷 " + self._get_current_camera_name())
                except Exception:
                    pass

        # 통합 프레임 표시 (컴팩트하게)
        self.mirror_stats_frame.pack(side="top", fill="x", padx=12, pady=(5, 2))

        # 카메라 + 좌우 패널 컨테이너
        if not hasattr(self, 'mirror_content_frame') or self.mirror_content_frame is None:
            self.mirror_content_frame = tk.Frame(self, bg="#1A1A1A")
        self.mirror_content_frame.pack(side="top", fill="both", expand=True, padx=5, pady=(2, 5))

        # === 안전장구 패널 생성 (왼쪽) - 검정 배경 ===
        if not hasattr(self, 'mirror_ppe_panel') or self.mirror_ppe_panel is None:
            self.mirror_ppe_panel = tk.Frame(self.mirror_content_frame, bg="#000000", width=250)
            self.mirror_ppe_panel.pack_propagate(False)

        # PPE 인식 활성화 여부 확인
        ppe_detection_on = True
        try:
            ppe_detection_on = bool(self.app.cfg.env.get('ppe_detection_enabled', True))
        except Exception:
            pass

        if ppe_detection_on:
            self.mirror_ppe_panel.pack(side="left", fill="y", padx=(0, 2))
            self._update_ppe_panel()
        else:
            self.mirror_ppe_panel.pack_forget()

        # 카메라 라벨 생성 (중앙)
        if self.mirror_camera_label is None:
            self.mirror_camera_label = tk.Label(self.mirror_content_frame, bg="#000000", text="카메라 로딩 중...",
                                               font=("Pretendard", 24, "bold"), fg="#FFFFFF")
        self.mirror_camera_label.pack(side="left", fill="both", expand=True)

        # === 실시간 설정 미니 패널 생성 (좌측 하단 오버레이) ===
        self._create_realtime_settings_panel()

        # === 사물 인식 패널 생성 (오른쪽) - 검정 배경 ===
        if not hasattr(self, 'mirror_object_panel') or self.mirror_object_panel is None:
            self.mirror_object_panel = tk.Frame(self.mirror_content_frame, bg="#000000", width=300)
            self.mirror_object_panel.pack_propagate(False)

        # 사물 인식 활성화 여부 확인 (성능 모드 3 이상에서만)
        object_detection_on = False
        try:
            performance_mode = int(self.app.cfg.env.get('performance_mode', 2))
            if performance_mode >= 3:
                object_detection_on = bool(self.app.cfg.env.get('object_detection_enabled', False))
        except Exception:
            pass

        if object_detection_on:
            self.mirror_object_panel.pack(side="right", fill="y", padx=(2, 0))
            self._update_object_panel()
        else:
            self.mirror_object_panel.pack_forget()

        # 카메라 초기화 및 시작
        self._start_mirror_camera()

    def hide_mirror_view(self):
        """거울보기 모드 비활성화 - 원래 타일 화면으로 복귀"""
        if not self.mirror_mode_active:
            return

        self.mirror_mode_active = False
        self.mirror_frame_count = 0  # 프레임 카운터 리셋

        # 헤더 버튼 텍스트 동기화
        if hasattr(self, 'header') and hasattr(self.header, 'mirror_btn'):
            self.header.mirror_mode = False
            if self.header.mirror_camera_ready:
                self.header.mirror_btn.configure(text="거울보기", bg="#9C27B0")
            else:
                self.header.mirror_btn.configure(text="거울 준비중", bg="#9C27B0", state="disabled")

        # 카메라 중지
        self._stop_mirror_camera()

        # PTZ 컨트롤 숨기기 및 연결 해제
        self._hide_ptz_controls()
        if self._ptz_controller:
            self._ptz_controller.disconnect()
            self._ptz_controller = None

        # 인식률 프레임 숨기기
        if self.mirror_stats_frame:
            self.mirror_stats_frame.pack_forget()

        # 안전장구 패널 숨기기
        if hasattr(self, 'mirror_ppe_panel') and self.mirror_ppe_panel:
            self.mirror_ppe_panel.pack_forget()

        # 사물 인식 패널 숨기기
        if hasattr(self, 'mirror_object_panel') and self.mirror_object_panel:
            self.mirror_object_panel.pack_forget()

        # 카메라 라벨 숨기기
        if self.mirror_camera_label:
            self.mirror_camera_label.pack_forget()
            # 이미지 참조 해제
            self.mirror_camera_label.image = None

        # 실시간 설정 패널 숨기기
        self._hide_realtime_settings_panel()

        # 컨텐츠 프레임 숨기기
        if hasattr(self, 'mirror_content_frame') and self.mirror_content_frame:
            self.mirror_content_frame.pack_forget()

        # 화재 패널 다시 표시 (거울보기 해제 시)
        if hasattr(self, 'fire_alert_panel') and self.fire_alert_panel:
            self.fire_alert_panel.pack(side="left", fill="y", padx=(0, 10), before=self.tiles_container)

        # 타일 컨테이너 다시 표시
        self.tiles_container.pack(side="top", fill="both", expand=True, padx=12, pady=12)

    def _start_mirror_camera(self):
        """거울보기용 카메라 시작 (빠른 초기화)"""
        try:
            import cv2
            import platform
            CV2_OK = True
            IS_WINDOWS = platform.system().lower() == 'windows'
        except ImportError:
            CV2_OK = False
            if self.mirror_camera_label:
                self.mirror_camera_label.configure(text="OpenCV가 설치되지 않았습니다.\n카메라 기능을 사용할 수 없습니다.",
                                                  fg="#FF6B6B")
            return

        if self.mirror_camera is not None:
            return  # 이미 실행 중

        try:
            # 고급 설정 로드
            self._load_advanced_settings()

            # 카메라 설정에서 IP 카메라/USB 카메라 정보 읽기
            ip_url = None
            selected_idx = None
            use_ip_camera = False

            try:
                if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                    # use_ip_camera 설정 확인 (명시적으로 IP 카메라 사용 여부)
                    use_ip_camera = self.app.cfg.camera.get("use_ip_camera", False)
                    ip_url = self.app.cfg.camera.get("ip_camera_url", "")
                    if not ip_url:
                        ip_url = None
                    selected_idx = self.app.cfg.camera.get("device_index", 0)
                    print(f"[카메라 설정] use_ip_camera={use_ip_camera}, ip_url={ip_url}, device_index={selected_idx}")
            except Exception as e:
                print(f"[카메라 설정] 읽기 오류: {e}")

            # IP 카메라 사용이 설정되어 있고 URL이 있으면 IP 카메라 사용
            if use_ip_camera and ip_url:
                print(f"거울보기: IP 카메라 연결 (설정) - {ip_url}")
                self._connect_ip_camera(ip_url)
                return

            # USB 카메라 사용 시 IP 카메라 URL 초기화 (중요!)
            self._ip_camera_url = None

            cached_index = getattr(self, '_cached_camera_index', None)
            cached_backend = getattr(self, '_cached_camera_backend', None)

            # 설정에서 선택된 카메라가 있으면 우선 사용
            if selected_idx is not None and selected_idx >= 0:
                cached_index = selected_idx

            camera_index = None
            backend_used = None

            # 캐시가 있으면 바로 시도
            if cached_index is not None:
                try:
                    if cached_backend is not None:
                        test_camera = cv2.VideoCapture(cached_index, cached_backend)
                    else:
                        test_camera = cv2.VideoCapture(cached_index)

                    if test_camera.isOpened():
                        ret, frame = test_camera.read()
                        if ret and frame is not None:
                            camera_index = cached_index
                            backend_used = cached_backend
                            test_camera.release()
                            print(f"거울보기: 캐시된 카메라 {cached_index} 사용")
                        else:
                            test_camera.release()
                except Exception:
                    pass

            # 캐시된 카메라가 없거나 실패하면 빠르게 검색 (인덱스 0만 우선 시도)
            if camera_index is None:
                # Linux: V4L2 백엔드로 카메라 0번만 빠르게 시도
                if not IS_WINDOWS:
                    try:
                        test_camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
                        if test_camera.isOpened():
                            ret, frame = test_camera.read()
                            if ret and frame is not None:
                                camera_index = 0
                                backend_used = cv2.CAP_V4L2
                                test_camera.release()
                                print(f"거울보기: 카메라 0을 V4L2 백엔드로 찾았습니다.")
                            else:
                                test_camera.release()
                    except Exception:
                        pass

                # 기본 백엔드로 카메라 0번 시도
                if camera_index is None:
                    try:
                        test_camera = cv2.VideoCapture(0)
                        if test_camera.isOpened():
                            ret, frame = test_camera.read()
                            if ret and frame is not None:
                                camera_index = 0
                                backend_used = None
                                test_camera.release()
                                print(f"거울보기: 카메라 0을 기본 백엔드로 찾았습니다.")
                            else:
                                test_camera.release()
                    except Exception:
                        pass

                # 여전히 없으면 다른 인덱스도 시도 (V4L2 sysfs 기반 검색)
                if camera_index is None:
                    import os
                    for i in range(10):
                        device_path = f"/dev/video{i}"
                        if not os.path.exists(device_path):
                            continue
                        # 메타데이터 장치 필터링 (index != 0)
                        index_path = f"/sys/class/video4linux/video{i}/index"
                        if os.path.exists(index_path):
                            try:
                                with open(index_path, 'r') as f:
                                    if f.read().strip() != '0':
                                        continue
                            except:
                                continue
                        try:
                            test_camera = cv2.VideoCapture(i, cv2.CAP_V4L2)
                            if test_camera.isOpened():
                                ret, frame = test_camera.read()
                                if ret and frame is not None:
                                    camera_index = i
                                    backend_used = cv2.CAP_V4L2
                                    test_camera.release()
                                    print(f"거울보기: 카메라 {i}을 찾았습니다.")
                                    break
                                test_camera.release()
                        except Exception:
                            continue

            if camera_index is None:
                if self.mirror_camera_label:
                    self.mirror_camera_label.configure(
                        text="카메라 사용 불가\n\n카메라가 연결되지 않았거나\n다른 프로그램에서 사용 중입니다.",
                        fg="#FF6B6B")
                return

            # 성공한 카메라 설정 캐시
            self._cached_camera_index = camera_index
            self._cached_camera_backend = backend_used

            # 카메라 열기 (사용한 백엔드로)
            if backend_used is not None:
                self.mirror_camera = cv2.VideoCapture(camera_index, backend_used)
            else:
                self.mirror_camera = cv2.VideoCapture(camera_index)
            
            if not self.mirror_camera.isOpened():
                if self.mirror_camera_label:
                    self.mirror_camera_label.configure(
                        text="카메라를 열 수 없습니다.\n카메라를 확인해주세요.",
                        fg="#FF6B6B")
                return
            
            # 카메라 설정 - 최대 화각(FOV)으로 설정
            try:
                # 해상도 설정 (1920x1080 Full HD로 더 넓은 화각)
                self.mirror_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.mirror_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.mirror_camera.set(cv2.CAP_PROP_FPS, 30)
                self.mirror_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                # 화각(FOV) 최대화 설정
                try:
                    # 줌을 최소값(0)으로 설정하면 화각이 최대로 넓어짐
                    self.mirror_camera.set(cv2.CAP_PROP_ZOOM, 0)
                    print("거울보기: 줌 최소값 설정 (화각 최대)")
                except:
                    pass

                try:
                    # FOV(Field of View) 직접 설정 시도 (지원하는 카메라만)
                    # CAP_PROP_XI_LENS_APERTURE_VALUE = 511 (일부 카메라)
                    # 일반적으로 줌=0이 가장 넓은 화각
                    pass
                except:
                    pass

                # Auto-focus 끄기 (일부 카메라에서 문제 발생 방지)
                try:
                    self.mirror_camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                except:
                    pass

                # 실제 적용된 해상도 확인
                actual_w = int(self.mirror_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.mirror_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_zoom = self.mirror_camera.get(cv2.CAP_PROP_ZOOM)
                print(f"거울보기: 카메라 설정 완료 - 해상도: {actual_w}x{actual_h}, 줌: {actual_zoom}")
            except Exception as e:
                print(f"거울보기: 카메라 설정 오류 (무시): {e}")
            
            # 초기 프레임 몇 개 버리기 (카메라 초기화 대기)
            for _ in range(5):
                try:
                    self.mirror_camera.read()
                except:
                    pass
            
            # 새로운 PPE 감지기 초기화 (YOLOv10 기반) - 우선
            if PPE_DETECTOR_AVAILABLE:
                try:
                    self.ppe_detector = PPEDetector()
                    self.ppe_visualizer = PPEVisualizer(font_size=20)
                    print("거울보기: YOLOv10 PPE 감지기 초기화 완료")
                except Exception as e:
                    print(f"거울보기: YOLOv10 PPE 감지기 초기화 실패: {e}")
                    self.ppe_detector = None
                    self.ppe_visualizer = None

            # 기존 안전장구 감지기 초기화 (fallback)
            try:
                from ..sensor.safety_detector import SafetyEquipmentDetector
                self.safety_detector = SafetyEquipmentDetector(camera=None)
                self.safety_detector.set_camera(self.mirror_camera)
                # 얼굴 인식 기능 활성화
                self.safety_detector.enable_face_recognition(True)
                print("거울보기: 기존 안전장구 감지 시스템 초기화 완료 (fallback)")
            except Exception as e:
                print(f"거울보기: 기존 안전장구 감지 시스템 초기화 실패: {e}")
                self.safety_detector = None
                # 감지기 실패해도 카메라 화면은 표시되어야 함
            
            # 프레임 업데이트 시작
            self._update_mirror_frame()
            
            # 카메라가 성공적으로 시작되면 헤더 버튼을 "거울보기"로 변경
            if hasattr(self, 'header') and hasattr(self.header, 'set_mirror_camera_ready'):
                self.header.set_mirror_camera_ready(True)
            
        except Exception as e:
            import traceback
            print(f"거울보기 카메라 시작 오류: {e}")
            traceback.print_exc()

            error_msg = str(e)
            # 권한 오류 감지
            if "Permission denied" in error_msg or "EACCES" in error_msg:
                error_msg = "카메라 접근 권한 없음\n\n다음 명령 실행 후 재로그인:\nsudo usermod -aG video $USER"
            elif "Device or resource busy" in error_msg:
                error_msg = "카메라가 다른 프로그램에서\n사용 중입니다."

            if self.mirror_camera_label:
                self.mirror_camera_label.configure(text=f"카메라 오류:\n{error_msg}", fg="#FF6B6B")
            # 실패 시 카메라 정리 및 버튼 상태 유지
            try:
                if self.mirror_camera:
                    self.mirror_camera.release()
                    self.mirror_camera = None
            except:
                pass
            # 카메라 실패 시 버튼 상태는 "거울 준비중"으로 유지
    
    def _update_mirror_frame(self):
        """거울보기 카메라 프레임 업데이트"""
        # 거울보기 모드가 비활성화되었거나 카메라가 없으면 중지
        if not self.mirror_mode_active or self.mirror_camera is None:
            return

        # 카메라 라벨이 유효한지 확인 (pyimage 오류 방지)
        if self.mirror_camera_label is None:
            return
        try:
            if not self.mirror_camera_label.winfo_exists():
                return
        except Exception:
            return
        
        try:
            import cv2
            from PIL import Image, ImageTk

            # 버퍼 비우기: 오래된 프레임 제거 (버퍼링 방지)
            # grab()은 프레임을 버퍼에서 제거만 하고 디코딩하지 않아 빠름
            for _ in range(2):
                self.mirror_camera.grab()

            # 최신 프레임 읽기
            ret = False
            frame = None
            try:
                ret, frame = self.mirror_camera.read()
            except Exception as e:
                print(f"거울보기 프레임 읽기 실패: {e}")
                # 카메라 재초기화 시도
                self.after(100, self._restart_mirror_camera)
                return
            
            if ret and frame is not None:
                self.mirror_frame_count += 1

                # FPS 계산 (실시간 설정 패널용)
                current_time = time.time()
                if not hasattr(self, '_fps_last_time'):
                    self._fps_last_time = current_time
                    self._fps_frame_count = 0
                    self._current_fps = 0.0

                self._fps_frame_count += 1
                elapsed = current_time - self._fps_last_time
                if elapsed >= 1.0:  # 1초마다 FPS 업데이트
                    self._current_fps = self._fps_frame_count / elapsed
                    self._fps_frame_count = 0
                    self._fps_last_time = current_time

                # 이미지 전처리 적용 (고급 설정)
                frame = self._apply_image_processing(frame)

                # 배경 학습을 위해 최신 프레임 저장
                self.mirror_last_frame = frame.copy()

                # 첫 프레임이면 로딩 텍스트 제거
                if self.mirror_frame_count == 1:
                    if self.mirror_camera_label:
                        self.mirror_camera_label.configure(text="")

                # 안전장구 감지 및 화면 표시
                # 성능 최적화: AI 추론을 백그라운드 스레드에서 실행하여 UI 블로킹 방지
                detection_results = None

                if self.safety_detection_enabled and (self.ppe_detector is not None or self.safety_detector is not None):
                    # 백그라운드 AI 스레드 시작 (아직 실행 중이 아니면)
                    if not self._ai_thread_running:
                        self._start_ai_thread()

                    # 5프레임마다 AI 추론용 프레임 전달 (약 6fps, 실시간 반응)
                    if self.mirror_frame_count % 5 == 1:
                        if self._ai_frame_queue is not None:
                            try:
                                # 큐가 비어있으면 프레임 추가 (이전 프레임 버리고 최신만 유지)
                                while not self._ai_frame_queue.empty():
                                    try:
                                        self._ai_frame_queue.get_nowait()
                                    except:
                                        break

                                # 디버그: 큐에 넣기 전 프레임 상태 (100프레임마다)
                                if self.mirror_frame_count % 500 == 1:
                                    import numpy as np
                                    h, w = frame.shape[:2]
                                    mean_val = np.mean(frame)
                                    is_ip = hasattr(self, '_ip_camera_url') and self._ip_camera_url
                                    print(f"[Frame Queue] 프레임 #{self.mirror_frame_count}: {w}x{h}, mean={mean_val:.1f}, IP={is_ip}")

                                self._ai_frame_queue.put_nowait(frame.copy())
                            except:
                                pass

                    # 캐시된 결과 사용 (스레드에서 업데이트됨)
                    with self._ai_result_lock:
                        detection_results = getattr(self, '_cached_detection_results', None)

                # 2) 화면 반전 여부 확인 (체크박스 상태)
                should_flip = self.mirror_flip_var.get() if self.mirror_flip_var else True

                # 3) 영상 처리
                # 중요: 인식은 항상 원본 프레임으로 수행되었고, 표시만 반전
                if should_flip:
                    # 좌우 반전 (거울 모드)
                    try:
                        flipped_bgr = cv2.flip(frame, 1)
                    except Exception as e:
                        if self.mirror_frame_count % 30 == 0:
                            print(f"거울보기: 좌우 반전 오류: {e}")
                        flipped_bgr = frame

                    # 반전된 프레임 위에 PPE 상태/바운딩박스/안전률 표시
                    if detection_results is not None:
                        try:
                            # 새로운 PPE Visualizer 사용 (우선)
                            if self.ppe_visualizer is not None and self._ppe_status_cache is not None:
                                # 활성화된 항목 및 이름 (config에서 가져오기)
                                enabled_items = {
                                    'helmet': self.app.cfg.env.get('ppe_helmet_enabled', True),
                                    'vest': self.app.cfg.env.get('ppe_vest_enabled', True),
                                    'mask': self.app.cfg.env.get('ppe_mask_enabled', True),
                                    'glasses': self.app.cfg.env.get('ppe_glasses_enabled', True),
                                    'gloves': self.app.cfg.env.get('ppe_gloves_enabled', True),
                                    'boots': self.app.cfg.env.get('ppe_boots_enabled', True)
                                }
                                item_names = {
                                    'helmet': self.app.cfg.env.get('ppe_helmet_name', '헬멧'),
                                    'vest': self.app.cfg.env.get('ppe_vest_name', '조끼'),
                                    'mask': self.app.cfg.env.get('ppe_mask_name', '마스크'),
                                    'glasses': self.app.cfg.env.get('ppe_glasses_name', '보안경'),
                                    'gloves': self.app.cfg.env.get('ppe_gloves_name', '장갑'),
                                    'boots': self.app.cfg.env.get('ppe_boots_name', '안전화')
                                }

                                # 프레임 너비 미리 계산 (얼굴 박스 그리기에서도 사용)
                                frame_width = flipped_bgr.shape[1]

                                # 1) 바운딩 박스 그리기 (반전된 좌표로)
                                if self._ppe_detections_cache:
                                    flipped_bgr = self._draw_flipped_detections(
                                        flipped_bgr, self._ppe_detections_cache, frame_width
                                    )

                                # PPE 상태/안전률은 왼쪽 별도 패널에 표시 (카메라 영역 외부)

                                # 2) 얼굴 인식 박스 그리기 (기존 safety_detector 사용)
                                if self.safety_detector is not None and self._face_results_cache:
                                    flipped_bgr = self._draw_face_boxes_flipped(
                                        flipped_bgr, self._face_results_cache, frame_width
                                    )
                            # 기존 safety_detector 사용 (fallback)
                            elif self.safety_detector is not None:
                                flipped_bgr = self.safety_detector.draw_results_on_flipped(flipped_bgr, detection_results)
                        except Exception as e:
                            if self.mirror_frame_count % 30 == 0:
                                print(f"거울보기: 프레임 시각화 오류: {e}")

                    # 사물 인식 바운딩 박스 그리기 (거울 모드)
                    if self._detected_objects_cache:
                        try:
                            flipped_bgr = self._draw_detected_objects_boxes(
                                flipped_bgr, self._detected_objects_cache, flipped=True
                            )
                        except Exception as e:
                            if self.mirror_frame_count % 30 == 0:
                                print(f"거울보기: 사물 인식 시각화 오류: {e}")

                    display_frame = flipped_bgr
                else:
                    # 반전 안 함 (일반 모드)
                    display_frame = frame.copy()

                    # 원본 프레임 위에 PPE 상태/바운딩박스/안전률 표시
                    if detection_results is not None:
                        try:
                            # 새로운 PPE Visualizer 사용 (우선)
                            if self.ppe_visualizer is not None and self._ppe_status_cache is not None:
                                # 활성화된 항목 및 이름 (config에서 가져오기)
                                enabled_items = {
                                    'helmet': self.app.cfg.env.get('ppe_helmet_enabled', True),
                                    'vest': self.app.cfg.env.get('ppe_vest_enabled', True),
                                    'mask': self.app.cfg.env.get('ppe_mask_enabled', True),
                                    'glasses': self.app.cfg.env.get('ppe_glasses_enabled', True),
                                    'gloves': self.app.cfg.env.get('ppe_gloves_enabled', True),
                                    'boots': self.app.cfg.env.get('ppe_boots_enabled', True)
                                }
                                item_names = {
                                    'helmet': self.app.cfg.env.get('ppe_helmet_name', '헬멧'),
                                    'vest': self.app.cfg.env.get('ppe_vest_name', '조끼'),
                                    'mask': self.app.cfg.env.get('ppe_mask_name', '마스크'),
                                    'glasses': self.app.cfg.env.get('ppe_glasses_name', '보안경'),
                                    'gloves': self.app.cfg.env.get('ppe_gloves_name', '장갑'),
                                    'boots': self.app.cfg.env.get('ppe_boots_name', '안전화')
                                }

                                # 1) 바운딩 박스 그리기
                                if self._ppe_detections_cache:
                                    display_frame = self.ppe_visualizer.draw_detections(
                                        display_frame, self._ppe_detections_cache
                                    )

                                # PPE 상태/안전률은 왼쪽 별도 패널에 표시 (카메라 영역 외부)

                                # 2) 얼굴 인식 박스 그리기 (기존 safety_detector 사용)
                                if self.safety_detector is not None and self._face_results_cache:
                                    display_frame = self._draw_face_boxes(
                                        display_frame, self._face_results_cache
                                    )
                            # 기존 safety_detector 사용 (fallback)
                            elif self.safety_detector is not None:
                                display_frame = self.safety_detector.draw_results_on_frame(display_frame, detection_results)
                        except Exception as e:
                            if self.mirror_frame_count % 30 == 0:
                                print(f"거울보기: 프레임 시각화 오류: {e}")

                    # 사물 인식 바운딩 박스 그리기 (일반 모드)
                    if self._detected_objects_cache:
                        try:
                            display_frame = self._draw_detected_objects_boxes(
                                display_frame, self._detected_objects_cache, flipped=False
                            )
                        except Exception as e:
                            if self.mirror_frame_count % 30 == 0:
                                print(f"거울보기: 사물 인식 시각화 오류: {e}")

                # 5) 최소 인식 화소 영역 박스 그리기 (화면 상단 중앙)
                try:
                    h, w = display_frame.shape[:2]
                    # 최소 인식 크기: 사람 50×100, 헬멧 30×30, 얼굴 40×40
                    min_person_w, min_person_h = 50, 100
                    min_helmet_size = 30
                    min_face_size = 40

                    # 화면 상단 중앙에 표시 (10픽셀 마진)
                    margin_top = 10
                    center_x = w // 2

                    # 사람 인식 최소 영역 (빨간 점선)
                    person_x1 = center_x - min_person_w // 2
                    person_y1 = margin_top
                    person_x2 = center_x + min_person_w // 2
                    person_y2 = margin_top + min_person_h

                    # 점선 효과 (대시 패턴)
                    dash_length = 5
                    for i in range(person_x1, person_x2, dash_length * 2):
                        cv2.line(display_frame, (i, person_y1), (min(i + dash_length, person_x2), person_y1), (0, 0, 255), 1)
                        cv2.line(display_frame, (i, person_y2), (min(i + dash_length, person_x2), person_y2), (0, 0, 255), 1)
                    for i in range(person_y1, person_y2, dash_length * 2):
                        cv2.line(display_frame, (person_x1, i), (person_x1, min(i + dash_length, person_y2)), (0, 0, 255), 1)
                        cv2.line(display_frame, (person_x2, i), (person_x2, min(i + dash_length, person_y2)), (0, 0, 255), 1)

                    # 헬멧 인식 최소 영역 (초록 실선, 사람 박스 오른쪽)
                    helmet_x1 = person_x2 + 15
                    helmet_y1 = margin_top
                    helmet_x2 = helmet_x1 + min_helmet_size
                    helmet_y2 = helmet_y1 + min_helmet_size
                    cv2.rectangle(display_frame, (helmet_x1, helmet_y1), (helmet_x2, helmet_y2), (0, 255, 0), 1)

                    # 얼굴 인식 최소 영역 (노란 실선, 헬멧 박스 오른쪽)
                    face_x1 = helmet_x2 + 10
                    face_y1 = margin_top
                    face_x2 = face_x1 + min_face_size
                    face_y2 = face_y1 + min_face_size
                    cv2.rectangle(display_frame, (face_x1, face_y1), (face_x2, face_y2), (0, 255, 255), 1)

                    # 레이블 표시 (프레임 카운터가 일정 이상이면 표시)
                    if self.mirror_frame_count > 5:
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.4
                        thickness = 1

                        # 사람 레이블
                        cv2.putText(display_frame, "Person", (person_x1, person_y2 + 12),
                                   font, font_scale, (0, 0, 255), thickness)
                        cv2.putText(display_frame, f"{min_person_w}x{min_person_h}px", (person_x1, person_y2 + 24),
                                   font, font_scale, (0, 0, 255), thickness)

                        # 헬멧 레이블
                        cv2.putText(display_frame, "PPE", (helmet_x1, helmet_y2 + 12),
                                   font, font_scale, (0, 255, 0), thickness)
                        cv2.putText(display_frame, f"{min_helmet_size}px", (helmet_x1, helmet_y2 + 24),
                                   font, font_scale, (0, 255, 0), thickness)

                        # 얼굴 레이블
                        cv2.putText(display_frame, "Face", (face_x1, face_y2 + 12),
                                   font, font_scale, (0, 255, 255), thickness)
                        cv2.putText(display_frame, f"{min_face_size}px", (face_x1, face_y2 + 24),
                                   font, font_scale, (0, 255, 255), thickness)

                    # 거리 추정 자 표시 (화면 우측)
                    # 사람 바운딩 박스 높이 기반 대략적 거리 추정
                    # 기준: 720p 카메라에서 평균 사람(170cm)이 화면 전체 높이일 때 약 1m
                    ruler_x = w - 40  # 오른쪽 여백
                    ruler_y_start = 50
                    ruler_height = min(h - 100, 400)  # 최대 400px 높이

                    # 거리 자 배경 (반투명 효과 - 검정 선)
                    cv2.rectangle(display_frame, (ruler_x - 5, ruler_y_start - 5),
                                 (ruler_x + 25, ruler_y_start + ruler_height + 20),
                                 (0, 0, 0), -1)

                    # 거리 눈금 (0.5m ~ 5m 범위)
                    # 사람 높이 픽셀과 거리 관계: 거리 = k / pixel_height
                    # 대략적 추정: 720px = 1m, 360px = 2m, 180px = 4m
                    distances = [1, 2, 3, 4, 5]  # 미터
                    pixel_heights = [ruler_height, ruler_height//2, ruler_height//3, ruler_height//4, ruler_height//5]

                    # 자 선 그리기
                    cv2.line(display_frame, (ruler_x, ruler_y_start),
                            (ruler_x, ruler_y_start + ruler_height), (255, 255, 255), 2)

                    # 눈금 표시
                    for i, (dist, px_h) in enumerate(zip(distances, pixel_heights)):
                        y_pos = ruler_y_start + (ruler_height - px_h)
                        # 눈금 선
                        cv2.line(display_frame, (ruler_x - 5, y_pos), (ruler_x + 5, y_pos), (255, 255, 255), 1)
                        # 거리 표시
                        cv2.putText(display_frame, f"{dist}m", (ruler_x + 8, y_pos + 4),
                                   font, 0.35, (255, 255, 255), 1)

                    # 사람이 감지된 경우 해당 거리에 마커 표시
                    if self._ppe_detections_cache:
                        for det in self._ppe_detections_cache:
                            # PersonDetection 객체 또는 dict 모두 지원
                            if hasattr(det, 'bbox'):
                                # PersonDetection 객체
                                bbox_obj = det.bbox
                                if hasattr(bbox_obj, 'class_name') and bbox_obj.class_name == 'person':
                                    person_height = bbox_obj.height
                                elif hasattr(bbox_obj, 'y2') and hasattr(bbox_obj, 'y1'):
                                    person_height = bbox_obj.y2 - bbox_obj.y1
                                else:
                                    continue
                            elif isinstance(det, dict):
                                # dict 형태
                                if det.get('class_name') != 'person':
                                    continue
                                bbox = det.get('bbox', [])
                                if len(bbox) >= 4:
                                    person_height = bbox[3] - bbox[1]
                                else:
                                    continue
                            else:
                                continue

                            if person_height > 50:  # 최소 인식 크기 이상
                                # 거리 추정 (매우 대략적)
                                # 기준: 화면 높이의 70%가 1m일 때
                                ref_height = h * 0.7
                                estimated_dist = ref_height / person_height
                                estimated_dist = max(0.5, min(10, estimated_dist))  # 0.5m ~ 10m 범위 제한

                                # 자에 마커 표시
                                marker_y = ruler_y_start + int(ruler_height * (1 - 1/estimated_dist))
                                marker_y = max(ruler_y_start, min(ruler_y_start + ruler_height, marker_y))

                                cv2.circle(display_frame, (ruler_x, marker_y), 5, (0, 165, 255), -1)
                                cv2.putText(display_frame, f"~{estimated_dist:.1f}m",
                                           (ruler_x - 45, marker_y + 4),
                                           font, 0.4, (0, 165, 255), 1)
                                break  # 첫 번째 사람만 표시

                    # "추정" 레이블 (정확하지 않음을 표시)
                    cv2.putText(display_frame, "Est.", (ruler_x - 5, ruler_y_start - 10),
                               font, 0.35, (128, 128, 128), 1)

                except Exception as e:
                    if self.mirror_frame_count % 60 == 0:
                        print(f"거울보기: 최소 인식 영역 표시 오류: {e}")

                # 6) 표시용으로 RGB 변환
                try:
                    frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                except Exception as e:
                    if self.mirror_frame_count % 30 == 0:
                        print(f"거울보기: 색상 변환 오류: {e}")
                    frame_rgb = display_frame

                # 라벨 크기에 맞춰 리사이즈 및 표시
                try:
                    # 라벨이 유효한지 다시 확인 (pyimage 오류 방지)
                    if self.mirror_camera_label and self.mirror_mode_active:
                        try:
                            if not self.mirror_camera_label.winfo_exists():
                                return
                        except Exception:
                            return

                        # 고정 크기 사용 (줌 현상 방지)
                        # 처음에 크기를 결정하고 이후에는 유지
                        if not hasattr(self, '_fixed_display_size') or self._fixed_display_size is None:
                            self.mirror_camera_label.update_idletasks()
                            label_width = self.mirror_camera_label.winfo_width()
                            label_height = self.mirror_camera_label.winfo_height()

                            # 라벨 크기가 아직 결정되지 않았으면 기본값 사용
                            if label_width <= 1 or label_height <= 1:
                                try:
                                    parent_width = self.winfo_width()
                                    parent_height = self.winfo_height()
                                    if parent_width > 1 and parent_height > 1:
                                        label_width = parent_width - 24  # 패딩 고려
                                        label_height = parent_height - 24
                                    else:
                                        label_width = 1280
                                        label_height = 720
                                except:
                                    label_width = 1280
                                    label_height = 720

                            # 크기 고정 (이후 변경 안 됨)
                            self._fixed_display_size = (label_width, label_height)
                            print(f"[거울보기] 표시 크기 고정: {label_width}x{label_height}")

                        label_width, label_height = self._fixed_display_size

                        # 비율 유지하면서 리사이즈
                        img = Image.fromarray(frame_rgb)
                        img.thumbnail((label_width, label_height), Image.LANCZOS)

                        photo = ImageTk.PhotoImage(image=img)

                        # 이미지 설정 전 다시 확인
                        if self.mirror_camera_label and self.mirror_mode_active:
                            try:
                                if self.mirror_camera_label.winfo_exists():
                                    self.mirror_camera_label.configure(image=photo, text="")
                                    self.mirror_camera_label.image = photo  # 참조 유지
                            except Exception:
                                pass
                except Exception as e:
                    if self.mirror_frame_count % 30 == 0:  # 오류 메시지 스팸 방지
                        print(f"거울보기: 이미지 표시 오류: {e}")

                # 실시간 설정 패널 FPS/감지 수 업데이트 (매 프레임)
                try:
                    if hasattr(self, '_rt_fps_label') and self._rt_fps_label:
                        # 감지 수 계산
                        detection_count = 0
                        if self._detected_objects_cache:
                            detection_count += len(self._detected_objects_cache)
                        if self._ppe_detections_cache:
                            detection_count += len(self._ppe_detections_cache)

                        # FPS 및 감지 수 표시 업데이트
                        fps = getattr(self, '_current_fps', 0.0)
                        self._update_realtime_fps_display(fps, detection_count)
                except Exception:
                    pass

                # 다음 프레임 업데이트 (약 33ms마다, 30fps)
                self.after(33, self._update_mirror_frame)
            else:
                # 프레임 읽기 실패 시 재시도
                self.after(100, self._update_mirror_frame)
        except Exception as e:
            print(f"거울보기 프레임 업데이트 오류: {e}")
            # 오류 발생 시 약간 늦춰서 재시도
            self.after(100, self._update_mirror_frame)
    
    def _draw_flipped_detections(self, frame, detections, frame_width):
        """좌우 반전된 프레임에 PPE 바운딩 박스 그리기 (좌표 변환)

        주의: 얼굴 박스는 별도의 _draw_face_boxes_flipped()에서 처리
        """
        import cv2

        # PPEVisualizer 색상 사용
        colors = {
            'person': (255, 128, 0),
            'helmet': (0, 255, 0),
            'glasses': (0, 255, 255),
            'mask': (255, 0, 255),
            'gloves': (0, 165, 255),
            'vest': (0, 255, 128),
            'boots': (128, 0, 255),
        }

        for i, detection in enumerate(detections):
            bbox = detection.bbox

            # 좌우 반전 좌표 계산
            flipped_x1 = frame_width - bbox.x2
            flipped_x2 = frame_width - bbox.x1

            # 사람 박스 그리기
            cv2.rectangle(frame, (flipped_x1, bbox.y1), (flipped_x2, bbox.y2),
                         colors['person'], 2)

            # 사람 레이블 (번호만)
            label = f"사람 {i+1}"

            # 한글 레이블 표시
            if self.ppe_visualizer:
                frame = self.ppe_visualizer.put_korean_text(
                    frame, label, (flipped_x1, bbox.y1 - 25), colors['person'], 16
                )
            else:
                cv2.putText(frame, label, (flipped_x1, bbox.y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['person'], 2)

        return frame

    def _draw_face_boxes_flipped(self, frame, face_results, frame_width):
        """좌우 반전된 프레임에 얼굴 박스 그리기 (기존 safety_detector 스타일)

        녹색 박스 + 한글 이름 표시 (소속/사원번호/신뢰도 포함)
        """
        import cv2

        if not face_results:
            return frame

        recognized = face_results.get('recognized_faces', [])

        for face_info in recognized:
            bbox = face_info.get('location', [])
            if len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(x) for x in bbox]

            # 좌우 반전 좌표 계산
            flipped_x1 = frame_width - x2
            flipped_x2 = frame_width - x1

            # 녹색 얼굴 박스 그리기
            cv2.rectangle(frame, (flipped_x1, y1), (flipped_x2, y2), (0, 255, 0), 3)

            # 이름 및 정보 표시 (한글 지원)
            name = face_info.get('name', 'Unknown')
            if name and name != 'Unknown':
                employee_id = face_info.get('employee_id', '')
                department = face_info.get('department', '')
                confidence = face_info.get('confidence', 0.0)

                text = f"{name}"
                # 소속(department) 또는 사원번호(employee_id) 표시
                if department:
                    text += f" ({department})"
                elif employee_id:
                    text += f" ({employee_id})"
                text += f" [{int(confidence * 100)}%]"

                # 한글 지원 텍스트 출력
                if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                    frame = self.safety_detector._put_korean_text(frame, text, (flipped_x1, y1 - 30), (0, 255, 0), 20)
                elif self.ppe_visualizer:
                    frame = self.ppe_visualizer.put_korean_text(frame, text, (flipped_x1, y1 - 30), (0, 255, 0), 18)
                else:
                    cv2.putText(frame, name, (flipped_x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return frame

    def _draw_face_boxes(self, frame, face_results):
        """원본 프레임에 얼굴 박스 그리기 (기존 safety_detector 스타일)

        녹색 박스 + 한글 이름 표시 (소속/사원번호/신뢰도 포함)
        """
        import cv2

        if not face_results:
            return frame

        recognized = face_results.get('recognized_faces', [])

        for face_info in recognized:
            bbox = face_info.get('location', [])
            if len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(x) for x in bbox]

            # 녹색 얼굴 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # 이름 및 정보 표시 (한글 지원)
            name = face_info.get('name', 'Unknown')
            if name and name != 'Unknown':
                employee_id = face_info.get('employee_id', '')
                department = face_info.get('department', '')
                confidence = face_info.get('confidence', 0.0)

                text = f"{name}"
                # 소속(department) 또는 사원번호(employee_id) 표시
                if department:
                    text += f" ({department})"
                elif employee_id:
                    text += f" ({employee_id})"
                text += f" [{int(confidence * 100)}%]"

                # 한글 지원 텍스트 출력
                if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                    frame = self.safety_detector._put_korean_text(frame, text, (x1, y1 - 30), (0, 255, 0), 20)
                elif self.ppe_visualizer:
                    frame = self.ppe_visualizer.put_korean_text(frame, text, (x1, y1 - 30), (0, 255, 0), 18)
                else:
                    cv2.putText(frame, name, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return frame

    def _draw_detected_objects_boxes(self, frame, detected_objects, flipped=False):
        """
        감지된 사물의 바운딩 박스를 카메라 화면에 그리기

        Args:
            frame: 입력 프레임 (BGR)
            detected_objects: 감지된 사물 리스트 [{'class': str, 'class_kr': str, 'confidence': float, 'bbox': [x1,y1,x2,y2]}, ...]
            flipped: 좌우 반전 여부 (거울 모드)

        Returns:
            frame: 바운딩 박스가 그려진 프레임
        """
        import cv2

        if not detected_objects:
            return frame

        frame_width = frame.shape[1]

        # 카테고리별 색상 정의 (BGR)
        category_colors = {
            # 동물 - 주황색
            'bird': (0, 165, 255), 'cat': (0, 165, 255), 'dog': (0, 165, 255),
            'horse': (0, 165, 255), 'sheep': (0, 165, 255), 'cow': (0, 165, 255),
            'elephant': (0, 165, 255), 'bear': (0, 165, 255), 'zebra': (0, 165, 255),
            'giraffe': (0, 165, 255),
            # 차량 - 파란색
            'bicycle': (255, 100, 0), 'car': (255, 100, 0), 'motorcycle': (255, 100, 0),
            'airplane': (255, 100, 0), 'bus': (255, 100, 0), 'train': (255, 100, 0),
            'truck': (255, 100, 0), 'boat': (255, 100, 0),
            # 가구 - 보라색
            'chair': (200, 0, 200), 'couch': (200, 0, 200), 'bed': (200, 0, 200),
            'dining table': (200, 0, 200), 'toilet': (200, 0, 200),
            # 전자기기 - 청록색
            'tv': (255, 255, 0), 'laptop': (255, 255, 0), 'cell phone': (255, 255, 0),
            'keyboard': (255, 255, 0), 'mouse': (255, 255, 0), 'remote': (255, 255, 0),
            # 음식 - 연두색
            'banana': (0, 255, 128), 'apple': (0, 255, 128), 'sandwich': (0, 255, 128),
            'orange': (0, 255, 128), 'pizza': (0, 255, 128), 'donut': (0, 255, 128),
            'cake': (0, 255, 128),
            # 스포츠 - 노란색
            'sports ball': (0, 255, 255), 'baseball bat': (0, 255, 255),
            'tennis racket': (0, 255, 255), 'skateboard': (0, 255, 255),
            'surfboard': (0, 255, 255), 'frisbee': (0, 255, 255),
            # 액세서리 - 핑크색
            'backpack': (180, 105, 255), 'umbrella': (180, 105, 255),
            'handbag': (180, 105, 255), 'suitcase': (180, 105, 255), 'tie': (180, 105, 255),
            # 주방용품 - 하늘색
            'bottle': (255, 200, 100), 'cup': (255, 200, 100), 'fork': (255, 200, 100),
            'knife': (255, 200, 100), 'spoon': (255, 200, 100), 'bowl': (255, 200, 100),
        }
        default_color = (128, 128, 128)  # 기본 회색

        for obj in detected_objects:
            bbox = obj.get('bbox', [])
            if len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(x) for x in bbox]

            # 거울 모드면 좌표 반전
            if flipped:
                x1_new = frame_width - x2
                x2_new = frame_width - x1
                x1, x2 = x1_new, x2_new

            class_name = obj.get('class', '')
            class_kr = obj.get('class_kr', class_name)
            confidence = obj.get('confidence', 0.0)

            # 카테고리별 색상
            color = category_colors.get(class_name, default_color)

            # 바운딩 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 라벨 배경
            label = f"{class_kr} {int(confidence * 100)}%"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            label_y = max(y1 - 10, label_size[1] + 5)

            cv2.rectangle(frame, (x1, label_y - label_size[1] - 5),
                         (x1 + label_size[0] + 10, label_y + 5), color, -1)

            # 한글 텍스트 출력
            if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                frame = self.safety_detector._put_korean_text(
                    frame, label, (x1 + 5, label_y - label_size[1]), (255, 255, 255), 16
                )
            elif self.ppe_visualizer and hasattr(self.ppe_visualizer, 'put_korean_text'):
                frame = self.ppe_visualizer.put_korean_text(
                    frame, label, (x1 + 5, label_y - label_size[1]), (255, 255, 255), 14
                )
            else:
                cv2.putText(frame, label, (x1 + 5, label_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def _draw_detected_objects_list(self, frame, detected_objects, position='right'):
        """
        감지된 사물 목록 + 인식 가능 카테고리를 프레임 오른쪽에 표시

        Args:
            frame: 입력 프레임 (BGR)
            detected_objects: 감지된 사물 리스트 [{'class_kr': str, 'confidence': float}, ...]
            position: 표시 위치 ('right' = 오른쪽)

        Returns:
            frame: 오버레이가 추가된 프레임
        """
        import cv2

        h, w = frame.shape[:2]

        # 인식 가능 카테고리 정의
        category_info = [
            ("animals", "동물", "새,고양이,개,말,양,소,코끼리,곰,얼룩말,기린"),
            ("vehicles", "탈것", "자전거,자동차,오토바이,비행기,버스,기차,트럭,보트"),
            ("furniture", "가구", "의자,소파,침대,식탁,변기"),
            ("electronics", "전자기기", "TV,노트북,휴대폰,키보드,마우스,리모컨"),
            ("food", "음식", "바나나,사과,샌드위치,오렌지,피자,도넛,케이크"),
            ("sports", "스포츠", "공,야구배트,테니스라켓,스케이트보드,서핑보드"),
            ("accessories", "소지품", "백팩,우산,핸드백,여행가방,넥타이"),
            ("kitchen", "주방", "병,컵,포크,나이프,숟가락,그릇"),
        ]

        # 활성화된 카테고리 확인
        enabled_categories = []
        try:
            for key, label, items in category_info:
                if bool(self.app.cfg.env.get(f'object_{key}_enabled', True)):
                    enabled_categories.append((label, items))
        except Exception:
            enabled_categories = [(label, items) for _, label, items in category_info]

        # 중복 제거 및 신뢰도 순 정렬 (감지된 사물)
        unique_objects = {}
        if detected_objects:
            for obj in detected_objects:
                class_kr = obj.get('class_kr', obj.get('class', 'Unknown'))
                conf = obj.get('confidence', 0.0)
                if class_kr not in unique_objects or unique_objects[class_kr] < conf:
                    unique_objects[class_kr] = conf

        sorted_objects = sorted(unique_objects.items(), key=lambda x: x[1], reverse=True)[:5]

        # 박스 크기 계산
        box_width = 240
        line_height_detect = 20
        line_height_cat = 15
        padding = 6

        # 감지된 사물 영역 높이
        detect_height = 0
        if sorted_objects:
            detect_height = len(sorted_objects) * line_height_detect + 25

        # 카테고리 영역 높이
        cat_height = len(enabled_categories) * line_height_cat + 22

        box_height = detect_height + cat_height + padding * 2

        # 박스 위치 (오른쪽 상단)
        box_x = w - box_width - 8
        box_y = 95

        # 검정 배경 박스
        overlay = frame.copy()
        cv2.rectangle(overlay, (box_x, box_y), (box_x + box_width, box_y + box_height),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # 테두리
        cv2.rectangle(frame, (box_x, box_y), (box_x + box_width, box_y + box_height),
                     (60, 60, 60), 1)

        y_offset = box_y + padding

        # === 감지된 사물 표시 ===
        if sorted_objects:
            title = "■ 감지된 사물"
            if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                frame = self.safety_detector._put_korean_text(
                    frame, title, (box_x + 6, y_offset), (0, 255, 255), 12
                )
            elif self.ppe_visualizer:
                frame = self.ppe_visualizer.put_korean_text(
                    frame, title, (box_x + 6, y_offset), (0, 255, 255), 12
                )
            y_offset += 18

            for class_kr, confidence in sorted_objects:
                if confidence >= 0.7:
                    color = (0, 255, 0)
                elif confidence >= 0.5:
                    color = (0, 255, 255)
                else:
                    color = (0, 200, 255)

                text = f"  • {class_kr} ({int(confidence * 100)}%)"
                if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                    frame = self.safety_detector._put_korean_text(
                        frame, text, (box_x + 6, y_offset), color, 11
                    )
                elif self.ppe_visualizer:
                    frame = self.ppe_visualizer.put_korean_text(
                        frame, text, (box_x + 6, y_offset), color, 11
                    )
                y_offset += line_height_detect

            # 구분선
            y_offset += 2
            cv2.line(frame, (box_x + 6, y_offset), (box_x + box_width - 6, y_offset),
                    (50, 50, 50), 1)
            y_offset += 6

        # === 인식 가능 카테고리 표시 (흰색 폰트) ===
        title2 = "■ 인식 가능 항목"
        if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
            frame = self.safety_detector._put_korean_text(
                frame, title2, (box_x + 6, y_offset), (255, 255, 255), 11
            )
        elif self.ppe_visualizer:
            frame = self.ppe_visualizer.put_korean_text(
                frame, title2, (box_x + 6, y_offset), (255, 255, 255), 11
            )
        y_offset += 16

        for cat_label, cat_items in enabled_categories:
            # 카테고리명과 항목들 (축약)
            items_short = cat_items[:22] + ".." if len(cat_items) > 22 else cat_items
            text = f"{cat_label}: {items_short}"

            if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                frame = self.safety_detector._put_korean_text(
                    frame, text, (box_x + 8, y_offset), (200, 200, 200), 9
                )
            elif self.ppe_visualizer:
                frame = self.ppe_visualizer.put_korean_text(
                    frame, text, (box_x + 8, y_offset), (200, 200, 200), 9
                )
            y_offset += line_height_cat

        return frame

    def _update_object_panel(self):
        """
        거울보기 오른쪽 사물 인식 패널 업데이트 (Tkinter Label 사용)
        검정 배경에 흰색 폰트로 카테고리별 인식 가능 항목 표시
        폰트 크기 2배 증가 (11->22, 10->20, 9->18, 8->16)
        """
        if not hasattr(self, 'mirror_object_panel') or self.mirror_object_panel is None:
            return

        # 기존 위젯 제거
        for widget in self.mirror_object_panel.winfo_children():
            widget.destroy()

        # 인식 가능 카테고리 정의
        category_info = [
            ("animals", "동물", "새,고양이,개,말,양,소,코끼리,곰,얼룩말,기린"),
            ("vehicles", "탈것", "자전거,자동차,오토바이,비행기,버스,기차,트럭,보트"),
            ("furniture", "가구", "의자,소파,침대,식탁,변기"),
            ("electronics", "전자기기", "TV,노트북,휴대폰,키보드,마우스,리모컨"),
            ("food", "음식", "바나나,사과,샌드위치,오렌지,피자,도넛,케이크"),
            ("sports", "스포츠", "공,야구배트,테니스라켓,스케이트보드,서핑보드"),
            ("accessories", "소지품", "백팩,우산,핸드백,여행가방,넥타이"),
            ("kitchen", "주방", "병,컵,포크,나이프,숟가락,그릇"),
        ]

        # 활성화된 카테고리 확인
        enabled_categories = []
        try:
            for key, label, items in category_info:
                if bool(self.app.cfg.env.get(f'object_{key}_enabled', True)):
                    enabled_categories.append((label, items))
        except Exception:
            enabled_categories = [(label, items) for _, label, items in category_info]

        # 제목 (폰트 30% 축소: 22 -> 15)
        title_label = tk.Label(
            self.mirror_object_panel,
            text="■ 사물 인식",
            font=("Pretendard", 15, "bold"),
            bg="#000000", fg="#00FFFF",
            anchor="w"
        )
        title_label.pack(fill="x", padx=8, pady=(10, 6))

        # 감지된 사물 표시 영역
        detected_frame = tk.Frame(self.mirror_object_panel, bg="#000000")
        detected_frame.pack(fill="x", padx=8)

        # 감지된 사물 레이블 (폰트 30% 축소: 18 -> 13)
        self.detected_objects_label = tk.Label(
            detected_frame,
            text="(감지 대기중...)",
            font=("Pretendard", 13),
            bg="#000000", fg="#888888",
            anchor="w", justify="left"
        )
        self.detected_objects_label.pack(fill="x")

        # 구분선
        sep = tk.Frame(self.mirror_object_panel, bg="#333333", height=1)
        sep.pack(fill="x", padx=8, pady=8)

        # 인식 가능 항목 제목 (폰트 30% 축소: 20 -> 14)
        avail_title = tk.Label(
            self.mirror_object_panel,
            text="■ 인식 가능 항목",
            font=("Pretendard", 14, "bold"),
            bg="#000000", fg="#FFFFFF",
            anchor="w"
        )
        avail_title.pack(fill="x", padx=8, pady=(0, 5))

        # 카테고리별 항목 표시
        for cat_label, cat_items in enabled_categories:
            # 카테고리명 (폰트 30% 축소: 18 -> 13)
            cat_name_label = tk.Label(
                self.mirror_object_panel,
                text=f"▸ {cat_label}",
                font=("Pretendard", 13, "bold"),
                bg="#000000", fg="#AAAAAA",
                anchor="w"
            )
            cat_name_label.pack(fill="x", padx=10, pady=(3, 0))

            # 항목들 (폰트 30% 축소: 16 -> 11, wraplength 축소)
            items_label = tk.Label(
                self.mirror_object_panel,
                text=f"  {cat_items}",
                font=("Pretendard", 11),
                bg="#000000", fg="#777777",
                anchor="w", justify="left",
                wraplength=260
            )
            items_label.pack(fill="x", padx=10)

    def _update_ppe_panel(self):
        """
        거울보기 왼쪽 안전장구 패널 업데이트 (Tkinter Label 사용)
        검정 배경에 흰색 폰트로 PPE 상태 표시
        착용: 녹색, 미착용: 빨간색
        각 장구별 아이콘 표시
        """
        if not hasattr(self, 'mirror_ppe_panel') or self.mirror_ppe_panel is None:
            return

        # 기존 위젯 제거
        for widget in self.mirror_ppe_panel.winfo_children():
            widget.destroy()

        # PPE 항목 정의 (키, 한글명, 아이콘)
        ppe_items = [
            ("helmet", "안전모", "⛑"),      # 헬멧
            ("vest", "조끼", "🦺"),          # 안전조끼
            ("glasses", "보안경", "🥽"),     # 고글
            ("gloves", "장갑", "🧤"),        # 장갑
            ("mask", "마스크", "😷"),        # 마스크
            ("boots", "안전화", "👢"),       # 부츠
        ]

        # 활성화된 PPE 항목 확인
        enabled_items = []
        try:
            for key, label, icon in ppe_items:
                if bool(self.app.cfg.env.get(f'ppe_{key}_enabled', True)):
                    enabled_items.append((key, label, icon))
        except Exception:
            enabled_items = ppe_items

        # 제목
        title_label = tk.Label(
            self.mirror_ppe_panel,
            text="🛡 안전장구",
            font=("Pretendard", 18, "bold"),
            bg="#000000", fg="#00FFFF",
            anchor="w"
        )
        title_label.pack(fill="x", padx=8, pady=(12, 8))

        # PPE 상태 레이블들을 저장 (업데이트용)
        self._ppe_status_labels = {}
        self._ppe_icons = {}  # 아이콘 저장

        # 각 PPE 항목 표시
        for key, label, icon in enabled_items:
            item_frame = tk.Frame(self.mirror_ppe_panel, bg="#000000")
            item_frame.pack(fill="x", padx=8, pady=4)

            # 아이콘 레이블
            icon_label = tk.Label(
                item_frame,
                text=icon,
                font=("Segoe UI Emoji", 20),
                bg="#000000", fg="#888888",
                width=2
            )
            icon_label.pack(side="left")

            # 상태 레이블
            status_label = tk.Label(
                item_frame,
                text=f" {label}",
                font=("Pretendard", 15),
                bg="#000000", fg="#888888",
                anchor="w"
            )
            status_label.pack(side="left", fill="x")

            # 레이블 저장 (나중에 업데이트)
            self._ppe_status_labels[key] = status_label
            self._ppe_icons[key] = icon_label

        # 구분선
        sep = tk.Frame(self.mirror_ppe_panel, bg="#333333", height=2)
        sep.pack(fill="x", padx=8, pady=12)

        # 안전률 표시
        self._ppe_safety_rate_label = tk.Label(
            self.mirror_ppe_panel,
            text="📊 안전률: --%",
            font=("Pretendard", 16, "bold"),
            bg="#000000", fg="#FFFFFF",
            anchor="w"
        )
        self._ppe_safety_rate_label.pack(fill="x", padx=8, pady=(0, 8))

    def _update_ppe_status_display(self):
        """PPE 상태 표시 업데이트 (주기적으로 호출) - 아이콘 색상도 함께 변경"""
        if not hasattr(self, '_ppe_status_labels') or not self._ppe_status_labels:
            return

        if not self.mirror_mode_active:
            return

        try:
            # PPE 상태 캐시에서 정보 가져오기
            ppe_status = self._ppe_status_cache

            # PPE 항목 정의
            ppe_items = {
                "helmet": "안전모",
                "vest": "조끼",
                "glasses": "보안경",
                "gloves": "장갑",
                "mask": "마스크",
                "boots": "안전화",
            }

            wearing_count = 0
            total_enabled = 0

            for key, label in ppe_items.items():
                if key not in self._ppe_status_labels:
                    continue

                status_label = self._ppe_status_labels[key]
                icon_label = self._ppe_icons.get(key) if hasattr(self, '_ppe_icons') else None
                total_enabled += 1

                # PPE 상태 확인
                is_wearing = False
                extra_info = ""
                if ppe_status is not None:
                    is_wearing = getattr(ppe_status, key, False)

                    # 헬멧 색상 표시
                    if key == "helmet" and is_wearing:
                        helmet_color = getattr(ppe_status, 'helmet_color_kr', '') or getattr(ppe_status, 'helmet_color', '')
                        if helmet_color:
                            extra_info = f" ({helmet_color})"

                    # 조끼 색상 표시
                    elif key == "vest" and is_wearing:
                        vest_color = getattr(ppe_status, 'vest_color_kr', '') or getattr(ppe_status, 'vest_color', '')
                        if vest_color:
                            extra_info = f" ({vest_color})"

                    # 장갑 개수 표시
                    elif key == "gloves" and is_wearing:
                        gloves_count = getattr(ppe_status, 'gloves_count', 0)
                        if gloves_count == 1:
                            extra_info = " (1개)"
                        elif gloves_count >= 2:
                            extra_info = " (양손)"

                if is_wearing:
                    wearing_count += 1
                    # 착용: 녹색 (추가 정보 포함)
                    status_label.configure(
                        text=f" {label}{extra_info} ✓",
                        fg="#00FF00"
                    )
                    if icon_label:
                        icon_label.configure(fg="#00FF00")
                else:
                    # 미착용: 빨간색
                    status_label.configure(
                        text=f" {label} ✗",
                        fg="#FF4444"
                    )
                    if icon_label:
                        icon_label.configure(fg="#FF4444")

            # 안전률 업데이트
            if hasattr(self, '_ppe_safety_rate_label') and self._ppe_safety_rate_label:
                if total_enabled > 0:
                    rate = (wearing_count / total_enabled) * 100
                    if rate >= 100:
                        color = "#00FF00"  # 녹색
                    elif rate >= 50:
                        color = "#FFAA00"  # 주황색
                    else:
                        color = "#FF4444"  # 빨간색
                    self._ppe_safety_rate_label.configure(
                        text=f"📊 안전률: {rate:.0f}%",
                        fg=color
                    )
                else:
                    self._ppe_safety_rate_label.configure(
                        text="📊 안전률: --%",
                        fg="#FFFFFF"
                    )
        except Exception:
            pass

    def _update_detected_objects_display(self):
        """감지된 사물 표시 업데이트 (주기적으로 호출)"""
        if not hasattr(self, 'detected_objects_label') or self.detected_objects_label is None:
            return

        if not self.mirror_mode_active:
            return

        try:
            if self._detected_objects_cache:
                # 중복 제거 및 정렬
                unique_objects = {}
                for obj in self._detected_objects_cache:
                    class_kr = obj.get('class_kr', obj.get('class', 'Unknown'))
                    conf = obj.get('confidence', 0.0)
                    if class_kr not in unique_objects or unique_objects[class_kr] < conf:
                        unique_objects[class_kr] = conf

                sorted_objects = sorted(unique_objects.items(), key=lambda x: x[1], reverse=True)[:5]

                if sorted_objects:
                    text_lines = []
                    for class_kr, conf in sorted_objects:
                        text_lines.append(f"• {class_kr} ({int(conf * 100)}%)")
                    self.detected_objects_label.configure(
                        text="\n".join(text_lines),
                        fg="#00FF00"
                    )
                else:
                    self.detected_objects_label.configure(
                        text="(감지된 사물 없음)",
                        fg="#888888"
                    )
            else:
                self.detected_objects_label.configure(
                    text="(감지된 사물 없음)",
                    fg="#888888"
                )
        except Exception:
            pass

    def _calculate_iou(self, box1, box2):
        """두 바운딩 박스의 IoU (Intersection over Union) 계산"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        # 교집합 영역
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    def _calculate_center_distance(self, box1, box2):
        """두 바운딩 박스 중심점 사이의 유클리드 거리 계산"""
        import math
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        cx1, cy1 = (x1_1 + x2_1) // 2, (y1_1 + y2_1) // 2
        cx2, cy2 = (x1_2 + x2_2) // 2, (y1_2 + y2_2) // 2

        return math.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)

    def _update_person_tracking(self, detections, face_results):
        """사람 바운딩 박스와 얼굴을 매칭하여 ID 추적 업데이트

        강화된 추적 로직:
        1. IoU 기반 매칭 (기본)
        2. 중심점 거리 기반 매칭 (IoU 실패 시 fallback)
        3. 이름이 있는 추적은 영구 유지 (타임아웃 없음)
        """
        import time
        current_time = time.time()

        # 타임아웃 처리: None이면 영구 추적 (이름이 있는 추적은 절대 제거 안 함)
        # 이름이 없는 추적만 일정 시간 후 제거 (화면에서 사라진 사람)
        if self._track_timeout is not None:
            expired_ids = []
            for track_id, info in self._tracked_persons.items():
                # 이름이 있는 추적은 절대 만료되지 않음
                if info.get('name'):
                    continue
                elapsed = current_time - info['last_seen']
                if elapsed > self._track_timeout:
                    expired_ids.append(track_id)

            for track_id in expired_ids:
                del self._tracked_persons[track_id]
        # _track_timeout이 None이면 타임아웃 처리 없음 (영구 추적)

        recognized = face_results.get('recognized_faces', [])
        faces = face_results.get('faces', [])

        # 이미 매칭된 추적 ID 기록 (중복 매칭 방지)
        used_track_ids = set()

        # 인식된 얼굴을 사람 바운딩 박스와 매칭
        for det in detections:
            person_bbox = (det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2)
            person_center = ((det.bbox.x1 + det.bbox.x2) // 2, (det.bbox.y1 + det.bbox.y2) // 2)
            matched_name = None
            matched_confidence = 0.0

            # 얼굴이 사람 박스 안에 있는지 확인
            for i, face_bbox in enumerate(faces):
                if len(face_bbox) >= 4:
                    fx1, fy1, fx2, fy2 = int(face_bbox[0]), int(face_bbox[1]), int(face_bbox[2]), int(face_bbox[3])
                    face_center_x = (fx1 + fx2) // 2
                    face_center_y = (fy1 + fy2) // 2

                    # 얼굴 중심이 사람 박스 안에 있는지 확인
                    if (det.bbox.x1 <= face_center_x <= det.bbox.x2 and
                        det.bbox.y1 <= face_center_y <= det.bbox.y2):
                        # 인식된 이름 찾기
                        if i < len(recognized):
                            rec = recognized[i]
                            name = rec.get('name', '')
                            conf = rec.get('confidence', 0.0)
                            if name and name != 'Unknown':
                                matched_name = name
                                matched_confidence = conf
                                break

            # 1단계: IoU 기반 매칭
            best_track_id = None
            best_score = 0.0
            best_match_type = None

            for track_id, track_info in self._tracked_persons.items():
                if track_id in used_track_ids:
                    continue

                iou = self._calculate_iou(person_bbox, track_info['bbox'])
                if iou > self._track_iou_threshold and iou > best_score:
                    best_score = iou
                    best_track_id = track_id
                    best_match_type = 'iou'

            # 2단계: IoU 매칭 실패 시 중심점 거리 기반 매칭
            if best_track_id is None:
                min_distance = self._track_center_dist_threshold
                for track_id, track_info in self._tracked_persons.items():
                    if track_id in used_track_ids:
                        continue

                    distance = self._calculate_center_distance(person_bbox, track_info['bbox'])

                    # 이름이 있는 추적은 거리 임계값을 훨씬 더 크게 (마스크 쓰면서 움직일 수 있음)
                    threshold = self._track_center_dist_threshold
                    if track_info.get('name'):
                        threshold *= 2.5  # 이름이 있으면 200픽셀 * 2.5 = 500픽셀까지 허용 (화면 절반)

                    if distance < threshold and distance < min_distance:
                        min_distance = distance
                        best_track_id = track_id
                        best_match_type = 'center'

            if best_track_id is not None:
                # 기존 추적 업데이트
                used_track_ids.add(best_track_id)
                track_info = self._tracked_persons[best_track_id]
                track_info['bbox'] = person_bbox
                track_info['center'] = person_center
                track_info['last_seen'] = current_time

                # 얼굴이 인식되면 이름 업데이트 (더 높은 confidence로)
                if matched_name:
                    # 기존 이름이 없거나, 새 인식의 confidence가 더 높으면 업데이트
                    if not track_info.get('name') or matched_confidence > track_info.get('confidence', 0):
                        track_info['name'] = matched_name
                        track_info['confidence'] = matched_confidence

                # 추적 정보를 detection에 저장
                det.track_id = best_track_id
                if track_info.get('name'):
                    det.face_name = track_info['name']
                    det.face_detected = True
            else:
                # 새 추적 생성
                new_track_id = self._next_track_id
                self._next_track_id += 1

                self._tracked_persons[new_track_id] = {
                    'name': matched_name or '',
                    'bbox': person_bbox,
                    'center': person_center,
                    'last_seen': current_time,
                    'confidence': matched_confidence
                }
                det.track_id = new_track_id
                if matched_name:
                    det.face_name = matched_name
                    det.face_detected = True

    def _get_tracked_name_for_detection(self, detection):
        """detection에 매칭되는 추적 ID의 이름 반환"""
        if not hasattr(detection, 'track_id'):
            return None

        track_id = detection.track_id
        if track_id in self._tracked_persons:
            return self._tracked_persons[track_id].get('name', '')
        return None

    def _restart_mirror_camera(self):
        """거울보기 카메라 재시작"""
        if not self.mirror_mode_active:
            return
        try:
            if self.mirror_camera:
                self.mirror_camera.release()
                self.mirror_camera = None

            # 카메라 전환 시 감지기 상태 초기화 (IP → USB 전환 문제 해결)
            # safety_detector는 새 카메라와 연결해야 함
            self.safety_detector = None

            # IP 카메라 URL 초기화 (USB 카메라로 전환 시 중요!)
            self._ip_camera_url = None

            # PPEDetector 싱글톤도 리셋 (새 카메라에서 재초기화)
            if PPE_DETECTOR_AVAILABLE and PPEDetector is not None:
                try:
                    PPEDetector.reset_instance()
                    self.ppe_detector = None
                    self.ppe_visualizer = None
                except Exception as e:
                    print(f"[카메라] PPEDetector 리셋 오류: {e}")

            print("[카메라] 카메라 재시작 - 감지기 및 IP URL 초기화됨")

            if self.mirror_camera_label:
                self.mirror_camera_label.configure(text="카메라 재연결 중...", fg="#FFFFFF")
            self.after(500, self._start_mirror_camera)
        except Exception as e:
            print(f"거울보기 카메라 재시작 오류: {e}")

    def _start_ai_thread(self):
        """AI 추론 백그라운드 스레드 시작"""
        import queue
        if self._ai_thread_running:
            return

        self._ai_frame_queue = queue.Queue(maxsize=2)
        self._ai_thread_running = True
        self._ai_thread = threading.Thread(target=self._ai_inference_worker, daemon=True)
        self._ai_thread.start()
        print("[AI Thread] 백그라운드 AI 추론 스레드 시작")

    def _stop_ai_thread(self):
        """AI 추론 백그라운드 스레드 중지"""
        self._ai_thread_running = False
        if self._ai_frame_queue is not None:
            try:
                self._ai_frame_queue.put_nowait(None)  # 종료 신호
            except:
                pass
        self._ai_thread = None
        self._ai_frame_queue = None
        print("[AI Thread] 백그라운드 AI 추론 스레드 중지")

    def _ai_inference_worker(self):
        """AI 추론 백그라운드 워커 스레드"""
        while self._ai_thread_running and self.mirror_mode_active:
            try:
                # 프레임 큐에서 대기 (최대 0.1초, 빠른 반응)
                if self._ai_frame_queue is None:
                    break
                frame = self._ai_frame_queue.get(timeout=0.1)

                if frame is None:  # 종료 신호
                    break

                detection_results = None
                ppe_status = None

                # 디버그 카운터 초기화
                if not hasattr(self, '_ai_debug_count'):
                    self._ai_debug_count = 0
                self._ai_debug_count += 1

                # 성능 설정 확인 (1: 기본, 2: 표준, 3: 고급)
                performance_mode = 2
                try:
                    performance_mode = int(self.app.cfg.env.get('performance_mode', 2))
                    performance_mode = max(1, min(3, performance_mode))
                except Exception:
                    pass

                # PPE 인식 활성화 여부 확인 (성능 모드 2 이상에서만 활성화)
                ppe_detection_enabled = performance_mode >= 2
                try:
                    # 사용자 설정도 함께 확인
                    user_ppe_enabled = bool(self.app.cfg.env.get('ppe_detection_enabled', True))
                    ppe_detection_enabled = ppe_detection_enabled and user_ppe_enabled
                except Exception:
                    pass

                # 새로운 PPE 감지기 사용 (우선) - PPE 인식이 활성화된 경우에만
                if ppe_detection_enabled and self.ppe_detector is not None and self.ppe_detector.is_available():
                    try:
                        # 프레임 유효성 검사 (IP 카메라 호환성)
                        if frame is None or len(frame.shape) < 3:
                            if self._ai_debug_count % 30 == 0:
                                print(f"[AI Thread] 유효하지 않은 프레임: shape={frame.shape if frame is not None else None}")
                            continue

                        # IP 카메라 프레임 형식 변환 (필요시)
                        h, w = frame.shape[:2]
                        if frame.shape[2] == 4:  # RGBA → BGR
                            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

                        # 프레임 크기 검사 및 디버그 (IP 카메라 첫 프레임)
                        if self._ai_debug_count == 1 or (self._ai_debug_count % 100 == 0):
                            is_ip_camera = hasattr(self, '_ip_camera_url') and self._ip_camera_url
                            cam_type = "IP카메라" if is_ip_camera else "웹캠"
                            mode_desc = {1: "기본(얼굴만)", 2: "표준(얼굴+PPE)", 3: "고급(전체)"}
                            print(f"[AI Thread] 성능 모드: {performance_mode} ({mode_desc.get(performance_mode, '알수없음')})")
                            print(f"[AI Thread] {cam_type} 프레임: {w}x{h}, dtype={frame.dtype}, channels={frame.shape[2]}")

                            # 프레임 픽셀 값 확인 (검은 화면 또는 잘못된 데이터 체크)
                            import numpy as np
                            mean_val = np.mean(frame)
                            min_val = np.min(frame)
                            max_val = np.max(frame)
                            print(f"[AI Thread] 프레임 픽셀: mean={mean_val:.1f}, min={min_val}, max={max_val}")

                            # 프레임이 너무 어두우면 경고
                            if mean_val < 10:
                                print(f"[AI Thread] 경고: 프레임이 거의 검은색입니다!")

                            # 디버그 프레임 저장 (AI 스레드에서 받은 프레임)
                            try:
                                debug_path = "/tmp/ai_thread_frame.jpg"
                                cv2.imwrite(debug_path, frame)
                                print(f"[AI Thread] 디버그 프레임 저장: {debug_path}")
                            except Exception as e:
                                print(f"[AI Thread] 디버그 프레임 저장 실패: {e}")

                        # YOLOv10 PPE 감지
                        detections = self.ppe_detector.detect(frame)
                        if detections:
                            ppe_status = detections[0].ppe_status  # 첫 번째 사람의 PPE 상태
                            # 캐시에 저장
                            self._ppe_status_cache = ppe_status
                            self._ppe_detections_cache = detections  # 바운딩 박스용
                            # 감지 성공 시 빈 카운터 리셋
                            self._ppe_empty_count = 0

                            # 왼쪽 PPE 패널 업데이트 (메인 스레드에서)
                            try:
                                self.after(0, self._update_ppe_status_display)
                            except Exception:
                                pass

                            # 디버그 출력 (10프레임마다)
                            if self._ai_debug_count % 10 == 0:
                                print(f"[AI Thread] YOLOv10 PPE: 헬멧={ppe_status.helmet}, 조끼={ppe_status.vest}, 장갑={ppe_status.gloves}({ppe_status.gloves_count}개)")

                            # PPE 상태를 detection_results 형태로 변환 (호환성)
                            detection_results = {
                                'ppe': {
                                    'helmet': ppe_status.helmet,
                                    'helmet_color': ppe_status.helmet_color_kr or ppe_status.helmet_color,
                                    'vest': ppe_status.vest,
                                    'vest_color': ppe_status.vest_color_kr or ppe_status.vest_color,
                                    'mask': ppe_status.mask,
                                    'glasses': ppe_status.glasses,
                                    'gloves': ppe_status.gloves,
                                    'gloves_count': ppe_status.gloves_count,
                                    'boots': ppe_status.boots,
                                },
                                'detections': detections  # 원본 감지 결과도 저장
                            }

                            # 얼굴 인식 (safety_detector에서 기존 DB 사용) - 실시간 최적화
                            if self.safety_detector is not None:
                                try:
                                    # detect_face_only(): 얼굴만 감지 (~30ms)
                                    # detect_all(): PPE + 얼굴 전체 (~1800ms)
                                    face_results = self.safety_detector.detect_face_only(frame)
                                    if face_results and (face_results.get('faces') or face_results.get('recognized_faces')):
                                        # 얼굴 인식 결과 캐시에 저장 (박스 표시용)
                                        self._face_results_cache = face_results
                                        # 얼굴 감지 성공 시 빈 카운터 리셋
                                        self._face_empty_count = 0

                                        # 얼굴 인식 결과 추가
                                        detection_results['faces'] = face_results.get('faces', [])
                                        detection_results['recognized_faces'] = face_results.get('recognized_faces', [])

                                        # ID 추적: 사람 바운딩 박스와 얼굴을 매칭하여 추적
                                        self._update_person_tracking(detections, face_results)

                                        # 감지된 사람에 얼굴 정보 매핑 (추적 ID 기반)
                                        for det in detections:
                                            matched_name = self._get_tracked_name_for_detection(det)
                                            if matched_name:
                                                det.face_detected = True
                                                det.face_name = matched_name
                                    else:
                                        # 얼굴 감지 안 됨 - 연속 10프레임 후 캐시 초기화 (깜빡임 방지)
                                        if not hasattr(self, '_face_empty_count'):
                                            self._face_empty_count = 0
                                        self._face_empty_count += 1
                                        if self._face_empty_count >= 10:
                                            self._face_results_cache = None
                                            self._face_empty_count = 0
                                except Exception as e:
                                    if self._ai_debug_count % 30 == 0:
                                        print(f"[AI Thread] 얼굴 인식 오류: {e}")
                        else:
                            # 감지 결과 없으면 캐시 유지 시간 체크 후 초기화
                            # 연속 5프레임 동안 감지 안되면 캐시 초기화 (깜빡임 방지)
                            if not hasattr(self, '_ppe_empty_count'):
                                self._ppe_empty_count = 0
                            self._ppe_empty_count += 1
                            if self._ppe_empty_count >= 5:
                                self._ppe_detections_cache = None
                                self._ppe_status_cache = None
                                self._ppe_empty_count = 0
                    except Exception as e:
                        if self._ai_debug_count % 30 == 0:
                            print(f"[AI Thread] YOLOv10 PPE 감지 오류: {e}")

                # PPE 비활성화 시 또는 PPE 감지기 없을 때: 얼굴 인식만 수행
                if detection_results is None and self.safety_detector is not None:
                    try:
                        if ppe_detection_enabled:
                            # PPE + 얼굴 전체 감지 (fallback)
                            detection_results = self.safety_detector.detect_all(frame)

                            # PPE 감지 결과 디버그 (10프레임마다)
                            if detection_results and self._ai_debug_count % 10 == 0:
                                helmet = detection_results.get('hard_hat', {}).get('wearing', False)
                                glasses = detection_results.get('safety_glasses', {}).get('wearing', False)
                                print(f"[AI Thread] Fallback PPE 감지: helmet={helmet}, glasses={glasses}")
                        else:
                            # 얼굴 인식만 수행 (PPE 비활성화)
                            face_results = self.safety_detector.detect_face_only(frame)
                            if face_results:
                                self._face_results_cache = face_results
                                detection_results = {
                                    'faces': face_results.get('faces', []),
                                    'recognized_faces': face_results.get('recognized_faces', [])
                                }
                    except Exception as e:
                        print(f"[AI Thread] Fallback 추론 오류: {e}")

                # === 일반 사물 인식 (COCO 클래스) ===
                # 성능 모드 3에서만 사물 인식 활성화
                object_detection_enabled = False
                if performance_mode >= 3:
                    try:
                        object_detection_enabled = bool(self.app.cfg.env.get('object_detection_enabled', True))
                    except Exception:
                        object_detection_enabled = True

                # IP 카메라도 성능 모드 3에서만 사물 인식
                is_ip_camera = getattr(self, '_ip_camera_url', None) is not None

                # 디버그 로그 (30프레임마다)
                if self._ai_debug_count % 30 == 0:
                    print(f"[AI Thread] COCO 감지 상태: enabled={object_detection_enabled}, is_ip={is_ip_camera}, safety_detector={self.safety_detector is not None}")
                    # yolo_person_model 상태 확인
                    if self.safety_detector is not None:
                        yolo_model = getattr(self.safety_detector, 'yolo_person_model', None)
                        if yolo_model is not None:
                            print(f"[AI Thread] COCO 모델: {len(yolo_model.names)}개 클래스")

                if object_detection_enabled and self.safety_detector is not None:
                    try:
                        # 활성화된 카테고리 가져오기
                        enabled_categories = {
                            'animals': bool(self.app.cfg.env.get('object_animals_enabled', True)),
                            'vehicles': bool(self.app.cfg.env.get('object_vehicles_enabled', True)),
                            'furniture': bool(self.app.cfg.env.get('object_furniture_enabled', True)),
                            'electronics': bool(self.app.cfg.env.get('object_electronics_enabled', True)),
                            'food': bool(self.app.cfg.env.get('object_food_enabled', True)),
                            'sports': bool(self.app.cfg.env.get('object_sports_enabled', True)),
                            'accessories': bool(self.app.cfg.env.get('object_accessories_enabled', True)),
                            'kitchen': bool(self.app.cfg.env.get('object_kitchen_enabled', True)),
                        }

                        # COCO 사물 감지 신뢰도 결정 (실시간 설정 우선, 없으면 기본값)
                        # 실시간 설정 패널에서 변경한 값 사용
                        if hasattr(self, '_rt_coco_conf_current'):
                            coco_conf = self._rt_coco_conf_current
                        else:
                            # 기본값: IP 카메라 0.25, USB 0.35 (성능 최적화)
                            coco_conf = 0.25 if is_ip_camera else 0.35
                        detected_objects = self.safety_detector.detect_objects_coco(
                            frame, enabled_categories, confidence_threshold=coco_conf
                        )

                        # 캐시에 저장
                        self._detected_objects_cache = detected_objects

                        # 오른쪽 패널 업데이트 (메인 스레드에서)
                        try:
                            self.after(0, self._update_detected_objects_display)
                        except Exception:
                            pass

                        # 디버그 로그 (30프레임마다)
                        if self._ai_debug_count % 30 == 0:
                            if detected_objects:
                                obj_names = [obj['class_kr'] for obj in detected_objects[:3]]
                                print(f"[AI Thread] 사물 감지: {obj_names} 외 {max(0, len(detected_objects)-3)}개")
                            else:
                                # 감지 결과가 없을 때 상세 로그 출력
                                yolo_model = getattr(self.safety_detector, 'yolo_person_model', None)
                                h, w = frame.shape[:2] if frame is not None else (0, 0)
                                cam_type = "IP" if is_ip_camera else "USB"
                                print(f"[AI Thread] 사물 감지 결과: 0개 ({cam_type}, {w}x{h}, conf={coco_conf}, model={yolo_model is not None})")
                    except Exception as e:
                        if self._ai_debug_count % 30 == 0:
                            print(f"[AI Thread] 사물 감지 오류: {e}")
                else:
                    # 사물 인식 비활성화 시 캐시 초기화
                    self._detected_objects_cache = []

                # 결과 캐싱 (스레드 안전)
                with self._ai_result_lock:
                    self._cached_detection_results = detection_results

                # 인식률 업데이트 (메인 스레드에서 실행해야 함)
                try:
                    self.after(0, lambda: self._update_accuracy_display(detection_results))
                except:
                    pass

            except Exception:
                # 큐 타임아웃 또는 기타 오류
                continue

        print("[AI Thread] 워커 스레드 종료")

    def _update_accuracy_display(self, detection_results):
        """인식률 계산 및 표시 업데이트"""
        try:
            # 인식률 계산
            accuracy = 0.0
            if detection_results:
                # 1) 얼굴 인식 결과 확인 (recognized_faces)
                recognized_faces = detection_results.get('recognized_faces', [])
                if recognized_faces:
                    # 인식된 얼굴의 신뢰도 평균 사용
                    confidences = [face.get('confidence', 0.0) for face in recognized_faces]
                    if confidences:
                        accuracy = sum(confidences) / len(confidences) * 100
                # 2) 얼굴 감지 결과 확인 (faces)
                elif detection_results.get('faces'):
                    faces_count = len(detection_results.get('faces', []))
                    if faces_count > 0:
                        # 얼굴이 감지되었지만 인식되지 않은 경우 기본 신뢰도
                        accuracy = 65.0  # 감지만 된 경우 기본값
                # 3) 안전장구 감지 결과로 계산
                else:
                    # 안전모 감지
                    hard_hat = detection_results.get('hard_hat', {})
                    if hard_hat and hard_hat.get('wearing', False):
                        helmet_conf = hard_hat.get('confidence', 0.0)
                        accuracy = max(accuracy, helmet_conf * 100)

                    # 안전화 감지
                    safety_shoes = detection_results.get('safety_shoes', {})
                    if safety_shoes and safety_shoes.get('wearing', False):
                        shoes_conf = safety_shoes.get('confidence', 0.0)
                        accuracy = max(accuracy, shoes_conf * 100)

            # 이동 평균 적용 (부드러운 변화)
            alpha = 0.3  # 가중치 (0.3 = 30% 새 값, 70% 기존 값)
            self.mirror_normal_accuracy = alpha * accuracy + (1 - alpha) * self.mirror_normal_accuracy

            # UI 업데이트
            if self.mirror_normal_accuracy_label:
                self.mirror_normal_accuracy_label.configure(
                    text=f"인식률: {self.mirror_normal_accuracy:.1f}%"
                )

        except Exception as e:
            if self.mirror_frame_count % 30 == 0:
                print(f"인식률 계산 오류: {e}")

    def _check_camera_availability(self):
        """카메라 사용 가능 여부를 확인 (다른 패널에서 사용 중이면 스킵)"""
        # 다른 패널에서 카메라를 사용 중인지 확인
        try:
            for panel_key, panel in self.app.panels.items():
                if panel_key == self.sid_key:
                    continue
                if hasattr(panel, 'mirror_mode_active') and panel.mirror_mode_active:
                    # 다른 패널에서 거울보기 사용 중 - 카메라 테스트 스킵
                    print(f"[카메라] 다른 패널에서 카메라 사용 중 - 테스트 스킵")
                    # 자기 자신만 업데이트 (전파하지 않음)
                    self.camera_available = True
                    if hasattr(self, 'header') and hasattr(self.header, 'set_mirror_camera_ready'):
                        self.header.set_mirror_camera_ready(True)
                    return
                # 다른 패널에서 카메라가 이미 사용 가능으로 확인된 경우
                if hasattr(panel, 'camera_available') and panel.camera_available:
                    print(f"[카메라] 다른 패널에서 카메라 확인됨 - 테스트 스킵")
                    # 자기 자신만 업데이트 (전파하지 않음 - 이미 다른 패널에서 전파됨)
                    self.camera_available = True
                    if hasattr(self, 'header') and hasattr(self.header, 'set_mirror_camera_ready'):
                        self.header.set_mirror_camera_ready(True)
                    return
        except Exception:
            pass

        def check_camera():
            try:
                import cv2
                import platform
                system = platform.system().lower()

                # 플랫폼별 백엔드 설정
                if system == 'windows':
                    backend = cv2.CAP_DSHOW
                elif system == 'linux':
                    backend = cv2.CAP_V4L2
                else:
                    backend = cv2.CAP_ANY

                # 카메라 사용 가능 여부 확인 (빠른 테스트)
                camera_found = False
                for i in range(3):  # 0~2까지만 빠르게 확인
                    try:
                        test_camera = cv2.VideoCapture(i, backend)

                        if test_camera.isOpened():
                            ret, frame = test_camera.read()
                            if ret and frame is not None:
                                camera_found = True
                                test_camera.release()
                                break
                            test_camera.release()
                    except Exception:
                        continue

                # UI 스레드에서 버튼 상태 업데이트
                self.after(0, lambda found=camera_found: self._update_camera_button_state(found))
            except ImportError:
                # OpenCV가 없으면 카메라 사용 불가
                self.after(0, lambda: self._update_camera_button_state(False))
            except Exception as e:
                print(f"카메라 확인 오류: {e}")
                self.after(0, lambda: self._update_camera_button_state(False))

        # 백그라운드 스레드에서 실행
        threading.Thread(target=check_camera, daemon=True).start()
    
    def _update_camera_button_state(self, camera_available):
        """카메라 버튼 상태 업데이트 및 모든 패널에 전파"""
        # 카메라 가용성 상태 저장
        self.camera_available = camera_available

        if hasattr(self, 'header') and hasattr(self.header, 'set_mirror_camera_ready'):
            self.header.set_mirror_camera_ready(camera_available)

        # 카메라가 사용 가능하면 모든 패널에 상태 전파
        if camera_available and hasattr(self, 'app') and hasattr(self.app, 'panels'):
            try:
                for panel_key, panel in self.app.panels.items():
                    if panel_key == self.sid_key:
                        continue  # 자기 자신은 이미 업데이트됨
                    # 다른 패널의 카메라 상태도 업데이트
                    if hasattr(panel, 'camera_available'):
                        panel.camera_available = True
                    if hasattr(panel, 'header') and hasattr(panel.header, 'set_mirror_camera_ready'):
                        panel.header.set_mirror_camera_ready(True)
            except Exception as e:
                print(f"[카메라] 다른 패널 상태 전파 오류: {e}")
    
    def _stop_mirror_camera(self):
        """거울보기 카메라 중지"""
        try:
            # 먼저 mirror_mode_active를 False로 설정하여 프레임 업데이트 중지
            self.mirror_mode_active = False

            # AI 추론 스레드 중지
            self._stop_ai_thread()

            # PPE 감지기 정리 (새 모듈)
            self.ppe_detector = None
            self.ppe_visualizer = None
            self._ppe_status_cache = None
            self._ppe_detections_cache = None

            # 얼굴 인식 결과 및 추적 데이터 정리
            self._face_results_cache = None
            self._tracked_persons = {}
            self._next_track_id = 1

            # 표시 크기 초기화 (다음 거울보기 시작 시 새로 계산)
            self._fixed_display_size = None

            # 안전장구 감지기 정리 (fallback)
            if self.safety_detector is not None:
                self.safety_detector = None

            # 카메라 라벨 이미지 참조 해제 (pyimage 오류 방지)
            if self.mirror_camera_label is not None:
                try:
                    self.mirror_camera_label.configure(image="", text="")
                    self.mirror_camera_label.image = None
                except Exception:
                    pass

            if self.mirror_camera is not None:
                self.mirror_camera.release()
                self.mirror_camera = None
        except Exception as e:
            print(f"거울보기 카메라 중지 오류: {e}")

    def _get_available_cameras(self):
        """사용 가능한 카메라 목록 검색 (Linux 전용)"""
        try:
            import os
        except ImportError:
            return []

        cameras = []

        # Linux: /dev/video* 장치 검색 (V4L2 정보로 필터링)
        for i in range(10):  # 최대 10개 카메라 검색
            device_path = f"/dev/video{i}"
            if not os.path.exists(device_path):
                continue

            try:
                # V4L2 장치 정보 확인 (캡처 가능 여부)
                # index 파일이 있고 0이면 메인 캡처 장치
                index_path = f"/sys/class/video4linux/video{i}/index"
                if os.path.exists(index_path):
                    with open(index_path, 'r') as f:
                        idx_val = f.read().strip()
                        if idx_val != '0':
                            # 메타데이터 장치는 스킵 (index != 0)
                            continue
                else:
                    # index 파일이 없으면 sysfs 디렉토리 존재 여부로 판단
                    sysfs_path = f"/sys/class/video4linux/video{i}"
                    if not os.path.exists(sysfs_path):
                        continue

                # V4L2 장치 이름 읽기
                name = f"카메라 {i}"
                name_path = f"/sys/class/video4linux/video{i}/name"
                if os.path.exists(name_path):
                    with open(name_path, 'r') as f:
                        device_name = f.read().strip()
                        if device_name:
                            name = f"{device_name} ({i})"

                cameras.append((i, name))
            except Exception:
                continue

        return cameras

    def _get_current_camera_name(self):
        """현재 설정된 카메라 이름 반환"""
        try:
            if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                # IP 카메라 확인
                ip_url = self.app.cfg.camera.get("ip_camera_url", "")
                if ip_url:
                    ip_name = self.app.cfg.camera.get("ip_camera_name", "IP 카메라")
                    return f"🌐 {ip_name}"

                # USB 카메라
                camera_idx = self.app.cfg.camera.get("device_index", 0)
                camera_name = self.app.cfg.camera.get("device_name", "")
                if camera_name:
                    return camera_name
                return f"카메라 {camera_idx}"
        except Exception:
            pass
        return "기본 카메라"

    def _on_camera_selected(self, event=None):
        """카메라 선택 변경 시 호출 (더 이상 사용하지 않음 - 설정-카메라로 이동)"""
        if self.camera_combo is None:
            return

        try:
            selection = self.camera_combo.get()

            # IP 카메라 추가 옵션 선택 시
            if "IP 카메라 추가" in selection:
                self._show_ip_camera_dialog()
                return

            # 선택된 카메라 인덱스 추출
            for idx, name in self.available_cameras:
                if name == selection:
                    if idx != self.selected_camera_index:
                        self.selected_camera_index = idx
                        self._cached_camera_index = idx
                        self._ip_camera_url = None  # USB 카메라 선택 시 IP URL 초기화
                        print(f"[카메라] 카메라 변경: {name} (인덱스 {idx})")
                        # 카메라 재시작
                        self._restart_mirror_camera()
                    break
        except Exception as e:
            print(f"[카메라] 선택 오류: {e}")

    def _show_ip_camera_dialog(self):
        """IP 카메라 URL 입력 다이얼로그 표시"""
        dialog = tk.Toplevel(self)
        dialog.title("IP 카메라 연결")
        dialog.geometry("500x280")
        dialog.resizable(False, False)
        dialog.configure(bg="#2C3E50")

        # 모달 설정
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 500) // 2
        y = (dialog.winfo_screenheight() - 280) // 2
        dialog.geometry(f"500x280+{x}+{y}")

        # 제목
        title_label = tk.Label(
            dialog,
            text="🌐 IP 카메라 연결",
            font=("Pretendard", 16, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF"
        )
        title_label.pack(pady=(20, 10))

        # 설명
        desc_label = tk.Label(
            dialog,
            text="RTSP 또는 HTTP 스트림 URL을 입력하세요",
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#BDC3C7"
        )
        desc_label.pack(pady=(0, 15))

        # URL 입력 프레임
        input_frame = tk.Frame(dialog, bg="#2C3E50")
        input_frame.pack(fill="x", padx=30, pady=5)

        url_label = tk.Label(
            input_frame,
            text="URL:",
            font=("Pretendard", 12),
            bg="#2C3E50",
            fg="#FFFFFF"
        )
        url_label.pack(side="left", padx=(0, 10))

        url_entry = tk.Entry(
            input_frame,
            font=("Pretendard", 11),
            width=40,
            bg="#34495E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF"
        )
        url_entry.pack(side="left", fill="x", expand=True)
        url_entry.insert(0, "rtsp://")

        # 예시 URL
        example_frame = tk.Frame(dialog, bg="#2C3E50")
        example_frame.pack(fill="x", padx=30, pady=(10, 5))

        example_label = tk.Label(
            example_frame,
            text="예시:\n• rtsp://admin:password@192.168.1.100:554/stream1\n• http://192.168.1.100:8080/video",
            font=("Pretendard", 9),
            bg="#2C3E50",
            fg="#7F8C8D",
            justify="left"
        )
        example_label.pack(anchor="w")

        # 버튼 프레임
        btn_frame = tk.Frame(dialog, bg="#2C3E50")
        btn_frame.pack(pady=20)

        def on_connect():
            url = url_entry.get().strip()
            if url and url != "rtsp://":
                dialog.destroy()
                self._connect_ip_camera(url)

        def on_cancel():
            dialog.destroy()
            # 이전 선택으로 복원
            if self.available_cameras:
                self.camera_combo.current(0)

        connect_btn = tk.Button(
            btn_frame,
            text="연결",
            font=("Pretendard", 12, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            width=10,
            command=on_connect
        )
        connect_btn.pack(side="left", padx=10)

        cancel_btn = tk.Button(
            btn_frame,
            text="취소",
            font=("Pretendard", 12),
            bg="#7F8C8D",
            fg="#FFFFFF",
            width=10,
            command=on_cancel
        )
        cancel_btn.pack(side="left", padx=10)

        # Enter 키로 연결
        url_entry.bind("<Return>", lambda e: on_connect())
        url_entry.focus_set()

    def _connect_ip_camera(self, url):
        """IP 카메라 연결"""
        try:
            import cv2

            # 연결 시도
            print(f"[IP카메라] 연결 시도: {url}")

            if self.mirror_camera_label:
                self.mirror_camera_label.configure(text="IP 카메라 연결 중...", fg="#F39C12")
                self.mirror_camera_label.update()

            # 기존 카메라 해제
            if self.mirror_camera is not None:
                self.mirror_camera.release()
                self.mirror_camera = None

            # 기존 감지기 초기화 (USB → IP 전환 시 재초기화 필요)
            self.safety_detector = None
            if PPE_DETECTOR_AVAILABLE and PPEDetector is not None:
                try:
                    PPEDetector.reset_instance()
                    self.ppe_detector = None
                    self.ppe_visualizer = None
                except Exception as e:
                    print(f"[IP카메라] PPEDetector 리셋 오류: {e}")
            print("[IP카메라] 기존 감지기 초기화됨")

            # IP 카메라 연결 (RTSP 최적화 옵션)
            # Tapo 카메라 등 RTSP 스트림에 TCP 전송 모드 사용
            # H.264 디코딩 오류 감소를 위한 환경 변수 설정
            import os
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;10000000|probesize;10000000"

            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

            # 타임아웃 및 버퍼 설정
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # 버퍼 크기 증가로 프레임 드롭 감소

            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.mirror_camera = cap
                    self._ip_camera_url = url
                    self.selected_camera_index = -1  # IP 카메라는 -1로 표시

                    h, w = frame.shape[:2]
                    print(f"[IP카메라] 연결 성공: {url} ({w}x{h})")

                    # PPE 감지기 초기화 (IP 카메라용)
                    if PPE_DETECTOR_AVAILABLE and self.ppe_detector is None:
                        try:
                            self.ppe_detector = PPEDetector()
                            self.ppe_visualizer = PPEVisualizer(font_size=20)
                            print("[IP카메라] YOLOv10 PPE 감지기 초기화 완료")
                        except Exception as e:
                            print(f"[IP카메라] YOLOv10 PPE 감지기 초기화 실패: {e}")
                            self.ppe_detector = None
                            self.ppe_visualizer = None

                    # 기존 안전장구 감지기 초기화 (fallback)
                    if self.safety_detector is None:
                        try:
                            from ..sensor.safety_detector import SafetyEquipmentDetector
                            self.safety_detector = SafetyEquipmentDetector(camera=None)
                            self.safety_detector.set_camera(self.mirror_camera)
                            self.safety_detector.enable_face_recognition(True)
                            print("[IP카메라] 기존 안전장구 감지 시스템 초기화 완료 (fallback)")

                            # yolo_person_model 확인 (COCO 사물 인식용)
                            if hasattr(self.safety_detector, 'yolo_person_model'):
                                if self.safety_detector.yolo_person_model is not None:
                                    model_names = len(self.safety_detector.yolo_person_model.names) if hasattr(self.safety_detector.yolo_person_model, 'names') else 0
                                    print(f"[IP카메라] yolo_person_model 로드됨: {model_names}개 클래스")
                                else:
                                    print("[IP카메라] 경고: yolo_person_model이 None입니다!")
                            else:
                                print("[IP카메라] 경고: yolo_person_model 속성이 없습니다!")
                        except Exception as e:
                            print(f"[IP카메라] 기존 안전장구 감지 시스템 초기화 실패: {e}")
                            self.safety_detector = None

                    # PTZ 컨트롤러 초기화 (Tapo 카메라용)
                    self._init_ptz_controller(url)

                    # 프레임 업데이트 시작
                    self.mirror_frame_count = 0

                    # UI 업데이트하여 라벨 크기 결정 (줌 문제 방지)
                    self.update_idletasks()
                    if self.mirror_camera_label:
                        self.mirror_camera_label.update_idletasks()

                    self._update_mirror_frame()
                    return
                else:
                    cap.release()

            # 연결 실패
            if self.mirror_camera_label:
                self.mirror_camera_label.configure(
                    text=f"IP 카메라 연결 실패\n\nURL: {url}\n\n• URL이 올바른지 확인하세요\n• 카메라가 네트워크에 연결되어 있는지 확인하세요\n• Tapo: /stream1 또는 /stream2",
                    fg="#E74C3C"
                )

            print(f"[IP카메라] 연결 실패: {url}")

        except Exception as e:
            print(f"[IP카메라] 연결 오류: {e}")
            import traceback
            traceback.print_exc()
            if self.mirror_camera_label:
                self.mirror_camera_label.configure(
                    text=f"IP 카메라 연결 오류\n\n{str(e)}",
                    fg="#E74C3C"
                )

    def _init_ptz_controller(self, rtsp_url: str):
        """
        PTZ 컨트롤러 초기화 (Tapo 카메라용)

        Args:
            rtsp_url: RTSP URL (rtsp://user:pass@ip:port/path 형식)
        """
        if not TAPO_PTZ_AVAILABLE:
            print("[PTZ] pytapo 라이브러리 없음 - PTZ 비활성화")
            return

        try:
            # RTSP URL에서 IP, 사용자명, 비밀번호 추출
            # 형식: rtsp://username:password@ip:port/path
            import re
            match = re.match(r'rtsp://([^:]+):([^@]+)@([^:/]+)', rtsp_url)
            if not match:
                print(f"[PTZ] RTSP URL 파싱 실패: {rtsp_url}")
                return

            username, password, ip = match.groups()
            print(f"[PTZ] RTSP URL 파싱: ip={ip}, user={username}")

            # 카메라 설정에서 PTZ 활성화 여부 및 Tapo 계정 확인 (IP로 매칭)
            ptz_enabled = False
            ptz_email = ""
            ptz_password = ""
            try:
                if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                    ip_cameras = self.app.cfg.camera.get("ip_cameras", [])
                    for cam in ip_cameras:
                        cam_ip = cam.get("ip", "")
                        if cam_ip == ip:
                            ptz_enabled = cam.get("ptz_enabled", False)
                            ptz_email = cam.get("ptz_email", "")
                            ptz_password = cam.get("ptz_password", "")
                            print(f"[PTZ] 카메라 '{cam.get('name', '')}' 설정: ptz_enabled={ptz_enabled}, ptz_email={ptz_email[:3]}***" if ptz_email else f"[PTZ] 카메라 '{cam.get('name', '')}' 설정: ptz_enabled={ptz_enabled}")
                            break
                    else:
                        print(f"[PTZ] IP {ip}에 해당하는 카메라 설정을 찾을 수 없습니다")
            except Exception as e:
                print(f"[PTZ] 설정 확인 오류: {e}")

            if not ptz_enabled:
                print("[PTZ] PTZ 기능이 비활성화되어 있습니다 (카메라 설정에서 활성화)")
                return

            # PTZ Tapo 계정이 있으면 사용, 없으면 RTSP 계정 사용 (호환성 유지)
            ptz_user = ptz_email if ptz_email else username
            ptz_pass = ptz_password if ptz_password else password

            if ptz_email:
                print(f"[PTZ] Tapo 카메라 연결 시도: {ip} (Tapo 계정: {ptz_email[:3]}***)")
            else:
                print(f"[PTZ] Tapo 카메라 연결 시도: {ip} (RTSP 계정: {username}) - PTZ Tapo 계정 미설정")

            # PTZ 컨트롤러 생성
            self._ptz_controller = TapoPTZController(
                ip=ip,
                username=ptz_user,
                password=ptz_pass,
                on_status_change=self._on_ptz_status_change
            )

            # PTZ 활성화되어 있으면 일단 UI 표시 (연결 상태와 무관하게)
            self.after(0, self._show_ptz_controls)

            # 백그라운드에서 연결 (UI 블로킹 방지)
            def connect_async():
                if self._ptz_controller.connect():
                    # PTZ 지원 시 상태 업데이트
                    if self._ptz_controller.ptz_supported:
                        self.after(0, lambda: self._on_ptz_status_change("준비"))
                        print("[PTZ] 연결 성공 - PTZ 제어 가능")
                    else:
                        self.after(0, lambda: self._on_ptz_status_change("PTZ 미지원"))
                        print("[PTZ] 카메라가 PTZ를 지원하지 않습니다 (고정 카메라)")
                else:
                    # 연결 실패해도 UI는 유지, 상태만 표시
                    error_msg = self._ptz_controller.last_error[:15] if self._ptz_controller.last_error else "연결 실패"
                    self.after(0, lambda: self._on_ptz_status_change(error_msg))
                    print(f"[PTZ] 연결 실패 - 재시도 필요: {self._ptz_controller.last_error}")

            thread = threading.Thread(target=connect_async, daemon=True)
            thread.start()

        except Exception as e:
            print(f"[PTZ] 초기화 오류: {e}")
            import traceback
            traceback.print_exc()

    def _on_ptz_status_change(self, status: str):
        """PTZ 상태 변경 콜백"""
        if self._ptz_status_label:
            try:
                # 상태에 따라 색상 변경
                if "준비" in status or "완료" in status:
                    color = "#27AE60"  # 녹색 (정상)
                elif "연결" in status or "이동" in status:
                    color = "#F39C12"  # 주황색 (진행 중)
                elif "실패" in status or "오류" in status or "미지원" in status:
                    color = "#E74C3C"  # 빨간색 (오류)
                else:
                    color = "#3498DB"  # 파란색 (기타)
                self._ptz_status_label.configure(text=status, fg=color)
            except Exception:
                pass

    def _show_ptz_controls(self):
        """PTZ 컨트롤 패널 표시"""
        if self._ptz_panel is not None:
            return  # 이미 표시됨

        if not hasattr(self, 'mirror_stats_frame') or self.mirror_stats_frame is None:
            return

        # PTZ 컨트롤 프레임 생성 (상단 stats_frame 안에)
        self._ptz_panel = tk.Frame(self.mirror_stats_frame, bg="#2C3E50")
        self._ptz_panel.pack(side="right", padx=(10, 5))

        # PTZ 레이블
        ptz_label = tk.Label(
            self._ptz_panel,
            text="PTZ:",
            font=("Pretendard", 10),
            bg="#2C3E50",
            fg="#AAAAAA"
        )
        ptz_label.pack(side="left", padx=(0, 5))

        # 방향 버튼 스타일
        btn_style = {
            "font": ("Pretendard", 12),
            "width": 3,
            "height": 1,
            "bg": "#34495E",
            "fg": "#FFFFFF",
            "activebackground": "#3498DB",
            "activeforeground": "#FFFFFF",
            "relief": "flat",
            "cursor": "hand2"
        }

        # 위 버튼
        btn_up = tk.Button(
            self._ptz_panel,
            text="▲",
            command=self._ptz_move_up,
            **btn_style
        )
        btn_up.pack(side="left", padx=1)

        # 아래 버튼
        btn_down = tk.Button(
            self._ptz_panel,
            text="▼",
            command=self._ptz_move_down,
            **btn_style
        )
        btn_down.pack(side="left", padx=1)

        # 왼쪽 버튼
        btn_left = tk.Button(
            self._ptz_panel,
            text="◀",
            command=self._ptz_move_left,
            **btn_style
        )
        btn_left.pack(side="left", padx=1)

        # 오른쪽 버튼
        btn_right = tk.Button(
            self._ptz_panel,
            text="▶",
            command=self._ptz_move_right,
            **btn_style
        )
        btn_right.pack(side="left", padx=1)

        # 홈 버튼
        btn_home = tk.Button(
            self._ptz_panel,
            text="⌂",
            command=self._ptz_move_home,
            font=("Pretendard", 12),
            width=3,
            height=1,
            bg="#27AE60",
            fg="#FFFFFF",
            activebackground="#2ECC71",
            relief="flat",
            cursor="hand2"
        )
        btn_home.pack(side="left", padx=(5, 2))

        # 상태 레이블
        self._ptz_status_label = tk.Label(
            self._ptz_panel,
            text="연결 중...",
            font=("Pretendard", 9),
            bg="#2C3E50",
            fg="#F39C12",  # 주황색 (연결 대기)
            width=12
        )
        self._ptz_status_label.pack(side="left", padx=(5, 0))

        print("[PTZ] 컨트롤 패널 표시됨")

    def _hide_ptz_controls(self):
        """PTZ 컨트롤 패널 숨기기"""
        if self._ptz_panel is not None:
            self._ptz_panel.destroy()
            self._ptz_panel = None
            self._ptz_status_label = None

    def _ptz_move_up(self):
        """PTZ 위로 이동"""
        self._ptz_execute_move(lambda: self._ptz_controller.move_up())

    def _ptz_move_down(self):
        """PTZ 아래로 이동"""
        self._ptz_execute_move(lambda: self._ptz_controller.move_down())

    def _ptz_move_left(self):
        """PTZ 왼쪽으로 이동"""
        self._ptz_execute_move(lambda: self._ptz_controller.move_left())

    def _ptz_move_right(self):
        """PTZ 오른쪽으로 이동"""
        self._ptz_execute_move(lambda: self._ptz_controller.move_right())

    def _ptz_move_home(self):
        """PTZ 홈 위치로 이동"""
        self._ptz_execute_move(lambda: self._ptz_controller.move_home())

    def _ptz_execute_move(self, move_func):
        """PTZ 이동 실행 (연결 안 되어 있으면 재연결 시도)"""
        if self._ptz_controller is None:
            self._on_ptz_status_change("PTZ 없음")
            return

        # 차단 상태인지 확인
        if hasattr(self, '_ptz_blocked') and self._ptz_blocked:
            self._on_ptz_status_change("PTZ 차단됨")
            print("[PTZ] Tapo 카메라가 일시 차단되었습니다. 잠시 후 다시 시도하세요.")
            return

        def execute():
            # 연결 안 되어 있으면 재연결 시도
            if not self._ptz_controller.is_available:
                self._on_ptz_status_change("재연결 중...")
                if self._ptz_controller.connect():
                    self._on_ptz_status_change("연결됨")
                    self._ptz_blocked = False
                else:
                    error_msg = self._ptz_controller.last_error or "연결 실패"

                    # Temporary Suspension 감지 시 차단 상태 설정
                    if "Temporary Suspension" in error_msg or "Suspension" in error_msg:
                        self._ptz_blocked = True
                        self.after(0, lambda: self._on_ptz_status_change("차단됨(30분)"))
                        print(f"[PTZ] Tapo 카메라 일시 차단 - 30분 후 다시 시도하세요")
                    elif "Invalid authentication" in error_msg:
                        self._ptz_blocked = True
                        self.after(0, lambda: self._on_ptz_status_change("인증 실패"))
                        print(f"[PTZ] Tapo 계정 정보가 올바르지 않습니다. 카메라 설정에서 PTZ 계정 정보를 확인하세요.")
                    else:
                        display_msg = error_msg[:15] if len(error_msg) > 15 else error_msg
                        self.after(0, lambda: self._on_ptz_status_change(display_msg))
                        print(f"[PTZ] 재연결 실패: {error_msg}")
                    return

            # 이동 실행
            try:
                move_func()
            except Exception as e:
                self.after(0, lambda: self._on_ptz_status_change("오류"))
                print(f"[PTZ] 이동 오류: {e}")

        threading.Thread(target=execute, daemon=True).start()

    def _apply_image_processing(self, frame):
        """
        이미지 전처리 적용 (고급 설정)

        밝기, 대비, 채도 조절
        """
        try:
            import cv2
            import numpy as np

            # 이미지 전처리 설정 확인
            if not hasattr(self, '_image_processing'):
                return frame

            settings = self._image_processing
            brightness = settings.get('brightness', 0)
            contrast = settings.get('contrast', 1.0)
            saturation = settings.get('saturation', 1.0)

            # 기본값이면 처리 안 함 (성능 최적화)
            if brightness == 0 and contrast == 1.0 and saturation == 1.0:
                return frame

            result = frame.copy()

            # 1. 밝기/대비 조절
            if brightness != 0 or contrast != 1.0:
                # result = contrast * frame + brightness
                result = cv2.convertScaleAbs(result, alpha=contrast, beta=brightness)

            # 2. 채도 조절
            if saturation != 1.0:
                # BGR -> HSV
                hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)

                # 채도(S) 채널 조절
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)

                # HSV -> BGR
                result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

            return result

        except Exception as e:
            # 오류 발생 시 원본 반환
            if hasattr(self, 'mirror_frame_count') and self.mirror_frame_count % 300 == 1:
                print(f"[이미지 전처리] 오류: {e}")
            return frame

    def _load_advanced_settings(self):
        """고급 설정 로드 및 적용"""
        try:
            config = None
            # app.cfg 또는 app.config에서 설정 가져오기
            if hasattr(self, 'app'):
                if hasattr(self.app, 'cfg'):
                    config = self.app.cfg
                elif hasattr(self.app, 'config'):
                    config = self.app.config

            if config and hasattr(config, 'camera'):
                advanced = config.camera.get("advanced_settings", {})

                # 이미지 전처리 설정
                self._image_processing = {
                    'brightness': advanced.get('brightness', 0),
                    'contrast': advanced.get('contrast', 1.0),
                    'saturation': advanced.get('saturation', 1.0)
                }

                # 감지 주기 설정
                self._detection_interval = advanced.get('detection_interval', 1)

                if advanced:
                    print(f"[고급설정] 로드 완료: brightness={self._image_processing['brightness']}, "
                          f"contrast={self._image_processing['contrast']}, "
                          f"saturation={self._image_processing['saturation']}")
        except Exception as e:
            print(f"[고급설정] 로드 오류: {e}")

    def _create_realtime_settings_panel(self):
        """거울보기 화면 좌측 하단에 실시간 설정 미니 패널 생성"""
        try:
            # 이미 존재하면 스킵
            if hasattr(self, '_realtime_panel') and self._realtime_panel is not None:
                try:
                    if self._realtime_panel.winfo_exists():
                        return
                except:
                    pass

            # 미니 패널 프레임 (좌측 하단 오버레이)
            self._realtime_panel = tk.Frame(
                self.mirror_content_frame,
                bg="#1a1a2e",
                relief="raised",
                bd=1
            )

            # 접기/펼치기 상태
            self._realtime_panel_expanded = False

            # 토글 버튼
            self._realtime_toggle_btn = tk.Button(
                self._realtime_panel,
                text="⚙️ 설정",
                font=("Pretendard", 9),
                bg="#16213e",
                fg="#00d4ff",
                relief="flat",
                command=self._toggle_realtime_panel
            )
            self._realtime_toggle_btn.pack(fill="x", padx=2, pady=2)

            # 설정 컨텐츠 프레임 (초기에는 숨김)
            self._realtime_content = tk.Frame(self._realtime_panel, bg="#1a1a2e")

            # === 설정 항목들 ===
            # 현재 설정값 로드
            self._load_realtime_settings_values()

            # 1. COCO 신뢰도 (IP 카메라)
            row1 = tk.Frame(self._realtime_content, bg="#1a1a2e")
            row1.pack(fill="x", pady=2, padx=3)
            tk.Label(row1, text="사물감지:", font=("Pretendard", 8), bg="#1a1a2e", fg="#aaa", width=7, anchor="w").pack(side="left")
            self._rt_coco_var = tk.DoubleVar(value=getattr(self, '_rt_coco_conf', 0.15))
            self._rt_coco_scale = tk.Scale(
                row1, from_=0.01, to=0.50, resolution=0.01, orient="horizontal",
                variable=self._rt_coco_var, length=100, bg="#16213e", fg="#fff",
                troughcolor="#0f3460", highlightthickness=0, sliderrelief="flat",
                showvalue=False, command=self._on_rt_coco_change
            )
            self._rt_coco_scale.pack(side="left", padx=2)
            self._rt_coco_label = tk.Label(row1, text=f"{self._rt_coco_var.get():.2f}", font=("Pretendard", 8, "bold"), bg="#1a1a2e", fg="#00d4ff", width=4)
            self._rt_coco_label.pack(side="left")

            # 2. PPE 신뢰도
            row2 = tk.Frame(self._realtime_content, bg="#1a1a2e")
            row2.pack(fill="x", pady=2, padx=3)
            tk.Label(row2, text="안전장구:", font=("Pretendard", 8), bg="#1a1a2e", fg="#aaa", width=7, anchor="w").pack(side="left")
            self._rt_ppe_var = tk.DoubleVar(value=getattr(self, '_rt_ppe_conf', 0.25))
            self._rt_ppe_scale = tk.Scale(
                row2, from_=0.05, to=0.70, resolution=0.05, orient="horizontal",
                variable=self._rt_ppe_var, length=100, bg="#16213e", fg="#fff",
                troughcolor="#0f3460", highlightthickness=0, sliderrelief="flat",
                showvalue=False, command=self._on_rt_ppe_change
            )
            self._rt_ppe_scale.pack(side="left", padx=2)
            self._rt_ppe_label = tk.Label(row2, text=f"{self._rt_ppe_var.get():.2f}", font=("Pretendard", 8, "bold"), bg="#1a1a2e", fg="#00d4ff", width=4)
            self._rt_ppe_label.pack(side="left")

            # 3. 밝기
            row3 = tk.Frame(self._realtime_content, bg="#1a1a2e")
            row3.pack(fill="x", pady=2, padx=3)
            tk.Label(row3, text="밝기:", font=("Pretendard", 8), bg="#1a1a2e", fg="#aaa", width=7, anchor="w").pack(side="left")
            self._rt_brightness_var = tk.IntVar(value=getattr(self, '_rt_brightness', 0))
            self._rt_brightness_scale = tk.Scale(
                row3, from_=-50, to=50, resolution=5, orient="horizontal",
                variable=self._rt_brightness_var, length=100, bg="#16213e", fg="#fff",
                troughcolor="#0f3460", highlightthickness=0, sliderrelief="flat",
                showvalue=False, command=self._on_rt_brightness_change
            )
            self._rt_brightness_scale.pack(side="left", padx=2)
            self._rt_brightness_label = tk.Label(row3, text=f"{self._rt_brightness_var.get():+d}", font=("Pretendard", 8, "bold"), bg="#1a1a2e", fg="#00d4ff", width=4)
            self._rt_brightness_label.pack(side="left")

            # 4. 대비
            row4 = tk.Frame(self._realtime_content, bg="#1a1a2e")
            row4.pack(fill="x", pady=2, padx=3)
            tk.Label(row4, text="대비:", font=("Pretendard", 8), bg="#1a1a2e", fg="#aaa", width=7, anchor="w").pack(side="left")
            self._rt_contrast_var = tk.DoubleVar(value=getattr(self, '_rt_contrast', 1.0))
            self._rt_contrast_scale = tk.Scale(
                row4, from_=0.5, to=2.0, resolution=0.1, orient="horizontal",
                variable=self._rt_contrast_var, length=100, bg="#16213e", fg="#fff",
                troughcolor="#0f3460", highlightthickness=0, sliderrelief="flat",
                showvalue=False, command=self._on_rt_contrast_change
            )
            self._rt_contrast_scale.pack(side="left", padx=2)
            self._rt_contrast_label = tk.Label(row4, text=f"{self._rt_contrast_var.get():.1f}x", font=("Pretendard", 8, "bold"), bg="#1a1a2e", fg="#00d4ff", width=4)
            self._rt_contrast_label.pack(side="left")

            # 5. FPS/지연 표시
            row5 = tk.Frame(self._realtime_content, bg="#1a1a2e")
            row5.pack(fill="x", pady=2, padx=3)
            self._rt_fps_label = tk.Label(row5, text="FPS: -- | 감지: --개", font=("Pretendard", 8), bg="#1a1a2e", fg="#888")
            self._rt_fps_label.pack(side="left")

            # place로 좌측 하단에 배치
            self._realtime_panel.place(x=5, rely=1.0, anchor="sw", y=-5)

        except Exception as e:
            print(f"[실시간설정] 패널 생성 오류: {e}")
            import traceback
            traceback.print_exc()

    def _load_realtime_settings_values(self):
        """실시간 설정 패널의 초기값 로드"""
        try:
            # 기본값 (성능 최적화: IP 카메라 0.25)
            self._rt_coco_conf = 0.25
            self._rt_ppe_conf = 0.25
            self._rt_brightness = 0
            self._rt_contrast = 1.0

            # 저장된 고급 설정에서 로드
            config = None
            if hasattr(self, 'app'):
                if hasattr(self.app, 'cfg'):
                    config = self.app.cfg
                elif hasattr(self.app, 'config'):
                    config = self.app.config

            if config and hasattr(config, 'camera'):
                advanced = config.camera.get("advanced_settings", {})
                self._rt_coco_conf = advanced.get('coco_confidence_ip', 0.25)
                self._rt_ppe_conf = advanced.get('ppe_confidence', 0.25)
                self._rt_brightness = advanced.get('brightness', 0)
                self._rt_contrast = advanced.get('contrast', 1.0)

        except Exception as e:
            print(f"[실시간설정] 값 로드 오류: {e}")

    def _toggle_realtime_panel(self):
        """실시간 설정 패널 접기/펼치기"""
        try:
            if self._realtime_panel_expanded:
                # 접기
                self._realtime_content.pack_forget()
                self._realtime_toggle_btn.configure(text="⚙️ 설정")
                self._realtime_panel_expanded = False
            else:
                # 펼치기
                self._realtime_content.pack(fill="x", padx=2, pady=2)
                self._realtime_toggle_btn.configure(text="⚙️ 접기")
                self._realtime_panel_expanded = True
        except Exception as e:
            print(f"[실시간설정] 토글 오류: {e}")

    def _on_rt_coco_change(self, val):
        """COCO 신뢰도 실시간 변경"""
        try:
            conf = float(val)
            self._rt_coco_label.configure(text=f"{conf:.2f}")

            # 감지기에 즉시 적용
            if hasattr(self, 'safety_detector') and self.safety_detector:
                if hasattr(self.safety_detector, '_coco_conf'):
                    self.safety_detector._coco_conf = conf

            # 이미지 전처리 설정에도 저장
            if not hasattr(self, '_image_processing'):
                self._image_processing = {}
            # coco_conf는 별도 저장
            self._rt_coco_conf_current = conf

        except Exception as e:
            print(f"[실시간설정] COCO 변경 오류: {e}")

    def _on_rt_ppe_change(self, val):
        """PPE 신뢰도 실시간 변경"""
        try:
            conf = float(val)
            self._rt_ppe_label.configure(text=f"{conf:.2f}")

            # PPE 감지기에 즉시 적용
            if hasattr(self, 'ppe_detector') and self.ppe_detector:
                if hasattr(self.ppe_detector, 'conf_threshold'):
                    self.ppe_detector.conf_threshold = conf

        except Exception as e:
            print(f"[실시간설정] PPE 변경 오류: {e}")

    def _on_rt_brightness_change(self, val):
        """밝기 실시간 변경"""
        try:
            brightness = int(float(val))
            self._rt_brightness_label.configure(text=f"{brightness:+d}")

            # 이미지 전처리에 즉시 적용
            if not hasattr(self, '_image_processing'):
                self._image_processing = {}
            self._image_processing['brightness'] = brightness

        except Exception as e:
            print(f"[실시간설정] 밝기 변경 오류: {e}")

    def _on_rt_contrast_change(self, val):
        """대비 실시간 변경"""
        try:
            contrast = float(val)
            self._rt_contrast_label.configure(text=f"{contrast:.1f}x")

            # 이미지 전처리에 즉시 적용
            if not hasattr(self, '_image_processing'):
                self._image_processing = {}
            self._image_processing['contrast'] = contrast

        except Exception as e:
            print(f"[실시간설정] 대비 변경 오류: {e}")

    def _update_realtime_fps_display(self, fps, detection_count):
        """실시간 FPS 및 감지 수 업데이트"""
        try:
            if hasattr(self, '_rt_fps_label') and self._rt_fps_label:
                self._rt_fps_label.configure(text=f"FPS: {fps:.1f} | 감지: {detection_count}개")
        except:
            pass

    def _hide_realtime_settings_panel(self):
        """실시간 설정 패널 숨기기"""
        try:
            if hasattr(self, '_realtime_panel') and self._realtime_panel:
                self._realtime_panel.place_forget()
                self._realtime_panel.destroy()
                self._realtime_panel = None
        except:
            pass
