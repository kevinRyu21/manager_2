#!/usr/bin/env python3
"""
센서 시뮬레이터 테스트 프로그램
GARAMe Manager v2.0용 센서 테스트 클라이언트

기능:
- 센서 ID 1-4까지 동시 접속 지원
- 9개 센서 값 (CO2, CO, O2, H2S, CH4, 온도, 습도, 연기, 누수) 전송
- 화재/질식/누수 등 각종 경고 레벨 시나리오 테스트
- 랜덤 데이터 생성
- GUI 컨트롤 패널
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import socket
import json
import threading
import time
import random
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class SensorData:
    """센서 데이터"""
    co2: Optional[float] = None      # ppm
    co: Optional[float] = None       # ppm
    o2: Optional[float] = None       # %
    h2s: Optional[float] = None      # ppm
    temperature: Optional[float] = None  # ℃
    humidity: Optional[float] = None     # %RH
    water: Optional[int] = None      # 0/1
    ch4: Optional[float] = None      # %LEL
    smoke: Optional[float] = None    # %
    ext_input: Optional[int] = None  # 0/1

    def to_dict(self) -> Dict[str, Any]:
        """None 값 제외하고 딕셔너리로 변환"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class SensorClient:
    """센서 클라이언트 (TCP 연결 + 데이터 전송)"""

    def __init__(self, sensor_id: str, host: str, port: int, password: str = "1234"):
        self.sensor_id = sensor_id
        self.host = host
        self.port = port
        self.password = password
        self.connected = False
        self.socket: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.sequence = 0
        self.send_interval = 1.0  # 전송 주기 (초)
        self.current_scenario = "정상"
        self.log_callback = None

    def connect(self):
        """서버 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self._log(f"[센서 {self.sensor_id}] 연결 성공: {self.host}:{self.port}")

            # hello 메시지 전송
            self._send_hello()
            return True
        except Exception as e:
            self._log(f"[센서 {self.sensor_id}] 연결 실패: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """연결 종료"""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        self._log(f"[센서 {self.sensor_id}] 연결 종료")

    def start_sending(self):
        """데이터 전송 시작"""
        if not self.connected:
            self._log(f"[센서 {self.sensor_id}] 연결되지 않음")
            return

        self.stop_event.clear()
        self.thread = threading.Thread(target=self._send_loop, daemon=True)
        self.thread.start()
        self._log(f"[센서 {self.sensor_id}] 데이터 전송 시작")

    def _send_hello(self):
        """Hello 핸드셰이크 메시지 전송"""
        hello_msg = {
            "type": "hello",
            "id": self.sensor_id,
            "msg_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "protocol_version": "2.0",
            "device_type": "sensor",
            "firmware_version": "SIMULATOR-1.0",
            "capabilities": ["sensor_update", "heartbeat"],
            "supported_sensors": ["co2", "co", "o2", "h2s", "ch4", "temperature", "humidity", "smoke", "water", "ext_input"]
        }
        self._send_message(hello_msg)

    def _send_loop(self):
        """데이터 전송 루프"""
        while not self.stop_event.is_set():
            try:
                # 시나리오에 따른 센서 데이터 생성
                sensor_data = self._generate_sensor_data(self.current_scenario)

                # sensor_update 메시지 생성
                msg = {
                    "type": "sensor_update",
                    "id": self.sensor_id,
                    "msg_id": str(uuid.uuid4()),
                    "timestamp": time.time(),
                    "protocol_version": "2.0",
                    "sequence": self.sequence,
                    "password": self.password,
                    "version": "SIMULATOR-1.0",
                    "data": sensor_data.to_dict()
                }

                # 메시지 전송
                self._send_message(msg)
                self.sequence += 1

                # 대기
                time.sleep(self.send_interval)

            except Exception as e:
                self._log(f"[센서 {self.sensor_id}] 전송 오류: {e}")
                break

    def _send_message(self, msg: dict):
        """메시지 전송"""
        try:
            json_str = json.dumps(msg, ensure_ascii=False)
            data = (json_str + "\n").encode('utf-8')
            self.socket.sendall(data)
            # self._log(f"[센서 {self.sensor_id}] 전송: {msg['type']}")
        except Exception as e:
            self._log(f"[센서 {self.sensor_id}] 전송 실패: {e}")
            self.connected = False

    def _generate_sensor_data(self, scenario: str) -> SensorData:
        """시나리오별 센서 데이터 생성"""
        if scenario == "정상":
            return SensorData(
                co2=400 + random.uniform(-50, 50),
                co=random.uniform(0, 5),
                o2=20.9 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 1),
                ch4=random.uniform(0, 5),
                temperature=20 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(0, 5),
                water=0,
                ext_input=0
            )

        elif scenario == "화재 레벨1 (주의)":
            return SensorData(
                co2=800 + random.uniform(-50, 100),
                co=15 + random.uniform(-2, 5),
                o2=20.5 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 2),
                ch4=10 + random.uniform(-2, 5),
                temperature=25 + random.uniform(-1, 3),
                humidity=50 + random.uniform(-10, 10),
                smoke=15 + random.uniform(-3, 5),
                water=0,
                ext_input=0
            )

        elif scenario == "화재 레벨2 (경계)":
            return SensorData(
                co2=1500 + random.uniform(-100, 200),
                co=30 + random.uniform(-5, 10),
                o2=20.0 + random.uniform(-1, 0.5),
                h2s=random.uniform(0, 3),
                ch4=20 + random.uniform(-5, 10),
                temperature=30 + random.uniform(-2, 5),
                humidity=55 + random.uniform(-10, 10),
                smoke=30 + random.uniform(-5, 10),
                water=0,
                ext_input=0
            )

        elif scenario == "화재 레벨3 (경고)":
            return SensorData(
                co2=3000 + random.uniform(-200, 500),
                co=60 + random.uniform(-10, 20),
                o2=19.0 + random.uniform(-1, 0.5),
                h2s=random.uniform(0, 5),
                ch4=40 + random.uniform(-10, 20),
                temperature=40 + random.uniform(-3, 8),
                humidity=60 + random.uniform(-10, 10),
                smoke=50 + random.uniform(-10, 20),
                water=0,
                ext_input=0
            )

        elif scenario == "화재 레벨4 (위험)":
            return SensorData(
                co2=5000 + random.uniform(-500, 1000),
                co=100 + random.uniform(-20, 40),
                o2=18.0 + random.uniform(-1, 0.5),
                h2s=random.uniform(0, 8),
                ch4=60 + random.uniform(-15, 30),
                temperature=60 + random.uniform(-5, 15),
                humidity=65 + random.uniform(-10, 10),
                smoke=70 + random.uniform(-15, 30),
                water=0,
                ext_input=0
            )

        elif scenario == "CO2 질식 위험":
            return SensorData(
                co2=5000 + random.uniform(-500, 1000),
                co=random.uniform(0, 10),
                o2=19.0 + random.uniform(-1, 0.5),
                h2s=random.uniform(0, 2),
                ch4=random.uniform(0, 5),
                temperature=22 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(0, 10),
                water=0,
                ext_input=0
            )

        elif scenario == "CO 중독 위험":
            return SensorData(
                co2=800 + random.uniform(-100, 200),
                co=100 + random.uniform(-20, 50),
                o2=20.5 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 2),
                ch4=random.uniform(0, 10),
                temperature=24 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(10, 30),
                water=0,
                ext_input=0
            )

        elif scenario == "산소 부족":
            return SensorData(
                co2=1000 + random.uniform(-100, 200),
                co=random.uniform(0, 10),
                o2=18.0 + random.uniform(-1, 0.5),
                h2s=random.uniform(0, 2),
                ch4=random.uniform(0, 5),
                temperature=22 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(0, 10),
                water=0,
                ext_input=0
            )

        elif scenario == "H2S 황화수소 위험":
            return SensorData(
                co2=600 + random.uniform(-50, 100),
                co=random.uniform(0, 10),
                o2=20.5 + random.uniform(-0.5, 0.5),
                h2s=15 + random.uniform(-3, 10),
                ch4=random.uniform(0, 5),
                temperature=22 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(0, 10),
                water=0,
                ext_input=0
            )

        elif scenario == "CH4 가연성가스 위험":
            return SensorData(
                co2=600 + random.uniform(-50, 100),
                co=random.uniform(0, 10),
                o2=20.5 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 2),
                ch4=60 + random.uniform(-10, 30),
                temperature=22 + random.uniform(-2, 2),
                humidity=50 + random.uniform(-10, 10),
                smoke=random.uniform(0, 10),
                water=0,
                ext_input=0
            )

        elif scenario == "연기 감지":
            return SensorData(
                co2=1200 + random.uniform(-100, 300),
                co=20 + random.uniform(-5, 10),
                o2=20.0 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 2),
                ch4=random.uniform(0, 10),
                temperature=28 + random.uniform(-2, 5),
                humidity=55 + random.uniform(-10, 10),
                smoke=60 + random.uniform(-10, 30),
                water=0,
                ext_input=0
            )

        elif scenario == "누수 감지":
            return SensorData(
                co2=400 + random.uniform(-50, 50),
                co=random.uniform(0, 5),
                o2=20.9 + random.uniform(-0.5, 0.5),
                h2s=random.uniform(0, 1),
                ch4=random.uniform(0, 5),
                temperature=20 + random.uniform(-2, 2),
                humidity=80 + random.uniform(-5, 10),
                smoke=random.uniform(0, 5),
                water=1,  # 누수 감지!
                ext_input=0
            )

        elif scenario == "랜덤":
            return SensorData(
                co2=random.uniform(350, 5000),
                co=random.uniform(0, 150),
                o2=random.uniform(17, 21),
                h2s=random.uniform(0, 20),
                ch4=random.uniform(0, 100),
                temperature=random.uniform(15, 50),
                humidity=random.uniform(30, 90),
                smoke=random.uniform(0, 100),
                water=random.choice([0, 1]),
                ext_input=random.choice([0, 1])
            )

        else:
            # 기본값 (정상)
            return self._generate_sensor_data("정상")

    def _log(self, message: str):
        """로그 출력"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)


