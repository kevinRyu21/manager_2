"""
화재 경보 긴급 다이얼로그

화재가 감지되었을 때 화면 전체에 표시되는 긴급 경고 다이얼로그입니다.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Dict, Optional, Callable
import threading


class FireAlertDialog(tk.Toplevel):
    """화재 경보 긴급 다이얼로그"""

    # 경보 레벨별 색상
    LEVEL_COLORS = {
        3: {"bg": "#E67E22", "fg": "#FFFFFF", "name": "주의"},  # 주황
        4: {"bg": "#E74C3C", "fg": "#FFFFFF", "name": "경계"},  # 빨강
        5: {"bg": "#8E44AD", "fg": "#FFFFFF", "name": "위험"},  # 보라
    }

    def __init__(
        self,
        parent,
        level: int,
        probability: float,
        triggered_sensors: List[str],
        sensor_values: Dict[str, float],
        location: str = "알 수 없음",
        on_dismiss: Optional[Callable] = None,
        on_emergency_call: Optional[Callable] = None
    ):
        super().__init__(parent)

        self.level = level
        self.probability = probability
        self.triggered_sensors = triggered_sensors
        self.sensor_values = sensor_values
        self.location = location
        self.on_dismiss = on_dismiss
        self.on_emergency_call = on_emergency_call

        self._alarm_playing = False
        self._blink_state = True

        # 다이얼로그 설정
        self.title("🔥 화재 경보")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 전체 화면 모드
        self.attributes("-fullscreen", True)

        # 배경색 설정
        level_config = self.LEVEL_COLORS.get(level, self.LEVEL_COLORS[4])
        self.configure(bg=level_config["bg"])

        self._build_ui(level_config)
        self._start_alarm()
        self._start_blink()

    def _build_ui(self, level_config: dict):
        """UI 구성"""
        bg = level_config["bg"]
        fg = level_config["fg"]
        level_name = level_config["name"]

        # 메인 컨테이너
        main_frame = tk.Frame(self, bg=bg)
        main_frame.pack(expand=True, fill="both")

        # 상단: 경보 아이콘 및 레벨
        header_frame = tk.Frame(main_frame, bg=bg)
        header_frame.pack(pady=50)

        # 큰 경고 아이콘
        self.alert_icon = tk.Label(
            header_frame,
            text="🔥",
            font=("Pretendard", 120),
            bg=bg,
            fg=fg
        )
        self.alert_icon.pack()

        # 경보 레벨
        level_label = tk.Label(
            header_frame,
            text=f"화재 {level_name}",
            font=("Pretendard", 72, "bold"),
            bg=bg,
            fg=fg
        )
        level_label.pack(pady=20)

        # 중앙: 상세 정보
        info_frame = tk.Frame(main_frame, bg=bg)
        info_frame.pack(pady=30)

        # 화재 확률
        prob_text = f"화재 확률: {self.probability * 100:.1f}%"
        prob_label = tk.Label(
            info_frame,
            text=prob_text,
            font=("Pretendard", 36, "bold"),
            bg=bg,
            fg=fg
        )
        prob_label.pack(pady=10)

        # 위치
        location_label = tk.Label(
            info_frame,
            text=f"📍 위치: {self.location}",
            font=("Pretendard", 28),
            bg=bg,
            fg=fg
        )
        location_label.pack(pady=10)

        # 감지 시간
        time_label = tk.Label(
            info_frame,
            text=f"⏰ 감지 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            font=("Pretendard", 24),
            bg=bg,
            fg=fg
        )
        time_label.pack(pady=10)

        # 경보 발생 센서 목록
        if self.triggered_sensors:
            sensor_frame = tk.Frame(main_frame, bg="#00000044")
            sensor_frame.pack(pady=20, padx=100, fill="x")

            sensor_title = tk.Label(
                sensor_frame,
                text="⚠️ 경보 발생 센서",
                font=("Pretendard", 24, "bold"),
                bg="#00000044",
                fg="#FFFFFF"
            )
            sensor_title.pack(pady=10)

            # 센서 이름 매핑
            sensor_names = {
                "temperature": "온도",
                "humidity": "습도",
                "co": "일산화탄소(CO)",
                "co2": "이산화탄소(CO2)",
                "o2": "산소(O2)",
                "smoke": "연기",
                "h2s": "황화수소(H2S)",
                "lel": "가연성가스(LEL)",
            }

            for sensor_key in self.triggered_sensors:
                sensor_name = sensor_names.get(sensor_key, sensor_key)
                value = self.sensor_values.get(sensor_key, "--")

                sensor_row = tk.Label(
                    sensor_frame,
                    text=f"  • {sensor_name}: {value}",
                    font=("Pretendard", 20),
                    bg="#00000044",
                    fg="#FFFFFF",
                    anchor="w"
                )
                sensor_row.pack(fill="x", padx=20, pady=2)

        # 하단: 버튼
        button_frame = tk.Frame(main_frame, bg=bg)
        button_frame.pack(side="bottom", pady=50)

        # 긴급 연락 버튼
        emergency_btn = tk.Button(
            button_frame,
            text="📞 119 긴급 연락",
            font=("Pretendard", 24, "bold"),
            bg="#FF0000",
            fg="#FFFFFF",
            relief="raised",
            bd=5,
            padx=40,
            pady=20,
            command=self._on_emergency_click,
            activebackground="#CC0000",
            activeforeground="#FFFFFF"
        )
        emergency_btn.pack(side="left", padx=20)

        # 확인 버튼
        dismiss_btn = tk.Button(
            button_frame,
            text="✓ 확인",
            font=("Pretendard", 24, "bold"),
            bg="#333333",
            fg="#FFFFFF",
            relief="raised",
            bd=5,
            padx=40,
            pady=20,
            command=self._on_close,
            activebackground="#555555",
            activeforeground="#FFFFFF"
        )
        dismiss_btn.pack(side="left", padx=20)

        # 전체 화면 해제 안내
        hint_label = tk.Label(
            main_frame,
            text="ESC 키를 눌러 창을 닫을 수 있습니다",
            font=("Pretendard", 14),
            bg=bg,
            fg="#FFFFFF88"
        )
        hint_label.pack(side="bottom", pady=20)

        # 키보드 바인딩
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("<Return>", lambda e: self._on_close())

    def _start_alarm(self):
        """경보음 시작"""
        self._alarm_playing = True

        def play_alarm():
            try:
                import winsound
                while self._alarm_playing:
                    winsound.Beep(1000, 500)
                    winsound.Beep(800, 500)
            except ImportError:
                # Linux/Mac에서는 시스템 벨 사용
                while self._alarm_playing:
                    print("\a")  # 시스템 벨
                    import time
                    time.sleep(1)
            except Exception:
                pass

        # 백그라운드 스레드에서 경보음 재생
        threading.Thread(target=play_alarm, daemon=True).start()

    def _stop_alarm(self):
        """경보음 중지"""
        self._alarm_playing = False

    def _start_blink(self):
        """깜빡임 효과 시작"""
        self._blink()

    def _blink(self):
        """깜빡임 애니메이션"""
        if not self.winfo_exists():
            return

        self._blink_state = not self._blink_state

        if self._blink_state:
            self.alert_icon.configure(text="🔥")
        else:
            self.alert_icon.configure(text="⚠️")

        self.after(500, self._blink)

    def _on_emergency_click(self):
        """긴급 연락 버튼 클릭"""
        if self.on_emergency_call:
            self.on_emergency_call()

        # 119 안내 다이얼로그
        info_dialog = tk.Toplevel(self)
        info_dialog.title("긴급 연락")
        info_dialog.geometry("400x200")
        info_dialog.attributes("-topmost", True)

        msg = tk.Label(
            info_dialog,
            text="📞 119 (소방서)\n\n화재 발생 시 즉시 대피하고\n119에 신고하세요.",
            font=("Pretendard", 16),
            justify="center"
        )
        msg.pack(expand=True)

        close_btn = tk.Button(
            info_dialog,
            text="확인",
            command=info_dialog.destroy,
            font=("Pretendard", 14),
            padx=20,
            pady=10
        )
        close_btn.pack(pady=20)

    def _on_close(self):
        """다이얼로그 닫기"""
        self._stop_alarm()

        if self.on_dismiss:
            self.on_dismiss()

        self.destroy()


class FireAlertManager:
    """화재 경보 다이얼로그 관리자"""

    def __init__(self, app):
        self.app = app
        self._current_dialog = None
        self._last_alert_level = 1
        self._alert_cooldown = {}  # 센서별 경보 쿨다운

    def show_fire_alert(
        self,
        level: int,
        probability: float,
        triggered_sensors: List[str],
        sensor_values: Dict[str, float],
        location: str = "알 수 없음"
    ):
        """화재 경보 다이얼로그 표시"""
        # 레벨 3(주의) 이상만 다이얼로그 표시
        if level < 3:
            return

        # 이전 다이얼로그가 있으면 닫기
        if self._current_dialog and self._current_dialog.winfo_exists():
            # 같은 레벨이면 갱신하지 않음
            if level <= self._last_alert_level:
                return
            self._current_dialog.destroy()

        self._last_alert_level = level

        # 새 다이얼로그 생성
        self._current_dialog = FireAlertDialog(
            self.app,
            level=level,
            probability=probability,
            triggered_sensors=triggered_sensors,
            sensor_values=sensor_values,
            location=location,
            on_dismiss=self._on_dialog_dismiss
        )

    def _on_dialog_dismiss(self):
        """다이얼로그 닫힘 콜백"""
        self._current_dialog = None
        self._last_alert_level = 1

    def close_current_alert(self):
        """현재 표시 중인 경보 다이얼로그 닫기"""
        if self._current_dialog and self._current_dialog.winfo_exists():
            self._current_dialog._on_close()
