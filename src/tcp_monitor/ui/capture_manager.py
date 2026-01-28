"""
캡쳐 파일 관리 뷰어

captures 디렉토리에 저장된 화면 캡쳐 이미지를 보여주고, 폴더 열기/삭제/새로고침을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import platform
import subprocess

from ..utils.helpers import get_base_dir

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class CaptureManager:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.tree = None
        self.preview = None
        self.img_ref = None
        # 프로그램 설치 디렉토리 기준으로 경로 설정
        install_dir = get_base_dir()
        self.capture_dir = os.path.join(install_dir, "captures")

    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("캡쳐 파일 관리")
        # 안전교육 사진 관리와 동일: 전체화면 + 최상단
        self.dialog.attributes("-fullscreen", True)
        self.dialog.attributes("-topmost", True)
        self.dialog.configure(bg="#2C3E50")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Top bar
        top = tk.Frame(self.dialog, bg="#34495E")
        top.pack(side="top", fill="x")

        tk.Label(top, text="캡쳐 파일 관리", font=("Pretendard", 18, "bold"),
                 bg="#34495E", fg="#FFFFFF").pack(side="left", padx=12, pady=12)

        # 상단 우측 버튼: 닫기(빨간색), 파일로 저장(초록색) - 새로고침 제거
        tk.Button(top, text="✕ 닫기", command=self._close,
                  bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                  relief="raised", bd=2, width=12, height=1,
                  activebackground="#C0392B", activeforeground="#FFFFFF").pack(side="right", padx=8, pady=10)
        tk.Button(top, text="💾 파일로 저장", command=self._save_to_file,
                  bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                  relief="raised", bd=2, width=14, height=1,
                  activebackground="#229954", activeforeground="#FFFFFF").pack(side="right", padx=8, pady=10)

        # Body split (3:1 비율)
        body = tk.Frame(self.dialog, bg="#2C3E50")
        body.pack(fill="both", expand=True)
        # 고정 비율 3:7
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=7)
        body.grid_rowconfigure(0, weight=1)

        # Left list
        left = tk.Frame(body, bg="#2C3E50")
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # 검색/필터 (기간, 파일명)
        filter_bar = tk.Frame(top, bg="#34495E")
        filter_bar.pack(side="left", padx=18)
        tk.Label(filter_bar, text="기간:", font=("Pretendard", 11), bg="#34495E", fg="#ECF0F1").pack(side="left", padx=4)
        self.date_from = tk.Entry(filter_bar, width=10)
        self.date_from.insert(0, "YYYYMMDD")
        self.date_from.pack(side="left")
        tk.Label(filter_bar, text="~", font=("Pretendard", 11, "bold"), bg="#34495E", fg="#ECF0F1").pack(side="left", padx=3)
        self.date_to = tk.Entry(filter_bar, width=10)
        self.date_to.insert(0, "YYYYMMDD")
        self.date_to.pack(side="left")
        tk.Label(filter_bar, text="파일명:", font=("Pretendard", 11), bg="#34495E", fg="#ECF0F1").pack(side="left", padx=6)
        self.name_query = tk.Entry(filter_bar, width=12)
        self.name_query.pack(side="left")
        tk.Button(filter_bar, text="🔍 검색", command=self._search,
                  bg="#2980B9", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                  relief="raised", bd=2, width=8, height=1).pack(side="left", padx=6)
        tk.Button(filter_bar, text="전체", command=self._refresh,
                  bg="#7F8C8D", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                  relief="raised", bd=2, width=6, height=1).pack(side="left")

        # 순번/선택/파일명/크기(KB) 그리드 구성
        cols = ("순번", "선택", "파일명", "크기(KB)")
        self.tree = ttk.Treeview(left, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            if c == "파일명":
                self.tree.column(c, width=420, anchor='w')
            elif c == "선택":
                self.tree.column(c, width=80, anchor='center')
            elif c == "순번":
                self.tree.column(c, width=80, anchor='center')
            else:
                self.tree.column(c, width=120, anchor='center')
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-1>", self._on_click_toggle_select)

        # 하단 선택 제어 버튼들
        bottom = tk.Frame(self.dialog, bg="#2C3E50")
        bottom.pack(side="bottom", fill="x", padx=20, pady=10)
        tk.Button(bottom, text="전체선택", command=self._select_all,
                  bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                  relief="raised", bd=2, width=14, height=2).pack(side="left", padx=6)
        tk.Button(bottom, text="선택해제", command=self._clear_selection,
                  bg="#7F8C8D", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                  relief="raised", bd=2, width=14, height=2).pack(side="left", padx=6)
        tk.Button(bottom, text="선택 삭제", command=self._delete_selected,
                  bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                  relief="raised", bd=2, width=14, height=2).pack(side="left", padx=6)

        # Right preview (고정 캔버스 크기로 이미지에 따라 레이아웃 변하지 않도록)
        right = tk.Frame(body, bg="#2C3E50", relief="sunken", bd=1)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.preview_w = 1000  # 3:7 비율 고려, 전체 화면에서 넉넉한 기본값
        self.preview_h = 700
        self.preview = tk.Canvas(right, width=self.preview_w, height=self.preview_h,
                                 bg="#2C3E50", highlightthickness=0)
        self.preview.pack(anchor="center")

        self._selected_paths = set()
        self._ensure_dir()
        self._refresh()

    def _close(self):
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None

    def _ensure_dir(self):
        try:
            os.makedirs(self.capture_dir, exist_ok=True)
        except Exception:
            pass

    def _list_files(self, q_from=None, q_to=None, name_q=None):
        items = []
        try:
            for name in os.listdir(self.capture_dir):
                if not name.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue
                path = os.path.join(self.capture_dir, name)
                try:
                    size_kb = max(1, int(os.path.getsize(path) / 1024))
                except Exception:
                    size_kb = 0
                # 간단한 필터: 파일명에 날짜가 포함되어 있으면 YYYYMMDD 기준
                # capture_<id>_YYYYMMDD_HHMMSS.png 형태를 가정
                if q_from or q_to or name_q:
                    if name_q and name_q not in name:
                        continue
                    date_key = None
                    try:
                        base = os.path.splitext(name)[0]
                        parts = base.split("_")
                        if len(parts) >= 3:
                            date_key = parts[-2]
                    except Exception:
                        date_key = None
                    if q_from and date_key and date_key < q_from:
                        continue
                    if q_to and date_key and date_key > q_to:
                        continue
                items.append((name, size_kb, path))
        except Exception:
            pass
        items.sort(key=lambda x: x[0], reverse=True)
        return items

    def _refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        seq = 1
        for name, size_kb, path in self._list_files():
            checked = "✓" if path in self._selected_paths else ""
            self.tree.insert('', 'end', values=(seq, checked, name, size_kb), tags=(path,))
            seq += 1
        self.preview.delete("all")
        self.img_ref = None
        self.preview.create_text(self.preview_w//2, self.preview_h//2,
                                 text="미리보기",
                                 fill="#ECF0F1", font=("Pretendard", 16, "bold"))

    def _search(self):
        q_from = self.date_from.get().strip() or None
        q_to = self.date_to.get().strip() or None
        name_q = self.name_query.get().strip() or None
        for i in self.tree.get_children():
            self.tree.delete(i)
        seq = 1
        for name, size_kb, path in self._list_files(q_from, q_to, name_q):
            checked = "✓" if path in self._selected_paths else ""
            self.tree.insert('', 'end', values=(seq, checked, name, size_kb), tags=(path,))
            seq += 1
        self.preview.delete("all")
        self.img_ref = None
        self.preview.create_text(self.preview_w//2, self.preview_h//2,
                                 text="미리보기",
                                 fill="#ECF0F1", font=("Pretendard", 16, "bold"))

    def _on_select(self, event):
        try:
            sel = self.tree.selection()
            if not sel:
                return
            item = sel[0]
            path = self.tree.item(item, 'tags')[0]
            if PIL_OK:
                from PIL import Image
                im = Image.open(path)
                im.load()  # 이미지 로드 강제 (손상 검사)
                w = self.preview_w
                h = self.preview_h
                im.thumbnail((w-20, h-20))
                # master 지정하여 이미지 생성
                self.img_ref = ImageTk.PhotoImage(im, master=self.preview)
                self.preview.delete("all")
                # 중앙 배치
                cx = w//2
                cy = h//2
                self.preview.create_image(cx, cy, image=self.img_ref)
            else:
                self.preview.delete("all")
                self.preview.create_text(self.preview_w//2, self.preview_h//2,
                                         text=path, fill="#ECF0F1")
        except Exception as e:
            # Canvas는 text 옵션이 없음 - create_text 사용
            self.preview.delete("all")
            self.preview.create_text(self.preview_w//2, self.preview_h//2,
                                     text=f"미리보기 실패:\n{e}",
                                     fill="#E74C3C", font=("Pretendard", 12))

    def _open_folder(self):
        try:
            # 플랫폼별 시스템 유틸리티 사용
            from ...platform import SystemUtils
            system_utils = SystemUtils()
            system_utils.open_file(self.capture_dir)
        except Exception as e:
            messagebox.showerror("오류", f"폴더 열기 실패:\n{e}", parent=self.dialog)

    def _delete_selected(self):
        targets = list(self._selected_paths)
        if not targets:
            messagebox.showinfo("삭제", "삭제할 파일을 선택하세요.", parent=self.dialog)
            return
        if not messagebox.askyesno("삭제", f"선택한 {len(targets)}개 파일을 삭제하시겠습니까?", parent=self.dialog):
            return
        for path in targets:
            try:
                os.remove(path)
            except Exception:
                pass
        self._selected_paths.clear()
        self._refresh()

    def _save_to_file(self):
        # 선택 파일 CSV/XLSX 매니페스트 생성 후 ZIP 저장 (안전교육 사진 관리와 유사)
        if not self._selected_paths:
            messagebox.showinfo("저장", "저장할 캡쳐 파일을 선택하세요.", parent=self.dialog)
            return
        paths = list(self._selected_paths)
        try:
            import zipfile
            import csv
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            initial = os.path.join(self.capture_dir, f"captures_{ts}.zip")
            filename = filedialog.asksaveasfilename(parent=self.dialog, title="ZIP 파일 저장",
                                                    defaultextension=".zip",
                                                    initialfile=os.path.basename(initial),
                                                    filetypes=[("ZIP 파일", "*.zip"), ("모든 파일", "*.*")])
            if not filename:
                return
            with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # CSV 매니페스트 생성
                manifest_csv = os.path.join(self.capture_dir, f"captures_manifest_{ts}.csv")
                try:
                    with open(manifest_csv, 'w', newline='', encoding='utf-8-sig') as f:
                        w = csv.writer(f)
                        w.writerow(["filename", "size_kb"]) 
                        for p in paths:
                            w.writerow([os.path.basename(p), max(1, int(os.path.getsize(p)/1024))])
                    zipf.write(manifest_csv, os.path.basename(manifest_csv))
                finally:
                    try:
                        os.remove(manifest_csv)
                    except Exception:
                        pass

                # 가능하면 XLSX 매니페스트 생성
                try:
                    import pandas as pd
                    df = pd.DataFrame({
                        'filename': [os.path.basename(p) for p in paths],
                        'size_kb': [max(1, int(os.path.getsize(p)/1024)) for p in paths],
                    })
                    manifest_xlsx = os.path.join(self.capture_dir, f"captures_manifest_{ts}.xlsx")
                    df.to_excel(manifest_xlsx, index=False)
                    zipf.write(manifest_xlsx, os.path.basename(manifest_xlsx))
                    try:
                        os.remove(manifest_xlsx)
                    except Exception:
                        pass
                except Exception:
                    # pandas나 openpyxl 없으면 XLSX 생략
                    pass

                # 이미지 파일 추가
                for p in paths:
                    zipf.write(p, os.path.basename(p))
            messagebox.showinfo("저장 완료", f"ZIP 파일이 저장되었습니다.\n\n경로: {filename}", parent=self.dialog)
        except Exception as e:
            messagebox.showerror("오류", f"ZIP 저장 중 오류가 발생했습니다:\n{e}", parent=self.dialog)

    # ---- 선택 토글/전체선택/해제 ----
    def _on_click_toggle_select(self, event):
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            col = self.tree.identify_column(event.x)
            if col != "#2":  # 두 번째 열(선택)만 토글 (첫 번째는 순번)
                return
            row = self.tree.identify_row(event.y)
            if not row:
                return
            path = self.tree.item(row, 'tags')[0]
            if path in self._selected_paths:
                self._selected_paths.discard(path)
                self.tree.set(row, column="선택", value="")
            else:
                self._selected_paths.add(path)
                self.tree.set(row, column="선택", value="✓")
        except Exception:
            pass

    def _select_all(self):
        try:
            for iid in self.tree.get_children():
                path = self.tree.item(iid, 'tags')[0]
                self._selected_paths.add(path)
                self.tree.set(iid, column="선택", value="✓")
        except Exception:
            pass

    def _clear_selection(self):
        try:
            self._selected_paths.clear()
            for iid in self.tree.get_children():
                self.tree.set(iid, column="선택", value="")
        except Exception:
            pass


