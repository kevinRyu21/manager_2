#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARAMe Manager 라이선스 키 생성기 GUI

관리자용 키 생성 도구 (GUI 버전)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
from datetime import datetime

# generator 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator import LicenseKeyGenerator, LicenseType


class LicenseGeneratorGUI:
    """라이선스 키 생성기 GUI"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("GARAMe Manager 라이선스 키 생성기")
        self.root.geometry("600x700")
        self.root.resizable(False, False)

        # 생성기 인스턴스
        self.generator = LicenseKeyGenerator()

        # 생성된 키 목록
        self.generated_keys = []

        self._setup_ui()

    def _setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_label = ttk.Label(
            main_frame,
            text="GARAMe Manager 라이선스 키 생성기",
            font=("맑은 고딕", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # ===== 라이선스 타입 선택 =====
        type_frame = ttk.LabelFrame(main_frame, text="라이선스 타입", padding="10")
        type_frame.pack(fill=tk.X, pady=(0, 10))

        self.license_type = tk.StringVar(value="trial")

        types = [
            ("trial", "테스트 키 (7일)"),
            ("timed", "기간 제한 키"),
            ("perpetual", "영구 키"),
            ("version", "버전 제한 키")
        ]

        for value, text in types:
            rb = ttk.Radiobutton(
                type_frame,
                text=text,
                value=value,
                variable=self.license_type,
                command=self._on_type_changed
            )
            rb.pack(anchor=tk.W, pady=2)

        # 기간 제한 설정 프레임
        self.days_frame = ttk.Frame(type_frame)
        self.days_frame.pack(fill=tk.X, padx=(20, 0), pady=5)

        ttk.Label(self.days_frame, text="유효 기간:").pack(side=tk.LEFT)
        self.days_var = tk.StringVar(value="30")
        self.days_entry = ttk.Entry(self.days_frame, textvariable=self.days_var, width=10)
        self.days_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.days_frame, text="일").pack(side=tk.LEFT)

        # 버전 제한 설정 프레임
        self.version_frame = ttk.Frame(type_frame)
        self.version_frame.pack(fill=tk.X, padx=(20, 0), pady=5)

        ttk.Label(self.version_frame, text="최대 버전:").pack(side=tk.LEFT)
        self.version_var = tk.StringVar(value="1.9.8.4")
        self.version_entry = ttk.Entry(self.version_frame, textvariable=self.version_var, width=15)
        self.version_entry.pack(side=tk.LEFT, padx=5)

        # 초기 상태 설정
        self._on_type_changed()

        # ===== 고객 정보 =====
        customer_frame = ttk.LabelFrame(main_frame, text="고객 정보", padding="10")
        customer_frame.pack(fill=tk.X, pady=(0, 10))

        # 고객 ID
        id_frame = ttk.Frame(customer_frame)
        id_frame.pack(fill=tk.X, pady=2)
        ttk.Label(id_frame, text="고객 ID:", width=10).pack(side=tk.LEFT)
        self.customer_id_var = tk.StringVar(value="1")
        ttk.Entry(id_frame, textvariable=self.customer_id_var, width=20).pack(side=tk.LEFT, padx=5)

        # 회사명
        company_frame = ttk.Frame(customer_frame)
        company_frame.pack(fill=tk.X, pady=2)
        ttk.Label(company_frame, text="회사명:", width=10).pack(side=tk.LEFT)
        self.company_var = tk.StringVar()
        ttk.Entry(company_frame, textvariable=self.company_var, width=30).pack(side=tk.LEFT, padx=5)

        # 담당자
        contact_frame = ttk.Frame(customer_frame)
        contact_frame.pack(fill=tk.X, pady=2)
        ttk.Label(contact_frame, text="담당자:", width=10).pack(side=tk.LEFT)
        self.contact_var = tk.StringVar()
        ttk.Entry(contact_frame, textvariable=self.contact_var, width=30).pack(side=tk.LEFT, padx=5)

        # 비고
        note_frame = ttk.Frame(customer_frame)
        note_frame.pack(fill=tk.X, pady=2)
        ttk.Label(note_frame, text="비고:", width=10).pack(side=tk.LEFT)
        self.note_var = tk.StringVar()
        ttk.Entry(note_frame, textvariable=self.note_var, width=40).pack(side=tk.LEFT, padx=5)

        # ===== 생성 옵션 =====
        option_frame = ttk.LabelFrame(main_frame, text="생성 옵션", padding="10")
        option_frame.pack(fill=tk.X, pady=(0, 10))

        count_frame = ttk.Frame(option_frame)
        count_frame.pack(fill=tk.X)
        ttk.Label(count_frame, text="생성 수량:").pack(side=tk.LEFT)
        self.count_var = tk.StringVar(value="1")
        self.count_spinbox = ttk.Spinbox(
            count_frame,
            from_=1,
            to=100,
            textvariable=self.count_var,
            width=10
        )
        self.count_spinbox.pack(side=tk.LEFT, padx=5)

        # ===== 버튼 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.generate_btn = ttk.Button(
            btn_frame,
            text="🔑 키 생성",
            command=self._generate_keys,
            width=15
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        self.copy_btn = ttk.Button(
            btn_frame,
            text="📋 복사",
            command=self._copy_to_clipboard,
            width=10
        )
        self.copy_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(
            btn_frame,
            text="💾 CSV 내보내기",
            command=self._export_csv,
            width=15
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(
            btn_frame,
            text="🗑 초기화",
            command=self._clear_keys,
            width=10
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # ===== 생성된 키 목록 =====
        result_frame = ttk.LabelFrame(main_frame, text="생성된 키", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 스크롤바
        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 텍스트 위젯
        self.result_text = tk.Text(
            result_frame,
            height=10,
            font=("Consolas", 11),
            yscrollcommand=scrollbar.set
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.result_text.yview)

        # 상태 표시줄
        self.status_var = tk.StringVar(value="준비됨")
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_label.pack(fill=tk.X, pady=(10, 0))

    def _on_type_changed(self):
        """라이선스 타입 변경 시"""
        license_type = self.license_type.get()

        # 기간 제한 설정 표시/숨김
        if license_type in ['trial', 'timed']:
            self.days_frame.pack(fill=tk.X, padx=(20, 0), pady=5)
            if license_type == 'trial':
                self.days_var.set("7")
                self.days_entry.config(state='disabled')
            else:
                self.days_var.set("30")
                self.days_entry.config(state='normal')
        else:
            self.days_frame.pack_forget()

        # 버전 제한 설정 표시/숨김
        if license_type == 'version':
            self.version_frame.pack(fill=tk.X, padx=(20, 0), pady=5)
        else:
            self.version_frame.pack_forget()

    def _generate_keys(self):
        """키 생성"""
        try:
            license_type = self.license_type.get()
            count = int(self.count_var.get())
            customer_id = int(self.customer_id_var.get() or "0")
            days = int(self.days_var.get() or "7")
            version = self.version_var.get() or "1.9.8.4"

            # 고객 정보
            company = self.company_var.get()
            contact = self.contact_var.get()
            note = self.note_var.get()

            new_keys = []
            for i in range(count):
                cid = customer_id + i

                if license_type == 'trial':
                    key = self.generator.generate_trial_key(cid, days)
                    type_text = f"테스트 ({days}일)"
                elif license_type == 'timed':
                    key = self.generator.generate_timed_key(cid, days)
                    type_text = f"기간 제한 ({days}일)"
                elif license_type == 'perpetual':
                    key = self.generator.generate_perpetual_key(cid)
                    type_text = "영구"
                elif license_type == 'version':
                    key = self.generator.generate_version_key(cid, version)
                    type_text = f"버전 제한 (최대 {version})"

                new_keys.append({
                    'key': key,
                    'type': type_text,
                    'customer_id': cid,
                    'company': company,
                    'contact': contact,
                    'note': note,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            self.generated_keys.extend(new_keys)

            # 결과 표시
            self.result_text.insert(tk.END, f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            for item in new_keys:
                self.result_text.insert(tk.END, f"[{item['type']}] {item['key']}\n")
            self.result_text.see(tk.END)

            self.status_var.set(f"{len(new_keys)}개 키 생성 완료 (총 {len(self.generated_keys)}개)")

        except Exception as e:
            messagebox.showerror("오류", f"키 생성 실패: {e}")

    def _copy_to_clipboard(self):
        """클립보드 복사"""
        if not self.generated_keys:
            messagebox.showwarning("경고", "생성된 키가 없습니다.")
            return

        # 키만 추출
        keys = [item['key'] for item in self.generated_keys]
        text = "\n".join(keys)

        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        self.status_var.set(f"{len(keys)}개 키가 클립보드에 복사되었습니다.")

    def _export_csv(self):
        """CSV 내보내기"""
        if not self.generated_keys:
            messagebox.showwarning("경고", "생성된 키가 없습니다.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
            initialfilename=f"license_keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not filepath:
            return

        try:
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['key', 'type', 'customer_id', 'company', 'contact', 'note', 'created_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.generated_keys)

            self.status_var.set(f"CSV 내보내기 완료: {filepath}")
            messagebox.showinfo("완료", f"CSV 파일이 저장되었습니다.\n\n{filepath}")
        except Exception as e:
            messagebox.showerror("오류", f"CSV 내보내기 실패: {e}")

    def _clear_keys(self):
        """초기화"""
        if self.generated_keys:
            if not messagebox.askyesno("확인", "생성된 키를 모두 삭제하시겠습니까?"):
                return

        self.generated_keys.clear()
        self.result_text.delete(1.0, tk.END)
        self.status_var.set("초기화됨")


def main():
    """메인 함수"""
    root = tk.Tk()

    # 아이콘 설정 (있으면)
    try:
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "logo.ico"
        )
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    app = LicenseGeneratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
