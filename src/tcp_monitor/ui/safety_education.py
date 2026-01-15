"""
안전 교육 UI 컴포넌트

안전 교육 포스터 뷰어와 웹캠 확인 기능을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime

# OpenCV 카메라 로딩 최적화를 위한 환경 변수 설정 (cv2 import 전에 설정)
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

# 플랫폼별 어댑터 사용
from ..platform import CameraBackend
from ..utils.helpers import get_base_dir, get_data_dir

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

try:
    import cv2
    CV2_OK = True
except Exception:
    CV2_OK = False


class SafetyEducationDialog:
    """안전 교육 오버레이"""

    # 권장 포스터 이미지 크기: 800x1000 픽셀 (세로형)
    POSTER_WIDTH = 800
    POSTER_HEIGHT = 1000

    def __init__(self, parent_frame, config, app=None):
        self.parent_frame = parent_frame  # SensorPanel의 메인 프레임
        self.config = config
        self.app = app  # 메인 앱 (탭 숨기기용)
        self.overlay = None
        self.camera = None
        self.camera_label = None
        self.poster_images = []  # PIL Image 객체 리스트
        self.poster_tk_images = []  # PhotoImage 객체 리스트 (참조 유지용)
        self.current_page = 0
        self.viewed_pages = set()  # 본 페이지 추적
        self.confirm_btn = None
        self.camera_running = False

        # 플랫폼별 카메라 백엔드 초기화
        self.camera_backend = CameraBackend()
        self.zoom_factor = 1.2  # 확대 비율 (1.2 = 20% 확대)
        self.safety_detector = None  # 얼굴 인식 감지기

        # 백그라운드 AI 감지 관련
        self.ai_frame_count = 0  # AI 감지 주기 카운터
        self.ai_detection_interval = 15  # 15프레임마다 AI 감지 (약 2fps)
        self.last_detection_results = None  # 마지막 AI 감지 결과
        self.ai_thread_running = False  # AI 스레드 실행 중 여부

        # PPE 감지기 관련 (YOLOv10 기반)
        self.ppe_detector = None
        self.ppe_visualizer = None
        self._ppe_status_cache = None
        self._ppe_detections_cache = None

        # ID 추적 관련 (거울보기와 동일하게 - 마스크/얼굴 돌림 시 유지)
        self._tracked_persons = {}  # {track_id: {'name': str, 'bbox': (x1,y1,x2,y2), 'last_seen': time, 'confidence': float, 'center': (cx, cy)}}
        self._next_track_id = 1
        self._track_iou_threshold = 0.15  # 추적 IOU 임계값
        self._track_timeout = None  # 타임아웃 없음 - 한번 인식하면 영구 추적
        self._track_center_dist_threshold = 200  # 중심점 거리 임계값 (픽셀)

        # 얼굴 인식 결과 캐시 (박스 표시용)
        self._face_results_cache = None

        # 탭 숨김 상태 저장
        self._tab_was_visible = True

        # 백그라운드 저장 스레드 (해시 파일 저장 완료 대기용)
        self._save_thread = None

    def show(self):
        """안전 교육 오버레이 표시"""
        import time

        # 상단 센서 탭 숨기기 (화면 공간 확보)
        self._hide_notebook_tabs()

        # 거울보기 카메라가 사용 중이면 해제 (카메라 충돌 방지)
        try:
            if hasattr(self.parent_frame, '_stop_mirror_camera'):
                self.parent_frame._stop_mirror_camera()
                print("안전교육: 거울보기 카메라 해제 완료")

            # 카메라 객체가 있으면 직접 해제
            if hasattr(self.parent_frame, 'mirror_camera') and self.parent_frame.mirror_camera is not None:
                try:
                    self.parent_frame.mirror_camera.release()
                    self.parent_frame.mirror_camera = None
                    print("안전교육: 거울보기 카메라 객체 직접 해제")
                except Exception:
                    pass

            # 카메라 리소스 해제를 위해 충분히 대기 (Linux V4L2는 해제에 시간이 걸림)
            time.sleep(0.8)
        except Exception as e:
            print(f"안전교육: 거울보기 카메라 해제 실패 (무시): {e}")

        # 오버레이 프레임 생성 (앱의 루트 윈도우에 직접 배치하여 탭 위에 표시)
        root_window = self._get_root_window()
        self.overlay = tk.Frame(root_window, bg="#2C3E50")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ESC로 닫기
        self.overlay.bind("<Escape>", lambda e: self._close_overlay())

        # 메인 컨테이너 (grid 사용)
        main_container = tk.Frame(self.overlay, bg="#2C3E50")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 그리드 가중치 설정 (3:1 비율 고정 - uniform으로 비율 유지)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=3, uniform="col")  # 포스터 (75%)
        main_container.grid_columnconfigure(1, weight=1, uniform="col")  # 카메라 (25%)

        # 왼쪽: 포스터 영역 (75%)
        left_frame = tk.Frame(main_container, bg="#FFFFFF", relief="raised", bd=3)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 포스터 표시 영역 (전체 영역 채움)
        poster_display = tk.Frame(left_frame, bg="#FFFFFF")
        poster_display.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # 캔버스가 전체 영역을 채우도록 설정
        self.poster_canvas = tk.Canvas(poster_display, bg="#FFFFFF", highlightthickness=0)
        self.poster_canvas.pack(fill="both", expand=True)

        # 포스터 라벨을 캔버스 내부에 배치 (중앙 정렬)
        self.poster_label = tk.Label(self.poster_canvas, bg="#FFFFFF")
        # 초기 위치 (캔버스 크기가 결정된 후 업데이트됨)
        self.poster_window = self.poster_canvas.create_window(0, 0, anchor="center", window=self.poster_label)

        # 캔버스 리사이즈 시 포스터 라벨 위치 업데이트
        self.poster_canvas.bind("<Configure>", self._on_poster_canvas_resize)

        # 포스터 하단 컨트롤 (고정 높이 - 버튼이 잘 보이도록 높이 증가)
        poster_control = tk.Frame(left_frame, bg="#FFFFFF", height=160)
        poster_control.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        poster_control.pack_propagate(False)  # 고정 높이 유지

        # 이미지 확대/축소/초기화 버튼 영역
        zoom_frame = tk.Frame(poster_control, bg="#FFFFFF")
        zoom_frame.pack(side="top", fill="x", pady=(5, 5))

        # 확대 버튼
        zoom_in_btn = tk.Button(zoom_frame, text="🔍+ 확대",
                               command=self._zoom_in,
                               bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                               relief="raised", bd=2, width=8,
                               activebackground="#2980B9", activeforeground="#FFFFFF")
        zoom_in_btn.pack(side="left", padx=2)

        # 축소 버튼
        zoom_out_btn = tk.Button(zoom_frame, text="🔍- 축소",
                                command=self._zoom_out,
                                bg="#3498DB", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                relief="raised", bd=2, width=8,
                                activebackground="#2980B9", activeforeground="#FFFFFF")
        zoom_out_btn.pack(side="left", padx=2)

        # 초기화 버튼
        reset_zoom_btn = tk.Button(zoom_frame, text="🔄 초기화",
                                  command=self._reset_zoom,
                                  bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                                  relief="raised", bd=2, width=8,
                                  activebackground="#D35400", activeforeground="#FFFFFF")
        reset_zoom_btn.pack(side="left", padx=2)

        # 확대 비율 표시
        self.zoom_label = tk.Label(zoom_frame, text="120%", bg="#FFFFFF", fg="#2C3E50",
                                   font=("Pretendard", 11, "bold"))
        self.zoom_label.pack(side="right", padx=10)

        # 페이지 정보
        self.page_label = tk.Label(poster_control, text="", font=("Pretendard", 12, "bold"),
                                   bg="#FFFFFF", fg="#2C3E50")
        self.page_label.pack(side="top", pady=(5, 5))

        # 네비게이션 버튼
        nav_frame = tk.Frame(poster_control, bg="#FFFFFF")
        nav_frame.pack(side="bottom", pady=(0, 5))

        self.btn_prev = tk.Button(nav_frame, text="◀ 이전", command=self._prev_page,
                                  bg="#5DADE2", fg="#000000", font=("Pretendard", 16, "bold"),
                                  relief="raised", bd=3, width=12, height=2,
                                  activebackground="#3498DB", activeforeground="#000000",
                                  disabledforeground="#555555")
        self.btn_prev.pack(side="left", padx=10, ipady=5)

        self.btn_next = tk.Button(nav_frame, text="다음 ▶", command=self._next_page,
                                 bg="#5DADE2", fg="#000000", font=("Pretendard", 16, "bold"),
                                 relief="raised", bd=3, width=12, height=2,
                                 activebackground="#3498DB", activeforeground="#000000",
                                 disabledforeground="#555555")
        self.btn_next.pack(side="left", padx=10, ipady=5)

        # 오른쪽: 카메라 영역 (25%)
        right_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=3)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 카메라 표시 영역 (전체 영역 채움)
        camera_display = tk.Frame(right_frame, bg="#000000", relief="sunken", bd=3)
        camera_display.pack(fill="both", expand=True, padx=5, pady=5)

        self.camera_label = tk.Label(camera_display, bg="#000000", fg="#FFFFFF",
                                     text="카메라 로딩 중...", font=("Pretendard", 18, "bold"))
        self.camera_label.pack(fill="both", expand=True)

        # 하단 버튼 영역
        bottom_frame = tk.Frame(right_frame, bg="#34495E")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # 얼굴 촬영 활성화 여부 확인 (서명은 항상 받음)
        photo_enabled = self.config.env.get("safety_education_photo", True)

        # 안전교육 확인 체크박스 변수
        self.education_confirmed_var = tk.BooleanVar(value=False)

        # 체크박스 프레임 (버튼 위에 배치)
        checkbox_frame = tk.Frame(bottom_frame, bg="#34495E")
        checkbox_frame.pack(side="top", fill="x", pady=(0, 10))

        self.education_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="☑ 위 안전교육 내용을 모두 확인하였습니다.",
            font=("Pretendard", 14, "bold"),
            bg="#34495E", fg="#FFFFFF",
            selectcolor="#2C3E50",
            activebackground="#34495E",
            activeforeground="#27AE60",
            variable=self.education_confirmed_var,
            command=self._on_education_checkbox_changed
        )
        self.education_checkbox.pack(anchor="center")
        self.education_checkbox.configure(state="disabled")  # 모든 페이지 확인 전까지 비활성화

        # 버튼 프레임
        btn_frame = tk.Frame(bottom_frame, bg="#34495E")
        btn_frame.pack(side="bottom", fill="x")

        # 확인 버튼 (비활성화 상태로 시작) - 항상 서명은 받음
        self.confirm_btn = tk.Button(btn_frame, text="확인 (모든 페이지를 확인하세요)",
                                     command=self._take_signature, state="disabled",
                                     bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 18, "bold"),
                                     relief="raised", bd=3, height=3,
                                     disabledforeground="#CCCCCC")
        self.confirm_btn.pack(side="left", fill="x", expand=True, padx=5)

        # 닫기 버튼
        close_btn = tk.Button(btn_frame, text="✕ 닫기", command=self._close_overlay,
                             bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 18, "bold"),
                             relief="raised", bd=3, height=3,
                             activebackground="#C0392B", activeforeground="#FFFFFF")
        close_btn.pack(side="right", padx=5)

        # 포스터 먼저 동기로 로드 (즉시 표시) - 카메라보다 먼저
        self._load_posters()
        self._update_zoom_display()  # 확대 비율 표시 초기화
        self._update_poster_display()
        
        # 화면 업데이트 (포스터가 먼저 보이도록)
        self.overlay.update_idletasks()

        # 얼굴 촬영이 활성화된 경우에만 카메라 시작
        if photo_enabled:
            # 카메라는 포스터가 표시된 후에 로딩 시작 (비동기)
            self.camera_label.configure(text="카메라 로딩 중...", fg="#FFFFFF", font=("Pretendard", 16, "bold"))
            self.overlay.after(500, self._start_camera)  # 포스터가 먼저 보이도록 500ms 지연
        else:
            # 얼굴 촬영 비활성화 시 카메라 영역에 안내 메시지
            self.camera_label.configure(
                text="얼굴 촬영 기능이\n비활성화되어 있습니다.\n\n서명만 받습니다.",
                fg="#FFFFFF", font=("Pretendard", 14, "bold")
            )

    def _load_posters(self):
        """안전 교육 포스터 이미지 로드"""
        # safety_posters 디렉토리에서 이미지 로드 (프로그램 설치 디렉토리 기준)
        install_dir = get_base_dir()
        poster_dir = os.path.join(install_dir, "safety_posters")

        if not os.path.exists(poster_dir):
            # 디렉토리가 없으면 생성하고 안내 메시지
            os.makedirs(poster_dir, exist_ok=True)
            print(f"안전 교육 포스터 디렉토리가 생성되었습니다: {poster_dir}")
            print(f"권장 이미지 크기: {self.POSTER_WIDTH}x{self.POSTER_HEIGHT} 픽셀 (세로형)")
            # 기본 더미 이미지 생성
            self._create_dummy_posters()
            return

        # 이미지 파일 로드 (png, jpg, jpeg)
        image_files = []
        for f in os.listdir(poster_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(poster_dir, f))

        image_files.sort()  # 파일명 순으로 정렬

        if not image_files:
            print(f"안전 교육 포스터가 없습니다. {poster_dir}에 이미지를 추가하세요.")
            print(f"권장 이미지 크기: {self.POSTER_WIDTH}x{self.POSTER_HEIGHT} 픽셀 (세로형)")
            self._create_dummy_posters()
            return

        # PIL로 이미지 로드
        if PIL_OK:
            for img_path in image_files:
                try:
                    img = Image.open(img_path)
                    self.poster_images.append(img)
                except Exception as e:
                    print(f"이미지 로드 실패: {img_path} - {e}")
        else:
            print("PIL(Pillow) 라이브러리가 설치되지 않았습니다.")
            self._create_dummy_posters()

        if not self.poster_images:
            self._create_dummy_posters()

    def _create_dummy_posters(self):
        """더미 포스터 생성 (PIL 미설치 또는 이미지 없을 때)"""
        # 간단한 텍스트 기반 더미 포스터 3개 생성
        if PIL_OK:
            for i in range(3):
                img = Image.new('RGB', (self.POSTER_WIDTH, self.POSTER_HEIGHT), color=(200, 200, 200))
                self.poster_images.append(img)
        else:
            # PIL 없으면 None으로 표시 (텍스트로 대체)
            self.poster_images = [None, None, None]

    def _update_poster_display(self):
        """포스터 표시 업데이트"""
        if not self.poster_images:
            self.poster_label.configure(text="포스터 이미지가 없습니다.", image="")
            return

        # 현재 페이지를 본 것으로 표시
        self.viewed_pages.add(self.current_page)

        # 페이지 정보 업데이트
        total_pages = len(self.poster_images)
        self.page_label.configure(
            text=f"페이지 {self.current_page + 1} / {total_pages}  |  "
                 f"확인한 페이지: {len(self.viewed_pages)} / {total_pages}"
        )

        # 네비게이션 버튼 상태
        if self.current_page == 0:
            self.btn_prev.configure(state="disabled", bg="#95A5A6")
        else:
            self.btn_prev.configure(state="normal", bg="#3498DB")

        if self.current_page == total_pages - 1:
            self.btn_next.configure(state="disabled", bg="#95A5A6")
        else:
            self.btn_next.configure(state="normal", bg="#3498DB")

        # 포스터 이미지 표시
        current_img = self.poster_images[self.current_page]

        if current_img is None or not PIL_OK:
            # PIL 없거나 이미지가 None이면 텍스트로 표시
            self.poster_label.configure(
                text=f"안전 교육 포스터 #{self.current_page + 1}\n\n"
                     f"safety_posters/ 디렉토리에\n"
                     f"{self.POSTER_WIDTH}x{self.POSTER_HEIGHT} 크기의\n"
                     f"이미지를 추가하세요.",
                image="", fg="#666666", font=("Pretendard", 20, "bold")
            )
        else:
            # 캔버스 크기 가져오기 (전체 영역을 채움)
            self.poster_canvas.update_idletasks()
            canvas_width = self.poster_canvas.winfo_width()
            canvas_height = self.poster_canvas.winfo_height()

            # 캔버스 크기가 아직 결정되지 않았으면 기본값 사용
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800
                canvas_height = 600

            # 캔버스 크기에서 여백 제외 (화면을 벗어나지 않도록)
            available_width = canvas_width - 20  # 좌우 여백 10px씩
            available_height = canvas_height - 20  # 상하 여백 10px씩

            # 원본 이미지 비율 계산
            original_width, original_height = current_img.size
            aspect_ratio = original_width / original_height

            # 사용 가능한 공간에 맞춰 최대 크기 계산 (화면에 꽉 차게)
            if available_width / available_height > aspect_ratio:
                # 높이 기준으로 맞춤
                display_height = available_height
                display_width = int(display_height * aspect_ratio)
            else:
                # 너비 기준으로 맞춤
                display_width = available_width
                display_height = int(display_width / aspect_ratio)

            # 확대 비율 적용
            display_width = int(display_width * self.zoom_factor)
            display_height = int(display_height * self.zoom_factor)

            # 화면 크기를 벗어나지 않도록 최종 제한
            if display_width > available_width:
                display_width = available_width
                display_height = int(display_width / aspect_ratio)
            if display_height > available_height:
                display_height = available_height
                display_width = int(display_height * aspect_ratio)

            # 비율 유지하면서 리사이즈
            img_copy = current_img.copy()
            img_copy.thumbnail((display_width, display_height), Image.LANCZOS)

            # PhotoImage로 변환
            photo = ImageTk.PhotoImage(img_copy)
            self.poster_tk_images.append(photo)  # 참조 유지

            # 라벨 크기 조정 및 이미지 설정
            self.poster_label.configure(image=photo, text="", width=display_width, height=display_height)
            self.poster_label.image = photo  # 참조 유지

            # 이미지는 항상 캔버스 중앙에 고정
            self.poster_canvas.coords(self.poster_window, canvas_width // 2, canvas_height // 2)

        # 모든 페이지를 확인했는지 체크
        self._check_all_viewed()

    def _prev_page(self):
        """이전 페이지"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_poster_display()

    def _next_page(self):
        """다음 페이지"""
        if self.current_page < len(self.poster_images) - 1:
            self.current_page += 1
            self._update_poster_display()

    def _check_all_viewed(self):
        """모든 페이지를 확인했는지 체크"""
        total_pages = len(self.poster_images)

        if len(self.viewed_pages) == total_pages:
            # 모든 페이지 확인 완료 - 체크박스 활성화
            if hasattr(self, 'education_checkbox') and self.education_checkbox:
                self.education_checkbox.configure(state="normal")

            # 체크박스가 체크되지 않았으면 안내 메시지
            if not self.education_confirmed_var.get():
                self.confirm_btn.configure(
                    state="disabled",
                    bg="#F39C12",
                    text="☑ 위 체크박스를 선택해 주세요"
                )
            else:
                # 체크박스가 체크되어 있으면 확인 버튼 활성화
                self._enable_confirm_button()
        else:
            # 아직 확인 안 한 페이지가 있음
            remaining = total_pages - len(self.viewed_pages)
            self.confirm_btn.configure(
                state="disabled",
                bg="#95A5A6",
                text=f"확인 ({remaining}개 페이지 남음)"
            )
            # 체크박스 비활성화 및 체크 해제
            if hasattr(self, 'education_checkbox') and self.education_checkbox:
                self.education_confirmed_var.set(False)
                self.education_checkbox.configure(state="disabled")

    def _on_education_checkbox_changed(self):
        """안전교육 확인 체크박스 상태 변경 시 호출"""
        total_pages = len(self.poster_images)

        # 모든 페이지를 확인했고 체크박스가 체크되면 확인 버튼 활성화
        if len(self.viewed_pages) == total_pages and self.education_confirmed_var.get():
            self._enable_confirm_button()
        else:
            # 체크 해제 시 버튼 비활성화
            self.confirm_btn.configure(
                state="disabled",
                bg="#F39C12",
                text="☑ 위 체크박스를 선택해 주세요"
            )

    def _enable_confirm_button(self):
        """확인 버튼 활성화"""
        photo_enabled = self.config.env.get("safety_education_photo", True)

        if photo_enabled:
            self.confirm_btn.configure(
                state="normal",
                bg="#27AE60",
                text="✓ 확인 (얼굴 촬영 및 서명)",
                activebackground="#229954"
            )
        else:
            self.confirm_btn.configure(
                state="normal",
                bg="#27AE60",
                text="✓ 확인 (서명)",
                activebackground="#229954"
            )

    def _start_camera(self):
        """카메라 시작"""
        print("안전교육: 카메라 시작 시도...")

        if not CV2_OK:
            self.camera_label.configure(
                text="OpenCV가 설치되지 않았습니다.\n\n"
                     "pip install opencv-python\n\n"
                     "명령으로 설치하세요.",
                fg="#FF6B6B"
            )
            return

        try:
            # 사용 가능한 카메라 찾기
            print("안전교육: 사용 가능한 카메라 검색 중...")
            camera_index = None
            for i in range(5):  # 0~4까지 카메라 인덱스 확인
                try:
                    # 플랫폼별 백엔드로 우선 시도
                    backend = self.camera_backend.get_backend()
                    test_camera = cv2.VideoCapture(i, backend)
                    if test_camera.isOpened():
                        ret, frame = test_camera.read()
                        if ret and frame is not None:
                            camera_index = i
                            test_camera.release()
                            break
                        test_camera.release()
                except:
                    continue
            
            if camera_index is None:
                print("안전교육: 사용 가능한 카메라 없음")
                self.camera_label.configure(
                    text="카메라 사용 불가\n\n카메라가 연결되지 않았거나\n다른 프로그램에서 사용 중입니다.\n\n카메라를 확인하고\n다시 시도해주세요.",
                    fg="#FF6B6B", font=("Pretendard", 14, "bold")
                )
                return

            print(f"안전교육: 카메라 {camera_index} 발견")

            # 플랫폼별 백엔드로 열기
            primary_backend = self.camera_backend.get_backend()
            self.camera = cv2.VideoCapture(camera_index, primary_backend)

            if not self.camera.isOpened():
                # 1차 실패 시 대체 백엔드로 재시도
                fallback_backend = self.camera_backend.get_fallback_backend()
                self.camera = cv2.VideoCapture(camera_index, fallback_backend)
                if not self.camera.isOpened():
                    # 최종 재시도: 기본 백엔드
                    self.camera = cv2.VideoCapture(camera_index)
                if not self.camera.isOpened():
                    self.camera_label.configure(
                        text="카메라 사용 불가\n\n카메라가 연결되지 않았거나\n다른 프로그램에서 사용 중입니다.\n\n카메라를 확인하고\n다시 시도해주세요.",
                        fg="#FF6B6B", font=("Pretendard", 14, "bold")
                    )
                    return

            # 카메라 설정 최적화 (순서 중요)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기를 1로 설정하여 최신 프레임 유지

            # MJPEG 코덱 사용 (성능 향상)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            # PPE 감지기 초기화 (YOLOv10 기반) - 거울보기와 동일하게
            try:
                from ..ppe import PPEDetector, PPEVisualizer
                self.ppe_detector = PPEDetector()  # 거울보기와 동일하게 직접 생성
                self.ppe_visualizer = PPEVisualizer(font_size=5)
                print("안전교육: PPE 감지기 (YOLOv10) 초기화 완료")
            except Exception as e:
                print(f"안전교육: PPE 감지기 초기화 실패 (무시): {e}")
                self.ppe_detector = None
                self.ppe_visualizer = None

            # 얼굴 인식 감지기 초기화 (선택적)
            try:
                from ..sensor.safety_detector import SafetyEquipmentDetector
                self.safety_detector = SafetyEquipmentDetector(camera=None)
                self.safety_detector.set_camera(self.camera)
                # 얼굴 인식 기능 활성화
                self.safety_detector.enable_face_recognition(True)
                print("안전교육: 얼굴 인식 시스템 초기화 완료")
            except Exception as e:
                print(f"안전교육: 얼굴 인식 시스템 초기화 실패 (무시): {e}")
                self.safety_detector = None

            self.camera_running = True
            self._update_camera_frame()

        except Exception as e:
            self.camera_label.configure(
                text=f"카메라 오류:\n{str(e)}\n\n"
                     f"카메라가 연결되어 있는지 확인하세요.\n"
                     f"또는 카메라 설정에서 카메라 사용을\n"
                     f"비활성화할 수 있습니다.",
                fg="#FF6B6B"
            )

    def _run_ai_detection(self, frame):
        """백그라운드에서 AI 감지 실행 (PPE + 얼굴인식 + ID 추적) - 거울보기와 동일"""
        import threading
        if self.ai_thread_running:
            return  # 이미 실행 중이면 스킵

        def detect_async():
            self.ai_thread_running = True
            try:
                # PPE 감지 (YOLOv10) - 거울보기와 동일하게 is_available() 체크
                if self.ppe_detector is not None and self.ppe_detector.is_available():
                    try:
                        detections = self.ppe_detector.detect(frame)
                        if detections:
                            self._ppe_detections_cache = detections
                            self._ppe_status_cache = detections[0].ppe_status

                            # 얼굴 인식 (safety_detector에서 기존 DB 사용) - 실시간 최적화
                            if self.safety_detector is not None:
                                try:
                                    face_results = self.safety_detector.detect_face_only(frame)
                                    if face_results:
                                        self._face_results_cache = face_results
                                        self.last_detection_results = face_results

                                        # ID 추적: 사람 바운딩 박스와 얼굴을 매칭하여 추적
                                        self._update_person_tracking(detections, face_results)

                                        # 감지된 사람에 얼굴 정보 매핑 (추적 ID 기반)
                                        for det in detections:
                                            matched_name = self._get_tracked_name_for_detection(det)
                                            if matched_name:
                                                det.face_detected = True
                                                det.face_name = matched_name
                                except Exception as e:
                                    print(f"안전교육: 얼굴 인식 오류: {e}")
                        else:
                            self._ppe_detections_cache = None
                            self._ppe_status_cache = None
                    except Exception as e:
                        print(f"안전교육: PPE 감지 오류: {e}")
                else:
                    # PPE 감지기 없으면 얼굴 인식만 수행 - 실시간 최적화
                    if self.safety_detector is not None:
                        detection_results = self.safety_detector.detect_face_only(frame)
                        self.last_detection_results = detection_results
                        self._face_results_cache = detection_results
            except Exception as e:
                print(f"안전교육: AI 감지 오류: {e}")
            finally:
                self.ai_thread_running = False

        threading.Thread(target=detect_async, daemon=True).start()

    def _get_tracked_name_for_detection(self, detection):
        """detection에 매칭되는 추적 ID의 이름 반환"""
        if not hasattr(detection, 'track_id'):
            return None

        track_id = detection.track_id
        if track_id in self._tracked_persons:
            return self._tracked_persons[track_id].get('name', '')
        return None

    def _update_camera_frame(self):
        """카메라 프레임 업데이트 (백그라운드 AI 감지 - UI 블로킹 없음)"""
        # 상태 검증 먼저 수행
        if not self.camera_running:
            return

        if self.camera is None:
            return

        # overlay 존재 여부 먼저 확인
        try:
            if self.overlay is None or not self.overlay.winfo_exists():
                self.camera_running = False
                return
        except Exception:
            self.camera_running = False
            return

        try:
            # 버퍼 비우기
            self.camera.grab()
            ret, frame = self.camera.read()

            if ret and frame is not None:
                # 화면 반전 설정 읽기 (환경설정에서 저장된 값 사용)
                should_flip = True  # 기본값
                try:
                    should_flip = self.config.camera.get("flip_horizontal", True)
                except Exception as e:
                    print(f"안전교육: 카메라 반전 설정 오류: {e}")

                # 화면 표시용 프레임 반전
                if should_flip:
                    frame = cv2.flip(frame, 1)

                # 백그라운드 AI 감지 (15프레임마다 = 약 2fps)
                self.ai_frame_count += 1
                if self.ai_frame_count >= self.ai_detection_interval:
                    self.ai_frame_count = 0
                    self._run_ai_detection(frame.copy())

                # PPE 상태 및 바운딩 박스 그리기 (YOLOv10)
                if self.ppe_visualizer is not None and self._ppe_status_cache is not None:
                    try:
                        # 활성화된 항목 및 이름 (config에서 가져오기 - 거울보기와 동일)
                        enabled_items = {
                            'helmet': self.config.env.get('ppe_helmet_enabled', True),
                            'vest': self.config.env.get('ppe_vest_enabled', True),
                            'mask': self.config.env.get('ppe_mask_enabled', True),
                            'glasses': self.config.env.get('ppe_glasses_enabled', True),
                            'gloves': self.config.env.get('ppe_gloves_enabled', True),
                            'boots': self.config.env.get('ppe_boots_enabled', True)
                        }
                        item_names = {
                            'helmet': self.config.env.get('ppe_helmet_name', '헬멧'),
                            'vest': self.config.env.get('ppe_vest_name', '조끼'),
                            'mask': self.config.env.get('ppe_mask_name', '마스크'),
                            'glasses': self.config.env.get('ppe_glasses_name', '보안경'),
                            'gloves': self.config.env.get('ppe_gloves_name', '장갑'),
                            'boots': self.config.env.get('ppe_boots_name', '안전화')
                        }

                        # 1) PPE 바운딩 박스 및 레이블 (ID 추적 정보 포함)
                        if self._ppe_detections_cache:
                            frame = self.ppe_visualizer.draw_detections(frame, self._ppe_detections_cache)

                        # 2) PPE 상태 오버레이
                        frame = self.ppe_visualizer.draw_ppe_status_overlay(
                            frame, self._ppe_status_cache, enabled_items, item_names, 'top_left'
                        )

                        # 3) 안전률 표시 (우측 상단)
                        required_ppe = [k for k, v in enabled_items.items() if v]
                        h, w = frame.shape[:2]
                        frame = self.ppe_visualizer.draw_safety_rate(
                            frame, self._ppe_status_cache, required_ppe, (w - 210, 10)
                        )

                        # 4) 얼굴 인식 박스 그리기 (ID 추적 정보 포함)
                        if self._face_results_cache is not None and self.safety_detector is not None:
                            frame = self._draw_face_boxes(frame, self._face_results_cache)
                    except Exception as e:
                        print(f"안전교육: PPE 시각화 오류: {e}")

                # 얼굴 인식 결과 그리기 (fallback - PPE 감지 실패 시)
                elif self.last_detection_results is not None and self.safety_detector is not None:
                    try:
                        frame = self.safety_detector.draw_results(frame, self.last_detection_results)
                    except Exception:
                        pass

                # BGR을 RGB로 변환
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # PIL Image로 변환
                if PIL_OK:
                    img = Image.fromarray(frame_rgb)

                    # 카메라 라벨 크기에 맞춤
                    try:
                        display_width = self.camera_label.winfo_width() or 640
                        display_height = self.camera_label.winfo_height() or 480
                    except Exception:
                        display_width = 640
                        display_height = 480

                    # 여백 고려
                    display_width = max(display_width - 20, 400)
                    display_height = max(display_height - 20, 300)

                    # 비율 유지하면서 리사이즈
                    img.thumbnail((display_width, display_height), Image.LANCZOS)

                    # PhotoImage로 변환
                    photo = ImageTk.PhotoImage(img)

                    try:
                        if self.camera_label and self.camera_label.winfo_exists():
                            self.camera_label.configure(image=photo, text="")
                            self.camera_label.image = photo  # 참조 유지
                    except Exception:
                        pass

            # 30fps로 업데이트 (33ms) - 더 부드럽게
            try:
                if self.camera_running and self.overlay and self.overlay.winfo_exists():
                    self.overlay.after(33, self._update_camera_frame)
            except Exception:
                self.camera_running = False

        except Exception as e:
            print(f"카메라 프레임 업데이트 오류: {e}")
            # 오류 시 다음 프레임 시도 (3회까지)
            if not hasattr(self, '_camera_error_count'):
                self._camera_error_count = 0
            self._camera_error_count += 1

            if self._camera_error_count < 3:
                try:
                    if self.camera_running and self.overlay and self.overlay.winfo_exists():
                        self.overlay.after(100, self._update_camera_frame)
                except Exception:
                    self.camera_running = False
            else:
                self.camera_running = False
                try:
                    if self.camera_label and self.camera_label.winfo_exists():
                        self.camera_label.configure(text=f"카메라 오류:\n{str(e)}", fg="#FF6B6B")
                except Exception:
                    pass

    def _draw_face_boxes(self, frame, face_results):
        """얼굴 박스 그리기 (기존 safety_detector 스타일)

        녹색 박스 + 한글 이름 표시 (소속/사원번호/신뢰도 포함)
        """
        if not face_results:
            return frame

        recognized = face_results.get('recognized_faces', [])

        for face_info in recognized:
            bbox = face_info.get('location', [])
            if len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(x) for x in bbox]

            # 녹색 얼굴 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # 이름 및 정보 표시 (한글 지원)
            name = face_info.get('name', 'Unknown')
            if name and name != 'Unknown':
                employee_id = face_info.get('employee_id', '')
                department = face_info.get('department', '')
                confidence = face_info.get('confidence', 0.0)

                text = f"{name}"
                # 소속(department) 또는 사원번호(employee_id) 표시
                if department:
                    text += f" ({department})"
                elif employee_id:
                    text += f" ({employee_id})"
                text += f" [{int(confidence * 100)}%]"

                # 한글 지원 텍스트 출력
                if self.safety_detector and hasattr(self.safety_detector, '_put_korean_text'):
                    frame = self.safety_detector._put_korean_text(frame, text, (x1, y1 - 30), (0, 255, 0), 20)
                elif self.ppe_visualizer:
                    frame = self.ppe_visualizer.put_korean_text(frame, text, (x1, y1 - 30), (0, 255, 0), 18)
                else:
                    cv2.putText(frame, name, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return frame

    def _calculate_iou(self, box1, box2):
        """두 박스 간 IoU (Intersection over Union) 계산"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        # 교집합 영역
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        inter_area = (xi2 - xi1) * (yi2 - yi1)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area

        if union_area <= 0:
            return 0.0

        return inter_area / union_area

    def _calculate_center_distance(self, box1, box2):
        """두 박스 중심점 간 거리 계산"""
        import math
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        cx1, cy1 = (x1_1 + x2_1) // 2, (y1_1 + y2_1) // 2
        cx2, cy2 = (x1_2 + x2_2) // 2, (y1_2 + y2_2) // 2

        return math.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)

    def _update_person_tracking(self, detections, face_results):
        """사람 바운딩 박스와 얼굴을 매칭하여 ID 추적 업데이트 (거울보기와 동일)

        강화된 추적 로직:
        1. IoU 기반 매칭 (기본)
        2. 중심점 거리 기반 매칭 (IoU 실패 시 fallback)
        3. 이름이 있는 추적은 영구 유지 (타임아웃 없음)
        """
        import time
        current_time = time.time()

        # 타임아웃 처리: None이면 영구 추적
        if self._track_timeout is not None:
            expired_ids = []
            for track_id, info in self._tracked_persons.items():
                if info.get('name'):
                    continue
                elapsed = current_time - info['last_seen']
                if elapsed > self._track_timeout:
                    expired_ids.append(track_id)

            for track_id in expired_ids:
                del self._tracked_persons[track_id]

        recognized = face_results.get('recognized_faces', [])
        faces = face_results.get('faces', [])

        used_track_ids = set()

        for det in detections:
            person_bbox = (det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2)
            person_center = ((det.bbox.x1 + det.bbox.x2) // 2, (det.bbox.y1 + det.bbox.y2) // 2)
            matched_name = None
            matched_confidence = 0.0

            # 얼굴이 사람 박스 안에 있는지 확인
            for i, face_bbox in enumerate(faces):
                if len(face_bbox) >= 4:
                    fx1, fy1, fx2, fy2 = int(face_bbox[0]), int(face_bbox[1]), int(face_bbox[2]), int(face_bbox[3])
                    face_center_x = (fx1 + fx2) // 2
                    face_center_y = (fy1 + fy2) // 2

                    if (det.bbox.x1 <= face_center_x <= det.bbox.x2 and
                        det.bbox.y1 <= face_center_y <= det.bbox.y2):
                        if i < len(recognized):
                            rec = recognized[i]
                            name = rec.get('name', '')
                            conf = rec.get('confidence', 0.0)
                            if name and name != 'Unknown':
                                matched_name = name
                                matched_confidence = conf
                                break

            # 1단계: IoU 기반 매칭
            best_track_id = None
            best_score = 0.0

            for track_id, track_info in self._tracked_persons.items():
                if track_id in used_track_ids:
                    continue

                iou = self._calculate_iou(person_bbox, track_info['bbox'])
                if iou > self._track_iou_threshold and iou > best_score:
                    best_score = iou
                    best_track_id = track_id

            # 2단계: IoU 매칭 실패 시 중심점 거리 기반 매칭
            if best_track_id is None:
                min_distance = self._track_center_dist_threshold
                for track_id, track_info in self._tracked_persons.items():
                    if track_id in used_track_ids:
                        continue

                    distance = self._calculate_center_distance(person_bbox, track_info['bbox'])
                    threshold = self._track_center_dist_threshold
                    if track_info.get('name'):
                        threshold *= 2.5  # 이름이 있으면 500픽셀까지 허용

                    if distance < threshold and distance < min_distance:
                        min_distance = distance
                        best_track_id = track_id

            if best_track_id is not None:
                used_track_ids.add(best_track_id)
                track_info = self._tracked_persons[best_track_id]
                track_info['bbox'] = person_bbox
                track_info['center'] = person_center
                track_info['last_seen'] = current_time

                if matched_name:
                    if not track_info.get('name') or matched_confidence > track_info.get('confidence', 0):
                        track_info['name'] = matched_name
                        track_info['confidence'] = matched_confidence

                det.track_id = best_track_id
                if track_info.get('name'):
                    det.face_name = track_info['name']
                    det.face_detected = True
            else:
                new_track_id = self._next_track_id
                self._next_track_id += 1

                self._tracked_persons[new_track_id] = {
                    'name': matched_name or '',
                    'bbox': person_bbox,
                    'center': person_center,
                    'last_seen': current_time,
                    'confidence': matched_confidence
                }
                det.track_id = new_track_id
                if matched_name:
                    det.face_name = matched_name
                    det.face_detected = True

    def _take_signature(self):
        """서명 받기 (얼굴 촬영은 설정에 따라)"""
        photo_enabled = self.config.env.get("safety_education_photo", True)

        # 안전교육 카메라 프레임 업데이트 중지 (서명 화면에서 카메라 사용)
        self.camera_running = False
        if hasattr(self, 'camera_frame_id') and self.camera_frame_id:
            try:
                if self.overlay and self.overlay.winfo_exists():
                    self.overlay.after_cancel(self.camera_frame_id)
            except Exception:
                pass
            self.camera_frame_id = None
        print("안전교육: 카메라 프레임 업데이트 중지 (서명 화면 전환)")

        # 얼굴+서명 다이얼로그 표시 (오버레이 위에 Frame으로)
        from .safety_signature import SafetySignatureDialog

        # 콜백 함수 전달 (photo_enabled와 config를 전달, 감지기 모두 공유)
        signature_dialog = SafetySignatureDialog(
            self.overlay,
            self.camera if photo_enabled else None,
            self._on_signature_complete,
            photo_enabled=photo_enabled,
            config=self.config,
            safety_detector=self.safety_detector,  # 얼굴 인식 감지기 공유
            ppe_detector=self.ppe_detector,  # PPE 감지기 공유
            ppe_visualizer=self.ppe_visualizer  # PPE visualizer 공유
        )
        signature_dialog.show()

    def _on_signature_complete(self, result):
        """서명 완료 콜백"""
        print(f"[안전교육] _on_signature_complete 호출됨")
        print(f"[안전교육] result keys: {result.keys() if result else 'None'}")

        # result = {"face_image": PIL.Image or None, "signature_image": PIL.Image,
        #           "recognized_name": str or None, "safety_equipment": dict or None}

        if not result:
            print("[안전교육] result가 None입니다!")
            return

        if "signature_image" not in result or result["signature_image"] is None:
            print("[안전교육] signature_image가 없습니다!")
            return

        # 백그라운드 스레드에서 이미지 저장 수행 (UI 블록 방지)
        import threading
        import sys
        def _save_in_background():
            try:
                self._save_combined_image(
                    result.get("face_image"),
                    result["signature_image"],
                    result.get("recognized_name"),
                    result.get("safety_equipment")
                )
            except Exception as e:
                print(f"[안전교육] 저장 오류: {e}")
                import traceback
                traceback.print_exc()
                # UI에 저장 실패 알림 (메인 스레드에서 실행)
                error_msg = f"안전교육 사진 저장 실패:\n{str(e)}"
                if self.app:
                    self.app.after(0, lambda: self._show_error_popup(error_msg))
            finally:
                # 저장 성공/실패와 무관하게 첫 화면으로 돌아가고 카메라 재시작
                if self.app:
                    self.app.after(200, self._safe_reset_to_first_page)

        # daemon=False: 해시 파일 저장이 완료될 때까지 스레드가 종료되지 않도록 함
        # 인스턴스 변수로 저장하여 _close_overlay에서 완료 대기 가능하게 함
        self._save_thread = threading.Thread(target=_save_in_background, daemon=False)
        self._save_thread.start()

    def _save_combined_image(self, face_image, signature_image, recognized_name=None,
                              safety_equipment=None):
        """
        얼굴과 서명을 합쳐서 저장 (얼굴 이미지가 없으면 서명만 저장)
        + 메타데이터 JSON 생성 및 해시 체인 등록

        Args:
            face_image: 얼굴 PIL Image 또는 None
            signature_image: 서명 PIL Image
            recognized_name: 인식된 이름 또는 None
            safety_equipment: 안전장구 착용 정보 딕셔너리 또는 None
        """
        if not PIL_OK:
            self._show_error_popup("PIL(Pillow) 라이브러리가 필요합니다.")
            return

        try:
            import hashlib
            import json
            from PIL import ImageDraw, ImageFont

            # 저장 디렉토리 생성 (년도별 폴더) - 프로그램 설치 디렉토리 기준
            current_year = datetime.datetime.now().year
            install_dir = get_base_dir()
            save_dir = os.path.join(install_dir, "safety_photos", str(current_year))
            os.makedirs(save_dir, exist_ok=True)

            # 파일명: safety_이름_YYYYMMDD_HHMMSS.jpg (인식된 이름이 있으면 포함)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if recognized_name:
                # 파일명에 사용할 수 없는 문자 제거
                safe_name = recognized_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                # 한글, 영문, 숫자, 언더스코어, 하이픈만 허용
                def is_valid_char(c):
                    if c.isalnum():
                        return True
                    if c in "_-":
                        return True
                    # 한글 범위 체크 (가-힣, ㄱ-ㅎ, ㅏ-ㅣ)
                    if '\uAC00' <= c <= '\uD7A3':  # 가-힣
                        return True
                    if '\u3131' <= c <= '\u3163':  # ㄱ-ㅎ, ㅏ-ㅣ
                        return True
                    return False
                safe_name = "".join(c for c in safe_name if is_valid_char(c))
                filename = f"safety_{safe_name}_{timestamp}.jpg"
            else:
                filename = f"safety_{timestamp}.jpg"
            filepath = os.path.join(save_dir, filename)
            print(f"[안전교육] 저장 경로: {filepath}")

            # 서명 이미지 정보 확인
            print(f"[안전교육] 서명 이미지: type={type(signature_image)}, size={signature_image.size if hasattr(signature_image, 'size') else 'N/A'}")

            # 서명 이미지 크기 조정 (가로 800px)
            sig_width = 800
            sig_ratio = sig_width / signature_image.width
            sig_height = int(signature_image.height * sig_ratio)
            signature_resized = signature_image.resize((sig_width, sig_height), Image.LANCZOS)
            print(f"[안전교육] 서명 이미지 리사이즈 완료: {sig_width}x{sig_height}")

            # 안전교육 이미지들 로드
            safety_images = self._load_safety_images()
            print(f"[안전교육] 안전교육 이미지 로드: {len(safety_images)}개")

            if face_image is not None:
                # 얼굴 이미지가 있으면 합성 이미지 생성
                # 얼굴 이미지 크기 조정 (가로 800px)
                face_width = 800
                face_ratio = face_width / face_image.width
                face_height = int(face_image.height * face_ratio)
                face_resized = face_image.resize((face_width, face_height), Image.LANCZOS)

                # 안전교육 이미지들 크기 조정 (가로 800px)
                safety_height = 0
                safety_resized = []
                for img in safety_images:
                    img_width = 800
                    img_ratio = img_width / img.width
                    img_height = int(img.height * img_ratio)
                    img_resized = img.resize((img_width, img_height), Image.LANCZOS)
                    safety_resized.append(img_resized)
                    safety_height += img_height

                # 합성 이미지 생성 (세로로 배치: 얼굴 -> 안전교육 이미지들 -> 서명)
                total_height = face_height + safety_height + sig_height
                combined_image = Image.new('RGB', (800, total_height), color='white')

                # 얼굴 붙이기 (상단)
                combined_image.paste(face_resized, (0, 0))

                # 안전교육 이미지들 붙이기 (얼굴 아래)
                y_offset = face_height
                for img_resized in safety_resized:
                    combined_image.paste(img_resized, (0, y_offset))
                    y_offset += img_resized.height

                # 서명 붙이기 (하단)
                combined_image.paste(signature_resized, (0, face_height + safety_height))
            else:
                # 얼굴 이미지가 없으면 안전교육 이미지들과 서명만 저장
                safety_height = 0
                safety_resized = []
                for img in safety_images:
                    img_width = 800
                    img_ratio = img_width / img.width
                    img_height = int(img.height * img_ratio)
                    img_resized = img.resize((img_width, img_height), Image.LANCZOS)
                    safety_resized.append(img_resized)
                    safety_height += img_height

                # 합성 이미지 생성 (세로로 배치: 안전교육 이미지들 -> 서명)
                total_height = safety_height + sig_height
                combined_image = Image.new('RGB', (800, total_height), color='white')

                # 안전교육 이미지들 붙이기 (상단)
                y_offset = 0
                for img_resized in safety_resized:
                    combined_image.paste(img_resized, (0, y_offset))
                    y_offset += img_resized.height

                # 서명 붙이기 (하단)
                combined_image.paste(signature_resized, (0, safety_height))

            # 안전장구 착용 정보를 이미지에 텍스트로 추가
            combined_image = self._add_safety_equipment_text(combined_image, safety_equipment, recognized_name)
            print(f"[안전교육] 안전장구 착용 정보 텍스트 추가 완료")

            # SHA256 해시값 생성
            print(f"[안전교육] 합성 이미지 생성 완료: {combined_image.size}")
            hash_object = hashlib.sha256()
            hash_object.update(combined_image.tobytes())
            hash_value = hash_object.hexdigest()
            print(f"[안전교육] 해시값 생성 완료: {hash_value[:16]}...")

            # 해시 정보를 이미지에 추가 (새 이미지 반환)
            final_image = self._add_hash_to_image(combined_image, timestamp, hash_value)
            print(f"[안전교육] 해시 정보 이미지 추가 완료")

            # 이미지 저장
            final_image.save(filepath, 'JPEG', quality=95)
            print(f"[안전교육] 이미지 파일 저장 완료: {filepath}")

            # ================================================================
            # 메타데이터 JSON 생성 (특허 청구항 2 관련)
            # ================================================================
            metadata = {
                "version": "1.0",
                "person": {
                    "name": recognized_name,
                    "has_face_image": face_image is not None
                },
                "safety_equipment": safety_equipment or {
                    "helmet": {"worn": False, "color": None},
                    "vest": {"worn": False, "color": None},
                    "mask": {"worn": False}
                },
                "education": {
                    "posters_viewed": len(self.poster_images),
                    "total_posters": len(safety_images),
                    "viewed_pages": list(self.viewed_pages) if hasattr(self, 'viewed_pages') else []
                },
                "timestamps": {
                    "record_created": datetime.datetime.now().isoformat(),
                    "date_kr": datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')
                },
                "system_info": {
                    "software_version": "1.9.7",
                    "location": getattr(self.config.env, 'location', '미설정') if hasattr(self, 'config') and self.config and hasattr(self.config, 'env') else "미설정"
                },
                "image_hash": hash_value
            }

            # 메타데이터 파일 저장
            metadata_filepath = filepath.replace('.jpg', '.json')
            with open(metadata_filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # ================================================================
            # 해시 체인에 기록 추가 (특허 청구항 1(f), 6(g) 관련)
            # ================================================================
            chain_record = None
            try:
                from ..utils.integrity_manager import IntegrityManager

                # IntegrityManager 초기화 (safety_photos 디렉토리 기준)
                integrity = IntegrityManager(os.path.join(install_dir, "safety_photos"))

                # 기록 추가 (메타데이터 파일 해시는 이 시점에 계산됨)
                chain_record = integrity.add_record(
                    files={
                        "combined_image": filepath,
                        "metadata": metadata_filepath
                    },
                    metadata={
                        "person_name": recognized_name
                    }
                )
                # 참고: 체인 정보는 hash_chain.json에 별도 저장됨
                # 메타데이터 파일은 변경하지 않음 (무결성 검증을 위해 add_record 호출 시점의 해시 유지)

            except ImportError:
                print("[안전교육] IntegrityManager 모듈 없음 - 해시 체인 기록 생략")
            except Exception as chain_err:
                print(f"[안전교육] 해시 체인 기록 실패: {chain_err}")

            # ================================================================
            # 기존 해시 파일 저장 (하위 호환성)
            # ================================================================
            hash_filepath = filepath + ".hash"
            hash_saved = False
            try:
                with open(hash_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"파일명: {filename}\n")
                    f.write(f"촬영일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}\n")
                    f.write(f"해시함수: SHA256\n")
                    f.write(f"해시값: {hash_value}\n")
                    if chain_record:
                        f.write(f"기록ID: {chain_record.get('record_id')}\n")
                        f.write(f"체인해시: {chain_record.get('chain_hash')}\n")
                hash_saved = True
            except Exception as hash_err:
                print(f"[안전교육] 해시 파일 저장 실패: {hash_err}")

            # ================================================================
            # 저장 완료 검증
            # ================================================================
            files_ok = True
            missing_files = []

            # 필수 파일 존재 확인
            if not os.path.exists(filepath):
                files_ok = False
                missing_files.append("이미지 파일")
            if not os.path.exists(metadata_filepath):
                files_ok = False
                missing_files.append("메타데이터 파일")
            if not hash_saved or not os.path.exists(hash_filepath):
                files_ok = False
                missing_files.append("해시 파일")

            if files_ok:
                print(f"[안전교육] 사진 저장 완료: {filepath}")
            else:
                print(f"[안전교육] 경고: 일부 파일 누락 - {', '.join(missing_files)}")
                # 누락된 해시 파일 재시도
                if "해시 파일" in missing_files and os.path.exists(filepath):
                    try:
                        with open(hash_filepath, 'w', encoding='utf-8') as f:
                            f.write(f"파일명: {filename}\n")
                            f.write(f"촬영일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}\n")
                            f.write(f"해시함수: SHA256\n")
                            f.write(f"해시값: {hash_value}\n")
                    except Exception as retry_err:
                        print(f"[안전교육] 해시 파일 재생성 실패: {retry_err}")

            # 참고: 첫 화면 리셋은 호출자(저장 스레드의 finally)에서 처리

        except Exception as e:
            import traceback
            traceback.print_exc()
            # 에러 팝업도 메인 스레드에서 실행
            error_msg = f"이미지 저장 중 오류가 발생했습니다:\n{str(e)}"
            if self.app:
                self.app.after(0, lambda: self._show_error_popup(error_msg))

    def _load_safety_images(self):
        """안전교육 이미지들 로드"""
        safety_images = []

        try:
            # safety_posters 폴더에서 이미지 파일들 로드 (프로그램 설치 디렉토리 기준)
            install_dir = get_base_dir()
            posters_dir = os.path.join(install_dir, "safety_posters")
            if os.path.exists(posters_dir):
                for filename in os.listdir(posters_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        filepath = os.path.join(posters_dir, filename)
                        try:
                            img = Image.open(filepath)
                            safety_images.append(img)
                        except Exception as e:
                            print(f"안전교육 이미지 로드 실패: {filename} - {e}")
                            continue
        except Exception as e:
            print(f"안전교육 이미지 폴더 접근 실패: {e}")
        
        return safety_images

    def _add_safety_equipment_text(self, image, safety_equipment, recognized_name=None):
        """이미지에 안전장구 착용 정보 텍스트 추가 - 새 이미지 반환"""
        try:
            from PIL import ImageDraw, ImageFont

            # 안전장구 정보 텍스트 생성
            lines = []

            # 인식된 이름
            if recognized_name:
                lines.append(f"인식된 이름: {recognized_name}")
            else:
                lines.append("인식된 이름: 미등록자")

            lines.append("")  # 빈 줄

            # 안전장구 착용 정보
            lines.append("[ 안전장구 착용 현황 ]")

            if safety_equipment:
                # 헬멧
                helmet_info = safety_equipment.get("helmet", {})
                if helmet_info.get("worn"):
                    color = helmet_info.get("color", "")
                    color_text = f" ({color})" if color else ""
                    lines.append(f"  ✓ 안전모: 착용{color_text}")
                else:
                    lines.append("  ✗ 안전모: 미착용")

                # 조끼
                vest_info = safety_equipment.get("vest", {})
                if vest_info.get("worn"):
                    color = vest_info.get("color", "")
                    color_text = f" ({color})" if color else ""
                    lines.append(f"  ✓ 안전조끼: 착용{color_text}")
                else:
                    lines.append("  ✗ 안전조끼: 미착용")

                # 마스크
                mask_info = safety_equipment.get("mask", {})
                if mask_info.get("worn"):
                    lines.append("  ✓ 마스크: 착용")
                else:
                    lines.append("  ✗ 마스크: 미착용")

                # 보안경
                glasses_info = safety_equipment.get("glasses", {})
                if glasses_info.get("worn"):
                    lines.append("  ✓ 보안경: 착용")

                # 장갑
                gloves_info = safety_equipment.get("gloves", {})
                if gloves_info.get("worn"):
                    count = gloves_info.get("count", 2)
                    lines.append(f"  ✓ 장갑: 착용 ({count}개)")

                # 안전화
                boots_info = safety_equipment.get("boots", {})
                if boots_info.get("worn"):
                    lines.append("  ✓ 안전화: 착용")
            else:
                lines.append("  (안전장구 정보 없음)")

            # 텍스트 추가할 공간 확보 (상단에 추가)
            text_height = 20 * len(lines) + 30  # 각 줄 20px + 여백
            original_height = image.height
            new_height = original_height + text_height
            new_image = Image.new('RGB', (image.width, new_height), color='white')

            # 기존 이미지를 텍스트 영역 아래에 붙임
            new_image.paste(image, (0, text_height))

            # 텍스트 그리기
            draw = ImageDraw.Draw(new_image)

            # 폰트 설정 (한글 폰트)
            font = None
            try:
                for font_path in [
                    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                    '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    'arial.ttf'
                ]:
                    try:
                        font = ImageFont.truetype(font_path, 16)
                        break
                    except:
                        continue
            except:
                pass
            if font is None:
                font = ImageFont.load_default()

            # 텍스트 출력
            y = 10
            for line in lines:
                # 착용은 녹색, 미착용은 빨간색
                if "✓" in line:
                    fill_color = (0, 128, 0)  # 녹색
                elif "✗" in line:
                    fill_color = (200, 0, 0)  # 빨간색
                else:
                    fill_color = (0, 0, 0)  # 검정

                draw.text((20, y), line, fill=fill_color, font=font)
                y += 20

            return new_image

        except Exception as e:
            print(f"[안전교육] 안전장구 정보 텍스트 추가 실패: {e}")
            import traceback
            traceback.print_exc()
            return image

    def _add_hash_to_image(self, image, timestamp, hash_value):
        """이미지에 해시 정보 추가 - 새 이미지 반환"""
        try:
            from PIL import ImageDraw, ImageFont

            # 현재 시간 정보
            current_time = datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')

            # 해시 정보 텍스트
            hash_text = f"촬영일시: {current_time}\n해시함수: SHA256\n해시값: {hash_value}"

            # 이미지에 텍스트 추가할 공간 확보 (하단에 100px 추가)
            original_height = image.height
            new_height = original_height + 100
            new_image = Image.new('RGB', (image.width, new_height), color='white')
            new_image.paste(image, (0, 0))

            # 텍스트 그리기
            draw = ImageDraw.Draw(new_image)

            # 폰트 설정 (한글 폰트 또는 기본 폰트)
            font = None
            try:
                # Linux 한글 폰트
                for font_path in [
                    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    'arial.ttf'
                ]:
                    try:
                        font = ImageFont.truetype(font_path, 14)
                        break
                    except:
                        continue
            except:
                pass
            if font is None:
                font = ImageFont.load_default()

            # 텍스트 위치 (하단 중앙)
            text_lines = hash_text.split('\n')
            y_start = original_height + 10

            for i, line in enumerate(text_lines):
                # 텍스트 크기 계산
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # 중앙 정렬
                x = (image.width - text_width) // 2
                y = y_start + (i * (text_height + 5))

                # 텍스트 그리기
                draw.text((x, y), line, fill='black', font=font)

            # 새 이미지 반환
            return new_image

        except Exception as e:
            print(f"[안전교육] 해시 정보 추가 실패: {e}")
            # 해시 정보 추가 실패 시 원본 이미지 반환
            return image

    def _show_success_popup(self, filepath, recognized_name=None):
        """성공 팝업 (큰 버튼) - 확인 후 안전교육 첫 화면으로 돌아감"""
        # overlay 위에 팝업 표시 (overlay가 있으면 overlay 위에, 없으면 parent_frame 위에)
        parent_widget = self.overlay if self.overlay and self.overlay.winfo_exists() else self.parent_frame
        popup = tk.Toplevel(parent_widget)
        popup.title("완료")
        popup.configure(bg="#27AE60")

        # 화면 중앙 배치
        window_width = 800
        window_height = 600
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 포커스 강제 설정 (topmost를 나중에 설정)
        popup.update_idletasks()
        popup.grab_set()  # 모달 설정
        popup.lift()
        popup.attributes("-topmost", True)
        popup.focus_force()

        # 메시지 (인식된 이름이 있으면 표시)
        if recognized_name:
            message_text = f"안전 교육 확인이 완료되었습니다!\n\n인식된 이름: {recognized_name}\n\n얼굴 사진과 서명이 저장되었습니다."
        else:
            message_text = "안전 교육 확인이 완료되었습니다!\n\n얼굴 사진과 서명이 저장되었습니다."

        msg_label = tk.Label(popup,
                           text=message_text,
                           font=("Pretendard", 20, "bold"),
                           fg="#FFFFFF", bg="#27AE60",
                           wraplength=700, justify="center")
        msg_label.pack(pady=40, padx=40)

        # 파일 경로
        path_label = tk.Label(popup, text=f"저장 위치:\n{filepath}",
                            font=("Pretendard", 10),
                            fg="#FFFFFF", bg="#27AE60",
                            wraplength=700, justify="center")
        path_label.pack(pady=20, padx=40)

        # 확인 버튼 클릭 시 안전교육 첫 화면으로 돌아가기
        def on_confirm():
            popup.destroy()
            self._reset_to_first_page()

        # 확인 버튼 (크게)
        btn_ok = tk.Button(popup, text="✓ 확인", command=on_confirm,
                          bg="#FFFFFF", fg="#27AE60",
                          font=("Pretendard", 18, "bold"),
                          relief="raised", bd=5, height=3,
                          activebackground="#ECF0F1", activeforeground="#27AE60")
        btn_ok.pack(pady=40, padx=100, fill="x")

        # 버튼에 포커스 설정
        btn_ok.focus_set()

        popup.wait_window()

    def _show_success_popup_simple(self, message):
        """간단한 성공 팝업 (사진 촬영 없이 확인 시)"""
        popup = tk.Toplevel(self.overlay)
        popup.title("완료")
        popup.attributes("-topmost", True)
        popup.configure(bg="#27AE60")
        popup.grab_set()

        # 화면 중앙 배치
        window_width = 600
        window_height = 572  # 기존 대비 추가 +10% 확대
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 포커스 강제 설정
        popup.update_idletasks()
        popup.lift()
        popup.focus_force()

        # 메시지
        msg_label = tk.Label(popup, text=message,
                           font=("Pretendard", 20, "bold"),  # 28 -> 20
                           fg="#FFFFFF", bg="#27AE60",
                           wraplength=500, justify="center")
        msg_label.pack(pady=80, padx=40)

        # 확인 버튼 (크게)
        btn_ok = tk.Button(popup, text="✓ 확인", command=popup.destroy,
                          bg="#FFFFFF", fg="#27AE60",
                          font=("Pretendard", 18, "bold"),  # 26 -> 18
                          relief="raised", bd=5, height=3,
                          activebackground="#ECF0F1", activeforeground="#27AE60")
        btn_ok.pack(pady=40, padx=100, fill="x")

        popup.wait_window()

    def _show_error_popup(self, message):
        """에러 팝업 (큰 버튼)"""
        popup = tk.Toplevel(self.overlay)
        popup.title("오류")
        popup.attributes("-topmost", True)
        popup.configure(bg="#E74C3C")
        popup.grab_set()

        # 화면 중앙 배치
        window_width = 700
        window_height = 715  # 기존 대비 추가 +10% 확대
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 포커스 강제 설정
        popup.update_idletasks()
        popup.lift()
        popup.focus_force()

        # 메시지
        msg_label = tk.Label(popup, text=message,
                           font=("Pretendard", 17, "bold"),  # 24 -> 17
                           fg="#FFFFFF", bg="#E74C3C",
                           wraplength=600, justify="center")
        msg_label.pack(pady=80, padx=40)

        # 확인 버튼 (크게)
        btn_ok = tk.Button(popup, text="확인", command=popup.destroy,
                          bg="#FFFFFF", fg="#E74C3C",
                          font=("Pretendard", 17, "bold"),  # 24 -> 17
                          relief="raised", bd=5, height=3,
                          activebackground="#ECF0F1", activeforeground="#E74C3C")
        btn_ok.pack(pady=20, padx=100, fill="x")

        popup.wait_window()

    def _close_overlay(self):
        """오버레이 닫기"""
        # 저장 스레드가 실행 중이면 완료될 때까지 대기 (최대 10초)
        if self._save_thread is not None and self._save_thread.is_alive():
            self._save_thread.join(timeout=10)
            self._save_thread = None

        # 카메라 정지
        self.camera_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except:
                pass
            self.camera = None

        # 오버레이 닫기 (예외 처리로 Tcl 명령 충돌 방지)
        if self.overlay:
            try:
                self.overlay.place_forget()
            except Exception:
                pass
            try:
                if self.overlay.winfo_exists():
                    self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None

        # 상단 센서 탭 다시 보이기
        self._show_notebook_tabs()

        # 거울보기 버튼 상태 업데이트 (모든 패널에서)
        self._update_mirror_buttons_after_close()

    def _zoom_in(self):
        """이미지 확대"""
        if self.zoom_factor < 1.3:  # 최대 130%까지 확대 (30% 제한)
            self.zoom_factor += 0.1
            self._update_zoom_display()
            self._update_poster_display()

    def _zoom_out(self):
        """이미지 축소"""
        if self.zoom_factor > 0.7:  # 최소 70%까지 축소 (30% 제한)
            self.zoom_factor -= 0.1
            self._update_zoom_display()
            self._update_poster_display()

    def _reset_zoom(self):
        """확대 비율 초기화"""
        self.zoom_factor = 1.2  # 기본값을 20% 확대로 설정
        self._update_zoom_display()
        self._update_poster_display()

    def _update_zoom_display(self):
        """확대 비율 표시 업데이트"""
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_label.configure(text=f"{zoom_percent}%")

    def _on_poster_canvas_resize(self, event):
        """캔버스 리사이즈 시 포스터 라벨 위치 업데이트"""
        # 캔버스 중앙에 포스터 배치
        canvas_width = event.width
        canvas_height = event.height
        self.poster_canvas.coords(self.poster_window, canvas_width // 2, canvas_height // 2)
        # 포스터 크기도 함께 업데이트
        self._update_poster_display()

    def _safe_reset_to_first_page(self):
        """안전한 첫 화면 리셋 (예외 처리 포함)"""
        # 오버레이가 이미 닫혔으면 리셋 불필요
        if not self.overlay:
            return
        try:
            self._reset_to_first_page()
        except Exception as e:
            print(f"[안전교육] 첫 화면 리셋 오류: {e}")

    def _reset_to_first_page(self):
        """안전교육 첫 화면으로 돌아가기 (페이지 초기화)"""
        print("[안전교육] 첫 화면으로 리셋 시작")

        # 페이지 초기화
        self.current_page = 0
        self.viewed_pages.clear()

        # 체크박스 리셋
        if hasattr(self, 'education_confirmed_var'):
            self.education_confirmed_var.set(False)
        if hasattr(self, 'education_checkbox') and self.education_checkbox:
            try:
                self.education_checkbox.configure(state="disabled")
            except Exception:
                pass

        # 확인 버튼 비활성화
        if self.confirm_btn:
            self.confirm_btn.configure(
                state="disabled",
                bg="#95A5A6",
                text=f"확인 ({len(self.poster_images)}개 페이지 남음)"
            )

        # 오버레이가 있으면 UI 강제 새로고침
        if self.overlay and self.overlay.winfo_exists():
            try:
                # 포스터 다시 표시
                self._update_poster_display()

                # 카메라 프리뷰 재시작 (서명 화면에서 중지되었으므로)
                self._restart_camera_preview()

                # 오버레이가 여전히 유효한지 다시 확인 (카메라 재시작 중에 닫힐 수 있음)
                try:
                    if self.overlay and self.overlay.winfo_exists():
                        # 오버레이 강제 새로고침
                        self.overlay.update_idletasks()
                        self.overlay.update()

                        # 포커스 복원 (오버레이가 유효할 때만)
                        if self.overlay and self.overlay.winfo_exists():
                            self.overlay.focus_force()
                            self.overlay.lift()
                except Exception:
                    pass  # 오버레이 관련 오류는 무시

                print("[안전교육] 첫 화면 리셋 완료")
            except Exception as e:
                print(f"[안전교육] 첫 화면 리셋 오류: {e}")
        else:
            print("[안전교육] 오버레이가 없음 - 포스터만 업데이트")
            self._update_poster_display()

    def _restart_camera_preview(self):
        """카메라 프리뷰 재시작 (서명 화면 복귀 후)"""
        try:
            print(f"[안전교육] 카메라 프리뷰 재시작 시도 - camera={self.camera is not None}, isOpened={self.camera.isOpened() if self.camera else 'N/A'}")

            # 카메라가 닫혀있으면 다시 열기
            if self.camera is None or not self.camera.isOpened():
                print("[안전교육] 카메라가 닫혀있음 - 다시 열기 시도")
                import cv2
                # 카메라 다시 열기
                camera_index = 0
                for i in range(3):
                    try:
                        test_camera = cv2.VideoCapture(i)
                        if test_camera.isOpened():
                            ret, frame = test_camera.read()
                            if ret and frame is not None:
                                camera_index = i
                                test_camera.release()
                                break
                            test_camera.release()
                    except:
                        continue

                self.camera = cv2.VideoCapture(camera_index)
                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"[안전교육] 카메라 {camera_index} 다시 열기 성공")
                else:
                    print("[안전교육] 카메라 다시 열기 실패")
                    return

            # 카메라가 열려있으면 프리뷰 재시작
            if self.camera is not None and self.camera.isOpened():
                self.camera_running = True
                self.ai_frame_count = 0

                # 카메라 프레임 업데이트 스케줄링
                if self.overlay and self.overlay.winfo_exists():
                    self.camera_frame_id = self.overlay.after(33, self._update_camera_frame)
                    print("[안전교육] 카메라 프리뷰 재시작 완료")
            else:
                print("[안전교육] 카메라가 없거나 닫혀있음 - 프리뷰 재시작 스킵")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[안전교육] 카메라 프리뷰 재시작 오류: {e}")

    def _hide_notebook_tabs(self):
        """상단 센서 탭(Notebook) 및 메뉴 숨기기"""
        # 메뉴 숨기기
        if self.app:
            try:
                # 메뉴바의 설정, 보기 메뉴 비활성화
                if hasattr(self.app, 'menu_cfg'):
                    self.app.menubar.entryconfigure("설정", state="disabled")
                if hasattr(self.app, 'menu_view'):
                    self.app.menubar.entryconfigure("보기", state="disabled")
            except Exception as e:
                print(f"메뉴 숨기기 오류: {e}")

    def _show_notebook_tabs(self):
        """상단 센서 탭(Notebook) 및 메뉴 다시 보이기"""
        # 메뉴 다시 보이기
        if self.app:
            try:
                # 메뉴바의 설정, 보기 메뉴 활성화
                if hasattr(self.app, 'menu_cfg'):
                    self.app.menubar.entryconfigure("설정", state="normal")
                if hasattr(self.app, 'menu_view'):
                    self.app.menubar.entryconfigure("보기", state="normal")
            except Exception as e:
                print(f"메뉴 보이기 오류: {e}")

    def _update_mirror_buttons_after_close(self):
        """안전교육 닫은 후 모든 패널의 거울보기 버튼 상태 업데이트"""
        if not self.app:
            return

        def update_buttons():
            try:
                # 모든 패널의 거울보기 버튼을 "거울보기"로 변경하고 활성화
                for key, panel in self.app.panels.items():
                    if hasattr(panel, 'header') and hasattr(panel.header, 'mirror_btn'):
                        panel.header.mirror_camera_ready = True
                        panel.header.mirror_btn.configure(
                            text="거울보기",
                            bg="#9C27B0",
                            state="normal"
                        )
                print("안전교육: 거울보기 버튼 상태 업데이트 완료")
            except Exception as e:
                print(f"안전교육: 거울보기 버튼 업데이트 오류: {e}")

        # 카메라 해제 후 잠시 대기 후 버튼 업데이트
        if self.app:
            self.app.after(800, update_buttons)

    def _get_root_window(self):
        """앱의 루트 윈도우 가져오기"""
        if self.app:
            return self.app.winfo_toplevel()
        return self.parent_frame.winfo_toplevel()
