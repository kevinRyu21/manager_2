import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class AdminPasswordDialog:
    """관리자 암호 입력 다이얼로그 (숫자 패드)"""
    
    def __init__(self, parent, stored_password_hash=None):
        self.parent = parent
        self.stored_password_hash = stored_password_hash
        self.dialog = None
        self.password_var = tk.StringVar()
        self.password_var.set("")
        self.result = False
        
    def show(self):
        """다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("관리자 모드")
        # 원래 크기 유지
        base_height = 616
        self.dialog.geometry(f"400x{base_height}")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 중앙 정렬
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (base_height // 2)
        self.dialog.geometry(f"400x{base_height}+{x}+{y}")

        self._create_widgets()
        
        # 포커스 설정
        self.dialog.focus_set()
        
        # 대기
        self.parent.wait_window(self.dialog)
        return self.result
    
    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="관리자 모드", 
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 설명
        desc_label = ttk.Label(main_frame, text="관리자 암호를 입력하세요", 
                              font=("Arial", 12))
        desc_label.pack(pady=(0, 20))
        
        # 암호 표시 프레임
        password_frame = ttk.Frame(main_frame)
        password_frame.pack(fill="x", pady=(0, 20))
        
        # 암호 표시 라벨
        self.password_display = ttk.Label(password_frame, text="", 
                                          font=("Arial", 18, "bold"),
                                          foreground="#2C3E50",
                                          background="#ECF0F1",
                                          relief="sunken",
                                          anchor="center")
        self.password_display.pack(fill="x", ipady=10)
        
        # 암호 변경 감지
        self.password_var.trace('w', self._update_password_display)
        
        # 숫자 패드 프레임
        keypad_frame = ttk.Frame(main_frame)
        keypad_frame.pack(fill="both", expand=True)
        
        # 숫자 패드 그리드 설정
        keypad_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")
        keypad_frame.grid_rowconfigure((0, 1, 2, 3), weight=1, uniform="row")
        
        # 숫자 버튼들 (0-9)
        numbers = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["", "0", ""]
        ]
        
        for row, number_row in enumerate(numbers):
            for col, number in enumerate(number_row):
                if number:  # 빈 문자열이 아닌 경우만
                    btn = tk.Button(keypad_frame, text=number,
                                   font=("Arial", 16, "bold"),
                                   bg="#3498DB", fg="white",
                                   relief="raised", bd=3,
                                   command=lambda n=number: self._add_digit(n))
                    btn.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 20))
        
        # 지우기 버튼
        clear_btn = tk.Button(button_frame, text="지우기",
                             font=("Arial", 12, "bold"),
                             bg="#E74C3C", fg="white",
                             relief="raised", bd=2,
                             command=self._clear_password)
        clear_btn.pack(side="left", padx=(0, 10))
        
        # 확인 버튼
        confirm_btn = tk.Button(button_frame, text="확인",
                               font=("Arial", 12, "bold"),
                               bg="#27AE60", fg="white",
                               relief="raised", bd=2, height=2,
                               command=self._verify_password)
        confirm_btn.pack(side="right", padx=(10, 0))
        
        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="취소",
                               font=("Arial", 12, "bold"),
                               bg="#95A5A6", fg="white",
                               relief="raised", bd=2,
                               command=self._cancel)
        cancel_btn.pack(side="right")
        
        # 키보드 이벤트 바인딩
        self.dialog.bind("<Key>", self._on_key_press)
        
    def _add_digit(self, digit):
        """숫자 추가"""
        current = self.password_var.get()
        if len(current) < 10:  # 최대 10자리
            self.password_var.set(current + digit)
            self._animate_button_press(digit)
    
    def _clear_password(self):
        """암호 지우기"""
        self.password_var.set("")
        self._animate_button_press("clear")
    
    def _update_password_display(self, *args):
        """암호 표시 업데이트"""
        password = self.password_var.get()
        # 암호를 *로 표시
        display = "*" * len(password)
        self.password_display.configure(text=display)
    
    def _verify_password(self):
        """암호 검증"""
        entered_password = self.password_var.get()
        
        # 해시값으로 검증
        try:
            from ..utils.password_hasher import PasswordHasher
            if PasswordHasher.verify_password(entered_password, self.stored_password_hash):
                self.result = True
                self._show_success_animation()
                self.dialog.after(500, self.dialog.destroy)  # 0.5초 후 닫기
            else:
                self._show_error_animation()
                self.password_var.set("")  # 암호 초기화
        except Exception as e:
            print(f"비밀번호 검증 오류: {e}")
            self._show_error_animation()
            self.password_var.set("")  # 암호 초기화
    
    def _cancel(self):
        """취소"""
        self.result = False
        self.dialog.destroy()
    
    def _on_key_press(self, event):
        """키보드 입력 처리"""
        if event.char.isdigit():
            self._add_digit(event.char)
        elif event.keysym == "BackSpace":
            self._clear_password()
        elif event.keysym == "Return":
            self._verify_password()
        elif event.keysym == "Escape":
            self._cancel()
    
    def _animate_button_press(self, button_type):
        """버튼 클릭 애니메이션"""
        def animate():
            # 간단한 시각적 피드백
            pass
        
        # 별도 스레드에서 애니메이션 실행
        threading.Thread(target=animate, daemon=True).start()
    
    def _show_success_animation(self):
        """성공 애니메이션"""
        self.password_display.configure(foreground="#27AE60")
        self.dialog.configure(bg="#D5F4E6")
    
    def _show_error_animation(self):
        """오류 애니메이션"""
        self.password_display.configure(foreground="#E74C3C")
        self.dialog.configure(bg="#FADBD8")
        
        # 오류 메시지 표시
        messagebox.showerror("인증 실패", "입력하신 관리자 비밀번호가 틀렸습니다.\n\n다시 입력해주세요.", parent=self.dialog)
        
        # 1초 후 원래 색상으로 복원
        def restore_colors():
            time.sleep(1)
            self.password_display.configure(foreground="#2C3E50")
            self.dialog.configure(bg="#FFFFFF")
        
        threading.Thread(target=restore_colors, daemon=True).start()
