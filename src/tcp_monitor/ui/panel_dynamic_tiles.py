"""
동적 타일 그리드 UI 컴포넌트

접속된 센서 수에 따라 자동으로 그리드 레이아웃을 조정합니다.
- 1개: 1x1
- 2개: 1x2
- 3-4개: 2x2
- 5-6개: 2x3
- 7-9개: 3x3
- 10-12개: 3x4
- 13-16개: 4x4
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple
import math

from ..utils.helpers import SENSOR_KEYS, COLOR_TILE_OK, COLOR_ALARM, ideal_fg, fmt_ts


class DynamicTileGrid(ttk.Frame):
    """동적 센서 타일 그리드"""

    # 5단계 경보 색상
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
        5: "심각",
    }

    def __init__(self, master, app, on_tile_click):
        super().__init__(master)
        self.app = app
        self.on_tile_click = on_tile_click
        self.tiles = {}
        self._connection_status = "waiting"
        self._active_sensors = []  # 활성화된 센서 목록
        self._grid_rows = 3
        self._grid_cols = 3

        # 센서 정보 (key, 이름, 단위, 아이콘)
        self.sensor_info = {
            "co2": ("이산화탄소", "ppm", "🏭"),
            "o2": ("산소", "%", "💨"),
            "h2s": ("황화수소", "ppm", "☠️"),
            "co": ("일산화탄소", "ppm", "🔥"),
            "lel": ("가연성가스", "%", "⚡"),
            "smoke": ("연기", "ppm", "🌫️"),
            "temperature": ("온도", "℃", "🌡️"),
            "humidity": ("습도", "%", "💧"),
            "water": ("누수", "", "🚿"),
        }

        # 초기 그리드 생성 (기본 9개)
        self._build_grid(SENSOR_KEYS)

    def _calculate_grid_size(self, sensor_count: int) -> Tuple[int, int]:
        """센서 수에 따른 최적 그리드 크기 계산"""
        if sensor_count <= 1:
            return (1, 1)
        elif sensor_count == 2:
            return (1, 2)
        elif sensor_count <= 4:
            return (2, 2)
        elif sensor_count <= 6:
            return (2, 3)
        elif sensor_count <= 9:
            return (3, 3)
        elif sensor_count <= 12:
            return (3, 4)
        else:
            return (4, 4)

    def update_active_sensors(self, active_sensors: List[str]):
        """활성 센서 목록 업데이트 및 그리드 재구성"""
        # 이미 동일한 구성이면 스킵
        if set(active_sensors) == set(self._active_sensors):
            return

        self._active_sensors = active_sensors
        self._rebuild_grid()

    def _rebuild_grid(self):
        """그리드 재구성"""
        sensors = self._active_sensors if self._active_sensors else SENSOR_KEYS

        # 기존 타일 데이터 백업
        old_values = {}
        for key, tile in self.tiles.items():
            try:
                old_values[key] = {
                    "value": tile["val"].cget("text"),
                    "stat": tile["stat"].cget("text"),
                    "alert_level": tile.get("alert_level", 1)
                }
            except:
                pass

        # 그리드 재생성
        self._build_grid(sensors)

        # 데이터 복원
        for key, data in old_values.items():
            if key in self.tiles:
                try:
                    self.tiles[key]["val"].configure(text=data["value"])
                    self.tiles[key]["stat"].configure(text=data["stat"])
                except:
                    pass

    def _build_grid(self, sensors: List[str]):
        """그리드 생성"""
        # 기존 위젯 제거
        for w in self.grid_slaves():
            w.destroy()
        self.tiles.clear()

        # 그리드 크기 계산
        sensor_count = len(sensors)
        rows, cols = self._calculate_grid_size(sensor_count)
        self._grid_rows = rows
        self._grid_cols = cols

        # 그리드 설정
        for r in range(rows):
            self.grid_rowconfigure(r, weight=1, uniform="row")
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1, uniform="col")

        # 타일 생성
        for idx, key in enumerate(sensors[:rows * cols]):
            row = idx // cols
            col = idx % cols
            self._create_tile(row, col, key)

    def _create_tile(self, row: int, col: int, key: str):
        """단일 타일 생성"""
        info = self.sensor_info.get(key, (key, "", ""))
        title, unit, icon = info

        # 메인 프레임
        f = tk.Frame(self, bg=COLOR_TILE_OK, relief="raised", bd=3)
        f.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

        # 컨텐츠 프레임
        content = tk.Frame(f, bg=COLOR_TILE_OK)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # 상단: 아이콘 + 제목
        header = tk.Frame(content, bg=COLOR_TILE_OK)
        header.pack(fill="x", pady=(5, 10))

        icon_label = tk.Label(
            header,
            text=icon,
            font=("Pretendard", 24),
            bg=COLOR_TILE_OK,
            fg=ideal_fg(COLOR_TILE_OK)
        )
        icon_label.pack(side="left", padx=(0, 8))

        title_label = tk.Label(
            header,
            text=f"{title} ({unit})" if unit else title,
            font=("Pretendard", 14, "bold"),
            bg=COLOR_TILE_OK,
            fg=ideal_fg(COLOR_TILE_OK)
        )
        title_label.pack(side="left")

        # 중앙: 값
        value_label = tk.Label(
            content,
            text="--",
            font=("Pretendard", 48, "bold"),
            bg=COLOR_TILE_OK,
            fg=ideal_fg(COLOR_TILE_OK)
        )
        value_label.pack(expand=True)

        # 하단: 상태 + 통계
        footer = tk.Frame(content, bg=COLOR_TILE_OK)
        footer.pack(fill="x", pady=(10, 5))

        status_label = tk.Label(
            footer,
            text="정상",
            font=("Pretendard", 16, "bold"),
            bg=COLOR_TILE_OK,
            fg="#27AE60"
        )
        status_label.pack()

        stat_label = tk.Label(
            footer,
            text="오늘 통계: - / - / -",
            font=("Pretendard", 10),
            bg=COLOR_TILE_OK,
            fg=ideal_fg(COLOR_TILE_OK)
        )
        stat_label.pack()

        # 타일 정보 저장
        self.tiles[key] = {
            "frame": f,
            "content": content,
            "header": header,
            "icon": icon_label,
            "title": title_label,
            "val": value_label,
            "status": status_label,
            "stat": stat_label,
            "unit": unit,
            "alert_level": 1
        }

        # 클릭 이벤트
        def on_click(e, k=key):
            self.on_tile_click(k)

        f.bind("<Button-1>", on_click)
        for widget in (content, header, icon_label, title_label, value_label, status_label, stat_label):
            widget.bind("<Button-1>", on_click)

        # 리사이즈 이벤트
        f.bind("<Configure>", lambda e, k=key: self._autoscale_tile(k))

    def _autoscale_tile(self, key: str):
        """타일 자동 스케일링"""
        tile = self.tiles.get(key)
        if not tile:
            return

        f = tile["frame"]
        h = max(f.winfo_height(), 100)

        # 높이 기반 폰트 크기 계산
        icon_size = max(18, int(h * 0.15))
        title_size = max(12, int(h * 0.08))
        value_size = max(24, int(h * 0.25))
        status_size = max(12, int(h * 0.09))
        stat_size = max(8, int(h * 0.06))

        try:
            tile["icon"].configure(font=("Pretendard", icon_size))
            tile["title"].configure(font=("Pretendard", title_size, "bold"))
            tile["val"].configure(font=("Pretendard", value_size, "bold"))
            tile["status"].configure(font=("Pretendard", status_size, "bold"))
            tile["stat"].configure(font=("Pretendard", stat_size))
        except:
            pass

    def set_connection_status(self, status: str):
        """접속 상태 설정"""
        self._connection_status = status

        if status == "waiting":
            for k in self.tiles:
                self.apply_value(k, "--", "센서 연결 대기중...", 1)
        elif status == "connected":
            for k in self.tiles:
                self.apply_value(k, "--", "", 1)

    def apply_value(
        self,
        key: str,
        value: str,
        stat_text: str,
        alert_level: int = 1,
        skip_autoscale: bool = False
    ):
        """값 적용"""
        tile = self.tiles.get(key)
        if not tile:
            return

        # 배경색 설정
        if self._connection_status == "waiting":
            bg = "#E8E8E8"
            fg = "#2C3E50"
            display_value = "대기중"
            status_text = "대기"
            status_color = "#666666"
        else:
            bg = self.ALERT_COLORS.get(alert_level, COLOR_TILE_OK)
            fg = ideal_fg(bg)
            display_value = value
            status_text = self.ALERT_NAMES.get(alert_level, "정상")
            status_color = fg

        # 배경색 업데이트
        current_bg = tile["frame"].cget("bg")
        if current_bg != bg:
            for widget_key in ("frame", "content", "header", "icon", "title", "val", "status", "stat"):
                if widget_key in tile:
                    try:
                        tile[widget_key].configure(bg=bg)
                        if widget_key in ("icon", "title", "val", "stat"):
                            tile[widget_key].configure(fg=fg)
                    except:
                        pass

        # 값 업데이트
        tile["val"].configure(text=display_value)
        tile["status"].configure(text=status_text, fg=status_color)
        tile["stat"].configure(text=stat_text)
        tile["alert_level"] = alert_level

        if not skip_autoscale:
            self._autoscale_tile(key)

    def apply_value_with_color(
        self,
        key: str,
        value: str,
        stat_text: str,
        color: str,
        alert_level: int = 1,
        skip_autoscale: bool = False
    ):
        """커스텀 색상으로 값 적용"""
        tile = self.tiles.get(key)
        if not tile:
            return

        bg = color
        fg = ideal_fg(color)
        status_text = self.ALERT_NAMES.get(alert_level, "정상")

        # 배경색 업데이트
        for widget_key in ("frame", "content", "header", "icon", "title", "val", "status", "stat"):
            if widget_key in tile:
                try:
                    tile[widget_key].configure(bg=bg)
                    if widget_key in ("icon", "title", "val", "stat"):
                        tile[widget_key].configure(fg=fg)
                except:
                    pass

        tile["val"].configure(text=value)
        tile["status"].configure(text=status_text, fg=fg)
        tile["stat"].configure(text=stat_text)
        tile["alert_level"] = alert_level

        if not skip_autoscale:
            self._autoscale_tile(key)

    def apply_disconnected(self, key: str, value: str, stat_text: str):
        """통신 끊김 상태로 표시"""
        tile = self.tiles.get(key)
        if not tile:
            return

        bg = "#808080"
        fg = "#FFFFFF"

        for widget_key in ("frame", "content", "header", "icon", "title", "val", "status", "stat"):
            if widget_key in tile:
                try:
                    tile[widget_key].configure(bg=bg)
                    if widget_key in ("icon", "title", "val", "stat"):
                        tile[widget_key].configure(fg=fg)
                except:
                    pass

        tile["val"].configure(text=value if value != "--" else "---")
        tile["status"].configure(text="통신 끊김", fg="#FF6B6B")

        self._autoscale_tile(key)

    def update_stat(self, key: str, stat_text: str):
        """통계 업데이트"""
        tile = self.tiles.get(key)
        if tile:
            tile["stat"].configure(text=stat_text)

    def get_grid_size(self) -> Tuple[int, int]:
        """현재 그리드 크기 반환"""
        return (self._grid_rows, self._grid_cols)

    def get_active_sensors(self) -> List[str]:
        """활성 센서 목록 반환"""
        return self._active_sensors.copy()
