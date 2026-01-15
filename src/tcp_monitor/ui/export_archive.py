"""
반출 아카이브 대화상자

안전교육 기록을 지정 기간별로 ZIP 파일로 반출합니다.
(특허 청구항 3, 7 관련)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
from datetime import datetime, timedelta

from ..utils.helpers import get_base_dir


class ExportArchiveDialog:
    """반출 아카이브 생성 대화상자"""

    def __init__(self, parent, data_dir: str = None):
        """
        반출 대화상자 초기화

        Args:
            parent: 부모 윈도우
            data_dir: 데이터 디렉토리 (기본값: safety_photos)
        """
        self.parent = parent
        # 프로그램 설치 디렉토리 기준으로 경로 설정
        if data_dir is None:
            install_dir = get_base_dir()
            data_dir = os.path.join(install_dir, "safety_photos")
        self.data_dir = data_dir
        self.dialog = None
        self.export_running = False

        # 입력 필드
        self.start_date_var = None
        self.end_date_var = None
        self.purpose_var = None
        self.exporter_var = None
        self.export_path_var = None

        # 상태 표시
        self.status_label = None
        self.progress_var = None
        self.progress_bar = None

    def show(self):
        """대화상자 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("기록 반출")
        self.dialog.geometry("950x850")
        self.dialog.minsize(900, 800)

        # 모달 설정
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 중앙 배치
        self._center_window()

        # UI 생성
        self._create_ui()

        # 포커스
        self.dialog.focus_set()

    def _center_window(self):
        """창을 화면 중앙에 배치"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_ui(self):
        """UI 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        # 제목
        title_label = ttk.Label(
            main_frame,
            text="안전교육 기록 반출",
            font=("Pretendard", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        # 탭 노트북
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))

        # 새 반출 탭
        new_export_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(new_export_frame, text="새 반출")

        # 반출 이력 탭
        history_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(history_frame, text="반출 이력")

        # 새 반출 탭 내용 생성
        self._create_new_export_ui(new_export_frame)

        # 반출 이력 탭 내용 생성
        self._create_history_ui(history_frame)

        # 닫기 버튼 (하단)
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            close_frame,
            text="닫기",
            command=self._close,
            width=10
        ).pack(side="right")

    def _create_new_export_ui(self, parent):
        """새 반출 탭 UI 생성"""
        # 설명
        desc_label = ttk.Label(
            parent,
            text="지정 기간의 안전교육 기록을 ZIP 파일로 반출합니다.\n"
                 "반출 파일에는 이미지, 메타데이터, 해시 체인 검증 도구가 포함됩니다.",
            font=("Pretendard", 10),
            justify="center"
        )
        desc_label.pack(pady=(0, 15))

        # 기간 선택 프레임
        period_frame = ttk.LabelFrame(parent, text="반출 기간", padding=10)
        period_frame.pack(fill="x", pady=(0, 10))

        # 시작일
        start_frame = ttk.Frame(period_frame)
        start_frame.pack(fill="x", pady=5)

        ttk.Label(start_frame, text="시작일:", width=10).pack(side="left")

        self.start_date_var = tk.StringVar()
        # 기본값: 한 달 전
        default_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.start_date_var.set(default_start)

        start_entry = ttk.Entry(start_frame, textvariable=self.start_date_var, width=15)
        start_entry.pack(side="left", padx=5)

        ttk.Label(start_frame, text="(YYYY-MM-DD)", foreground="gray").pack(side="left")

        # 종료일
        end_frame = ttk.Frame(period_frame)
        end_frame.pack(fill="x", pady=5)

        ttk.Label(end_frame, text="종료일:", width=10).pack(side="left")

        self.end_date_var = tk.StringVar()
        # 기본값: 오늘
        self.end_date_var.set(datetime.now().strftime("%Y-%m-%d"))

        end_entry = ttk.Entry(end_frame, textvariable=self.end_date_var, width=15)
        end_entry.pack(side="left", padx=5)

        ttk.Label(end_frame, text="(YYYY-MM-DD)", foreground="gray").pack(side="left")

        # 빠른 선택 버튼
        quick_frame = ttk.Frame(period_frame)
        quick_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(quick_frame, text="오늘", width=8,
                   command=lambda: self._set_quick_date(0)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="최근 7일", width=10,
                   command=lambda: self._set_quick_date(7)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="최근 30일", width=10,
                   command=lambda: self._set_quick_date(30)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="이번 달", width=10,
                   command=self._set_this_month).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="전체", width=8,
                   command=self._set_all_period).pack(side="left", padx=2)

        # 반출 정보 프레임
        info_frame = ttk.LabelFrame(parent, text="반출 정보", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))

        # 반출 목적
        purpose_frame = ttk.Frame(info_frame)
        purpose_frame.pack(fill="x", pady=5)

        ttk.Label(purpose_frame, text="반출 목적:", width=10).pack(side="left")

        self.purpose_var = tk.StringVar()
        purpose_entry = ttk.Entry(purpose_frame, textvariable=self.purpose_var, width=40)
        purpose_entry.pack(side="left", padx=5, fill="x", expand=True)

        # 반출자
        exporter_frame = ttk.Frame(info_frame)
        exporter_frame.pack(fill="x", pady=5)

        ttk.Label(exporter_frame, text="반출자:", width=10).pack(side="left")

        self.exporter_var = tk.StringVar()
        exporter_entry = ttk.Entry(exporter_frame, textvariable=self.exporter_var, width=40)
        exporter_entry.pack(side="left", padx=5, fill="x", expand=True)

        # 저장 경로 프레임
        path_frame = ttk.LabelFrame(parent, text="저장 위치", padding=10)
        path_frame.pack(fill="x", pady=(0, 10))

        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill="x")

        self.export_path_var = tk.StringVar()
        # 기본 저장 경로
        default_filename = f"safety_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        default_path = os.path.join(os.path.expanduser("~"), default_filename)
        self.export_path_var.set(default_path)

        path_entry = ttk.Entry(path_inner, textvariable=self.export_path_var, width=50)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(path_inner, text="찾아보기...",
                   command=self._browse_save_path).pack(side="right")

        # 진행 상태 프레임
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", pady=10)

        self.status_label = ttk.Label(
            progress_frame,
            text="대기 중...",
            font=("Pretendard", 10)
        )
        self.status_label.pack(side="left")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side="right", padx=10)

        # 버튼 프레임
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=10)

        self.export_btn = ttk.Button(
            btn_frame,
            text="반출 실행",
            command=self._start_export,
            width=15
        )
        self.export_btn.pack(side="left", padx=5)

        # 정보 레이블
        info_label = ttk.Label(
            parent,
            text="반출된 파일에는 독립 검증 도구(Python 스크립트)가 포함됩니다.\n"
                 "이 도구를 사용하여 외부에서도 기록의 무결성을 검증할 수 있습니다.",
            font=("Pretendard", 9),
            foreground="gray",
            justify="center"
        )
        info_label.pack(pady=(10, 0))

    def _create_history_ui(self, parent):
        """반출 이력 탭 UI 생성"""
        # 설명
        desc_label = ttk.Label(
            parent,
            text="이전에 수행한 반출 작업 이력입니다. 항목을 선택하면 오른쪽에 상세 정보가 표시됩니다.",
            font=("Pretendard", 10)
        )
        desc_label.pack(pady=(0, 10))

        # 메인 컨테이너 (좌: 목록 50%, 우: 미리보기 50%) - PanedWindow 사용
        main_container = ttk.PanedWindow(parent, orient="horizontal")
        main_container.pack(fill="both", expand=True)

        # 좌측: 이력 목록 (50%)
        left_frame = ttk.Frame(main_container)

        # 이력 목록 (Treeview)
        columns = ("export_id", "datetime", "period", "records", "exporter")
        self.history_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)

        # 컬럼 설정
        self.history_tree.heading("export_id", text="반출 ID")
        self.history_tree.heading("datetime", text="반출 일시")
        self.history_tree.heading("period", text="기간")
        self.history_tree.heading("records", text="기록수")
        self.history_tree.heading("exporter", text="반출자")

        self.history_tree.column("export_id", width=120, anchor="w")
        self.history_tree.column("datetime", width=100, anchor="center")
        self.history_tree.column("period", width=120, anchor="center")
        self.history_tree.column("records", width=45, anchor="center")
        self.history_tree.column("exporter", width=60, anchor="center")

        # 스크롤바
        scrollbar_y = ttk.Scrollbar(left_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar_y.set)

        # 배치
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # 우측: 미리보기 패널 (50%)
        right_frame = ttk.LabelFrame(main_container, text="반출 상세 정보", padding=10)

        # 상세 정보 텍스트
        self.preview_text = tk.Text(
            right_frame,
            font=("Pretendard", 10),
            wrap="word",
            bg="#F8F9FA",
            fg="#2C3E50",
            state="disabled",
            width=45,
            height=20
        )
        preview_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)

        self.preview_text.pack(side="left", fill="both", expand=True)
        preview_scroll.pack(side="right", fill="y")

        # PanedWindow에 패널 추가 (각각 50% 비율)
        main_container.add(left_frame, weight=1)
        main_container.add(right_frame, weight=1)

        # 버튼 프레임
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            btn_frame,
            text="새로고침",
            command=self._refresh_history,
            width=12
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="보고서 만들기",
            command=self._create_pdf_report,
            width=12
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="이력 삭제",
            command=self._delete_history,
            width=12
        ).pack(side="right", padx=5)

        # 선택 이벤트 바인딩 (미리보기 업데이트)
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.history_tree.bind("<Double-1>", lambda e: self._create_pdf_report())

        # 초기 데이터 로드
        self._refresh_history()

    def _on_history_select(self, event=None):
        """이력 선택 시 미리보기 업데이트"""
        selection = self.history_tree.selection()
        if not selection:
            self._clear_preview()
            return

        item = self.history_tree.item(selection[0])
        values = item.get("values", [])

        if len(values) >= 1:
            export_id = values[0]

            try:
                from ..utils.integrity_manager import IntegrityManager
                integrity = IntegrityManager(self.data_dir)
                record = integrity.get_export_by_id(export_id)

                if record:
                    self._update_preview(record)
                else:
                    self._clear_preview()
            except Exception as e:
                self._clear_preview()
                print(f"[ExportArchive] 미리보기 로드 실패: {e}")

    def _update_preview(self, record):
        """미리보기 패널 업데이트"""
        period = record.get("period", {})
        archive_path = record.get("archive_path", "-")
        file_exists = os.path.exists(archive_path) if archive_path != "-" else False

        preview_content = f"""반출 ID
  {record.get('export_id', '-')}

반출 일시
  {record.get('export_datetime', '-')}

반출 기간
  {period.get('start', '-')} ~ {period.get('end', '-')}

기록 수
  {record.get('total_records', 0)}개

반출자
  {record.get('exported_by', '-')}

반출 목적
  {record.get('purpose', '-')}

저장 경로
  {archive_path}

파일 상태
  {'✅ 존재함' if file_exists else '❌ 파일 없음'}

아카이브 해시 (SHA-256)
  {record.get('archive_hash', '-')}
"""

        self.preview_text.configure(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, preview_content)
        self.preview_text.configure(state="disabled")

    def _clear_preview(self):
        """미리보기 패널 초기화"""
        self.preview_text.configure(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, "항목을 선택하면 상세 정보가 표시됩니다.")
        self.preview_text.configure(state="disabled")

    def _refresh_history(self):
        """반출 이력 새로고침"""
        # 기존 항목 삭제
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            from ..utils.integrity_manager import IntegrityManager
            integrity = IntegrityManager(self.data_dir)
            history = integrity.get_export_history()

            for record in history:
                period = record.get("period", {})
                period_str = f"{period.get('start', '-')} ~ {period.get('end', '-')}"

                # 날짜 포맷 변경
                export_dt = record.get("export_datetime", "-")
                if export_dt and export_dt != "-":
                    try:
                        dt = datetime.fromisoformat(export_dt)
                        export_dt = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                self.history_tree.insert(
                    "",
                    "end",
                    values=(
                        record.get("export_id", "-"),
                        export_dt,
                        period_str,
                        record.get("total_records", 0),
                        record.get("exported_by", "-")
                    )
                )

            # 미리보기 초기화
            self._clear_preview()
        except Exception as e:
            print(f"[ExportArchive] 이력 로드 실패: {e}")

    def _show_history_detail(self):
        """선택된 반출 이력 상세 보기"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("알림", "상세 정보를 볼 항목을 선택하세요.", parent=self.dialog)
            return

        item = self.history_tree.item(selection[0])
        values = item.get("values", [])

        if len(values) >= 1:
            export_id = values[0]

            try:
                from ..utils.integrity_manager import IntegrityManager
                integrity = IntegrityManager(self.data_dir)
                record = integrity.get_export_by_id(export_id)

                if record:
                    period = record.get("period", {})
                    detail_text = f"""반출 ID: {record.get('export_id', '-')}

