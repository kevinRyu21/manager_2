#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARAMe Manager 센서 테스트 클라이언트

9가지 센서 데이터를 시뮬레이션하여 Manager에 전송합니다.
각 센서별 경보 레벨 및 화재 경보 테스트가 가능합니다.

사용법:
    python3 sensor_test_client.py [--host HOST] [--port PORT] [--sid SENSOR_ID]
"""

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import time
import random
import json
from datetime import datetime

# 센서 정보 정의
SENSORS = {
    'co2': {'name': 'CO2 (이산화탄소)', 'unit': 'ppm', 'min': 0, 'max': 5000, 'normal': 400,
            'levels': [1000, 2000, 3000, 4000]},  # 관심/주의/경계/심각
    'o2': {'name': 'O2 (산소)', 'unit': '%', 'min': 0, 'max': 25, 'normal': 20.9,
           'levels': [19.5, 18.0, 16.0, 14.0], 'reverse': True},  # 낮을수록 위험
    'h2s': {'name': 'H2S (황화수소)', 'unit': 'ppm', 'min': 0, 'max': 100, 'normal': 0,
            'levels': [5, 10, 20, 50]},
    'co': {'name': 'CO (일산화탄소)', 'unit': 'ppm', 'min': 0, 'max': 500, 'normal': 0,
           'levels': [25, 50, 100, 200]},
    'lel': {'name': 'LEL (가연성가스)', 'unit': '%', 'min': 0, 'max': 100, 'normal': 0,
            'levels': [10, 20, 30, 50]},
    'smoke': {'name': 'Smoke (연기)', 'unit': '%', 'min': 0, 'max': 100, 'normal': 0,
              'levels': [10, 20, 40, 60]},
    'temperature': {'name': 'Temperature (온도)', 'unit': '°C', 'min': -20, 'max': 80, 'normal': 25,
                    'levels': [35, 40, 50, 60]},
    'humidity': {'name': 'Humidity (습도)', 'unit': '%', 'min': 0, 'max': 100, 'normal': 50,
                 'levels': [30, 25, 20, 15], 'reverse': True},  # 낮을수록 경고 (건조)
    'water': {'name': 'Water (누수)', 'unit': '', 'min': 0, 'max': 1, 'normal': 0,
              'levels': [0.5, 0.5, 0.5, 0.5], 'binary': True}  # 0 또는 1
}

# 화재 시나리오 프리셋
FIRE_SCENARIOS = {
    '정상': {'temperature': 25, 'humidity': 50, 'co': 0, 'co2': 400, 'smoke': 0, 'lel': 0},
    '관심 (초기)': {'temperature': 35, 'humidity': 35, 'co': 10, 'co2': 800, 'smoke': 5, 'lel': 5},
    '주의 (연기감지)': {'temperature': 40, 'humidity': 30, 'co': 30, 'co2': 1500, 'smoke': 20, 'lel': 10},
    '경계 (화재초기)': {'temperature': 50, 'humidity': 25, 'co': 80, 'co2': 2500, 'smoke': 40, 'lel': 25},
    '심각 (화재확산)': {'temperature': 65, 'humidity': 15, 'co': 150, 'co2': 4000, 'smoke': 70, 'lel': 45},
    '위험 (대형화재)': {'temperature': 80, 'humidity': 10, 'co': 250, 'co2': 5000, 'smoke': 95, 'lel': 70},
}

# 가스 누출 시나리오
GAS_SCENARIOS = {
    '정상': {'lel': 0, 'h2s': 0, 'co': 0, 'o2': 20.9},
    'LEL 관심': {'lel': 12, 'h2s': 0, 'co': 0, 'o2': 20.5},
    'LEL 주의': {'lel': 25, 'h2s': 2, 'co': 10, 'o2': 20.0},
    'H2S 검출': {'lel': 5, 'h2s': 8, 'co': 5, 'o2': 20.5},
    'H2S 위험': {'lel': 10, 'h2s': 25, 'co': 20, 'o2': 19.5},
    '산소 부족': {'lel': 5, 'h2s': 0, 'co': 0, 'o2': 17.0},
    '복합 위험': {'lel': 35, 'h2s': 15, 'co': 80, 'o2': 18.0},
}


class SensorTestClient:
    """센서 테스트 클라이언트 GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GARAMe 센서 테스트 클라이언트")
        self.root.geometry("1200x800")
        self.root.configure(bg="#2C3E50")

        # 연결 상태
        self.socket = None
        self.connected = False
        self.send_thread = None
        self.running = False

        # 센서 값 변수
        self.sensor_vars = {}
        self.sensor_scales = {}

        # 자동 전송 설정
        self.auto_send = tk.BooleanVar(value=False)
        self.send_interval = tk.DoubleVar(value=1.0)

        # UI 생성
        self._create_ui()

        # 종료 이벤트
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """UI 생성"""
        # 상단: 연결 설정
        self._create_connection_frame()

        # 중앙: 센서 컨트롤
        self._create_sensor_frame()

        # 하단: 시나리오 및 로그
        self._create_bottom_frame()

    def _create_connection_frame(self):
        """연결 설정 프레임"""
        conn_frame = tk.LabelFrame(self.root, text=" 연결 설정 ",
                                   font=("Pretendard", 12, "bold"),
                                   bg="#2C3E50", fg="#FFFFFF", padx=10, pady=5)
        conn_frame.pack(fill="x", padx=10, pady=5)

        # Host
        tk.Label(conn_frame, text="Host:", bg="#2C3E50", fg="#FFFFFF",
                font=("Pretendard", 11)).pack(side="left", padx=5)
        self.host_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(conn_frame, textvariable=self.host_var, width=15,
                font=("Pretendard", 11)).pack(side="left", padx=5)

        # Port
        tk.Label(conn_frame, text="Port:", bg="#2C3E50", fg="#FFFFFF",
                font=("Pretendard", 11)).pack(side="left", padx=5)
        self.port_var = tk.StringVar(value="9000")
        tk.Entry(conn_frame, textvariable=self.port_var, width=6,
                font=("Pretendard", 11)).pack(side="left", padx=5)

        # Sensor ID
        tk.Label(conn_frame, text="Sensor ID:", bg="#2C3E50", fg="#FFFFFF",
                font=("Pretendard", 11)).pack(side="left", padx=5)
        self.sid_var = tk.StringVar(value="test_sensor")
        tk.Entry(conn_frame, textvariable=self.sid_var, width=15,
                font=("Pretendard", 11)).pack(side="left", padx=5)

        # 연결 버튼
        self.connect_btn = tk.Button(conn_frame, text="연결", command=self._toggle_connection,
                                     font=("Pretendard", 11, "bold"), bg="#27AE60", fg="#FFFFFF",
                                     width=8, cursor="hand2")
        self.connect_btn.pack(side="left", padx=10)

        # 연결 상태
        self.status_label = tk.Label(conn_frame, text="● 연결 안됨",
                                     bg="#2C3E50", fg="#E74C3C",
                                     font=("Pretendard", 11, "bold"))
        self.status_label.pack(side="left", padx=10)

        # 자동 전송
        tk.Checkbutton(conn_frame, text="자동 전송", variable=self.auto_send,
                      bg="#2C3E50", fg="#FFFFFF", selectcolor="#34495E",
                      font=("Pretendard", 11), command=self._toggle_auto_send).pack(side="left", padx=10)

        tk.Label(conn_frame, text="간격(초):", bg="#2C3E50", fg="#FFFFFF",
                font=("Pretendard", 11)).pack(side="left")
        tk.Spinbox(conn_frame, from_=0.1, to=10.0, increment=0.1, width=5,
                  textvariable=self.send_interval, font=("Pretendard", 11)).pack(side="left", padx=5)

        # 수동 전송 버튼
        self.send_btn = tk.Button(conn_frame, text="데이터 전송", command=self._send_data,
                                  font=("Pretendard", 11, "bold"), bg="#3498DB", fg="#FFFFFF",
                                  width=10, cursor="hand2", state="disabled")
        self.send_btn.pack(side="right", padx=10)

    def _create_sensor_frame(self):
        """센서 컨트롤 프레임"""
        sensor_frame = tk.LabelFrame(self.root, text=" 센서 값 설정 ",
                                     font=("Pretendard", 12, "bold"),
                                     bg="#2C3E50", fg="#FFFFFF", padx=10, pady=10)
        sensor_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 3x3 그리드로 센서 배치
        row, col = 0, 0
        for key, info in SENSORS.items():
            frame = tk.Frame(sensor_frame, bg="#34495E", relief="raised", bd=2)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # 센서 이름
            tk.Label(frame, text=info['name'], bg="#34495E", fg="#FFFFFF",
                    font=("Pretendard", 11, "bold")).pack(pady=(5, 0))

            # 현재 값 표시
            var = tk.DoubleVar(value=info['normal'])
            self.sensor_vars[key] = var

            value_frame = tk.Frame(frame, bg="#34495E")
            value_frame.pack(fill="x", padx=5)

            value_label = tk.Label(value_frame, textvariable=var, bg="#34495E", fg="#00FF00",
                                  font=("Pretendard", 18, "bold"), width=8)
            value_label.pack(side="left", expand=True)

            tk.Label(value_frame, text=info['unit'], bg="#34495E", fg="#AAAAAA",
                    font=("Pretendard", 12)).pack(side="left")

            # 슬라이더
            if info.get('binary'):
                scale = tk.Scale(frame, from_=0, to=1, resolution=1,
                               orient="horizontal", variable=var,
                               bg="#34495E", fg="#FFFFFF", highlightthickness=0,
                               troughcolor="#1ABC9C", length=200)
            else:
                scale = tk.Scale(frame, from_=info['min'], to=info['max'],
                               resolution=0.1 if info['max'] <= 100 else 1,
                               orient="horizontal", variable=var,
                               bg="#34495E", fg="#FFFFFF", highlightthickness=0,
                               troughcolor="#1ABC9C", length=200)
            scale.pack(fill="x", padx=10, pady=5)
            self.sensor_scales[key] = scale

            # 퀵 버튼 (정상/관심/주의/경계/심각)
            btn_frame = tk.Frame(frame, bg="#34495E")
            btn_frame.pack(fill="x", padx=5, pady=(0, 5))

            levels = info['levels']
            is_reverse = info.get('reverse', False)

            # 정상
            tk.Button(btn_frame, text="정상", command=lambda k=key, v=info['normal']: self._set_sensor(k, v),
                     font=("Pretendard", 9), bg="#27AE60", fg="#FFFFFF", width=5).pack(side="left", padx=1)

            # 관심
            tk.Button(btn_frame, text="관심", command=lambda k=key, v=levels[0]: self._set_sensor(k, v),
                     font=("Pretendard", 9), bg="#3498DB", fg="#FFFFFF", width=5).pack(side="left", padx=1)

            # 주의
            tk.Button(btn_frame, text="주의", command=lambda k=key, v=levels[1]: self._set_sensor(k, v),
                     font=("Pretendard", 9), bg="#F1C40F", fg="#000000", width=5).pack(side="left", padx=1)

            # 경계
            tk.Button(btn_frame, text="경계", command=lambda k=key, v=levels[2]: self._set_sensor(k, v),
                     font=("Pretendard", 9), bg="#E67E22", fg="#FFFFFF", width=5).pack(side="left", padx=1)

            # 심각
            tk.Button(btn_frame, text="심각", command=lambda k=key, v=levels[3]: self._set_sensor(k, v),
                     font=("Pretendard", 9), bg="#E74C3C", fg="#FFFFFF", width=5).pack(side="left", padx=1)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        # 그리드 가중치 설정
        for i in range(3):
            sensor_frame.grid_columnconfigure(i, weight=1)
        for i in range(3):
            sensor_frame.grid_rowconfigure(i, weight=1)

    def _create_bottom_frame(self):
        """하단 프레임 (시나리오 + 로그)"""
        bottom_frame = tk.Frame(self.root, bg="#2C3E50")
        bottom_frame.pack(fill="x", padx=10, pady=5)

        # 좌측: 시나리오
        scenario_frame = tk.LabelFrame(bottom_frame, text=" 시나리오 프리셋 ",
                                       font=("Pretendard", 12, "bold"),
                                       bg="#2C3E50", fg="#FFFFFF", padx=10, pady=5)
        scenario_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # 화재 시나리오
        fire_frame = tk.Frame(scenario_frame, bg="#2C3E50")
        fire_frame.pack(fill="x", pady=5)
        tk.Label(fire_frame, text="🔥 화재 시나리오:", bg="#2C3E50", fg="#FF6B6B",
                font=("Pretendard", 11, "bold")).pack(side="left", padx=5)
        for name, values in FIRE_SCENARIOS.items():
            btn = tk.Button(fire_frame, text=name,
                           command=lambda v=values: self._apply_scenario(v),
                           font=("Pretendard", 10), bg="#C0392B", fg="#FFFFFF",
                           cursor="hand2")
            btn.pack(side="left", padx=2)

        # 가스 시나리오
        gas_frame = tk.Frame(scenario_frame, bg="#2C3E50")
        gas_frame.pack(fill="x", pady=5)
        tk.Label(gas_frame, text="💨 가스 시나리오:", bg="#2C3E50", fg="#F1C40F",
                font=("Pretendard", 11, "bold")).pack(side="left", padx=5)
        for name, values in GAS_SCENARIOS.items():
            btn = tk.Button(gas_frame, text=name,
                           command=lambda v=values: self._apply_scenario(v),
                           font=("Pretendard", 10), bg="#2980B9", fg="#FFFFFF",
                           cursor="hand2")
            btn.pack(side="left", padx=2)

        # 전체 리셋/랜덤
        ctrl_frame = tk.Frame(scenario_frame, bg="#2C3E50")
        ctrl_frame.pack(fill="x", pady=5)
        tk.Button(ctrl_frame, text="🔄 전체 정상", command=self._reset_all,
                 font=("Pretendard", 11, "bold"), bg="#27AE60", fg="#FFFFFF",
                 cursor="hand2").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="🎲 랜덤 값", command=self._randomize_all,
                 font=("Pretendard", 11, "bold"), bg="#9B59B6", fg="#FFFFFF",
                 cursor="hand2").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="⚠️ 전체 심각", command=self._set_all_critical,
                 font=("Pretendard", 11, "bold"), bg="#E74C3C", fg="#FFFFFF",
                 cursor="hand2").pack(side="left", padx=5)

        # 우측: 로그
        log_frame = tk.LabelFrame(bottom_frame, text=" 전송 로그 ",
                                  font=("Pretendard", 12, "bold"),
                                  bg="#2C3E50", fg="#FFFFFF", padx=10, pady=5)
        log_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.log_text = tk.Text(log_frame, height=8, width=50, bg="#1A1A1A", fg="#00FF00",
                               font=("Consolas", 10), state="disabled")
        self.log_text.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _set_sensor(self, key, value):
        """센서 값 설정"""
        self.sensor_vars[key].set(value)

    def _apply_scenario(self, values):
        """시나리오 적용"""
        for key, value in values.items():
            if key in self.sensor_vars:
                self.sensor_vars[key].set(value)
        self._log(f"시나리오 적용: {values}")

    def _reset_all(self):
        """전체 정상값으로 리셋"""
        for key, info in SENSORS.items():
            self.sensor_vars[key].set(info['normal'])
        self._log("전체 센서 정상값으로 리셋")

    def _randomize_all(self):
        """전체 랜덤값"""
        for key, info in SENSORS.items():
            if info.get('binary'):
                value = random.choice([0, 1])
            else:
                value = random.uniform(info['min'], info['max'])
                value = round(value, 1)
            self.sensor_vars[key].set(value)
        self._log("전체 센서 랜덤값 설정")

    def _set_all_critical(self):
        """전체 심각 레벨"""
        for key, info in SENSORS.items():
            if info.get('binary'):
                self.sensor_vars[key].set(1)
            else:
                self.sensor_vars[key].set(info['levels'][3])
        self._log("전체 센서 심각 레벨 설정")

    def _toggle_connection(self):
        """연결 토글"""
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """서버 연결"""
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((host, port))
            self.socket.settimeout(None)

            self.connected = True
            self.connect_btn.configure(text="연결 해제", bg="#E74C3C")
            self.status_label.configure(text="● 연결됨", fg="#27AE60")
            self.send_btn.configure(state="normal")

            self._log(f"서버 연결 성공: {host}:{port}")

            # 초기 데이터 전송
            self._send_data()

        except Exception as e:
            messagebox.showerror("연결 오류", f"서버 연결 실패:\n{e}")
            self._log(f"연결 오류: {e}")

    def _disconnect(self):
        """연결 해제"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        self.connected = False
        self.connect_btn.configure(text="연결", bg="#27AE60")
        self.status_label.configure(text="● 연결 안됨", fg="#E74C3C")
        self.send_btn.configure(state="disabled")
        self._log("서버 연결 해제")

    def _toggle_auto_send(self):
        """자동 전송 토글"""
        if self.auto_send.get() and self.connected:
            self.running = True
            self.send_thread = threading.Thread(target=self._auto_send_loop, daemon=True)
            self.send_thread.start()
            self._log("자동 전송 시작")
        else:
            self.running = False
            self._log("자동 전송 중지")

    def _auto_send_loop(self):
        """자동 전송 루프"""
        while self.running and self.connected:
            try:
                self.root.after(0, self._send_data)
                time.sleep(self.send_interval.get())
            except:
                break

    def _send_data(self):
        """데이터 전송"""
        if not self.connected or not self.socket:
            return

        try:
            sid = self.sid_var.get()

            # 센서 데이터 구성
            data = {
                'sid': sid,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'co2': self.sensor_vars['co2'].get(),
                'o2': self.sensor_vars['o2'].get(),
                'h2s': self.sensor_vars['h2s'].get(),
                'co': self.sensor_vars['co'].get(),
                'lel': self.sensor_vars['lel'].get(),
                'smoke': self.sensor_vars['smoke'].get(),
                'temperature': self.sensor_vars['temperature'].get(),
                'humidity': self.sensor_vars['humidity'].get(),
                'water': int(self.sensor_vars['water'].get()),
            }

            # JSON 형식으로 전송
            message = json.dumps(data) + "\n"
            self.socket.sendall(message.encode('utf-8'))

            self._log(f"전송: T={data['temperature']:.1f}°C, H={data['humidity']:.1f}%, "
                     f"CO2={data['co2']:.0f}, CO={data['co']:.1f}, Smoke={data['smoke']:.1f}%")

        except Exception as e:
            self._log(f"전송 오류: {e}")
            self._disconnect()

    def _log(self, message):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", log_message)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_close(self):
        """종료 처리"""
        self.running = False
        self._disconnect()
        self.root.destroy()

    def run(self):
        """실행"""
        self.root.mainloop()


def main():
    """메인 함수"""
    import argparse
    parser = argparse.ArgumentParser(description="GARAMe 센서 테스트 클라이언트")
    parser.add_argument("--host", default="127.0.0.1", help="서버 호스트")
    parser.add_argument("--port", type=int, default=9000, help="서버 포트")
    parser.add_argument("--sid", default="test_sensor", help="센서 ID")
    args = parser.parse_args()

    client = SensorTestClient()
    client.host_var.set(args.host)
    client.port_var.set(str(args.port))
    client.sid_var.set(args.sid)
    client.run()


if __name__ == "__main__":
    main()
