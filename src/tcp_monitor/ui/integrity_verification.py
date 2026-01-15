"""
무결성 검증 다이얼로그

안전교육 기록의 해시 체인 무결성을 검증하고 결과를 표시합니다.
(특허 청구항 9 관련)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
from datetime import datetime

from ..utils.helpers import get_base_dir


class IntegrityVerificationDialog:
    """무결성 검증 대화상자"""

    def __init__(self, parent, data_dir: str = None):
        """
        무결성 검증 대화상자 초기화

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
        self.result_tree = None
        self.status_label = None
        self.progress_var = None
        self.progress_bar = None
        self.verification_running = False

        # 검증 결과 저장
        self.verification_result = None

    def show(self):
        """대화상자 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("무결성 검증")
        self.dialog.geometry("900x700")
        self.dialog.minsize(800, 600)

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
            text="안전교육 기록 무결성 검증",
            font=("Pretendard", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        # 설명
        desc_label = ttk.Label(
            main_frame,
            text="해시 체인을 검증하여 기록의 위변조 여부를 확인합니다.\n"
                 "각 기록의 파일 해시와 체인 연결 상태를 검사합니다.",
            font=("Pretendard", 10),
            justify="center"
        )
        desc_label.pack(pady=(0, 15))

        # 검증 범위 선택 프레임
        scope_frame = ttk.LabelFrame(main_frame, text="검증 범위", padding=10)
        scope_frame.pack(fill="x", pady=(0, 10))

        self.scope_var = tk.StringVar(value="all")

        ttk.Radiobutton(
            scope_frame, text="전체 검증 (모든 기록)",
            variable=self.scope_var, value="all"
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            scope_frame, text="최근 기록만 (최근 100개)",
            variable=self.scope_var, value="recent"
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            scope_frame, text="오류 기록만 재검증",
            variable=self.scope_var, value="errors_only"
        ).pack(side="left", padx=10)

        # 버튼 프레임
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        self.verify_btn = ttk.Button(
            btn_frame,
            text="검증 시작",
            command=self._start_verification,
            width=15
        )
        self.verify_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(
            btn_frame,
            text="중지",
            command=self._stop_verification,
            state="disabled",
            width=10
        )
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="결과 저장",
            command=self._save_result,
            width=12
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="닫기",
            command=self._close,
            width=10
        ).pack(side="right", padx=5)

        # 진행 상태 프레임
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=5)

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
            length=300
        )
        self.progress_bar.pack(side="right", padx=10)

        # 결과 요약 프레임
        summary_frame = ttk.LabelFrame(main_frame, text="검증 결과 요약", padding=10)
        summary_frame.pack(fill="x", pady=10)

        # 요약 정보 그리드
        self.summary_labels = {}

        summary_items = [
            ("total", "전체 기록:"),
            ("verified", "검증 통과:"),
            ("failed", "검증 실패:"),
            ("missing", "파일 누락:"),
            ("chain_broken", "체인 단절:")
        ]

        for i, (key, label_text) in enumerate(summary_items):
            ttk.Label(summary_frame, text=label_text).grid(row=0, column=i*2, padx=5, pady=5, sticky="e")
            self.summary_labels[key] = ttk.Label(summary_frame, text="-", font=("Pretendard", 11, "bold"))
            self.summary_labels[key].grid(row=0, column=i*2+1, padx=5, pady=5, sticky="w")

        # 결과 목록 (Treeview)
        result_frame = ttk.LabelFrame(main_frame, text="상세 결과", padding=5)
        result_frame.pack(fill="both", expand=True, pady=5)

        # Treeview 생성 (연번 컬럼 추가)
        columns = ("no", "record_id", "person", "timestamp", "status", "details")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)

        # 컬럼 설정
        self.result_tree.heading("no", text="연번")
        self.result_tree.heading("record_id", text="기록 ID")
        self.result_tree.heading("person", text="이름")
        self.result_tree.heading("timestamp", text="기록 일시")
        self.result_tree.heading("status", text="상태")
        self.result_tree.heading("details", text="상세 정보")

        self.result_tree.column("no", width=50, anchor="center")
        self.result_tree.column("record_id", width=180, anchor="w")
        self.result_tree.column("person", width=100, anchor="center")
        self.result_tree.column("timestamp", width=150, anchor="center")
        self.result_tree.column("status", width=80, anchor="center")
        self.result_tree.column("details", width=280, anchor="w")

        # 스크롤바
        scrollbar_y = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_tree.yview)
        scrollbar_x = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # 배치
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        # 태그 설정 (색상)
        self.result_tree.tag_configure("pass", background="#D5F5E3")  # 연한 녹색
        self.result_tree.tag_configure("fail", background="#FADBD8")  # 연한 빨간색
        self.result_tree.tag_configure("missing", background="#FCF3CF")  # 연한 노란색
        self.result_tree.tag_configure("chain_error", background="#E8DAEF")  # 연한 보라색

        # 더블클릭 이벤트
        self.result_tree.bind("<Double-1>", self._on_item_double_click)

    def _start_verification(self):
        """검증 시작"""
        if self.verification_running:
            return

        self.verification_running = True
        self.verify_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        # 결과 초기화
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        for key in self.summary_labels:
            self.summary_labels[key].configure(text="-")

        self.progress_var.set(0)
        self.status_label.configure(text="검증 준비 중...")

        # 백그라운드 스레드에서 검증 실행
        thread = threading.Thread(target=self._run_verification, daemon=True)
        thread.start()

    def _run_verification(self):
        """검증 실행 (백그라운드 스레드)"""
        try:
            from ..utils.integrity_manager import IntegrityManager

            # IntegrityManager 초기화
            integrity = IntegrityManager(self.data_dir)

            # 검증 범위 확인
            scope = self.scope_var.get()

            # UI 업데이트 (메인 스레드에서)
            self._update_status("해시 체인 로드 중...")

            # 전체 검증 실행
            if scope == "all":
                result = integrity.verify_all()
            elif scope == "recent":
                result = integrity.verify_all(limit=100)
            else:  # errors_only
                result = integrity.verify_all(errors_only=True)

            self.verification_result = result

            # 결과 표시 (메인 스레드에서)
            self._update_results(result)

        except ImportError as e:
            self._show_error(f"IntegrityManager 모듈을 찾을 수 없습니다:\n{e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"검증 중 오류가 발생했습니다:\n{e}")
        finally:
            self.verification_running = False
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, self._verification_complete)

    def _update_status(self, text):
        """상태 텍스트 업데이트 (스레드 안전)"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: self.status_label.configure(text=text))

    def _update_progress(self, value):
        """진행률 업데이트 (스레드 안전)"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: self.progress_var.set(value))

    def _update_results(self, result):
        """검증 결과 표시 (메인 스레드에서 호출)"""
        if not self.dialog or not self.dialog.winfo_exists():
            return

        def update():
            # 요약 정보 업데이트
            summary = result.get("summary", {})
            self.summary_labels["total"].configure(text=str(summary.get("total_records", 0)))
            self.summary_labels["verified"].configure(
                text=str(summary.get("verified", 0)),
                foreground="green" if summary.get("verified", 0) > 0 else "black"
            )
            self.summary_labels["failed"].configure(
                text=str(summary.get("failed", 0)),
                foreground="red" if summary.get("failed", 0) > 0 else "black"
            )
            self.summary_labels["missing"].configure(
                text=str(summary.get("missing_files", 0)),
                foreground="orange" if summary.get("missing_files", 0) > 0 else "black"
            )
            self.summary_labels["chain_broken"].configure(
                text=str(summary.get("chain_broken", 0)),
                foreground="purple" if summary.get("chain_broken", 0) > 0 else "black"
            )

            # 상세 결과 표시
            records = result.get("records", [])
            total = len(records)

            for i, record in enumerate(records):
                # 진행률 업데이트
                progress = (i + 1) / total * 100 if total > 0 else 100
                self.progress_var.set(progress)

                # 상태 태그 결정
                status = record.get("status", "unknown")
                if status == "verified":
                    tag = "pass"
                    status_text = "통과"
                elif status == "failed":
                    tag = "fail"
                    status_text = "실패"
                elif status == "missing":
                    tag = "missing"
                    status_text = "누락"
                elif status == "chain_error":
                    tag = "chain_error"
                    status_text = "체인오류"
                else:
                    tag = ""
                    status_text = status

                # Treeview에 추가 (연번 포함)
                self.result_tree.insert(
                    "",
                    "end",
                    values=(
                        i + 1,  # 연번
                        record.get("record_id", "-"),
                        record.get("person_name", "-"),
                        record.get("timestamp", "-"),
                        status_text,
                        record.get("details", "-")
                    ),
                    tags=(tag,)
                )

            # 완료 상태
            self.progress_var.set(100)

            if summary.get("failed", 0) == 0 and summary.get("chain_broken", 0) == 0:
                self.status_label.configure(text="검증 완료 - 모든 기록이 정상입니다.")
            else:
                self.status_label.configure(text=f"검증 완료 - {summary.get('failed', 0)}개 실패, {summary.get('chain_broken', 0)}개 체인 오류")

        self.dialog.after(0, update)

    def _verification_complete(self):
        """검증 완료 후 처리"""
        self.verify_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _stop_verification(self):
        """검증 중지"""
        self.verification_running = False
        self.status_label.configure(text="검증이 중지되었습니다.")
        self.verify_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _save_result(self):
        """검증 결과 저장"""
        if not self.verification_result:
            messagebox.showwarning("알림", "저장할 검증 결과가 없습니다.\n먼저 검증을 실행해주세요.",
                                  parent=self.dialog)
            return

        from tkinter import filedialog
        import json

        # 기본 저장 디렉토리: 설치 경로/integrity
        install_dir = get_base_dir()
        integrity_dir = os.path.join(install_dir, "integrity")
        if not os.path.exists(integrity_dir):
            os.makedirs(integrity_dir, exist_ok=True)

        # 다이얼로그를 최상위로 올려서 파일 다이얼로그가 앞에 표시되도록
        self.dialog.attributes("-topmost", True)
        self.dialog.update()

        # 저장 경로 선택 (parent 지정으로 포커스 유지)
        filepath = filedialog.asksaveasfilename(
            title="검증 결과 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            initialdir=integrity_dir,
            parent=self.dialog
        )

        # topmost 해제
        self.dialog.attributes("-topmost", False)

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.verification_result, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("완료", f"검증 결과가 저장되었습니다:\n{filepath}",
                                   parent=self.dialog)
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 중 오류가 발생했습니다:\n{e}",
                                    parent=self.dialog)

    def _on_item_double_click(self, event):
        """항목 더블클릭 시 상세 정보 표시"""
        selection = self.result_tree.selection()
        if not selection:
            return

        item = self.result_tree.item(selection[0])
        values = item.get("values", [])

        if len(values) >= 5:
            record_id = values[0]
            person = values[1]
            timestamp = values[2]
            status = values[3]
            details = values[4]

            detail_text = f"""
기록 ID: {record_id}
이름: {person}
기록 일시: {timestamp}
검증 상태: {status}
상세 정보: {details}
            """.strip()

            messagebox.showinfo("기록 상세 정보", detail_text)

    def _show_error(self, message):
        """오류 메시지 표시"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: messagebox.showerror("오류", message))

    def _close(self):
        """대화상자 닫기"""
        if self.verification_running:
            if not messagebox.askyesno("확인", "검증이 진행 중입니다. 중지하고 닫으시겠습니까?"):
                return
            self.verification_running = False

        if self.dialog:
            self.dialog.destroy()
            self.dialog = None


def show_integrity_verification(parent, data_dir=None):
    """무결성 검증 대화상자 표시 (편의 함수)"""
    dialog = IntegrityVerificationDialog(parent, data_dir)
    dialog.show()
