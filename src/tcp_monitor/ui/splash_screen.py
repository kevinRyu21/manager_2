"""
GARAMe Manager 로딩 스플래시 화면

프로그램 시작 시 제품 이미지와 기능을 보여주는 로딩 화면
"""

import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


class SplashScreen(tk.Toplevel):
    """로딩 스플래시 화면"""

    def __init__(self, parent=None):
        # parent가 없으면 임시 root 생성
        if parent is None:
            self._temp_root = tk.Tk()
            self._temp_root.withdraw()
            parent = self._temp_root
        else:
            self._temp_root = None

        super().__init__(parent)

        self.title("")
        self.overrideredirect(True)  # 타이틀바 제거
        self.configure(bg="#1A1A2E")

        # 화면 중앙에 배치
        width = 700
        height = 500
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # 항상 최상위
        self.attributes("-topmost", True)

        self._create_content()
        self.update()

    def _create_content(self):
        """스플래시 화면 내용 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self, bg="#1A1A2E")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 상단: 로고 이미지
        logo_frame = tk.Frame(main_frame, bg="#1A1A2E")
        logo_frame.pack(fill="x", pady=(0, 10))

        self.logo_imgref = None
        logo_label = tk.Label(logo_frame, bg="#1A1A2E")
        logo_label.pack()

        # 로고 로드 시도
        if PIL_OK:
            logo_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "GARAMe.png"),
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "blueprint_data", "assets", "GARAMe.png"),
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "logo.png"),
            ]
            for logo_path in logo_paths:
                logo_path = os.path.abspath(logo_path)
                if os.path.exists(logo_path):
                    try:
                        img = Image.open(logo_path)
                        # 최대 높이 120px로 조정
                        ratio = min(400 / img.width, 120 / img.height)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                        self.logo_imgref = ImageTk.PhotoImage(img)
                        logo_label.configure(image=self.logo_imgref)
                        break
                    except Exception:
                        pass

        if self.logo_imgref is None:
            logo_label.configure(text="GARAMe", font=("Pretendard", 36, "bold"),
                               fg="#3498DB", bg="#1A1A2E")

        # 제품명
        title_label = tk.Label(main_frame, text="GARAMe Manager v2.0.1",
                              font=("Pretendard", 24, "bold"), fg="#FFFFFF", bg="#1A1A2E")
        title_label.pack(pady=(10, 5))

        subtitle_label = tk.Label(main_frame, text="통합 안전 관리 시스템",
                                 font=("Pretendard", 14), fg="#94A3B8", bg="#1A1A2E")
        subtitle_label.pack(pady=(0, 20))

        # 기능 소개 프레임
        features_frame = tk.Frame(main_frame, bg="#16213E", relief="raised", bd=1)
        features_frame.pack(fill="x", pady=10, padx=10)

        features = [
            ("🌡️", "실시간 센서 모니터링", "온도, 습도, 가스(O₂, CO₂, CO, H₂S, CH₄) 실시간 감시"),
            ("🔥", "AI 화재 감지 시스템", "Dempster-Shafer 증거이론 기반 5단계 경보"),
            ("👷", "PPE 안전장구 감지", "YOLOv10 기반 헬멧, 조끼, 마스크 등 인식"),
            ("📊", "데이터 로깅 및 분석", "센서 데이터 기록 및 그래프 분석"),
        ]

        for icon, title, desc in features:
            row = tk.Frame(features_frame, bg="#16213E")
            row.pack(fill="x", padx=15, pady=8)

            tk.Label(row, text=icon, font=("Pretendard", 16), bg="#16213E", fg="#FFFFFF",
                    width=3).pack(side="left")
            text_frame = tk.Frame(row, bg="#16213E")
            text_frame.pack(side="left", fill="x", expand=True, padx=10)
            tk.Label(text_frame, text=title, font=("Pretendard", 11, "bold"),
                    bg="#16213E", fg="#3498DB", anchor="w").pack(fill="x")
            tk.Label(text_frame, text=desc, font=("Pretendard", 9),
                    bg="#16213E", fg="#94A3B8", anchor="w").pack(fill="x")

        # 로딩 상태 프레임
        loading_frame = tk.Frame(main_frame, bg="#1A1A2E")
        loading_frame.pack(fill="x", pady=(20, 10))

        self.status_label = tk.Label(loading_frame, text="시스템 초기화 중...",
                                    font=("Pretendard", 11), fg="#94A3B8", bg="#1A1A2E")
        self.status_label.pack()

        # 프로그레스바
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Splash.Horizontal.TProgressbar",
                       troughcolor="#16213E",
                       background="#3498DB",
                       thickness=8)

        self.progress = ttk.Progressbar(loading_frame, style="Splash.Horizontal.TProgressbar",
                                        orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=10)
        self.progress["value"] = 0

        # 저작권
        copyright_label = tk.Label(main_frame, text="© 2026 GARAMe. All rights reserved.",
                                  font=("Pretendard", 9), fg="#64748B", bg="#1A1A2E")
        copyright_label.pack(side="bottom", pady=(10, 0))

    def update_status(self, message, progress=None):
        """상태 메시지 및 진행률 업데이트"""
        self.status_label.configure(text=message)
        if progress is not None:
            self.progress["value"] = progress
        self.update()

    def close(self):
        """스플래시 화면 닫기"""
        try:
            self.destroy()
            if self._temp_root:
                self._temp_root.destroy()
        except Exception:
            pass
