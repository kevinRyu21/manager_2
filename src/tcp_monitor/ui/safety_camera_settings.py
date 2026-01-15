# -*- coding: utf-8 -*-
"""
안전교육 카메라 설정 다이얼로그

안전교육 시 카메라 사용 여부를 설정할 수 있습니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class SafetyCameraSettingsDialog:
    """안전교육 카메라 설정 다이얼로그"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config = config_manager
        self.dialog = None
        self.camera_checkbox = None
        
    def show(self):
        """설정 다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("카메라 설정")
        self.dialog.geometry("300x200")
        self.dialog.resizable(False, False)
        
        # 다이얼로그가 닫힐 때까지 대기
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_current_settings()
        
        # 중앙 정렬
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"300x200+{x}+{y}")
        
    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="카메라 설정", 
                                font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 카메라 사용 체크박스
        self.camera_var = tk.BooleanVar()
        self.camera_checkbox = tk.Checkbutton(
            main_frame, 
            text="안전교육 시 얼굴 촬영 활성화",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            variable=self.camera_var
        )
        self.camera_checkbox.pack(anchor="w", pady=(0, 20))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", side="bottom", pady=(20, 0))
        
        # 저장 버튼
        save_btn = ttk.Button(button_frame, text="저장", command=self._save_settings)
        save_btn.pack(side="right", padx=(10, 0))
        
        # 취소 버튼
        cancel_btn = ttk.Button(button_frame, text="취소", command=self._cancel)
        cancel_btn.pack(side="right")
        
    def _load_current_settings(self):
        """현재 설정 로드"""
        # config에서 카메라 설정 로드
        camera_enabled = self.config.env.get("safety_education_photo", True)
        self.camera_var.set(camera_enabled)
        
    def _save_settings(self):
        """설정 저장"""
        try:
            # 체크박스 상태 저장
            camera_enabled = self.camera_var.get()
            self.config.env["safety_education_photo"] = camera_enabled
            
            # 파일 저장
            self.config.save()
            
            status = "활성화" if camera_enabled else "비활성화"
            messagebox.showinfo("저장 완료", f"안전교육 카메라 설정이 '{status}'로 저장되었습니다.")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("저장 오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")
            
    def _cancel(self):
        """취소"""
        self.dialog.destroy()