class SensorSimulatorGUI:
    """센서 시뮬레이터 GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("센서 시뮬레이터 - GARAMe Manager v2.0 테스트")
        self.root.geometry("1000x800")

        # 센서 클라이언트들
        self.clients: Dict[str, SensorClient] = {}

        # 시나리오 목록
        self.scenarios = [
            "정상",
            "화재 레벨1 (주의)",
            "화재 레벨2 (경계)",
            "화재 레벨3 (경고)",
            "화재 레벨4 (위험)",
            "CO2 질식 위험",
            "CO 중독 위험",
            "산소 부족",
            "H2S 황화수소 위험",
            "CH4 가연성가스 위험",
            "연기 감지",
            "누수 감지",
            "랜덤"
        ]

        self._build_ui()

    def _build_ui(self):
        """UI 구성"""
        # 상단: 서버 설정
        top_frame = tk.Frame(self.root, bg="#2C3E50", pady=10)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="서버 주소:", bg="#2C3E50", fg="#FFFFFF",
                font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.host_entry = tk.Entry(top_frame, width=15, font=("Arial", 10))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(side="left", padx=5)

        tk.Label(top_frame, text="포트:", bg="#2C3E50", fg="#FFFFFF",
                font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.port_entry = tk.Entry(top_frame, width=8, font=("Arial", 10))
        self.port_entry.insert(0, "9000")
        self.port_entry.pack(side="left", padx=5)

        tk.Label(top_frame, text="전송주기(초):", bg="#2C3E50", fg="#FFFFFF",
                font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.interval_entry = tk.Entry(top_frame, width=5, font=("Arial", 10))
        self.interval_entry.insert(0, "1.0")
        self.interval_entry.pack(side="left", padx=5)

        # 중앙: 센서 컨트롤 패널 (4개 센서)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 센서 패널 4개 생성
        self.sensor_panels = {}
        for i in range(4):
            sensor_id = str(i + 1)
            panel = self._create_sensor_panel(main_frame, sensor_id, i // 2, i % 2)
            self.sensor_panels[sensor_id] = panel

        # 하단: 로그
        bottom_frame = tk.Frame(self.root, bg="#34495E")
        bottom_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(bottom_frame, text="로그", bg="#34495E", fg="#FFFFFF",
                font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=10,
                                                   font=("Courier", 9),
                                                   bg="#1C1C1C", fg="#00FF00",
                                                   wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 로그 지우기 버튼
        clear_btn = tk.Button(bottom_frame, text="로그 지우기",
                             command=self._clear_log,
                             bg="#E74C3C", fg="#FFFFFF",
                             font=("Arial", 10, "bold"))
        clear_btn.pack(pady=5)

    def _create_sensor_panel(self, parent, sensor_id: str, row: int, col: int):
        """센서 컨트롤 패널 생성"""
        panel_frame = tk.LabelFrame(parent, text=f"센서 ID: {sensor_id}",
                                   font=("Arial", 12, "bold"),
                                   bg="#ECF0F1", fg="#2C3E50",
                                   relief="groove", bd=3)
        panel_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)

        # 상태 표시
        status_frame = tk.Frame(panel_frame, bg="#ECF0F1")
        status_frame.pack(fill="x", padx=10, pady=5)

        status_label = tk.Label(status_frame, text="● 연결 안됨",
                               font=("Arial", 11, "bold"),
                               bg="#ECF0F1", fg="#E74C3C")
        status_label.pack(side="left")

        # 시나리오 선택
        scenario_frame = tk.Frame(panel_frame, bg="#ECF0F1")
        scenario_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(scenario_frame, text="시나리오:",
                font=("Arial", 10, "bold"),
                bg="#ECF0F1").pack(anchor="w")

        scenario_combo = ttk.Combobox(scenario_frame, values=self.scenarios,
                                     state="readonly", width=20,
                                     font=("Arial", 10))
        scenario_combo.set("정상")
        scenario_combo.pack(fill="x", pady=5)

        # 버튼들
        button_frame = tk.Frame(panel_frame, bg="#ECF0F1")
        button_frame.pack(fill="x", padx=10, pady=5)

        connect_btn = tk.Button(button_frame, text="연결",
                               command=lambda: self._connect_sensor(sensor_id),
                               bg="#27AE60", fg="#FFFFFF",
                               font=("Arial", 10, "bold"),
                               width=10)
        connect_btn.pack(side="left", padx=5, pady=5)

        disconnect_btn = tk.Button(button_frame, text="연결 종료",
                                   command=lambda: self._disconnect_sensor(sensor_id),
                                   bg="#E74C3C", fg="#FFFFFF",
                                   font=("Arial", 10, "bold"),
                                   width=10)
        disconnect_btn.pack(side="left", padx=5, pady=5)

        start_btn = tk.Button(button_frame, text="전송 시작",
                             command=lambda: self._start_sending(sensor_id),
                             bg="#3498DB", fg="#FFFFFF",
                             font=("Arial", 10, "bold"),
                             width=10)
        start_btn.pack(side="left", padx=5, pady=5)

        # 패널 정보 저장
        return {
            "frame": panel_frame,
            "status_label": status_label,
            "scenario_combo": scenario_combo,
            "connect_btn": connect_btn,
            "disconnect_btn": disconnect_btn,
            "start_btn": start_btn
        }

    def _connect_sensor(self, sensor_id: str):
        """센서 연결"""
        host = self.host_entry.get()
        port = int(self.port_entry.get())

        # 이미 연결되어 있으면 종료
        if sensor_id in self.clients:
            self._disconnect_sensor(sensor_id)

        # 새 클라이언트 생성
        client = SensorClient(sensor_id, host, port)
        client.log_callback = self._log

        if client.connect():
            self.clients[sensor_id] = client
            panel = self.sensor_panels[sensor_id]
            panel["status_label"].config(text="● 연결됨", fg="#27AE60")
        else:
            self._log(f"[센서 {sensor_id}] 연결 실패")

    def _disconnect_sensor(self, sensor_id: str):
        """센서 연결 종료"""
        if sensor_id in self.clients:
            self.clients[sensor_id].disconnect()
            del self.clients[sensor_id]
            panel = self.sensor_panels[sensor_id]
            panel["status_label"].config(text="● 연결 안됨", fg="#E74C3C")

    def _start_sending(self, sensor_id: str):
        """데이터 전송 시작"""
        if sensor_id not in self.clients:
            self._log(f"[센서 {sensor_id}] 먼저 연결하세요")
            return

        client = self.clients[sensor_id]
        panel = self.sensor_panels[sensor_id]

        # 시나리오 설정
        scenario = panel["scenario_combo"].get()
        client.current_scenario = scenario

        # 전송 주기 설정
        try:
            interval = float(self.interval_entry.get())
            client.send_interval = interval
        except:
            pass

        # 전송 시작
        client.start_sending()
        self._log(f"[센서 {sensor_id}] 시나리오: {scenario}")

    def _clear_log(self):
        """로그 지우기"""
        self.log_text.delete(1.0, tk.END)

    def _log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_msg)
        self.log_text.see(tk.END)

    def run(self):
        """GUI 실행"""
        self.root.mainloop()

        # 종료 시 모든 연결 종료
        for client in self.clients.values():
            client.disconnect()


if __name__ == "__main__":
    root = tk.Tk()
    app = SensorSimulatorGUI(root)
    app.run()
