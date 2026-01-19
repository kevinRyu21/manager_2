"""
화재 경보 패널 UI 컴포넌트

화재 감지 시스템의 상태와 경보를 표시하는 좌측 사이드바 패널입니다.
5단계 화재 경보 레벨을 시각적으로 표시합니다.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional, Dict, List, Any

# 화재 감지 모듈 임포트
try:
    from ..fire import (
        FireAlertLevel,
        FireDetectionResult,
        SensorReading,
        FIRE_PROBABILITY_THRESHOLDS
    )
    FIRE_MODULE_AVAILABLE = True
except ImportError:
    FIRE_MODULE_AVAILABLE = False
    FireAlertLevel = None
    FireDetectionResult = None


class FireAlertPanel(tk.Frame):
    """화재 경보 표시 패널 - 좌측 사이드바용"""

    # 5단계 경보 색상 (화재 모듈과 동일)
    ALERT_COLORS = {
        1: "#27AE60",  # 정상 - 녹색
        2: "#F1C40F",  # 관심 - 노랑
        3: "#E67E22",  # 주의 - 주황
        4: "#E74C3C",  # 경계 - 빨강
        5: "#8E44AD",  # 위험 - 보라
    }

    ALERT_NAMES = {
        1: "정상",
        2: "관심",
        3: "주의",
        4: "경계",
        5: "위험",
    }

    ALERT_ICONS = {
        1: "🟢",
        2: "🟡",
        3: "🟠",
        4: "🔴",
        5: "🟣",
    }

    def __init__(self, master, app, width=280):
        super().__init__(master, bg="#1A1A2E", width=width)
        self.app = app
        self.panel_width = width

        # 상태 변수
        self._current_level = 1  # 현재 경보 레벨
        self._fire_probability = 0.0  # 화재 확률
        self._triggered_sensors = []  # 경보 발생 센서 목록
        self._last_update = None  # 마지막 업데이트 시간
        self._detection_result = None  # 화재 감지 결과

        # 고정 너비 유지
        self.pack_propagate(False)
        self.configure(width=width)

        self._build_ui()

    def _build_ui(self):
        """UI 구성"""
        # 상단: 제목
        title_frame = tk.Frame(self, bg="#16213E")
        title_frame.pack(fill="x", padx=5, pady=5)

        title_label = tk.Label(
            title_frame,
            text="🔥 화재 감시",
            font=("Pretendard", 16, "bold"),
            bg="#16213E",
            fg="#FFFFFF"
        )
        title_label.pack(pady=10)

        # 경보 레벨 표시 영역
        self.level_frame = tk.Frame(self, bg="#1A1A2E")
        self.level_frame.pack(fill="x", padx=10, pady=10)

        # 경보 아이콘
        self.level_icon_label = tk.Label(
            self.level_frame,
            text="🟢",
            font=("Pretendard", 48),
            bg="#1A1A2E",
            fg="#FFFFFF"
        )
        self.level_icon_label.pack(pady=5)

        # 경보 레벨 텍스트
        self.level_text_label = tk.Label(
            self.level_frame,
            text="정상",
            font=("Pretendard", 24, "bold"),
            bg="#1A1A2E",
            fg="#27AE60"
        )
        self.level_text_label.pack(pady=5)

        # 화재 확률 표시
        self.probability_frame = tk.Frame(self, bg="#0F3460")
        self.probability_frame.pack(fill="x", padx=10, pady=5)

        prob_title = tk.Label(
            self.probability_frame,
            text="화재 확률",
            font=("Pretendard", 12),
            bg="#0F3460",
            fg="#94A3B8"
        )
        prob_title.pack(pady=(5, 0))

        self.probability_label = tk.Label(
            self.probability_frame,
            text="0.0%",
            font=("Pretendard", 28, "bold"),
            bg="#0F3460",
            fg="#27AE60"
        )
        self.probability_label.pack(pady=5)

        # 프로그레스 바 (화재 확률)
        self.progress_canvas = tk.Canvas(
            self.probability_frame,
            width=self.panel_width - 40,
            height=20,
            bg="#1A1A2E",
            highlightthickness=0
        )
        self.progress_canvas.pack(pady=(0, 10))
        self._draw_progress_bar(0.0)

        # 구분선
        separator = tk.Frame(self, bg="#333333", height=2)
        separator.pack(fill="x", padx=10, pady=10)

        # AI 학습 상태 영역
        ai_title = tk.Label(
            self,
            text="🤖 AI 학습 통계",
            font=("Pretendard", 14, "bold"),
            bg="#1A1A2E",
            fg="#FFFFFF"
        )
        ai_title.pack(pady=(5, 5))

        # 학습 단계 표시
        self.learning_phase_frame = tk.Frame(self, bg="#16213E")
        self.learning_phase_frame.pack(fill="x", padx=10, pady=5)

        self.learning_phase_label = tk.Label(
            self.learning_phase_frame,
            text="단계: 대기중 | 샘플: 0",
            font=("Pretendard", 10),
            bg="#16213E",
            fg="#94A3B8"
        )
        self.learning_phase_label.pack(pady=3)

        self.learning_progress_label = tk.Label(
            self.learning_phase_frame,
            text="진행: 0일 / 30일",
            font=("Pretendard", 10),
            bg="#16213E",
            fg="#94A3B8"
        )
        self.learning_progress_label.pack(pady=3)

        # 센서별 학습 통계 리스트 (스크롤 가능)
        self.sensor_stats_frame = tk.Frame(self, bg="#1A1A2E")
        self.sensor_stats_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Canvas + Scrollbar for scrollable area
        self.stats_canvas = tk.Canvas(self.sensor_stats_frame, bg="#1A1A2E", highlightthickness=0)
        self.stats_scrollbar = tk.Scrollbar(self.sensor_stats_frame, orient="vertical", command=self.stats_canvas.yview)
        self.stats_inner_frame = tk.Frame(self.stats_canvas, bg="#1A1A2E")

        self.stats_canvas.configure(yscrollcommand=self.stats_scrollbar.set)

        self.stats_scrollbar.pack(side="right", fill="y")
        self.stats_canvas.pack(side="left", fill="both", expand=True)

        self.stats_canvas_window = self.stats_canvas.create_window((0, 0), window=self.stats_inner_frame, anchor="nw")

        self.stats_inner_frame.bind("<Configure>", self._on_stats_frame_configure)
        self.stats_canvas.bind("<Configure>", self._on_canvas_configure)

        # 마우스 휠 스크롤 바인딩
        self.stats_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.stats_canvas.bind("<Button-4>", self._on_mousewheel)
        self.stats_canvas.bind("<Button-5>", self._on_mousewheel)

        # 센서 학습 통계 저장용
        self._sensor_stat_widgets = {}

        # 하단: 마지막 업데이트 시간
        self.update_time_label = tk.Label(
            self,
            text="최종 갱신: --:--:--",
            font=("Pretendard", 10),
            bg="#1A1A2E",
            fg="#666666"
        )
        self.update_time_label.pack(side="bottom", pady=5)

    def _on_stats_frame_configure(self, event):
        """스크롤 영역 크기 업데이트"""
        self.stats_canvas.configure(scrollregion=self.stats_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """캔버스 크기에 맞춰 내부 프레임 너비 조정"""
        self.stats_canvas.itemconfig(self.stats_canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤"""
        if event.delta:
            self.stats_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.stats_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.stats_canvas.yview_scroll(1, "units")

    def _create_sensor_stats_widget(self, sensor_id: str):
        """센서별 학습 통계 위젯 생성"""
        # 센서 프레임
        sensor_frame = tk.LabelFrame(
            self.stats_inner_frame,
            text=f"📡 {sensor_id}",
            font=("Pretendard", 10, "bold"),
            bg="#0F3460",
            fg="#FFD700",
            relief="groove",
            bd=2
        )
        sensor_frame.pack(fill="x", padx=5, pady=3)

        # 가스 센서 타입 정의
        sensor_types = [
            ("temperature", "온도", "℃"),
            ("humidity", "습도", "%"),
            ("co", "CO", "ppm"),
            ("co2", "CO₂", "ppm"),
            ("o2", "O₂", "%"),
            ("smoke", "연기", ""),
        ]

        stat_labels = {}

        for key, name, unit in sensor_types:
            row = tk.Frame(sensor_frame, bg="#0F3460")
            row.pack(fill="x", padx=3, pady=1)

            # 센서 이름
            name_label = tk.Label(
                row,
                text=f"{name}:",
                font=("Pretendard", 9),
                bg="#0F3460",
                fg="#FFFFFF",
                width=5,
                anchor="w"
            )
            name_label.pack(side="left")

            # 학습 통계 (평균±표준편차)
            stat_label = tk.Label(
                row,
                text="--",
                font=("Pretendard", 9, "bold"),
                bg="#0F3460",
                fg="#27AE60",
                anchor="e"
            )
            stat_label.pack(side="right", padx=2)

            # 샘플 수
            sample_label = tk.Label(
                row,
                text="(n=0)",
                font=("Pretendard", 8),
                bg="#0F3460",
                fg="#666666",
                anchor="e"
            )
            sample_label.pack(side="right", padx=2)

            stat_labels[key] = {
                "stat": stat_label,
                "sample": sample_label,
                "unit": unit
            }

        self._sensor_stat_widgets[sensor_id] = {
            "frame": sensor_frame,
            "labels": stat_labels
        }

        return sensor_frame

    def _update_sensor_stats_widget(self, sensor_id: str, stats: Dict[str, Dict]):
        """센서별 학습 통계 위젯 업데이트"""
        if sensor_id not in self._sensor_stat_widgets:
            self._create_sensor_stats_widget(sensor_id)

        widget = self._sensor_stat_widgets[sensor_id]
        labels = widget["labels"]

        for key, data in stats.items():
            if key in labels:
                n = data.get('n', 0)
                mean = data.get('mean', 0)
                std = data.get('std', 0)
                unit = labels[key]["unit"]

                # 샘플 수에 따라 색상 변경
                if n == 0:
                    color = "#666666"
                    stat_text = "--"
                elif n < 100:
                    color = "#F1C40F"  # 노랑 - 학습 중
                    stat_text = f"{mean:.1f}±{std:.1f}"
                else:
                    color = "#27AE60"  # 녹색 - 충분한 데이터
                    stat_text = f"{mean:.1f}±{std:.1f}"

                labels[key]["stat"].configure(text=stat_text, fg=color)
                labels[key]["sample"].configure(text=f"(n={n})")

    def update_learning_stats(self, learning_summary: Dict):
        """AI 학습 통계 업데이트"""
        if not learning_summary:
            return

        # 학습 단계 업데이트
        phase_korean = learning_summary.get('phase_korean', '대기중')
        total_samples = learning_summary.get('total_samples', 0)
        days_elapsed = learning_summary.get('days_elapsed', 0)
        target_days = learning_summary.get('target_days', 30)

        # 학습 단계에 따른 색상
        phase_colors = {
            '초기화': '#E74C3C',
            '준비중': '#F1C40F',
            '학습중': '#3498DB',
            '적응완료': '#27AE60'
        }
        phase_color = phase_colors.get(phase_korean, '#94A3B8')

        self.learning_phase_label.configure(
            text=f"단계: {phase_korean} | 샘플: {total_samples:,}",
            fg=phase_color
        )
        self.learning_progress_label.configure(
            text=f"진행: {days_elapsed}일 / {target_days}일"
        )

        # 센서별 통계 업데이트
        sensors = learning_summary.get('sensors', {})

        # 기존에 없는 센서 위젯 제거
        existing_sensors = set(self._sensor_stat_widgets.keys())
        new_sensors = set(sensors.keys())

        for old_sensor in existing_sensors - new_sensors:
            if old_sensor in self._sensor_stat_widgets:
                self._sensor_stat_widgets[old_sensor]["frame"].destroy()
                del self._sensor_stat_widgets[old_sensor]

        # 센서별 통계 업데이트
        for sensor_id, sensor_stats in sensors.items():
            self._update_sensor_stats_widget(sensor_id, sensor_stats)

    def _draw_progress_bar(self, probability: float):
        """화재 확률 프로그레스 바 그리기"""
        self.progress_canvas.delete("all")

        width = self.panel_width - 40
        height = 20

        # 배경
        self.progress_canvas.create_rectangle(
            0, 0, width, height,
            fill="#333333",
            outline=""
        )

        # 프로그레스
        if probability > 0:
            # 확률에 따른 색상
            if probability < 0.2:
                color = self.ALERT_COLORS[1]
            elif probability < 0.4:
                color = self.ALERT_COLORS[2]
            elif probability < 0.6:
                color = self.ALERT_COLORS[3]
            elif probability < 0.8:
                color = self.ALERT_COLORS[4]
            else:
                color = self.ALERT_COLORS[5]

            prog_width = int(width * min(probability, 1.0))
            self.progress_canvas.create_rectangle(
                0, 0, prog_width, height,
                fill=color,
                outline=""
            )

        # 경계선 (5단계 구분)
        for i in range(1, 5):
            x = int(width * (i * 0.2))
            self.progress_canvas.create_line(
                x, 0, x, height,
                fill="#666666",
                width=1
            )

    def update_fire_status(
        self,
        level: int = 1,
        probability: float = 0.0,
        triggered_sensors: List[str] = None,
        sensor_values: Dict[str, float] = None,
        detection_result: Any = None
    ):
        """화재 상태 업데이트"""
        self._current_level = level
        self._fire_probability = probability
        self._triggered_sensors = triggered_sensors or []
        self._detection_result = detection_result
        self._last_update = datetime.now()

        # 경보 레벨 표시 업데이트
        icon = self.ALERT_ICONS.get(level, "🟢")
        name = self.ALERT_NAMES.get(level, "정상")
        color = self.ALERT_COLORS.get(level, "#27AE60")

        self.level_icon_label.configure(text=icon)
        self.level_text_label.configure(text=name, fg=color)

        # 화재 확률 업데이트
        self.probability_label.configure(
            text=f"{probability * 100:.1f}%",
            fg=color
        )
        self._draw_progress_bar(probability)

        # 업데이트 시간 표시
        self.update_time_label.configure(
            text=f"최종 갱신: {self._last_update.strftime('%H:%M:%S')}"
        )

        # 위험/경계 레벨이면 깜빡임 효과
        if level >= 4:
            self._start_blink_effect()
        else:
            self._stop_blink_effect()

    def _start_blink_effect(self):
        """경보 깜빡임 효과 시작"""
        if hasattr(self, '_blink_after_id'):
            return  # 이미 깜빡이는 중

        self._blink_state = True
        self._blink()

    def _blink(self):
        """깜빡임 애니메이션"""
        if self._current_level < 4:
            self._stop_blink_effect()
            return

        self._blink_state = not self._blink_state

        if self._blink_state:
            color = self.ALERT_COLORS.get(self._current_level, "#E74C3C")
            self.level_frame.configure(bg=color)
            self.level_icon_label.configure(bg=color)
            self.level_text_label.configure(bg=color)
        else:
            self.level_frame.configure(bg="#1A1A2E")
            self.level_icon_label.configure(bg="#1A1A2E")
            self.level_text_label.configure(bg="#1A1A2E")

        self._blink_after_id = self.after(500, self._blink)

    def _stop_blink_effect(self):
        """깜빡임 효과 중지"""
        if hasattr(self, '_blink_after_id'):
            self.after_cancel(self._blink_after_id)
            del self._blink_after_id

        # 원래 배경색으로 복원
        self.level_frame.configure(bg="#1A1A2E")
        self.level_icon_label.configure(bg="#1A1A2E")
        self.level_text_label.configure(bg="#1A1A2E")

    def get_current_level(self) -> int:
        """현재 경보 레벨 반환"""
        return self._current_level

    def get_fire_probability(self) -> float:
        """현재 화재 확률 반환"""
        return self._fire_probability
