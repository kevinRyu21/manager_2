# -*- coding: utf-8 -*-
"""
5단계 경보 시스템 설정 UI

센서별 경보 레벨 임계값을 편집할 수 있는 설정 창을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ..config.manager import ConfigManager
import os
import configparser


class AlertSettingsDialog:
    """5단계 경보 시스템 설정 다이얼로그"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config = config_manager
        self.dialog = None
        self.entries = {}
        
        # 센서별 설정 정보 (타일 화면 순서와 동일, 아이콘 포함)
        self.sensor_configs = {
            "🏭 이산화탄소 (CO₂)": {
                "unit": "ppm",
                "type": "max",
                "keys": ["co2_normal_max", "co2_concern_max", "co2_caution_max", "co2_warning_max", "co2_danger_max"],
                "labels": ["정상 최대", "관심 최대", "주의 최대", "경계 최대", "심각 최대"]
            },
            "💨 산소 (O₂)": {
                "unit": "%",
                "type": "range",
                "keys": ["o2_normal_min", "o2_normal_max", "o2_concern_min", "o2_concern_max",
                        "o2_caution_min", "o2_caution_max", "o2_warning_min", "o2_warning_max",
                        "o2_danger_min", "o2_danger_max"],
                "labels": ["정상 최소", "정상 최대", "관심 최소", "관심 최대",
                          "주의 최소", "주의 최대", "경계 최소", "경계 최대",
                          "심각 최소", "심각 최대"]
            },
            "☠️ 황화수소 (H₂S)": {
                "unit": "ppm",
                "type": "max",
                "keys": ["h2s_normal_max", "h2s_concern_max", "h2s_caution_max", "h2s_warning_max", "h2s_danger_max"],
                "labels": ["정상 최대", "관심 최대", "주의 최대", "경계 최대", "심각 최대"]
            },
            "🔥 일산화탄소 (CO)": {
                "unit": "ppm",
                "type": "max",
                "keys": ["co_normal_max", "co_concern_max", "co_caution_max", "co_warning_max", "co_danger_max"],
                "labels": ["정상 최대", "관심 최대", "주의 최대", "경계 최대", "심각 최대"]
            },
            "⚡ 가연성가스 (LEL%)": {
                "unit": "%",
                "type": "max",
                "keys": ["lel_normal_max", "lel_concern_max", "lel_caution_max", "lel_warning_max", "lel_danger_max"],
                "labels": ["정상 최대", "관심 최대", "주의 최대", "경계 최대", "심각 최대"]
            },
            "🌫️ 연기 (Smoke)": {
                "unit": "ppm",
                "type": "max",
                "keys": ["smoke_normal_max", "smoke_concern_max", "smoke_caution_max", "smoke_warning_max", "smoke_danger_max"],
                "labels": ["정상 최대", "관심 최대", "주의 최대", "경계 최대", "심각 최대"]
            },
            "🌡️ 온도 (℃)": {
                "unit": "℃",
                "type": "range",
                "keys": ["temp_normal_min", "temp_normal_max", "temp_concern_min", "temp_concern_max",
                        "temp_caution_min", "temp_caution_max", "temp_warning_min", "temp_warning_max",
                        "temp_danger_min", "temp_danger_max"],
                "labels": ["정상 최소", "정상 최대", "관심 최소", "관심 최대",
                          "주의 최소", "주의 최대", "경계 최소", "경계 최대",
                          "심각 최소", "심각 최대"]
            },
            "💧 습도 (RH%)": {
                "unit": "%",
                "type": "range",
                "keys": ["hum_normal_min", "hum_normal_max", "hum_concern_min", "hum_concern_max",
                        "hum_caution_min", "hum_caution_max", "hum_warning_min", "hum_warning_max",
                        "hum_danger_min", "hum_danger_max"],
                "labels": ["정상 최소", "정상 최대", "관심 최소", "관심 최대",
                          "주의 최소", "주의 최대", "경계 최소", "경계 최대",
                          "심각 최소", "심각 최대"]
            },
            "누수 감지": {
                "unit": "",
                "type": "binary",
                "keys": ["water_normal", "water_warning"],
                "labels": ["정상", "경계"]
            }
        }
        
    def show(self):
        """설정 다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("5단계 경보 시스템 설정")
        self.dialog.geometry("1000x700")
        self.dialog.resizable(True, True)
        
        # 다이얼로그가 닫힐 때까지 대기
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_current_values()
        # 초기값 스냅샷 저장 (변경 감지용)
        self._initial_values = {k: str(self.config.std.get(k, "")) for k in self.entries.keys()}
        
        # 중앙 정렬 - 높이 10% 확장
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1300 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (990 // 2)
        self.dialog.geometry(f"1300x990+{x}+{y}")  # 높이 10% 확장 (900 -> 990)
        
    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 제목 - 폰트 크기 30% 증가
        title_label = ttk.Label(main_frame, text="5단계 경보 시스템 임계값 설정", 
                               font=("Arial", 21, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 센서별 설정을 3x3 그리드로 배치 (타일 화면과 동일한 순서)
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill="both", expand=True)
        
        # 그리드 설정
        grid_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")
        grid_frame.grid_rowconfigure((0, 1, 2), weight=1, uniform="row")
        
        # 센서 순서 (타일 화면과 동일, 아이콘 포함)
        sensor_order = [
            ("🏭 이산화탄소 (CO₂)", "co2"),
            ("💨 산소 (O₂)", "o2"),
            ("☠️ 황화수소 (H₂S)", "h2s"),
            ("🔥 일산화탄소 (CO)", "co"),
            ("⚡ 가연성가스 (LEL%)", "lel"),
            ("🌫️ 연기 (Smoke)", "smoke"),
            ("🌡️ 온도 (℃)", "temperature"),
            ("💧 습도 (RH%)", "humidity"),
            ("🚿 누수 감지", "water")
        ]
        
        # 센서별 설정 섹션을 그리드에 배치
        for idx, (sensor_name, sensor_key) in enumerate(sensor_order):
            row = idx // 3
            col = idx % 3
            
            config = self.sensor_configs[sensor_name]
            self._create_sensor_section(grid_frame, sensor_name, config, row, col)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # 기본값 복원 버튼 - 폰트 크기 증가
        reset_btn = ttk.Button(button_frame, text="국가 기준값 초기화", command=self._reset_to_defaults)
        reset_btn.pack(side="left", padx=(0, 10))
        
        # 저장 버튼 - 폰트 크기 증가
        save_btn = ttk.Button(button_frame, text="설정 저장", command=self._save_settings)
        save_btn.pack(side="right", padx=(10, 0))
        
        # 닫기 버튼 - 폰트 크기 증가
        cancel_btn = ttk.Button(button_frame, text="닫기", command=self._cancel)
        cancel_btn.pack(side="right")
        
    def _create_sensor_section(self, parent, sensor_name, config, row, col):
        """센서별 설정 섹션 생성 (그리드 배치)"""
        # 센서 프레임 - 제목 가운데 정렬
        sensor_frame = ttk.LabelFrame(parent, text=sensor_name, padding=8)
        sensor_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        
        # 센서 제목 가운데 정렬을 위한 스타일 설정
        style = ttk.Style()
        style.configure("Centered.TLabelframe.Label", anchor="center")
        sensor_frame.configure(style="Centered.TLabelframe")
        
        # 레벨별 설정 (5단계 완성)
        levels = ["정상", "관심", "주의", "경계", "심각"]
        level_colors = ["#2ECC71", "#F1C40F", "#E67E22", "#E74C3C", "#C0392B"]
        
        for i, level in enumerate(levels):
            level_frame = ttk.Frame(sensor_frame)
            level_frame.pack(fill="x", pady=1)
            
            # 레벨 라벨 (색상 포함) - 폰트 크기 30% 증가
            level_label = ttk.Label(level_frame, text=f"{level}:", width=6, font=("Arial", 12))
            level_label.pack(side="left")
            
            # 색상 표시 (작게)
            color_frame = tk.Frame(level_frame, width=12, height=12, bg=level_colors[i])
            color_frame.pack(side="left", padx=(2, 5))
            
            # 입력 필드들 (크기 30% 증가)
            if config["type"] == "range":
                # 범위 타입 (최소, 최대)
                min_key = config["keys"][i*2]
                max_key = config["keys"][i*2+1]
                
                min_entry = ttk.Entry(level_frame, width=8, font=("Arial", 11), justify="center")
                min_entry.pack(side="left", padx=(0, 2))
                min_entry.bind('<KeyRelease>', lambda e, k=min_key: self._on_value_change(k))
                self.entries[min_key] = min_entry
                # 개별 초기화 버튼 (최초 값으로 복원)
                min_reset_btn = ttk.Button(level_frame, text="↺", width=2,
                                           command=lambda k=min_key: self._reset_field_to_initial(k))
                min_reset_btn.pack(side="left", padx=(2, 6))
                
                ttk.Label(level_frame, text="~", font=("Arial", 11)).pack(side="left")
                
                max_entry = ttk.Entry(level_frame, width=8, font=("Arial", 11), justify="center")
                max_entry.pack(side="left", padx=(2, 2))
                max_entry.bind('<KeyRelease>', lambda e, k=max_key: self._on_value_change(k))
                self.entries[max_key] = max_entry
                # 개별 초기화 버튼
                max_reset_btn = ttk.Button(level_frame, text="↺", width=2,
                                           command=lambda k=max_key: self._reset_field_to_initial(k))
                max_reset_btn.pack(side="left", padx=(2, 6))
                
                ttk.Label(level_frame, text=config["unit"], font=("Arial", 11)).pack(side="left")
                
            elif config["type"] == "binary":
                # 이진 타입 (누수 센서) - 2단계 시스템
                if i == 0:  # 정상
                    ttk.Label(level_frame, text="정상 (0)", font=("Arial", 11)).pack(side="left")
                elif i == 4:  # 심각 (누수 감지)
                    ttk.Label(level_frame, text="누수감지 (1)", font=("Arial", 11)).pack(side="left")
                else:
                    ttk.Label(level_frame, text="-", font=("Arial", 11)).pack(side="left")
            else:
                # 최대값 타입
                max_key = config["keys"][i]
                max_entry = ttk.Entry(level_frame, width=8, font=("Arial", 11), justify="center")
                max_entry.pack(side="left", padx=(0, 2))
                max_entry.bind('<KeyRelease>', lambda e, k=max_key: self._on_value_change(k))
                self.entries[max_key] = max_entry
                # 개별 초기화 버튼
                max_reset_btn = ttk.Button(level_frame, text="↺", width=2,
                                           command=lambda k=max_key: self._reset_field_to_initial(k))
                max_reset_btn.pack(side="left", padx=(2, 6))
                
                ttk.Label(level_frame, text=f"이하 {config['unit']}", font=("Arial", 11)).pack(side="left")
                
    def _load_current_values(self):
        """현재 설정값 로드"""
        for key, entry in self.entries.items():
            value = self.config.std.get(key, "")
            if value != "":
                entry.insert(0, str(value))
                
    def _on_value_change(self, key):
        """값 변경 시 실시간 검증 및 자동 조정"""
        try:
            entry = self.entries[key]
            value = entry.get()
            
            if not value or not value.replace('.', '').replace('-', '').isdigit():
                return
                
            float_value = float(value)
            
            # 센서별 레벨 검증 및 자동 조정
            self._validate_and_adjust_levels(key, float_value, value)
            
        except (ValueError, KeyError):
            pass

    def _validate_and_adjust_levels(self, changed_key, new_value, new_value_str):
        """경보 레벨 검증 및 자동 조정"""
        # 센서별 레벨 매핑
        sensor_levels = {
            "o2": ["normal", "concern", "caution", "warning", "danger"],
            "co2": ["normal", "concern", "caution", "warning", "danger"],
            "co": ["normal", "concern", "caution", "warning", "danger"],
            "h2s": ["normal", "concern", "caution", "warning", "danger"],
            "temp": ["normal", "concern", "caution", "warning", "danger"],
            "hum": ["normal", "concern", "caution", "warning", "danger"],
            "lel": ["normal", "concern", "caution", "warning", "danger"],
            "smoke": ["normal", "concern", "caution", "warning", "danger"]
        }
        
        # 범위값 센서 (산소, 온도, 습도)
        range_sensors = ["o2", "temp", "hum"]
        
        # 변경된 키에서 센서와 레벨 추출
        for sensor, levels in sensor_levels.items():
            for level in levels:
                if f"{sensor}_{level}" in changed_key:
                    current_level_index = levels.index(level)
                    
                    # 하위(덜 심각한) 레벨들 자동 조정: 0..current_index-1
                    for i in range(0, current_level_index):
                        lower_level = levels[i]
                        lower_key = f"{sensor}_{lower_level}"
                        
                        # Max 값 조정: 상위(더 심각) 단계의 최대값이 작아지면 하위(덜 심각) 단계의 최대값은 그보다 클 수 없음
                        if "_max" in changed_key and f"{lower_key}_max" in self.entries:
                            current_lower_value = self.entries[f"{lower_key}_max"].get()
                            try:
                                lower_float_value = float(current_lower_value) if current_lower_value else new_value
                                # 하위단계 Max > 상위단계 Max 이면 하위를 상위로 낮춤
                                if lower_float_value > new_value:
                                    self.entries[f"{lower_key}_max"].delete(0, tk.END)
                                    self.entries[f"{lower_key}_max"].insert(0, new_value_str)
                                    print(f"자동 조정: {sensor} {lower_level} max = {new_value}")
                            except ValueError:
                                pass
                        
                        # Min 값 조정 (범위 센서만): 상위(더 심각) 단계의 최소값이 작아질수록 하위(덜 심각) 단계 최소값은 그보다 작아질 수 없음
                        if sensor in range_sensors and "_min" in changed_key and f"{lower_key}_min" in self.entries:
                            current_lower_value = self.entries[f"{lower_key}_min"].get()
                            try:
                                lower_float_value = float(current_lower_value) if current_lower_value else new_value
                                # 하위단계 Min < 상위단계 Min 이면 하위를 상위로 올림
                                if lower_float_value < new_value:
                                    self.entries[f"{lower_key}_min"].delete(0, tk.END)
                                    self.entries[f"{lower_key}_min"].insert(0, new_value_str)
                                    print(f"자동 조정: {sensor} {lower_level} min = {new_value}")
                            except ValueError:
                                pass
                    break
            
    def _reset_to_defaults(self):
        """국가 기준 기본값으로 복원"""
        # 국가 기준 기본값 미리보기 다이얼로그 표시
        preview_dialog = self._show_default_values_preview()
        if preview_dialog:
            # 확인 시 입력 필드에 기본값 설정 (외부 기본값 파일 우선)
            defaults = self._load_external_defaults()
            for key, entry in self.entries.items():
                default_value = defaults.get(key, self.config.std.get(key, ""))
                if default_value != "":
                    entry.delete(0, tk.END)
                    entry.insert(0, str(default_value))
            # 초기 스냅샷 갱신 (변경 비교 기준 업데이트)
            self._initial_values = {k: str(self.entries[k].get()) for k in self.entries.keys()}

    def _show_default_values_preview(self):
        """국가 기준 기본값 미리보기 다이얼로그"""
        # 외부 기본값 파일 로드 시도
        defaults = self._load_external_defaults()

        preview_window = tk.Toplevel(self.dialog)
        preview_window.title("국가 기준 기본값 미리보기")
        preview_window.geometry("800x660")  # 높이 10% 확장 (600 -> 660)
        preview_window.configure(bg="#F5F5F5")
        preview_window.transient(self.dialog)
        preview_window.attributes("-topmost", True)
        preview_window.grab_set()
        
        # 중앙 배치
        preview_window.update_idletasks()
        x = (preview_window.winfo_screenwidth() // 2) - (800 // 2)
        y = (preview_window.winfo_screenheight() // 2) - (660 // 2)
        preview_window.geometry(f"800x660+{x}+{y}")  # 높이 10% 확장 (600 -> 660)
        
        # 제목
        title_label = tk.Label(preview_window, text="국가 기준 기본값 미리보기",
                              font=("Pretendard", 16, "bold"),
                              bg="#F5F5F5", fg="#2C3E50")
        title_label.pack(pady=20)
        
        # 설명
        desc_label = tk.Label(preview_window, 
                             text="다음 값들로 초기화됩니다. 계속하시겠습니까?",
                             font=("Pretendard", 12),
                             bg="#F5F5F5", fg="#666666")
        desc_label.pack(pady=(0, 20))
        
        # 스크롤 가능한 프레임
        canvas = tk.Canvas(preview_window, bg="#F5F5F5")
        scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#F5F5F5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 마우스 휠 스크롤 바인딩 (Windows/macOS + Linux)
        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<Button-4>", _on_mousewheel)
        scrollable_frame.bind("<Button-5>", _on_mousewheel)

        # 센서별 기본값 표시
        sensors_info = [
            ("💨 산소 (O₂)", "%", "range", [
                ("정상", str(defaults.get("o2_normal_min", 19.5)), str(defaults.get("o2_normal_max", 23.0))),
                ("관심", str(defaults.get("o2_concern_min", 19.0)), str(defaults.get("o2_concern_max", 23.1))),
                ("주의", str(defaults.get("o2_caution_min", 18.5)), str(defaults.get("o2_caution_max", 23.3))),
                ("경계", str(defaults.get("o2_warning_min", 18.0)), str(defaults.get("o2_warning_max", 23.5))),
                ("심각", str(defaults.get("o2_danger_min", 17.0)), str(defaults.get("o2_danger_max", 24.0)))
            ]),
            ("🏭 이산화탄소 (CO₂)", "ppm", "max", [
                ("정상", "", str(defaults.get("co2_normal_max", 1000))),
                ("관심", "", str(defaults.get("co2_concern_max", 5000))),
                ("주의", "", str(defaults.get("co2_caution_max", 10000))),
                ("경계", "", str(defaults.get("co2_warning_max", 15000))),
                ("심각", "", str(defaults.get("co2_danger_max", 20000)))
            ]),
            ("🔥 일산화탄소 (CO)", "ppm", "max", [
                ("정상", "", str(defaults.get("co_normal_max", 5.0))),
                ("관심", "", str(defaults.get("co_concern_max", 10.0))),
                ("주의", "", str(defaults.get("co_caution_max", 30))),
                ("경계", "", str(defaults.get("co_warning_max", 50))),
                ("심각", "", str(defaults.get("co_danger_max", 100)))
            ]),
            ("☠️ 황화수소 (H₂S)", "ppm", "max", [
                ("정상", "", str(defaults.get("h2s_normal_max", 5))),
                ("관심", "", str(defaults.get("h2s_concern_max", 8))),
                ("주의", "", str(defaults.get("h2s_caution_max", 10))),
                ("경계", "", str(defaults.get("h2s_warning_max", 15))),
                ("심각", "", str(defaults.get("h2s_danger_max", 50)))
            ]),
            ("🌡️ 온도 (℃)", "℃", "range", [
                ("정상", str(defaults.get("temp_normal_min", 18)), str(defaults.get("temp_normal_max", 28))),
                ("관심", str(defaults.get("temp_concern_min", 16)), str(defaults.get("temp_concern_max", 30))),
                ("주의", str(defaults.get("temp_caution_min", 14)), str(defaults.get("temp_caution_max", 32))),
                ("경계", str(defaults.get("temp_warning_min", 12)), str(defaults.get("temp_warning_max", 33))),
                ("심각", str(defaults.get("temp_danger_min", 10)), str(defaults.get("temp_danger_max", 35)))
            ]),
            ("💧 습도 (RH%)", "%", "range", [
                ("정상", str(defaults.get("hum_normal_min", 40)), str(defaults.get("hum_normal_max", 60))),
                ("관심", str(defaults.get("hum_concern_min", 30)), str(defaults.get("hum_concern_max", 70))),
                ("주의", str(defaults.get("hum_caution_min", 20)), str(defaults.get("hum_caution_max", 80))),
                ("경계", str(defaults.get("hum_warning_min", 20)), str(defaults.get("hum_warning_max", 80))),
                ("심각", str(defaults.get("hum_danger_min", 15)), str(defaults.get("hum_danger_max", 85)))
            ]),
            ("⚡ 가연성가스 (LEL%)", "%", "max", [
                ("정상", "", str(defaults.get("lel_normal_max", 10))),
                ("관심", "", str(defaults.get("lel_concern_max", 20))),
                ("주의", "", str(defaults.get("lel_caution_max", 50))),
                ("경계", "", str(defaults.get("lel_warning_max", 50))),
                ("심각", "", str(defaults.get("lel_danger_max", 100)))
            ]),
            ("🌫️ 연기 (Smoke)", "ppm", "max", [
                ("정상", "", str(defaults.get("smoke_normal_max", 0))),
                ("관심", "", str(defaults.get("smoke_concern_max", 10))),
                ("주의", "", str(defaults.get("smoke_caution_max", 25))),
                ("경계", "", str(defaults.get("smoke_warning_max", 50))),
                ("심각", "", str(defaults.get("smoke_danger_max", 100)))
            ]),
            ("🌡️ 체감온도 (HI)", "℃", "max", [
                ("정상", "", str(defaults.get("hi_normal_max", 27.0))),
                ("관심", "", str(defaults.get("hi_concern_max", 32.0))),
                ("주의", "", str(defaults.get("hi_caution_max", 39.0))),
                ("경계", "", str(defaults.get("hi_warning_max", 40.0))),
                ("심각", "", str(defaults.get("hi_danger_max", 45.0)))
            ]),
            ("😓 불쾌지수 (DI)", "", "max", [
                ("정상", "", str(defaults.get("di_normal_max", 68.0))),
                ("관심", "", str(defaults.get("di_concern_max", 75.0))),
                ("주의", "", str(defaults.get("di_caution_max", 80.0))),
                ("경계", "", str(defaults.get("di_warning_max", 80.0))),
                ("심각", "", str(defaults.get("di_danger_max", 85.0)))
            ])
        ]
        
        for sensor_name, unit, sensor_type, levels in sensors_info:
            # 센서 프레임
            sensor_frame = tk.LabelFrame(scrollable_frame, text=sensor_name,
                                        font=("Pretendard", 12, "bold"),
                                        bg="#F5F5F5", fg="#2C3E50",
                                        padx=15, pady=10)
            sensor_frame.pack(fill="x", padx=20, pady=5)
            
            # 레벨별 값 표시
            level_colors = ["#2ECC71", "#F1C40F", "#E67E22", "#E74C3C", "#C0392B"]
            level_names = ["정상", "관심", "주의", "경계", "심각"]
            
            for i, (level_name, min_val, max_val) in enumerate(levels):
                level_frame = tk.Frame(sensor_frame, bg="#F5F5F5")
                level_frame.pack(fill="x", pady=2)
                
                # 레벨 라벨 (색상 포함)
                level_label = tk.Label(level_frame, text=f"{level_names[i]}:",
                                     font=("Pretendard", 10, "bold"),
                                     bg="#F5F5F5", fg=level_colors[i], width=8, anchor="w")
                level_label.pack(side="left", padx=(0, 10))
                
                # 색상 표시
                color_frame = tk.Frame(level_frame, width=12, height=12, bg=level_colors[i])
                color_frame.pack(side="left", padx=(0, 10))
                
                # 값 표시
                if sensor_type == "range":
                    if min_val and max_val:
                        value_text = f"{min_val} ~ {max_val} {unit}"
                    else:
                        value_text = f"{max_val} {unit}"
                else:
                    value_text = f"{max_val} 이하 {unit}"
                
                value_label = tk.Label(level_frame, text=value_text,
                                     font=("Pretendard", 10),
                                     bg="#F5F5F5", fg="#333333")
                value_label.pack(side="left")
        
        # 스크롤바와 캔버스 배치
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        # 버튼 프레임
        button_frame = tk.Frame(preview_window, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=30)
        
        # 확인 버튼
        confirm_btn = tk.Button(button_frame, text="확인",
                               command=lambda: self._confirm_reset(preview_window),
                               bg="#27AE60", fg="#FFFFFF",
                               font=("Pretendard", 12, "bold"),
                               relief="raised", bd=3, width=10, height=2)
        confirm_btn.pack(side="left", padx=5)
        
        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="취소",
                               command=preview_window.destroy,
                               bg="#95A5A6", fg="#FFFFFF",
                               font=("Pretendard", 12, "bold"),
                               relief="raised", bd=3, width=10, height=2)
        cancel_btn.pack(side="right", padx=5)
        
        # 결과 저장 변수
        self._reset_confirmed = False
        
        # 다이얼로그가 닫힐 때까지 대기
        preview_window.wait_window()
        
        return self._reset_confirmed

    def _confirm_reset(self, preview_window):
        """초기화 확인"""
        self._reset_confirmed = True
        preview_window.destroy()

    def _reset_field_to_initial(self, key):
        """특정 필드를 최초 값으로 복원. 상위(더 심각) 레벨 복원 시 하위(덜 심각)도 함께 복원"""
        try:
            if not hasattr(self, '_initial_values'):
                return
            # 현재 키 복원
            initial_val = self._initial_values.get(key)
            if initial_val is not None and key in self.entries:
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, str(initial_val))

            # 센서와 레벨, 필드(min/max) 파싱
            # key 예: "co2_concern_max", "o2_warning_min"
            parts = key.split('_')
            if len(parts) < 3:
                return
            sensor = parts[0]
            field = parts[-1]  # min or max
            level = '_'.join(parts[1:-1])  # normal, concern, caution, warning, danger

            levels_order = ["normal", "concern", "caution", "warning", "danger"]
            if level not in levels_order:
                return
            level_index = levels_order.index(level)

            # 상위(더 심각) 복원 시 하위(덜 심각)도 복원: 하위는 indices 0..level_index-1
            # 하위를 복원하는 경우(낮은 인덱스)에는 상위는 복원하지 않음 (요구사항)
            # 따라서 언제나 하위들(0..level_index-1)에 대해서만 복원 실행
            if level_index > 0:
                for i in range(0, level_index):
                    lower_level = levels_order[i]
                    lower_key = f"{sensor}_{lower_level}_{field}"
                    if lower_key in self.entries and lower_key in self._initial_values:
                        init_val = self._initial_values[lower_key]
                        self.entries[lower_key].delete(0, tk.END)
                        self.entries[lower_key].insert(0, str(init_val))

            # 변경 반영 후 검증 로직 실행 (실시간 규칙 유지)
            self._on_value_change(key)
        except Exception:
            pass

    def _load_external_defaults(self):
        """외부 기본값 파일(standard_defaults.conf)의 [STANDARD]를 읽어 dict로 반환 - 매번 최신 파일 읽기"""
        defaults_path = os.path.join(os.path.dirname(self.config.path), "standard_defaults.conf")
        if not os.path.exists(defaults_path):
            print(f"표준 기본값 파일이 없습니다: {defaults_path}")
            # fallback: 현재 config.std 반환
            return dict(self.config.std)
        try:
            parser = configparser.ConfigParser()
            # 매번 파일을 새로 읽기 (캐시 사용 안함)
            parser.read(defaults_path, encoding="utf-8")
            if "STANDARD" not in parser:
                print("표준 기본값 파일에 [STANDARD] 섹션이 없습니다.")
                return dict(self.config.std)
            
            std = {}
            for k, v in parser["STANDARD"].items():
                try:
                    std[k] = float(v)
                except Exception:
                    std[k] = v
            
            print(f"표준 기본값 파일 로드 완료: {len(std)}개 항목")
            return std
        except Exception as e:
            print(f"표준 기본값 파일 읽기 실패: {e}")
            return dict(self.config.std)
                
    def _save_settings(self):
        """설정 저장"""
        try:
            # 변경된 키만 추출
            changed_keys = []
            for key, entry in self.entries.items():
                new_val = entry.get()
                old_val = self._initial_values.get(key, "")
                if str(new_val) != str(old_val):
                    changed_keys.append(key)

            # 저장 전 검증 (변경된 상위 단계로 인해 영향받는 하위 단계만 계산)
            validation_result = self._validate_all_levels(changed_keys)
            if validation_result['needs_adjustment']:
                # 자동 조정 확인 다이얼로그
                result = messagebox.askyesno(
                    "경보 레벨 자동 조정",
                    f"상위 단계 조정으로 인해 다음 하위 단계들이 자동으로 조정됩니다:\n\n{validation_result['message']}\n\n계속하시겠습니까?",
                    parent=self.dialog
                )
                if not result:
                    return
                
                # 자동 조정 실행
                self._apply_auto_adjustments(validation_result['adjustments'])

            # 입력값 검증 및 저장
            for key, entry in self.entries.items():
                value = float(entry.get())
                self.config.std[key] = value
                
            # 파일 저장
            self.config.save()
            
            # 실시간 적용을 위해 부모 앱에 알림
            if hasattr(self.parent, 'refresh_alert_thresholds'):
                self.parent.refresh_alert_thresholds()
            
            messagebox.showinfo("저장 완료", "설정이 성공적으로 저장되었습니다.")
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("입력 오류", "모든 값은 숫자여야 합니다.")
        except Exception as e:
            messagebox.showerror("저장 오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")

    def _validate_all_levels(self, changed_keys):
        """전체 경보 레벨 검증"""
        adjustments = []
        message_parts = []
        
        sensor_levels = {
            "o2": ["normal", "concern", "caution", "warning", "danger"],
            "co2": ["normal", "concern", "caution", "warning", "danger"],
            "co": ["normal", "concern", "caution", "warning", "danger"],
            "h2s": ["normal", "concern", "caution", "warning", "danger"],
            "temp": ["normal", "concern", "caution", "warning", "danger"],
            "hum": ["normal", "concern", "caution", "warning", "danger"],
            "lel": ["normal", "concern", "caution", "warning", "danger"],
            "smoke": ["normal", "concern", "caution", "warning", "danger"]
        }
        sensor_kor = {
            "o2": "산소",
            "co2": "이산화탄소",
            "co": "일산화탄소",
            "h2s": "황화수소",
            "temp": "온도",
            "hum": "습도",
            "lel": "가연성가스",
            "smoke": "연기"
        }
        level_kor = {
            "normal": "정상",
            "concern": "관심",
            "caution": "주의",
            "warning": "경계",
            "danger": "심각"
        }
        
        # 범위값 센서 (산소, 온도, 습도)
        range_sensors = ["o2", "temp", "hum"]
        
        for sensor, levels in sensor_levels.items():
            for i, level in enumerate(levels):
                current_level = level
                # 변경된 상위(더 심각) 레벨에 한해서만 하위(덜 심각) 영향 계산
                consider_max = f"{sensor}_{current_level}_max" in changed_keys
                consider_min = f"{sensor}_{current_level}_min" in changed_keys if sensor in range_sensors else False

                # 하위 인덱스(덜 심각)들만 검사: 0..i-1
                for j in range(0, i):
                    lower_level = levels[j]

                    # Max 값 검증: 하위단계 Max > 상위단계 Max 이면 하위를 상위로 낮춤
                    current_max_key = f"{sensor}_{current_level}_max"
                    lower_max_key = f"{sensor}_{lower_level}_max"
                    if consider_max and current_max_key in self.entries and lower_max_key in self.entries:
                        try:
                            current_max = float(self.entries[current_max_key].get())
                            lower_max = float(self.entries[lower_max_key].get())
                            if lower_max > current_max:
                                adjustments.append({
                                    'sensor': sensor,
                                    'level': lower_level,
                                    'field': 'max',
                                    'old_value': lower_max,
                                    'new_value': current_max
                                })
                                message_parts.append(f"{sensor_kor.get(sensor, sensor)} {level_kor[lower_level]} 최대값: {lower_max} → {current_max}")
                        except ValueError:
                            pass

                    # Min 값 검증 (범위 센서만): 하위단계 Min < 상위단계 Min 이면 하위를 상위로 올림
                    if sensor in range_sensors and consider_min:
                        current_min_key = f"{sensor}_{current_level}_min"
                        lower_min_key = f"{sensor}_{lower_level}_min"
                        if current_min_key in self.entries and lower_min_key in self.entries:
                            try:
                                current_min = float(self.entries[current_min_key].get())
                                lower_min = float(self.entries[lower_min_key].get())
                                if lower_min < current_min:
                                    adjustments.append({
                                        'sensor': sensor,
                                        'level': lower_level,
                                        'field': 'min',
                                        'old_value': lower_min,
                                        'new_value': current_min
                                    })
                                    message_parts.append(f"{sensor_kor.get(sensor, sensor)} {level_kor[lower_level]} 최소값: {lower_min} → {current_min}")
                            except ValueError:
                                pass
        
        return {
            'needs_adjustment': len(adjustments) > 0,
            'adjustments': adjustments,
            'message': '\n'.join(message_parts)
        }

    def _apply_auto_adjustments(self, adjustments):
        """자동 조정 적용"""
        for adj in adjustments:
            key = f"{adj['sensor']}_{adj['level']}_{adj['field']}"
            if key in self.entries:
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, str(adj['new_value']))
            
    def _cancel(self):
        """취소"""
        self.dialog.destroy()
