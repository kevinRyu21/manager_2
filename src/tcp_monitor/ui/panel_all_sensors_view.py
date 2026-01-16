"""
센서전체보기 뷰 컴포넌트

접속된 모든 센서 ID에서 오는 9개 센서값을 분할화면으로 표시합니다.
2개 센서: 2분할, 3-4개 센서: 4분할
"""

import tkinter as tk
from tkinter import ttk

from ..utils.helpers import SENSOR_KEYS


# 센서 표시 정보 (이름, 아이콘, 단위)
SENSOR_INFO = {
    "co2": ("CO₂", "🏭", "ppm"),
    "o2": ("O₂", "💨", "%"),
    "h2s": ("H₂S", "☠️", "ppm"),
    "co": ("CO", "🔥", "ppm"),
    "lel": ("LEL", "💥", "%"),
    "smoke": ("연기", "🌫️", "%"),
    "temperature": ("온도", "🌡️", "°C"),
    "humidity": ("습도", "💧", "%"),
    "water": ("침수", "🌊", "")
}


class SensorCard(tk.Frame):
    """한 센서 ID의 9개 센서값을 간결하게 표시하는 카드 (화재패널 스타일)"""

    def __init__(self, master, sid, app):
        super().__init__(master, bg="#1A1A2E", relief="raised", bd=2)
        self.sid = sid
        self.app = app
        self.sensor_rows = {}

        # 헤더 (센서 ID)
        header = tk.Frame(self, bg="#16213E", height=40)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        self.title_label = tk.Label(header, text=f"📡 센서 {sid}",
                                   font=("Pretendard", 14, "bold"),
                                   bg="#16213E", fg="#FFFFFF")
        self.title_label.pack(side="left", padx=10, pady=8)

        # 상태 표시
        self.status_label = tk.Label(header, text="● 대기중",
                                    font=("Pretendard", 10),
                                    bg="#16213E", fg="#FFFFFF")
        self.status_label.pack(side="right", padx=10, pady=8)

        # 센서값 리스트 (화재패널 스타일)
        content = tk.Frame(self, bg="#1A1A2E")
        content.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # 센서 배치 순서
        sensor_order = ["temperature", "humidity", "co2", "o2", "co", "h2s", "lel", "smoke", "water"]

        for key in sensor_order:
            info = SENSOR_INFO.get(key, (key, "📊", ""))
            self._create_sensor_row(content, key, info[0], info[1], info[2])

    def _create_sensor_row(self, parent, key, name, icon, unit):
        """센서 상태 행 생성 (화재패널 스타일)"""
        row = tk.Frame(parent, bg="#0F3460")
        row.pack(fill="x", pady=1)

        # 좌측: 아이콘 + 이름
        left = tk.Frame(row, bg="#0F3460")
        left.pack(side="left", padx=5, pady=4)

        icon_label = tk.Label(left, text=icon, font=("Pretendard", 11),
                             bg="#0F3460", fg="#FFFFFF")
        icon_label.pack(side="left")

        name_label = tk.Label(left, text=name, font=("Pretendard", 10),
                             bg="#0F3460", fg="#FFFFFF", width=4, anchor="w")
        name_label.pack(side="left", padx=3)

        # 우측: 값 + 단위
        right = tk.Frame(row, bg="#0F3460")
        right.pack(side="right", padx=5, pady=4)

        value_label = tk.Label(right, text="--", font=("Pretendard", 12, "bold"),
                              bg="#0F3460", fg="#27AE60", width=6, anchor="e")
        value_label.pack(side="left")

        unit_label = tk.Label(right, text=unit, font=("Pretendard", 9),
                             bg="#0F3460", fg="#94A3B8", width=4, anchor="w")
        unit_label.pack(side="left")

        self.sensor_rows[key] = {
            "row": row,
            "value": value_label,
            "unit": unit_label
        }

    def update_values(self, data):
        """센서값 업데이트"""
        for key, value in data.items():
            if key in self.sensor_rows:
                if value is None or value == "--":
                    self.sensor_rows[key]["value"].configure(text="--", fg="#666666")
                else:
                    try:
                        val = float(value)
                        if key in ["temperature", "humidity"]:
                            text = f"{val:.1f}"
                        elif key == "water":
                            text = "침수" if val > 0 else "정상"
                        else:
                            text = f"{val:.1f}"

                        # 색상 결정 (경보 레벨에 따라)
                        color = self._get_value_color(key, val)
                        self.sensor_rows[key]["value"].configure(text=text, fg=color)
                    except (ValueError, TypeError):
                        self.sensor_rows[key]["value"].configure(text=str(value), fg="#FFFFFF")

    def _get_value_color(self, key, value):
        """경보 수준에 따른 색상 반환"""
        # 5단계 색상 시스템
        if key == "o2":
            if value < 19.5 or value > 23.5:
                return "#E74C3C"  # 위험
            return "#27AE60"  # 정상

        thresholds = {
            "co2": [(5000, "#8E44AD"), (3000, "#E74C3C"), (1500, "#E67E22"), (1000, "#F1C40F"), (0, "#27AE60")],
            "h2s": [(20, "#8E44AD"), (10, "#E74C3C"), (5, "#E67E22"), (2, "#F1C40F"), (0, "#27AE60")],
            "co": [(200, "#8E44AD"), (100, "#E74C3C"), (50, "#E67E22"), (25, "#F1C40F"), (0, "#27AE60")],
            "lel": [(25, "#8E44AD"), (15, "#E74C3C"), (10, "#E67E22"), (5, "#F1C40F"), (0, "#27AE60")],
            "smoke": [(50, "#8E44AD"), (30, "#E74C3C"), (20, "#E67E22"), (10, "#F1C40F"), (0, "#27AE60")],
            "temperature": [(50, "#E74C3C"), (35, "#E67E22"), (30, "#F1C40F"), (0, "#27AE60")],
            "humidity": [(90, "#E67E22"), (70, "#F1C40F"), (30, "#27AE60"), (0, "#F1C40F")],
            "water": [(1, "#E74C3C"), (0, "#27AE60")]
        }

        if key in thresholds:
            for threshold, color in thresholds[key]:
                if value >= threshold:
                    return color

        return "#FFFFFF"

    def set_status(self, status):
        """연결 상태 설정"""
        if status == "connected":
            self.status_label.configure(text="● 연결됨", fg="#2ECC71")
            self.title_label.master.configure(bg="#27AE60")
            self.title_label.configure(bg="#27AE60")
            self.status_label.configure(bg="#27AE60")
        elif status == "disconnected":
            self.status_label.configure(text="● 끊김", fg="#FF6B6B")
            self.title_label.master.configure(bg="#E74C3C")
            self.title_label.configure(bg="#E74C3C")
            self.status_label.configure(bg="#E74C3C")
        else:  # waiting
            self.status_label.configure(text="● 대기중", fg="#FFFFFF")
            self.title_label.master.configure(bg="#16213E")
            self.title_label.configure(bg="#16213E")
            self.status_label.configure(bg="#16213E")


