#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카메라 설정 다이얼로그
- USB 카메라 목록 표시 및 선택
- IP 카메라 추가/편집/삭제
- 화면 반전 설정
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os


class CameraSettingsDialog:
    """카메라 설정 다이얼로그"""

    def __init__(self, parent, config):
        """
        Args:
            parent: 부모 윈도우 (App)
            config: 설정 객체
        """
        self.parent = parent
        self.config = config
        self.result = False

        # 다이얼로그 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("카메라 설정")
        self.dialog.geometry("750x700")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#2C3E50")

        # 모달 설정
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 750) // 2
        y = (self.dialog.winfo_screenheight() - 700) // 2
        self.dialog.geometry(f"750x700+{x}+{y}")

        # IP 카메라 목록 (설정에서 로드)
        self.ip_cameras = self._load_ip_cameras()

        # UI 생성
        self._create_ui()

        # 닫기 이벤트
        self.dialog.protocol("WM_DELETE_WINDOW", self._close)

    def show(self):
        """다이얼로그 표시 및 결과 반환"""
        self.dialog.wait_window()
        return self.result

    def _load_ip_cameras(self):
        """저장된 IP 카메라 목록 로드"""
        cameras = []
        try:
            if hasattr(self.config, 'camera'):
                ip_list = self.config.camera.get("ip_cameras", [])
                if isinstance(ip_list, list):
                    cameras = ip_list
        except Exception:
            pass
        return cameras

    def _create_ui(self):
        """UI 생성"""
        # 제목
        title_label = tk.Label(
            self.dialog,
            text="📷 카메라 설정",
            font=("Pretendard", 18, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF"
        )
        title_label.pack(pady=(20, 15))

        # 메인 프레임
        main_frame = tk.Frame(self.dialog, bg="#2C3E50")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # === USB 카메라 섹션 ===
        usb_frame = tk.LabelFrame(
            main_frame,
            text=" USB 카메라 ",
            font=("Pretendard", 12, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF",
            padx=10,
            pady=10
        )
        usb_frame.pack(fill="x", pady=(0, 15))

        # USB 카메라 목록
        usb_list_frame = tk.Frame(usb_frame, bg="#2C3E50")
        usb_list_frame.pack(fill="x")

        tk.Label(
            usb_list_frame,
            text="카메라 선택:",
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF"
        ).pack(side="left", padx=(0, 10))

        self.usb_cameras = self._get_usb_cameras()
        usb_names = [name for idx, name in self.usb_cameras]
        if not usb_names:
            usb_names = ["USB 카메라 없음"]

        self.usb_combo = ttk.Combobox(
            usb_list_frame,
            values=usb_names,
            state="readonly",
            width=40,
            font=("Pretendard", 11)
        )
        self.usb_combo.pack(side="left", fill="x", expand=True)

        # 현재 선택된 USB 카메라 설정
        current_idx = self.config.camera.get("device_index", 0) if hasattr(self.config, 'camera') else 0
        for i, (idx, name) in enumerate(self.usb_cameras):
            if idx == current_idx:
                self.usb_combo.current(i)
                break
        else:
            if self.usb_cameras:
                self.usb_combo.current(0)

        # 새로고침 버튼
        refresh_btn = tk.Button(
            usb_list_frame,
            text="🔄",
            font=("Pretendard", 11),
            bg="#34495E",
            fg="#FFFFFF",
            width=3,
            command=self._refresh_usb_cameras
        )
        refresh_btn.pack(side="left", padx=(10, 0))

        # === IP 카메라 섹션 ===
        ip_frame = tk.LabelFrame(
            main_frame,
            text=" IP 카메라 ",
            font=("Pretendard", 12, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF",
            padx=10,
            pady=10
        )
        ip_frame.pack(fill="both", expand=True, pady=(0, 15))

        # IP 카메라 리스트박스
        ip_list_frame = tk.Frame(ip_frame, bg="#2C3E50")
        ip_list_frame.pack(fill="both", expand=True)

        self.ip_listbox = tk.Listbox(
            ip_list_frame,
            font=("Pretendard", 11),
            bg="#34495E",
            fg="#FFFFFF",
            selectbackground="#3498DB",
            height=6
        )
        self.ip_listbox.pack(side="left", fill="both", expand=True)

        ip_scrollbar = tk.Scrollbar(ip_list_frame)
        ip_scrollbar.pack(side="right", fill="y")
        self.ip_listbox.config(yscrollcommand=ip_scrollbar.set)
        ip_scrollbar.config(command=self.ip_listbox.yview)

        # IP 카메라 목록 채우기
        self._update_ip_listbox()

        # IP 카메라 버튼
        ip_btn_frame = tk.Frame(ip_frame, bg="#2C3E50")
        ip_btn_frame.pack(fill="x", pady=(10, 0))

        add_btn = tk.Button(
            ip_btn_frame,
            text="➕ 추가",
            font=("Pretendard", 11),
            bg="#27AE60",
            fg="#FFFFFF",
            width=10,
            command=self._add_ip_camera
        )
        add_btn.pack(side="left", padx=(0, 5))

        edit_btn = tk.Button(
            ip_btn_frame,
            text="✏️ 편집",
            font=("Pretendard", 11),
            bg="#3498DB",
            fg="#FFFFFF",
            width=10,
            command=self._edit_ip_camera
        )
        edit_btn.pack(side="left", padx=5)

        del_btn = tk.Button(
            ip_btn_frame,
            text="🗑️ 삭제",
            font=("Pretendard", 11),
            bg="#E74C3C",
            fg="#FFFFFF",
            width=10,
            command=self._delete_ip_camera
        )
        del_btn.pack(side="left", padx=5)

        # === 화면 반전 ===
        flip_frame = tk.Frame(main_frame, bg="#2C3E50")
        flip_frame.pack(fill="x", pady=(0, 15))

        flip_value = True
        if hasattr(self.config, 'camera'):
            flip_value = self.config.camera.get("flip_horizontal", True)
        self.flip_var = tk.BooleanVar(value=flip_value)

        flip_check = tk.Checkbutton(
            flip_frame,
            text="🔄 화면 좌우 반전 (거울 모드)",
            variable=self.flip_var,
            font=("Pretendard", 12),
            bg="#2C3E50",
            fg="#FFFFFF",
            selectcolor="#34495E",
            activebackground="#2C3E50",
            activeforeground="#FFFFFF"
        )
        flip_check.pack(side="left")

        # === 사용할 카메라 선택 ===
        use_frame = tk.LabelFrame(
            main_frame,
            text=" 사용할 카메라 ",
            font=("Pretendard", 12, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF",
            padx=10,
            pady=10
        )
        use_frame.pack(fill="x", pady=(0, 10))

        # 현재 설정된 카메라 타입 확인 (use_ip_camera 설정 우선 사용)
        use_ip = False
        if hasattr(self.config, 'camera'):
            # use_ip_camera 설정이 있으면 사용, 없으면 ip_camera_url로 판단
            use_ip = self.config.camera.get("use_ip_camera", False)
            if not use_ip and self.config.camera.get("ip_camera_url", ""):
                use_ip = True  # 하위 호환성

        self.use_camera_var = tk.StringVar(value="ip" if use_ip else "usb")

        usb_radio = tk.Radiobutton(
            use_frame,
            text="USB 카메라 사용",
            variable=self.use_camera_var,
            value="usb",
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF",
            selectcolor="#34495E",
            activebackground="#2C3E50",
            activeforeground="#FFFFFF"
        )
        usb_radio.pack(side="left", padx=(0, 20))

        ip_radio = tk.Radiobutton(
            use_frame,
            text="IP 카메라 사용",
            variable=self.use_camera_var,
            value="ip",
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF",
            selectcolor="#34495E",
            activebackground="#2C3E50",
            activeforeground="#FFFFFF"
        )
        ip_radio.pack(side="left")

        # === 버튼 ===
        btn_frame = tk.Frame(self.dialog, bg="#34495E", pady=15)
        btn_frame.pack(fill="x", side="bottom")

        # 버튼 중앙 정렬용 프레임
        btn_inner = tk.Frame(btn_frame, bg="#34495E")
        btn_inner.pack()

        save_btn = tk.Button(
            btn_inner,
            text="💾 저장",
            font=("Pretendard", 11, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._save
        )
        save_btn.pack(side="left", padx=5)

        reset_btn = tk.Button(
            btn_inner,
            text="🔄 리셋",
            font=("Pretendard", 11),
            bg="#E67E22",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._reset_cameras
        )
        reset_btn.pack(side="left", padx=5)

        advanced_btn = tk.Button(
            btn_inner,
            text="⚙️ 고급설정",
            font=("Pretendard", 11),
            bg="#9B59B6",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._open_advanced_settings
        )
        advanced_btn.pack(side="left", padx=5)

        close_btn = tk.Button(
            btn_inner,
            text="🚪 닫기",
            font=("Pretendard", 11),
            bg="#7F8C8D",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._close
        )
        close_btn.pack(side="left", padx=5)

    def _open_advanced_settings(self):
        """고급 설정 다이얼로그 열기"""
        try:
            from .camera_advanced_settings import CameraAdvancedSettingsDialog
            # 카메라 설정 다이얼로그의 grab 해제 (중첩 방지)
            self.dialog.grab_release()
            dialog = CameraAdvancedSettingsDialog(self.dialog, self.config)
            dialog.show()

            # 고급 설정 닫힐 때 카메라 설정의 grab 복원
            def on_advanced_close():
                try:
                    self.dialog.grab_set()
                except:
                    pass

            dialog.dialog.bind("<Destroy>", lambda e: on_advanced_close())

        except Exception as e:
            self.dialog.grab_set()
            messagebox.showerror("오류", f"고급 설정 열기 실패:\n{str(e)}", parent=self.dialog)

    def _reset_cameras(self):
        """모든 카메라 리셋 (환경설정에서 이동됨)"""
        try:
            import cv2

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

            # 2초 후 카메라 가용성 재확인
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

    def _get_usb_cameras(self):
        """USB 카메라 목록 검색 (V4L2 sysfs 기반 - 빠른 검색)"""
        cameras = []

        # Linux: /dev/video* 장치 검색 (sysfs index로 메타데이터 장치 필터링)
        for i in range(10):
            device_path = f"/dev/video{i}"
            if not os.path.exists(device_path):
                continue

            try:
                # V4L2 index 파일로 메타데이터 장치 필터링
                index_path = f"/sys/class/video4linux/video{i}/index"
                if os.path.exists(index_path):
                    with open(index_path, 'r') as f:
                        idx_val = f.read().strip()
                        if idx_val != '0':
                            # 메타데이터 장치는 스킵 (index != 0)
                            continue

                # 장치 이름 읽기
                name = f"카메라 {i}"
                name_path = f"/sys/class/video4linux/video{i}/name"
                if os.path.exists(name_path):
                    with open(name_path, 'r') as f:
                        device_name = f.read().strip()
                        if device_name:
                            name = f"{device_name} ({i})"

                cameras.append((i, name))
            except Exception:
                continue

        return cameras

    def _refresh_usb_cameras(self):
        """USB 카메라 목록 새로고침"""
        self.usb_cameras = self._get_usb_cameras()
        usb_names = [name for idx, name in self.usb_cameras]
        if not usb_names:
            usb_names = ["USB 카메라 없음"]
        self.usb_combo['values'] = usb_names
        if self.usb_cameras:
            self.usb_combo.current(0)

    def _update_ip_listbox(self):
        """IP 카메라 리스트박스 업데이트"""
        self.ip_listbox.delete(0, tk.END)
        for cam in self.ip_cameras:
            name = cam.get("name", "IP 카메라")
            ip = cam.get("ip", "")
            ptz = cam.get("ptz_enabled", False)
            ptz_icon = " 🎮" if ptz else ""
            self.ip_listbox.insert(tk.END, f"🌐 {name} ({ip}){ptz_icon}")

    def _save_ip_cameras_to_config(self):
        """IP 카메라 목록을 설정에 즉시 저장"""
        try:
            if not hasattr(self.config, 'camera'):
                self.config.camera = {}
            self.config.camera["ip_cameras"] = self.ip_cameras
            self.config.save()
        except Exception as e:
            print(f"IP 카메라 설정 저장 오류: {e}")

    def _add_ip_camera(self):
        """IP 카메라 추가"""
        dialog = IPCameraDialog(self.dialog, None)
        self.dialog.wait_window(dialog.dialog)

        if dialog.result:
            self.ip_cameras.append(dialog.result)
            self._update_ip_listbox()
            # 추가 즉시 설정에 저장
            self._save_ip_cameras_to_config()

    def _edit_ip_camera(self):
        """IP 카메라 편집"""
        selection = self.ip_listbox.curselection()
        if not selection:
            messagebox.showwarning("선택 필요", "편집할 IP 카메라를 선택하세요.", parent=self.dialog)
            return

        idx = selection[0]
        camera_data = self.ip_cameras[idx]

        dialog = IPCameraDialog(self.dialog, camera_data)
        self.dialog.wait_window(dialog.dialog)

        if dialog.result:
            self.ip_cameras[idx] = dialog.result
            self._update_ip_listbox()
            # 편집 즉시 설정에 저장
            self._save_ip_cameras_to_config()

    def _delete_ip_camera(self):
        """IP 카메라 삭제"""
        selection = self.ip_listbox.curselection()
        if not selection:
            messagebox.showwarning("선택 필요", "삭제할 IP 카메라를 선택하세요.", parent=self.dialog)
            return

        idx = selection[0]
        name = self.ip_cameras[idx].get("name", "IP 카메라")

        if messagebox.askyesno("삭제 확인", f"'{name}'을(를) 삭제하시겠습니까?", parent=self.dialog):
            del self.ip_cameras[idx]
            self._update_ip_listbox()
            # 삭제 즉시 설정에 저장
            self._save_ip_cameras_to_config()

    def _save(self):
        """설정 저장"""
        try:
            if not hasattr(self.config, 'camera'):
                self.config.camera = {}

            # 화면 반전 설정
            self.config.camera["flip_horizontal"] = self.flip_var.get()

            # IP 카메라 목록 저장
            self.config.camera["ip_cameras"] = self.ip_cameras

            # 사용할 카메라 설정
            use_ip = self.use_camera_var.get() == "ip"
            self.config.camera["use_ip_camera"] = use_ip  # IP 카메라 사용 여부 저장

            if not use_ip:
                # USB 카메라 선택
                self.config.camera["ip_camera_url"] = ""
                self.config.camera["ip_camera_name"] = ""

                selection = self.usb_combo.current()
                if selection >= 0 and selection < len(self.usb_cameras):
                    idx, name = self.usb_cameras[selection]
                    self.config.camera["device_index"] = idx
                    self.config.camera["device_name"] = name
                else:
                    self.config.camera["device_index"] = 0
                    self.config.camera["device_name"] = ""
            else:
                # IP 카메라 선택
                selection = self.ip_listbox.curselection()
                if selection and selection[0] < len(self.ip_cameras):
                    cam = self.ip_cameras[selection[0]]
                    url = self._build_rtsp_url(cam)
                    self.config.camera["ip_camera_url"] = url
                    self.config.camera["ip_camera_name"] = cam.get("name", "IP 카메라")
                    self.config.camera["selected_ip_camera"] = cam.get("name", "")  # 선택된 IP 카메라 이름 저장
                elif self.ip_cameras:
                    # 선택 안 되어 있으면 첫 번째 사용
                    cam = self.ip_cameras[0]
                    url = self._build_rtsp_url(cam)
                    self.config.camera["ip_camera_url"] = url
                    self.config.camera["ip_camera_name"] = cam.get("name", "IP 카메라")
                    self.config.camera["selected_ip_camera"] = cam.get("name", "")
                else:
                    messagebox.showwarning("IP 카메라 없음", "IP 카메라를 먼저 추가해주세요.", parent=self.dialog)
                    return

            # 설정 파일 저장
            self.config.save()

            # 거울보기가 실행 중이면 자동으로 카메라 재시작
            self._apply_camera_change()

            # 저장 완료 알림 (최상위 창으로 표시) - 확인 누르면 창 닫기
            self._show_save_complete_dialog()
            self.result = True

        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _apply_camera_change(self):
        """카메라 설정 변경 즉시 적용 (거울보기 실행 중일 때)"""
        try:
            # parent가 App이고 현재 패널이 있으면
            if hasattr(self.parent, 'current_panel') and self.parent.current_panel is not None:
                panel = self.parent.current_panel

                # 거울보기가 실행 중인지 확인
                if hasattr(panel, '_mirror_running') and panel._mirror_running:
                    print("[카메라 설정] 거울보기 실행 중 - 카메라 재시작 중...")

                    # _restart_mirror_camera 호출 (panel.py에 정의됨)
                    if hasattr(panel, '_restart_mirror_camera'):
                        panel._restart_mirror_camera()
                        print("[카메라 설정] 카메라 재시작 완료")
                    else:
                        print("[카메라 설정] _restart_mirror_camera 메서드 없음")
                else:
                    print("[카메라 설정] 거울보기 미실행 - 다음 시작 시 적용됨")
        except Exception as e:
            print(f"[카메라 설정] 즉시 적용 오류: {e}")

    def _show_save_complete_dialog(self):
        """저장 완료 다이얼로그 표시 (확인 버튼 클릭 시 카메라 설정 창 닫기)"""
        # 커스텀 최상위 대화상자 생성
        info_dialog = tk.Toplevel(self.dialog)
        info_dialog.title("저장 완료")
        info_dialog.geometry("350x220")  # 높이 10% 확장
        info_dialog.resizable(False, False)
        info_dialog.configure(bg="#2C3E50")

        # 최상위로 설정
        info_dialog.attributes('-topmost', True)
        info_dialog.transient(self.dialog)
        info_dialog.grab_set()

        # 중앙 배치
        info_dialog.update_idletasks()
        x = (info_dialog.winfo_screenwidth() - 350) // 2
        y = (info_dialog.winfo_screenheight() - 220) // 2
        info_dialog.geometry(f"350x220+{x}+{y}")

        # 메시지
        tk.Label(
            info_dialog,
            text="✅",
            font=("Pretendard", 24),
            bg="#2C3E50",
            fg="#27AE60"
        ).pack(pady=(20, 10))

        tk.Label(
            info_dialog,
            text="카메라 설정이 저장되었습니다.\n\n거울보기 실행 중이면 자동 적용됩니다.",
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF",
            justify="center"
        ).pack(pady=10)

        def on_confirm():
            """확인 버튼 클릭 시 모든 창 닫기"""
            info_dialog.destroy()
            self.dialog.destroy()

        # 확인 버튼
        tk.Button(
            info_dialog,
            text="확인",
            font=("Pretendard", 11, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            width=10,
            command=on_confirm
        ).pack(pady=15)

        # 포커스
        info_dialog.focus_set()

    def _build_rtsp_url(self, camera_info):
        """카메라 정보로 RTSP URL 생성"""
        protocol = camera_info.get("protocol", "rtsp")
        ip = camera_info.get("ip", "")
        port = camera_info.get("port", "554")
        username = camera_info.get("username", "")
        password = camera_info.get("password", "")
        path = camera_info.get("path", "/stream1")

        if username and password:
            return f"{protocol}://{username}:{password}@{ip}:{port}{path}"
        else:
            return f"{protocol}://{ip}:{port}{path}"

    def _close(self):
        """다이얼로그 닫기 (확인 없이 바로 닫기)"""
        self.dialog.destroy()


class IPCameraDialog:
    """IP 카메라 추가/편집 다이얼로그"""

    def __init__(self, parent, camera_data=None):
        """
        Args:
            parent: 부모 윈도우
            camera_data: 기존 카메라 데이터 (편집 시)
        """
        self.parent = parent
        self.camera_data = camera_data or {}
        self.result = None

        # 다이얼로그 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("IP 카메라 추가" if not camera_data else "IP 카메라 편집")
        self.dialog.geometry("500x720")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#2C3E50")

        # 모달 설정
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 500) // 2
        y = (self.dialog.winfo_screenheight() - 720) // 2
        self.dialog.geometry(f"500x720+{x}+{y}")

        # UI 생성
        self._create_ui()

        # 닫기 이벤트
        self.dialog.protocol("WM_DELETE_WINDOW", self._close)

    def _create_ui(self):
        """UI 생성"""
        # 제목
        title_label = tk.Label(
            self.dialog,
            text="🌐 IP 카메라 설정",
            font=("Pretendard", 14, "bold"),
            bg="#2C3E50",
            fg="#FFFFFF"
        )
        title_label.pack(pady=(15, 10))

        # 입력 프레임
        form_frame = tk.Frame(self.dialog, bg="#2C3E50")
        form_frame.pack(fill="x", padx=30, pady=10)

        # 이름
        self._create_input_row(form_frame, "카메라 이름:", "name", self.camera_data.get("name", ""), 0)

        # 프로토콜
        protocol_frame = tk.Frame(form_frame, bg="#2C3E50")
        protocol_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        tk.Label(protocol_frame, text="프로토콜:", font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF").pack(side="left", padx=(0, 10))

        self.protocol_var = tk.StringVar(value=self.camera_data.get("protocol", "rtsp"))
        protocols = ["rtsp", "http", "https", "onvif"]
        for proto in protocols:
            tk.Radiobutton(
                protocol_frame,
                text=proto.upper(),
                variable=self.protocol_var,
                value=proto,
                font=("Pretendard", 10),
                bg="#2C3E50",
                fg="#FFFFFF",
                selectcolor="#34495E",
                activebackground="#2C3E50",
                command=self._on_protocol_change
            ).pack(side="left", padx=5)

        # IP 주소
        self._create_input_row(form_frame, "IP 주소:", "ip", self.camera_data.get("ip", ""), 2)

        # 포트
        self._create_input_row(form_frame, "포트:", "port", self.camera_data.get("port", "554"), 3)

        # 경로 (Tapo 카메라는 /stream1 또는 /stream2)
        self._create_input_row(form_frame, "스트림 경로:", "path", self.camera_data.get("path", "/stream1"), 4)

        # 경로 안내 (프로토콜에 따라 변경)
        self.path_hint = tk.Label(
            form_frame,
            text="Tapo: /stream1(고화질) /stream2(저화질)",
            font=("Pretendard", 9),
            bg="#2C3E50",
            fg="#95A5A6"
        )
        self.path_hint.grid(row=4, column=1, sticky="e", padx=(10, 0))

        # 폼 프레임 저장 (프로토콜 변경 시 사용)
        self.form_frame = form_frame

        # 사용자명
        self._create_input_row(form_frame, "사용자명:", "username", self.camera_data.get("username", ""), 5)

        # 비밀번호
        self._create_input_row(form_frame, "비밀번호:", "password", self.camera_data.get("password", ""), 6, show="*")

        # PTZ (Pan-Tilt-Zoom) 지원 체크박스
        ptz_frame = tk.Frame(form_frame, bg="#2C3E50")
        ptz_frame.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 5))

        self.ptz_var = tk.BooleanVar(value=self.camera_data.get("ptz_enabled", False))
        ptz_check = tk.Checkbutton(
            ptz_frame,
            text="🎮 PTZ (Pan-Tilt-Zoom) 제어 활성화",
            variable=self.ptz_var,
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF",
            selectcolor="#34495E",
            activebackground="#2C3E50",
            activeforeground="#FFFFFF"
        )
        ptz_check.pack(side="left")

        ptz_hint = tk.Label(
            form_frame,
            text="Tapo C210/C211/C220/C225 등 PTZ 지원 카메라용",
            font=("Pretendard", 9),
            bg="#2C3E50",
            fg="#95A5A6"
        )
        ptz_hint.grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 5))

        # PTZ Tapo 계정 입력 (RTSP 계정과 별도)
        ptz_account_frame = tk.LabelFrame(
            form_frame,
            text=" PTZ 제어용 Tapo 계정 ",
            font=("Pretendard", 10, "bold"),
            bg="#2C3E50",
            fg="#F39C12",
            padx=5,
            pady=5
        )
        ptz_account_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        # Tapo 계정 안내
        ptz_account_hint = tk.Label(
            ptz_account_frame,
            text="PTZ 제어는 TP-Link 클라우드 계정이 필요합니다.\n(Tapo 앱 로그인에 사용하는 이메일/비밀번호)\nRTSP 로컬 계정(카메라계정)과 다릅니다!",
            font=("Pretendard", 9),
            bg="#2C3E50",
            fg="#F39C12",
            justify="left"
        )
        ptz_account_hint.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        # Tapo 이메일
        tk.Label(
            ptz_account_frame,
            text="Tapo 이메일:",
            font=("Pretendard", 10),
            bg="#2C3E50",
            fg="#FFFFFF"
        ).grid(row=1, column=0, sticky="w", pady=3)

        self.ptz_email_entry = tk.Entry(
            ptz_account_frame,
            font=("Pretendard", 10),
            width=28,
            bg="#34495E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF"
        )
        self.ptz_email_entry.grid(row=1, column=1, sticky="w", pady=3, padx=(5, 0))
        self.ptz_email_entry.insert(0, self.camera_data.get("ptz_email", ""))

        # Tapo 비밀번호
        tk.Label(
            ptz_account_frame,
            text="Tapo 비밀번호:",
            font=("Pretendard", 10),
            bg="#2C3E50",
            fg="#FFFFFF"
        ).grid(row=2, column=0, sticky="w", pady=3)

        self.ptz_password_entry = tk.Entry(
            ptz_account_frame,
            font=("Pretendard", 10),
            width=28,
            bg="#34495E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            show="*"
        )
        self.ptz_password_entry.grid(row=2, column=1, sticky="w", pady=3, padx=(5, 0))
        self.ptz_password_entry.insert(0, self.camera_data.get("ptz_password", ""))

        # 연결 테스트 섹션
        test_frame = tk.Frame(self.dialog, bg="#2C3E50")
        test_frame.pack(fill="x", padx=30, pady=10)

        test_btn = tk.Button(
            test_frame,
            text="🔗 RTSP 테스트",
            font=("Pretendard", 11, "bold"),
            bg="#3498DB",
            fg="#FFFFFF",
            width=12,
            command=self._test_connection
        )
        test_btn.pack(side="left")

        # PTZ 연결 테스트 버튼
        self.ptz_test_btn = tk.Button(
            test_frame,
            text="🎮 PTZ 테스트",
            font=("Pretendard", 11, "bold"),
            bg="#9B59B6",
            fg="#FFFFFF",
            width=12,
            command=self._test_ptz_connection
        )
        self.ptz_test_btn.pack(side="left", padx=(10, 0))

        # 연결 테스트 결과 표시 레이블 (폰트 30% 축소)
        self.test_result_label = tk.Label(
            test_frame,
            text="",
            font=("Pretendard", 7),
            bg="#2C3E50",
            fg="#FFFFFF"
        )
        self.test_result_label.pack(side="left", padx=10, fill="x", expand=True)

        # === 버튼 ===
        btn_frame = tk.Frame(self.dialog, bg="#34495E", pady=12)
        btn_frame.pack(fill="x", side="bottom")

        # 버튼 중앙 정렬용 프레임
        btn_inner = tk.Frame(btn_frame, bg="#34495E")
        btn_inner.pack()

        save_btn = tk.Button(
            btn_inner,
            text="💾 저장",
            font=("Pretendard", 12, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._save
        )
        save_btn.pack(side="left", padx=8)

        cancel_btn = tk.Button(
            btn_inner,
            text="❌ 취소",
            font=("Pretendard", 12),
            bg="#E74C3C",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._close
        )
        cancel_btn.pack(side="left", padx=8)

        close_btn = tk.Button(
            btn_inner,
            text="🚪 닫기",
            font=("Pretendard", 12),
            bg="#7F8C8D",
            fg="#FFFFFF",
            width=10,
            height=2,
            command=self._close
        )
        close_btn.pack(side="left", padx=8)

    def _create_input_row(self, parent, label_text, field_name, default_value, row, show=None):
        """입력 행 생성"""
        tk.Label(
            parent,
            text=label_text,
            font=("Pretendard", 11),
            bg="#2C3E50",
            fg="#FFFFFF"
        ).grid(row=row, column=0, sticky="w", pady=5)

        entry = tk.Entry(
            parent,
            font=("Pretendard", 11),
            width=30,
            bg="#34495E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            show=show
        )
        entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        entry.insert(0, default_value)

        setattr(self, f"{field_name}_entry", entry)

    def _on_protocol_change(self):
        """프로토콜 변경 시 힌트 및 기본값 업데이트"""
        protocol = self.protocol_var.get()

        if protocol == "onvif":
            self.path_hint.configure(text="ONVIF: 자동 스트림 URL 탐색")
            # 포트 기본값 변경 (ONVIF 기본 포트: 80 또는 8080)
            if self.port_entry.get() in ["554", ""]:
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, "80")
            # 경로는 ONVIF에서 자동 탐색되므로 안내
            if self.path_entry.get() in ["/stream1", "/stream2", ""]:
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, "/onvif/device_service")
        elif protocol == "rtsp":
            self.path_hint.configure(text="Tapo: /stream1(고화질) /stream2(저화질)")
            if self.port_entry.get() in ["80", "8080", ""]:
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, "554")
            if self.path_entry.get() == "/onvif/device_service":
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, "/stream1")
        elif protocol in ["http", "https"]:
            self.path_hint.configure(text="HTTP: /video /mjpg/video.mjpg 등")
            if self.port_entry.get() in ["554", ""]:
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, "80" if protocol == "http" else "443")

    def _test_connection(self):
        """연결 테스트"""
        try:
            import cv2
            import threading

            camera_info = self._get_camera_info()
            if not camera_info.get("ip"):
                self.test_result_label.configure(text="⚠️ IP 주소를 입력하세요", fg="#F39C12")
                return

            protocol = camera_info.get("protocol", "rtsp")

            # ONVIF 프로토콜인 경우 별도 처리
            if protocol == "onvif":
                self._test_onvif_connection(camera_info)
                return

            url = self._build_url(camera_info)
            self.test_result_label.configure(text="🔄 연결 테스트 중...", fg="#3498DB")
            self.dialog.update()

            def do_test():
                try:
                    cap = cv2.VideoCapture(url)
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)

                    if cap.isOpened():
                        ret, frame = cap.read()
                        cap.release()
                        if ret and frame is not None:
                            h, w = frame.shape[:2]
                            self.dialog.after(0, lambda: self.test_result_label.configure(
                                text=f"✅ 연결 성공! ({w}x{h})", fg="#27AE60"))
                        else:
                            self.dialog.after(0, lambda: self.test_result_label.configure(
                                text="❌ 프레임 읽기 실패", fg="#E74C3C"))
                    else:
                        cap.release()
                        self.dialog.after(0, lambda: self.test_result_label.configure(
                            text="❌ 연결 실패 - IP/포트/경로 확인", fg="#E74C3C"))
                except Exception as e:
                    self.dialog.after(0, lambda: self.test_result_label.configure(
                        text=f"❌ 오류: {str(e)[:30]}", fg="#E74C3C"))

            # 백그라운드에서 테스트 실행 (UI 블로킹 방지)
            thread = threading.Thread(target=do_test, daemon=True)
            thread.start()

        except Exception as e:
            self.test_result_label.configure(text=f"❌ 오류: {str(e)[:30]}", fg="#E74C3C")

    def _test_onvif_connection(self, camera_info):
        """ONVIF 연결 테스트"""
        import threading

        ip = camera_info.get("ip", "")
        port = camera_info.get("port", "80")
        username = camera_info.get("username", "")
        password = camera_info.get("password", "")

        self.test_result_label.configure(text="🔄 ONVIF 연결 테스트 중...", fg="#3498DB")
        self.dialog.update()

        def do_onvif_test():
            try:
                from onvif import ONVIFCamera

                # ONVIF 카메라 연결
                cam = ONVIFCamera(ip, int(port), username, password)

                # 디바이스 정보 가져오기
                device_service = cam.create_devicemgmt_service()
                device_info = device_service.GetDeviceInformation()

                # 미디어 서비스에서 스트림 URL 가져오기
                media_service = cam.create_media_service()
                profiles = media_service.GetProfiles()

                if profiles:
                    # 첫 번째 프로파일의 스트림 URI 가져오기
                    stream_setup = {
                        'Stream': 'RTP-Unicast',
                        'Transport': {'Protocol': 'RTSP'}
                    }
                    uri = media_service.GetStreamUri({
                        'StreamSetup': stream_setup,
                        'ProfileToken': profiles[0].token
                    })
                    stream_url = uri.Uri

                    # 스트림 URL을 경로 필드에 자동 입력
                    self.dialog.after(0, lambda: self._update_stream_url(stream_url))

                    manufacturer = getattr(device_info, 'Manufacturer', 'Unknown')
                    model = getattr(device_info, 'Model', 'Unknown')
                    self.dialog.after(0, lambda: self.test_result_label.configure(
                        text=f"✅ ONVIF 성공! {manufacturer} {model}", fg="#27AE60"))
                else:
                    self.dialog.after(0, lambda: self.test_result_label.configure(
                        text="❌ ONVIF 프로파일 없음", fg="#E74C3C"))

            except ImportError:
                self.dialog.after(0, lambda: self.test_result_label.configure(
                    text="❌ onvif-zeep 미설치", fg="#E74C3C"))
            except Exception as e:
                err_msg = str(e)
                if "401" in err_msg or "Unauthorized" in err_msg:
                    err_msg = "인증 실패 - 사용자명/비밀번호 확인"
                elif "timeout" in err_msg.lower():
                    err_msg = "연결 시간 초과"
                elif "Connection refused" in err_msg:
                    err_msg = "연결 거부 - IP/포트 확인"
                self.dialog.after(0, lambda: self.test_result_label.configure(
                    text=f"❌ {err_msg[:25]}", fg="#E74C3C"))

        thread = threading.Thread(target=do_onvif_test, daemon=True)
        thread.start()

    def _update_stream_url(self, stream_url):
        """ONVIF에서 가져온 스트림 URL로 업데이트"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(stream_url)

            # 프로토콜을 RTSP로 변경
            self.protocol_var.set("rtsp")

            # 포트 업데이트
            if parsed.port:
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, str(parsed.port))

            # 경로 업데이트
            if parsed.path:
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, parsed.path)

            # 힌트 업데이트
            self.path_hint.configure(text=f"ONVIF 자동 탐색: {parsed.path}")
        except Exception:
            pass

    def _test_ptz_connection(self):
        """PTZ 연결 테스트"""
        try:
            import threading

            # PTZ 활성화 확인
            if not self.ptz_var.get():
                self.test_result_label.configure(text="⚠️ PTZ 기능을 먼저 활성화하세요", fg="#F39C12")
                return

            camera_info = self._get_camera_info()
            ip = camera_info.get("ip", "")
            ptz_email = camera_info.get("ptz_email", "")
            ptz_password = camera_info.get("ptz_password", "")

            if not ip:
                self.test_result_label.configure(text="⚠️ IP 주소를 입력하세요", fg="#F39C12")
                return

            if not ptz_email or not ptz_password:
                self.test_result_label.configure(text="⚠️ Tapo 계정 정보를 입력하세요", fg="#F39C12")
                return

            self.test_result_label.configure(text="🔄 PTZ 연결 테스트 중...", fg="#9B59B6")
            self.dialog.update()

            def do_ptz_test():
                try:
                    from ..sensor.tapo_ptz import TapoPTZController, PYTAPO_AVAILABLE

                    if not PYTAPO_AVAILABLE:
                        self.dialog.after(0, lambda: self.test_result_label.configure(
                            text="❌ pytapo 라이브러리 없음 (pip install pytapo)", fg="#E74C3C"))
                        return

                    controller = TapoPTZController(ip, ptz_email, ptz_password)
                    if controller.connect():
                        ptz_status = "PTZ 지원" if controller.ptz_supported else "PTZ 미지원"
                        controller.disconnect()
                        self.dialog.after(0, lambda: self.test_result_label.configure(
                            text=f"✅ PTZ 연결 성공! ({ptz_status})", fg="#27AE60"))
                    else:
                        error_msg = controller.last_error
                        # 에러 메시지 상세화
                        if "Invalid authentication" in error_msg:
                            error_msg = "인증 실패 - Tapo 앱 계정 확인"
                        elif "timeout" in error_msg.lower():
                            error_msg = "연결 시간 초과"
                        elif "Connection refused" in error_msg:
                            error_msg = "연결 거부 - IP 확인"
                        self.dialog.after(0, lambda: self.test_result_label.configure(
                            text=f"❌ PTZ 실패: {error_msg[:25]}", fg="#E74C3C"))

                except ImportError:
                    self.dialog.after(0, lambda: self.test_result_label.configure(
                        text="❌ pytapo 라이브러리 없음", fg="#E74C3C"))
                except Exception as e:
                    err_str = str(e)
                    if "Invalid authentication" in err_str:
                        err_str = "인증 실패 - Tapo 앱 계정 확인"
                    self.dialog.after(0, lambda: self.test_result_label.configure(
                        text=f"❌ PTZ 오류: {err_str[:25]}", fg="#E74C3C"))

            # 백그라운드에서 테스트 실행
            thread = threading.Thread(target=do_ptz_test, daemon=True)
            thread.start()

        except Exception as e:
            self.test_result_label.configure(text=f"❌ 오류: {str(e)[:30]}", fg="#E74C3C")

    def _get_camera_info(self):
        """입력된 카메라 정보 반환"""
        info = {
            "name": self.name_entry.get().strip(),
            "protocol": self.protocol_var.get(),
            "ip": self.ip_entry.get().strip(),
            "port": self.port_entry.get().strip() or "554",
            "path": self.path_entry.get().strip() or "/stream1",
            "username": self.username_entry.get().strip(),
            "password": self.password_entry.get().strip(),
            "ptz_enabled": self.ptz_var.get()
        }

        # PTZ Tapo 계정 정보 추가 (PTZ 활성화된 경우)
        if hasattr(self, 'ptz_email_entry') and hasattr(self, 'ptz_password_entry'):
            info["ptz_email"] = self.ptz_email_entry.get().strip()
            info["ptz_password"] = self.ptz_password_entry.get().strip()

        return info

    def _build_url(self, camera_info):
        """카메라 정보로 URL 생성"""
        protocol = camera_info.get("protocol", "rtsp")
        ip = camera_info.get("ip", "")
        port = camera_info.get("port", "554")
        username = camera_info.get("username", "")
        password = camera_info.get("password", "")
        path = camera_info.get("path", "/stream1")

        if username and password:
            return f"{protocol}://{username}:{password}@{ip}:{port}{path}"
        else:
            return f"{protocol}://{ip}:{port}{path}"

    def _save(self):
        """저장"""
        camera_info = self._get_camera_info()

        if not camera_info.get("name"):
            messagebox.showwarning("입력 필요", "카메라 이름을 입력하세요.", parent=self.dialog)
            return

        if not camera_info.get("ip"):
            messagebox.showwarning("입력 필요", "IP 주소를 입력하세요.", parent=self.dialog)
            return

        self.result = camera_info
        self._close()

    def _close(self):
        """다이얼로그 닫기"""
        self.dialog.destroy()
