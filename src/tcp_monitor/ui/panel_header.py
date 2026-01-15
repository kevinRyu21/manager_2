"""
패널 헤더 UI 컴포넌트

로고, 제목, 시계, 체감온도/불쾌지수, 컨트롤 버튼을 관리합니다.
"""

import tkinter as tk
from ..utils.helpers import find_asset, now_local, get_base_dir
from ..utils.comfort import heat_index_c, discomfort_index

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False


class PanelHeader(tk.Frame):
    """패널 헤더 - 로고, 제목, 시계, 체감온도/불쾌지수, 컨트롤 버튼"""

    def __init__(self, master, sid_key, app):
        super().__init__(master, bg="#E8F4FD", relief="raised", bd=2)
        self.app = app
        self.sid_key = sid_key

        # 체감온도/불쾌지수 변수 초기화
        self._latest_temp = None
        self._latest_hum = None
        self._connection_status = "waiting"

        # 좌측: 로고 + 제목 + 시계
        left = tk.Frame(self, bg="#E8F4FD")
        # 좌측은 확장하지 않음(체감온도/우측 컨트롤 침범 방지)
        left.pack(side="left", fill="y", expand=False)

        self.logo_imgref = None
        self.logo_label = tk.Label(left, text="", bg="#E8F4FD", fg="#2C3E50", font=("Pretendard", 12))
        self.logo_label.pack(side="left", padx=(0, 10))
        # 로고 로딩은 지연 처리 (100ms 후)
        self.after(100, self._load_logo)

        # 제목: 아이디만 표시 (ip 제거)
        base_sid = sid_key.split("@")[0].split("#")[0]
        self.title_label = tk.Label(left, text=f"{base_sid}", font=("Pretendard", 13, "bold"), bg="#E8F4FD", fg="#2C3E50")
        self.title_label.pack(side="left", padx=(0, 8))

        # 현재 화면 캡쳐 버튼 (ID 오른쪽) - 간격 축소
        self.capture_btn = tk.Button(left, text="📸 캡쳐", command=self._capture_current_screen,
                                     font=("Pretendard", 10, "bold"), bg="#3498DB", fg="#FFFFFF",
                                     relief="raised", bd=2, padx=6, pady=2,
                                     activebackground="#2E86C1", activeforeground="#FFFFFF",
                                     cursor="hand2")
        self.capture_btn.pack(side="left", padx=(0, 8))

        # (요청) 화면 캡쳐 옆 '오늘 경고' 버튼 제거

        self.clock_label = tk.Label(left, text="", font=("Pretendard", 13, "bold"), bg="#E8F4FD", fg="#2C3E50")
        self.clock_label.pack(side="left")

        # 음성 경보 토글 버튼 (시계 옆) - 간격 최적화
        # 앱 전역 상태에서 초기값 가져오기 (패널 재생성 시 상태 유지)
        self.voice_alert_enabled = getattr(app, 'global_voice_alert_enabled', True)
        initial_icon = "🔊" if self.voice_alert_enabled else "🔇"
        self.voice_toggle_btn = tk.Button(left, text=initial_icon, command=self._toggle_voice_alert,
                                        font=("Pretendard", 32, "bold"), bg="#E8F4FD", fg="#2C3E50",
                                        relief="flat", bd=0, padx=2, pady=0,
                                        activebackground="#D1E7DD", activeforeground="#2C3E50",
                                        cursor="hand2")
        self.voice_toggle_btn.pack(side="left", padx=(6, 6))

        # 거울보기/거울끄기 버튼 (카메라 화면 전체 표시) - 고정 크기 설정, 간격 축소
        self.mirror_mode = False
        self.mirror_camera_ready = False  # 카메라 준비 상태
        self.mirror_btn = tk.Button(left, text="거울 준비중", command=self._toggle_mirror_view,
                                   font=("Pretendard", 11, "bold"), bg="#9C27B0", fg="#FFFFFF",
                                   relief="raised", bd=2, width=9, height=1,  # 크기 축소
                                   activebackground="#7B1FA2", activeforeground="#FFFFFF",
                                   cursor="hand2", state="disabled")  # 초기에는 비활성화
        self.mirror_btn.pack(side="left", padx=(3, 6))

        # 모드 전환 버튼 (항상 표시) - 관리자/일반 모드 토글
        if app.cfg.admin_mode:
            # 관리자 모드일 때: 노란색 배경, "관리자" 표시
            self.mode_toggle_btn = tk.Button(left, text="🔓 관리자",
                                           font=("Pretendard", 11, "bold"), bg="#FFD700", fg="#D32F2F",
                                           relief="raised", bd=2, padx=5, pady=1,
                                           activebackground="#FFC107", activeforeground="#D32F2F",
                                           cursor="hand2",
                                           command=self._on_mode_toggle_click)
        else:
            # 일반 모드일 때: 파란색 배경, "일반모드" 표시
            self.mode_toggle_btn = tk.Button(left, text="🔒 일반모드",
                                           font=("Pretendard", 11, "bold"), bg="#3498DB", fg="#FFFFFF",
                                           relief="raised", bd=2, padx=5, pady=1,
                                           activebackground="#2980B9", activeforeground="#FFFFFF",
                                           cursor="hand2",
                                           command=self._on_mode_toggle_click)
        self.mode_toggle_btn.pack(side="left", padx=(6, 0))

        # 하위 호환성을 위한 별칭
        self.admin_mode_btn = self.mode_toggle_btn

        # 중앙: 체감온도/불쾌지수 박스 (항상 고정 위치)
        self.center_box = tk.Frame(self, bg="#D1E7DD", relief="raised", bd=2)
        self.center_box.pack(side="left", padx=10, pady=6)

        # 체감온도/불쾌지수 라벨 (중앙 박스 내부) - 반응형 크기
        self.hi_label = tk.Label(self.center_box, text="체감온도 HI: -- °C",
                                bg="#D1E7DD", fg="#2C3E50", font=("Pretendard", 18, "bold"),
                                cursor="hand2")
        self.hi_label.pack(side="left", padx=12, pady=6)

        self.di_label = tk.Label(self.center_box, text="불쾌지수 DI: --",
                                bg="#D1E7DD", fg="#2C3E50", font=("Pretendard", 18, "bold"),
                                cursor="hand2")
        self.di_label.pack(side="left", padx=12, pady=6)

        # 체감온도/불쾌지수 클릭 이벤트 바인딩
        self.hi_label.bind("<Button-1>", self._show_hi_tooltip)
        self.hi_label.bind("<Enter>", self._on_hi_enter)
        self.hi_label.bind("<Leave>", self._on_hi_leave)

        self.di_label.bind("<Button-1>", self._on_di_click)
        self.di_label.bind("<Enter>", self._on_di_enter)
        self.di_label.bind("<Leave>", self._on_di_leave)

        # 우측: 컨트롤 버튼들 - 고정 폭 (침범 방지)
        right = tk.Frame(self, bg="#E8F4FD")
        right.pack(side="right", fill="y", padx=8)

        # 오늘 경고 요약 버튼(주의/경계/심각) - 체감온도와 안전교육 사이에 위치
        self.alert_btn = tk.Button(right, text="오늘 경고 주의0 경계0 심각0", command=self._show_today_alerts,
                                   font=("Pretendard", 11, "bold"), bg="#E74C3C", fg="#FFFFFF",
                                   relief="raised", bd=2, padx=8, pady=3,
                                   activebackground="#C0392B", activeforeground="#FFFFFF",
                                   cursor="hand2", width=24, anchor='center')
        self.alert_btn.pack(side="left", padx=2)

        # 안전 교육 버튼 - 최소 크기 보장, 간격 축소
        self.btn_safety = tk.Button(right, text="안전 교육", command=lambda: master.show_safety_education(),
                                   bg="#FF9800", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                   relief="raised", bd=2, width=7, height=1,
                                   activebackground="#F57C00", activeforeground="#FFFFFF")
        self.btn_safety.pack(side="left", padx=2)

        # 모드 전환 버튼들 (타일/도면) - 그래프 모드 제거
        self.btn_card = tk.Button(right, text="타일", command=lambda: master.switch_to_card_mode(),
                                 bg="#4CAF50", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                 relief="sunken", bd=2, width=5, height=1,
                                 activebackground="#45A049", activeforeground="#FFFFFF")
        self.btn_card.pack(side="left", padx=2)

        # 그래프 버튼 제거됨 - 동적 타일 레이아웃으로 대체
        self.btn_graph = None  # 하위 호환성을 위해 None으로 유지

        self.btn_blueprint = tk.Button(right, text="도면", command=lambda: master.switch_to_blueprint_mode(),
                                      bg="#90A4AE", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                      relief="raised", bd=2, width=5, height=1,
                                      activebackground="#78909C", activeforeground="#FFFFFF")
        self.btn_blueprint.pack(side="left", padx=2)

        # 컨트롤 버튼들 표시
        self._show_control_buttons()

        # 체감온도/불쾌지수 말풍선
        self._hi_tooltip = None
        self._di_tooltip = None
        
        # 불쾌지수 DI 클릭 카운터 (7번 클릭 시 종료)
        self._di_click_count = 0
        self._di_click_reset_timer = None

        # 초기 버튼 상태 설정 (접속 대기 상태)
        self._update_button_states()

        # 시계 시작
        self.after(500, self._tick_clock)

    def _load_logo(self):
        """로고 로드"""
        if PIL_OK:
            p = find_asset("logo.png")
            if p:
                try:
                    im = Image.open(p)
                    target_h = 48
                    ratio = target_h / max(im.height, 1)
                    im = im.resize((max(int(im.width*ratio), 1), target_h), Image.LANCZOS)
                    self.logo_imgref = ImageTk.PhotoImage(im)
                    self.logo_label.configure(image=self.logo_imgref, text="", bg="#E8F4FD")
                    return
                except Exception:
                    self.logo_label.configure(text="(로고 로드 실패)", bg="#E8F4FD")
                    return
        self.logo_label.configure(image="", text="(로고 없음)", bg="#E8F4FD")

    def _show_control_buttons(self):
        """컨트롤 버튼들 표시 - 이미 pack되어 있으므로 패스"""
        pass

    def _tick_clock(self):
        """시계 업데이트"""
        self.clock_label.configure(text=now_local().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(500, self._tick_clock)

    def update_alert_count(self):
        """오늘 경고 카운트 버튼 텍스트 갱신"""
        try:
            if hasattr(self.app, 'get_today_alert_level_counts_for'):
                counts = self.app.get_today_alert_level_counts_for(self.sid_key)
                c3 = counts.get(3, 0)
                c4 = counts.get(4, 0)
                c5 = counts.get(5, 0)
                self.alert_btn.configure(text=f"오늘 경고 주의{c3} 경계{c4} 심각{c5}")
        except Exception:
            pass

    def _show_today_alerts(self):
        """오늘 경고 내역 팝업"""
        try:
            alerts = []
            if hasattr(self.app, 'get_today_alerts_for'):
                alerts = self.app.get_today_alerts_for(self.sid_key)
        except Exception:
            alerts = []

        dialog = tk.Toplevel(self.app)
        dialog.title("오늘 경고 내역")
        dialog.geometry("700x550")  # 높이 10% 확장 (500 -> 550)
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (550 // 2)
        dialog.geometry(f"700x550+{x}+{y}")  # 높이 10% 확장 (500 -> 550)

        title = tk.Label(dialog, text="오늘 경고 내역", font=("Pretendard", 18, "bold"),
                         bg="#F5F5F5", fg="#2C3E50")
        title.pack(pady=12)

        # 리스트 영역
        frame = tk.Frame(dialog, bg="#F5F5F5")
        frame.pack(fill="both", expand=True, padx=16, pady=8)

        from tkinter import ttk
        cols = ("시간", "ID", "센서", "레벨", "값")
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor='center')
        tree.pack(fill="both", expand=True)

        # 데이터 채우기
        level_map = {1:"정상",2:"관심",3:"주의",4:"경계",5:"심각"}
        for a in alerts:
            try:
                tree.insert('', 'end', values=(a.get('ts',''), a.get('sid',''), a.get('key',''), level_map.get(a.get('level',0), a.get('level')), a.get('value','')))
            except Exception:
                pass

        # 하단 버튼들: 저장, 초기화, 닫기
        btn_frame = tk.Frame(dialog, bg="#F5F5F5")
        btn_frame.pack(side="bottom", fill="x", pady=10)

        def save_alerts():
            try:
                from tkinter import filedialog, messagebox
                # 저장 파일 경로 선택 (CSV)
                path = filedialog.asksaveasfilename(
                    parent=dialog,
                    defaultextension=".csv",
                    filetypes=[["CSV 파일", "*.csv"], ["모든 파일", "*.*"]],
                    title="오늘 경고 내역 저장"
                )
                if not path:
                    return
                # CSV 저장
                import csv
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["시간", "ID", "센서", "레벨", "값"])
                    level_map = {1:"정상",2:"관심",3:"주의",4:"경계",5:"심각"}
                    for a in alerts:
                        writer.writerow([
                            a.get('ts',''),
                            a.get('sid',''),
                            a.get('key',''),
                            level_map.get(a.get('level',0), a.get('level')),
                            a.get('value','')
                        ])
                messagebox.showinfo("저장", "오늘 경고 내역이 CSV로 저장되었습니다.", parent=dialog)
            except Exception as e:
                try:
                    from tkinter import messagebox
                    messagebox.showerror("오류", f"저장 중 오류: {e}", parent=dialog)
                except Exception:
                    pass

        def reset_alerts():
            try:
                from tkinter import messagebox
                # 재확인
                if messagebox.askokcancel("초기화", "오늘 경고 내역을 모두 삭제하시겠습니까?", parent=dialog):
                    if hasattr(self.app, 'clear_today_alerts_for'):
                        ok = self.app.clear_today_alerts_for(self.sid_key)
                        if ok:
                            # 리스트 UI 비움
                            for item in tree.get_children():
                                tree.delete(item)
                            messagebox.showinfo("완료", "오늘 경고 내역이 초기화되었습니다.", parent=dialog)
                        else:
                            messagebox.showerror("오류", "초기화에 실패했습니다.", parent=dialog)
            except Exception:
                pass

        save_btn = tk.Button(btn_frame, text="저장", command=save_alerts,
                             bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                             relief="raised", bd=3, width=12, height=1,
                             activebackground="#229954", activeforeground="#FFFFFF")
        save_btn.pack(side="left", padx=8)

        reset_btn = tk.Button(btn_frame, text="초기화", command=reset_alerts,
                              bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                              relief="raised", bd=3, width=12, height=1,
                              activebackground="#C0392B", activeforeground="#FFFFFF")
        reset_btn.pack(side="left", padx=8)

        close_btn = tk.Button(btn_frame, text="닫기", command=dialog.destroy,
                              bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                              relief="raised", bd=3, width=12, height=1,
                              activebackground="#7F8C8D", activeforeground="#FFFFFF")
        close_btn.pack(side="right", padx=8)

    def _capture_current_screen(self):
        """현재 전체 화면 캡쳐 저장 (GNOME/Wayland 호환)"""
        print("[캡쳐] 캡쳐 버튼 클릭됨")
        import os
        import subprocess

        try:
            # 저장 경로 준비 (프로그램 설치 디렉토리 기준)
            base_dir = get_base_dir()
            cap_dir = os.path.join(base_dir, "captures")
            print(f"[캡쳐] 저장 경로: {cap_dir}")
            try:
                os.makedirs(cap_dir, exist_ok=True)
            except Exception:
                pass

            from ..utils.helpers import now_local
            ts = now_local().strftime("%Y%m%d_%H%M%S")
            base_sid = self.sid_key.split("@")[0].split("#")[0]
            # 파일명에서 특수문자 제거
            safe_sid = "".join(c for c in base_sid if c.isalnum() or c in "_-")
            if not safe_sid:
                safe_sid = "screen"
            filename = f"capture_{safe_sid}_{ts}.png"
            filepath = os.path.join(cap_dir, filename)
            print(f"[캡쳐] 파일명: {filename}")

            captured = False

            # flameshot full --raw > 파일 (가장 빠름)
            try:
                with open(filepath, 'wb') as f:
                    result = subprocess.run(
                        ['flameshot', 'full', '--raw'],
                        stdout=f, stderr=subprocess.PIPE, timeout=3
                    )
                if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
                    captured = True
                    print(f"[캡쳐] 저장 완료 (flameshot): {filepath}")
                else:
                    # 실패 시 파일 삭제
                    try:
                        os.unlink(filepath)
                    except:
                        pass
            except FileNotFoundError:
                print("[캡쳐] flameshot 없음 - sudo apt install flameshot")
            except Exception as e:
                print(f"[캡쳐] flameshot 오류: {e}")

            if captured:
                self._show_capture_notification(filepath)
            else:
                from tkinter import messagebox
                messagebox.showwarning(
                    "화면 캡쳐 실패",
                    "화면 캡쳐 도구를 찾을 수 없습니다.\n\n"
                    "GNOME Wayland에서 캡쳐하려면:\n"
                    "sudo apt install flameshot\n\n"
                    "또는 X11 모드로 실행하세요.",
                    parent=self.app
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[캡쳐] 오류: {e}")

    def _show_capture_notification(self, filepath):
        """캡쳐 완료 알림 (확인 버튼 클릭 시 닫기)"""
        try:
            import os
            # 알림 창 생성
            notification = tk.Toplevel(self.app)
            notification.title("캡쳐 완료")
            notification.configure(bg="#27AE60")
            notification.transient(self.app)  # 부모 창에 종속
            notification.grab_set()  # 모달 - 포커스 강제

            # 화면 중앙 배치 (하단 20% 확장: 200 -> 240)
            window_width = 450
            window_height = 240
            notification.update_idletasks()
            screen_width = notification.winfo_screenwidth()
            screen_height = notification.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            notification.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # 최상위 윈도우 설정
            try:
                notification.attributes("-topmost", True)
            except:
                pass

            # 포커스 강제
            notification.focus_force()
            notification.lift()

            # 메시지
            filename = os.path.basename(filepath)
            msg_text = f"✓ 캡쳐 완료!\n\n파일: {filename}"
            msg_label = tk.Label(notification,
                               text=msg_text,
                               font=("Pretendard", 14, "bold"),
                               fg="#FFFFFF", bg="#27AE60",
                               wraplength=400, justify="center")
            msg_label.pack(expand=True, pady=(20, 10), padx=20)

            # 확인 버튼 (하단 여백 확장)
            btn_ok = tk.Button(notification, text="확인",
                              command=notification.destroy,
                              bg="#FFFFFF", fg="#27AE60",
                              font=("Pretendard", 14, "bold"),
                              relief="raised", bd=2, width=12, height=2,
                              activebackground="#ECF0F1", activeforeground="#27AE60")
            btn_ok.pack(pady=(10, 30))
            btn_ok.focus_set()

            # Enter 키로도 닫기
            notification.bind("<Return>", lambda e: notification.destroy())

        except Exception as e:
            print(f"캡쳐 알림 표시 오류: {e}")

    def set_connection_status(self, status):
        """접속 상태 설정"""
        self._connection_status = status
        self._update_hi_di()
        self._update_button_states()

    def update_temperature(self, temp):
        """온도 업데이트"""
        try:
            self._latest_temp = float(str(temp).replace("℃", "").replace("C", "").strip())
            self._update_hi_di()
        except Exception:
            pass

    def update_humidity(self, hum):
        """습도 업데이트"""
        try:
            self._latest_hum = float(str(hum).replace("%", "").strip())
            self._update_hi_di()
        except Exception:
            pass

    def _update_button_states(self):
        """접속 상태에 따라 버튼 활성화/비활성화 - 최소 크기 보장"""
        if self._connection_status == "waiting":
            # 접속 대기 중에도 타일/안전교육/도면은 사용 가능하게 유지
            self.btn_safety.configure(state="normal", bg="#FF9800", width=8, height=1)
            self.btn_blueprint.configure(state="normal", bg="#90A4AE", width=6, height=1)
            # 타일 뷰는 접속대기 상태 표시용으로 활성화
            self.btn_card.configure(state="normal", bg="#4CAF50", width=6, height=1)
        elif self._connection_status == "disconnected":
            # 연결 끊김 상태
            self.btn_safety.configure(state="normal", bg="#FF9800", width=8, height=1)
            self.btn_card.configure(state="normal", bg="#4CAF50", width=6, height=1)
            self.btn_blueprint.configure(state="normal", bg="#90A4AE", width=6, height=1)
        else:
            # 연결됨 상태일 때는 버튼 활성화하되 최소 크기 보장
            self.btn_safety.configure(state="normal", bg="#FF9800", width=8, height=1)
            self.btn_card.configure(state="normal", bg="#4CAF50", width=6, height=1)
            self.btn_blueprint.configure(state="normal", bg="#90A4AE", width=6, height=1)

    def _update_hi_di(self):
        """체감온도/불쾌지수 업데이트"""
        t = self._latest_temp
        h = self._latest_hum
        if self._connection_status == "waiting":
            self.hi_label.configure(text="체감온도 HI: 대기중...", fg="#A0A0A0", font=("Pretendard", 14, "bold"))
            self.di_label.configure(text="불쾌지수 DI: 대기중...", fg="#A0A0A0", font=("Pretendard", 14, "bold"))
            return
        if self._connection_status == "disconnected":
            # 마지막 값이 있으면 회색으로 표시
            if t is not None and h is not None:
                hi = heat_index_c(t, h)
                di = discomfort_index(t, h)
                self.hi_label.configure(text=f"체감온도 HI: {hi} °C", fg="#808080", font=("Pretendard", 18, "bold"))
                self.di_label.configure(text=f"불쾌지수 DI: {int(di)}", fg="#808080", font=("Pretendard", 18, "bold"))
            else:
                self.hi_label.configure(text="체감온도 HI: --", fg="#808080", font=("Pretendard", 18, "bold"))
                self.di_label.configure(text="불쾌지수 DI: --", fg="#808080", font=("Pretendard", 18, "bold"))
            return
        if t is None or h is None:
            return
        hi = heat_index_c(t, h)
        di = discomfort_index(t, h)
        self.hi_label.configure(text=f"체감온도 HI: {hi} °C", fg="#2C3E50")
        self.di_label.configure(text=f"불쾌지수 DI: {int(di)}", fg="#2C3E50")

    def _show_hi_tooltip(self, event):
        """체감온도 말풍선 표시"""
        if self._hi_tooltip:
            self._hi_tooltip.destroy()

        self._hi_tooltip = tk.Toplevel(self)
        self._hi_tooltip.wm_overrideredirect(True)
        self._hi_tooltip.wm_attributes("-topmost", True)

        x = event.x_root + 10
        y = event.y_root - 10

        content = """체감온도(HI, Heat Index) 가이드:

• 27°C 미만: 쾌적
• 27-32°C: 주의 (장시간 노출/활동 시 피로 가능)
• 32-41°C: 극도 주의 (열경련, 열탈진 가능)
• 41-54°C: 위험 (열경련, 열탈진 가능성 높음)
• 54°C 이상: 극도 위험 (열사병 위험)

체감온도는 온도와 습도를 함께 고려하여
실제로 느껴지는 더위의 정도를 나타냅니다.

계산식: Steadman의 Heat Index 공식 사용
(온도와 상대습도 기반)"""

        tooltip_label = tk.Label(self._hi_tooltip, text=content,
                               bg="#FFEBCD", fg="#000000",
                               font=("Pretendard", 9),
                               justify="left", relief="solid", bd=1)
        tooltip_label.pack(padx=5, pady=5)

        self._hi_tooltip.wm_geometry(f"+{x}+{y}")
        self.after(5000, self._hide_hi_tooltip)

    def _hide_hi_tooltip(self):
        """체감온도 말풍선 숨기기"""
        if self._hi_tooltip:
            self._hi_tooltip.destroy()
            self._hi_tooltip = None

    def _on_hi_enter(self, event):
        """체감온도 마우스 진입"""
        self.hi_label.configure(fg="#FF6B9D")

    def _on_hi_leave(self, event):
        """체감온도 마우스 벗어남"""
        self.hi_label.configure(fg="#2C3E50")

    def _show_di_tooltip(self, event):
        """불쾌지수 말풍선 표시"""
        if self._di_tooltip:
            self._di_tooltip.destroy()

        self._di_tooltip = tk.Toplevel(self)
        self._di_tooltip.wm_overrideredirect(True)
        self._di_tooltip.wm_attributes("-topmost", True)

        x = event.x_root + 10
        y = event.y_root - 10

        content = """불쾌지수(DI) 가이드:

• 70 이하: 쾌적함
• 70-75: 약간 불쾌
• 75-80: 불쾌함
• 80-85: 매우 불쾌
• 85 이상: 극도로 불쾌

계산식: DI = 0.81×T + 0.01×R×(0.99×T-14.3) + 46.3
T: 온도(℃), R: 상대습도(%)"""

        tooltip_label = tk.Label(self._di_tooltip, text=content,
                               bg="#FFFFCC", fg="#000000",
                               font=("Pretendard", 9),
                               justify="left", relief="solid", bd=1)
        tooltip_label.pack(padx=5, pady=5)

        self._di_tooltip.wm_geometry(f"+{x}+{y}")
        self.after(5000, self._hide_di_tooltip)

    def _hide_di_tooltip(self):
        """불쾌지수 말풍선 숨기기"""
        if self._di_tooltip:
            self._di_tooltip.destroy()
            self._di_tooltip = None

    def _on_di_enter(self, event):
        """불쾌지수 마우스 진입"""
        self.di_label.configure(fg="#FF6B9D")

    def _on_di_leave(self, event):
        """불쾌지수 마우스 벗어남"""
        self.di_label.configure(fg="#2C3E50")

    def _on_di_click(self, event):
        """불쾌지수 DI 클릭 이벤트 처리 - 7번 클릭 시 종료"""
        # 클릭 카운터 증가
        self._di_click_count += 1
        
        # 3초 후 카운터 리셋 타이머
        if self._di_click_reset_timer:
            self.after_cancel(self._di_click_reset_timer)
        self._di_click_reset_timer = self.after(3000, self._reset_di_click_count)
        
        # 7번 클릭 시 종료 확인
        if self._di_click_count >= 7:
            self._reset_di_click_count()
            self._check_and_exit()
        else:
            # 7번 미만이면 기존 말풍선 표시
            self._show_di_tooltip(event)
    
    def _reset_di_click_count(self):
        """불쾌지수 DI 클릭 카운터 리셋"""
        self._di_click_count = 0
        self._di_click_reset_timer = None
    
    def _check_and_exit(self):
        """종료 확인 및 프로그램 종료"""
        try:
            # 패치되지 않은 원본 messagebox를 사용하기 위해 직접 _show 호출
            import tkinter.messagebox
            # 원본 _show 함수를 직접 사용하여 패치 우회
            try:
                result = tkinter.messagebox._show(
                    "종료 확인", 
                    "종료하시겠습니까?", 
                    tkinter.messagebox.QUESTION, 
                    tkinter.messagebox.OKCANCEL,
                    parent=self.app
                )
                # OK 버튼이 클릭되었는지 확인
                if result == tkinter.messagebox.OK:
                    # 정상 종료 절차 실행
                    if hasattr(self.app, 'exit_app'):
                        self.app.exit_app()
                    else:
                        self.app.quit()
                        self.app.destroy()
                # 취소 버튼 클릭 시는 아무것도 하지 않음 (종료 안 함)
            except AttributeError:
                # _show가 없으면 다른 방법 시도
                import importlib
                import tkinter.messagebox
                importlib.reload(tkinter.messagebox)
                result = tkinter.messagebox.askokcancel("종료 확인", "종료하시겠습니까?", parent=self.app)
                if result:
                    if hasattr(self.app, 'exit_app'):
                        self.app.exit_app()
                    else:
                        self.app.quit()
                        self.app.destroy()
        except Exception as e:
            print(f"종료 오류: {e}")

    def update_mode_buttons(self, current_mode):
        """모드 버튼 상태 업데이트 - 최소 크기 보장"""
        # 모든 버튼을 기본 상태로 변경하되 최소 크기 보장
        self.btn_card.configure(bg="#90A4AE", relief="raised", width=6, height=1)
        self.btn_blueprint.configure(bg="#90A4AE", relief="raised", width=6, height=1)

        # 현재 모드 버튼을 활성화 상태로 변경하되 최소 크기 보장
        if current_mode == "card":
            self.btn_card.configure(bg="#4CAF50", relief="sunken", width=6, height=1)
            # 타일 모드에서만 거울보기 활성화
            if self.mirror_camera_ready:
                self.mirror_btn.configure(state="normal")
        elif current_mode == "blueprint":
            self.btn_blueprint.configure(bg="#4CAF50", relief="sunken", width=6, height=1)
            # 도면 모드에서 거울보기 비활성화
            self.mirror_btn.configure(state="disabled")

    def update_admin_mode_indicator(self):
        """관리자 모드 표시 업데이트 - 버튼 스타일 변경"""
        if self.app.cfg.admin_mode:
            # 관리자 모드: 노란색 배경
            self.mode_toggle_btn.configure(
                text="🔓 관리자",
                bg="#FFD700", fg="#D32F2F",
                activebackground="#FFC107", activeforeground="#D32F2F"
            )
        else:
            # 일반 모드: 파란색 배경
            self.mode_toggle_btn.configure(
                text="🔒 일반모드",
                bg="#3498DB", fg="#FFFFFF",
                activebackground="#2980B9", activeforeground="#FFFFFF"
            )

    def _on_mode_toggle_click(self):
        """모드 전환 버튼 클릭 시 - 관리자/일반 모드 전환"""
        if self.app.cfg.admin_mode:
            # 관리자 → 일반 모드: 확인 다이얼로그
            self._show_exit_admin_dialog()
        else:
            # 일반 → 관리자 모드: 암호 입력
            self.app.enter_admin_mode()

    def _show_exit_admin_dialog(self):
        """관리자 모드 종료 확인 다이얼로그 (20% 확장)"""
        dialog = tk.Toplevel(self.app)
        dialog.title("일반 모드 전환")
        dialog.geometry("500x290")  # 20% 확장 (220 -> 264 -> 290)
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self.app)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (145)
        dialog.geometry(f"500x290+{x}+{y}")

        result = [False]

        # 제목
        tk.Label(dialog, text="일반 모드 전환",
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=25)

        # 메시지
        tk.Label(dialog, text="관리자 모드를 종료하고\n일반 모드로 전환하시겠습니까?",
                font=("Pretendard", 13), bg="#F5F5F5", fg="#2C3E50",
                justify="center").pack(pady=20)

        # 버튼 프레임
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=30, padx=40)

        def on_yes():
            result[0] = True
            dialog.destroy()

        def on_no():
            dialog.destroy()

        tk.Button(button_frame, text="✓ 예", command=on_yes,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=5, ipady=15)

        tk.Button(button_frame, text="✕ 아니오", command=on_no,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5, ipady=15)

        dialog.wait_window()

        if result[0]:
            self.app.exit_admin_mode()

    def _on_admin_mode_click(self):
        """하위 호환성을 위한 메서드 (기존 코드 호환)"""
        self._on_mode_toggle_click()

    def _toggle_voice_alert(self):
        """음성 경보 토글"""
        self.voice_alert_enabled = not self.voice_alert_enabled
        # 전역 상태도 업데이트 (패널 재생성 시 상태 유지)
        if hasattr(self.app, 'global_voice_alert_enabled'):
            self.app.global_voice_alert_enabled = self.voice_alert_enabled
        if self.voice_alert_enabled:
            self.voice_toggle_btn.configure(text="🔊")
            # 경고음 테스트
            self._test_voice_alert()
        else:
            self.voice_toggle_btn.configure(text="🔇")

        # 모든 패널의 타일에서 음성 경보 상태 업데이트
        for panel in self.app.panels.values():
            if hasattr(panel, 'tiles_container') and hasattr(panel.tiles_container, '_voice_alert_enabled'):
                panel.tiles_container._voice_alert_enabled = self.voice_alert_enabled
            # AlertManager의 TTS 상태도 업데이트
            if hasattr(panel, 'alert_manager'):
                if self.voice_alert_enabled:
                    panel.alert_manager.enable_tts()
                else:
                    panel.alert_manager.disable_tts()
                    # 큐에 있는 메시지도 비움
                    try:
                        while not panel.alert_manager._tts_queue.empty():
                            panel.alert_manager._tts_queue.get_nowait()
                            panel.alert_manager._tts_queue.task_done()
                    except Exception:
                        pass

        # 음성 끄면 현재 재생 중인 오디오도 중지
        if not self.voice_alert_enabled:
            try:
                from ..sensor.alerts import _stop_current_audio
                _stop_current_audio()
            except Exception:
                pass
    
    def _toggle_mirror_view(self):
        """거울보기/거울끄기 토글 - 카메라 화면을 타일 영역 전체에 표시"""
        if not self.mirror_camera_ready and not self.mirror_mode:
            return  # 카메라가 준비되지 않았으면 동작 안 함

        # 그래프/도면 모드에서는 거울보기 활성화 불가 (끄기만 가능)
        current_view_mode = getattr(self.master, 'view_mode', 'card') if hasattr(self, 'master') else 'card'
        if current_view_mode != "card" and not self.mirror_mode:
            return  # 타일 모드가 아니면 거울보기 시작 불가

        self.mirror_mode = not self.mirror_mode
        if self.mirror_mode:
            self.mirror_btn.configure(text="거울끄기", bg="#F44336")
            # 거울 모드 활성화 - 패널에 카메라 화면 표시 요청
            if hasattr(self, 'master') and hasattr(self.master, 'show_mirror_view'):
                self.master.show_mirror_view()
        else:
            # 카메라가 준비되었으면 "거울보기", 준비 안 되었으면 "거울 준비중"
            if self.mirror_camera_ready:
                self.mirror_btn.configure(text="거울보기", bg="#9C27B0")
            else:
                self.mirror_btn.configure(text="거울 준비중", bg="#9C27B0", state="disabled")
            # 거울 모드 비활성화 - 원래 화면으로 복귀
            if hasattr(self, 'master') and hasattr(self.master, 'hide_mirror_view'):
                self.master.hide_mirror_view()
    
    def set_mirror_camera_ready(self, ready):
        """카메라 준비 상태 설정 및 버튼 상태 업데이트"""
        # 상태가 변경될 때만 업데이트 (떨림 방지)
        if self.mirror_camera_ready == ready:
            return

        self.mirror_camera_ready = ready

        # 현재 뷰 모드 확인 - 그래프/도면에서는 거울보기 비활성화
        current_view_mode = getattr(self.master, 'view_mode', 'card') if hasattr(self, 'master') else 'card'
        is_tile_mode = current_view_mode == "card"

        if ready:
            # 카메라 준비됨 - 타일 모드일 때만 버튼 활성화
            if not self.mirror_mode:
                if is_tile_mode:
                    self.mirror_btn.configure(text="거울보기", bg="#9C27B0", state="normal")
                else:
                    self.mirror_btn.configure(text="거울보기", bg="#9C27B0", state="disabled")
        else:
            # 카메라 준비 안 됨 - 버튼 비활성화
            if not self.mirror_mode:
                self.mirror_btn.configure(text="거울 준비중", bg="#9C27B0", state="disabled")
    
    def _test_voice_alert(self):
        """경고음 테스트"""
        try:
            # Windows 내장 경고음 테스트
            import winsound
            winsound.Beep(1000, 300)
            winsound.Beep(1200, 200)
            print("경고음 테스트 완료")
        except Exception as e:
            print(f"경고음 테스트 실패: {e}")
            try:
                # 대체 경고음
                winsound.MessageBeep(0x00000030)
                print("대체 경고음 테스트 완료")
            except Exception as e2:
                print(f"대체 경고음도 실패: {e2}")
