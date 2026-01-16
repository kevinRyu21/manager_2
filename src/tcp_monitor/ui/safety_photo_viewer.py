"""
안전 교육 사진 뷰어

촬영된 안전 교육 사진을 날짜/시간과 함께 표시합니다.
"""

import tkinter as tk
from tkinter import ttk
import os
import datetime
import re

from ..utils.helpers import get_base_dir, get_data_dir

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class SafetyPhotoViewer:
    """안전 교육 사진 뷰어"""

    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.photos = []  # [(filepath, datetime_obj, name), ...]
        self.all_photos = []  # 전체 사진 목록 (필터링 전)
        self.current_index = 0
        self.photo_canvas = None  # Canvas로 변경
        self.info_label = None
        self.listbox = None
        self.image_cache = {}  # 이미지 캐시 (filepath: PhotoImage)

        # 컬럼 리사이즈 관련 변수
        self.resizing = False
        self.resize_column = None
        self.start_x = 0
        self.start_width = 0
        self.col_widths = None  # 컬럼 너비 (그리드 생성 시 초기화)

        # 선택된 항목 추적
        self.selected_items = set()
        self.checkbox_vars = []
        self.grid_items = []

    def show(self):
        """사진 뷰어 다이얼로그 표시"""
        # 사진 목록 로드
        self._load_photos()

        if not self.photos:
            from tkinter import messagebox
            messagebox.showinfo("안전 교육 사진",
                              "촬영된 안전 교육 사진이 없습니다.\n\n"
                              "안전 교육을 완료하고 사진을 촬영하세요.",
                              parent=self.parent)
            return

        # 전체 사진 목록 저장
        self.all_photos = self.photos.copy()

        # 다이얼로그 생성
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("안전 교육 사진 관리")
        self.dialog.attributes("-fullscreen", True)
        self.dialog.attributes("-topmost", True)
        self.dialog.configure(bg="#2C3E50")

        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # ESC로 닫기
        self.dialog.bind("<Escape>", lambda e: self._close())

        # 상단: 제목 및 검색
        top_frame = tk.Frame(self.dialog, bg="#34495E", relief="raised", bd=3)
        top_frame.pack(side="top", fill="x", padx=20, pady=20)

        title_label = tk.Label(top_frame, text="안전 교육 사진 관리",
                              font=("Pretendard", 24, "bold"), bg="#34495E", fg="#FFFFFF")
        title_label.pack(side="left", padx=20, pady=15)

        # 검색 영역
        search_frame = tk.Frame(top_frame, bg="#34495E")
        search_frame.pack(side="left", padx=40, pady=15)

        # 기간 검색
        period_frame = tk.Frame(search_frame, bg="#34495E")
        period_frame.pack(side="left", padx=10)

        tk.Label(period_frame, text="기간:",
                font=("Pretendard", 13), bg="#34495E", fg="#FFFFFF").pack(side="left", padx=5)

        self.date_from_entry = tk.Entry(period_frame, font=("Pretendard", 12), width=10)
        self.date_from_entry.pack(side="left", padx=3)
        self.date_from_entry.insert(0, "YYYYMMDD")
        self.date_from_entry.bind("<FocusIn>", lambda e: self._on_entry_focus(self.date_from_entry, "YYYYMMDD"))

        tk.Label(period_frame, text="~",
                font=("Pretendard", 13, "bold"), bg="#34495E", fg="#FFFFFF").pack(side="left", padx=3)

        self.date_to_entry = tk.Entry(period_frame, font=("Pretendard", 12), width=10)
        self.date_to_entry.pack(side="left", padx=3)
        self.date_to_entry.insert(0, "YYYYMMDD")
        self.date_to_entry.bind("<FocusIn>", lambda e: self._on_entry_focus(self.date_to_entry, "YYYYMMDD"))

        # 이름 검색
        name_frame = tk.Frame(search_frame, bg="#34495E")
        name_frame.pack(side="left", padx=10)

        tk.Label(name_frame, text="이름:",
                font=("Pretendard", 13), bg="#34495E", fg="#FFFFFF").pack(side="left", padx=5)

        self.name_entry = tk.Entry(name_frame, font=("Pretendard", 12), width=10)
        self.name_entry.pack(side="left", padx=3)

        # 검색 버튼
        tk.Button(search_frame, text="🔍 검색", command=self._search,
                 bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=2, width=8, height=1,
                 activebackground="#2980B9", activeforeground="#FFFFFF").pack(side="left", padx=8)

        # 전체 보기 버튼
        tk.Button(search_frame, text="전체", command=self._show_all,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=2, width=8, height=1,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="left", padx=3)

        # 설정 및 닫기 버튼 프레임
        button_frame = tk.Frame(top_frame, bg="#34495E")
        button_frame.pack(side="right", padx=20, pady=15)
        
        # 기록 반출 버튼
        save_file_btn = tk.Button(button_frame, text="📤 기록 반출", command=self._save_to_file,
                                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                              relief="raised", bd=2, width=12, height=2,
                                 activebackground="#229954", activeforeground="#FFFFFF")
        save_file_btn.pack(side="left", padx=(0, 10))

        # 반출 이력 버튼
        export_history_btn = tk.Button(button_frame, text="📋 반출 이력", command=self._show_export_history,
                                      bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                      relief="raised", bd=2, width=12, height=2,
                                      activebackground="#2980B9", activeforeground="#FFFFFF")
        export_history_btn.pack(side="left", padx=(0, 10))
        
        # (요청) 저장 폴더 열기 버튼 제거
        
        # 닫기 버튼
        close_btn = tk.Button(button_frame, text="✕ 닫기", command=self._close,
                             bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 16, "bold"),
                             relief="raised", bd=3, width=12, height=2,
                             activebackground="#C0392B", activeforeground="#FFFFFF")
        close_btn.pack(side="left")

        # 메인 컨테이너 (grid 사용 - 목록 60%, 이미지 40%)
        main_container = tk.Frame(self.dialog, bg="#2C3E50")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 그리드 가중치 설정 (3:2 비율 - 리스트 60%, 이미지 40%)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=3, minsize=800)  # 리스트 (60%) - 최소 800px
        main_container.grid_columnconfigure(1, weight=2, minsize=400)  # 이미지 (40%) - 최소 400px

        # 왼쪽: 사진 목록 (60%)
        list_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=3)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        list_title = tk.Label(list_frame, text="사진 목록 (시간순)",
                            font=("Pretendard", 16, "bold"), fg="#FFD700", bg="#34495E")
        list_title.pack(pady=10)

        # 그리드 형태의 사진 목록
        list_container = tk.Frame(list_frame, bg="#34495E")
        list_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 캔버스와 스크롤바
        canvas_frame = tk.Frame(list_container, bg="#34495E")
        canvas_frame.pack(fill="both", expand=True)

        self.grid_canvas = tk.Canvas(canvas_frame, bg="#FFFFFF", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.grid_canvas.yview)
        
        self.grid_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 캔버스 이벤트 바인딩 (Windows/macOS + Linux)
        self.grid_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.grid_canvas.bind("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.grid_canvas.bind("<Button-5>", self._on_mousewheel)  # Linux scroll down

        # 선택된 항목 추적
        self.selected_items = set()
        self.checkbox_vars = []  # 체크박스 변수들
        self.grid_items = []  # 그리드 항목들

        # 선택 관리 버튼들
        selection_frame = tk.Frame(list_frame, bg="#34495E")
        selection_frame.pack(fill="x", padx=10, pady=(0, 5))

        # 전체 선택 버튼
        select_all_btn = tk.Button(selection_frame, text="☑ 전체 선택", command=self._select_all,
                                  bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                  relief="raised", bd=2, width=12, height=1,
                                  activebackground="#229954", activeforeground="#FFFFFF")
        select_all_btn.pack(side="left", padx=(0, 5))

        # 전체 선택 해제 버튼
        deselect_all_btn = tk.Button(selection_frame, text="☐ 전체 해제", command=self._deselect_all,
                                    bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                    relief="raised", bd=2, width=12, height=1,
                                    activebackground="#7F8C8D", activeforeground="#FFFFFF")
        deselect_all_btn.pack(side="left", padx=(0, 5))

        # 선택된 사진 삭제 버튼
        delete_selected_btn = tk.Button(selection_frame, text="🗑 선택 삭제", command=self._delete_selected,
                                       bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                                       relief="raised", bd=2, width=12, height=1,
                              activebackground="#C0392B", activeforeground="#FFFFFF")
        delete_selected_btn.pack(side="left")


        # 오른쪽: 사진 표시 영역 (40%)
        right_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=3)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 정보 표시 (고정 높이)
        info_container = tk.Frame(right_frame, bg="#34495E", height=60)
        info_container.pack(fill="x", pady=15)
        info_container.pack_propagate(False)  # 크기 고정

        self.info_label = tk.Label(info_container, text="",
                                   font=("Pretendard", 18, "bold"), bg="#34495E", fg="#FFD700")
        self.info_label.pack(expand=True)

        # 사진 표시 영역 (상단)
        photo_display = tk.Frame(right_frame, bg="#000000", relief="sunken", bd=3)
        photo_display.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # 이미지 표시를 위한 Canvas와 스크롤바
        canvas_frame = tk.Frame(photo_display, bg="#000000")
        canvas_frame.pack(fill="both", expand=True)
        
        self.photo_canvas = tk.Canvas(canvas_frame, bg="#000000", highlightthickness=0)
        photo_scrollbar_v = tk.Scrollbar(canvas_frame, orient="vertical", command=self.photo_canvas.yview)
        photo_scrollbar_h = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.photo_canvas.xview)
        
        self.photo_canvas.configure(yscrollcommand=photo_scrollbar_v.set, xscrollcommand=photo_scrollbar_h.set)
        
        self.photo_canvas.pack(side="left", fill="both", expand=True)
        photo_scrollbar_v.pack(side="right", fill="y")
        photo_scrollbar_h.pack(side="bottom", fill="x")
        
        # 마우스 휠 스크롤 바인딩
        self.photo_canvas.bind("<MouseWheel>", self._on_photo_mousewheel)
        self.photo_canvas.bind("<Button-4>", self._on_photo_mousewheel)
        self.photo_canvas.bind("<Button-5>", self._on_photo_mousewheel)

        # 해시 정보 표시 영역 (하단)
        hash_frame = tk.Frame(right_frame, bg="#2C3E50", relief="sunken", bd=3)
        hash_frame.pack(fill="x", padx=20, pady=(0, 20))

        hash_title = tk.Label(hash_frame, text="해시 정보",
                            font=("Pretendard", 14, "bold"), fg="#FFD700", bg="#2C3E50")
        hash_title.pack(pady=5)

        # 해시 정보 텍스트 영역
        hash_text_frame = tk.Frame(hash_frame, bg="#2C3E50")
        hash_text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.hash_text = tk.Text(hash_text_frame, height=6, font=("Pretendard", 10),
                                bg="#34495E", fg="#FFFFFF", wrap="word", state="disabled")
        hash_scrollbar = tk.Scrollbar(hash_text_frame, orient="vertical", command=self.hash_text.yview)
        self.hash_text.configure(yscrollcommand=hash_scrollbar.set)

        self.hash_text.pack(side="left", fill="both", expand=True)
        hash_scrollbar.pack(side="right", fill="y")

        # 리스트 채우기
        self._update_grid()

        # 첫 번째 사진 선택
        if self.photos:
            self.current_index = 0
            self._display_photo()
            self._load_hash_content()

    def _load_photos(self):
        """안전 교육 사진 로드 (년도별 폴더 포함)"""
        # 기존 목록 초기화
        self.photos = []

        # 프로그램 설치 디렉토리 기준으로 경로 설정
        install_dir = get_base_dir()
        base_photo_dir = os.path.join(install_dir, "safety_photos")

        if not os.path.exists(base_photo_dir):
            return

        # safety_이름_YYYYMMDD_HHMMSS.jpg 또는 safety_YYYYMMDD_HHMMSS.jpg 형식의 파일 찾기
        pattern_with_name = re.compile(r'safety_(.+?)_(\d{8})_(\d{6})\.jpg')  # 이름 포함
        pattern_without_name = re.compile(r'safety_(\d{8})_(\d{6})\.jpg')  # 이름 없음

        # 년도별 폴더와 루트 폴더 모두 검색
        search_dirs = []
        
        # 루트 폴더 추가
        search_dirs.append(base_photo_dir)
        
        # 년도별 폴더 추가
        try:
            for item in os.listdir(base_photo_dir):
                item_path = os.path.join(base_photo_dir, item)
                if os.path.isdir(item_path) and item.isdigit() and len(item) == 4:  # 4자리 년도 폴더
                    search_dirs.append(item_path)
        except Exception as e:
            pass

        for photo_dir in search_dirs:
            try:
                file_count = 0
                for filename in os.listdir(photo_dir):
                    # 해시 파일(.hash)은 제외하고 이미지 파일만 처리
                    if filename.endswith('.hash'):
                        continue
                    
                    # 먼저 이름 포함 패턴 시도
                    match = pattern_with_name.match(filename)
                    if match:
                        filepath = os.path.join(photo_dir, filename)
                        name = match.group(1)  # 이름
                        date_str = match.group(2)  # YYYYMMDD
                        time_str = match.group(3)  # HHMMSS

                        # datetime 객체 생성
                        try:
                            dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                            self.photos.append((filepath, dt, name))
                            file_count += 1
                        except:
                            pass
                        continue

                    # 이름 없는 패턴 시도
                    match = pattern_without_name.match(filename)
                    if match:
                        filepath = os.path.join(photo_dir, filename)
                        date_str = match.group(1)  # YYYYMMDD
                        time_str = match.group(2)  # HHMMSS

                        # datetime 객체 생성
                        try:
                            dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                            self.photos.append((filepath, dt, None))  # 이름 없음
                            file_count += 1
                        except:
                            pass
            except Exception as e:
                continue

        # 최신순으로 정렬 (최근 것이 먼저)
        self.photos.sort(key=lambda x: x[1], reverse=True)

    def _update_grid(self):
        """그리드 형태로 사진 목록 업데이트"""
        # 캔버스 내용 지우기
        self.grid_canvas.delete("all")
        self.checkbox_vars.clear()
        self.grid_items.clear()
        self.selected_items.clear()

        if not self.photos:
            return

        # 그리드 설정 (더 넓게 조정)
        row_height = 35
        header_height = 40

        # 첫 번째 호출 시에만 컬럼 너비 초기화
        if not hasattr(self, 'col_widths') or self.col_widths is None:
            # 이름/파일명 열 너비를 내용에 맞게 자동 확장
            try:
                import tkinter.font as tkfont
                font_cell = tkfont.Font(family="Pretendard", size=10, weight="normal")
                # 기본값
                name_w = 160
                file_w = 420
                # 최소: 10자 기준 폭 보장
                min_name = font_cell.measure('가'*10) + 40
                min_file = font_cell.measure('W'*24) + 60
                for item in self.photos:
                    if len(item) == 3:
                        filepath, dt, name = item
                    else:
                        filepath, dt = item
                        name = None
                    nm = name or "미상"
                    fn = os.path.basename(filepath)
                    # 텍스트 픽셀 폭 측정 + 여유
                    name_w = max(name_w, font_cell.measure(nm) + 40, min_name)
                    file_w = max(file_w, font_cell.measure(fn) + 60, min_file)
                # 상한선(너무 넓어지지 않도록)
                name_w = min(name_w, 420)
                file_w = min(file_w, 980)
            except Exception:
                name_w = 120
                file_w = 300

            self.col_widths = [60, 60, 200, name_w, file_w]  # 순번, 체크박스, 촬영일시, 이름, 파일명

        total_width = sum(self.col_widths)

        # 헤더 그리기 (크기 조정 가능)
        y_pos = 5
        headers = ["순번", "선택", "촬영일시", "이름", "파일명"]

        for i, (header, width) in enumerate(zip(headers, self.col_widths)):
            x_pos = sum(self.col_widths[:i]) + 5

            # 헤더 배경
            self.grid_canvas.create_rectangle(
                x_pos, y_pos, x_pos + width, y_pos + header_height,
                fill="#34495E", outline="#2C3E50", width=1
            )

            # 헤더 텍스트 (좌측 정렬)
            self.grid_canvas.create_text(
                x_pos + 10, y_pos + header_height//2,
                text=header, font=("Pretendard", 12, "bold"),
                fill="#FFFFFF", anchor="w"
            )

            # 마지막 컬럼이 아닌 경우 크기 조정 핸들 추가 (더 넓게)
            if i < len(self.col_widths) - 1:
                # 조정 핸들 영역 (더 넓은 범위, 시각적으로 표시)
                handle_x = x_pos + width - 4
                resize_handle = self.grid_canvas.create_rectangle(
                    handle_x, y_pos, handle_x + 8, y_pos + header_height,
                    fill="#5DADE2", outline="", width=0, tags=f"resize_{i}"
                )

                # 조정 핸들에 커서 변경 및 이벤트 바인딩
                self.grid_canvas.tag_bind(resize_handle, "<Enter>",
                                        lambda e: self.grid_canvas.config(cursor="sb_h_double_arrow"))
                self.grid_canvas.tag_bind(resize_handle, "<Leave>",
                                        lambda e: self.grid_canvas.config(cursor=""))
                self.grid_canvas.tag_bind(resize_handle, "<Button-1>",
                                        lambda e, col=i: self._start_resize(e, col))
                self.grid_canvas.tag_bind(resize_handle, "<B1-Motion>",
                                        lambda e, col=i: self._resize_column(e, col))
                self.grid_canvas.tag_bind(resize_handle, "<ButtonRelease-1>",
                                        lambda e, col=i: self._end_resize(e, col))

        # 데이터 행 그리기
        y_pos = header_height + 5

        for i, item in enumerate(self.photos):
            if len(item) == 3:
                filepath, dt, name = item
            else:
                filepath, dt = item
                name = None

            # 행 배경색 (짝수/홀수 구분)
            row_color = "#F8F9FA" if i % 2 == 0 else "#FFFFFF"

            # 행 배경 그리기
            self.grid_canvas.create_rectangle(
                5, y_pos, total_width + 5, y_pos + row_height,
                fill=row_color, outline="#E9ECEF", width=1
            )

            # 순번 (좌측 정렬)
            x_pos = 5
            self.grid_canvas.create_text(
                x_pos + 10, y_pos + row_height//2,
                text=str(i + 1), font=("Pretendard", 10),
                fill="#000000", anchor="w"
            )

            # 체크박스 변수 생성
            var = tk.BooleanVar()
            self.checkbox_vars.append(var)

            # 실제 tkinter Checkbutton 사용
            checkbox_x = self.col_widths[0] + 10
            checkbox_y = y_pos + row_height//2

            # Checkbutton을 캔버스에 임베드
            checkbox = tk.Checkbutton(self.grid_canvas, variable=var,
                                    command=lambda idx=i: self._on_checkbox_change(idx),
                                    bg=row_color, activebackground=row_color,
                                    relief="flat", bd=0)

            # 캔버스에 Checkbutton 임베드
            self.grid_canvas.create_window(
                checkbox_x, checkbox_y, window=checkbox, anchor="w"
            )

            # 촬영일시 (좌측 정렬)
            time_str = dt.strftime("%Y/%m/%d %H:%M:%S")
            time_x = sum(self.col_widths[:2]) + 10
            self.grid_canvas.create_text(
                time_x, y_pos + row_height//2,
                text=time_str, font=("Pretendard", 10),
                fill="#000000", anchor="w"
            )

            # 이름 (좌측 정렬)
            name_text = name or "미상"
            name_x = sum(self.col_widths[:3]) + 10
            self.grid_canvas.create_text(
                name_x, y_pos + row_height//2,
                text=name_text, font=("Pretendard", 10),
                fill="#000000", anchor="w"
            )

            # 파일명 (좌측 정렬, 길이 제한 완화)
            filename = os.path.basename(filepath)
            # 파일명이 너무 길면 축약 (컬럼 너비에 맞춰 동적 조절)
            max_chars = max(20, self.col_widths[4] // 8)
            if len(filename) > max_chars:
                filename = filename[:max_chars-3] + "..."
            file_x = sum(self.col_widths[:4]) + 10
            self.grid_canvas.create_text(
                file_x, y_pos + row_height//2,
                text=filename, font=("Pretendard", 9),
                fill="#000000", anchor="w"
            )

            # 행 클릭 이벤트 (이미지 표시)
            row_rect = self.grid_canvas.create_rectangle(
                5, y_pos, total_width + 5, y_pos + row_height,
                fill="", outline="", width=0
            )
            self.grid_canvas.tag_bind(row_rect, "<Double-Button-1>",
                                    lambda e, idx=i: self._on_row_double_click(idx))

            self.grid_items.append((i, row_rect))
            y_pos += row_height

        # 스크롤 영역 설정
        self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))

    def _on_checkbox_change(self, index):
        """체크박스 상태 변경 이벤트"""
        print(f"체크박스 상태 변경됨: index={index}")
        
        if index < len(self.checkbox_vars):
            var = self.checkbox_vars[index]
            
            if var.get():
                self.selected_items.add(index)
                print(f"선택됨: {index}, 현재 선택된 항목: {self.selected_items}")
            else:
                self.selected_items.discard(index)
                print(f"선택 해제됨: {index}, 현재 선택된 항목: {self.selected_items}")
        else:
            print(f"오류: index {index}가 checkbox_vars 길이 {len(self.checkbox_vars)}를 초과함")

    def _toggle_checkbox(self, index):
        """체크박스 토글 (프로그래밍 방식)"""
        if index < len(self.checkbox_vars):
            var = self.checkbox_vars[index]
            var.set(not var.get())
            self._on_checkbox_change(index)

    def _update_checkbox_display(self):
        """체크박스 표시 업데이트 (더 이상 필요하지 않음)"""
        pass

    def _start_resize(self, event, column):
        """컬럼 크기 조정 시작"""
        self.resizing = True
        self.resize_column = column
        self.start_x = event.x
        self.start_width = self.col_widths[column]

    def _resize_column(self, event, column):
        """컬럼 크기 조정 중"""
        if not self.resizing or self.resize_column != column:
            return
        
        delta_x = event.x - self.start_x
        new_width = max(30, self.start_width + delta_x)  # 최소 30px
        self.col_widths[column] = new_width
        
        # 그리드 다시 그리기
        self._update_grid()

    def _end_resize(self, event, column):
        """컬럼 크기 조정 종료"""
        self.resizing = False
        self.resize_column = None

    def _on_row_double_click(self, index):
        """행 더블클릭 이벤트"""
        self.current_index = index
        self._display_photo()
        self._load_hash_content()

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤 (Windows/macOS/Linux)"""
        if event.delta:
            # Windows/macOS
            self.grid_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            # Linux scroll up
            self.grid_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            # Linux scroll down
            self.grid_canvas.yview_scroll(1, "units")
    
    def _on_photo_mousewheel(self, event):
        """사진 캔버스 마우스 휠 스크롤"""
        if event.delta:
            self.photo_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.photo_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.photo_canvas.yview_scroll(1, "units")

    def _load_hash_content(self):
        """해시 파일 내용 로드 및 표시"""
        if not self.photos or self.current_index >= len(self.photos):
            self.hash_text.config(state="normal")
            self.hash_text.delete(1.0, tk.END)
            self.hash_text.config(state="disabled")
            return

        item = self.photos[self.current_index]
        if len(item) == 3:
            filepath, dt, name = item
        else:
            filepath, dt = item
            name = None

        # 해시 파일 경로
        hash_filepath = filepath + ".hash"
        
        self.hash_text.config(state="normal")
        self.hash_text.delete(1.0, tk.END)
        
        if os.path.exists(hash_filepath):
            try:
                with open(hash_filepath, 'r', encoding='utf-8') as f:
                    hash_content = f.read()
                self.hash_text.insert(1.0, hash_content)
            except Exception as e:
                self.hash_text.insert(1.0, f"해시 파일 읽기 오류:\n{str(e)}")
        else:
            self.hash_text.insert(1.0, "해시 파일을 찾을 수 없습니다.")
        
        self.hash_text.config(state="disabled")

    def _select_all(self):
        """전체 선택"""
        for i, var in enumerate(self.checkbox_vars):
            var.set(True)
            self.selected_items.add(i)
        self._update_checkbox_display()

    def _deselect_all(self):
        """전체 선택 해제"""
        for i, var in enumerate(self.checkbox_vars):
            var.set(False)
        self.selected_items.clear()
        self._update_checkbox_display()

    def _delete_selected(self):
        """선택된 사진들 삭제"""
        if not self.selected_items:
            self._show_custom_warning("선택 없음", "삭제할 사진을 선택하세요.\n\n목록에서 체크박스를 클릭하여 사진을 선택하세요.")
            return

        selected_indices = list(self.selected_items)

        # 커스텀 확인 다이얼로그 (예/아니오)
        confirm_result = [False]

        confirm_dlg = tk.Toplevel(self.dialog)
        confirm_dlg.title("삭제 확인")
        confirm_dlg.configure(bg="#2C3E50")
        confirm_dlg.transient(self.dialog)
        confirm_dlg.grab_set()
        confirm_dlg.geometry("450x200")
        confirm_dlg.update_idletasks()
        x = (confirm_dlg.winfo_screenwidth() // 2) - 225
        y = (confirm_dlg.winfo_screenheight() // 2) - 100
        confirm_dlg.geometry(f"450x200+{x}+{y}")
        confirm_dlg.attributes("-topmost", True)
        confirm_dlg.focus_force()

        # 제목
        title_frm = tk.Frame(confirm_dlg, bg="#E74C3C")
        title_frm.pack(fill="x")
        tk.Label(title_frm, text="🗑️ 사진 삭제 확인",
                font=("Pretendard", 14, "bold"), bg="#E74C3C", fg="#FFFFFF").pack(pady=10)

        # 메시지
        msg_frm = tk.Frame(confirm_dlg, bg="#2C3E50")
        msg_frm.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(msg_frm, text=f"선택된 {len(selected_indices)}개의 사진을 삭제하시겠습니까?\n\n(삭제된 파일은 복구할 수 없습니다)",
                font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF", justify="center").pack(expand=True)

        # 버튼 프레임
        btn_frm = tk.Frame(confirm_dlg, bg="#2C3E50")
        btn_frm.pack(pady=15)

        def on_yes():
            confirm_result[0] = True
            confirm_dlg.destroy()

        def on_no():
            confirm_result[0] = False
            confirm_dlg.destroy()

        tk.Button(btn_frm, text="삭제", command=on_yes,
                 bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 width=8).pack(side="left", padx=10)
        tk.Button(btn_frm, text="취소", command=on_no,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 width=8).pack(side="left", padx=10)

        confirm_dlg.bind("<Return>", lambda e: on_yes())
        confirm_dlg.bind("<Escape>", lambda e: on_no())

        # 모달 대기
        self.dialog.wait_window(confirm_dlg)

        if not confirm_result[0]:
            return

        # 삭제 실행
        deleted_count = 0
        errors = []
        for index in sorted(selected_indices, reverse=True):  # 역순으로 삭제 (인덱스 유지)
            try:
                item = self.photos[index]
                if len(item) == 3:
                    filepath, dt, name = item
                else:
                    filepath, dt = item
                    name = None

                # 파일 삭제
                if os.path.exists(filepath):
                    os.remove(filepath)

                # 해시 파일도 삭제
                hash_filepath = filepath + ".hash"
                if os.path.exists(hash_filepath):
                    os.remove(hash_filepath)

                # 리스트에서 제거
                self.photos.pop(index)
                deleted_count += 1

            except Exception as e:
                errors.append(str(e))

        # 오류가 있으면 표시
        if errors:
            self._show_custom_error("삭제 오류", f"일부 파일 삭제 중 오류가 발생했습니다:\n{errors[0]}")

        # UI 업데이트
        self.current_index = 0
        self._update_grid()
        self._display_photo()
        self._load_hash_content()

        # 완료 메시지
        self._show_custom_info("삭제 완료", f"{deleted_count}개의 사진이 삭제되었습니다.")

    def _display_photo(self):
        """현재 사진 표시"""
        # Canvas 내용 지우기
        self.photo_canvas.delete("all")

        if not self.photos:
            # Canvas에 텍스트로 표시
            self.photo_canvas.create_text(
                self.photo_canvas.winfo_width() // 2 or 400,
                self.photo_canvas.winfo_height() // 2 or 300,
                text="사진이 없습니다.",
                fill="#FFFFFF", font=("Pretendard", 20, "bold")
            )
            self.info_label.configure(text="")
            return

        item = self.photos[self.current_index]
        if len(item) == 3:
            filepath, dt, name = item
        else:
            filepath, dt = item
            name = None

        # 정보 업데이트
        date_str = dt.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        info_text = f"촬영 일시: {date_str}"
        if name:
            info_text += f"  |  이름: {name}"
        info_text += f"  |  {self.current_index + 1} / {len(self.photos)}"
        self.info_label.configure(text=info_text)

        # 이미지 표시
        if not PIL_OK:
            self.photo_canvas.create_text(
                self.photo_canvas.winfo_width() // 2 or 400,
                self.photo_canvas.winfo_height() // 2 or 300,
                text=f"PIL(Pillow) 라이브러리가 필요합니다.\n\n파일: {os.path.basename(filepath)}\n경로: {filepath}",
                fill="#FFFFFF", font=("Pretendard", 14, "bold"), justify="center"
            )
            return

        try:
            # Canvas 크기 가져오기 (update 후)
            self.photo_canvas.update_idletasks()
            canvas_width = self.photo_canvas.winfo_width()
            canvas_height = self.photo_canvas.winfo_height()

            # Canvas 크기가 아직 설정 안 되었을 경우 기본값
            if canvas_width <= 1:
                canvas_width = 1000
            if canvas_height <= 1:
                canvas_height = 700

            # 여백 고려
            display_width = canvas_width - 40
            display_height = canvas_height - 40

            # 캐시 키 생성 (파일경로 + 캔버스 크기)
            cache_key = f"{filepath}_{display_width}x{display_height}"

            # 캐시에서 확인
            if cache_key in self.image_cache:
                photo = self.image_cache[cache_key]
            else:
                # 이미지 로드 및 리사이즈
                img = Image.open(filepath)
                img_copy = img.copy()
                img_copy.thumbnail((display_width, display_height), Image.LANCZOS)

                # PhotoImage로 변환
                photo = ImageTk.PhotoImage(img_copy)

                # 캐시에 저장 (최대 10개까지만)
                if len(self.image_cache) >= 10:
                    # 가장 오래된 항목 삭제
                    oldest_key = next(iter(self.image_cache))
                    del self.image_cache[oldest_key]

                self.image_cache[cache_key] = photo

            # Canvas 중앙에 이미지 배치
            x = canvas_width // 2
            y = canvas_height // 2
            self.photo_canvas.create_image(x, y, image=photo, anchor="center")

            # 스크롤 영역 설정 (이미지 크기에 맞춰)
            img_width = photo.width()
            img_height = photo.height()
            scroll_width = max(canvas_width, img_width + 40)
            scroll_height = max(canvas_height, img_height + 40)
            
            self.photo_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))

            # 참조 유지 (Canvas에 저장)
            self.photo_canvas.image = photo

        except Exception as e:
            self.photo_canvas.create_text(
                self.photo_canvas.winfo_width() // 2 or 400,
                self.photo_canvas.winfo_height() // 2 or 300,
                text=f"이미지 로드 실패:\n{str(e)}\n\n파일: {filepath}",
                fill="#FF6B6B", font=("Pretendard", 14, "bold"), justify="center"
            )


    def _delete_current(self):
        """현재 사진 삭제"""
        if not self.photos:
            return

        from tkinter import messagebox

        item = self.photos[self.current_index]
        if len(item) == 3:
            filepath, dt, name = item
        else:
            filepath, dt = item
            name = None

        date_str = dt.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")

        message = f"다음 사진을 삭제하시겠습니까?\n\n촬영 일시: {date_str}\n"
        if name:
            message += f"이름: {name}\n"
        message += f"파일: {os.path.basename(filepath)}"

        if messagebox.askyesno("사진 삭제", message, parent=self.dialog):
            try:
                os.remove(filepath)
                messagebox.showinfo("삭제 완료", "사진이 삭제되었습니다.", parent=self.dialog)

                # 캐시에서도 제거
                keys_to_remove = [key for key in self.image_cache.keys() if key.startswith(filepath)]
                for key in keys_to_remove:
                    del self.image_cache[key]

                # 목록에서 제거
                self.photos.pop(self.current_index)
                self.all_photos = [p for p in self.all_photos if p[0] != filepath]

                # 인덱스 조정
                if self.current_index >= len(self.photos):
                    self.current_index = max(0, len(self.photos) - 1)

                # 리스트 업데이트
                self._update_grid()

                # 사진이 없으면 닫기
                if not self.photos:
                    messagebox.showinfo("알림", "모든 사진이 삭제되었습니다.", parent=self.dialog)
                    self._close()
                else:
                    # 새로운 선택 항목 표시
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(self.current_index)
                    self._display_photo()

            except Exception as e:
                messagebox.showerror("오류", f"사진 삭제 중 오류가 발생했습니다:\n{str(e)}",
                                   parent=self.dialog)

    def _on_entry_focus(self, entry, placeholder):
        """입력란 포커스"""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)

    def _search(self):
        """통합 검색 (기간 + 이름)"""
        from tkinter import messagebox

        # 전체 사진 로드
        self._load_photos()

        # 검색 조건 수집
        date_from = self.date_from_entry.get().strip()
        date_to = self.date_to_entry.get().strip()
        name_query = self.name_entry.get().strip()

        # 플레이스홀더 제거
        if date_from == "YYYYMMDD":
            date_from = ""
        if date_to == "YYYYMMDD":
            date_to = ""

        # 검색 조건이 하나도 없으면 경고
        if not date_from and not date_to and not name_query:
            messagebox.showwarning("검색", "검색 조건을 하나 이상 입력하세요.", parent=self.dialog)
            return

        # 날짜 유효성 검사
        if date_from and (len(date_from) != 8 or not date_from.isdigit()):
            messagebox.showerror("오류", "시작 날짜 형식이 올바르지 않습니다.\nYYYYMMDD 형식으로 입력하세요.",
                               parent=self.dialog)
            return

        if date_to and (len(date_to) != 8 or not date_to.isdigit()):
            messagebox.showerror("오류", "종료 날짜 형식이 올바르지 않습니다.\nYYYYMMDD 형식으로 입력하세요.",
                               parent=self.dialog)
            return

        # 필터링
        filtered_photos = []
        for item in self.photos:
            if len(item) == 3:
                filepath, dt, name = item
            else:
                filepath, dt = item
                name = None

            # 기간 필터
            dt_str = dt.strftime("%Y%m%d")
            if date_from and dt_str < date_from:
                continue
            if date_to and dt_str > date_to:
                continue

            # 이름 필터 (부분 일치)
            if name_query:
                if not name or name_query not in name:
                    continue

            # 조건 통과
            if name:
                filtered_photos.append((filepath, dt, name))
            else:
                filtered_photos.append((filepath, dt))

        if not filtered_photos:
            search_desc = []
            if date_from or date_to:
                if date_from and date_to:
                    search_desc.append(f"기간: {date_from} ~ {date_to}")
                elif date_from:
                    search_desc.append(f"기간: {date_from} 이후")
                else:
                    search_desc.append(f"기간: {date_to} 이전")
            if name_query:
                search_desc.append(f"이름: {name_query}")

            messagebox.showinfo("검색 결과", f"검색 조건에 맞는 사진이 없습니다.\n\n{' / '.join(search_desc)}",
                              parent=self.dialog)
            return

        # 필터링된 사진으로 교체
        self.photos = filtered_photos
        self.current_index = 0

        # 리스트 업데이트
        self._update_grid()

        # 첫 번째 항목 선택
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(0)
        self._display_photo()

        # 검색 결과 메시지
        search_desc = []
        if date_from or date_to:
            if date_from and date_to:
                search_desc.append(f"기간: {date_from} ~ {date_to}")
            elif date_from:
                search_desc.append(f"기간: {date_from} 이후")
            else:
                search_desc.append(f"기간: {date_to} 이전")
        if name_query:
            search_desc.append(f"이름: {name_query}")

        messagebox.showinfo("검색 결과",
                          f"{' / '.join(search_desc)}\n\n총 {len(filtered_photos)}개의 사진이 있습니다.",
                          parent=self.dialog)

    def _search_by_date(self):
        """날짜로 검색"""
        date_str = self.date_entry.get().strip()

        if not date_str or date_str == "YYYYMMDD":
            from tkinter import messagebox
            messagebox.showwarning("경고", "날짜를 입력하세요 (예: 20240315)", parent=self.dialog)
            return

        # 날짜 형식 검증 (YYYYMMDD)
        if len(date_str) != 8 or not date_str.isdigit():
            from tkinter import messagebox
            messagebox.showerror("오류", "날짜 형식이 올바르지 않습니다.\nYYYYMMDD 형식으로 입력하세요 (예: 20240315)",
                               parent=self.dialog)
            return

        # 전체 사진 로드
        self._load_photos()

        # 날짜로 필터링
        filtered_photos = []
        for item in self.photos:
            if len(item) == 3:
                filepath, dt, name = item
            else:
                filepath, dt = item
                name = None

            if dt.strftime("%Y%m%d") == date_str:
                if name:
                    filtered_photos.append((filepath, dt, name))
                else:
                    filtered_photos.append((filepath, dt))

        if not filtered_photos:
            from tkinter import messagebox
            messagebox.showinfo("검색 결과", f"{date_str[:4]}년 {date_str[4:6]}월 {date_str[6:8]}일에 촬영된 사진이 없습니다.",
                              parent=self.dialog)
            return

        # 필터링된 사진으로 교체
        self.photos = filtered_photos
        self.current_index = 0

        # 리스트 업데이트
        self._update_grid()

        # 첫 번째 항목 선택
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(0)
        self._display_photo()

        # 검색 결과 메시지
        from tkinter import messagebox
        messagebox.showinfo("검색 결과",
                          f"{date_str[:4]}년 {date_str[4:6]}월 {date_str[6:8]}일\n"
                          f"총 {len(filtered_photos)}개의 사진이 있습니다.",
                          parent=self.dialog)

    def _show_all(self):
        """전체 사진 보기"""
        # 전체 사진 복원
        self.photos = self.all_photos.copy()
        self.current_index = 0

        # 리스트 업데이트
        self._update_grid()

        # 첫 번째 항목 선택
        if self.photos:
            self.current_index = 0
            self._display_photo()
            self._load_hash_content()

        # 검색 입력란 초기화
        self.date_from_entry.delete(0, tk.END)
        self.date_from_entry.insert(0, "YYYYMMDD")
        self.date_to_entry.delete(0, tk.END)
        self.date_to_entry.insert(0, "YYYYMMDD")
        self.name_entry.delete(0, tk.END)

    def _save_to_file(self):
        """선택된 사진들을 기록 반출 (반출사유/반출자 입력 후 저장)"""
        if not self.selected_items:
            # 전체화면 모드에서 메시지가 보이도록 커스텀 다이얼로그 사용
            self._show_custom_warning("선택 없음", "반출할 사진을 먼저 선택하세요.\n\n목록에서 체크박스를 클릭하여 사진을 선택하세요.")
            return

        selected_indices = list(self.selected_items)

        # 기록 반출 다이얼로그 표시
        self._show_export_dialog(selected_indices)

    def _show_custom_warning(self, title, message):
        """커스텀 경고 다이얼로그 (전체화면 모드에서도 표시)"""
        warn_dialog = tk.Toplevel(self.dialog)
        warn_dialog.title(title)
        warn_dialog.configure(bg="#2C3E50")
        warn_dialog.transient(self.dialog)
        warn_dialog.grab_set()

        # 창 크기 및 중앙 배치 (하단 10% 확장하여 버튼 완전 표시)
        dialog_width = 450
        dialog_height = 220
        warn_dialog.geometry(f"{dialog_width}x{dialog_height}")
        warn_dialog.update_idletasks()
        x = (warn_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (warn_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        warn_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        warn_dialog.attributes("-topmost", True)
        warn_dialog.focus_force()

        # 아이콘과 제목
        title_frame = tk.Frame(warn_dialog, bg="#E67E22")
        title_frame.pack(fill="x")
        tk.Label(title_frame, text=f"⚠️ {title}",
                font=("Pretendard", 14, "bold"), bg="#E67E22", fg="#FFFFFF").pack(pady=10)

        # 메시지
        msg_frame = tk.Frame(warn_dialog, bg="#2C3E50")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(msg_frame, text=message,
                font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF",
                justify="center", wraplength=400).pack(expand=True)

        # 확인 버튼
        btn_frame = tk.Frame(warn_dialog, bg="#2C3E50")
        btn_frame.pack(pady=15)
        ok_btn = tk.Button(btn_frame, text="확인", command=warn_dialog.destroy,
                          bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                          relief="raised", bd=2, width=10, height=1,
                          activebackground="#D35400", activeforeground="#FFFFFF")
        ok_btn.pack()
        ok_btn.focus_set()

        # Enter/ESC로 닫기
        warn_dialog.bind("<Return>", lambda e: warn_dialog.destroy())
        warn_dialog.bind("<Escape>", lambda e: warn_dialog.destroy())

    def _show_custom_info(self, title, message):
        """커스텀 정보 다이얼로그 (전체화면 모드에서도 표시)"""
        info_dialog = tk.Toplevel(self.dialog)
        info_dialog.title(title)
        info_dialog.configure(bg="#2C3E50")
        info_dialog.transient(self.dialog)
        info_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 450
        dialog_height = 200
        info_dialog.geometry(f"{dialog_width}x{dialog_height}")
        info_dialog.update_idletasks()
        x = (info_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (info_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        info_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        info_dialog.attributes("-topmost", True)
        info_dialog.focus_force()

        # 아이콘과 제목
        title_frame = tk.Frame(info_dialog, bg="#3498DB")
        title_frame.pack(fill="x")
        tk.Label(title_frame, text=f"ℹ️ {title}",
                font=("Pretendard", 14, "bold"), bg="#3498DB", fg="#FFFFFF").pack(pady=10)

        # 메시지
        msg_frame = tk.Frame(info_dialog, bg="#2C3E50")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(msg_frame, text=message,
                font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF",
                justify="center", wraplength=400).pack(expand=True)

        # 확인 버튼
        btn_frame = tk.Frame(info_dialog, bg="#2C3E50")
        btn_frame.pack(pady=15)
        ok_btn = tk.Button(btn_frame, text="확인", command=info_dialog.destroy,
                          bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                          relief="raised", bd=2, width=10, height=1,
                          activebackground="#2980B9", activeforeground="#FFFFFF")
        ok_btn.pack()
        ok_btn.focus_set()

        # Enter/ESC로 닫기
        info_dialog.bind("<Return>", lambda e: info_dialog.destroy())
        info_dialog.bind("<Escape>", lambda e: info_dialog.destroy())

    def _show_custom_error(self, title, message):
        """커스텀 오류 다이얼로그 (전체화면 모드에서도 표시)"""
        err_dialog = tk.Toplevel(self.dialog)
        err_dialog.title(title)
        err_dialog.configure(bg="#2C3E50")
        err_dialog.transient(self.dialog)
        err_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 450
        dialog_height = 220
        err_dialog.geometry(f"{dialog_width}x{dialog_height}")
        err_dialog.update_idletasks()
        x = (err_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (err_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        err_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        err_dialog.attributes("-topmost", True)
        err_dialog.focus_force()

        # 아이콘과 제목
        title_frame = tk.Frame(err_dialog, bg="#E74C3C")
        title_frame.pack(fill="x")
        tk.Label(title_frame, text=f"❌ {title}",
                font=("Pretendard", 14, "bold"), bg="#E74C3C", fg="#FFFFFF").pack(pady=10)

        # 메시지
        msg_frame = tk.Frame(err_dialog, bg="#2C3E50")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(msg_frame, text=message,
                font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF",
                justify="center", wraplength=400).pack(expand=True)

        # 확인 버튼
        btn_frame = tk.Frame(err_dialog, bg="#2C3E50")
        btn_frame.pack(pady=15)
        ok_btn = tk.Button(btn_frame, text="확인", command=err_dialog.destroy,
                          bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                          relief="raised", bd=2, width=10, height=1,
                          activebackground="#C0392B", activeforeground="#FFFFFF")
        ok_btn.pack()
        ok_btn.focus_set()

        # Enter/ESC로 닫기
        err_dialog.bind("<Return>", lambda e: err_dialog.destroy())
        err_dialog.bind("<Escape>", lambda e: err_dialog.destroy())

    def _save_as_csv_and_zip(self, selected_indices):
        """CSV 파일 생성 후 ZIP으로 압축하여 export 디렉토리에 저장"""
        import zipfile
        import csv
        import tempfile
        import shutil

        # export 디렉토리 경로 (프로그램 설치 디렉토리 기준)
        base_dir = get_base_dir()
        folder_path = os.path.join(base_dir, "export")

        # export 디렉토리 생성
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"export 폴더를 생성할 수 없습니다:\n{str(e)}", parent=self.dialog)
            return
        
        try:
            # 현재 날짜와 시간으로 파일명 생성
            current_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"안전교육사진_{current_datetime}.zip"
            zip_filepath = os.path.join(folder_path, zip_filename)
            
            # 임시 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                # 데이터 준비
                data = []
                for i, index in enumerate(selected_indices):
                    item = self.photos[index]
                    if len(item) == 3:
                        filepath, dt, name = item
                    else:
                        filepath, dt = item
                        name = None
                    
                    # 해시 파일에서 해시값 읽기
                    hash_value = ""
                    hash_filepath = filepath + ".hash"
                    if os.path.exists(hash_filepath):
                        try:
                            with open(hash_filepath, 'r', encoding='utf-8') as f:
                                hash_content = f.read()
                                # 해시값 추출 (해시값: 뒤의 값)
                                for line in hash_content.split('\n'):
                                    if line.startswith('해시값:'):
                                        hash_value = line.replace('해시값:', '').strip()
                                        break
                        except:
                            hash_value = "읽기 실패"
                    
                    data.append({
                        '번호': i + 1,
                        '촬영일시': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        '이름': name or '미상',
                        '파일명': os.path.basename(filepath),
                        '파일경로': filepath,
                        '년도': dt.year,
                        '월': dt.month,
                        '일': dt.day,
                        '시간': dt.strftime('%H:%M:%S'),
                        '해시값': hash_value
                    })
                
                # CSV 파일 생성
                csv_filename = f"안전교육사진목록_{current_datetime}.csv"
                csv_filepath = os.path.join(temp_dir, csv_filename)
                
                with open(csv_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['번호', '촬영일시', '이름', '파일명', '파일경로', '년도', '월', '일', '시간', '해시값']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for row in data:
                        writer.writerow(row)
                
                # XLSX 파일 생성
                xlsx_filename = f"안전교육사진목록_{current_datetime}.xlsx"
                xlsx_filepath = os.path.join(temp_dir, xlsx_filename)
                
                try:
                    import pandas as pd
                    df = pd.DataFrame(data)
                    df.to_excel(xlsx_filepath, index=False, engine='openpyxl')
                    xlsx_created = True
                except ImportError:
                    xlsx_created = False
                
                # ZIP 파일 생성
                with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # CSV 파일 추가
                    zipf.write(csv_filepath, csv_filename)
                    
                    # XLSX 파일 추가 (생성된 경우만)
                    if xlsx_created:
                        zipf.write(xlsx_filepath, xlsx_filename)
                    
                    # 선택된 이미지 파일들과 해시 파일들 추가
                    for index in selected_indices:
                        item = self.photos[index]
                        if len(item) == 3:
                            filepath, dt, name = item
                        else:
                            filepath, dt = item
                            name = None
                        
                        # 이미지 파일명 생성
                        if name:
                            image_filename = f"safety_{name}_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                        else:
                            image_filename = f"safety_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                        
                        # 이미지 파일 추가
                        zipf.write(filepath, image_filename)
                        
                        # 해시 파일도 함께 추가
                        hash_filepath = filepath + ".hash"
                        if os.path.exists(hash_filepath):
                            hash_filename = image_filename + ".hash"
                            zipf.write(hash_filepath, hash_filename)
            
            # 저장 완료 다이얼로그 표시
            files_info = f"{len(selected_indices)}개 이미지 + 해시파일 + CSV목록"
            if xlsx_created:
                files_info += " + XLSX목록"

            self._show_save_complete_dialog(zip_filename, folder_path, files_info)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _show_save_format_dialog(self, selected_indices):
        """파일 저장 형식 선택 다이얼로그"""
        format_dialog = tk.Toplevel(self.dialog)
        format_dialog.title("파일 저장 형식 선택")
        format_dialog.geometry("500x520")  # 400에서 520으로 30% 확장 (400 * 1.3 = 520)
        format_dialog.configure(bg="#34495E")
        format_dialog.transient(self.dialog)
        format_dialog.grab_set()

        # 중앙 배치
        format_dialog.update_idletasks()
        x = (format_dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (format_dialog.winfo_screenheight() // 2) - (520 // 2)  # 520/2 = 260
        format_dialog.geometry(f"500x520+{x}+{y}")

        # 제목
        title_label = tk.Label(format_dialog, text="파일 저장 형식 선택",
                              font=("Pretendard", 20, "bold"), bg="#34495E", fg="#FFFFFF")
        title_label.pack(pady=20)

        # 선택된 사진 수 표시
        count_label = tk.Label(format_dialog, text=f"선택된 사진: {len(selected_indices)}개",
                              font=("Pretendard", 14), bg="#34495E", fg="#FFD700")
        count_label.pack(pady=10)

        # 저장 형식 선택
        format_frame = tk.Frame(format_dialog, bg="#34495E")
        format_frame.pack(pady=20)

        self.selected_format = tk.StringVar(value="zip")

        formats = [
            ("ZIP 압축 파일 (.zip)", "zip"),
            ("폴더로 복사", "folder"),
            ("Excel 파일 (.xlsx)", "excel"),
            ("CSV 파일 (.csv)", "csv")
        ]

        for i, (text, value) in enumerate(formats):
            rb = tk.Radiobutton(format_frame, text=text, variable=self.selected_format, value=value,
                               font=("Pretendard", 14), bg="#34495E", fg="#FFFFFF",
                               selectcolor="#3498DB", activebackground="#34495E")
            rb.pack(anchor="w", pady=5)

        # 설명
        desc_label = tk.Label(format_dialog, 
                             text="• ZIP: 사진들을 압축 파일로 저장\n"
                                  "• 폴더: 사진들을 폴더에 복사\n"
                                  "• Excel: 사진 정보를 엑셀 파일로 저장\n"
                                  "• CSV: 사진 정보를 CSV 파일로 저장",
                             font=("Pretendard", 12), bg="#34495E", fg="#BDC3C7",
                             justify="left")
        desc_label.pack(pady=20)

        # 버튼 프레임
        button_frame = tk.Frame(format_dialog, bg="#34495E")
        button_frame.pack(pady=20)

        # 확인 버튼
        ok_btn = tk.Button(button_frame, text="확인", command=lambda: self._proceed_save(selected_indices, format_dialog),
                          bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                          relief="raised", bd=3, width=10, height=2,
                          activebackground="#229954", activeforeground="#FFFFFF")
        ok_btn.pack(side="left", padx=10)

        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="취소", command=format_dialog.destroy,
                              bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                              relief="raised", bd=3, width=10, height=2,
                              activebackground="#7F8C8D", activeforeground="#FFFFFF")
        cancel_btn.pack(side="left", padx=10)

    def _proceed_save(self, selected_indices, format_dialog):
        """선택된 형식으로 저장 진행"""
        format_dialog.destroy()
        
        selected_format = self.selected_format.get()
        
        if selected_format == "zip":
            self._save_as_zip(selected_indices)
        elif selected_format == "folder":
            self._save_as_folder(selected_indices)
        elif selected_format == "excel":
            self._save_as_excel(selected_indices)
        elif selected_format == "csv":
            self._save_as_csv(selected_indices)

    def _save_as_zip(self, selected_indices):
        """ZIP 파일로 저장"""
        from tkinter import filedialog
        import zipfile
        
        # 저장 경로 선택
        filename = filedialog.asksaveasfilename(
            title="ZIP 파일 저장",
            defaultextension=".zip",
            filetypes=[("ZIP 파일", "*.zip"), ("모든 파일", "*.*")],
            parent=self.dialog
        )
        
        if not filename:
            return
            
        try:
            with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for index in selected_indices:
                    item = self.photos[index]
                    if len(item) == 3:
                        filepath, dt, name = item
                    else:
                        filepath, dt = item
                        name = None
                    
                    # 이미지 파일 저장
                    if name:
                        arcname = f"safety_{name}_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                    else:
                        arcname = f"safety_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    zipf.write(filepath, arcname)
                    
                    # 해시 파일도 함께 저장
                    hash_filepath = filepath + ".hash"
                    if os.path.exists(hash_filepath):
                        hash_arcname = arcname + ".hash"
                        zipf.write(hash_filepath, hash_arcname)
            
            from tkinter import messagebox
            messagebox.showinfo("저장 완료", f"ZIP 파일이 저장되었습니다.\n\n경로: {filename}", parent=self.dialog)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"ZIP 파일 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _save_as_folder(self, selected_indices):
        """폴더로 복사"""
        from tkinter import filedialog
        
        # 저장 폴더 선택
        folder_path = filedialog.askdirectory(
            title="저장 폴더 선택",
            parent=self.dialog
        )
        
        if not folder_path:
            return
            
        try:
            import shutil
            copied_count = 0
            
            for index in selected_indices:
                item = self.photos[index]
                if len(item) == 3:
                    filepath, dt, name = item
                else:
                    filepath, dt = item
                    name = None
                
                # 이미지 파일 복사
                if name:
                    filename = f"safety_{name}_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                else:
                    filename = f"safety_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                
                dest_path = os.path.join(folder_path, filename)
                shutil.copy2(filepath, dest_path)
                copied_count += 1
                
                # 해시 파일도 함께 복사
                hash_filepath = filepath + ".hash"
                if os.path.exists(hash_filepath):
                    hash_filename = filename + ".hash"
                    hash_dest_path = os.path.join(folder_path, hash_filename)
                    shutil.copy2(hash_filepath, hash_dest_path)
            
            from tkinter import messagebox
            messagebox.showinfo("복사 완료", f"{copied_count}개의 사진과 해시 파일이 복사되었습니다.\n\n경로: {folder_path}", parent=self.dialog)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"폴더 복사 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _save_as_excel(self, selected_indices):
        """Excel 파일로 저장"""
        from tkinter import filedialog
        
        # 저장 경로 선택
        filename = filedialog.asksaveasfilename(
            title="Excel 파일 저장",
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx"), ("모든 파일", "*.*")],
            parent=self.dialog
        )
        
        if not filename:
            return
            
        try:
            import pandas as pd
            
            # 데이터 준비
            data = []
            for index in selected_indices:
                item = self.photos[index]
                if len(item) == 3:
                    filepath, dt, name = item
                else:
                    filepath, dt = item
                    name = None
                
                data.append({
                    '번호': index + 1,
                    '촬영일시': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    '이름': name or '미상',
                    '파일명': os.path.basename(filepath),
                    '파일경로': filepath,
                    '년도': dt.year,
                    '월': dt.month,
                    '일': dt.day,
                    '시간': dt.strftime('%H:%M:%S')
                })
            
            # DataFrame 생성 및 저장
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            
            from tkinter import messagebox
            messagebox.showinfo("저장 완료", f"Excel 파일이 저장되었습니다.\n\n경로: {filename}", parent=self.dialog)
            
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror("오류", "Excel 저장을 위해 pandas와 openpyxl 라이브러리가 필요합니다.\n\npip install pandas openpyxl", parent=self.dialog)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"Excel 파일 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)

    def _save_as_csv(self, selected_indices):
        """CSV 파일로 저장"""
        from tkinter import filedialog
        
        # 저장 경로 선택
        filename = filedialog.asksaveasfilename(
            title="CSV 파일 저장",
            defaultextension=".csv",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
            parent=self.dialog
        )
        
        if not filename:
            return
            
        try:
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['번호', '촬영일시', '이름', '파일명', '파일경로', '년도', '월', '일', '시간']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for index in selected_indices:
                    item = self.photos[index]
                    if len(item) == 3:
                        filepath, dt, name = item
                    else:
                        filepath, dt = item
                        name = None
                    
                    writer.writerow({
                        '번호': index + 1,
                        '촬영일시': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        '이름': name or '미상',
                        '파일명': os.path.basename(filepath),
                        '파일경로': filepath,
                        '년도': dt.year,
                        '월': dt.month,
                        '일': dt.day,
                        '시간': dt.strftime('%H:%M:%S')
                    })
            
            from tkinter import messagebox
            messagebox.showinfo("저장 완료", f"CSV 파일이 저장되었습니다.\n\n경로: {filename}", parent=self.dialog)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"CSV 파일 저장 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog)
            
    def _show_save_complete_dialog(self, filename, folder_path, files_info):
        """저장 완료 다이얼로그 표시 (디렉토리, 파일명, 확인 버튼)"""
        # 다이얼로그 생성
        save_dialog = tk.Toplevel(self.dialog)
        save_dialog.title("저장 완료")
        save_dialog.configure(bg="#2C3E50")
        save_dialog.transient(self.dialog)
        save_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 600
        dialog_height = 320
        save_dialog.geometry(f"{dialog_width}x{dialog_height}")
        save_dialog.update_idletasks()
        x = (save_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (save_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        save_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        save_dialog.attributes("-topmost", True)
        save_dialog.focus_force()

        # 제목 (체크 아이콘)
        title_frame = tk.Frame(save_dialog, bg="#2C3E50")
        title_frame.pack(pady=20)

        title_label = tk.Label(title_frame, text="✅ 저장 완료",
                              font=("Pretendard", 22, "bold"), bg="#2C3E50", fg="#27AE60")
        title_label.pack()

        # 정보 프레임
        info_frame = tk.Frame(save_dialog, bg="#34495E", relief="raised", bd=2)
        info_frame.pack(fill="x", padx=30, pady=10)

        # 저장 디렉토리
        dir_frame = tk.Frame(info_frame, bg="#34495E")
        dir_frame.pack(fill="x", padx=15, pady=(15, 5))

        tk.Label(dir_frame, text="저장 위치:", font=("Pretendard", 12, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(dir_frame, text=folder_path, font=("Pretendard", 12),
                bg="#34495E", fg="#FFFFFF", wraplength=450, justify="left").pack(side="left", padx=10)

        # 파일명
        file_frame = tk.Frame(info_frame, bg="#34495E")
        file_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(file_frame, text="파일명:", font=("Pretendard", 12, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(file_frame, text=filename, font=("Pretendard", 12),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 저장 내용
        content_frame = tk.Frame(info_frame, bg="#34495E")
        content_frame.pack(fill="x", padx=15, pady=(5, 15))

        tk.Label(content_frame, text="저장 내용:", font=("Pretendard", 12, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(content_frame, text=files_info, font=("Pretendard", 12),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 버튼 프레임
        button_frame = tk.Frame(save_dialog, bg="#2C3E50")
        button_frame.pack(pady=25)

        # 확인 버튼만
        ok_btn = tk.Button(button_frame, text="확인", command=save_dialog.destroy,
                          bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                          relief="raised", bd=3, width=12, height=2,
                          activebackground="#229954", activeforeground="#FFFFFF")
        ok_btn.pack()

        # 확인 버튼에 포커스
        ok_btn.focus_set()

        # Enter 키로 닫기
        save_dialog.bind("<Return>", lambda e: save_dialog.destroy())
        save_dialog.bind("<Escape>", lambda e: save_dialog.destroy())

    def _open_safety_photos_folder(self):
        """안전교육 사진 저장 폴더 열기"""
        try:
            import subprocess
            import platform
            
            # safety_photos 폴더 경로 (프로그램 설치 디렉토리 기준)
            install_dir = get_base_dir()
            safety_photos_dir = os.path.join(install_dir, "safety_photos")
            
            # 폴더가 없으면 생성
            if not os.path.exists(safety_photos_dir):
                os.makedirs(safety_photos_dir, exist_ok=True)
            
            # 운영체제별 파일 탐색기 열기
            if platform.system() == "Windows":
                # Windows에서는 os.startfile 사용 (더 안정적)
                os.startfile(safety_photos_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", safety_photos_dir], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", safety_photos_dir], check=True)
                
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"폴더를 열 수 없습니다:\n{str(e)}", parent=self.dialog)
            
    def _show_export_dialog(self, selected_indices):
        """기록 반출 다이얼로그 표시 (반출사유/반출자 입력)"""
        from tkinter import filedialog
        from datetime import datetime as dt_module

        # 반출 다이얼로그 생성
        export_dialog = tk.Toplevel(self.dialog)
        export_dialog.title("안전교육 기록 반출")
        export_dialog.configure(bg="#2C3E50")
        export_dialog.transient(self.dialog)
        export_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 650
        dialog_height = 520
        export_dialog.geometry(f"{dialog_width}x{dialog_height}")
        export_dialog.update_idletasks()
        x = (export_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (export_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        export_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        export_dialog.attributes("-topmost", True)
        export_dialog.focus_force()

        # 제목
        title_frame = tk.Frame(export_dialog, bg="#34495E", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        title_label = tk.Label(title_frame, text="📤 안전교육 기록 반출",
                              font=("Pretendard", 18, "bold"), bg="#34495E", fg="#FFFFFF")
        title_label.pack(expand=True)

        # 메인 프레임
        main_frame = tk.Frame(export_dialog, bg="#2C3E50")
        main_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # 선택된 사진 수 표시
        info_frame = tk.Frame(main_frame, bg="#34495E", relief="raised", bd=2)
        info_frame.pack(fill="x", pady=(0, 15))

        tk.Label(info_frame, text=f"선택된 사진: {len(selected_indices)}개",
                font=("Pretendard", 14, "bold"), bg="#34495E", fg="#FFD700").pack(pady=10)

        # 반출 정보 프레임
        form_frame = tk.Frame(main_frame, bg="#2C3E50")
        form_frame.pack(fill="x", pady=10)

        # 반출 목적
        purpose_frame = tk.Frame(form_frame, bg="#2C3E50")
        purpose_frame.pack(fill="x", pady=8)

        tk.Label(purpose_frame, text="반출 목적:", font=("Pretendard", 12, "bold"),
                bg="#2C3E50", fg="#FFFFFF", width=12, anchor="w").pack(side="left")

        purpose_var = tk.StringVar()
        purpose_entry = tk.Entry(purpose_frame, textvariable=purpose_var,
                                font=("Pretendard", 12), width=40)
        purpose_entry.pack(side="left", padx=10, fill="x", expand=True)

        # 반출자
        exporter_frame = tk.Frame(form_frame, bg="#2C3E50")
        exporter_frame.pack(fill="x", pady=8)

        tk.Label(exporter_frame, text="반출자:", font=("Pretendard", 12, "bold"),
                bg="#2C3E50", fg="#FFFFFF", width=12, anchor="w").pack(side="left")

        exporter_var = tk.StringVar()
        exporter_entry = tk.Entry(exporter_frame, textvariable=exporter_var,
                                 font=("Pretendard", 12), width=40)
        exporter_entry.pack(side="left", padx=10, fill="x", expand=True)

        # 저장 위치
        path_frame = tk.Frame(form_frame, bg="#2C3E50")
        path_frame.pack(fill="x", pady=8)

        tk.Label(path_frame, text="저장 위치:", font=("Pretendard", 12, "bold"),
                bg="#2C3E50", fg="#FFFFFF", width=12, anchor="w").pack(side="left")

        # 기본 저장 경로
        current_datetime = dt_module.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"safety_export_{current_datetime}.zip"
        # 기본 반출 디렉토리: 설치 경로/export
        export_dir = os.path.join(get_base_dir(), "export")
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
        default_path = os.path.join(export_dir, default_filename)

        path_var = tk.StringVar(value=default_path)
        path_entry = tk.Entry(path_frame, textvariable=path_var,
                             font=("Pretendard", 11), width=35)
        path_entry.pack(side="left", padx=10, fill="x", expand=True)

        def browse_path():
            export_dialog.attributes("-topmost", False)
            filepath = filedialog.asksaveasfilename(
                title="반출 파일 저장",
                defaultextension=".zip",
                filetypes=[("ZIP 파일", "*.zip"), ("모든 파일", "*.*")],
                initialfile=default_filename,
                initialdir=export_dir,
                parent=export_dialog
            )
            export_dialog.attributes("-topmost", True)
            if filepath:
                path_var.set(filepath)

        browse_btn = tk.Button(path_frame, text="찾아보기",
                              command=browse_path,
                              bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 10),
                              relief="raised", bd=2)
        browse_btn.pack(side="left", padx=5)

        # 안내 메시지
        info_label = tk.Label(main_frame,
                             text="반출된 파일에는 사진, 해시 파일, CSV 목록이 포함됩니다.\n"
                                  "반출 이력은 '반출 이력' 버튼에서 확인할 수 있습니다.",
                             font=("Pretendard", 10), bg="#2C3E50", fg="#95A5A6",
                             justify="center")
        info_label.pack(pady=15)

        # 버튼 프레임
        button_frame = tk.Frame(main_frame, bg="#2C3E50")
        button_frame.pack(pady=20)

        def show_export_warning(title, message):
            """기록 반출 다이얼로그용 커스텀 경고"""
            warn_dlg = tk.Toplevel(export_dialog)
            warn_dlg.title(title)
            warn_dlg.configure(bg="#2C3E50")
            warn_dlg.transient(export_dialog)
            warn_dlg.grab_set()
            warn_dlg.geometry("380x150")
            warn_dlg.update_idletasks()
            x = (warn_dlg.winfo_screenwidth() // 2) - 190
            y = (warn_dlg.winfo_screenheight() // 2) - 75
            warn_dlg.geometry(f"380x150+{x}+{y}")
            warn_dlg.attributes("-topmost", True)
            warn_dlg.focus_force()

            tk.Label(warn_dlg, text=f"⚠️ {message}",
                    font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF").pack(expand=True)
            tk.Button(warn_dlg, text="확인", command=warn_dlg.destroy,
                     bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                     width=8).pack(pady=15)
            warn_dlg.bind("<Return>", lambda e: warn_dlg.destroy())
            warn_dlg.bind("<Escape>", lambda e: warn_dlg.destroy())

        def show_export_error(title, message):
            """기록 반출 다이얼로그용 커스텀 오류"""
            err_dlg = tk.Toplevel(export_dialog)
            err_dlg.title(title)
            err_dlg.configure(bg="#2C3E50")
            err_dlg.transient(export_dialog)
            err_dlg.grab_set()
            err_dlg.geometry("400x180")
            err_dlg.update_idletasks()
            x = (err_dlg.winfo_screenwidth() // 2) - 200
            y = (err_dlg.winfo_screenheight() // 2) - 90
            err_dlg.geometry(f"400x180+{x}+{y}")
            err_dlg.attributes("-topmost", True)
            err_dlg.focus_force()

            title_frm = tk.Frame(err_dlg, bg="#E74C3C")
            title_frm.pack(fill="x")
            tk.Label(title_frm, text=f"❌ {title}",
                    font=("Pretendard", 14, "bold"), bg="#E74C3C", fg="#FFFFFF").pack(pady=8)

            tk.Label(err_dlg, text=message,
                    font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF", wraplength=350).pack(expand=True, pady=10)
            tk.Button(err_dlg, text="확인", command=err_dlg.destroy,
                     bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                     width=8).pack(pady=10)
            err_dlg.bind("<Return>", lambda e: err_dlg.destroy())
            err_dlg.bind("<Escape>", lambda e: err_dlg.destroy())

        def do_export():
            # 입력값 검증
            purpose = purpose_var.get().strip()
            exporter = exporter_var.get().strip()
            export_path = path_var.get().strip()

            if not purpose:
                show_export_warning("입력 필요", "반출 목적을 입력하세요.")
                return

            if not exporter:
                show_export_warning("입력 필요", "반출자를 입력하세요.")
                return

            if not export_path:
                show_export_warning("입력 필요", "저장 위치를 지정하세요.")
                return

            # 저장 디렉토리 확인
            save_dir = os.path.dirname(export_path)
            if save_dir and not os.path.exists(save_dir):
                # 커스텀 확인 다이얼로그 (예/아니오)
                confirm_result = [False]

                confirm_dlg = tk.Toplevel(export_dialog)
                confirm_dlg.title("확인")
                confirm_dlg.configure(bg="#2C3E50")
                confirm_dlg.transient(export_dialog)
                confirm_dlg.grab_set()
                confirm_dlg.geometry("450x180")
                confirm_dlg.update_idletasks()
                x = (confirm_dlg.winfo_screenwidth() // 2) - 225
                y = (confirm_dlg.winfo_screenheight() // 2) - 90
                confirm_dlg.geometry(f"450x180+{x}+{y}")
                confirm_dlg.attributes("-topmost", True)
                confirm_dlg.focus_force()

                # 제목
                title_frm = tk.Frame(confirm_dlg, bg="#E67E22")
                title_frm.pack(fill="x")
                tk.Label(title_frm, text="❓ 폴더 생성 확인",
                        font=("Pretendard", 14, "bold"), bg="#E67E22", fg="#FFFFFF").pack(pady=10)

                # 메시지
                tk.Label(confirm_dlg, text=f"저장 폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n{save_dir}",
                        font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF", justify="center", wraplength=400).pack(expand=True, pady=5)

                # 버튼 프레임
                btn_frm = tk.Frame(confirm_dlg, bg="#2C3E50")
                btn_frm.pack(pady=15)

                def on_yes():
                    confirm_result[0] = True
                    confirm_dlg.destroy()

                def on_no():
                    confirm_result[0] = False
                    confirm_dlg.destroy()

                tk.Button(btn_frm, text="예", command=on_yes,
                         bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(side="left", padx=10)
                tk.Button(btn_frm, text="아니오", command=on_no,
                         bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(side="left", padx=10)

                confirm_dlg.bind("<Return>", lambda e: on_yes())
                confirm_dlg.bind("<Escape>", lambda e: on_no())

                export_dialog.wait_window(confirm_dlg)

                if not confirm_result[0]:
                    return
                try:
                    os.makedirs(save_dir, exist_ok=True)
                except Exception as e:
                    show_export_error("오류", f"폴더 생성 실패:\n{e}")
                    return

            # 반출 실행
            export_dialog.destroy()
            self._execute_export(selected_indices, purpose, exporter, export_path)

        # 반출 실행 버튼
        export_btn = tk.Button(button_frame, text="반출 실행",
                              command=do_export,
                              bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                              relief="raised", bd=3, width=12, height=2,
                              activebackground="#229954", activeforeground="#FFFFFF")
        export_btn.pack(side="left", padx=10)

        # 취소 버튼
        cancel_btn = tk.Button(button_frame, text="취소",
                              command=export_dialog.destroy,
                              bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                              relief="raised", bd=3, width=12, height=2,
                              activebackground="#7F8C8D", activeforeground="#FFFFFF")
        cancel_btn.pack(side="left", padx=10)

        # ESC 키로 닫기
        export_dialog.bind("<Escape>", lambda e: export_dialog.destroy())
        # Enter 키로 실행
        export_dialog.bind("<Return>", lambda e: do_export())

        # 첫 번째 입력란에 포커스
        purpose_entry.focus_set()

    def _execute_export(self, selected_indices, purpose, exporter, export_path):
        """기록 반출 실행"""
        import zipfile
        import csv
        import tempfile
        import hashlib
        from datetime import datetime as dt_module

        try:
            # 현재 날짜와 시간
            current_datetime = dt_module.now()
            export_id = f"EXP_{current_datetime.strftime('%Y%m%d_%H%M%S')}"

            # 임시 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                # 데이터 준비
                data = []
                for i, index in enumerate(selected_indices):
                    item = self.photos[index]
                    if len(item) == 3:
                        filepath, dt, name = item
                    else:
                        filepath, dt = item
                        name = None

                    # 해시 파일에서 해시값 읽기
                    hash_value = ""
                    hash_filepath = filepath + ".hash"
                    if os.path.exists(hash_filepath):
                        try:
                            with open(hash_filepath, 'r', encoding='utf-8') as f:
                                hash_content = f.read()
                                for line in hash_content.split('\n'):
                                    if line.startswith('해시값:'):
                                        hash_value = line.replace('해시값:', '').strip()
                                        break
                        except:
                            hash_value = "읽기 실패"

                    data.append({
                        '번호': i + 1,
                        '촬영일시': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        '이름': name or '미상',
                        '파일명': os.path.basename(filepath),
                        '파일경로': filepath,
                        '년도': dt.year,
                        '월': dt.month,
                        '일': dt.day,
                        '시간': dt.strftime('%H:%M:%S'),
                        '해시값': hash_value
                    })

                # CSV 파일 생성
                csv_filename = f"안전교육사진목록_{current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
                csv_filepath = os.path.join(temp_dir, csv_filename)

                with open(csv_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['번호', '촬영일시', '이름', '파일명', '파일경로', '년도', '월', '일', '시간', '해시값']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in data:
                        writer.writerow(row)

                # XLSX 파일 생성
                xlsx_filename = f"안전교육사진목록_{current_datetime.strftime('%Y%m%d_%H%M%S')}.xlsx"
                xlsx_filepath = os.path.join(temp_dir, xlsx_filename)
                xlsx_created = False

                try:
                    import pandas as pd
                    df = pd.DataFrame(data)
                    df.to_excel(xlsx_filepath, index=False, engine='openpyxl')
                    xlsx_created = True
                except ImportError:
                    pass

                # 반출 정보 파일 생성
                export_info_filename = "export_info.txt"
                export_info_filepath = os.path.join(temp_dir, export_info_filename)

                with open(export_info_filepath, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("안전교육 기록 반출 정보\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"반출 ID: {export_id}\n")
                    f.write(f"반출 일시: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"반출 목적: {purpose}\n")
                    f.write(f"반출자: {exporter}\n")
                    f.write(f"반출 파일 수: {len(selected_indices)}개\n\n")
                    f.write("-" * 60 + "\n")
                    f.write("포함된 파일 목록:\n")
                    f.write("-" * 60 + "\n")
                    for row in data:
                        f.write(f"  {row['번호']}. {row['파일명']} ({row['촬영일시']})\n")

                # ZIP 파일 생성
                with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # CSV 파일 추가
                    zipf.write(csv_filepath, csv_filename)

                    # XLSX 파일 추가 (생성된 경우)
                    if xlsx_created:
                        zipf.write(xlsx_filepath, xlsx_filename)

                    # 반출 정보 파일 추가
                    zipf.write(export_info_filepath, export_info_filename)

                    # 선택된 이미지 파일들과 해시 파일들 추가
                    for index in selected_indices:
                        item = self.photos[index]
                        if len(item) == 3:
                            filepath, dt, name = item
                        else:
                            filepath, dt = item
                            name = None

                        # 이미지 파일명 생성
                        if name:
                            image_filename = f"safety_{name}_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"
                        else:
                            image_filename = f"safety_{dt.strftime('%Y%m%d_%H%M%S')}.jpg"

                        # 이미지 파일 추가
                        zipf.write(filepath, f"photos/{image_filename}")

                        # 해시 파일도 함께 추가
                        hash_filepath = filepath + ".hash"
                        if os.path.exists(hash_filepath):
                            hash_filename = image_filename + ".hash"
                            zipf.write(hash_filepath, f"photos/{hash_filename}")

            # 아카이브 해시 계산
            archive_hash = ""
            try:
                with open(export_path, 'rb') as f:
                    archive_hash = hashlib.sha256(f.read()).hexdigest()
            except:
                pass

            # 반출 이력 저장
            self._save_export_history(export_id, current_datetime, purpose, exporter,
                                     export_path, len(selected_indices), archive_hash)

            # 저장 완료 다이얼로그 표시
            files_info = f"{len(selected_indices)}개 이미지 + 해시파일 + CSV목록"
            if xlsx_created:
                files_info += " + XLSX목록"

            self._show_export_complete_dialog(export_id, os.path.basename(export_path),
                                             os.path.dirname(export_path), files_info,
                                             purpose, exporter)

        except Exception as e:
            self._show_custom_error("기록 반출 오류", f"기록 반출 중 오류가 발생했습니다:\n{str(e)}")

    def _save_export_history(self, export_id, export_datetime, purpose, exporter,
                            archive_path, total_records, archive_hash):
        """반출 이력 저장"""
        import json

        try:
            # 반출 이력 파일 경로
            install_dir = get_base_dir()
            history_dir = os.path.join(install_dir, "safety_photos", ".export_history")
            os.makedirs(history_dir, exist_ok=True)

            history_file = os.path.join(history_dir, "export_history.json")

            # 기존 이력 로드
            history = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []

            # 새 반출 기록 추가
            record = {
                "export_id": export_id,
                "export_datetime": export_datetime.isoformat(),
                "purpose": purpose,
                "exported_by": exporter,
                "archive_path": archive_path,
                "total_records": total_records,
                "archive_hash": archive_hash
            }
            history.insert(0, record)  # 최신순으로 추가

            # 이력 저장
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[SafetyPhotoViewer] 반출 이력 저장 실패: {e}")

    def _show_export_complete_dialog(self, export_id, filename, folder_path, files_info, purpose, exporter):
        """반출 완료 다이얼로그 표시"""
        # 다이얼로그 생성
        complete_dialog = tk.Toplevel(self.dialog)
        complete_dialog.title("반출 완료")
        complete_dialog.configure(bg="#2C3E50")
        complete_dialog.transient(self.dialog)
        complete_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 650
        dialog_height = 420
        complete_dialog.geometry(f"{dialog_width}x{dialog_height}")
        complete_dialog.update_idletasks()
        x = (complete_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (complete_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        complete_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        complete_dialog.attributes("-topmost", True)
        complete_dialog.focus_force()

        # 제목
        title_frame = tk.Frame(complete_dialog, bg="#2C3E50")
        title_frame.pack(pady=20)

        title_label = tk.Label(title_frame, text="✅ 기록 반출 완료",
                              font=("Pretendard", 22, "bold"), bg="#2C3E50", fg="#27AE60")
        title_label.pack()

        # 정보 프레임
        info_frame = tk.Frame(complete_dialog, bg="#34495E", relief="raised", bd=2)
        info_frame.pack(fill="x", padx=30, pady=10)

        # 반출 ID
        id_frame = tk.Frame(info_frame, bg="#34495E")
        id_frame.pack(fill="x", padx=15, pady=(15, 5))
        tk.Label(id_frame, text="반출 ID:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(id_frame, text=export_id, font=("Pretendard", 11),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 저장 위치
        dir_frame = tk.Frame(info_frame, bg="#34495E")
        dir_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(dir_frame, text="저장 위치:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(dir_frame, text=folder_path, font=("Pretendard", 10),
                bg="#34495E", fg="#FFFFFF", wraplength=450, justify="left").pack(side="left", padx=10)

        # 파일명
        file_frame = tk.Frame(info_frame, bg="#34495E")
        file_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(file_frame, text="파일명:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(file_frame, text=filename, font=("Pretendard", 11),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 저장 내용
        content_frame = tk.Frame(info_frame, bg="#34495E")
        content_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(content_frame, text="저장 내용:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(content_frame, text=files_info, font=("Pretendard", 11),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 반출 목적
        purpose_frame = tk.Frame(info_frame, bg="#34495E")
        purpose_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(purpose_frame, text="반출 목적:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(purpose_frame, text=purpose, font=("Pretendard", 11),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 반출자
        exporter_frame = tk.Frame(info_frame, bg="#34495E")
        exporter_frame.pack(fill="x", padx=15, pady=(5, 15))
        tk.Label(exporter_frame, text="반출자:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(exporter_frame, text=exporter, font=("Pretendard", 11),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 버튼 프레임
        button_frame = tk.Frame(complete_dialog, bg="#2C3E50")
        button_frame.pack(pady=25)

        # 확인 버튼
        ok_btn = tk.Button(button_frame, text="확인", command=complete_dialog.destroy,
                          bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                          relief="raised", bd=3, width=12, height=2,
                          activebackground="#229954", activeforeground="#FFFFFF")
        ok_btn.pack()

        # 확인 버튼에 포커스
        ok_btn.focus_set()

        # Enter/ESC 키로 닫기
        complete_dialog.bind("<Return>", lambda e: complete_dialog.destroy())
        complete_dialog.bind("<Escape>", lambda e: complete_dialog.destroy())

    def _show_export_history(self):
        """반출 이력 및 검색 다이얼로그 표시 (미리보기 및 보고서 기능 포함)"""
        import json
        from datetime import datetime as dt_module
        from tkinter import filedialog

        # 반출 이력 다이얼로그 생성
        history_dialog = tk.Toplevel(self.dialog)
        history_dialog.title("반출 이력 조회")
        history_dialog.configure(bg="#2C3E50")
        history_dialog.transient(self.dialog)
        history_dialog.grab_set()

        # 창 크기 및 중앙 배치 (확장)
        dialog_width = 1400
        dialog_height = 750
        history_dialog.geometry(f"{dialog_width}x{dialog_height}")
        history_dialog.update_idletasks()
        x = (history_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (history_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        history_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        history_dialog.attributes("-topmost", True)

        # 제목
        title_frame = tk.Frame(history_dialog, bg="#34495E", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        title_label = tk.Label(title_frame, text="📋 반출 이력 조회",
                              font=("Pretendard", 18, "bold"), bg="#34495E", fg="#FFFFFF")
        title_label.pack(expand=True)

        # 검색 프레임
        search_frame = tk.Frame(history_dialog, bg="#2C3E50")
        search_frame.pack(fill="x", padx=20, pady=10)

        # 기간 검색
        period_frame = tk.Frame(search_frame, bg="#2C3E50")
        period_frame.pack(side="left", padx=10)

        tk.Label(period_frame, text="반출 기간:",
                font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF").pack(side="left", padx=5)

        date_from_var = tk.StringVar(value="")
        date_from_entry = tk.Entry(period_frame, textvariable=date_from_var,
                                  font=("Pretendard", 11), width=12)
        date_from_entry.pack(side="left", padx=3)
        date_from_entry.insert(0, "YYYY-MM-DD")
        date_from_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(date_from_entry, "YYYY-MM-DD"))

        tk.Label(period_frame, text="~",
                font=("Pretendard", 11, "bold"), bg="#2C3E50", fg="#FFFFFF").pack(side="left", padx=3)

        date_to_var = tk.StringVar(value="")
        date_to_entry = tk.Entry(period_frame, textvariable=date_to_var,
                                font=("Pretendard", 11), width=12)
        date_to_entry.pack(side="left", padx=3)
        date_to_entry.insert(0, "YYYY-MM-DD")
        date_to_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(date_to_entry, "YYYY-MM-DD"))

        # 반출자 검색
        exporter_search_frame = tk.Frame(search_frame, bg="#2C3E50")
        exporter_search_frame.pack(side="left", padx=20)

        tk.Label(exporter_search_frame, text="반출자:",
                font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF").pack(side="left", padx=5)

        exporter_search_var = tk.StringVar()
        exporter_search_entry = tk.Entry(exporter_search_frame, textvariable=exporter_search_var,
                                        font=("Pretendard", 11), width=15)
        exporter_search_entry.pack(side="left", padx=3)

        # 검색 버튼
        def do_search():
            search_history(date_from_entry.get(), date_to_entry.get(), exporter_search_var.get())

        search_btn = tk.Button(search_frame, text="🔍 검색", command=do_search,
                              bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                              relief="raised", bd=2, width=8)
        search_btn.pack(side="left", padx=10)

        # 전체 보기 버튼
        def show_all():
            date_from_entry.delete(0, tk.END)
            date_from_entry.insert(0, "YYYY-MM-DD")
            date_to_entry.delete(0, tk.END)
            date_to_entry.insert(0, "YYYY-MM-DD")
            exporter_search_var.set("")
            load_history()
            clear_preview()

        all_btn = tk.Button(search_frame, text="전체", command=show_all,
                           bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                           relief="raised", bd=2, width=8)
        all_btn.pack(side="left", padx=5)

        # 메인 컨테이너 (좌우 분할)
        main_container = tk.Frame(history_dialog, bg="#2C3E50")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # 좌측: 이력 목록 (55%)
        left_frame = tk.Frame(main_container, bg="#2C3E50")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 이력 목록 (Treeview)
        columns = ("export_id", "datetime", "purpose", "exporter", "records")
        history_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=18)

        # 스타일 설정
        style = ttk.Style()
        style.configure("Treeview", font=("Pretendard", 10), rowheight=28)
        style.configure("Treeview.Heading", font=("Pretendard", 11, "bold"))

        # 컬럼 설정
        history_tree.heading("export_id", text="반출 ID")
        history_tree.heading("datetime", text="반출 일시")
        history_tree.heading("purpose", text="반출 목적")
        history_tree.heading("exporter", text="반출자")
        history_tree.heading("records", text="파일수")

        history_tree.column("export_id", width=180, anchor="w")
        history_tree.column("datetime", width=140, anchor="center")
        history_tree.column("purpose", width=180, anchor="w")
        history_tree.column("exporter", width=80, anchor="center")
        history_tree.column("records", width=60, anchor="center")

        # 스크롤바
        scrollbar_y = ttk.Scrollbar(left_frame, orient="vertical", command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar_y.set)

        history_tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # 우측: 미리보기 패널 (45%)
        right_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=2, width=480)
        right_frame.pack(side="right", fill="both", padx=(10, 0))
        right_frame.pack_propagate(False)

        # 미리보기 제목
        preview_title = tk.Label(right_frame, text="📄 반출 상세 정보",
                                font=("Pretendard", 14, "bold"), bg="#34495E", fg="#FFD700")
        preview_title.pack(pady=10)

        # 미리보기 텍스트
        preview_text = tk.Text(right_frame, font=("Pretendard", 10), wrap="word",
                              bg="#2C3E50", fg="#FFFFFF", state="disabled",
                              width=50, height=22, relief="sunken", bd=2)
        preview_scroll = tk.Scrollbar(right_frame, orient="vertical", command=preview_text.yview)
        preview_text.configure(yscrollcommand=preview_scroll.set)

        preview_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        preview_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

        # 현재 선택된 레코드 저장용
        current_record = [None]

        # 미리보기 업데이트 함수
        def update_preview(record):
            current_record[0] = record
            archive_path = record.get("archive_path", "-")
            file_exists = os.path.exists(archive_path) if archive_path != "-" else False

            # ZIP 파일에서 파일 목록 추출
            file_count = 0
            file_list = []
            if archive_path != "-" and file_exists:
                try:
                    import zipfile
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        file_list = zf.namelist()
                        file_count = len(file_list)
                except:
                    pass

            preview_content = f"""반출 ID
  {record.get('export_id', '-')}

