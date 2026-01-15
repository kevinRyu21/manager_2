#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카메라 고급 설정 다이얼로그

AI 감지 신뢰도, YOLO 설정, 이미지 전처리 등 미세 조정 기능
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os


class CameraAdvancedSettingsDialog:
    """카메라 고급 설정 다이얼로그"""

    # 기본 설정값 (RTX 3060 + Ryzen 5 기준 최적화)
    DEFAULT_SETTINGS = {
        # AI 감지 신뢰도 (높을수록 정확하지만 감지 수 감소)
        "ppe_confidence": 0.25,      # 안전장구 감지 임계값
        "coco_confidence_usb": 0.35, # COCO 사물 감지 (USB)
        "coco_confidence_ip": 0.25,  # COCO 사물 감지 (IP) - 0.25로 상향 (성능 최적화)
        "face_confidence": 0.35,     # 얼굴 인식 임계값
        "nms_threshold": 0.45,       # NMS 임계값

        # YOLO 설정
        "yolo_imgsz": 640,           # 추론 이미지 크기 (640 권장)

        # 이미지 전처리
        "brightness": 0,             # 밝기 (-100 ~ +100)
        "contrast": 1.0,             # 대비 (0.5 ~ 2.0)
        "saturation": 1.0            # 채도 (0 ~ 2.0)
    }

    def __init__(self, parent, config):
        """
        Args:
            parent: 부모 윈도우 (App 또는 CameraSettingsDialog)
            config: 설정 객체
        """
        self.parent = parent
        self.config = config
        self.result = False

        # 현재 설정 로드
        self.current_settings = self._load_settings()

        # 다이얼로그 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("카메라 고급 설정")
        self.dialog.geometry("550x680")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#1a1a2e")

        # 모달 설정
        self.dialog.transient(parent)

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 550) // 2
        y = (self.dialog.winfo_screenheight() - 680) // 2
        self.dialog.geometry(f"550x680+{x}+{y}")

        # UI 생성
        self._create_ui()

        # 닫기 이벤트
        self.dialog.protocol("WM_DELETE_WINDOW", self._close)

    def show(self):
        """다이얼로그 표시 (비차단 방식)"""
        # wait_window() 대신 focus만 설정 (messagebox 표시 문제 해결)
        self.dialog.deiconify()
        self.dialog.focus_set()
        self.dialog.lift()
        # 부모 창 비활성화 효과
        self.dialog.grab_set()

    def _load_settings(self):
        """저장된 고급 설정 로드"""
        settings = self.DEFAULT_SETTINGS.copy()
        try:
            if hasattr(self.config, 'camera'):
                advanced = self.config.camera.get("advanced_settings", {})
                if isinstance(advanced, dict):
                    for key in settings:
                        if key in advanced:
                            settings[key] = advanced[key]
        except Exception as e:
            print(f"[고급설정] 로드 오류: {e}")
        return settings

    def _create_ui(self):
        """UI 생성"""
        # 스크롤 가능한 캔버스 생성
        canvas_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#1a1a2e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 캔버스 참조 저장 (닫을 때 이벤트 해제용)
        self._canvas = canvas

        # 마우스 휠 스크롤 (Linux/Windows 호환)
        def _on_mousewheel(event):
            # Windows
            if event.delta:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            # Linux (Button-4: 위, Button-5: 아래)
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        # 다이얼로그 내부에만 바인딩 (bind_all 대신 bind)
        canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind("<Button-4>", _on_mousewheel)    # Linux scroll up
        canvas.bind("<Button-5>", _on_mousewheel)    # Linux scroll down
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-5>", _on_mousewheel)

        # 제목
        title_label = tk.Label(
            self.scrollable_frame,
            text="카메라 고급 설정",
            font=("Pretendard", 16, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff"
        )
        title_label.pack(pady=(10, 15))

        # 참고: 프리셋(저사양/일반/고성능)은 [설정-성능설정]에서 관리

        # === AI 감지 신뢰도 섹션 ===
        self._create_ai_confidence_section()

        # === YOLO 설정 섹션 ===
        self._create_yolo_section()

        # === 이미지 전처리 섹션 ===
        self._create_image_processing_section()

        # 참고: 성능 설정은 [설정-성능설정]에서 관리

        # === 버튼 ===
        self._create_buttons()

    def _create_section_frame(self, title, icon=""):
        """섹션 프레임 생성"""
        frame = tk.LabelFrame(
            self.scrollable_frame,
            text=f" {icon} {title} ",
            font=("Pretendard", 11, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff",
            padx=15,
            pady=10
        )
        frame.pack(fill="x", padx=10, pady=(0, 10))
        return frame

    def _create_ai_confidence_section(self):
        """AI 감지 신뢰도 섹션 생성"""
        frame = self._create_section_frame("AI 감지 신뢰도", "🎯")

        # 안전장구 감지 (PPE)
        self.ppe_scale = self._create_slider(
            frame,
            "안전장구 감지 (PPE)",
            "ppe_confidence",
            0.05, 0.90, 0.05,
            "낮을수록 더 많이 감지 (오탐 증가)"
        )

        # COCO 사물 감지 (USB)
        self.coco_usb_scale = self._create_slider(
            frame,
            "사물 감지 - USB 카메라",
            "coco_confidence_usb",
            0.05, 0.90, 0.05,
            "USB 웹캠용 (근거리)"
        )

        # COCO 사물 감지 (IP)
        self.coco_ip_scale = self._create_slider(
            frame,
            "사물 감지 - IP 카메라",
            "coco_confidence_ip",
            0.01, 0.50, 0.01,
            "IP 카메라용 (원거리, 매우 낮게 설정)"
        )

        # 얼굴 인식
        self.face_scale = self._create_slider(
            frame,
            "얼굴 인식",
            "face_confidence",
            0.10, 0.90, 0.05,
            "낮을수록 더 많이 인식"
        )

        # NMS 임계값
        self.nms_scale = self._create_slider(
            frame,
            "NMS 임계값",
            "nms_threshold",
            0.20, 0.80, 0.05,
            "중복 박스 제거 기준 (높을수록 박스 많음)"
        )

    def _create_yolo_section(self):
        """YOLO 설정 섹션 생성"""
        frame = self._create_section_frame("YOLO 추론 설정", "🔬")

        # imgsz 선택
        imgsz_frame = tk.Frame(frame, bg="#1a1a2e")
        imgsz_frame.pack(fill="x", pady=5)

        tk.Label(
            imgsz_frame,
            text="추론 이미지 크기 (imgsz):",
            font=("Pretendard", 11),
            bg="#1a1a2e",
            fg="#ffffff"
        ).pack(side="left")

        self.imgsz_var = tk.IntVar(value=self.current_settings.get("yolo_imgsz", 640))
        imgsz_values = [320, 480, 640, 960, 1280, 1920]

        self.imgsz_combo = ttk.Combobox(
            imgsz_frame,
            values=imgsz_values,
            textvariable=self.imgsz_var,
            state="readonly",
            width=10,
            font=("Pretendard", 10)
        )
        self.imgsz_combo.pack(side="left", padx=(10, 0))

        # 현재 값 선택
        current_imgsz = self.current_settings.get("yolo_imgsz", 640)
        if current_imgsz in imgsz_values:
            self.imgsz_combo.current(imgsz_values.index(current_imgsz))
        else:
            self.imgsz_combo.current(2)  # 기본 640

        tk.Label(
            imgsz_frame,
            text="px",
            font=("Pretendard", 10),
            bg="#1a1a2e",
            fg="#888888"
        ).pack(side="left", padx=(5, 0))

        # 설명
        tk.Label(
            frame,
            text="클수록 정확하지만 느림 (GPU: 1280 권장, CPU: 640 이하)",
            font=("Pretendard", 9),
            bg="#1a1a2e",
            fg="#888888"
        ).pack(anchor="w")

    def _create_image_processing_section(self):
        """이미지 전처리 섹션 생성"""
        frame = self._create_section_frame("이미지 전처리", "🖼️")

        # 밝기
        self.brightness_scale = self._create_slider(
            frame,
            "밝기",
            "brightness",
            -100, 100, 5,
            "영상 밝기 조절",
            format_func=lambda v: f"{int(v):+d}"
        )

        # 대비
        self.contrast_scale = self._create_slider(
            frame,
            "대비",
            "contrast",
            0.5, 2.0, 0.1,
            "영상 대비 조절",
            format_func=lambda v: f"{v:.1f}x"
        )

        # 채도
        self.saturation_scale = self._create_slider(
            frame,
            "채도",
            "saturation",
            0.0, 2.0, 0.1,
            "색상 채도 조절 (0=흑백)",
            format_func=lambda v: f"{v:.1f}x"
        )

    def _create_slider(self, parent, label, setting_key, min_val, max_val, resolution, hint="", format_func=None):
        """슬라이더 컨트롤 생성"""
        row_frame = tk.Frame(parent, bg="#1a1a2e")
        row_frame.pack(fill="x", pady=5)

        # 레이블
        tk.Label(
            row_frame,
            text=f"{label}:",
            font=("Pretendard", 10),
            bg="#1a1a2e",
            fg="#ffffff",
            width=20,
            anchor="w"
        ).pack(side="left")

        # 현재 값
        current_val = self.current_settings.get(setting_key, min_val)

        # 값 표시 레이블
        if format_func:
            val_text = format_func(current_val)
        else:
            val_text = f"{current_val:.2f}"

        value_label = tk.Label(
            row_frame,
            text=val_text,
            font=("Pretendard", 10, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff",
            width=8
        )
        value_label.pack(side="right")

        # 슬라이더
        scale = tk.Scale(
            row_frame,
            from_=min_val,
            to=max_val,
            resolution=resolution,
            orient="horizontal",
            length=200,
            bg="#16213e",
            fg="#ffffff",
            troughcolor="#0f3460",
            highlightthickness=0,
            sliderrelief="flat",
            showvalue=False
        )
        scale.set(current_val)
        scale.pack(side="right", padx=(10, 10))

        # 값 변경 시 레이블 업데이트
        def on_change(val):
            if format_func:
                value_label.config(text=format_func(float(val)))
            else:
                value_label.config(text=f"{float(val):.2f}")

        scale.config(command=on_change)

        # 힌트
        if hint:
            hint_label = tk.Label(
                parent,
                text=f"  ↳ {hint}",
                font=("Pretendard", 8),
                bg="#1a1a2e",
                fg="#666666"
            )
            hint_label.pack(anchor="w")

        return scale

    def _create_buttons(self):
        """버튼 영역 생성"""
        btn_frame = tk.Frame(self.dialog, bg="#16213e", pady=15)
        btn_frame.pack(fill="x", side="bottom")

        btn_inner = tk.Frame(btn_frame, bg="#16213e")
        btn_inner.pack()

        # 적용 버튼
        apply_btn = tk.Button(
            btn_inner,
            text="적용",
            font=("Pretendard", 12, "bold"),
            bg="#00d4ff",
            fg="#000000",
            width=10,
            height=2,
            command=self._apply_settings
        )
        apply_btn.pack(side="left", padx=5)

        # 저장 버튼
        save_btn = tk.Button(
            btn_inner,
            text="저장",
            font=("Pretendard", 12, "bold"),
            bg="#27AE60",
            fg="#ffffff",
            width=10,
            height=2,
            command=self._save_settings
        )
        save_btn.pack(side="left", padx=5)

        # 초기화 버튼
        reset_btn = tk.Button(
            btn_inner,
            text="초기화",
            font=("Pretendard", 12),
            bg="#E67E22",
            fg="#ffffff",
            width=10,
            height=2,
            command=self._reset_to_default
        )
        reset_btn.pack(side="left", padx=5)

        # 닫기 버튼
        close_btn = tk.Button(
            btn_inner,
            text="닫기",
            font=("Pretendard", 12),
            bg="#7F8C8D",
            fg="#ffffff",
            width=10,
            height=2,
            command=self._close
        )
        close_btn.pack(side="left", padx=5)

    def _get_current_ui_settings(self):
        """현재 UI에서 설정값 수집"""
        return {
            "ppe_confidence": self.ppe_scale.get(),
            "coco_confidence_usb": self.coco_usb_scale.get(),
            "coco_confidence_ip": self.coco_ip_scale.get(),
            "face_confidence": self.face_scale.get(),
            "nms_threshold": self.nms_scale.get(),
            "yolo_imgsz": self.imgsz_var.get(),
            "brightness": self.brightness_scale.get(),
            "contrast": self.contrast_scale.get(),
            "saturation": self.saturation_scale.get()
        }

    def _show_message(self, msg_type, title, message):
        """커스텀 메시지 다이얼로그 표시"""
        # grab 해제
        try:
            self.dialog.grab_release()
        except:
            pass

        result = [None]  # 리스트로 래핑 (클로저에서 수정 가능)

        # 커스텀 다이얼로그 생성
        msg_dialog = tk.Toplevel(self.dialog)
        msg_dialog.title(title)
        msg_dialog.configure(bg="#2C3E50")
        msg_dialog.resizable(False, False)
        msg_dialog.transient(self.dialog)

        # 크기 및 위치
        width = 380
        height = 200
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - width) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - height) // 2
        msg_dialog.geometry(f"{width}x{height}+{x}+{y}")

        # 아이콘 및 색상
        if msg_type == "info":
            icon = "✅"
            color = "#27AE60"
        elif msg_type == "error":
            icon = "❌"
            color = "#E74C3C"
        else:  # yesno
            icon = "❓"
            color = "#3498DB"

        # 메시지 영역
        msg_frame = tk.Frame(msg_dialog, bg="#2C3E50")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # 아이콘 + 제목
        tk.Label(
            msg_frame,
            text=f"{icon} {title}",
            font=("Pretendard", 13, "bold"),
            bg="#2C3E50",
            fg=color
        ).pack(anchor="w")

        # 메시지 내용
        tk.Label(
            msg_frame,
            text=message,
            font=("Pretendard", 10),
            bg="#2C3E50",
            fg="#ECF0F1",
            justify="left",
            wraplength=300
        ).pack(anchor="w", pady=(10, 0))

        # 버튼 영역
        btn_frame = tk.Frame(msg_dialog, bg="#34495E", height=50)
        btn_frame.pack(fill="x", side="bottom", pady=10)
        btn_frame.pack_propagate(False)

        def on_ok():
            result[0] = True
            msg_dialog.destroy()

        def on_cancel():
            result[0] = False
            msg_dialog.destroy()

        # 버튼 컨테이너 (중앙 정렬용)
        btn_container = tk.Frame(btn_frame, bg="#34495E")
        btn_container.place(relx=0.5, rely=0.5, anchor="center")

        if msg_type == "yesno":
            tk.Button(
                btn_container, text="예", font=("Pretendard", 10, "bold"),
                bg="#27AE60", fg="#FFFFFF", width=8, height=1,
                command=on_ok
            ).pack(side="left", padx=5)
            tk.Button(
                btn_container, text="아니오", font=("Pretendard", 10),
                bg="#7F8C8D", fg="#FFFFFF", width=8, height=1,
                command=on_cancel
            ).pack(side="left", padx=5)
        else:
            tk.Button(
                btn_container, text="확인", font=("Pretendard", 10, "bold"),
                bg=color, fg="#FFFFFF", width=10, height=1,
                command=on_ok
            ).pack()

        # 모달 설정
        msg_dialog.grab_set()
        msg_dialog.focus_set()

        # ESC로 닫기
        msg_dialog.bind("<Escape>", lambda e: on_cancel())
        msg_dialog.bind("<Return>", lambda e: on_ok())

        # 닫기 버튼
        msg_dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        # 다이얼로그 완료 대기
        self.dialog.wait_window(msg_dialog)

        # grab 복원
        try:
            self.dialog.grab_set()
        except:
            pass

        return result[0]

    def _apply_settings(self):
        """설정 즉시 적용 (저장 없이)"""
        print("[고급설정] 적용 버튼 클릭됨")
        settings = self._get_current_ui_settings()

        try:
            # 현재 실행 중인 감지기에 설정 적용
            self._apply_to_detectors(settings)

            # 확인 다이얼로그 표시
            self._show_message(
                "info",
                "적용 완료",
                "설정이 적용되었습니다.\n\n"
                "영구 저장하려면 '저장' 버튼을 누르세요."
            )
        except Exception as e:
            self._show_message("error", "오류", f"설정 적용 중 오류:\n{str(e)}")

    def _apply_to_detectors(self, settings):
        """감지기들에 설정 적용"""
        print(f"[고급설정] 설정 적용: {settings}")

        # App 객체 찾기
        app = self._find_app()
        if not app:
            print("[고급설정] App 객체를 찾을 수 없음")
            return

        # 현재 패널의 감지기에 적용
        if hasattr(app, 'current_panel') and app.current_panel:
            panel = app.current_panel

            # SafetyDetector 설정 적용
            if hasattr(panel, 'safety_detector') and panel.safety_detector:
                detector = panel.safety_detector

                # COCO 신뢰도 설정
                if hasattr(detector, '_coco_conf'):
                    # IP 카메라인지 확인
                    is_ip = hasattr(panel, '_ip_camera_url') and panel._ip_camera_url
                    if is_ip:
                        detector._coco_conf = settings["coco_confidence_ip"]
                    else:
                        detector._coco_conf = settings["coco_confidence_usb"]
                    print(f"[고급설정] COCO 신뢰도: {detector._coco_conf}")

                # PPE 신뢰도 설정 (YOLO 모델 conf)
                if hasattr(detector, '_ppe_conf'):
                    detector._ppe_conf = settings["ppe_confidence"]
                    print(f"[고급설정] PPE 신뢰도: {detector._ppe_conf}")

                # 얼굴 인식 신뢰도
                if hasattr(detector, '_face_threshold'):
                    detector._face_threshold = settings["face_confidence"]
                    print(f"[고급설정] 얼굴 신뢰도: {detector._face_threshold}")

            # PPEDetector 설정 적용
            if hasattr(panel, 'ppe_detector') and panel.ppe_detector:
                ppe = panel.ppe_detector
                if hasattr(ppe, 'conf_threshold'):
                    ppe.conf_threshold = settings["ppe_confidence"]
                if hasattr(ppe, 'nms_threshold'):
                    ppe.nms_threshold = settings["nms_threshold"]
                if hasattr(ppe, 'imgsz'):
                    ppe.imgsz = settings["yolo_imgsz"]
                print(f"[고급설정] PPEDetector 업데이트")

            # 이미지 전처리 설정 저장 (패널에서 사용)
            if not hasattr(panel, '_image_processing'):
                panel._image_processing = {}
            panel._image_processing['brightness'] = settings["brightness"]
            panel._image_processing['contrast'] = settings["contrast"]
            panel._image_processing['saturation'] = settings["saturation"]
            print(f"[고급설정] 이미지 전처리 설정 저장")

    def _find_app(self):
        """App 객체 찾기"""
        # parent가 App인지 확인
        if hasattr(self.parent, 'panels'):
            return self.parent

        # parent의 parent가 App인지 확인 (CameraSettingsDialog에서 열린 경우)
        if hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'panels'):
            return self.parent.parent

        # Toplevel의 master에서 찾기
        try:
            widget = self.dialog.master
            while widget:
                if hasattr(widget, 'panels'):
                    return widget
                widget = widget.master if hasattr(widget, 'master') else None
        except:
            pass

        return None

    def _save_settings(self):
        """설정 저장"""
        print("[고급설정] 저장 버튼 클릭됨")
        settings = self._get_current_ui_settings()

        try:
            # 설정에 저장
            if not hasattr(self.config, 'camera'):
                self.config.camera = {}

            self.config.camera["advanced_settings"] = settings
            self.config.save()

            # 즉시 적용도 함께 수행
            self._apply_to_detectors(settings)

            self.result = True

            # 확인 다이얼로그 표시
            self._show_message(
                "info",
                "저장 완료",
                "고급 설정이 저장되었습니다.\n\n"
                "변경된 설정이 즉시 적용됩니다."
            )

        except Exception as e:
            self._show_message("error", "오류", f"설정 저장 중 오류:\n{str(e)}")

    def _reset_to_default(self):
        """기본값으로 초기화"""
        if not self._show_message("yesno", "초기화 확인", "모든 설정을 기본값으로 초기화하시겠습니까?"):
            return

        # 기본값으로 UI 업데이트
        defaults = self.DEFAULT_SETTINGS

        self.ppe_scale.set(defaults["ppe_confidence"])
        self.coco_usb_scale.set(defaults["coco_confidence_usb"])
        self.coco_ip_scale.set(defaults["coco_confidence_ip"])
        self.face_scale.set(defaults["face_confidence"])
        self.nms_scale.set(defaults["nms_threshold"])
        self.imgsz_var.set(defaults["yolo_imgsz"])
        self.brightness_scale.set(defaults["brightness"])
        self.contrast_scale.set(defaults["contrast"])
        self.saturation_scale.set(defaults["saturation"])

        # 콤보박스 인덱스 업데이트
        imgsz_values = [320, 480, 640, 960, 1280, 1920]
        if defaults["yolo_imgsz"] in imgsz_values:
            self.imgsz_combo.current(imgsz_values.index(defaults["yolo_imgsz"]))

        # 확인 다이얼로그 표시 (창은 유지)
        self._show_message(
            "info",
            "초기화 완료",
            "기본값으로 초기화되었습니다.\n\n"
            "영구 저장하려면 '저장' 버튼을 누르세요."
        )

    def _close(self):
        """다이얼로그 닫기"""
        self.dialog.destroy()


# 테스트용
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    class MockConfig:
        def __init__(self):
            self.camera = {}
        def save(self):
            print("Config saved")

    config = MockConfig()
    dialog = CameraAdvancedSettingsDialog(root, config)
    dialog.show()
    root.destroy()
