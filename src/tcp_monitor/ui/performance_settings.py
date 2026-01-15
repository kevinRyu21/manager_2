"""
성능 설정 다이얼로그

AI 인식 수준 및 성능 모드를 설정합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from ..utils.helpers import get_system_specs_summary


class PerformanceSettingsDialog:
    """성능 설정 다이얼로그"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.dialog = None
        self.result = False
        self.recommended_mode = 2

    def show(self):
        """다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("성능 설정")

        # 화면 크기에 맞춰 다이얼로그 크기 조정
        self.dialog.update_idletasks()
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        base_w, base_h = 820, 940  # 높이 15% 추가 확장 (820 -> 940)
        max_h = max(700, screen_h - 100)
        dlg_h = min(base_h, max_h)
        self.dialog.geometry(f"{base_w}x{dlg_h}")
        self.dialog.configure(bg="#F5F5F5")
        self.dialog.transient(self.parent)
        self.dialog.attributes("-topmost", True)
        self.dialog.grab_set()

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (screen_w // 2) - (base_w // 2)
        y = (screen_h // 2) - (dlg_h // 2)
        self.dialog.geometry(f"{base_w}x{dlg_h}+{x}+{y}")

        # ESC로 닫기
        self.dialog.bind("<Escape>", lambda e: self._close())

        self._create_widgets()
        self._load_settings()

        # 다이얼로그가 닫힐 때까지 대기
        self.dialog.wait_window()
        return self.result

    def _create_widgets(self):
        """위젯 생성 - 폰트 추가 15% 축소 (총 25% 축소)"""
        # 제목 (19 -> 16)
        title_label = tk.Label(self.dialog, text="성능 설정 (AI 인식 수준)",
                              font=("Pretendard", 16, "bold"),
                              bg="#F5F5F5", fg="#2C3E50")
        title_label.pack(pady=(8, 6))

        # 메인 프레임
        main_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        main_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # === 시스템 사양 정보 표시 영역 ===
        self.system_info_frame = tk.Frame(main_frame, bg="#E8F4FD", padx=10, pady=8)
        self.system_info_frame.pack(fill="x", pady=(0, 10))

        # 시스템 사양 타이틀 (14 -> 12)
        sys_title_frame = tk.Frame(self.system_info_frame, bg="#E8F4FD")
        sys_title_frame.pack(fill="x")
        tk.Label(sys_title_frame, text="💻 현재 시스템 사양",
                font=("Pretendard", 12, "bold"), bg="#E8F4FD", fg="#1565C0").pack(side="left")

        # 시스템 정보 (비동기 로드) (11 -> 9)
        self.system_specs_label = tk.Label(self.system_info_frame, text="시스템 정보 분석 중...",
                                           font=("Pretendard", 9), bg="#E8F4FD", fg="#333333",
                                           anchor="w", justify="left")
        self.system_specs_label.pack(fill="x", pady=(4, 0))

        # 추천 모드 표시 영역
        self.recommend_frame = tk.Frame(self.system_info_frame, bg="#E8F4FD")
        self.recommend_frame.pack(fill="x", pady=(4, 0))

        self.recommend_label = tk.Label(self.recommend_frame, text="",
                                        font=("Pretendard", 10, "bold"), bg="#E8F4FD", fg="#2E7D32")
        self.recommend_label.pack(side="left")

        self.recommend_reason_label = tk.Label(self.recommend_frame, text="",
                                               font=("Pretendard", 9), bg="#E8F4FD", fg="#666666")
        self.recommend_reason_label.pack(side="left", padx=(6, 0))

        # 추천 모드 적용 버튼 (11 -> 9)
        self.apply_recommend_btn = tk.Button(self.recommend_frame, text="추천 적용",
                                             command=self._apply_recommended_mode,
                                             bg="#1976D2", fg="#FFFFFF",
                                             font=("Pretendard", 9, "bold"),
                                             state="disabled")
        self.apply_recommend_btn.pack(side="right")

        # 비동기로 시스템 사양 분석
        threading.Thread(target=self._load_system_specs, daemon=True).start()

        # === 성능 모드 선택 영역 === (폰트 추가 15% 축소)
        mode_frame = tk.LabelFrame(main_frame, text="성능 모드 선택",
                                   font=("Pretendard", 13, "bold"),
                                   bg="#F5F5F5", fg="#2C3E50",
                                   padx=8, pady=4)
        mode_frame.pack(fill="x", pady=(0, 6))

        self.performance_mode_var = tk.IntVar(value=2)

        # 모드별 라디오버튼 프레임 저장 (추천 표시용)
        self.mode_frames = {}
        self.mode_recommend_labels = {}

        # 모드 1: 기본 (얼굴 인식만) (13->11, 10->9)
        mode1_frame = tk.Frame(mode_frame, bg="#F5F5F5")
        mode1_frame.pack(fill="x", pady=2)
        self.mode_frames[1] = mode1_frame
        tk.Radiobutton(mode1_frame, text="1. 기본 모드 (얼굴 인식만)",
                      font=("Pretendard", 11, "bold"), bg="#F5F5F5",
                      variable=self.performance_mode_var, value=1).pack(side="left")
        tk.Label(mode1_frame, text="- 권장: N5095 등 저사양 CPU",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left", padx=6)
        self.mode_recommend_labels[1] = tk.Label(mode1_frame, text="",
                font=("Pretendard", 9, "bold"), bg="#F5F5F5", fg="#E74C3C")
        self.mode_recommend_labels[1].pack(side="left", padx=2)

        mode1_desc = tk.Label(mode_frame,
                             text="    • 거울보기/안전교육: 얼굴 인식만  |  FPS: 15-25  |  메모리: ~500MB  |  GPU 불필요",
                             font=("Pretendard", 9), bg="#F5F5F5", fg="#555555", anchor="w", justify="left")
        mode1_desc.pack(fill="x")

        # 모드 2: 얼굴 + 안전장구
        mode2_frame = tk.Frame(mode_frame, bg="#F5F5F5")
        mode2_frame.pack(fill="x", pady=2)
        self.mode_frames[2] = mode2_frame
        tk.Radiobutton(mode2_frame, text="2. 표준 모드 (얼굴 + 안전장구)",
                      font=("Pretendard", 11, "bold"), bg="#F5F5F5",
                      variable=self.performance_mode_var, value=2).pack(side="left")
        tk.Label(mode2_frame, text="- 권장: Intel i5/i7 이상",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left", padx=6)
        self.mode_recommend_labels[2] = tk.Label(mode2_frame, text="",
                font=("Pretendard", 9, "bold"), bg="#F5F5F5", fg="#E74C3C")
        self.mode_recommend_labels[2].pack(side="left", padx=2)

        mode2_desc = tk.Label(mode_frame,
                             text="    • 기본 + 안전장구 6종 (헬멧,조끼,보안경,장갑,마스크,안전화)  |  FPS: 8-15  |  ~1.5GB",
                             font=("Pretendard", 9), bg="#F5F5F5", fg="#555555", anchor="w", justify="left")
        mode2_desc.pack(fill="x")

        # 모드 3: 전체 (얼굴 + 안전장구 + 사물)
        mode3_frame = tk.Frame(mode_frame, bg="#F5F5F5")
        mode3_frame.pack(fill="x", pady=2)
        self.mode_frames[3] = mode3_frame
        tk.Radiobutton(mode3_frame, text="3. 고급 모드 (전체 AI 인식)",
                      font=("Pretendard", 11, "bold"), bg="#F5F5F5",
                      variable=self.performance_mode_var, value=3).pack(side="left")
        tk.Label(mode3_frame, text="- 권장: i7 + RTX 3060+",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#E74C3C").pack(side="left", padx=6)
        self.mode_recommend_labels[3] = tk.Label(mode3_frame, text="",
                font=("Pretendard", 9, "bold"), bg="#F5F5F5", fg="#E74C3C")
        self.mode_recommend_labels[3].pack(side="left", padx=2)

        mode3_desc = tk.Label(mode_frame,
                             text="    • 표준 + 사물 80종 (동물,차량,가구,전자기기)  |  FPS: 15-30 (GPU)  |  ~3GB+  |  GPU 필수",
                             font=("Pretendard", 9), bg="#F5F5F5", fg="#555555", anchor="w", justify="left")
        mode3_desc.pack(fill="x")

        # === 안전장구 인식 설정 === (폰트 추가 15% 축소)
        ppe_frame = tk.LabelFrame(main_frame, text="안전장구 인식 설정",
                                  font=("Pretendard", 13, "bold"),
                                  bg="#F5F5F5", fg="#2C3E50",
                                  padx=8, pady=4)
        ppe_frame.pack(fill="x", pady=(0, 6))

        # PPE 활성화 체크박스 (12->10, 10->9)
        ppe_top = tk.Frame(ppe_frame, bg="#F5F5F5")
        ppe_top.pack(fill="x")
        self.ppe_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ppe_top, text="안전장구 인식 사용",
                      font=("Pretendard", 10, "bold"), bg="#F5F5F5",
                      variable=self.ppe_enabled_var,
                      command=self._on_ppe_enabled_toggle).pack(side="left")
        tk.Label(ppe_top, text="(체크 해제 시 성능 향상)",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left", padx=4)

        # PPE 항목들 (6개를 1줄에) (11->9)
        self.ppe_items_frame = tk.Frame(ppe_frame, bg="#F5F5F5")
        self.ppe_items_frame.pack(fill="x", pady=2)

        ppe_items = [
            ("helmet", "안전모"), ("vest", "조끼"), ("glasses", "보안경"),
            ("gloves", "장갑"), ("mask", "마스크"), ("boots", "안전화"),
        ]
        self.ppe_item_vars = {}

        ppe_row = tk.Frame(self.ppe_items_frame, bg="#F5F5F5")
        ppe_row.pack(fill="x")
        for key, label in ppe_items:
            var = tk.BooleanVar(value=True)
            self.ppe_item_vars[key] = var
            tk.Checkbutton(ppe_row, text=label, font=("Pretendard", 9),
                          bg="#F5F5F5", variable=var, width=7,
                          anchor="w").pack(side="left", padx=2)

        # === 사물 인식 설정 === (폰트 추가 15% 축소)
        object_frame = tk.LabelFrame(main_frame, text="사물 인식 설정 (모드 3 전용)",
                                     font=("Pretendard", 13, "bold"),
                                     bg="#F5F5F5", fg="#2C3E50",
                                     padx=8, pady=4)
        object_frame.pack(fill="x", pady=(0, 6))

        # 사물 인식 활성화 (12->10, 10->9)
        obj_top = tk.Frame(object_frame, bg="#F5F5F5")
        obj_top.pack(fill="x")
        self.object_detection_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(obj_top, text="일반 사물 인식 사용",
                      font=("Pretendard", 10, "bold"), bg="#F5F5F5",
                      variable=self.object_detection_enabled_var,
                      command=self._on_object_detection_toggle).pack(side="left")
        tk.Label(obj_top, text="(거울보기 우측 패널에 표시, 모드 3에서만 동작)",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left", padx=4)

        # 카테고리별 사물 (2열 배치) (11->9, 10->8)
        self.object_items_frame = tk.Frame(object_frame, bg="#F5F5F5")
        self.object_items_frame.pack(fill="x", pady=2)

        object_categories = [
            ("animals", "동물", "새,고양이,개,말,양,소,코끼리,곰"),
            ("vehicles", "탈것", "자전거,자동차,오토바이,버스,트럭"),
            ("furniture", "가구", "의자,소파,침대,식탁"),
            ("electronics", "전자기기", "TV,노트북,휴대폰,키보드"),
            ("food", "음식", "바나나,사과,피자,케이크"),
            ("sports", "스포츠", "공,야구배트,테니스라켓"),
            ("accessories", "소지품", "백팩,우산,핸드백,여행가방"),
            ("kitchen", "주방", "병,컵,포크,나이프,숟가락"),
        ]
        self.object_category_vars = {}

        # 2열 4행 배치
        row_frame = None
        for i, (key, label, items) in enumerate(object_categories):
            if i % 2 == 0:
                row_frame = tk.Frame(self.object_items_frame, bg="#F5F5F5")
                row_frame.pack(fill="x", pady=0)

            cat_frame = tk.Frame(row_frame, bg="#F5F5F5", width=380)
            cat_frame.pack(side="left", fill="x", expand=True)

            var = tk.BooleanVar(value=True)
            self.object_category_vars[key] = var

            cb = tk.Checkbutton(cat_frame, text=label, font=("Pretendard", 9, "bold"),
                               bg="#F5F5F5", variable=var, width=5, anchor="w")
            cb.pack(side="left")

            items_short = items[:22] + ".." if len(items) > 22 else items
            tk.Label(cat_frame, text=f": {items_short}",
                    font=("Pretendard", 8), bg="#F5F5F5", fg="#555555",
                    anchor="w").pack(side="left")

        # 초기 상태 설정
        self._on_object_detection_toggle()

        # === 얼굴 인식 설정 === (폰트 추가 15% 축소)
        face_frame = tk.LabelFrame(main_frame, text="얼굴 인식 설정",
                                   font=("Pretendard", 13, "bold"),
                                   bg="#F5F5F5", fg="#2C3E50",
                                   padx=8, pady=4)
        face_frame.pack(fill="x", pady=(0, 6))

        # 얼굴 인식 임계값 (tolerance) (12->10, 10->8)
        tol_row = tk.Frame(face_frame, bg="#F5F5F5")
        tol_row.pack(fill="x", pady=2)
        tk.Label(tol_row, text="인식 민감도:",
                font=("Pretendard", 10), bg="#F5F5F5").pack(side="left")

        self.face_tolerance_var = tk.DoubleVar(value=0.7)
        tol_scale = tk.Scale(tol_row, from_=0.5, to=0.9, resolution=0.05,
                            orient="horizontal", variable=self.face_tolerance_var,
                            font=("Pretendard", 9), bg="#F5F5F5",
                            length=160, showvalue=True)
        tol_scale.pack(side="left", padx=6)

        tk.Label(tol_row, text="(낮을수록 엄격, 높을수록 관대)",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left")

        # 도움말 (10->8)
        tol_help = tk.Frame(face_frame, bg="#F5F5F5")
        tol_help.pack(fill="x")
        tk.Label(tol_help, text="💡 IP 카메라에서 Unknown이 자주 뜨면 값을 높이세요 (권장: 0.75~0.85)",
                font=("Pretendard", 9), bg="#F5F5F5", fg="#1565C0").pack(anchor="w")

        # === 경고 메시지 === (11->9)
        warn_frame = tk.Frame(main_frame, bg="#FFF3CD", padx=6, pady=4)
        warn_frame.pack(fill="x", pady=(0, 6))
        tk.Label(warn_frame, text="⚠️ 성능 설정 변경 시 프로그램을 재시작해야 적용됩니다.",
                font=("Pretendard", 9, "bold"), bg="#FFF3CD", fg="#856404").pack(anchor="w")

        # === 하단 버튼 === (13->11)
        button_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=8, padx=12)

        # 저장 버튼
        save_btn = tk.Button(button_frame, text="저장",
                            command=self._save_settings,
                            bg="#27AE60", fg="#FFFFFF",
                            font=("Pretendard", 11, "bold"),
                            width=10, height=1)
        save_btn.pack(side="left", padx=4, ipady=2)

        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="취소",
                              command=self._close,
                              bg="#95A5A6", fg="#FFFFFF",
                              font=("Pretendard", 11, "bold"),
                              width=10, height=1)
        cancel_btn.pack(side="right", padx=4, ipady=2)

    def _load_settings(self):
        """설정 로드"""
        try:
            # 성능 모드 로드
            perf_mode = int(self.config.env.get("performance_mode", 2))
            perf_mode = max(1, min(3, perf_mode))
            self.performance_mode_var.set(perf_mode)

            # PPE 설정
            self.ppe_enabled_var.set(bool(self.config.env.get("ppe_detection_enabled", True)))
            for key in self.ppe_item_vars:
                val = bool(self.config.env.get(f"ppe_{key}_enabled", True))
                self.ppe_item_vars[key].set(val)
            self._on_ppe_enabled_toggle()

            # 사물 인식 설정
            self.object_detection_enabled_var.set(bool(self.config.env.get("object_detection_enabled", False)))
            for key in self.object_category_vars:
                val = bool(self.config.env.get(f"object_{key}_enabled", True))
                self.object_category_vars[key].set(val)
            self._on_object_detection_toggle()

            # 얼굴 인식 임계값 로드
            face_tolerance = float(self.config.env.get("face_recognition_tolerance", 0.7))
            face_tolerance = max(0.5, min(0.9, face_tolerance))
            self.face_tolerance_var.set(face_tolerance)

        except Exception as e:
            print(f"성능 설정 로드 오류: {e}")

    def _save_settings(self):
        """설정 저장"""
        try:
            # 성능 설정 저장
            old_perf_mode = int(self.config.env.get("performance_mode", 2))
            new_perf_mode = self.performance_mode_var.get()
            self.config.env["performance_mode"] = new_perf_mode

            # PPE 설정 저장
            self.config.env["ppe_detection_enabled"] = self.ppe_enabled_var.get()
            for key, var in self.ppe_item_vars.items():
                self.config.env[f"ppe_{key}_enabled"] = var.get()

            # 사물 인식 설정 저장
            self.config.env["object_detection_enabled"] = self.object_detection_enabled_var.get()
            for key, var in self.object_category_vars.items():
                self.config.env[f"object_{key}_enabled"] = var.get()

            # 얼굴 인식 임계값 저장
            self.config.env["face_recognition_tolerance"] = self.face_tolerance_var.get()

            # 설정 파일 저장
            self.config.save()

            # 성능 설정 변경 시 재시작 안내
            if old_perf_mode != new_perf_mode:
                messagebox.showwarning(
                    "재시작 필요",
                    f"성능 설정이 변경되었습니다.\n\n"
                    f"모드 {old_perf_mode} → 모드 {new_perf_mode}\n\n"
                    f"변경 사항을 적용하려면 프로그램을 재시작하세요.",
                    parent=self.dialog
                )
            else:
                messagebox.showinfo("완료", "성능 설정이 저장되었습니다.", parent=self.dialog)

            self.result = True
            self._close()

        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _load_system_specs(self):
        """시스템 사양 비동기 로드"""
        try:
            summary, recommended_mode, reason = get_system_specs_summary()
            self.recommended_mode = recommended_mode

            # UI 업데이트 (메인 스레드에서 실행)
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self._update_system_specs_ui(summary, recommended_mode, reason))
        except Exception as e:
            print(f"시스템 사양 분석 오류: {e}")
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self._update_system_specs_ui(
                    "시스템 정보를 가져올 수 없습니다.", 2, "기본값 사용"))

    def _update_system_specs_ui(self, summary: str, recommended_mode: int, reason: str):
        """시스템 사양 UI 업데이트"""
        try:
            # 시스템 사양 텍스트 업데이트
            self.system_specs_label.configure(text=summary)

            # 추천 모드 표시
            mode_names = {1: "기본 모드", 2: "표준 모드", 3: "고급 모드"}
            mode_name = mode_names.get(recommended_mode, "표준 모드")
            self.recommend_label.configure(text=f"⭐ 추천: {mode_name} (모드 {recommended_mode})")
            self.recommend_reason_label.configure(text=f"({reason})")

            # 추천 적용 버튼 활성화
            self.apply_recommend_btn.configure(state="normal")

            # 추천 모드 라벨에 표시
            for mode_num, label in self.mode_recommend_labels.items():
                if mode_num == recommended_mode:
                    label.configure(text="⭐ 추천", fg="#E74C3C")
                else:
                    label.configure(text="")

        except Exception as e:
            print(f"시스템 사양 UI 업데이트 오류: {e}")

    def _apply_recommended_mode(self):
        """추천 모드 적용"""
        try:
            self.performance_mode_var.set(self.recommended_mode)
        except Exception as e:
            print(f"추천 모드 적용 오류: {e}")

    def _on_ppe_enabled_toggle(self):
        """PPE 인식 토글"""
        try:
            enabled = bool(self.ppe_enabled_var.get())
            state = "normal" if enabled else "disabled"
            for widget in self.ppe_items_frame.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Checkbutton):
                        child.configure(state=state)
        except Exception as e:
            print(f"PPE 토글 오류: {e}")

    def _on_object_detection_toggle(self):
        """사물 인식 토글"""
        try:
            enabled = bool(self.object_detection_enabled_var.get())
            state = "normal" if enabled else "disabled"
            for widget in self.object_items_frame.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Checkbutton):
                        child.configure(state=state)
        except Exception as e:
            print(f"사물 인식 토글 오류: {e}")

    def _close(self):
        """다이얼로그 닫기"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