class AllSensorsView(tk.Frame):
    """모든 센서를 분할화면으로 표시하는 뷰"""

    def __init__(self, master, app):
        super().__init__(master, bg="#1A1A2E")
        self.master_panel = master
        self.app = app
        self.sensor_cards = {}  # sid_key -> SensorCard
        self.current_layout = 0  # 현재 레이아웃 (센서 개수)

        # 컨테이너 프레임
        self.container = tk.Frame(self, bg="#1A1A2E")
        self.container.pack(fill="both", expand=True, padx=5, pady=5)

        # 초기 레이아웃 구성
        self._rebuild_layout()

    def _rebuild_layout(self):
        """연결된 센서 수에 따라 레이아웃 재구성"""
        # 연결된 센서 키 목록 (대기 탭 제외)
        connected_sids = [k for k in self.app.panels.keys() if k != "__waiting__"]
        num_sensors = len(connected_sids)

        # 레이아웃이 변경되었는지 확인
        if num_sensors == self.current_layout and set(connected_sids) == set(self.sensor_cards.keys()):
            return  # 변경 없음

        # 기존 카드 제거
        for card in self.sensor_cards.values():
            card.destroy()
        self.sensor_cards.clear()

        # 컨테이너 내부 위젯 제거
        for widget in self.container.winfo_children():
            widget.destroy()

        if num_sensors == 0:
            # 센서 없음 메시지
            msg = tk.Label(self.container, text="연결된 센서가 없습니다",
                          font=("Pretendard", 16, "bold"),
                          bg="#1A1A2E", fg="#FFFFFF")
            msg.place(relx=0.5, rely=0.5, anchor="center")
            self.current_layout = 0
            return

        if num_sensors == 1:
            # 1개 센서는 센서전체보기 불가 (버튼 비활성화됨)
            msg = tk.Label(self.container, text="센서가 2개 이상일 때 사용 가능합니다",
                          font=("Pretendard", 14, "bold"),
                          bg="#1A1A2E", fg="#FFFFFF")
            msg.place(relx=0.5, rely=0.5, anchor="center")
            self.current_layout = 1
            return

        # 분할 레이아웃 결정
        if num_sensors == 2:
            rows, cols = 1, 2
        else:  # 3-4개
            rows, cols = 2, 2

        # 그리드 weight 설정
        for i in range(rows):
            self.container.grid_rowconfigure(i, weight=1)
        for j in range(cols):
            self.container.grid_columnconfigure(j, weight=1)

        # 센서 카드 생성
        for idx, sid_key in enumerate(connected_sids[:4]):  # 최대 4개
            row = idx // cols
            col = idx % cols

            # SID 추출
            if "@" in sid_key:
                sid = sid_key.split("@")[0]
            elif "#" in sid_key:
                sid = sid_key.split("#")[0]
            else:
                sid = sid_key

            card = SensorCard(self.container, sid, self.app)
            card.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            self.sensor_cards[sid_key] = card

        self.current_layout = num_sensors

    def update_sensor_data(self, sid_key, data, status="connected"):
        """특정 센서 데이터 업데이트"""
        # 레이아웃 확인 및 필요시 재구성
        if sid_key not in self.sensor_cards:
            self._rebuild_layout()

        if sid_key in self.sensor_cards:
            self.sensor_cards[sid_key].update_values(data)
            self.sensor_cards[sid_key].set_status(status)

    def update_all_sensors(self):
        """모든 센서 데이터 업데이트"""
        # 레이아웃 재구성 확인
        self._rebuild_layout()

        # 각 센서 패널에서 최신 데이터 가져오기
        for sid_key in list(self.sensor_cards.keys()):
            if sid_key in self.sensor_cards:
                # app.panels에서 패널 가져오기
                panel = self.app.panels.get(sid_key)
                if panel:
                    # 패널의 data 속성에서 센서 데이터 추출
                    data = {}
                    for key in SENSOR_KEYS:
                        if hasattr(panel, 'data') and key in panel.data:
                            data[key] = panel.data[key]

                    # 연결 상태 확인
                    status = "connected"
                    if hasattr(panel, '_connection_status'):
                        if panel._connection_status == "disconnected":
                            status = "disconnected"
                        elif panel._connection_status == "waiting":
                            status = "waiting"

                    self.sensor_cards[sid_key].update_values(data)
                    self.sensor_cards[sid_key].set_status(status)

    def refresh(self):
        """뷰 새로고침"""
        self._rebuild_layout()
        self.update_all_sensors()
