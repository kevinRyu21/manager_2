"""
패널 오버레이 UI 컴포넌트

상세 그래프/표 오버레이를 관리합니다.
"""

import tkinter as tk
from tkinter import ttk
import datetime
from .panel_graph import GraphRenderer


class PanelOverlay:
    """상세 오버레이 - 그래프/표 토글"""

    def __init__(self, parent_frame, log_manager, sid, peer, on_close):
        self.parent_frame = parent_frame
        self.log_manager = log_manager
        self.sid = sid
        self.peer = peer
        self.on_close = on_close

        # 오버레이 프레임
        self.overlay = tk.Frame(parent_frame, bg="#1A1A1A")
        self.overlay.place_forget()

        # 상단 컨트롤
        control_frame = ttk.Frame(self.overlay)
        control_frame.pack(side="top", fill="x", pady=5)

        self.overlay_title = tk.Label(control_frame, text="", fg="#FFFFFF", bg="#1A1A1A", font=("Pretendard", 18, "bold"))
        self.overlay_title.pack(side="left", padx=10)

        # 왼쪽 버튼들
        left_buttons = ttk.Frame(control_frame)
        left_buttons.pack(side="left", padx=15)

        self.overlay_toggle = tk.Button(left_buttons, text="그래프", command=self._toggle_overlay_mode,
                                       bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                                       relief="raised", bd=2, width=12, height=1,
                                       activebackground="#2980B9", activeforeground="#FFFFFF")
        self.overlay_toggle.pack(side="left", padx=5)

        self.time_range_btn = tk.Button(left_buttons, text="최근 1시간", command=self._toggle_time_range,
                                       bg="#9B59B6", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                                       relief="raised", bd=2, width=12, height=1,
                                       activebackground="#8E44AD", activeforeground="#FFFFFF")
        self.time_range_btn.pack(side="left", padx=5)

        # 로딩 표시 라벨 (초기에는 숨김)
        self.loading_label = tk.Label(control_frame, text="", bg="#1A1A1A", fg="#FFD700",
                                     font=("Pretendard", 11, "bold"))
        # pack하지 않음 - 필요할 때만 표시

        # 오른쪽 닫기 버튼
        tk.Button(control_frame, text="✕ 닫기", command=self._hide_overlay,
                 bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                 relief="raised", bd=2, width=10, height=1,
                 activebackground="#C0392B", activeforeground="#FFFFFF").pack(side="right", padx=15)

        # 표시 모드
        self._display_mode = "graph"
        self._current_time_range_index = 0
        self._detail_key = None

        # 그래프 컨테이너
        self.graph_container = ttk.Frame(self.overlay)
        self.overlay_canvas = tk.Canvas(self.graph_container, bg="#0F0F0F", highlightthickness=0)

        # 표 컨테이너
        self.table_container = ttk.Frame(self.overlay)
        self.overlay_table = tk.Text(self.table_container, bg="#2A2A2A", fg="#FFFFFF", font=("Pretendard", 11))
        self.overlay_table.pack(fill="both", expand=True)

        # 그래프 렌더러
        self.graph_renderer = GraphRenderer(self.graph_container, self.overlay_canvas, log_manager, sid, peer)

        # 바인딩
        self.overlay.bind("<Map>", lambda e: self._render_overlay())
        self.overlay.bind("<Configure>", lambda e: self._on_configure())

    def _on_configure(self):
        """Configure 이벤트 핸들러"""
        # Configure 이벤트는 연속으로 발생하므로 디바운싱 적용
        if not hasattr(self, '_configure_timer'):
            self._configure_timer = None

        # 기존 타이머 취소
        if self._configure_timer:
            self.overlay.after_cancel(self._configure_timer)

        # 100ms 후에 실행 (디바운싱)
        def do_configure():
            self._configure_timer = None
            if self._detail_key and self._display_mode in ("graph", "both"):
                self.graph_renderer.draw_graph(self._detail_key, force=True)

        self._configure_timer = self.overlay.after(100, do_configure)

    def show(self, key):
        """오버레이 표시"""
        self._detail_key = key
        self._render_overlay()

    def hide(self):
        """오버레이 숨기기"""
        self._detail_key = None
        self.graph_renderer.cleanup()
        self.overlay.place_forget()
        self.on_close()

    def _hide_overlay(self):
        """오버레이 숨기기 (버튼 클릭)"""
        # 비동기로 닫기 처리 (즉각 반응)
        self.overlay.after_idle(self.hide)

    def _render_overlay(self):
        """오버레이 렌더링"""
        if not self._detail_key:
            self.overlay.place_forget()
            return

        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        title_map = {
            "co2": "CO₂", "h2s": "H₂S", "co": "CO",
            "o2": "O₂", "temperature": "온도", "humidity": "습도"
        }

        # 시간 범위 초기화
        self._current_time_range_index = 0
        self.graph_renderer.set_time_range_index(0)
        self.time_range_btn.configure(text="최근 1시간")
        self.overlay_title.configure(text=f"{title_map.get(self._detail_key, self._detail_key)} 최근 1시간")

        # 초기화
        self.graph_container.pack_forget()
        self.table_container.pack_forget()
        self.graph_renderer.cleanup()

        # 로딩 표시
        self._show_loading("그래프 로딩 중...")

        # 초기 모드는 그래프
        self._display_mode = "graph"
        self.overlay_toggle.configure(text="그래프")
        self.graph_container.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.overlay_canvas.pack(fill="both", expand=True)

        # 그래프를 지연 렌더링 (로딩 표시가 먼저 보이도록)
        self.overlay.after(10, lambda: self._draw_graph_with_loading(self._detail_key))

    def _show_loading(self, text):
        """로딩 표시"""
        self.loading_label.configure(text=text)
        self.loading_label.pack(side="left", padx=10)

    def _hide_loading(self):
        """로딩 숨기기"""
        self.loading_label.pack_forget()
        self.loading_label.configure(text="")

    def _toggle_overlay_mode(self):
        """표/그래프 토글"""
        # 로딩 표시
        self._show_loading("로딩 중...")

        # 비동기 처리로 UI 블로킹 방지
        def do_toggle():
            self.graph_container.pack_forget()
            self.table_container.pack_forget()

            # cleanup은 필요 없음 (그래프 객체 재사용)

            if self._display_mode == "graph":
                self._display_mode = "table"
                self.overlay_toggle.configure(text="표")
                self.table_container.pack(side="top", fill="both", expand=True, padx=10, pady=10)
                self.overlay.after(10, lambda: self._fill_table_with_loading(self._detail_key))

            elif self._display_mode == "table":
                self._display_mode = "both"
                self.overlay_toggle.configure(text="그래프+표")
                self.graph_container.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 5))
                self.graph_container.pack_propagate(False)
                self.graph_container.configure(height=350)
                self.overlay_canvas.pack(fill="both", expand=True)
                self.table_container.pack(side="top", fill="both", expand=True, padx=10, pady=(5, 10))
                self.overlay_table.configure(height=12)
                # 그래프와 표를 순차적으로 지연 렌더링
                self.overlay.after(10, lambda: self._draw_graph_with_loading(self._detail_key))
                self.overlay.after(50, lambda: self._fill_table_with_loading(self._detail_key))

            else:
                self._display_mode = "graph"
                self.overlay_toggle.configure(text="그래프")
                self.graph_container.pack(side="top", fill="both", expand=True, padx=10, pady=10)
                self.graph_container.pack_propagate(True)
                self.graph_container.configure(height=0)
                self.overlay_canvas.pack(fill="both", expand=True)
                self.overlay_table.configure(height=0)
                self.overlay.after(10, lambda: self._draw_graph_with_loading(self._detail_key))

        # after_idle로 UI 스레드가 준비된 후 실행
        self.overlay.after_idle(do_toggle)

    def _toggle_time_range(self):
        """시간 범위 토글"""
        # 로딩 표시
        self._show_loading("데이터 로딩 중...")

        # 비동기 처리로 UI 블로킹 방지
        def do_toggle_range():
            self._current_time_range_index = (self._current_time_range_index + 1) % 4
            self.graph_renderer.set_time_range_index(self._current_time_range_index)

            hours = self.graph_renderer.get_time_range_hours()

            if hours == 1:
                self.time_range_btn.configure(text="최근 1시간")
            elif hours == 24:
                self.time_range_btn.configure(text="최근 24시간")
            elif hours == 168:
                self.time_range_btn.configure(text="최근 7일")
            elif hours == 720:
                self.time_range_btn.configure(text="최근 1달")

            title_map = {
                "co2": "CO₂", "h2s": "H₂S", "co": "CO",
                "o2": "O₂", "temperature": "온도", "humidity": "습도"
            }
            time_text = self.time_range_btn.cget("text")
            self.overlay_title.configure(text=f"{title_map.get(self._detail_key, self._detail_key)} {time_text}")

            # 그래프와 표를 지연 렌더링
            if self._display_mode in ("graph", "both"):
                self.overlay.after(10, lambda: self._draw_graph_with_loading(self._detail_key))
            if self._display_mode in ("table", "both"):
                self.overlay.after(50, lambda: self._fill_table_with_loading(self._detail_key))

        # after_idle로 UI 스레드가 준비된 후 실행
        self.overlay.after_idle(do_toggle_range)

    def _draw_graph_with_loading(self, key):
        """그래프 그리기 with 로딩 표시"""
        try:
            self.graph_renderer.draw_graph(key, force=True)
        finally:
            self._hide_loading()

    def _fill_table_with_loading(self, key):
        """표 채우기 with 로딩 표시"""
        try:
            self._fill_table(key)
        finally:
            self._hide_loading()

    def _fill_table(self, key):
        """테이블 데이터 채우기"""
        # 상태 변경을 일시적으로 비활성화 (성능 향상)
        self.overlay_table.config(state='normal')
        self.overlay_table.delete("1.0", tk.END)

        hours = self.graph_renderer.get_time_range_hours()
        data = self.log_manager.get_sensor_data_for_hours(self.sid, self.peer, key, hours)

        if not data:
            self.overlay_table.insert(tk.END, "데이터 없음\n")
            return

        # 배치 처리를 위한 텍스트 빌더
        lines = []

        # 오늘 통계 계산 (LogManager에서)
        today_stats = self.log_manager.get_today_stats(self.sid, self.peer, key)
        if today_stats:
            max_val = today_stats["max"]
            min_val = today_stats["min"]
            avg_val = today_stats["avg"]
            count = today_stats["count"]

            lines.append("=" * 50)
            lines.append(f"오늘 통계 (총 {count}개 데이터)")
            lines.append("-" * 50)
            lines.append(f"최대값: {max_val:.2f}")
            lines.append(f"평균값: {avg_val:.2f}")
            lines.append(f"최소값: {min_val:.2f}")
            lines.append("=" * 50)
            lines.append("")

        time_text = self.graph_renderer._get_time_text(hours)
        lines.append(f"{time_text} 데이터")
        lines.append("-" * 50)
        lines.append(f"{'시각':<20} {'값':>10}")
        lines.append("-" * 50)

        # 최근 100개만 표시
        for ts, v in data[-100:][::-1]:
            if hours <= 24:
                time_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            lines.append(f"{time_str:<20} {v:>10.2f}")

        # 배치 삽입 (한 번에 삽입하여 성능 향상)
        full_text = "\n".join(lines)
        self.overlay_table.insert(tk.END, full_text)

        # 태그 설정 (통계 부분만)
        if today_stats:
            self.overlay_table.tag_add("max", "4.0", "4.end")
            self.overlay_table.tag_add("avg", "5.0", "5.end")
            self.overlay_table.tag_add("min", "6.0", "6.end")
            self.overlay_table.tag_config("max", foreground="#FF6B6B")
            self.overlay_table.tag_config("avg", foreground="#FFD700")
            self.overlay_table.tag_config("min", foreground="#4ECDC4")

    def update(self):
        """업데이트"""
        if self._detail_key:
            if self._display_mode in ("table", "both"):
                self._fill_table(self._detail_key)
            if self._display_mode in ("graph", "both"):
                self.graph_renderer.draw_graph(self._detail_key)
