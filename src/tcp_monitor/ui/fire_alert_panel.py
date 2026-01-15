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

        # 센서 상태 영역
        sensor_title = tk.Label(
            self,
            text="센서 상태",
            font=("Pretendard", 14, "bold"),
            bg="#1A1A2E",
            fg="#FFFFFF"
        )
        sensor_title.pack(pady=(5, 10))

        # 센서 상태 리스트
        self.sensor_list_frame = tk.Frame(self, bg="#1A1A2E")
        self.sensor_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 초기 센서 상태 표시
        self._sensor_labels = {}
        sensor_types = [
            ("temperature", "온도", "🌡️"),
            ("humidity", "습도", "💧"),
            ("co", "CO", "🔥"),
            ("co2", "CO2", "🏭"),
            ("o2", "O2", "💨"),
            ("smoke", "연기", "🌫️"),
        ]

        for key, name, icon in sensor_types:
            self._create_sensor_status_row(key, name, icon)

        # 하단: 마지막 업데이트 시간
        self.update_time_label = tk.Label(
            self,
            text="최종 갱신: --:--:--",
            font=("Pretendard", 10),
            bg="#1A1A2E",
            fg="#666666"
        )
        self.update_time_label.pack(side="bottom", pady=10)

        # AI 적응 상태 표시
        self.ai_status_frame = tk.Frame(self, bg="#16213E")
        self.ai_status_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.ai_status_label = tk.Label(
            self.ai_status_frame,
            text="🤖 AI 학습: 대기중",
            font=("Pretendard", 10),
            bg="#16213E",
            fg="#94A3B8"
        )
        self.ai_status_label.pack(pady=5)

    def _create_sensor_status_row(self, key: str, name: str, icon: str):
        """센서 상태 행 생성"""
        row = tk.Frame(self.sensor_list_frame, bg="#0F3460")
        row.pack(fill="x", pady=2)

        # 아이콘 + 이름
        left = tk.Frame(row, bg="#0F3460")
        left.pack(side="left", padx=5, pady=3)

        icon_label = tk.Label(
            left,
            text=icon,
            font=("Pretendard", 12),
            bg="#0F3460",
            fg="#FFFFFF"
        )
        icon_label.pack(side="left")

        name_label = tk.Label(
            left,
            text=name,
            font=("Pretendard", 11),
            bg="#0F3460",
            fg="#FFFFFF"
        )
        name_label.pack(side="left", padx=5)

        # 상태 표시
        status_label = tk.Label(
            row,
            text="--",
            font=("Pretendard", 11, "bold"),
            bg="#0F3460",
            fg="#27AE60"
        )
        status_label.pack(side="right", padx=10, pady=3)

        self._sensor_labels[key] = {
            "row": row,
            "status": status_label
        }

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

        # 센서 상태 업데이트
        if sensor_values:
            for key, value in sensor_values.items():
                if key in self._sensor_labels:
                    is_triggered = key in self._triggered_sensors
                    status_color = "#E74C3C" if is_triggered else "#27AE60"
                    status_text = f"{value:.1f}" if isinstance(value, float) else str(value)

                    self._sensor_labels[key]["status"].configure(
                        text=status_text,
                        fg=status_color
                    )

                    # 경보 발생 센서는 배경색 변경
                    row_bg = "#3D1C1C" if is_triggered else "#0F3460"
                    self._sensor_labels[key]["row"].configure(bg=row_bg)
                    for child in self._sensor_labels[key]["row"].winfo_children():
                        if isinstance(child, tk.Frame):
                            child.configure(bg=row_bg)
                            for subchild in child.winfo_children():
                                subchild.configure(bg=row_bg)
                        else:
                            try:
                                child.configure(bg=row_bg)
                            except:
                                pass

        # 업데이트 시간 표시
        self.update_time_label.configure(
            text=f"최종 갱신: {self._last_update.strftime('%H:%M:%S')}"
        )

        # 위험/경계 레벨이면 깜빡임 효과
        if level >= 4:
            self._start_blink_effect()
        else:
            self._stop_blink_effect()

    def update_ai_status(self, status_text: str):
        """AI 학습 상태 업데이트"""
        self.ai_status_label.configure(text=f"🤖 {status_text}")

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
