import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class AdminPasswordChangeDialog:
    """관리자 비밀번호 변경 다이얼로그 (숫자 패드)"""
    
    def __init__(self, parent, current_password_hash):
        self.parent = parent
        self.current_password_hash = current_password_hash
        self.dialog = None
        self.current_password_var = tk.StringVar()
        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.current_password_var.set("")
        self.new_password_var.set("")
        self.confirm_password_var.set("")
        self.result = False
        self.new_password = None
        
    def show(self):
        """다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("관리자 비밀번호 변경")
        self.dialog.geometry("700x990")  # 높이 10% 확장 (900 -> 990)
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 중앙 정렬
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (990 // 2)
        self.dialog.geometry(f"700x990+{x}+{y}")  # 높이 10% 확장 (900 -> 990)
        
        self._create_widgets()
        
        # 포커스 설정
        self.dialog.focus_set()
        
        # 대기
        self.parent.wait_window(self.dialog)
        return self.result, self.new_password
    
    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="관리자 비밀번호 변경", 
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 상단 버튼 프레임 (저장/취소)
        top_button_frame = ttk.Frame(main_frame)
        top_button_frame.pack(fill="x", pady=(0, 20))
        
        # 저장 버튼 (상단)
        save_btn_top = tk.Button(top_button_frame, text="저장",
                                font=("Arial", 16, "bold"),
                                bg="#27AE60", fg="white",
                                relief="raised", bd=3,
                                width=10, height=2,
                                command=self._change_password)
        save_btn_top.pack(side="right", padx=(10, 0))
        
        # 취소 버튼 (상단)
        cancel_btn_top = tk.Button(top_button_frame, text="취소",
                                   font=("Arial", 16, "bold"),
                                   bg="#95A5A6", fg="white",
                                   relief="raised", bd=3,
                                   width=10, height=2,
                                   command=self._cancel)
        cancel_btn_top.pack(side="right", padx=(10, 0))
        
        
        # 현재 비밀번호 프레임
        current_frame = ttk.LabelFrame(main_frame, text="현재 비밀번호", padding=10)
        current_frame.pack(fill="x", pady=(0, 15))
        
        current_label = ttk.Label(current_frame, text="현재 비밀번호를 입력하세요", 
                                 font=("Arial", 12))
        current_label.pack(pady=(0, 10))
        
        self.current_password_display = ttk.Label(current_frame, text="", 
                                                 font=("Arial", 18, "bold"),
                                                 foreground="#2C3E50",
                                                 background="#ECF0F1",
                                                 relief="sunken",
                                                 anchor="center")
        self.current_password_display.pack(fill="x", ipady=10)
        
        # 마우스 클릭 이벤트 바인딩
        self.current_password_display.bind("<Button-1>", lambda e: self._select_field("current"))
        
        # 새 비밀번호 프레임
        new_frame = ttk.LabelFrame(main_frame, text="새 비밀번호", padding=10)
        new_frame.pack(fill="x", pady=(0, 15))
        
        new_label = ttk.Label(new_frame, text="새 비밀번호를 입력하세요 (6자리 이상 10자리 이하)", 
                              font=("Arial", 12))
        new_label.pack(pady=(0, 10))
        
        self.new_password_display = ttk.Label(new_frame, text="", 
                                             font=("Arial", 18, "bold"),
                                             foreground="#2C3E50",
                                             background="#ECF0F1",
                                             relief="sunken",
                                             anchor="center")
        self.new_password_display.pack(fill="x", ipady=10)
        
        # 마우스 클릭 이벤트 바인딩
        self.new_password_display.bind("<Button-1>", lambda e: self._select_field("new"))
        
        # 비밀번호 확인 프레임
        confirm_frame = ttk.LabelFrame(main_frame, text="비밀번호 확인", padding=10)
        confirm_frame.pack(fill="x", pady=(0, 20))
        
        confirm_label = ttk.Label(confirm_frame, text="새 비밀번호를 다시 입력하세요", 
                                  font=("Arial", 12))
        confirm_label.pack(pady=(0, 10))
        
        self.confirm_password_display = ttk.Label(confirm_frame, text="", 
                                                 font=("Arial", 18, "bold"),
                                                 foreground="#2C3E50",
                                                 background="#ECF0F1",
                                                 relief="sunken",
                                                 anchor="center")
        self.confirm_password_display.pack(fill="x", ipady=10)
        
        # 마우스 클릭 이벤트 바인딩
        self.confirm_password_display.bind("<Button-1>", lambda e: self._select_field("confirm"))
        
        # 비밀번호 변경 감지
        self.current_password_var.trace('w', lambda *args: self._update_password_display("current"))
        self.new_password_var.trace('w', lambda *args: self._update_password_display("new"))
        self.confirm_password_var.trace('w', lambda *args: self._update_password_display("confirm"))
        
        # 숫자 패드 프레임
        keypad_frame = ttk.Frame(main_frame)
        keypad_frame.pack(fill="both", expand=True)
        
        # 숫자 패드 그리드 설정
        keypad_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")
        keypad_frame.grid_rowconfigure((0, 1, 2, 3), weight=1, uniform="row")
        
        # 숫자 버튼들 (1-9)
        numbers = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"]
        ]
        
        for row, number_row in enumerate(numbers):
            for col, number in enumerate(number_row):
                btn = tk.Button(keypad_frame, text=number,
                               font=("Arial", 24, "bold"),
                               bg="#3498DB", fg="white",
                               relief="raised", bd=3,
                               command=lambda n=number: self._add_digit(n))
                btn.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
        
        # 하단 버튼들 (지우기, 0, 다음칸)
        # 지우기 버튼
        clear_btn = tk.Button(keypad_frame, text="지우기",
                             font=("Arial", 18, "bold"),
                             bg="#E74C3C", fg="white",
                             relief="raised", bd=3,
                             command=self._clear_current_password)
        clear_btn.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        
        # 0 버튼
        zero_btn = tk.Button(keypad_frame, text="0",
                            font=("Arial", 24, "bold"),
                            bg="#3498DB", fg="white",
                            relief="raised", bd=3,
                            command=lambda: self._add_digit("0"))
        zero_btn.grid(row=3, column=1, sticky="nsew", padx=10, pady=10)
        
        # 다음 칸 이동 버튼
        next_btn = tk.Button(keypad_frame, text="다음칸",
                            font=("Arial", 18, "bold"),
                            bg="#27AE60", fg="white",
                            relief="raised", bd=3,
                            command=self._move_to_next_field)
        next_btn.grid(row=3, column=2, sticky="nsew", padx=10, pady=10)
        
        
        # 키보드 이벤트 바인딩
        self.dialog.bind("<Key>", self._on_key_press)
        
        # 현재 입력 필드 추적
        self.current_input_field = "current"
        
        # 초기 하이라이트 설정
        self._update_field_highlight()
    
    def _add_digit(self, digit):
        """숫자 추가"""
        if self.current_input_field == "current":
            current = self.current_password_var.get()
            if len(current) < 10:  # 최대 10자리
                self.current_password_var.set(current + digit)
        elif self.current_input_field == "new":
            current = self.new_password_var.get()
            if len(current) < 10:  # 최대 10자리
                self.new_password_var.set(current + digit)
        elif self.current_input_field == "confirm":
            current = self.confirm_password_var.get()
            if len(current) < 10:  # 최대 10자리
                self.confirm_password_var.set(current + digit)
        
        # 하이라이트 업데이트
        self._update_field_highlight()
    
    def _clear_current_password(self):
        """현재 입력 필드 지우기"""
        if self.current_input_field == "current":
            self.current_password_var.set("")
        elif self.current_input_field == "new":
            self.new_password_var.set("")
        elif self.current_input_field == "confirm":
            self.confirm_password_var.set("")
    
    def _update_password_display(self, field_type):
        """비밀번호 표시 업데이트"""
        if field_type == "current":
            password = self.current_password_var.get()
            display = "*" * len(password)
            self.current_password_display.configure(text=display, foreground="black")
            
            # 자동 필드 이동 기능 제거 - 사용자가 수동으로 이동해야 함
        elif field_type == "new":
            password = self.new_password_var.get()
            display = "*" * len(password)
            self.new_password_display.configure(text=display, foreground="black")
            
            # 자동 필드 이동 기능 제거 - 사용자가 수동으로 이동해야 함
        elif field_type == "confirm":
            password = self.confirm_password_var.get()
            display = "*" * len(password)
            self.confirm_password_display.configure(text=display, foreground="black")
    
    def _update_field_highlight(self):
        """현재 입력 필드 하이라이트 업데이트"""
        # 모든 필드의 배경색을 기본값으로 설정
        self.current_password_display.configure(background="#ECF0F1")
        self.new_password_display.configure(background="#ECF0F1")
        self.confirm_password_display.configure(background="#ECF0F1")
        
        # 현재 입력 필드만 하이라이트 (별표는 검정색 유지)
        if self.current_input_field == "current":
            self.current_password_display.configure(background="#3498DB")
            # 별표는 검정색으로 유지
            current_text = self.current_password_display.cget("text")
            if current_text:
                self.current_password_display.configure(foreground="black")
        elif self.current_input_field == "new":
            self.new_password_display.configure(background="#3498DB")
            # 별표는 검정색으로 유지
            new_text = self.new_password_display.cget("text")
            if new_text:
                self.new_password_display.configure(foreground="black")
        elif self.current_input_field == "confirm":
            self.confirm_password_display.configure(background="#3498DB")
            # 별표는 검정색으로 유지
            confirm_text = self.confirm_password_display.cget("text")
            if confirm_text:
                self.confirm_password_display.configure(foreground="black")
    
    def _select_field(self, field_type):
        """마우스 클릭으로 입력 필드 선택"""
        self.current_input_field = field_type
        self._update_field_highlight()
    
    def _move_to_next_field(self):
        """다음 입력 필드로 이동"""
        if self.current_input_field == "current":
            self.current_input_field = "new"
        elif self.current_input_field == "new":
            self.current_input_field = "confirm"
        else:
            self.current_input_field = "current"
        
        self._update_field_highlight()
    
    def _change_password(self):
        """비밀번호 변경"""
        current_password = self.current_password_var.get()
        new_password = self.new_password_var.get()
        confirm_password = self.confirm_password_var.get()
        
        # 현재 비밀번호 확인 (해시 검증)
        try:
            from ..utils.password_hasher import PasswordHasher
            if not PasswordHasher.verify_password(current_password, self.current_password_hash):
                self._show_error_animation("현재 비밀번호가 올바르지 않습니다.")
                return
        except Exception as e:
            self._show_error_animation(f"비밀번호 검증 중 오류: {str(e)}")
            return
        
        # 새 비밀번호 길이 확인
        if len(new_password) < 6 or len(new_password) > 10:
            self._show_error_animation("새 비밀번호는 6자리 이상 10자리 이하여야 합니다.")
            return
        
        # 비밀번호 확인
        if new_password != confirm_password:
            self._show_error_animation("새 비밀번호가 일치하지 않습니다.")
            return
        
        # 현재 비밀번호와 동일한지 확인 (해시 검증)
        try:
            from ..utils.password_hasher import PasswordHasher
            if PasswordHasher.verify_password(new_password, self.current_password_hash):
                self._show_error_animation("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
                return
        except Exception as e:
            self._show_error_animation(f"비밀번호 검증 중 오류: {str(e)}")
            return
        
        # 비밀번호 변경 성공
        self.result = True
        self.new_password = new_password
        self._show_success_animation()
        self.dialog.after(1000, self.dialog.destroy)  # 1초 후 닫기
    
    def _cancel(self):
        """취소"""
        self.result = False
        self.dialog.destroy()
    
    def _on_key_press(self, event):
        """키보드 입력 처리"""
        if event.char.isdigit():
            self._add_digit(event.char)
        elif event.keysym == "BackSpace":
            self._clear_current_password()
        elif event.keysym == "Return":
            self._change_password()
        elif event.keysym == "Escape":
            self._cancel()
        elif event.keysym == "Tab":
            # Tab 키로 입력 필드 전환
            if self.current_input_field == "current":
                self.current_input_field = "new"
            elif self.current_input_field == "new":
                self.current_input_field = "confirm"
            else:
                self.current_input_field = "current"
            
            # 하이라이트 업데이트
            self._update_field_highlight()
    
    def _show_success_animation(self):
        """성공 애니메이션"""
        self.dialog.configure(bg="#D5F4E6")
        messagebox.showinfo("성공", "비밀번호가 성공적으로 변경되었습니다.", parent=self.dialog)
    
    def _show_error_animation(self, message):
        """오류 애니메이션"""
        self.dialog.configure(bg="#FADBD8")
        messagebox.showerror("오류", message, parent=self.dialog)
        
        # 1초 후 원래 색상으로 복원
        def restore_colors():
            time.sleep(1)
            self.dialog.configure(bg="#FFFFFF")
        
        threading.Thread(target=restore_colors, daemon=True).start()
