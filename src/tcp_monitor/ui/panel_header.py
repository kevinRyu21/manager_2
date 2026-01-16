"""
패널 헤더 UI 컴포넌트

로고, 시계, 체감온도/불쾌지수, 화재확률, 날씨, 컨트롤 버튼을 관리합니다.
고정형 레이아웃으로 구현.
"""

import tkinter as tk
from ..utils.helpers import find_asset, now_local, get_base_dir
from ..utils.comfort import heat_index_c, discomfort_index

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class PanelHeader(tk.Frame):
    """패널 헤더 - 고정형 레이아웃"""

    def __init__(self, master, sid_key, app):
        super().__init__(master, bg="#E8F4FD", relief="raised", bd=2, height=60)
        self.pack_propagate(False)  # 고정 높이 유지
        self.app = app
        self.sid_key = sid_key
        self.master_panel = master

        # 체감온도/불쾌지수 변수 초기화
        self._latest_temp = None
        self._latest_hum = None
        self._connection_status = "waiting"

        # 화재 정보
        self._fire_probability = 0.0
        self._fire_level = "정상"

        # 날씨 정보
        self._weather_info = None

        # === 좌측 영역: 로고 + 시계 + 음성 + 안전안전점검 ===
        left_frame = tk.Frame(self, bg="#E8F4FD")
        left_frame.place(x=5, rely=0.5, anchor="w")

        # 로고
        self.logo_imgref = None
        self.logo_label = tk.Label(left_frame, text="", bg="#E8F4FD", fg="#2C3E50", font=("Pretendard", 10))
        self.logo_label.pack(side="left", padx=(0, 5))
        self.after(100, self._load_logo)

        # 시계 (년도-날짜-시간)
        self.clock_label = tk.Label(left_frame, text="2026-01-16 00:00:00", font=("Pretendard", 11, "bold"),
                                   bg="#E8F4FD", fg="#2C3E50")
        self.clock_label.pack(side="left", padx=(0, 5))

        # 음성 토글
        self.voice_alert_enabled = getattr(app, 'global_voice_alert_enabled', True)
        initial_icon = "🔊" if self.voice_alert_enabled else "🔇"
        self.voice_toggle_btn = tk.Button(left_frame, text=initial_icon, command=self._toggle_voice_alert,
                                         font=("Pretendard", 18), bg="#E8F4FD", fg="#2C3E50",
                                         relief="flat", bd=0, padx=2, pady=0, cursor="hand2")
        self.voice_toggle_btn.pack(side="left", padx=(0, 5))

        # 안전안전점검 버튼
        self.mirror_mode = False
        self.mirror_camera_ready = False
        self.mirror_btn = tk.Button(left_frame, text="안전점검", command=self._toggle_mirror_view,
                                   font=("Pretendard", 9, "bold"), bg="#9C27B0", fg="#FFFFFF",
                                   relief="raised", bd=1, width=7, cursor="hand2", state="disabled")
        self.mirror_btn.pack(side="left", padx=(0, 5))

        # 캡쳐 버튼
        self.capture_btn = tk.Button(left_frame, text="📸캡쳐", command=self._capture_current_screen,
                                    font=("Pretendard", 10, "bold"), bg="#3498DB", fg="#FFFFFF",
                                    relief="raised", bd=1, width=6, cursor="hand2")
        self.capture_btn.pack(side="left", padx=(0, 5))

        # 모드 전환 버튼 (관리자/일반)
        if app.cfg.admin_mode:
            self.mode_toggle_btn = tk.Button(left_frame, text="🔓관리자",
                                            font=("Pretendard", 9, "bold"), bg="#FFD700", fg="#D32F2F",
                                            relief="raised", bd=1, width=7, cursor="hand2",
                                            command=self._on_mode_toggle_click)
        else:
            self.mode_toggle_btn = tk.Button(left_frame, text="🔒일반",
                                            font=("Pretendard", 9, "bold"), bg="#3498DB", fg="#FFFFFF",
                                            relief="raised", bd=1, width=7, cursor="hand2",
                                            command=self._on_mode_toggle_click)
        self.mode_toggle_btn.pack(side="left", padx=(0, 10))
        self.admin_mode_btn = self.mode_toggle_btn

        # === 중앙 영역: 체감온도 + 불쾌지수 + 화재확률 + 날씨 ===
        center_frame = tk.Frame(self, bg="#D1E7DD", relief="raised", bd=1)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # 체감온도
        self.hi_label = tk.Label(center_frame, text="체감온도 HI: --°C", bg="#D1E7DD", fg="#2C3E50",
                                font=("Pretendard", 11, "bold"), cursor="hand2")
        self.hi_label.pack(side="left", padx=6, pady=4)
        self.hi_label.bind("<Button-1>", self._show_hi_tooltip)
        self.hi_label.bind("<Enter>", self._on_hi_enter)
        self.hi_label.bind("<Leave>", self._on_hi_leave)

        # 불쾌지수
        self.di_label = tk.Label(center_frame, text="불쾌지수 DI: --", bg="#D1E7DD", fg="#2C3E50",
                                font=("Pretendard", 11, "bold"), cursor="hand2")
        self.di_label.pack(side="left", padx=6, pady=4)
        self.di_label.bind("<Button-1>", self._on_di_click)
        self.di_label.bind("<Enter>", self._on_di_enter)
        self.di_label.bind("<Leave>", self._on_di_leave)

        # 구분선
        tk.Frame(center_frame, bg="#888888", width=1).pack(side="left", fill="y", padx=3, pady=4)

        # 화재 확률/경보
        self.fire_label = tk.Label(center_frame, text="🔥0% 정상", bg="#D1E7DD", fg="#27AE60",
                                  font=("Pretendard", 11, "bold"))
        self.fire_label.pack(side="left", padx=6, pady=4)

        # 구분선
        tk.Frame(center_frame, bg="#888888", width=1).pack(side="left", fill="y", padx=3, pady=4)

        # 날씨 정보
        self.weather_label = tk.Label(center_frame, text="🌤️ --°C", bg="#D1E7DD", fg="#2C3E50",
                                     font=("Pretendard", 11, "bold"))
        self.weather_label.pack(side="left", padx=6, pady=4)

        self.center_box = center_frame  # 하위 호환성

        # === 우측 영역: 오늘경고 + 안전교육 + 뷰모드 버튼 ===
        right_frame = tk.Frame(self, bg="#E8F4FD")
        right_frame.place(relx=1.0, x=-5, rely=0.5, anchor="e")

        # 오늘 경고 버튼 (주의/경계/심각)
        self.alert_btn = tk.Button(right_frame, text="주의0/경계0/심각0", command=self._show_today_alerts,
                                  font=("Pretendard", 9, "bold"), bg="#E74C3C", fg="#FFFFFF",
                                  relief="raised", bd=1, width=15, cursor="hand2")
        self.alert_btn.pack(side="left", padx=2)

        # 안전 교육 버튼
        self.btn_safety = tk.Button(right_frame, text="안전교육", command=lambda: master.show_safety_education(),
                                   bg="#FF9800", fg="#FFFFFF", font=("Pretendard", 9, "bold"),
                                   relief="raised", bd=1, width=6)
        self.btn_safety.pack(side="left", padx=2)

        # 센서상세보기 버튼 (기존 타일)
        self.btn_card = tk.Button(right_frame, text="센서상세", command=lambda: master.switch_to_card_mode(),
                                 bg="#4CAF50", fg="#FFFFFF", font=("Pretendard", 9, "bold"),
                                 relief="sunken", bd=1, width=7)
        self.btn_card.pack(side="left", padx=2)

        # 센서전체보기 버튼 (새로 추가) - 초기에는 비활성화 (센서 2개 이상일 때만 활성화)
        self.btn_all_sensors = tk.Button(right_frame, text="센서전체", command=lambda: master.switch_to_all_sensors_mode(),
                                        bg="#2196F3", fg="#FFFFFF", font=("Pretendard", 9, "bold"),
                                        relief="raised", bd=1, width=7, state="disabled")
        self.btn_all_sensors.pack(side="left", padx=2)

        # 도면 버튼
        self.btn_blueprint = tk.Button(right_frame, text="도면", command=lambda: master.switch_to_blueprint_mode(),
                                      bg="#90A4AE", fg="#FFFFFF", font=("Pretendard", 9, "bold"),
                                      relief="raised", bd=1, width=4)
        self.btn_blueprint.pack(side="left", padx=2)

        # 하위 호환성
        self.btn_graph = None
        self.title_label = self.clock_label  # 하위 호환성

        # 툴팁 변수
        self._hi_tooltip = None
        self._di_tooltip = None
        self._di_click_count = 0
        self._di_click_reset_timer = None

        # 초기 상태
        self._update_button_states()
        self.after(500, self._tick_clock)

    def _load_logo(self):
        """로고 로드"""
        if PIL_OK:
            p = find_asset("logo.png")
            if p:
                try:
                    im = Image.open(p)
                    target_h = 40
                    ratio = target_h / max(im.height, 1)
                    im = im.resize((max(int(im.width * ratio), 1), target_h), Image.LANCZOS)
                    self.logo_imgref = ImageTk.PhotoImage(im)
                    self.logo_label.configure(image=self.logo_imgref, text="", bg="#E8F4FD")
                    return
                except Exception:
                    pass
        self.logo_label.configure(image="", text="GARAMe", font=("Pretendard", 10, "bold"))

    def _show_control_buttons(self):
        """컨트롤 버튼들 표시 - 이미 배치됨"""
        pass

    def _tick_clock(self):
        """시계 업데이트 (년도-날짜-시간)"""
        self.clock_label.configure(text=now_local().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(500, self._tick_clock)

    def update_alert_count(self):
        """오늘 경고 카운트 버튼 텍스트 갱신 (주의/경계/심각)"""
        try:
            if hasattr(self.app, 'get_today_alert_level_counts_for'):
                counts = self.app.get_today_alert_level_counts_for(self.sid_key)
                c3 = counts.get(3, 0)  # 주의
                c4 = counts.get(4, 0)  # 경계
                c5 = counts.get(5, 0)  # 심각
                self.alert_btn.configure(text=f"주의{c3}/경계{c4}/심각{c5}")
        except Exception:
            pass

    def update_fire_info(self, probability, level):
        """화재 확률 및 경보 수준 업데이트"""
        self._fire_probability = probability
        self._fire_level = level

        # 색상 결정
        if level == "정상":
            color = "#27AE60"
        elif level == "관심":
            color = "#3498DB"
        elif level == "주의":
            color = "#F1C40F"
        elif level == "경계":
            color = "#E67E22"
        else:  # 심각/위험
            color = "#E74C3C"

        self.fire_label.configure(text=f"🔥{probability:.0f}% {level}", fg=color)

    def update_weather_info(self, temp=None, condition=None, humidity=None):
        """날씨 정보 업데이트"""
        if temp is not None:
            icon = "🌤️"
            if condition:
                condition_lower = condition.lower()
                if "rain" in condition_lower or "비" in condition:
                    icon = "🌧️"
                elif "cloud" in condition_lower or "흐림" in condition:
                    icon = "☁️"
                elif "snow" in condition_lower or "눈" in condition:
                    icon = "❄️"
                elif "sun" in condition_lower or "맑음" in condition:
                    icon = "☀️"

            text = f"{icon} {temp:.0f}°C"
            if humidity is not None:
                text += f" {humidity:.0f}%"
            self.weather_label.configure(text=text)

    def _show_today_alerts(self):
        """오늘 경고 내역 팝업"""
        try:
            alerts = []
            if hasattr(self.app, 'get_today_alerts_for'):
                alerts = self.app.get_today_alerts_for(self.sid_key)
        except Exception:
            alerts = []

        dialog = tk.Toplevel(self.app)
        dialog.title("오늘 경고 내역")
        dialog.geometry("700x550")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (550 // 2)
        dialog.geometry(f"700x550+{x}+{y}")

        title = tk.Label(dialog, text="오늘 경고 내역", font=("Pretendard", 18, "bold"),
                        bg="#F5F5F5", fg="#2C3E50")
        title.pack(pady=12)

        frame = tk.Frame(dialog, bg="#F5F5F5")
        frame.pack(fill="both", expand=True, padx=16, pady=8)

        from tkinter import ttk
        cols = ("시간", "ID", "센서", "레벨", "값")
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor='center')
        tree.pack(fill="both", expand=True)

        level_map = {1: "정상", 2: "관심", 3: "주의", 4: "경계", 5: "심각"}
        for a in alerts:
            ts = a.get('timestamp', '--')
            sid = a.get('sid', '--')
            sensor = a.get('sensor', '--')
            lvl = level_map.get(a.get('level', 1), '--')
            val = a.get('value', '--')
            tree.insert('', 'end', values=(ts, sid, sensor, lvl, val))

        tk.Button(dialog, text="닫기", command=dialog.destroy,
                 font=("Pretendard", 12, "bold"), bg="#3498DB", fg="#FFFFFF",
                 width=10).pack(pady=12)

    def _update_button_states(self):
        """버튼 상태 업데이트"""
        pass

    def update_mode_buttons(self, current_mode):
        """모드 버튼 상태 업데이트"""
        # 모든 버튼을 기본 상태로
        self.btn_card.configure(bg="#90A4AE", relief="raised")
        self.btn_all_sensors.configure(bg="#90A4AE", relief="raised")
        self.btn_blueprint.configure(bg="#90A4AE", relief="raised")

        # 센서전체보기 버튼 활성화/비활성화 (센서 2개 이상일 때만 활성화)
        self._update_all_sensors_button_state()

        # 현재 모드 버튼 활성화
        if current_mode == "card":
            self.btn_card.configure(bg="#4CAF50", relief="sunken")
            if self.mirror_camera_ready:
                self.mirror_btn.configure(state="normal")
        elif current_mode == "all_sensors":
            self.btn_all_sensors.configure(bg="#2196F3", relief="sunken")
            self.mirror_btn.configure(state="disabled")
        elif current_mode == "blueprint":
            self.btn_blueprint.configure(bg="#4CAF50", relief="sunken")
            self.mirror_btn.configure(state="disabled")

    def _update_all_sensors_button_state(self):
        """센서전체보기 버튼 활성화/비활성화 상태 업데이트"""
        try:
            # 접속된 센서 수 확인 (대기 탭 제외)
            connected_count = len([k for k in self.app.panels.keys() if k != "__waiting__"])
            if connected_count >= 2:
                self.btn_all_sensors.configure(state="normal")
            else:
                self.btn_all_sensors.configure(state="disabled")
        except Exception:
            self.btn_all_sensors.configure(state="disabled")

    def update_admin_mode_indicator(self):
        """관리자 모드 표시 업데이트"""
        if self.app.cfg.admin_mode:
            self.mode_toggle_btn.configure(text="🔓관리자", bg="#FFD700", fg="#D32F2F")
        else:
            self.mode_toggle_btn.configure(text="🔒일반", bg="#3498DB", fg="#FFFFFF")

    def _on_mode_toggle_click(self):
        """모드 전환 버튼 클릭"""
        if self.app.cfg.admin_mode:
            self._show_exit_admin_dialog()
        else:
            self.app.enter_admin_mode()

    def _show_exit_admin_dialog(self):
        """관리자 모드 종료 확인"""
        dialog = tk.Toplevel(self.app)
        dialog.title("일반 모드 전환")
        dialog.geometry("400x200")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 200) // 2
        dialog.geometry(f"400x200+{x}+{y}")

        tk.Label(dialog, text="일반 모드로 전환하시겠습니까?",
                font=("Pretendard", 14, "bold"), bg="#F5F5F5").pack(pady=30)

        btn_frame = tk.Frame(dialog, bg="#F5F5F5")
        btn_frame.pack(pady=20)

        def confirm():
            self.app.cfg.admin_mode = False
            self.update_admin_mode_indicator()
            dialog.destroy()

        tk.Button(btn_frame, text="확인", command=confirm,
                 font=("Pretendard", 12, "bold"), bg="#27AE60", fg="#FFFFFF",
                 width=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="취소", command=dialog.destroy,
                 font=("Pretendard", 12, "bold"), bg="#95A5A6", fg="#FFFFFF",
                 width=10).pack(side="left", padx=10)

    def _toggle_voice_alert(self):
        """음성 경보 토글"""
        self.voice_alert_enabled = not self.voice_alert_enabled
        self.app.global_voice_alert_enabled = self.voice_alert_enabled

        if self.voice_alert_enabled:
            self.voice_toggle_btn.configure(text="🔊")
        else:
            self.voice_toggle_btn.configure(text="🔇")

        # 다른 패널 동기화
        try:
            if hasattr(self.app, 'sync_voice_alert_state'):
                self.app.sync_voice_alert_state(self.voice_alert_enabled)
        except Exception:
            pass

    def _toggle_mirror_view(self):
        """안전안전점검 토글"""
        if self.mirror_mode:
            self.master_panel.hide_mirror_view()
            self.mirror_mode = False
            self.mirror_btn.configure(text="안전점검", bg="#9C27B0")
        else:
            self.master_panel.show_mirror_view()
            self.mirror_mode = True
            self.mirror_btn.configure(text="점검종료", bg="#F44336")

    def set_mirror_camera_ready(self, ready):
        """카메라 준비 상태 설정"""
        self.mirror_camera_ready = ready
        if ready:
            self.mirror_btn.configure(state="normal", text="안전점검")
        else:
            self.mirror_btn.configure(state="disabled", text="안전점검")

    def _capture_current_screen(self):
        """화면 캡쳐"""
        try:
            if hasattr(self.master_panel, 'capture_current_screen'):
                self.master_panel.capture_current_screen()
        except Exception as e:
            print(f"캡쳐 오류: {e}")

    def set_connection_status(self, status):
        """연결 상태 설정"""
        self._connection_status = status

    def update_comfort_indices(self, temp, hum):
        """체감온도/불쾌지수 업데이트"""
        self._latest_temp = temp
        self._latest_hum = hum

        if temp is not None and hum is not None:
            try:
                hi = heat_index_c(temp, hum)
                di = discomfort_index(temp, hum)

                # 체감온도 표시
                hi_text = f"체감온도 HI: {hi:.1f}°C"
                self.hi_label.configure(text=hi_text)

                # 불쾌지수 표시 및 색상 (시인성 개선)
                di_text = f"불쾌지수 DI: {di:.1f}"
                if di >= 80:
                    di_color = "#FFFFFF"  # 흰색 글자
                    di_bg = "#E74C3C"     # 빨간 배경
                elif di >= 75:
                    di_color = "#FFFFFF"  # 흰색 글자
                    di_bg = "#E67E22"     # 주황 배경
                elif di >= 68:
                    di_color = "#2C3E50"  # 어두운 글자
                    di_bg = "#F1C40F"     # 노란 배경
                else:
                    di_color = "#FFFFFF"  # 흰색 글자
                    di_bg = "#27AE60"     # 초록 배경

                self.di_label.configure(text=di_text, fg=di_color, bg=di_bg)
            except Exception:
                pass

    def _show_hi_tooltip(self, event=None):
        """체감온도 툴팁"""
        pass

    def _on_hi_enter(self, event=None):
        pass

    def _on_hi_leave(self, event=None):
        pass

    def _on_di_click(self, event=None):
        """불쾌지수 클릭 (10번 클릭 시 종료 확인)"""
        self._di_click_count += 1
        if self._di_click_count >= 10:
            self._di_click_count = 0
            self._show_exit_confirm_dialog()
        else:
            if self._di_click_reset_timer:
                self.after_cancel(self._di_click_reset_timer)
            self._di_click_reset_timer = self.after(2000, self._reset_di_click)

    def _show_exit_confirm_dialog(self):
        """종료 확인 다이얼로그"""
        dialog = tk.Toplevel(self.app)
        dialog.title("프로그램 종료")
        dialog.geometry("350x150")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 350) // 2
        y = (dialog.winfo_screenheight() - 150) // 2
        dialog.geometry(f"350x150+{x}+{y}")

        tk.Label(dialog, text="프로그램을 종료하시겠습니까?",
                font=("Pretendard", 14, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=25)

        btn_frame = tk.Frame(dialog, bg="#F5F5F5")
        btn_frame.pack(pady=15)

        def confirm_exit():
            dialog.destroy()
            try:
                self.app.quit()
                self.app.destroy()
            except:
                pass

        tk.Button(btn_frame, text="종료", command=confirm_exit,
                 font=("Pretendard", 12, "bold"), bg="#E74C3C", fg="#FFFFFF",
                 width=8).pack(side="left", padx=10)
        tk.Button(btn_frame, text="취소", command=dialog.destroy,
                 font=("Pretendard", 12, "bold"), bg="#95A5A6", fg="#FFFFFF",
                 width=8).pack(side="left", padx=10)

        # 다이얼로그가 표시된 후 grab_set 호출
        dialog.after(100, lambda: self._safe_grab_set(dialog))

    def _safe_grab_set(self, dialog):
        """안전하게 grab_set 호출"""
        try:
            if dialog.winfo_exists() and dialog.winfo_viewable():
                dialog.grab_set()
        except Exception:
            pass

    def _reset_di_click(self):
        self._di_click_count = 0

    def _on_di_enter(self, event=None):
        pass

    def _on_di_leave(self, event=None):
        pass

    def update_temperature(self, value_str):
        """온도 업데이트 (하위 호환성) - 체감온도/불쾌지수 업데이트에 사용"""
        try:
            temp = float(value_str)
            self._latest_temp = temp
            if self._latest_hum is not None:
                self.update_comfort_indices(temp, self._latest_hum)
        except (ValueError, TypeError):
            pass

    def update_humidity(self, value_str):
        """습도 업데이트 (하위 호환성) - 체감온도/불쾌지수 업데이트에 사용"""
        try:
            hum = float(value_str)
            self._latest_hum = hum
            if self._latest_temp is not None:
                self.update_comfort_indices(self._latest_temp, hum)
        except (ValueError, TypeError):
            pass