반출 일시: {record.get('export_datetime', '-')}
반출 기간: {period.get('start', '-')} ~ {period.get('end', '-')}
기록 수: {record.get('total_records', 0)}개

반출자: {record.get('exported_by', '-')}
반출 목적: {record.get('purpose', '-')}

저장 경로:
{record.get('archive_path', '-')}

아카이브 해시:
{record.get('archive_hash', '-')}"""

                    messagebox.showinfo("반출 상세 정보", detail_text, parent=self.dialog)
                else:
                    messagebox.showwarning("알림", "반출 이력을 찾을 수 없습니다.", parent=self.dialog)
            except Exception as e:
                messagebox.showerror("오류", f"상세 정보 조회 실패:\n{e}", parent=self.dialog)

    def _create_pdf_report(self):
        """선택된 반출 이력의 PDF 보고서 생성"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("알림", "보고서를 만들 항목을 선택하세요.", parent=self.dialog)
            return

        item = self.history_tree.item(selection[0])
        values = item.get("values", [])

        if len(values) < 1:
            messagebox.showwarning("알림", "항목 정보를 가져올 수 없습니다.", parent=self.dialog)
            return

        export_id = values[0]

        try:
            from ..utils.integrity_manager import IntegrityManager
            integrity = IntegrityManager(self.data_dir)
            record = integrity.get_export_by_id(export_id)

            if not record:
                messagebox.showwarning("알림", "반출 이력을 찾을 수 없습니다.", parent=self.dialog)
                return

            # 저장 경로 선택
            self.dialog.attributes("-topmost", True)
            self.dialog.update()

            default_filename = f"export_report_{export_id}.pdf"
            filepath = filedialog.asksaveasfilename(
                title="보고서 저장",
                defaultextension=".pdf",
                filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")],
                initialfile=default_filename,
                parent=self.dialog
            )

            self.dialog.attributes("-topmost", False)

            if not filepath:
                return

            # PDF 생성
            self._generate_pdf_report(record, filepath)

        except Exception as e:
            messagebox.showerror("오류", f"보고서 생성 실패:\n{e}", parent=self.dialog)

    def _generate_pdf_report(self, record: dict, filepath: str):
        """PDF 보고서 생성"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.colors import HexColor
        except ImportError:
            messagebox.showerror(
                "오류",
                "PDF 생성을 위해 reportlab 패키지가 필요합니다.\n\n"
                "설치 명령어:\npip install reportlab",
                parent=self.dialog
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

            if not font_registered:
                korean_font = "Helvetica"
            else:
                korean_font = "KoreanFont"

            # 시스템 정보 수집
            os_info = f"{platform.system()} {platform.release()}"
            try:
                # Linux에서 더 자세한 정보
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
                    file_list = []
                    file_count = 0

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

            period = record.get("period", {})
            info_items = [
                ("반출 ID", record.get("export_id", "-")),
                ("반출 일시", record.get("export_datetime", "-")),
                ("반출 기간", f"{period.get('start', '-')} ~ {period.get('end', '-')}"),
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

            # 파일 목록 출력 (최대 25개, 페이지 넘침 방지)
            max_files_display = 25
            displayed_files = file_list[:max_files_display]

            for i, fname in enumerate(displayed_files):
                if y_pos < 60:  # 페이지 하단 여백 확보
                    c.drawString(50, y_pos, f"... 외 {len(file_list) - i}개 파일")
                    break
                # 폴더 구분자 처리
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
            c.drawString(30, 20, f"보고서 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(width - 180, 20, f"{program_name} {program_version}")

            c.save()

            # 완료 다이얼로그 표시
            self._show_report_complete_dialog(filepath)

        except Exception as e:
            messagebox.showerror("오류", f"PDF 생성 중 오류:\n{e}", parent=self.dialog)

    def _show_report_complete_dialog(self, filepath: str):
        """보고서 저장 완료 다이얼로그"""
        folder_path = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        # 다이얼로그 생성
        report_dialog = tk.Toplevel(self.dialog)
        report_dialog.title("보고서 저장 완료")
        report_dialog.configure(bg="#2C3E50")
        report_dialog.transient(self.dialog)
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
        dir_frame.pack(fill="x", padx=15, pady=(15, 5))

        tk.Label(dir_frame, text="저장 위치:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(dir_frame, text=folder_path, font=("Pretendard", 10),
                bg="#34495E", fg="#FFFFFF", wraplength=400, justify="left").pack(side="left", padx=10)

        # 파일명
        file_frame = tk.Frame(info_frame, bg="#34495E")
        file_frame.pack(fill="x", padx=15, pady=(5, 15))

        tk.Label(file_frame, text="파일명:", font=("Pretendard", 11, "bold"),
                bg="#34495E", fg="#FFD700").pack(side="left")
        tk.Label(file_frame, text=filename, font=("Pretendard", 10),
                bg="#34495E", fg="#FFFFFF").pack(side="left", padx=10)

        # 버튼 프레임
        button_frame = tk.Frame(report_dialog, bg="#2C3E50")
        button_frame.pack(pady=20)

        # 확인 버튼
        ok_btn = tk.Button(button_frame, text="확인", command=report_dialog.destroy,
                          bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                          relief="raised", bd=3, width=10, height=1,
                          activebackground="#229954", activeforeground="#FFFFFF")
        ok_btn.pack(side="left", padx=10)

        # 확인 버튼에 포커스
        ok_btn.focus_set()

        # Enter/Escape 키 바인딩
        report_dialog.bind("<Return>", lambda e: report_dialog.destroy())
        report_dialog.bind("<Escape>", lambda e: report_dialog.destroy())

    def _show_builtin_pdf_viewer(self, filepath: str, parent_dialog=None):
        """내장 PDF 뷰어 다이얼로그 표시"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            # PyMuPDF가 없으면 외부 뷰어로 폴백
            messagebox.showinfo(
                "PDF 뷰어",
                "내장 PDF 뷰어를 사용하려면 PyMuPDF가 필요합니다.\n\n"
                "설치: pip install PyMuPDF\n\n"
                "외부 PDF 뷰어로 엽니다.",
                parent=parent_dialog or self.dialog
            )
            self._open_external_pdf(filepath)
            return

        try:
            # PDF 열기
            doc = fitz.open(filepath)
            total_pages = len(doc)

            if total_pages == 0:
                messagebox.showerror("오류", "PDF 파일에 페이지가 없습니다.", parent=parent_dialog or self.dialog)
                doc.close()
                return

            # PDF 뷰어 다이얼로그 생성
            pdf_dialog = tk.Toplevel(parent_dialog or self.dialog)
            pdf_dialog.title(f"PDF 보고서 - {os.path.basename(filepath)}")
            pdf_dialog.geometry("850x1000")
            pdf_dialog.configure(bg="#2C3E50")

            # 중앙 배치
            pdf_dialog.update_idletasks()
            x = (pdf_dialog.winfo_screenwidth() // 2) - (850 // 2)
            y = (pdf_dialog.winfo_screenheight() // 2) - (1000 // 2)
            pdf_dialog.geometry(f"850x1000+{x}+{y}")

            # 최상위로 표시
            pdf_dialog.attributes("-topmost", True)
            pdf_dialog.lift()
            pdf_dialog.focus_force()
            pdf_dialog.after(100, lambda: pdf_dialog.attributes("-topmost", False))

            # 모달 설정
            pdf_dialog.transient(parent_dialog or self.dialog)
            pdf_dialog.grab_set()

            # 현재 페이지 변수
            current_page = [0]  # 리스트로 감싸서 클로저에서 수정 가능하게

            # 상단 툴바
            toolbar = tk.Frame(pdf_dialog, bg="#34495E", height=50)
            toolbar.pack(fill="x", padx=5, pady=5)
            toolbar.pack_propagate(False)

            # 제목
            title_label = tk.Label(
                toolbar,
                text=f"📄 {os.path.basename(filepath)}",
                font=("Pretendard", 12, "bold"),
                bg="#34495E",
                fg="#FFFFFF"
            )
            title_label.pack(side="left", padx=10)

            # 페이지 컨트롤
            nav_frame = tk.Frame(toolbar, bg="#34495E")
            nav_frame.pack(side="right", padx=10)

            # 이전 페이지 버튼
            prev_btn = tk.Button(
                nav_frame,
                text="◀ 이전",
                font=("Pretendard", 10, "bold"),
                bg="#3498DB",
                fg="#FFFFFF",
                width=8,
                command=lambda: go_to_page(current_page[0] - 1)
            )
            prev_btn.pack(side="left", padx=5)

            # 페이지 표시 레이블
            page_label = tk.Label(
                nav_frame,
                text=f"1 / {total_pages}",
                font=("Pretendard", 11, "bold"),
                bg="#34495E",
                fg="#FFFFFF",
                width=10
            )
            page_label.pack(side="left", padx=10)

            # 다음 페이지 버튼
            next_btn = tk.Button(
                nav_frame,
                text="다음 ▶",
                font=("Pretendard", 10, "bold"),
                bg="#3498DB",
                fg="#FFFFFF",
                width=8,
                command=lambda: go_to_page(current_page[0] + 1)
            )
            next_btn.pack(side="left", padx=5)

            # PDF 표시 영역 (스크롤 가능)
            canvas_frame = tk.Frame(pdf_dialog, bg="#1A252F")
            canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # 캔버스와 스크롤바
            canvas = tk.Canvas(canvas_frame, bg="#1A252F", highlightthickness=0)
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)

            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            v_scrollbar.pack(side="right", fill="y")
            h_scrollbar.pack(side="bottom", fill="x")
            canvas.pack(side="left", fill="both", expand=True)

            # 이미지 레이블 (캔버스 내부)
            pdf_image_label = tk.Label(canvas, bg="#1A252F")
            canvas.create_window((0, 0), window=pdf_image_label, anchor="nw")

            # PDF 이미지 참조 유지
            pdf_dialog.pdf_image = None

            def render_page(page_num):
                """특정 페이지 렌더링"""
                if page_num < 0 or page_num >= total_pages:
                    return

                current_page[0] = page_num
                page_label.config(text=f"{page_num + 1} / {total_pages}")

                # 버튼 상태 업데이트
                prev_btn.config(state="normal" if page_num > 0 else "disabled")
                next_btn.config(state="normal" if page_num < total_pages - 1 else "disabled")

                try:
                    page = doc.load_page(page_num)
                    # 고해상도 렌더링 (2x 스케일)
                    zoom = 2.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    # PIL Image로 변환
                    from PIL import Image, ImageTk
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # 창 크기에 맞게 조정 (최대 800px 너비)
                    max_width = 800
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                    # Tkinter 이미지로 변환
                    pdf_dialog.pdf_image = ImageTk.PhotoImage(img)
                    pdf_image_label.config(image=pdf_dialog.pdf_image)

                    # 스크롤 영역 업데이트
                    pdf_image_label.update_idletasks()
                    canvas.config(scrollregion=canvas.bbox("all"))

                    # 스크롤 맨 위로
                    canvas.yview_moveto(0)
                    canvas.xview_moveto(0)

                except Exception as e:
                    print(f"페이지 렌더링 오류: {e}")
                    pdf_image_label.config(text=f"페이지 렌더링 오류: {e}", image="")

            def go_to_page(page_num):
                """특정 페이지로 이동"""
                if 0 <= page_num < total_pages:
                    render_page(page_num)

            # 키보드 바인딩
            def on_key(event):
                if event.keysym in ("Left", "Up", "Prior"):  # Prior = Page Up
                    go_to_page(current_page[0] - 1)
                elif event.keysym in ("Right", "Down", "Next"):  # Next = Page Down
                    go_to_page(current_page[0] + 1)
                elif event.keysym == "Home":
                    go_to_page(0)
                elif event.keysym == "End":
                    go_to_page(total_pages - 1)
                elif event.keysym == "Escape":
                    pdf_dialog.destroy()

            pdf_dialog.bind("<Key>", on_key)

            # 마우스 휠 스크롤
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            def on_mousewheel_linux(event):
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

            canvas.bind("<MouseWheel>", on_mousewheel)
            canvas.bind("<Button-4>", on_mousewheel_linux)
            canvas.bind("<Button-5>", on_mousewheel_linux)

            # 하단 버튼
            bottom_frame = tk.Frame(pdf_dialog, bg="#2C3E50", height=50)
            bottom_frame.pack(fill="x", padx=5, pady=5)

            # 외부 뷰어로 열기 버튼
            external_btn = tk.Button(
                bottom_frame,
                text="🔗 외부 뷰어로 열기",
                font=("Pretendard", 10, "bold"),
                bg="#9B59B6",
                fg="#FFFFFF",
                width=16,
                command=lambda: self._open_external_pdf(filepath)
            )
            external_btn.pack(side="left", padx=10, pady=5)

            # 닫기 버튼
            close_btn = tk.Button(
                bottom_frame,
                text="닫기",
                font=("Pretendard", 11, "bold"),
                bg="#E74C3C",
                fg="#FFFFFF",
                width=10,
                command=pdf_dialog.destroy
            )
            close_btn.pack(side="right", padx=10, pady=5)

            # 다이얼로그 종료 시 PDF 닫기
            def on_close():
                try:
                    doc.close()
                except:
                    pass
                pdf_dialog.destroy()

            pdf_dialog.protocol("WM_DELETE_WINDOW", on_close)

            # 첫 페이지 렌더링
            render_page(0)

            # 포커스 설정
            pdf_dialog.focus_set()

        except Exception as e:
            import traceback
            print(f"PDF 뷰어 오류:\n{traceback.format_exc()}")
            messagebox.showerror("오류", f"PDF 뷰어 오류:\n{e}", parent=parent_dialog or self.dialog)

    def _open_external_pdf(self, filepath: str):
        """외부 PDF 뷰어로 열기"""
        import subprocess
        import platform

        try:
            system = platform.system()
            if system == "Linux":
                subprocess.Popen(['xdg-open', filepath])
            elif system == "Darwin":
                subprocess.Popen(['open', filepath])
            elif system == "Windows":
                os.startfile(filepath)
            else:
                subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            print(f"외부 PDF 뷰어 열기 오류: {e}")

    def _focus_pdf_viewer(self, filepath: str, attempt: int = 1):
        """PDF 뷰어 창을 최상위로 포커싱 (Linux) - 여러 번 시도"""
        import subprocess
        import platform

        max_attempts = 5

        try:
            system = platform.system()

            if system == "Linux":
                filename = os.path.basename(filepath)

                # 방법 1: wmctrl 사용 (설치되어 있으면)
                try:
                    # wmctrl로 창 활성화 시도 (파일명 또는 PDF 뷰어 이름으로)
                    result = subprocess.run(['wmctrl', '-a', filename], capture_output=True, timeout=2)
                    if result.returncode != 0:
                        # 파일명으로 찾지 못하면 일반적인 PDF 뷰어 이름으로 시도
                        subprocess.run(['wmctrl', '-a', 'pdf'], capture_output=True, timeout=2)
                        subprocess.run(['wmctrl', '-a', 'evince'], capture_output=True, timeout=2)
                        subprocess.run(['wmctrl', '-a', 'Document'], capture_output=True, timeout=2)
                except FileNotFoundError:
                    # wmctrl이 없으면 xdotool 시도
                    try:
                        result = subprocess.run(
                            ['xdotool', 'search', '--name', filename, 'windowactivate', '--sync'],
                            capture_output=True, timeout=3
                        )
                        if result.returncode != 0:
                            # PDF 뷰어 이름으로 시도
                            subprocess.run(
                                ['xdotool', 'search', '--name', 'pdf', 'windowactivate'],
                                capture_output=True, timeout=2
                            )
                    except FileNotFoundError:
                        # 둘 다 없으면 무시
                        pass
                except subprocess.TimeoutExpired:
                    pass
                except Exception as e:
                    print(f"PDF 뷰어 포커싱 시도 {attempt} 실패: {e}")

                # 포커싱이 안 되면 재시도 (최대 5회, 점점 늘어나는 지연)
                if attempt < max_attempts:
                    delay = 500 * attempt  # 500ms, 1000ms, 1500ms, 2000ms
                    self.dialog.after(delay, lambda: self._focus_pdf_viewer(filepath, attempt + 1))

        except Exception as e:
            print(f"PDF 뷰어 포커싱 오류 (무시): {e}")

    def _delete_history(self):
        """선택된 반출 이력 삭제"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("알림", "삭제할 항목을 선택하세요.", parent=self.dialog)
            return

        item = self.history_tree.item(selection[0])
        values = item.get("values", [])

        if len(values) >= 1:
            export_id = values[0]

            if not messagebox.askyesno("확인", f"반출 이력을 삭제하시겠습니까?\n\n반출 ID: {export_id}\n\n(실제 파일은 삭제되지 않습니다)", parent=self.dialog):
                return

            try:
                from ..utils.integrity_manager import IntegrityManager
                integrity = IntegrityManager(self.data_dir)

                if integrity.delete_export_history(export_id):
                    messagebox.showinfo("완료", "반출 이력이 삭제되었습니다.", parent=self.dialog)
                    self._refresh_history()
                else:
                    messagebox.showwarning("알림", "이력 삭제에 실패했습니다.", parent=self.dialog)
            except Exception as e:
                messagebox.showerror("오류", f"이력 삭제 실패:\n{e}", parent=self.dialog)

    def _set_quick_date(self, days):
        """빠른 날짜 선택"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

    def _set_this_month(self):
        """이번 달 선택"""
        today = datetime.now()
        start_date = today.replace(day=1)
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(today.strftime("%Y-%m-%d"))

    def _set_all_period(self):
        """전체 기간 선택"""
        self.start_date_var.set("2020-01-01")
        self.end_date_var.set(datetime.now().strftime("%Y-%m-%d"))

    def _browse_save_path(self):
        """저장 경로 선택"""
        # 다이얼로그를 최상위로 올려서 파일 다이얼로그가 앞에 표시되도록
        self.dialog.attributes("-topmost", True)
        self.dialog.update()

        filepath = filedialog.asksaveasfilename(
            title="반출 파일 저장",
            defaultextension=".zip",
            filetypes=[("ZIP 파일", "*.zip"), ("모든 파일", "*.*")],
            initialfile=f"safety_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            parent=self.dialog
        )

        # topmost 해제
        self.dialog.attributes("-topmost", False)

        if filepath:
            self.export_path_var.set(filepath)

    def _validate_inputs(self) -> bool:
        """입력값 검증"""
        # 날짜 형식 검증
        try:
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")

            if start_date > end_date:
                messagebox.showwarning("입력 오류", "시작일이 종료일보다 늦습니다.")
                return False

        except ValueError:
            messagebox.showwarning("입력 오류", "날짜 형식이 올바르지 않습니다.\nYYYY-MM-DD 형식으로 입력하세요.")
            return False

        # 저장 경로 검증
        export_path = self.export_path_var.get()
        if not export_path:
            messagebox.showwarning("입력 오류", "저장 경로를 입력하세요.")
            return False

        # 저장 디렉토리 존재 확인
        save_dir = os.path.dirname(export_path)
        if save_dir and not os.path.exists(save_dir):
            if not messagebox.askyesno("확인", f"저장 폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n{save_dir}"):
                return False
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("오류", f"폴더 생성 실패:\n{e}")
                return False

        return True

    def _start_export(self):
        """반출 시작"""
        if self.export_running:
            return

        if not self._validate_inputs():
            return

        self.export_running = True
        self.export_btn.configure(state="disabled")
        self.progress_var.set(0)
        self.status_label.configure(text="반출 준비 중...")

        # 백그라운드 스레드에서 반출 실행
        thread = threading.Thread(target=self._run_export, daemon=True)
        thread.start()

    def _run_export(self):
        """반출 실행 (백그라운드 스레드)"""
        try:
            from ..utils.integrity_manager import IntegrityManager

            # IntegrityManager 초기화
            integrity = IntegrityManager(self.data_dir)

            # UI 업데이트
            self._update_status("기록 조회 중...")
            self._update_progress(10)

            # 반출 실행
            result = integrity.create_export_archive(
                start_date=self.start_date_var.get(),
                end_date=self.end_date_var.get(),
                export_path=self.export_path_var.get(),
                purpose=self.purpose_var.get() or "미지정",
                exported_by=self.exporter_var.get() or "미지정"
            )

            self._update_progress(100)

            # 결과 처리
            if result.get("success"):
                self._show_success(result)
            else:
                self._show_error(result.get("message", "알 수 없는 오류"))

        except ImportError as e:
            self._show_error(f"IntegrityManager 모듈을 찾을 수 없습니다:\n{e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"반출 중 오류가 발생했습니다:\n{e}")
        finally:
            self.export_running = False
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self.export_btn.configure(state="normal"))

    def _update_status(self, text):
        """상태 텍스트 업데이트 (스레드 안전)"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: self.status_label.configure(text=text))

    def _update_progress(self, value):
        """진행률 업데이트 (스레드 안전)"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: self.progress_var.set(value))

    def _show_success(self, result):
        """성공 메시지 표시"""
        def show():
            self.status_label.configure(text="반출 완료")

            message = f"""반출이 완료되었습니다.

반출 ID: {result.get('export_id', '-')}
기록 수: {result.get('total_records', 0)}개
기간: {result.get('period', {}).get('start', '-')} ~ {result.get('period', {}).get('end', '-')}

저장 위치:
{result.get('archive_path', '-')}

해시 파일:
{result.get('hash_file_path', '-')}

아카이브 해시:
{result.get('archive_hash', '-')[:32]}..."""

            messagebox.showinfo("반출 완료", message, parent=self.dialog)

            # 반출 이력 탭으로 전환 및 새로고침
            self.notebook.select(1)  # 이력 탭 (인덱스 1)
            self._refresh_history()

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, show)

    def _show_error(self, message):
        """오류 메시지 표시"""
        def show():
            self.status_label.configure(text="반출 실패")
            messagebox.showerror("오류", message)

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, show)

    def _close(self):
        """대화상자 닫기"""
        if self.export_running:
            if not messagebox.askyesno("확인", "반출이 진행 중입니다. 중지하고 닫으시겠습니까?"):
                return
            self.export_running = False

        if self.dialog:
            self.dialog.destroy()
            self.dialog = None


def show_export_archive(parent, data_dir=None):
    """반출 대화상자 표시 (편의 함수)"""
    dialog = ExportArchiveDialog(parent, data_dir)
    dialog.show()
