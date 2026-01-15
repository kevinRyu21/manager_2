"""
도면 관리자

도면 이미지 추가, 삭제, 순서 변경 기능을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import json

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class BlueprintManager:
    """도면 관리자"""

    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.blueprint_dir = os.path.join(os.getcwd(), "blueprints")
        self.blueprint_data_dir = os.path.join(os.getcwd(), "blueprint_data")
        self.blueprints = []  # [(filename, filepath), ...]
        self.listbox = None

    def show(self):
        """도면 관리 다이얼로그 표시"""
        # 디렉토리 생성
        os.makedirs(self.blueprint_dir, exist_ok=True)
        os.makedirs(self.blueprint_data_dir, exist_ok=True)

        # 다이얼로그 생성
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("도면 관리")
        self.dialog.geometry("800x730")  # 높이 추가 확장 (660 -> 730)
        self.dialog.configure(bg="#F5F5F5")
        self.dialog.resizable(False, False)

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (730 // 2)
        self.dialog.geometry(f"800x730+{x}+{y}")  # 높이 추가 확장 (660 -> 730)

        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 제목
        title_label = tk.Label(self.dialog, text="도면 관리",
                              font=("Pretendard", 18, "bold"), fg="#2C3E50", bg="#F5F5F5")
        title_label.pack(pady=20)

        # 안내 문구
        info_frame = tk.Frame(self.dialog, bg="#E8F4FD", relief="solid", bd=2)
        info_frame.pack(fill="x", padx=20, pady=(0, 10))

        info_text = tk.Label(info_frame,
                            text="• 파일 형식: PNG, JPG, JPEG\n"
                                 "• 여러 이미지를 동시에 업로드할 수 있습니다\n"
                                 "• 도면 삭제 시 해당 도면의 센서/모니터 위치 정보도 함께 삭제됩니다",
                            font=("Pretendard", 10), fg="#2C3E50", bg="#E8F4FD",
                            justify="left")
        info_text.pack(padx=10, pady=10)

        # 메인 프레임 (좌우 분할)
        main_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 왼쪽: 도면 목록
        left_frame = ttk.LabelFrame(main_frame, text="도면 목록", padding="10")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 리스트박스 + 스크롤바
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                  font=("Pretendard", 11), height=15)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # 오른쪽: 버튼들
        right_frame = tk.Frame(main_frame, bg="#F5F5F5")
        right_frame.pack(side="right", fill="y", padx=(10, 0))

        # 추가 버튼
        tk.Button(right_frame, text="➕ 도면 추가", command=self._add_blueprint,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(pady=5)

        # 삭제 버튼
        tk.Button(right_frame, text="🗑 선택 삭제", command=self._delete_blueprint,
                 bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#C0392B", activeforeground="#FFFFFF").pack(pady=5)

        # 구분선
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", pady=15)

        # 위로 버튼
        tk.Button(right_frame, text="▲ 위로", command=self._move_up,
                 bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#2980B9", activeforeground="#FFFFFF").pack(pady=5)

        # 아래로 버튼
        tk.Button(right_frame, text="▼ 아래로", command=self._move_down,
                 bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#2980B9", activeforeground="#FFFFFF").pack(pady=5)

        # 하단 버튼
        bottom_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        bottom_frame.pack(fill="x", padx=20, pady=20)

        # 폴더 열기 버튼
        tk.Button(bottom_frame, text="📁 폴더 열기", command=self._open_folder,
                 bg="#F39C12", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#E67E22", activeforeground="#FFFFFF").pack(side="left", padx=5)

        # 닫기 버튼
        tk.Button(bottom_frame, text="✓ 확인", command=self._close,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, width=15, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5)

        # 도면 목록 로드
        self._load_blueprints()

        # 다이얼로그가 닫힐 때까지 대기 (모달)
        self.dialog.wait_window()

    def _load_blueprints(self):
        """도면 목록 로드"""
        self.blueprints = []
        self.listbox.delete(0, tk.END)

        if not os.path.exists(self.blueprint_dir):
            return

        # 이미지 파일 찾기 및 번호 정렬
        files = []
        for filename in os.listdir(self.blueprint_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(self.blueprint_dir, filename)
                files.append((filename, filepath))

        # 파일명으로 정렬 (숫자 prefix가 있으면 숫자 순서대로)
        files.sort(key=lambda x: self._get_sort_key(x[0]))

        for filename, filepath in files:
            self.blueprints.append((filename, filepath))
            # 번호 제거하고 표시 (예: 01_floor1.png -> floor1.png)
            display_name = self._remove_number_prefix(filename)
            self.listbox.insert(tk.END, display_name)

    def _get_sort_key(self, filename):
        """정렬 키 생성 (숫자 prefix 고려)"""
        import re
        match = re.match(r'^(\d+)_', filename)
        if match:
            return int(match.group(1))
        return float('inf')  # 번호 없는 파일은 맨 뒤로

    def _remove_number_prefix(self, filename):
        """파일명에서 숫자 prefix 제거"""
        import re
        return re.sub(r'^\d+_', '', filename)

    def _add_blueprint(self):
        """도면 추가 (다중 선택 지원)"""
        filepaths = filedialog.askopenfilenames(
            title="도면 이미지 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg"),
                ("PNG 파일", "*.png"),
                ("JPEG 파일", "*.jpg *.jpeg"),
                ("모든 파일", "*.*")
            ],
            parent=self.dialog
        )

        if not filepaths:
            return

        added_count = 0
        for filepath in filepaths:
            try:
                # 파일명 추출
                filename = os.path.basename(filepath)

                # 중복 확인
                dest_path = os.path.join(self.blueprint_dir, filename)
                if os.path.exists(dest_path):
                    # 파일명에 번호 추가
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(self.blueprint_dir, f"{name}_{counter}{ext}")):
                        counter += 1
                    filename = f"{name}_{counter}{ext}"
                    dest_path = os.path.join(self.blueprint_dir, filename)

                # 파일 복사
                shutil.copy2(filepath, dest_path)
                added_count += 1

            except Exception as e:
                messagebox.showerror("오류",
                                   f"도면 추가 중 오류가 발생했습니다:\n{filepath}\n{str(e)}",
                                   parent=self.dialog)

        # 목록 새로고침
        self._load_blueprints()
        if added_count > 0:
            messagebox.showinfo("완료", f"{added_count}개의 도면이 추가되었습니다.", parent=self.dialog)

    def _delete_blueprint(self):
        """선택한 도면 삭제"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 도면을 선택하세요.", parent=self.dialog)
            return

        index = selection[0]
        filename, filepath = self.blueprints[index]

        if messagebox.askyesno("도면 삭제",
                              f"다음 도면을 삭제하시겠습니까?\n\n{filename}\n\n"
                              f"해당 도면의 센서/모니터 위치 정보도 함께 삭제됩니다.",
                              parent=self.dialog):
            try:
                # 이미지 파일 삭제
                os.remove(filepath)

                # 해당 도면의 데이터 파일도 삭제
                data_filename = os.path.splitext(filename)[0] + ".json"
                data_filepath = os.path.join(self.blueprint_data_dir, data_filename)
                if os.path.exists(data_filepath):
                    os.remove(data_filepath)

                self._load_blueprints()
                messagebox.showinfo("완료", "도면 및 관련 데이터가 삭제되었습니다.", parent=self.dialog)
            except Exception as e:
                messagebox.showerror("오류",
                                   f"도면 삭제 중 오류가 발생했습니다:\n{str(e)}",
                                   parent=self.dialog)

    def _move_up(self):
        """선택한 도면을 위로 이동"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "이동할 도면을 선택하세요.", parent=self.dialog)
            return

        index = selection[0]
        if index == 0:
            return  # 이미 맨 위

        try:
            # 두 항목의 위치 변경
            self.blueprints[index], self.blueprints[index - 1] = self.blueprints[index - 1], self.blueprints[index]

            # 파일명에 번호 prefix 추가하여 리네임
            self._renumber_all_blueprints()

            # 목록 새로고침
            self._load_blueprints()

            # 선택 유지
            self.listbox.selection_set(index - 1)

        except Exception as e:
            messagebox.showerror("오류",
                               f"순서 변경 중 오류가 발생했습니다:\n{str(e)}",
                               parent=self.dialog)

    def _move_down(self):
        """선택한 도면을 아래로 이동"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "이동할 도면을 선택하세요.", parent=self.dialog)
            return

        index = selection[0]
        if index == len(self.blueprints) - 1:
            return  # 이미 맨 아래

        try:
            # 두 항목의 위치 변경
            self.blueprints[index], self.blueprints[index + 1] = self.blueprints[index + 1], self.blueprints[index]

            # 파일명에 번호 prefix 추가하여 리네임
            self._renumber_all_blueprints()

            # 목록 새로고침
            self._load_blueprints()

            # 선택 유지
            self.listbox.selection_set(index + 1)

        except Exception as e:
            messagebox.showerror("오류",
                               f"순서 변경 중 오류가 발생했습니다:\n{str(e)}",
                               parent=self.dialog)

    def _renumber_all_blueprints(self):
        """모든 도면에 번호 prefix 추가/수정"""
        import re

        for i, (filename, filepath) in enumerate(self.blueprints):
            # 기존 번호 제거
            clean_name = re.sub(r'^\d+_', '', filename)

            # 새로운 번호 추가 (01_, 02_, ...)
            new_filename = f"{i+1:02d}_{clean_name}"
            new_filepath = os.path.join(self.blueprint_dir, new_filename)

            # 파일명이 다르면 리네임
            if filepath != new_filepath:
                os.rename(filepath, new_filepath)
                self.blueprints[i] = (new_filename, new_filepath)

                # 데이터 파일도 리네임
                old_data_filename = os.path.splitext(filename)[0] + ".json"
                new_data_filename = os.path.splitext(new_filename)[0] + ".json"
                old_data_path = os.path.join(self.blueprint_data_dir, old_data_filename)
                new_data_path = os.path.join(self.blueprint_data_dir, new_data_filename)
                if os.path.exists(old_data_path) and old_data_path != new_data_path:
                    os.rename(old_data_path, new_data_path)

    def _open_folder(self):
        """도면 폴더 열기"""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                os.startfile(self.blueprint_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.blueprint_dir])
            else:  # Linux
                subprocess.run(["xdg-open", self.blueprint_dir])
        except Exception as e:
            messagebox.showerror("오류",
                               f"폴더 열기 중 오류가 발생했습니다:\n{str(e)}",
                               parent=self.dialog)

    def _close(self):
        """다이얼로그 닫기"""
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
