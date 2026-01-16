"""
센서 패널용 도면 뷰

각 센서별 도면 이미지 표시, 센서/모니터 위치 설정, 드래그 앤 드롭, 줌/팬 기능을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import json
import math

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_OK = True
except Exception:
    PIL_OK = False


class PanelBlueprintView(tk.Frame):
    """센서 패널용 도면 뷰"""

    def __init__(self, parent, panel, app):
        super().__init__(parent, bg="#2C3E50")
        self.panel = panel  # SensorPanel 참조
        self.app = app
        self.sid = panel.sid
        self.peer = panel.peer

        self.blueprint_dir = os.path.join(os.getcwd(), "blueprints")
        self.blueprint_data_dir = os.path.join(os.getcwd(), "blueprint_data")

        # 디렉토리 생성
        os.makedirs(self.blueprint_dir, exist_ok=True)
        os.makedirs(self.blueprint_data_dir, exist_ok=True)

        # 현재 도면 정보
        self.current_blueprint = None  # 파일명
        self.blueprint_image = None  # PIL Image
        self.blueprint_photo = None  # PhotoImage

        # 줌/팬 상태
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = None
        self.drag_start_y = None

        # 센서/모니터 아이템
        # sensors: 센서 이름 위치(x,y), 센서값 아이콘들(individual_items)
        self.sensors = []  # [{"sid": str, "panel_key": str, "x": float, "y": float, "individual_items": [{"key": str, "x": float, "y": float}, ...]}, ...]
        self.monitors = []  # [{"name": str, "x": float, "y": float}, ...]

        # 드래그 중인 아이템
        self.dragging_item = None  # {"type": "sensor|monitor|individual_item", "index": int, "sub_index": int (for individual_item)}

        # 도면 편집 잠금 상태
        self.blueprint_locked = True  # 기본적으로 잠김

        # 화재 경보 상태
        self._fire_alert_data = {
            "level": 1,  # 현재 경보 레벨
            "probability": 0.0,  # 화재 확률
            "triggered_sensors": [],  # 경보 발생 센서 목록
            "sensor_values": {}  # 센서별 값
        }

        # UI 생성
        self._create_ui()

        # 도면 목록 로드
        self._load_blueprint_list()

    def _create_ui(self):
        """UI 생성"""
        # 상단 컨트롤 패널
        control_frame = tk.Frame(self, bg="#34495E", height=80)
        control_frame.pack(side="top", fill="x", padx=10, pady=10)
        control_frame.pack_propagate(False)

        # 도면 편집 잠금/해제 버튼 (관리자 모드일 때만 표시)
        self.lock_button = tk.Button(control_frame, text="🔒 도면 설정 활성화",
                                     command=self._toggle_blueprint_lock,
                                     bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                     relief="raised", bd=3, width=18, height=2,
                                     activebackground="#C0392B", activeforeground="#FFFFFF")
        
        # 관리자 모드일 때만 버튼 표시
        if self.app.cfg.admin_mode:
            self.lock_button.pack(side="left", padx=5)

        # 도면 설정 버튼
        self.blueprint_settings_btn = tk.Button(control_frame, text="도면 설정",
                                               command=self._open_blueprint_manager,
                                               bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                               relief="raised", bd=3, width=12, height=2,
                                               activebackground="#2980B9", activeforeground="#FFFFFF")
        # 초기에는 숨김 (잠금 상태)

        # 도면 선택 라벨과 콤보박스
        self.blueprint_select_label = tk.Label(control_frame, text="도면 선택:", bg="#34495E", fg="#FFFFFF",
                                              font=("Pretendard", 12, "bold"))
        # 초기에는 숨김

        self.blueprint_combo = ttk.Combobox(control_frame, state="readonly", width=45,
                                           font=("Pretendard", 12))
        self.blueprint_combo.bind("<<ComboboxSelected>>", self._on_blueprint_selected)
        # 초기에는 숨김

        # 센서 추가 버튼 (모든 연결된 센서 선택 가능)
        self.add_sensor_btn = tk.Button(control_frame, text="➕ 센서 추가", command=self._add_sensor,
                                       bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                       relief="raised", bd=3, width=14, height=2,
                                       activebackground="#229954", activeforeground="#FFFFFF")
        # 초기에는 숨김

        # 모니터 추가 버튼
        self.add_monitor_btn = tk.Button(control_frame, text="➕ 모니터 추가", command=self._add_monitor,
                                        bg="#F39C12", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                        relief="raised", bd=3, width=12, height=2,
                                        activebackground="#E67E22", activeforeground="#FFFFFF")
        # 초기에는 숨김

        # 줌 컨트롤
        tk.Button(control_frame, text="🔍+", command=self._zoom_in,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 relief="raised", bd=2, width=5, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=2)

        tk.Button(control_frame, text="🔍-", command=self._zoom_out,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 relief="raised", bd=2, width=5, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=2)

        tk.Button(control_frame, text="초기화", command=self._reset_view,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 relief="raised", bd=2, width=8, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=2)

        # 캔버스 (도면 표시)
        self.canvas = tk.Canvas(self, bg="#1C2833", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 캔버스 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<ButtonPress-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _toggle_blueprint_lock(self):
        """도면 편집 잠금/해제 토글"""
        if self.blueprint_locked:
            # 잠금 해제 시도 - 관리자 모드이거나 비밀번호 확인
            if self.app.cfg.admin_mode:
                # 관리자 모드면 즉시 해제
                self._unlock_blueprint()
            else:
                # 비밀번호 확인
                if self._verify_blueprint_password():
                    self._unlock_blueprint()
        else:
            # 잠금
            self._lock_blueprint()

    def _verify_blueprint_password(self):
        """도면 편집 비밀번호 확인"""
        import hashlib

        # config에서 해시된 비밀번호 가져오기
        settings_password_hash = self.app.cfg.ui.get("settings_password_hash", None)

        # 비밀번호가 설정되지 않았으면 바로 통과
        if not settings_password_hash:
            return True

        # 비밀번호 입력 다이얼로그
        dialog = tk.Toplevel(self.app)
        dialog.title("도면 설정 권한 확인")
        dialog.geometry("500x280")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (140)
        dialog.geometry(f"500x280+{x}+{y}")

        result = [False]

        # 제목
        tk.Label(dialog, text="도면 설정 권한 확인",
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=20)

        # 입력 프레임
        input_frame = tk.Frame(dialog, bg="#F5F5F5")
        input_frame.pack(pady=15, padx=40, fill="x")

        tk.Label(input_frame, text="비밀번호:",
                font=("Pretendard", 13, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(anchor="w", pady=(0, 8))

        password_entry = tk.Entry(input_frame, font=("Pretendard", 14), show="*", width=30, relief="solid", bd=2)
        password_entry.pack(fill="x", ipady=10)
        password_entry.focus()

        # 버튼 프레임
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=40)

        def on_verify():
            password = password_entry.get()
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            if password_hash == settings_password_hash:
                result[0] = True
                dialog.destroy()
            else:
                messagebox.showerror("인증 실패", "비밀번호가 올바르지 않습니다.", parent=dialog)
                password_entry.delete(0, tk.END)
                password_entry.focus()

        def on_cancel():
            dialog.destroy()

        tk.Button(button_frame, text="✓ 확인", command=on_verify,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=5, ipady=12)

        tk.Button(button_frame, text="✕ 취소", command=on_cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5, ipady=12)

        password_entry.bind("<Return>", lambda e: on_verify())

        dialog.wait_window()
        return result[0]

    def _unlock_blueprint(self):
        """도면 편집 잠금 해제"""
        self.blueprint_locked = False
        self.lock_button.config(text="🔓 도면 설정 비활성화", bg="#27AE60", activebackground="#229954")

        # 버튼들 표시
        self.blueprint_settings_btn.pack(side="left", padx=5)
        self.blueprint_select_label.pack(side="left", padx=(20, 5))
        self.blueprint_combo.pack(side="left", padx=5)
        self.add_sensor_btn.pack(side="left", padx=5)
        self.add_monitor_btn.pack(side="left", padx=5)

    def _lock_blueprint(self):
        """도면 편집 잠금"""
        self.blueprint_locked = True
        self.lock_button.config(text="🔒 도면 설정 활성화", bg="#E74C3C", activebackground="#C0392B")

        # 버튼들 숨김
        self.blueprint_settings_btn.pack_forget()
        self.blueprint_select_label.pack_forget()
        self.blueprint_combo.pack_forget()
        self.add_sensor_btn.pack_forget()
        self.add_monitor_btn.pack_forget()

    def _load_blueprint_list(self):
        """도면 목록 로드"""
        if not os.path.exists(self.blueprint_dir):
            return

        blueprints = []
        for filename in os.listdir(self.blueprint_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                blueprints.append(filename)

        blueprints.sort()
        self.blueprint_combo['values'] = blueprints

        if blueprints:
            self.blueprint_combo.current(0)
            self._on_blueprint_selected(None)

    def _open_blueprint_manager(self):
        """도면 관리자 열기"""
        from .blueprint_manager import BlueprintManager
        manager = BlueprintManager(self.app)
        manager.show()
        # 다이얼로그 닫힌 후 목록 새로고침
        self._load_blueprint_list()

    def _on_blueprint_selected(self, event):
        """도면 선택 이벤트"""
        selected = self.blueprint_combo.get()
        if not selected:
            return

        self.current_blueprint = selected
        self._load_blueprint_image()
        self._load_blueprint_data()
        self._reset_view()
        self._redraw_canvas()

    def _load_blueprint_image(self):
        """도면 이미지 로드"""
        if not self.current_blueprint or not PIL_OK:
            return

        try:
            filepath = os.path.join(self.blueprint_dir, self.current_blueprint)
            self.blueprint_image = Image.open(filepath)
        except Exception as e:
            messagebox.showerror("오류", f"도면 이미지 로드 실패:\n{str(e)}")
            self.blueprint_image = None

    def _load_blueprint_data(self):
        """도면 데이터 로드 (도면 단위로 저장됨)"""
        if not self.current_blueprint:
            return

        data_filename = os.path.splitext(self.current_blueprint)[0] + ".json"
        data_filepath = os.path.join(self.blueprint_data_dir, data_filename)

        self.sensors = []
        self.monitors = []

        if os.path.exists(data_filepath):
            try:
                with open(data_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sensors = data.get("sensors", [])
                    self.monitors = data.get("monitors", [])
            except Exception as e:
                print(f"도면 데이터 로드 실패: {e}")

    def _save_blueprint_data(self):
        """도면 데이터 저장 (도면 단위로 저장)"""
        if not self.current_blueprint:
            return

        data_filename = os.path.splitext(self.current_blueprint)[0] + ".json"
        data_filepath = os.path.join(self.blueprint_data_dir, data_filename)

        data = {
            "sensors": self.sensors,
            "monitors": self.monitors
        }

        try:
            with open(data_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"도면 데이터 저장 실패: {e}")

    def _reset_view(self):
        """뷰 초기화 (줌/팬 리셋)"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

    def _zoom_in(self):
        """줌 인"""
        self.zoom_level = min(self.zoom_level * 1.2, 5.0)
        self._redraw_canvas()

    def _zoom_out(self):
        """줌 아웃"""
        self.zoom_level = max(self.zoom_level / 1.2, 0.2)
        self._redraw_canvas()

    def _on_mouse_wheel(self, event):
        """마우스 휠로 줌"""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _on_canvas_resize(self, event):
        """캔버스 크기 변경 시"""
        self._redraw_canvas()

    def refresh_display(self):
        """디스플레이 새로고침 (실시간 센서 값 업데이트용)"""
        self._redraw_canvas()

    def _redraw_canvas(self):
        """캔버스 재그리기"""
        self.canvas.delete("all")

        if not self.blueprint_image or not PIL_OK:
            self.canvas.create_text(self.canvas.winfo_width() // 2,
                                   self.canvas.winfo_height() // 2,
                                   text="도면을 선택하세요",
                                   fill="#FFFFFF", font=("Pretendard", 16, "bold"))
            return

        # 캔버스 크기
        canvas_width = max(self.canvas.winfo_width(), 100)
        canvas_height = max(self.canvas.winfo_height(), 100)

        # 이미지 크기 (줌 적용)
        img_width = int(self.blueprint_image.width * self.zoom_level)
        img_height = int(self.blueprint_image.height * self.zoom_level)

        # 이미지 리사이즈
        resized_image = self.blueprint_image.resize((img_width, img_height), Image.LANCZOS)

        # 오버레이를 더 큰 크기로 생성 (도면 밖에도 아이콘 배치 가능)
        # 오버레이는 이미지 크기의 3배로 생성 (여백 포함)
        overlay_width = img_width * 3
        overlay_height = img_height * 3
        overlay = Image.new('RGBA', (overlay_width, overlay_height), (0, 0, 0, 0))

        # 오버레이 중앙에 도면 이미지 배치할 위치 계산
        offset_x = img_width
        offset_y = img_height

        # 이미지 합성 (먼저 도면 이미지를 오버레이 중앙에 배치)
        if resized_image.mode != 'RGBA':
            resized_image = resized_image.convert('RGBA')

        # 오버레이에 도면 이미지를 중앙에 붙여넣기
        overlay.paste(resized_image, (offset_x, offset_y), resized_image if resized_image.mode == 'RGBA' else None)

        # 이제 오버레이 위에 센서/모니터 그리기 (도면 위에 표시됨)
        draw = ImageDraw.Draw(overlay)

        # 센서 그리기 (오프셋 적용)
        for sensor in self.sensors:
            x = sensor["x"] * img_width + offset_x
            y = sensor["y"] * img_height + offset_y
            self._draw_sensor_on_image(draw, x, y, sensor)

        # 모니터 그리기 (오프셋 적용)
        for monitor in self.monitors:
            x = monitor["x"] * img_width + offset_x
            y = monitor["y"] * img_height + offset_y
            self._draw_monitor_on_image(draw, x, y, monitor)

        # 화재 경보 오버레이 그리기 (센서/모니터 위에 표시)
        self._draw_fire_alert_overlay(draw, img_width, img_height, offset_x, offset_y)

        # PhotoImage로 변환
        self.blueprint_photo = ImageTk.PhotoImage(overlay)

        # 캔버스에 이미지 표시 (팬 적용)
        x_pos = canvas_width // 2 + self.pan_x
        y_pos = canvas_height // 2 + self.pan_y
        self.canvas.create_image(x_pos, y_pos, image=self.blueprint_photo, anchor="center")

    def _draw_sensor_on_image(self, draw, x, y, sensor):
        """이미지에 센서 그리기 (개별 센서값 표시만)"""
        # 고정 크기 (줌과 무관)
        base_radius = 40  # 개별 센서 원 반경

        # 센서별로 고유한 색상 할당 (sid 기반)
        sensor_sid = sensor.get("sid", self.sid)
        sensor_color = self._get_sensor_color(sensor_sid)

        # 개별 센서값 표기 (원형 아이콘 + 값) - 각각 독립적으로 배치
        # PIL ImageDraw는 이모지를 지원하지 않으므로 간단한 텍스트 사용
        sensor_keys = ["co2", "h2s", "co", "o2", "lel", "smoke", "temperature", "humidity", "water"]
        labels = ["CO2", "H2S", "CO", "O2", "LEL", "Smoke", "Temp", "Humi", "Water"]

        # individual_items가 없으면 초기화 (원형 배치)
        if "individual_items" not in sensor or not sensor["individual_items"]:
            sensor["individual_items"] = []
            default_radius = 150  # 픽셀 단위 (도면 밖으로 나가지 않도록)
            for i, key in enumerate(sensor_keys):
                angle = (i * 60 - 90) * math.pi / 180
                # 비율이 아닌 픽셀 오프셋으로 계산
                offset_x = default_radius * math.cos(angle) / self.blueprint_image.width
                offset_y = default_radius * math.sin(angle) / self.blueprint_image.height
                rel_x = sensor["x"] + offset_x
                rel_y = sensor["y"] + offset_y
                sensor["individual_items"].append({"key": key, "x": rel_x, "y": rel_y})

        # 폰트 로드 (Linux/Windows 모두 지원)
        font_name = None
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/pretendard/Pretendard-Regular.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_name = ImageFont.truetype(font_path, 14)
                    break
                except:
                    continue
        if font_name is None:
            font_name = ImageFont.load_default()

        # 좌표 계산을 위한 변수
        img_width_zoomed = self.blueprint_image.width * self.zoom_level
        img_height_zoomed = self.blueprint_image.height * self.zoom_level
        sensor_rel_x = sensor["x"]
        sensor_rel_y = sensor["y"]

        # 반투명 선 색상
        line_color = sensor_color[:3] + (100,)  # 반투명 (alpha=100)

        # 각 센서 아이템 그리기
        for i, item in enumerate(sensor["individual_items"]):
            key = item["key"]
            # item의 비율 좌표를 절대 좌표로 변환
            item_rel_x = item["x"]
            item_rel_y = item["y"]
            item_x = x + (item_rel_x - sensor_rel_x) * img_width_zoomed
            item_y = y + (item_rel_y - sensor_rel_y) * img_height_zoomed

            label = labels[sensor_keys.index(key)]

            # 센서 값과 임계값 상태 가져오기
            value, is_ok, alert_level = self._get_sensor_value_with_status(sensor_sid, key)

            # 경보 레벨에 따른 색상 결정
            if alert_level == 1:  # 정상
                color = sensor_color
            elif alert_level == 2:  # 관심
                color = (241, 196, 15, 255)  # 노랑
            elif alert_level == 3:  # 주의
                color = (230, 126, 34, 255)  # 주황
            elif alert_level == 4:  # 경계
                color = (231, 76, 60, 255)   # 빨강
            elif alert_level == 5:  # 심각
                color = (192, 57, 43, 255)  # 진홍
            else:
                color = sensor_color

            # 센서 아이템에서 센서 이름으로 반투명 선 그리기
            draw.line([(item_x, item_y), (x, y)], fill=line_color, width=1)

            # 원 그리기 (고정 크기)
            draw.ellipse([item_x - base_radius, item_y - base_radius,
                        item_x + base_radius, item_y + base_radius],
                       fill=color, outline=(255, 255, 255, 255), width=2)

            # 텍스트 (라벨 + 값) - Linux/Windows 모두 지원
            font_label = None
            font_value = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_label = ImageFont.truetype(font_path, 16)
                        font_value = ImageFont.truetype(font_path, 18)
                        break
                    except:
                        continue

            # 라벨 (위) - 폰트가 없으면 기본 폰트 사용 (anchor 미지원)
            if font_label:
                draw.text((item_x, item_y - 10), label,
                         fill=(255, 255, 255, 255), font=font_label, anchor="mm")
                # 값 (아래)
                draw.text((item_x, item_y + 10), value,
                         fill=(255, 255, 255, 255), font=font_value, anchor="mm")
            else:
                # 기본 폰트 - anchor 지원 안할 수 있음
                default_font = ImageFont.load_default()
                # 텍스트 바운딩박스 계산하여 중앙 정렬
                try:
                    label_bbox = draw.textbbox((0, 0), label, font=default_font)
                    label_w = label_bbox[2] - label_bbox[0]
                    value_bbox = draw.textbbox((0, 0), value, font=default_font)
                    value_w = value_bbox[2] - value_bbox[0]
                except:
                    label_w = len(label) * 6
                    value_w = len(value) * 6
                draw.text((item_x - label_w // 2, item_y - 15), label,
                         fill=(255, 255, 255, 255), font=default_font)
                draw.text((item_x - value_w // 2, item_y + 5), value,
                         fill=(255, 255, 255, 255), font=default_font)

        # 센서 이름 배경 (원형) - 맨 위에 그리기
        name_bg_radius = 35
        # 반투명 색상으로 변경 (alpha=220)
        sensor_color_transparent = sensor_color[:3] + (220,)
        draw.ellipse([x - name_bg_radius, y - name_bg_radius,
                     x + name_bg_radius, y + name_bg_radius],
                   fill=sensor_color_transparent, outline=(255, 255, 255, 255), width=3)

        # display_name이 있으면 사용, 없으면 sid 사용
        display_name = sensor.get("display_name", sensor_sid)
        draw.text((x, y), display_name, fill=(255, 255, 255, 255), font=font_name, anchor="mm")

    def _get_sensor_color(self, sid):
        """센서별 고유 색상 반환 (sid 기반 해시)"""
        # sid를 숫자로 변환하여 색상 생성
        hash_val = sum(ord(c) for c in sid)
        colors = [
            (52, 152, 219, 220),   # 파랑
            (46, 204, 113, 220),   # 초록
            (155, 89, 182, 220),   # 보라
            (230, 126, 34, 220),   # 주황
            (26, 188, 156, 220),   # 청록
            (241, 196, 15, 220),   # 노랑
            (231, 76, 60, 220),    # 빨강
            (149, 165, 166, 220),  # 회색
        ]
        return colors[hash_val % len(colors)]

    def _draw_monitor_on_image(self, draw, x, y, monitor):
        """이미지에 모니터 그리기 (고정 크기)"""
        # 사각형 아이콘 (고정 크기)
        width = 70
        height = 45
        draw.rectangle([x - width//2, y - height//2, x + width//2, y + height//2],
                      fill=(243, 156, 18, 220), outline=(255, 255, 255, 255), width=2)

        # 모니터 이름 - Linux/Windows 모두 지원
        name = monitor.get("name", "모니터")
        font = None
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/pretendard/Pretendard-Regular.otf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 12)
                    break
                except:
                    continue
        if font is None:
            font = ImageFont.load_default()
        draw.text((x, y), name, fill=(255, 255, 255, 255), font=font, anchor="mm")

    def _get_sensor_value(self, sid, key):
        """센서 값 가져오기 (실시간) - 다른 센서의 값도 가져올 수 있음"""
        value_str, _, _ = self._get_sensor_value_with_status(sid, key)
        return value_str

    def _get_sensor_value_with_status(self, sid, key):
        """센서 값과 임계값 상태 가져오기 (실시간)

        Returns:
            tuple: (값 문자열, 정상 여부, 경보 레벨)
        """
        # 해당 센서의 패널 찾기
        target_panel = None
        for panel_key, panel in self.app.panels.items():
            if panel_key == "__waiting__":
                continue
            # panel의 sid와 비교
            if hasattr(panel, 'sid') and panel.sid == sid:
                target_panel = panel
                break

        # 패널에서 데이터 가져오기 (타일과 동일한 방식)
        value = None
        if target_panel and hasattr(target_panel, 'data'):
            value = target_panel.data.get(key)

        # 가연성가스와 연기는 더미 센서이므로 접속 대기 상태로 처리 (타일과 동일)
        # -1 값이 들어오는 경우도 더미 센서로 처리
        if key in ["lel", "smoke"] or (value is not None and float(value) == -1 and key in ["lel", "smoke"]):
            return "--", True, 1

        # 실제 센서 데이터 처리
        if value is not None:
            try:
                fv = float(value)

                # 경보 레벨 계산 (타일과 동일한 방식)
                alert_level = 1  # 기본값: 정상
                if target_panel and hasattr(target_panel, 'alert_manager'):
                    alert_level = target_panel.alert_manager.get_alert_level(key, fv)

                # 임계값 체크
                is_ok = self._check_threshold(key, fv)

                # 포맷팅 (타일과 동일한 원칙)
                if key == "co2":
                    return f"{fv:.0f}", is_ok, alert_level
                elif key in ["h2s", "co"]:
                    return f"{fv:.1f}", is_ok, alert_level
                elif key == "o2":
                    return f"{fv:.1f}", is_ok, alert_level
                elif key == "temperature":
                    return f"{fv:.1f}", is_ok, alert_level
                elif key == "humidity":
                    return f"{fv:.1f}", is_ok, alert_level
                elif key == "water":
                    return "누수" if fv == 1 else "정상", is_ok, alert_level
            except Exception as e:
                pass
        
        # 데이터가 없으면 "-" 표시 (센서 연결 대기중)
        return "-", True, 1

    def _check_threshold(self, key, value):
        """임계값 검사"""
        try:
            x = float(value)
        except:
            return True

        cfg = self.app.cfg
        s = cfg.std
        e = cfg.env

        if key == "o2":
            return s.get("o2_min", 19.5) <= x <= s.get("o2_max", 23.0)
        elif key == "h2s":
            return x < s.get("h2s", 5.0)
        elif key == "co":
            return x < s.get("co", 9.0)
        elif key == "co2":
            return x < s.get("co2", 1000.0)
        elif key == "temperature":
            if x >= e.get("temp_danger", 38.0):
                return False
            if x > e.get("temp_max", 28.0):
                return False
            if x < e.get("temp_min", 18.0):
                return False
            return True
        elif key == "humidity":
            return e.get("hum_min", 40.0) <= x <= e.get("hum_max", 65.0)
        elif key == "lel":
            return x < s.get("lel_normal_max", 10)
        elif key == "smoke":
            return x < s.get("smoke_normal_max", 0)
        elif key == "water":
            return x == 0  # 누수 감지 시 False (경고)

        return True

    def _on_canvas_press(self, event):
        """캔버스 클릭"""
        # 잠금 상태에서는 아이템 드래그 불가, 팬만 가능
        if self.blueprint_locked:
            # 캔버스 팬만 허용
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            return

        # 클릭한 위치가 센서/모니터 위에 있는지 확인
        clicked_item = self._get_item_at_pos(event.x, event.y)

        if clicked_item:
            # 아이템 드래그 시작
            self.dragging_item = clicked_item
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        else:
            # 캔버스 팬 시작
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def _on_canvas_drag(self, event):
        """캔버스 드래그"""
        if self.drag_start_x is None or self.drag_start_y is None:
            return

        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        if self.dragging_item:
            # 아이템 이동
            item_type = self.dragging_item["type"]
            item_index = self.dragging_item["index"]

            # 캔버스 좌표를 이미지 좌표로 변환
            canvas_width = max(self.canvas.winfo_width(), 100)
            canvas_height = max(self.canvas.winfo_height(), 100)
            img_width = int(self.blueprint_image.width * self.zoom_level)
            img_height = int(self.blueprint_image.height * self.zoom_level)

            # 오버레이 크기 (3배)
            overlay_width = img_width * 3
            overlay_height = img_height * 3

            # 오버레이의 좌상단 위치
            overlay_left = canvas_width // 2 + self.pan_x - overlay_width // 2
            overlay_top = canvas_height // 2 + self.pan_y - overlay_height // 2

            # 도면 이미지의 좌상단 위치 (오버레이 내에서)
            img_left = overlay_left + img_width
            img_top = overlay_top + img_height

            # 마우스 위치를 도면 이미지 내 비율로 변환
            rel_x = (event.x - img_left) / img_width
            rel_y = (event.y - img_top) / img_height

            # 범위 제한 제거 - 도면 밖에도 배치 가능
            # rel_x = max(0, min(1, rel_x))
            # rel_y = max(0, min(1, rel_y))

            if item_type == "sensor":
                self.sensors[item_index]["x"] = rel_x
                self.sensors[item_index]["y"] = rel_y
            elif item_type == "monitor":
                self.monitors[item_index]["x"] = rel_x
                self.monitors[item_index]["y"] = rel_y
            elif item_type == "individual_item":
                # 개별 센서 아이템 이동
                sub_index = self.dragging_item.get("sub_index", 0)
                sensor = self.sensors[item_index]
                if "individual_items" in sensor and sub_index < len(sensor["individual_items"]):
                    sensor["individual_items"][sub_index]["x"] = rel_x
                    sensor["individual_items"][sub_index]["y"] = rel_y

            self._redraw_canvas()
            self._save_blueprint_data()  # 자동 저장
        else:
            # 캔버스 팬
            self.pan_x += dx
            self.pan_y += dy
            self._redraw_canvas()

        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_canvas_release(self, event):
        """캔버스 릴리즈"""
        self.drag_start_x = None
        self.drag_start_y = None
        self.dragging_item = None

    def _get_item_at_pos(self, canvas_x, canvas_y):
        """클릭 위치의 아이템 반환"""
        if not self.blueprint_image:
            return None

        canvas_width = max(self.canvas.winfo_width(), 100)
        canvas_height = max(self.canvas.winfo_height(), 100)
        img_width = int(self.blueprint_image.width * self.zoom_level)
        img_height = int(self.blueprint_image.height * self.zoom_level)

        # 오버레이 크기 (3배)
        overlay_width = img_width * 3
        overlay_height = img_height * 3

        # 오버레이의 좌상단 위치 (캔버스 중앙에 오버레이 중심 배치)
        overlay_left = canvas_width // 2 + self.pan_x - overlay_width // 2
        overlay_top = canvas_height // 2 + self.pan_y - overlay_height // 2

        # 도면 이미지의 좌상단 위치 (오버레이 내에서)
        img_left = overlay_left + img_width  # 오프셋
        img_top = overlay_top + img_height   # 오프셋

        # 마우스 위치를 도면 이미지 내 비율로 변환
        rel_x = (canvas_x - img_left) / img_width
        rel_y = (canvas_y - img_top) / img_height

        # 개별 센서 아이템 체크 (우선순위 높음)
        for i, sensor in enumerate(self.sensors):
            if "individual_items" in sensor:
                for j, item in enumerate(sensor["individual_items"]):
                    if self._is_point_in_individual_item(rel_x, rel_y, item):
                        return {"type": "individual_item", "index": i, "sub_index": j}

        # 센서 이름 체크
        for i, sensor in enumerate(self.sensors):
            if self._is_point_in_sensor(rel_x, rel_y, sensor):
                return {"type": "sensor", "index": i}

        # 모니터 체크
        for i, monitor in enumerate(self.monitors):
            if self._is_point_in_monitor(rel_x, rel_y, monitor):
                return {"type": "monitor", "index": i}

        return None

    def _is_point_in_individual_item(self, x, y, item):
        """점이 개별 센서 아이템 영역 안에 있는지 확인"""
        # 고정 반경 (40 픽셀 - 2배 키움)
        radius = 40 / (self.blueprint_image.width * self.zoom_level)
        dx = x - item["x"]
        dy = y - item["y"]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < radius

    def _is_point_in_sensor(self, x, y, sensor):
        """점이 센서 중심점 영역 안에 있는지 확인 (센서 이름 배경)"""
        # 센서 이름 배경 원: 반경 35픽셀
        radius = 35 / (self.blueprint_image.width * self.zoom_level)

        dx = x - sensor["x"]
        dy = y - sensor["y"]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < radius

    def _is_point_in_monitor(self, x, y, monitor):
        """점이 모니터 영역 안에 있는지 확인 (고정 크기)"""
        # 사각형 영역 (고정 크기: 70x45)
        width = 70 / (self.blueprint_image.width * self.zoom_level)
        height = 45 / (self.blueprint_image.height * self.zoom_level)

        return (abs(x - monitor["x"]) < width/2 and
                abs(y - monitor["y"]) < height/2)

    def _on_canvas_right_click(self, event):
        """캔버스 우클릭"""
        # 잠금 상태에서는 컨텍스트 메뉴 비활성화
        if self.blueprint_locked:
            return

        clicked_item = self._get_item_at_pos(event.x, event.y)

        if clicked_item:
            self._show_context_menu(event, clicked_item)

    def _show_context_menu(self, event, item):
        """컨텍스트 메뉴 표시"""
        menu = tk.Menu(self, tearoff=0, font=("Pretendard", 11))

        item_type = item["type"]
        item_index = item["index"]

        if item_type == "individual_item":
            # 개별 센서 아이템: 해당 아이템만 삭제 또는 전체 삭제
            menu.add_command(label="이 센서값만 삭제",
                           command=lambda: self._delete_individual_item(item_index, item.get("sub_index", 0)))
            menu.add_separator()
            menu.add_command(label="☑ 해당 센서 전체 삭제",
                           command=lambda: self._delete_sensor(item_index))

        elif item_type == "sensor":
            # 센서 중심점: 이름 변경 또는 전체 삭제
            sensor = self.sensors[item_index]
            sid = sensor.get("sid", "")
            menu.add_command(label=f"표기 이름 변경 (ID: {sid})",
                           command=lambda: self._change_sensor_display_name(item_index))
            menu.add_separator()
            menu.add_command(label="☑ 해당 센서 전체 삭제",
                           command=lambda: self._delete_sensor(item_index))

        elif item_type == "monitor":
            # 모니터: 삭제
            menu.add_command(label="삭제하시겠습니까?",
                           command=lambda: self._delete_monitor(item_index))

        menu.tk_popup(event.x_root, event.y_root)

    def _delete_individual_item(self, sensor_index, item_index):
        """개별 센서 아이템 삭제"""
        if 0 <= sensor_index < len(self.sensors):
            sensor = self.sensors[sensor_index]
            if "individual_items" in sensor and 0 <= item_index < len(sensor["individual_items"]):
                del sensor["individual_items"][item_index]
                self._save_blueprint_data()
                self._redraw_canvas()

    def _delete_sensor(self, index):
        """센서 삭제"""
        if 0 <= index < len(self.sensors):
            del self.sensors[index]

        self._save_blueprint_data()
        self._redraw_canvas()

    def _delete_monitor(self, index):
        """모니터 삭제"""
        if 0 <= index < len(self.monitors):
            del self.monitors[index]
            self._save_blueprint_data()
            self._redraw_canvas()

    def _change_sensor_display_name(self, index):
        """센서 표기 이름 변경"""
        if not (0 <= index < len(self.sensors)):
            return

        sensor = self.sensors[index]
        sid = sensor.get("sid", "")
        current_name = sensor.get("display_name", sid)

        # 커스텀 다이얼로그 생성
        dialog = tk.Toplevel(self.app)
        dialog.title("센서 표기 이름 변경")
        dialog.geometry("500x423")  # 325에서 423으로 30% 더 확장 (325 * 1.3 = 423)
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (211)  # 423/2 = 211.5
        dialog.geometry(f"500x423+{x}+{y}")

        # 제목
        tk.Label(dialog, text=f"센서 표기 이름 변경",
                font=("Pretendard", 16, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=15)

        # ID 표시
        tk.Label(dialog, text=f"센서 ID: {sid}",
                font=("Pretendard", 12), bg="#F5F5F5", fg="#7F8C8D").pack(pady=5)

        # 입력 프레임
        input_frame = tk.Frame(dialog, bg="#F5F5F5")
        input_frame.pack(pady=20, padx=30, fill="x")

        tk.Label(input_frame, text="표기 이름:",
                font=("Pretendard", 12, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(anchor="w", pady=(0, 5))

        name_entry = tk.Entry(input_frame, font=("Pretendard", 14), width=30, relief="solid", bd=2)
        name_entry.insert(0, current_name)
        name_entry.pack(fill="x", ipady=8)
        name_entry.select_range(0, tk.END)
        name_entry.focus()

        # 버튼 프레임
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=30)

        def on_save():
            new_name = name_entry.get().strip()
            if new_name:
                sensor["display_name"] = new_name
                self._save_blueprint_data()
                self._redraw_canvas()
                dialog.destroy()

        def on_cancel():
            dialog.destroy()

        tk.Button(button_frame, text="✓ 저장", command=on_save,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 13, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=5)

        tk.Button(button_frame, text="✕ 취소", command=on_cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 13, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5)

        # Enter 키로 저장
        name_entry.bind("<Return>", lambda e: on_save())

    def _add_sensor(self):
        """센서 추가 - 연결된 모든 센서 선택 가능"""
        if not self.current_blueprint:
            messagebox.showwarning("경고", "먼저 도면을 선택하세요.")
            return

        # 연결된 센서 목록 가져오기
        sensor_list = []
        for panel_key in self.app.panels.keys():
            if panel_key != "__waiting__":
                # SID 추출
                if "@" in panel_key:
                    sid = panel_key.split("@")[0]
                elif "#" in panel_key:
                    sid = panel_key.split("#")[0]
                else:
                    sid = panel_key
                sensor_list.append((panel_key, sid))

        if not sensor_list:
            messagebox.showwarning("경고", "연결된 센서가 없습니다.")
            return

        # 센서 선택 다이얼로그
        dialog = tk.Toplevel(self.app)
        dialog.title("센서 추가")
        dialog.geometry("700x600")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"700x600+{x}+{y}")

        # 제목
        tk.Label(dialog, text="센서 추가",
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=15)

        # 센서 선택
        sensor_frame = tk.LabelFrame(dialog, text="추가할 센서 선택", font=("Pretendard", 13, "bold"),
                                     bg="#F5F5F5", fg="#2C3E50", padx=15, pady=15)
        sensor_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 스크롤 가능한 체크박스 리스트
        canvas = tk.Canvas(sensor_frame, bg="#FFFFFF", highlightthickness=0, height=150)
        scrollbar = tk.Scrollbar(sensor_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#FFFFFF")

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

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 센서 체크박스 변수
        sensor_vars = {}
        for panel_key, sid in sensor_list:
            var = tk.BooleanVar(value=(panel_key == self.sid or sid == self.sid))
            check = tk.Checkbutton(scrollable_frame, text=f"{sid} ({panel_key})",
                                  variable=var, bg="#FFFFFF", font=("Pretendard", 11),
                                  activebackground="#FFFFFF", selectcolor="#FFFFFF")
            check.pack(anchor="w", pady=3, padx=10)
            sensor_vars[panel_key] = var

        # 센서값 선택 섹션 추가
        sensor_values_frame = tk.LabelFrame(dialog, text="표시할 센서값 선택", font=("Pretendard", 13, "bold"),
                                           bg="#F5F5F5", fg="#2C3E50", padx=15, pady=15)
        sensor_values_frame.pack(fill="x", padx=20, pady=10)

        # 센서값 한글 매핑
        sensor_value_names = {
            "co2": "이산화탄소 (CO₂)",
            "o2": "산소 (O₂)",
            "h2s": "황화수소 (H₂S)",
            "co": "일산화탄소 (CO)",
            "lel": "가연성가스 (LEL%)",
            "smoke": "연기 (Smoke)",
            "temperature": "온도 (℃)",
            "humidity": "습도 (RH%)",
            "water": "누수 감지"
        }

        # 센서값 체크박스 (3x3 그리드)
        values_frame = tk.Frame(sensor_values_frame, bg="#F5F5F5")
        values_frame.pack(fill="x", pady=10)

        sensor_value_vars = {}
        for i, (key, name) in enumerate(sensor_value_names.items()):
            row = i // 3
            col = i % 3
            
            var = tk.BooleanVar(value=True)  # 기본적으로 모두 선택
            check = tk.Checkbutton(values_frame, text=name, variable=var,
                                  bg="#F5F5F5", font=("Pretendard", 10),
                                  activebackground="#F5F5F5", selectcolor="#F5F5F5")
            check.grid(row=row, column=col, sticky="w", padx=10, pady=5)
            sensor_value_vars[key] = var


        # 하단 버튼
        bottom_frame = tk.Frame(dialog, bg="#F5F5F5")
        bottom_frame.pack(side="bottom", fill="x", pady=15, padx=20)

        def on_add():
            # 선택된 센서들 가져오기
            selected_sensors = [panel_key for panel_key, var in sensor_vars.items() if var.get()]

            if not selected_sensors:
                messagebox.showwarning("경고", "추가할 센서를 선택하세요.", parent=dialog)
                return

            # 선택된 센서값들 가져오기
            selected_values = [key for key, var in sensor_value_vars.items() if var.get()]

            if not selected_values:
                messagebox.showwarning("경고", "표시할 센서값을 선택하세요.", parent=dialog)
                return

            # 선택된 센서들 추가 (개별 센서값 표시 모드)
            for panel_key in selected_sensors:
                # SID 추출
                if "@" in panel_key:
                    sid = panel_key.split("@")[0]
                elif "#" in panel_key:
                    sid = panel_key.split("#")[0]
                else:
                    sid = panel_key

                # 개별 센서값 아이템들 생성
                individual_items = []
                for i, value_key in enumerate(selected_values):
                    # 센서값들을 원형으로 배치
                    angle = (2 * 3.14159 * i) / len(selected_values)
                    radius = 0.15  # 센서 중심에서의 거리
                    x = 0.5 + radius * math.cos(angle)
                    y = 0.5 + radius * math.sin(angle)
                    
                    individual_items.append({
                        "key": value_key,
                        "x": x,
                        "y": y
                    })

                new_sensor = {
                    "sid": sid,
                    "panel_key": panel_key,
                    "x": 0.5,
                    "y": 0.5,
                    "individual_items": individual_items
                }

                self.sensors.append(new_sensor)

            self._save_blueprint_data()
            self._redraw_canvas()
            dialog.destroy()

        tk.Button(bottom_frame, text="✓ 추가", command=on_add,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=5)

        tk.Button(bottom_frame, text="✕ 취소", command=dialog.destroy,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5)

    def _add_monitor(self):
        """모니터 추가"""
        if not self.current_blueprint:
            messagebox.showwarning("경고", "먼저 도면을 선택하세요.")
            return

        # 모니터 이름 입력
        name = simpledialog.askstring("모니터 추가", "모니터 이름을 입력하세요:",
                                     parent=self.app)
        if not name:
            return

        # 모니터 추가 (중앙에 배치)
        new_monitor = {
            "name": name,
            "x": 0.5,
            "y": 0.5
        }
        self.monitors.append(new_monitor)
        self._save_blueprint_data()
        self._redraw_canvas()

    def update_admin_mode(self):
        """관리자 모드 변경 시 UI 업데이트"""
        if self.app.cfg.admin_mode:
            # 관리자 모드일 때 버튼 표시
            if not self.lock_button.winfo_viewable():
                self.lock_button.pack(side="left", padx=5)
        else:
            # 관리자 모드가 아닐 때 버튼 숨김
            if self.lock_button.winfo_viewable():
                self.lock_button.pack_forget()

    def update_fire_alert(self, level: int, probability: float,
                          triggered_sensors: list, sensor_values: dict):
        """화재 경보 상태 업데이트

        Args:
            level: 경보 레벨 (1-5)
            probability: 화재 확률 (0.0-1.0)
            triggered_sensors: 경보 발생 센서 키 목록
            sensor_values: 센서별 현재값
        """
        self._fire_alert_data = {
            "level": level,
            "probability": probability,
            "triggered_sensors": triggered_sensors,
            "sensor_values": sensor_values
        }

        # 도면 뷰가 활성화 상태면 즉시 갱신
        if self.winfo_viewable():
            self._redraw_canvas()

    def _draw_fire_alert_overlay(self, draw, img_width, img_height, offset_x, offset_y):
        """화재 경보 오버레이 그리기"""
        level = self._fire_alert_data.get("level", 1)

        # 레벨 3 (주의) 이상일 때만 표시
        if level < 3:
            return

        # 경보 레벨별 색상
        alert_colors = {
            3: (230, 126, 34, 150),   # 주의 - 주황 (반투명)
            4: (231, 76, 60, 180),    # 경계 - 빨강 (반투명)
            5: (142, 68, 173, 200),   # 위험 - 보라 (반투명)
        }

        alert_names = {
            3: "화재 주의",
            4: "화재 경계",
            5: "화재 위험",
        }

        color = alert_colors.get(level, (231, 76, 60, 180))
        name = alert_names.get(level, "화재 경보")

        # 상단에 경보 배너 표시
        banner_height = 60
        draw.rectangle(
            [offset_x, offset_y, offset_x + img_width, offset_y + banner_height],
            fill=color
        )

        # 경보 텍스트
        probability = self._fire_alert_data.get("probability", 0.0)
        text = f"🔥 {name} - 화재 확률: {probability * 100:.1f}%"

        # 폰트 로드
        font = None
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "C:/Windows/Fonts/malgun.ttf",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype(font_path, 24)
                    break
                except:
                    continue

        if font:
            draw.text(
                (offset_x + img_width // 2, offset_y + banner_height // 2),
                text,
                fill=(255, 255, 255, 255),
                font=font,
                anchor="mm"
            )

    def get_fire_alert_sensors(self) -> list:
        """화재 경보 발생 센서 목록 반환"""
        return self._fire_alert_data.get("triggered_sensors", [])