반출 일시
  {record.get('export_datetime', '-')}

반출자
  {record.get('exported_by', '-')}

반출 목적
  {record.get('purpose', '-')}

파일 수
  {record.get('total_records', 0)}개

저장 경로
  {archive_path}

파일 상태
  {'✅ 존재함' if file_exists else '❌ 파일 없음'}

아카이브 해시 (SHA-256)
  {record.get('archive_hash', '-')}

포함 파일 ({file_count}개)
"""
            # 파일 목록 추가 (최대 10개)
            for i, fname in enumerate(file_list[:10]):
                preview_content += f"  • {fname}\n"
            if len(file_list) > 10:
                preview_content += f"  ... 외 {len(file_list) - 10}개 파일\n"

            preview_text.configure(state="normal")
            preview_text.delete(1.0, tk.END)
            preview_text.insert(1.0, preview_content)
            preview_text.configure(state="disabled")

        # 미리보기 초기화 함수
        def clear_preview():
            current_record[0] = None
            preview_text.configure(state="normal")
            preview_text.delete(1.0, tk.END)
            preview_text.insert(1.0, "항목을 선택하면 상세 정보가 표시됩니다.")
            preview_text.configure(state="disabled")

        # 이력 선택 이벤트
        def on_history_select(event=None):
            selection = history_tree.selection()
            if not selection:
                clear_preview()
                return

            item = history_tree.item(selection[0])
            values = item.get("values", [])

            if len(values) >= 1:
                export_id = values[0]
                # 이력에서 해당 레코드 찾기
                install_dir = get_base_dir()
                history_file = os.path.join(install_dir, "safety_photos", ".export_history", "export_history.json")

                try:
                    if os.path.exists(history_file):
                        with open(history_file, 'r', encoding='utf-8') as f:
                            records = json.load(f)
                        for record in records:
                            if record.get("export_id") == export_id:
                                update_preview(record)
                                return
                except:
                    pass
                clear_preview()

        history_tree.bind("<<TreeviewSelect>>", on_history_select)

        # 이력 데이터 저장용
        all_records = []

        # 이력 로드 함수
        def load_history(records=None):
            nonlocal all_records
            # 기존 항목 삭제
            for item in history_tree.get_children():
                history_tree.delete(item)

            if records is None:
                # 반출 이력 파일 로드
                install_dir = get_base_dir()
                history_file = os.path.join(install_dir, "safety_photos", ".export_history", "export_history.json")

                records = []
                if os.path.exists(history_file):
                    try:
                        with open(history_file, 'r', encoding='utf-8') as f:
                            records = json.load(f)
                    except:
                        pass

            all_records = records

            for record in records:
                export_dt = record.get("export_datetime", "-")
                if export_dt and export_dt != "-":
                    try:
                        dt = dt_module.fromisoformat(export_dt)
                        export_dt = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                history_tree.insert(
                    "", "end",
                    values=(
                        record.get("export_id", "-"),
                        export_dt,
                        record.get("purpose", "-"),
                        record.get("exported_by", "-"),
                        record.get("total_records", 0)
                    )
                )

        # 검색 함수
        def search_history(date_from, date_to, exporter_query):
            # 반출 이력 파일 로드
            install_dir = get_base_dir()
            history_file = os.path.join(install_dir, "safety_photos", ".export_history", "export_history.json")

            records = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        records = json.load(f)
                except:
                    pass

            # 플레이스홀더 처리
            if date_from == "YYYY-MM-DD":
                date_from = ""
            if date_to == "YYYY-MM-DD":
                date_to = ""

            # 필터링
            filtered = []
            for record in records:
                export_dt_str = record.get("export_datetime", "")

                # 날짜 필터
                if date_from:
                    try:
                        export_date = export_dt_str[:10]  # YYYY-MM-DD 부분
                        if export_date < date_from:
                            continue
                    except:
                        pass

                if date_to:
                    try:
                        export_date = export_dt_str[:10]
                        if export_date > date_to:
                            continue
                    except:
                        pass

                # 반출자 필터
                if exporter_query:
                    if exporter_query.lower() not in record.get("exported_by", "").lower():
                        continue

                filtered.append(record)

            load_history(filtered)

            if not filtered:
                # 커스텀 검색 결과 없음 다이얼로그
                no_result_dlg = tk.Toplevel(history_dialog)
                no_result_dlg.title("검색 결과")
                no_result_dlg.configure(bg="#2C3E50")
                no_result_dlg.transient(history_dialog)
                no_result_dlg.grab_set()
                no_result_dlg.geometry("380x150")
                no_result_dlg.update_idletasks()
                x = (no_result_dlg.winfo_screenwidth() // 2) - 190
                y = (no_result_dlg.winfo_screenheight() // 2) - 75
                no_result_dlg.geometry(f"380x150+{x}+{y}")
                no_result_dlg.attributes("-topmost", True)
                no_result_dlg.focus_force()

                tk.Label(no_result_dlg, text="ℹ️ 검색 조건에 맞는 반출 이력이 없습니다.",
                        font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF").pack(expand=True)
                tk.Button(no_result_dlg, text="확인", command=no_result_dlg.destroy,
                         bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(pady=15)
                no_result_dlg.bind("<Return>", lambda e: no_result_dlg.destroy())
                no_result_dlg.bind("<Escape>", lambda e: no_result_dlg.destroy())

        # 버튼 프레임
        button_frame = tk.Frame(history_dialog, bg="#2C3E50")
        button_frame.pack(fill="x", padx=20, pady=10)

        # PDF 보고서 생성 함수
        def create_pdf_report():
            if current_record[0] is None:
                # 커스텀 경고 다이얼로그
                warn_dlg = tk.Toplevel(history_dialog)
                warn_dlg.title("알림")
                warn_dlg.configure(bg="#2C3E50")
                warn_dlg.transient(history_dialog)
                warn_dlg.grab_set()
                warn_dlg.geometry("380x150")
                warn_dlg.update_idletasks()
                x = (warn_dlg.winfo_screenwidth() // 2) - 190
                y = (warn_dlg.winfo_screenheight() // 2) - 75
                warn_dlg.geometry(f"380x150+{x}+{y}")
                warn_dlg.attributes("-topmost", True)
                warn_dlg.focus_force()

                tk.Label(warn_dlg, text="⚠️ 보고서를 만들 항목을 선택하세요.",
                        font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF").pack(expand=True)
                tk.Button(warn_dlg, text="확인", command=warn_dlg.destroy,
                         bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(pady=15)
                warn_dlg.bind("<Return>", lambda e: warn_dlg.destroy())
                warn_dlg.bind("<Escape>", lambda e: warn_dlg.destroy())
                return

            record = current_record[0]
            export_id = record.get("export_id", "export")

            # 기본 보고서 디렉토리: 설치 경로/report
            report_dir = os.path.join(get_base_dir(), "report")
            if not os.path.exists(report_dir):
                os.makedirs(report_dir, exist_ok=True)

            # 저장 경로 선택
            history_dialog.attributes("-topmost", False)
            history_dialog.update()

            default_filename = f"export_report_{export_id}.pdf"
            filepath = filedialog.asksaveasfilename(
                title="보고서 저장",
                defaultextension=".pdf",
                filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")],
                initialfile=default_filename,
                initialdir=report_dir,
                parent=history_dialog
            )

            history_dialog.attributes("-topmost", True)

            if not filepath:
                return

            # PDF 생성
            self._generate_pdf_report(record, filepath, history_dialog)

        # 보고서 만들기 버튼
        report_btn = tk.Button(button_frame, text="📄 보고서 만들기", command=create_pdf_report,
                              bg="#9B59B6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                              relief="raised", bd=2, width=14, height=2,
                              activebackground="#8E44AD", activeforeground="#FFFFFF")
        report_btn.pack(side="left", padx=5)

        # 이력 삭제 버튼
        def delete_selected():
            selection = history_tree.selection()
            if not selection:
                # 커스텀 경고 다이얼로그
                warn_dlg = tk.Toplevel(history_dialog)
                warn_dlg.title("알림")
                warn_dlg.configure(bg="#2C3E50")
                warn_dlg.transient(history_dialog)
                warn_dlg.grab_set()
                warn_dlg.geometry("350x150")
                warn_dlg.update_idletasks()
                x = (warn_dlg.winfo_screenwidth() // 2) - 175
                y = (warn_dlg.winfo_screenheight() // 2) - 75
                warn_dlg.geometry(f"350x150+{x}+{y}")
                warn_dlg.attributes("-topmost", True)
                warn_dlg.focus_force()

                tk.Label(warn_dlg, text="⚠️ 삭제할 항목을 선택하세요.",
                        font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF").pack(expand=True)
                tk.Button(warn_dlg, text="확인", command=warn_dlg.destroy,
                         bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(pady=15)
                warn_dlg.bind("<Return>", lambda e: warn_dlg.destroy())
                warn_dlg.bind("<Escape>", lambda e: warn_dlg.destroy())
                return

            item = history_tree.item(selection[0])
            values = item.get("values", [])
            export_id = values[0] if values else ""

            # 커스텀 확인 다이얼로그 (예/아니오)
            confirm_result = [False]  # 결과 저장용 리스트

            confirm_dlg = tk.Toplevel(history_dialog)
            confirm_dlg.title("확인")
            confirm_dlg.configure(bg="#2C3E50")
            confirm_dlg.transient(history_dialog)
            confirm_dlg.grab_set()
            confirm_dlg.geometry("450x200")
            confirm_dlg.update_idletasks()
            x = (confirm_dlg.winfo_screenwidth() // 2) - 225
            y = (confirm_dlg.winfo_screenheight() // 2) - 100
            confirm_dlg.geometry(f"450x200+{x}+{y}")
            confirm_dlg.attributes("-topmost", True)
            confirm_dlg.focus_force()

            # 제목
            title_frm = tk.Frame(confirm_dlg, bg="#E67E22")
            title_frm.pack(fill="x")
            tk.Label(title_frm, text="❓ 삭제 확인",
                    font=("Pretendard", 14, "bold"), bg="#E67E22", fg="#FFFFFF").pack(pady=10)

            # 메시지
            msg_frm = tk.Frame(confirm_dlg, bg="#2C3E50")
            msg_frm.pack(fill="both", expand=True, padx=20, pady=10)
            tk.Label(msg_frm, text=f"반출 이력을 삭제하시겠습니까?\n\n반출 ID: {export_id}\n\n(실제 파일은 삭제되지 않습니다)",
                    font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF", justify="center").pack(expand=True)

            # 버튼 프레임
            btn_frm = tk.Frame(confirm_dlg, bg="#2C3E50")
            btn_frm.pack(pady=15)

            def on_yes():
                confirm_result[0] = True
                confirm_dlg.destroy()

            def on_no():
                confirm_result[0] = False
                confirm_dlg.destroy()

            tk.Button(btn_frm, text="예", command=on_yes,
                     bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                     width=8).pack(side="left", padx=10)
            tk.Button(btn_frm, text="아니오", command=on_no,
                     bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                     width=8).pack(side="left", padx=10)

            confirm_dlg.bind("<Return>", lambda e: on_yes())
            confirm_dlg.bind("<Escape>", lambda e: on_no())

            # 모달 대기
            history_dialog.wait_window(confirm_dlg)

            if not confirm_result[0]:
                return

            # 이력에서 삭제
            install_dir = get_base_dir()
            history_file = os.path.join(install_dir, "safety_photos", ".export_history", "export_history.json")

            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)

                records = [r for r in records if r.get("export_id") != export_id]

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)

                # 커스텀 완료 다이얼로그
                done_dlg = tk.Toplevel(history_dialog)
                done_dlg.title("완료")
                done_dlg.configure(bg="#2C3E50")
                done_dlg.transient(history_dialog)
                done_dlg.grab_set()
                done_dlg.geometry("350x150")
                done_dlg.update_idletasks()
                x = (done_dlg.winfo_screenwidth() // 2) - 175
                y = (done_dlg.winfo_screenheight() // 2) - 75
                done_dlg.geometry(f"350x150+{x}+{y}")
                done_dlg.attributes("-topmost", True)
                done_dlg.focus_force()

                tk.Label(done_dlg, text="✅ 반출 이력이 삭제되었습니다.",
                        font=("Pretendard", 12), bg="#2C3E50", fg="#FFFFFF").pack(expand=True)
                tk.Button(done_dlg, text="확인", command=done_dlg.destroy,
                         bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(pady=15)
                done_dlg.bind("<Return>", lambda e: done_dlg.destroy())
                done_dlg.bind("<Escape>", lambda e: done_dlg.destroy())

                load_history()

            except Exception as e:
                # 커스텀 오류 다이얼로그
                err_dlg = tk.Toplevel(history_dialog)
                err_dlg.title("오류")
                err_dlg.configure(bg="#2C3E50")
                err_dlg.transient(history_dialog)
                err_dlg.grab_set()
                err_dlg.geometry("400x180")
                err_dlg.update_idletasks()
                x = (err_dlg.winfo_screenwidth() // 2) - 200
                y = (err_dlg.winfo_screenheight() // 2) - 90
                err_dlg.geometry(f"400x180+{x}+{y}")
                err_dlg.attributes("-topmost", True)
                err_dlg.focus_force()

                title_frm = tk.Frame(err_dlg, bg="#E74C3C")
                title_frm.pack(fill="x")
                tk.Label(title_frm, text="❌ 오류",
                        font=("Pretendard", 14, "bold"), bg="#E74C3C", fg="#FFFFFF").pack(pady=8)

                tk.Label(err_dlg, text=f"이력 삭제 실패:\n{e}",
                        font=("Pretendard", 11), bg="#2C3E50", fg="#FFFFFF", wraplength=350).pack(expand=True, pady=10)
                tk.Button(err_dlg, text="확인", command=err_dlg.destroy,
                         bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         width=8).pack(pady=10)
                err_dlg.bind("<Return>", lambda e: err_dlg.destroy())
                err_dlg.bind("<Escape>", lambda e: err_dlg.destroy())

        delete_btn = tk.Button(button_frame, text="이력 삭제", command=delete_selected,
                              bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                              relief="raised", bd=2, width=12, height=2,
                              activebackground="#C0392B", activeforeground="#FFFFFF")
        delete_btn.pack(side="left", padx=5)

        # 닫기 버튼
        close_btn = tk.Button(button_frame, text="닫기", command=history_dialog.destroy,
                             bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                             relief="raised", bd=2, width=12, height=2,
                             activebackground="#7F8C8D", activeforeground="#FFFFFF")
        close_btn.pack(side="right", padx=5)

        # ESC 키로 닫기
        history_dialog.bind("<Escape>", lambda e: history_dialog.destroy())

        # 더블클릭으로 보고서 만들기
        history_tree.bind("<Double-1>", lambda e: create_pdf_report())

        # 초기 데이터 로드
        load_history()
        clear_preview()

    def _generate_pdf_report(self, record: dict, filepath: str, parent_dialog=None):
        """PDF 보고서 생성"""
        from datetime import datetime as dt_module

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.colors import HexColor
        except ImportError:
            self._show_custom_error(
                "라이브러리 필요",
                "PDF 생성을 위해 reportlab 패키지가 필요합니다.\n\n설치 명령어:\npip install reportlab"
            )
            return

        try:
            import platform
            import zipfile

            # 한글 폰트 등록
            font_registered = False
            font_paths = [
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
                "/usr/share/fonts/opentype/pretendard/Pretendard-Regular.otf",
                "C:/Windows/Fonts/malgun.ttf",
                "C:/Windows/Fonts/NanumGothic.ttf"
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('KoreanFont', font_path))
                        font_registered = True
                        break
                    except:
                        continue

            korean_font = "KoreanFont" if font_registered else "Helvetica"

            # 시스템 정보 수집
            os_info = f"{platform.system()} {platform.release()}"
            try:
                if platform.system() == "Linux":
                    import subprocess
                    result = subprocess.run(['lsb_release', '-d'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        os_info = result.stdout.strip().replace("Description:", "").strip()
            except:
                pass

            program_name = "GARAMe Manager"
            program_version = "v1.9.7"
            hash_algorithm = "SHA-256"

            # ZIP 파일에서 파일 목록 추출
            archive_path = record.get("archive_path", "-")
            file_list = []
            file_count = 0
            if archive_path != "-" and os.path.exists(archive_path):
                try:
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        file_list = zf.namelist()
                        file_count = len(file_list)
                except:
                    pass

            # PDF 생성
            c = canvas.Canvas(filepath, pagesize=A4)
            width, height = A4

            # 색상 정의
            header_color = HexColor("#2C3E50")
            accent_color = HexColor("#3498DB")
            text_color = HexColor("#333333")
            light_gray = HexColor("#ECF0F1")

            # 헤더 배경
            c.setFillColor(header_color)
            c.rect(0, height - 80, width, 80, fill=True, stroke=False)

            # 제목
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont(korean_font, 24)
            c.drawString(30, height - 50, "안전교육 기록 반출 보고서")

            y_pos = height - 110

            # ========== 시스템 정보 섹션 ==========
            c.setFillColor(accent_color)
            c.setFont(korean_font, 13)
            c.drawString(30, y_pos, "▶ 시스템 정보")
            y_pos -= 22

            sys_items = [
                ("운영체제", os_info),
                ("프로그램", f"{program_name} {program_version}"),
                ("해시 알고리즘", hash_algorithm),
            ]

            for label, value in sys_items:
                c.setFont(korean_font, 9)
                c.setFillColor(HexColor("#7F8C8D"))
                c.drawString(40, y_pos, f"{label}:")
                c.setFillColor(text_color)
                c.setFont(korean_font, 10)
                c.drawString(130, y_pos, str(value))
                y_pos -= 16

            y_pos -= 10

            # ========== 반출 정보 섹션 ==========
            c.setFillColor(accent_color)
            c.setFont(korean_font, 13)
            c.drawString(30, y_pos, "▶ 반출 정보")
            y_pos -= 22

            info_items = [
                ("반출 ID", record.get("export_id", "-")),
                ("반출 일시", record.get("export_datetime", "-")),
                ("기록 수", f"{record.get('total_records', 0)}개"),
                ("반출자", record.get("exported_by", "-")),
                ("반출 목적", record.get("purpose", "-")),
            ]

            for label, value in info_items:
                c.setFont(korean_font, 9)
                c.setFillColor(HexColor("#7F8C8D"))
                c.drawString(40, y_pos, f"{label}:")
                c.setFillColor(text_color)
                c.setFont(korean_font, 10)
                c.drawString(130, y_pos, str(value))
                y_pos -= 16

            y_pos -= 10

            # ========== 아카이브 파일 정보 섹션 ==========
            c.setFillColor(accent_color)
            c.setFont(korean_font, 13)
            c.drawString(30, y_pos, "▶ 아카이브 파일 정보")
            y_pos -= 22

            file_exists = os.path.exists(archive_path) if archive_path != "-" else False

            c.setFont(korean_font, 9)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(40, y_pos, "저장 경로:")
            c.setFillColor(text_color)
            c.setFont(korean_font, 9)
            y_pos -= 14

            # 긴 경로 줄바꿈
            if len(archive_path) > 80:
                c.drawString(50, y_pos, archive_path[:80])
                y_pos -= 12
                c.drawString(50, y_pos, archive_path[80:])
            else:
                c.drawString(50, y_pos, archive_path)
            y_pos -= 16

            c.setFont(korean_font, 9)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(40, y_pos, "파일 상태:")
            if file_exists:
                c.setFillColor(HexColor("#27AE60"))
                c.drawString(130, y_pos, "존재함")
            else:
                c.setFillColor(HexColor("#E74C3C"))
                c.drawString(130, y_pos, "파일 없음")
            y_pos -= 16

            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(40, y_pos, "포함 파일 수:")
            c.setFillColor(text_color)
            c.drawString(130, y_pos, f"{file_count}개")
            y_pos -= 18

            # ========== 무결성 검증 정보 섹션 ==========
            c.setFillColor(accent_color)
            c.setFont(korean_font, 13)
            c.drawString(30, y_pos, "▶ 무결성 검증 정보")
            y_pos -= 22

            archive_hash = record.get("archive_hash", "-")
            c.setFont(korean_font, 9)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(40, y_pos, "해시 함수:")
            c.setFillColor(text_color)
            c.drawString(130, y_pos, hash_algorithm)
            y_pos -= 16

            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(40, y_pos, "아카이브 해시:")
            y_pos -= 14

            c.setFillColor(text_color)
            c.setFont(korean_font, 8)
            if len(archive_hash) > 64:
                c.drawString(50, y_pos, archive_hash[:64])
                y_pos -= 11
                c.drawString(50, y_pos, archive_hash[64:])
            else:
                c.drawString(50, y_pos, archive_hash)
            y_pos -= 18

            # ========== 포함 파일 목록 섹션 ==========
            c.setFillColor(accent_color)
            c.setFont(korean_font, 13)
            c.drawString(30, y_pos, f"▶ 포함 파일 목록 ({file_count}개)")
            y_pos -= 20

            c.setFillColor(text_color)
            c.setFont(korean_font, 8)

            # 파일 목록 출력 (최대 25개)
            max_files_display = 25
            displayed_files = file_list[:max_files_display]

            for i, fname in enumerate(displayed_files):
                if y_pos < 60:
                    c.drawString(50, y_pos, f"... 외 {len(file_list) - i}개 파일")
                    break
                display_name = fname if len(fname) <= 70 else f"...{fname[-67:]}"
                c.drawString(50, y_pos, f"• {display_name}")
                y_pos -= 11

            if len(file_list) > max_files_display:
                c.drawString(50, y_pos, f"... 외 {len(file_list) - max_files_display}개 파일")
                y_pos -= 11

            # ========== 푸터 ==========
            c.setFillColor(light_gray)
            c.rect(0, 0, width, 40, fill=True, stroke=False)

            c.setFillColor(HexColor("#7F8C8D"))
            c.setFont(korean_font, 8)
            c.drawString(30, 20, f"보고서 생성: {dt_module.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(width - 180, 20, f"{program_name} {program_version}")

            c.save()

            # 완료 다이얼로그 표시
            self._show_report_complete_dialog(filepath, parent_dialog)

        except Exception as e:
            self._show_custom_error("PDF 생성 오류", f"PDF 생성 중 오류:\n{e}")

    def _show_report_complete_dialog(self, filepath: str, parent_dialog=None):
        """보고서 저장 완료 다이얼로그"""
        folder_path = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        parent = parent_dialog if parent_dialog else self.dialog

        # 다이얼로그 생성
        report_dialog = tk.Toplevel(parent)
        report_dialog.title("보고서 저장 완료")
        report_dialog.configure(bg="#2C3E50")
        report_dialog.transient(parent)
        report_dialog.grab_set()

        # 창 크기 및 중앙 배치
        dialog_width = 550
        dialog_height = 280
        report_dialog.geometry(f"{dialog_width}x{dialog_height}")
        report_dialog.update_idletasks()
        x = (report_dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (report_dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        report_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 최상위 표시
        report_dialog.attributes("-topmost", True)
        report_dialog.focus_force()

        # 제목
        title_frame = tk.Frame(report_dialog, bg="#2C3E50")
        title_frame.pack(pady=20)

        title_label = tk.Label(title_frame, text="✅ 보고서 저장 완료",
                              font=("Pretendard", 20, "bold"), bg="#2C3E50", fg="#27AE60")
        title_label.pack()

        # 정보 프레임
        info_frame = tk.Frame(report_dialog, bg="#34495E", relief="raised", bd=2)
        info_frame.pack(fill="x", padx=30, pady=10)

        # 저장 디렉토리
        dir_frame = tk.Frame(info_frame, bg="#34495E")
        dir_frame.pack(fill="x", padx=15, pady=8)

        tk.Label(dir_frame, text="저장 위치:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700", width=10, anchor="w").pack(side="left")
        tk.Label(dir_frame, text=folder_path, font=("Pretendard", 10),
                bg="#34495E", fg="#FFFFFF", wraplength=380).pack(side="left", padx=10)

        # 파일명
        file_frame = tk.Frame(info_frame, bg="#34495E")
        file_frame.pack(fill="x", padx=15, pady=8)

        tk.Label(file_frame, text="파일명:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700", width=10, anchor="w").pack(side="left")
        tk.Label(file_frame, text=filename, font=("Pretendard", 10),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 버튼 프레임
        btn_frame = tk.Frame(report_dialog, bg="#2C3E50")
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="확인", command=report_dialog.destroy,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                 relief="raised", bd=2, width=12).pack(side="left", padx=10)

        report_dialog.bind("<Return>", lambda e: report_dialog.destroy())
        report_dialog.bind("<Escape>", lambda e: report_dialog.destroy())

    def _clear_placeholder(self, entry, placeholder):
        """입력란 플레이스홀더 제거"""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)

    def _close(self):
        """다이얼로그 닫기"""
        if self.dialog:
            # 캐시 정리
            self.image_cache.clear()

            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
