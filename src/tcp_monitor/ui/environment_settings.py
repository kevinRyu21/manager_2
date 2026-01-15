"""
환경설정 다이얼로그

카메라 촬영 여부를 설정합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import os


class EnvironmentSettingsDialog:
    """환경설정 다이얼로그"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.dialog = None
        self.result = False

    def show(self):
        """다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("환경설정")

        # 화면 크기에 맞춰 다이얼로그 크기 조정
        self.dialog.update_idletasks()
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        base_w, base_h = 800, 500  # 높이 10% 확장 (450 -> 500)
        max_h = max(450, screen_h - 100)
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
        """위젯 생성 - 폰트 1.5배 증가 (8->12, 9->14, 10->15, 11->17)"""
        # 제목 (14 -> 21)
        title_label = tk.Label(self.dialog, text="환경설정",
                              font=("Pretendard", 21, "bold"),
                              bg="#F5F5F5", fg="#2C3E50")
        title_label.pack(pady=(15, 10))

        # 메인 프레임
        main_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # === 상단 2열 레이아웃 ===
        top_container = tk.Frame(main_frame, bg="#F5F5F5")
        top_container.pack(fill="x", pady=5)

        # 안전교육 설정 섹션 (왼쪽) - 폰트 1.5배: 11->17
        safety_frame = tk.LabelFrame(top_container, text="안전교육 설정",
                                     font=("Pretendard", 17, "bold"),
                                     bg="#F5F5F5", fg="#2C3E50",
                                     padx=10, pady=8)
        safety_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # 카메라 촬영 설정 - 폰트 1.5배: 10->15
        self.camera_var = tk.BooleanVar()
        tk.Checkbutton(safety_frame, text="안전교육 시 얼굴 촬영",
                      font=("Pretendard", 15, "bold"), bg="#F5F5F5",
                      variable=self.camera_var).pack(anchor="w")
        tk.Label(safety_frame, text="체크 시 교육 완료 시 얼굴을 촬영합니다.",
                font=("Pretendard", 12), bg="#F5F5F5", fg="#666666").pack(anchor="w", padx=15)

        # 패널/센서 설정 섹션 (오른쪽) - 폰트 1.5배: 11->17
        panel_frame = tk.LabelFrame(top_container, text="패널/센서 설정",
                                    font=("Pretendard", 17, "bold"),
                                    bg="#F5F5F5", fg="#2C3E50",
                                    padx=10, pady=8)
        panel_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # 최대 센서 수 - 폰트 1.5배: 10->15, 8->12
        sensor_row = tk.Frame(panel_frame, bg="#F5F5F5")
        sensor_row.pack(fill="x", pady=2)
        tk.Label(sensor_row, text="최대 센서 수:", font=("Pretendard", 15),
                bg="#F5F5F5").pack(side="left")
        self.max_sensors_var = tk.IntVar(value=4)
        tk.Spinbox(sensor_row, from_=1, to=4, textvariable=self.max_sensors_var,
                  font=("Pretendard", 15), width=3).pack(side="left", padx=5)
        tk.Label(sensor_row, text="(1~4)", font=("Pretendard", 12),
                bg="#F5F5F5", fg="#666666").pack(side="left")

        # 그래프 기능 - 폰트 1.5배: 10->15
        self.graph_enabled_var = tk.BooleanVar()
        tk.Checkbutton(panel_frame, text="그래프 기능 사용",
                      font=("Pretendard", 15, "bold"), bg="#F5F5F5",
                      variable=self.graph_enabled_var,
                      command=self._on_graph_enabled_toggle).pack(anchor="w", pady=(3, 0))

        # 동시 그래프 허용 - 폰트 1.5배: 9->14
        self.allow_multi_graph_var = tk.BooleanVar()
        self.allow_multi_graph_checkbox = tk.Checkbutton(
            panel_frame, text="동시 그래프 보기 허용",
            font=("Pretendard", 14), bg="#F5F5F5",
            variable=self.allow_multi_graph_var, state="disabled")
        self.allow_multi_graph_checkbox.pack(anchor="w", padx=15)

        # 동시 그래프 최대 수 - 폰트 1.5배: 9->14
        mg_row = tk.Frame(panel_frame, bg="#F5F5F5")
        mg_row.pack(fill="x", padx=15, pady=2)
        tk.Label(mg_row, text="최대 그래프 수:", font=("Pretendard", 14),
                bg="#F5F5F5").pack(side="left")
        self.max_graphs_var = tk.IntVar(value=1)
        self.max_graphs_spin = tk.Spinbox(mg_row, from_=1, to=4,
                                          textvariable=self.max_graphs_var,
                                          font=("Pretendard", 14), width=3)
        self.max_graphs_spin.pack(side="left", padx=3)

        # 카메라 리셋 버튼은 카메라 설정으로 이동됨 (v1.9.8.3-1)

        # === 안내 메시지 ===
        info_frame = tk.Frame(main_frame, bg="#E3F2FD", padx=10, pady=8)
        info_frame.pack(fill="x", pady=(15, 5))
        tk.Label(info_frame, text="💡 AI 인식 수준, 안전장구/사물 인식 설정은 [설정 > 성능 설정] 메뉴에서 변경하세요.",
                font=("Pretendard", 12), bg="#E3F2FD", fg="#1565C0").pack(anchor="w")

        # === 하단 버튼 (고정) === - 폰트 1.5배: 11->17
        button_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=15, padx=20)

        # 저장 버튼 - 폰트 1.5배: 11->17
        save_btn = tk.Button(button_frame, text="저장",
                            command=self._save_settings,
                            bg="#27AE60", fg="#FFFFFF",
                            font=("Pretendard", 15, "bold"),
                            width=10, height=1)
        save_btn.pack(side="left", padx=5, ipady=5)

        # 취소 버튼 - 폰트 1.5배: 11->17
        cancel_btn = tk.Button(button_frame, text="취소",
                              command=self._close,
                              bg="#95A5A6", fg="#FFFFFF",
                              font=("Pretendard", 15, "bold"),
                              width=10, height=1)
        cancel_btn.pack(side="right", padx=5, ipady=5)

    def _load_settings(self):
        """설정 로드"""
        try:
            # 카메라 설정
            camera_enabled = self.config.env.get("safety_education_photo", True)
            self.camera_var.set(camera_enabled)

            # 최대 센서 수
            max_s = 4
            try:
                if hasattr(self.config, 'env') and 'max_sensors' in self.config.env:
                    max_s = int(self.config.env.get("max_sensors", 4))
                elif hasattr(self.config, 'ui') and 'max_sensors' in self.config.ui:
                    max_s = int(self.config.ui.get("max_sensors", 4))
            except Exception:
                max_s = 4
            max_s = max(1, min(4, max_s))
            self.max_sensors_var.set(max_s)

            # 그래프 기능
            graph_enabled = bool(self.config.env.get("graph_enabled", True))
            self.graph_enabled_var.set(graph_enabled)
            self._on_graph_enabled_toggle()

            # 동시 그래프
            self.allow_multi_graph_var.set(bool(self.config.env.get("allow_multi_graph_view", False)))

            # 최대 그래프 수
            max_graphs = max(1, min(4, int(self.config.env.get("max_graphs", 1))))
            self.max_graphs_var.set(max_graphs)

        except Exception as e:
            print(f"설정 로드 오류: {e}")

    def _save_settings(self):
        """설정 저장"""
        try:
            # 카메라 설정 저장
            self.config.env["safety_education_photo"] = self.camera_var.get()

            # 최대 센서 수 저장
            max_s = max(1, min(4, int(self.max_sensors_var.get())))
            self.config.env["max_sensors"] = max_s
            if hasattr(self.config, 'ui'):
                self.config.ui["max_sensors"] = max_s

            # 그래프 설정 저장
            graph_enabled_before = self.config.env.get("graph_enabled", True)
            graph_enabled_after = self.graph_enabled_var.get()
            self.config.env["graph_enabled"] = graph_enabled_after
            self.config.env["allow_multi_graph_view"] = self.allow_multi_graph_var.get()
            self.config.env["max_graphs"] = max(1, min(4, int(self.max_graphs_var.get())))

            # 설정 파일 저장
            self.config.save()

            # 그래프 설정 변경 즉시 반영
            if graph_enabled_before != graph_enabled_after:
                try:
                    for key, panel in list(self.parent.panels.items()):
                        if hasattr(panel, 'header') and hasattr(panel.header, 'update_mode_buttons'):
                            current_mode = getattr(panel, 'view_mode', 'card')
                            panel.header.update_mode_buttons(current_mode)
                        if not graph_enabled_after:
                            if hasattr(panel, 'view_mode') and panel.view_mode == "graph":
                                try:
                                    panel.switch_to_card_mode()
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"그래프 설정 반영 오류: {e}")

            # 최대 센서 수 반영
            try:
                if hasattr(self.parent, "_remove_waiting_panel_if_reached"):
                    self.parent._remove_waiting_panel_if_reached()
                if hasattr(self.parent, "_ensure_waiting_panel_if_needed"):
                    self.parent._ensure_waiting_panel_if_needed()
                if hasattr(self.parent, "_update_waiting_tab_title"):
                    self.parent._update_waiting_tab_title()
            except Exception:
                pass

            messagebox.showinfo("완료", "환경설정이 저장되었습니다.", parent=self.dialog)
            self.result = True
            self._close()

        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _reset_cameras(self):
        """모든 카메라 리셋"""
        try:
            import cv2
            import subprocess
            import platform

            confirm = messagebox.askyesno(
                "카메라 리셋",
                "모든 카메라를 리셋하시겠습니까?\n\n"
                "현재 사용 중인 카메라가 모두 해제됩니다.",
                parent=self.dialog
            )

            if not confirm:
                return

            reset_count = 0
            mirror_panels = []

            # 패널 거울보기 카메라 종료
            for key, panel in list(self.parent.panels.items()):
                try:
                    if hasattr(panel, 'mirror_mode_active') and panel.mirror_mode_active:
                        mirror_panels.append(key)
                        if hasattr(panel, 'hide_mirror_view'):
                            panel.hide_mirror_view()

                    if hasattr(panel, 'mirror_camera') and panel.mirror_camera is not None:
                        panel.mirror_camera.release()
                        panel.mirror_camera = None
                        reset_count += 1

                    if hasattr(panel, 'header') and hasattr(panel.header, 'mirror_btn'):
                        panel.header.mirror_mode = False
                        panel.header.mirror_camera_ready = False
                        panel.header.mirror_btn.configure(text="거울 준비중", bg="#9C27B0", state="disabled")
                except Exception as e:
                    print(f"카메라 리셋 오류: {e}")

            # 시스템 카메라 해제
            for i in range(10):
                try:
                    cam = cv2.VideoCapture(i)
                    if cam.isOpened():
                        cam.release()
                        reset_count += 1
                except Exception:
                    pass

            self.parent.after(2000, lambda: self._check_camera_availability_after_reset(mirror_panels))
            messagebox.showinfo("완료", f"카메라 리셋 완료 ({reset_count}개 해제)", parent=self.dialog)

        except Exception as e:
            messagebox.showerror("오류", f"카메라 리셋 오류:\n{str(e)}", parent=self.dialog)

    def _check_camera_availability_after_reset(self, mirror_panels):
        """카메라 리셋 후 가용성 재확인"""
        try:
            for key, panel in list(self.parent.panels.items()):
                if hasattr(panel, '_check_camera_availability'):
                    panel._check_camera_availability()
        except Exception as e:
            print(f"카메라 가용성 재확인 오류: {e}")

    def _on_camera_toggle(self):
        """카메라 설정 토글"""
        pass

    def _on_graph_enabled_toggle(self):
        """그래프 사용 토글"""
        try:
            enabled = bool(self.graph_enabled_var.get())
            state = "normal" if enabled else "disabled"
            self.allow_multi_graph_checkbox.configure(state=state)
            self.max_graphs_spin.configure(state=state)
        except Exception:
            pass

    def _close(self):
        """다이얼로그 닫기"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
