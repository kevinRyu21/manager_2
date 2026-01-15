"""
서명 및 얼굴 촬영 화면

안전 교육 완료 후 서명과 얼굴 사진을 수집하는 전체 화면입니다.
(1.9.0 방식 - 오버레이 위에 Frame으로 전체 화면 표시)
"""

import tkinter as tk
from tkinter import messagebox
import os
import threading

# 외부 라이브러리 (선택)
try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_OK = True
except Exception:
    PIL_OK = False
    Image = ImageTk = ImageDraw = None

try:
    import cv2
    import numpy as np
    CV2_OK = True
except Exception:
    CV2_OK = False
    cv2 = np = None

# 새로운 PPE 감지 모듈 (YOLOv10 기반)
PPE_DETECTOR_AVAILABLE = False
try:
    from ..ppe import PPEDetector, PPEVisualizer, PPEStatus
    PPE_DETECTOR_AVAILABLE = True
except ImportError:
    PPEDetector = None
    PPEVisualizer = None
    PPEStatus = None


class SafetySignatureDialog:
    """얼굴 촬영 + 서명 전체 화면 (1.9.0 방식)"""

    def __init__(self, parent, camera, callback, photo_enabled=True, config=None,
                 safety_detector=None, ppe_detector=None, ppe_visualizer=None):
        """
        서명 화면 초기화

        Args:
            parent: 부모 프레임 (안전 교육 오버레이)
            camera: cv2.VideoCapture 객체 (None이면 얼굴 촬영 비활성화)
            callback: 완료 콜백 함수 (result 딕셔너리 전달)
            photo_enabled: 얼굴 촬영 활성화 여부
            config: 설정 객체
            safety_detector: SafetyEquipmentDetector 인스턴스 (얼굴 인식용) - 안전교육에서 공유
            ppe_detector: PPEDetector 인스턴스 - 안전교육에서 공유 (재초기화 방지)
            ppe_visualizer: PPEVisualizer 인스턴스 - 안전교육에서 공유 (재초기화 방지)
        """
        self.parent = parent  # 안전 교육 오버레이
        self.camera = camera
        self.callback = callback
        self.photo_enabled = photo_enabled and camera is not None
        self.config = config
        self.shared_safety_detector = safety_detector  # 공유 감지기

        self.dialog = None
        self.face_label = None
        self.face_image = None  # PIL Image
        self.recognized_name = None

        # 서명 관련
        self.signature_canvas = None
        self.signature_lines = []
        self.last_x = None
        self.last_y = None
        self.is_drawing = False
        self.line_width = 6  # 기본 선 굵기

        # 카메라 프리뷰 제어
        self.camera_frame_id = None
        self.preview_paused = False  # 서명 중 프리뷰 일시정지
        self.preview_update_interval = 33  # 프리뷰 업데이트 간격 (ms) - 30fps 목표

        # 비동기 AI 감지 관련
        self._ai_detection_running = False
        self._ai_detection_frame = None
        self._ai_detection_result = None
        self._ai_detection_lock = threading.Lock()

        # 완료 버튼
        self.btn_complete = None
        self.btn_capture = None  # 촬영/재촬영 버튼

        # 얼굴 인식 관련
        self.safety_detector = None

        # PPE 감지기 (안전교육에서 전달받아 재사용 - 빠른 전환)
        self.ppe_detector = ppe_detector
        self.ppe_visualizer = ppe_visualizer
        self._ppe_status_cache = None
        self._ppe_detections_cache = None

        # 전달받지 못한 경우에만 새로 초기화
        if self.ppe_detector is None and PPE_DETECTOR_AVAILABLE:
            try:
                from ..ppe import PPEDetector, PPEVisualizer
                self.ppe_detector = PPEDetector()
                self.ppe_visualizer = PPEVisualizer(font_size=5)
                print("서명 화면: YOLOv10 PPE 감지기 새로 초기화")
            except Exception as e:
                print(f"서명 화면: YOLOv10 PPE 감지기 초기화 실패: {e}")
        else:
            print("서명 화면: 안전교육에서 PPE 감지기 공유받음 (빠른 전환)")

        # 얼굴 감지 및 수동 촬영 관련
        self.face_detected_time = None  # 얼굴 처음 감지된 시간
        self.preview_recognized_name = None  # 미리보기 중 인식된 이름
        self.capture_datetime = None  # 촬영 시간
        self.face_recognition_done = False  # 얼굴 인식 완료 여부
        self.face_recognition_in_progress = False  # 얼굴 인식 진행 중

        # 안전장구 인식 관련 (실시간)
        self.ppe_status = {
            "helmet": {"worn": False, "color": None},
            "vest": {"worn": False, "color": None},
            "mask": {"worn": False},
            "glasses": {"worn": False},
            "gloves": {"worn": False},
            "boots": {"worn": False}
        }
        self.ppe_detection_interval = 0  # PPE 감지 간격 카운터 (매 프레임마다 하면 느림)

        # PPE 설정 로드 (환경설정에서)
        self.ppe_detection_enabled = True
        self.ppe_helmet_enabled = True
        self.ppe_vest_enabled = True
        self.ppe_mask_enabled = True
        self.ppe_glasses_enabled = True
        self.ppe_gloves_enabled = True
        self.ppe_boots_enabled = True
        self.ppe_helmet_name = "헬멧"
        self.ppe_vest_name = "조끼"
        self.ppe_mask_name = "마스크"
        self.ppe_glasses_name = "보안경"
        self.ppe_gloves_name = "장갑"
        self.ppe_boots_name = "안전화"
        self._load_ppe_settings()

        # 수동 촬영 관련
        self.countdown_active = False  # 카운트다운 진행 중
        self.countdown_remaining = 0  # 남은 카운트다운 초
        self.last_preview_frame = None  # 마지막 프리뷰 프레임 (촬영용)

        # 얼굴 인식 타임아웃 (5초)
        self.face_recognition_start_time = None  # 얼굴 인식 시작 시간
        self.face_recognition_timeout = 5  # 5초 타임아웃

        # 카메라 시작 시간 (얼굴 미감지 시 타임아웃용)
        self.camera_start_time = None
        self.no_face_timeout = 10  # 10초 후 얼굴 없이도 촬영 가능

        # 한글 폰트 캐시
        self._korean_font = None
        self._korean_font_loaded = False

        # 얼굴 인식 결과 캐시 (박스 표시용)
        self._face_results_cache = None

        # ID 추적 관련 (거울보기와 동일하게 - 마스크/얼굴 돌림 시 유지)
        self._tracked_persons = {}  # {track_id: {'name': str, 'bbox': (x1,y1,x2,y2), 'last_seen': time, 'confidence': float, 'center': (cx, cy)}}
        self._next_track_id = 1
        self._track_iou_threshold = 0.15  # 추적 IOU 임계값
        self._track_timeout = None  # 타임아웃 없음 - 한번 인식하면 영구 추적
        self._track_center_dist_threshold = 200  # 중심점 거리 임계값 (픽셀)

    def _load_ppe_settings(self):
        """환경설정에서 PPE 설정 로드"""
        try:
            if self.config is None:
                return

            env = self.config.env if hasattr(self.config, 'env') else {}

            # PPE 인식 사용 여부
            self.ppe_detection_enabled = bool(env.get("ppe_detection_enabled", True))

            # 개별 장구 인식 사용 여부
            self.ppe_helmet_enabled = bool(env.get("ppe_helmet_enabled", True))
            self.ppe_vest_enabled = bool(env.get("ppe_vest_enabled", True))
            self.ppe_mask_enabled = bool(env.get("ppe_mask_enabled", True))
            self.ppe_glasses_enabled = bool(env.get("ppe_glasses_enabled", True))
            self.ppe_gloves_enabled = bool(env.get("ppe_gloves_enabled", True))
            self.ppe_boots_enabled = bool(env.get("ppe_boots_enabled", True))

            # 장구 표시명
            self.ppe_helmet_name = str(env.get("ppe_helmet_name", "헬멧"))
            self.ppe_vest_name = str(env.get("ppe_vest_name", "조끼"))
            self.ppe_mask_name = str(env.get("ppe_mask_name", "마스크"))
            self.ppe_glasses_name = str(env.get("ppe_glasses_name", "보안경"))
            self.ppe_gloves_name = str(env.get("ppe_gloves_name", "장갑"))
            self.ppe_boots_name = str(env.get("ppe_boots_name", "안전화"))

            print(f"서명 화면: PPE 설정 로드 완료 - enabled={self.ppe_detection_enabled}")

        except Exception as e:
            print(f"서명 화면: PPE 설정 로드 오류 (기본값 사용): {e}")

    def _put_korean_text_on_frame(self, frame, text, position, color, font_size=24):
        """OpenCV 프레임에 한글 텍스트를 PIL로 그리기"""
        try:
            if not PIL_OK:
                return frame

            from PIL import ImageFont

            # 한글 폰트 로드 (캐시 사용)
            if not self._korean_font_loaded:
                self._korean_font_loaded = True
                font_paths = [
                    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            self._korean_font = ImageFont.truetype(font_path, font_size)
                            break
                        except:
                            continue
                if self._korean_font is None:
                    self._korean_font = ImageFont.load_default()

            # BGR → RGB 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_img)

            # 배경 박스 그리기 (가독성 향상)
            x, y = position
            try:
                bbox = draw.textbbox((x, y), text, font=self._korean_font)
                padding = 5
                draw.rectangle(
                    [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding],
                    fill=(0, 0, 0)
                )
            except:
                pass

            # 텍스트 그리기 (RGB 색상)
            draw.text(position, text, font=self._korean_font, fill=(color[2], color[1], color[0]))

            # RGB → BGR 변환
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"서명 화면: 한글 텍스트 표시 오류: {e}")
            return frame

    def show(self):
        """전체 화면 표시 (오버레이 위에 Frame으로)"""
        if not PIL_OK:
            messagebox.showerror("오류", "PIL(Pillow) 라이브러리가 필요합니다.")
            return

        # Frame으로 생성 (Toplevel 대신 - 전체 화면)
        self.dialog = tk.Frame(self.parent, bg="#2C3E50")
        self.dialog.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ESC로 닫기
        self.dialog.bind("<Escape>", lambda e: self._cancel())
        self.dialog.focus_set()

        # 제목
        title_frame = tk.Frame(self.dialog, bg="#2C3E50")
        title_frame.pack(fill="x", padx=20, pady=(15, 10))

        if self.photo_enabled:
            title_text = "안전 교육 확인 - 얼굴 촬영 및 서명"
        else:
            title_text = "안전 교육 확인 - 서명"

        title_label = tk.Label(title_frame, text=title_text,
                              font=("Pretendard", 20, "bold"), fg="#FFFFFF", bg="#2C3E50")
        title_label.pack()

        # 메인 컨테이너 (grid 사용)
        main_container = tk.Frame(self.dialog, bg="#2C3E50")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        if self.photo_enabled:
            # 그리드 가중치 설정 (6:4 비율 고정 - uniform으로 비율 유지)
            main_container.grid_rowconfigure(0, weight=1)
            main_container.grid_columnconfigure(0, weight=6, uniform="col")  # 카메라 (60%)
            main_container.grid_columnconfigure(1, weight=4, uniform="col")  # 서명 (40%)

            # 왼쪽: 얼굴 촬영 영역 (60%)
            face_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=3)
            face_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

            face_title = tk.Label(face_frame, text="1. 얼굴 촬영",
                                font=("Pretendard", 16, "bold"), fg="#FFD700", bg="#34495E")
            face_title.pack(pady=5)

            # 얼굴 미리보기 (카메라 화면 - 고정 크기)
            face_display = tk.Frame(face_frame, bg="#000000", relief="sunken", bd=3)
            face_display.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            # 내부 크기가 변해도 외부 프레임 크기 유지
            face_display.pack_propagate(False)

            self.face_label = tk.Label(face_display, bg="#000000", fg="#FFFFFF",
                                       text="카메라 로딩 중...",
                                       font=("Pretendard", 12, "bold"))
            self.face_label.pack(fill="both", expand=True)

            # 촬영 버튼 (얼굴 인식 전에는 비활성화)
            self.btn_capture = tk.Button(face_frame, text="📷 촬영", command=self._start_countdown,
                                         bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                                         relief="raised", bd=3, height=2, state="disabled",
                                         activebackground="#2980B9", activeforeground="#FFFFFF",
                                         disabledforeground="#CCCCCC")
            self.btn_capture.pack(pady=10, padx=10, fill="x")
        else:
            # 서명만 있는 경우 (전체 너비 사용)
            main_container.grid_rowconfigure(0, weight=1)
            main_container.grid_columnconfigure(0, weight=1)

        # 서명 영역
        sig_frame = tk.Frame(main_container, bg="#34495E", relief="raised", bd=3)
        if self.photo_enabled:
            sig_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            sig_title_text = "2. 서명"
        else:
            sig_frame.grid(row=0, column=0, sticky="nsew")
            sig_title_text = "서명"

        sig_title = tk.Label(sig_frame, text=sig_title_text,
                           font=("Pretendard", 16, "bold"), fg="#FFD700", bg="#34495E")
        sig_title.pack(pady=5)

        # 서명 안내 문구
        guide_label = tk.Label(sig_frame, text="정자로 이름을 또박또박 써 주세요.",
                               font=("Pretendard", 12, "bold"), fg="#FFFFFF", bg="#34495E")
        guide_label.pack(pady=(0, 5))

        # 서명 캔버스 (전체 영역 채움)
        canvas_container = tk.Frame(sig_frame, bg="#FFFFFF", relief="sunken", bd=3)
        canvas_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self.signature_canvas = tk.Canvas(canvas_container, bg="#FFFFFF", highlightthickness=0,
                                          cursor="pencil")
        self.signature_canvas.pack(fill="both", expand=True)

        # 터치스크린 및 마우스 이벤트 바인딩
        self.signature_canvas.bind("<Button-1>", self._on_pen_down)
        self.signature_canvas.bind("<B1-Motion>", self._on_pen_motion)
        self.signature_canvas.bind("<ButtonRelease-1>", self._on_pen_up)

        # 서명 제어 버튼들
        sig_button_frame = tk.Frame(sig_frame, bg="#34495E")
        sig_button_frame.pack(pady=5, padx=5, fill="x")

        # 선 두께 조절
        thickness_frame = tk.Frame(sig_button_frame, bg="#34495E")
        thickness_frame.pack(fill="x", pady=(0, 5))

        tk.Label(thickness_frame, text="선 두께:", font=("Pretendard", 10, "bold"),
                fg="#FFFFFF", bg="#34495E").pack(side="left", padx=(0, 5))

        self.thickness_var = tk.IntVar(value=self.line_width)
        thickness_scale = tk.Scale(thickness_frame, from_=2, to=12, orient="horizontal",
                                  variable=self.thickness_var, command=self._on_thickness_change,
                                  bg="#34495E", fg="#FFFFFF", highlightthickness=0,
                                  font=("Pretendard", 9, "bold"), length=100)
        thickness_scale.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # 지우기 버튼
        tk.Button(sig_button_frame, text="🗑 서명 지우기", command=self._clear_signature,
                 bg="#E74C3C", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 relief="raised", bd=3, height=1,
                 activebackground="#C0392B", activeforeground="#FFFFFF").pack(fill="x")

        # 하단 버튼
        bottom_frame = tk.Frame(self.dialog, bg="#2C3E50")
        bottom_frame.pack(fill="x", padx=20, pady=10)

        # 완료 버튼 (비활성화 상태로 시작)
        self.btn_complete = tk.Button(bottom_frame,
                                      text="✓ 완료 (안전 교육을 받았음을 확인합니다)",
                                      command=self._complete, state="disabled",
                                      bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                                      relief="raised", bd=3, height=2,
                                      disabledforeground="#CCCCCC")
        self.btn_complete.pack(side="left", padx=5, fill="x", expand=True)

        # 취소 버튼
        tk.Button(bottom_frame, text="✕ 취소", command=self._cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5)

        # 웹캠 프리뷰 시작 (얼굴 촬영이 활성화된 경우에만)
        if self.photo_enabled:
            self._init_face_recognition()
            self._start_preview()

        # 완료 버튼 상태 업데이트
        self._update_complete_button()

        print(f"서명 화면: 표시 완료 (photo_enabled={self.photo_enabled})")

    def _on_thickness_change(self, value):
        """선 두께 변경"""
        self.line_width = int(value)

    def _init_face_recognition(self):
        """얼굴 인식 초기화"""
        # 공유 감지기가 있으면 그것을 사용
        if self.shared_safety_detector is not None:
            self.safety_detector = self.shared_safety_detector
            print("서명 화면: 공유 얼굴 인식 감지기 사용")
            return

        # 공유 감지기가 없으면 새로 생성 (백그라운드에서)
        def init_async():
            try:
                from ..sensor.safety_detector import SafetyEquipmentDetector
                self.safety_detector = SafetyEquipmentDetector(camera=None)
                self.safety_detector.enable_face_recognition(True)
                print("서명 화면: 새 얼굴 인식 감지기 생성 완료")
            except Exception as e:
                print(f"서명 화면: 얼굴 인식 초기화 실패: {e}")

        threading.Thread(target=init_async, daemon=True).start()

    def _start_preview(self):
        """웹캠 프리뷰 시작"""
        if not self.photo_enabled:
            return

        if not CV2_OK or self.camera is None:
            if self.face_label:
                self.face_label.configure(text="카메라가 준비되지 않았습니다.", fg="#FF6B6B")
            return

        if not self.camera.isOpened():
            if self.face_label:
                self.face_label.configure(text="카메라가 열려있지 않습니다.", fg="#FF6B6B")
            return

        # 카메라 시작 시간 기록 (얼굴 미감지 타임아웃용)
        import time
        self.camera_start_time = time.time()

        self._update_preview()

    def _update_preview(self):
        """웹캠 프리뷰 업데이트 (최적화 버전 - 비동기 AI 감지)"""
        if not self.dialog or not self.dialog.winfo_exists():
            return

        # 이미 얼굴이 촬영되었으면 프리뷰 중단
        if self.face_image is not None:
            return

        # 서명 중에는 프리뷰 일시정지
        if self.preview_paused:
            if self.dialog and self.dialog.winfo_exists():
                self.camera_frame_id = self.dialog.after(self.preview_update_interval, self._update_preview)
            return

        try:
            # 버퍼 비우기
            self.camera.grab()
            ret, frame = self.camera.read()

            if not ret or frame is None:
                if self.dialog and self.dialog.winfo_exists():
                    self.camera_frame_id = self.dialog.after(self.preview_update_interval, self._update_preview)
                return

            if PIL_OK and CV2_OK:
                # 원본 프레임 저장 (저장용, 반전 전)
                self.last_preview_frame = frame.copy()

                # 화면 반전 설정 읽기 (환경설정에서 저장된 값 사용)
                should_flip = True  # 기본값
                try:
                    if self.config and hasattr(self.config, 'camera'):
                        should_flip = self.config.camera.get("flip_horizontal", True)
                except:
                    should_flip = True

                # 화면 표시용 프레임 (반전 적용)
                display_frame = frame.copy()
                if should_flip:
                    display_frame = cv2.flip(display_frame, 1)

                # AI 감지는 원본 프레임 사용
                frame = display_frame  # 화면 표시는 반전된 프레임 사용

                # 비동기 AI 감지 시작 (이미 실행 중이 아닌 경우만)
                # PPE 감지 비활성화된 경우에도 얼굴 인식은 필요
                if not self._ai_detection_running:
                    self._start_async_ai_detection(frame.copy())

                # 카운트다운 중이면 카운트 표시
                if self.countdown_active:
                    # 화면 중앙에 카운트다운 표시
                    h, w = frame.shape[:2]
                    text = str(self.countdown_remaining)
                    font_scale = 5
                    thickness = 10
                    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                    x = (w - text_w) // 2
                    y = (h + text_h) // 2
                    # 배경
                    cv2.rectangle(frame, (x-20, y-text_h-20), (x+text_w+20, y+20), (0, 0, 0), -1)
                    # 숫자
                    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)

                else:
                    # 비동기 AI 감지 결과 적용 (캐시된 결과 사용)
                    import time
                    current_time = time.time()

                    # 얼굴 감지 결과 확인 (캐시된 결과 사용)
                    has_face = self._face_results_cache is not None and len(self._face_results_cache.get('faces', [])) > 0

                    if has_face:
                        # 얼굴 인식 시작 시간 기록 (타임아웃용)
                        if self.face_recognition_start_time is None:
                            self.face_recognition_start_time = current_time

                        # 얼굴 처음 감지 시 상태 업데이트
                        if self.face_detected_time is None:
                            self.face_detected_time = current_time
                            self.face_recognition_in_progress = True

                        # 5초 타임아웃 체크 - 얼굴 인식 완료 안 되면 미인식으로 진행
                        elapsed = current_time - self.face_recognition_start_time
                        if not self.face_recognition_done and elapsed >= self.face_recognition_timeout:
                            self.face_recognition_done = True
                            self.face_recognition_in_progress = False
                            print(f"서명 화면: 얼굴 인식 타임아웃 ({self.face_recognition_timeout}초) - 미인식으로 진행")

                        # 얼굴 인식이 완료되면 촬영 버튼 활성화 (등록/미등록 모두)
                        if self.face_recognition_done and self.btn_capture:
                            if self.preview_recognized_name:
                                # 등록된 얼굴
                                self.btn_capture.configure(
                                    state="normal",
                                    bg="#27AE60",
                                    text=f"📷 촬영 ({self.preview_recognized_name})"
                                )
                            else:
                                # 미등록 얼굴 - 촬영 버튼 활성화 (주황색)
                                self.btn_capture.configure(
                                    state="normal",
                                    bg="#E67E22",
                                    text="📷 촬영 (미등록 얼굴)"
                                )
                    else:
                        # 얼굴이 감지 안 되면 상태 리셋
                        self.face_detected_time = None
                        self.face_recognition_done = False
                        self.face_recognition_in_progress = False
                        self.face_recognition_start_time = None

                        # 얼굴 미감지 타임아웃 체크 (10초 후 얼굴 없이도 촬영 가능)
                        if self.camera_start_time is not None:
                            no_face_elapsed = current_time - self.camera_start_time
                            if no_face_elapsed >= self.no_face_timeout:
                                # 10초 경과 - 얼굴 없이도 촬영 가능
                                if self.btn_capture and not self.countdown_active:
                                    self.btn_capture.configure(
                                        state="normal",
                                        bg="#9B59B6",  # 보라색 - 얼굴 미감지 촬영
                                        text="📷 촬영 (얼굴 미감지)"
                                    )
                            else:
                                # 타임아웃 전 - 남은 시간 표시
                                remaining = int(self.no_face_timeout - no_face_elapsed)
                                if self.btn_capture and not self.countdown_active:
                                    self.btn_capture.configure(
                                        state="disabled",
                                        bg="#95A5A6",
                                        text=f"📷 촬영 (얼굴 인식 중... {remaining}초)"
                                    )
                        else:
                            # 촬영 버튼 비활성화
                            if self.btn_capture and not self.countdown_active:
                                self.btn_capture.configure(
                                    state="disabled",
                                    bg="#95A5A6",
                                    text="📷 촬영 (얼굴을 인식해 주세요)"
                                )

                # 안전장구 상태 표시 (화면 좌측 상단, 설정에서 활성화된 경우만)
                if self.ppe_detection_enabled:
                    frame = self._draw_ppe_status(frame)

                # 프레임을 RGB로 변환하여 표시
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)

                # 디스플레이 크기 가져오기 (라벨 전체 영역)
                try:
                    display_width = self.face_label.winfo_width()
                    display_height = self.face_label.winfo_height()
                    if display_width < 100 or display_height < 100:
                        display_width = 640
                        display_height = 480
                except Exception:
                    display_width = 640
                    display_height = 480

                # 영역에 맞게 리사이즈 (비율 유지, 잘리지 않게 - letterbox 방식)
                img_ratio = img.width / img.height
                display_ratio = display_width / display_height

                if img_ratio > display_ratio:
                    # 이미지가 더 넓음 - 너비에 맞추고 상하 여백
                    new_width = display_width
                    new_height = int(display_width / img_ratio)
                else:
                    # 이미지가 더 높음 - 높이에 맞추고 좌우 여백
                    new_height = display_height
                    new_width = int(display_height * img_ratio)

                img = img.resize((new_width, new_height), Image.LANCZOS)

                # 검은색 배경에 중앙 배치
                final_img = Image.new("RGB", (display_width, display_height), (0, 0, 0))
                paste_x = (display_width - new_width) // 2
                paste_y = (display_height - new_height) // 2
                final_img.paste(img, (paste_x, paste_y))
                img = final_img

                photo = ImageTk.PhotoImage(img)

                if self.face_label and self.face_label.winfo_exists():
                    self.face_label.configure(image=photo, text="")
                    self.face_label.image = photo

        except Exception as e:
            print(f"서명 화면: 카메라 오류: {e}")

        # 다음 프레임
        if self.dialog and self.dialog.winfo_exists():
            self.camera_frame_id = self.dialog.after(self.preview_update_interval, self._update_preview)

    def _start_async_ai_detection(self, frame):
        """비동기 AI 감지 시작 (백그라운드 스레드)"""
        self._ai_detection_running = True

        def run_detection():
            try:
                # PPE 감지 (YOLOv10) - PPE 감지가 활성화된 경우만
                if self.ppe_detection_enabled and self.ppe_detector is not None and self.ppe_detector.is_available():
                    detections = self.ppe_detector.detect(frame)
                    if detections:
                        with self._ai_detection_lock:
                            self._ppe_detections_cache = detections
                            ppe_status = detections[0].ppe_status
                            self._ppe_status_cache = ppe_status

                            # PPE 상태 업데이트
                            self.ppe_status["helmet"]["worn"] = ppe_status.helmet
                            self.ppe_status["helmet"]["color"] = ppe_status.helmet_color_kr or ppe_status.helmet_color
                            self.ppe_status["vest"]["worn"] = ppe_status.vest
                            self.ppe_status["vest"]["color"] = ppe_status.vest_color_kr or ppe_status.vest_color
                            self.ppe_status["mask"]["worn"] = ppe_status.mask
                            self.ppe_status["glasses"]["worn"] = ppe_status.glasses
                            self.ppe_status["gloves"]["worn"] = ppe_status.gloves
                            self.ppe_status["gloves"]["count"] = ppe_status.gloves_count
                            self.ppe_status["boots"]["worn"] = ppe_status.boots
                    else:
                        with self._ai_detection_lock:
                            self._ppe_detections_cache = None
                            self._ppe_status_cache = None

                # 얼굴 인식 (safety_detector) - PPE와 별개로 항상 수행 (실시간 최적화)
                if self.safety_detector is not None:
                    try:
                        face_results = self.safety_detector.detect_face_only(frame)
                        if face_results:
                            with self._ai_detection_lock:
                                self._face_results_cache = face_results

                                # ID 추적: 사람 바운딩 박스와 얼굴을 매칭하여 추적
                                if self._ppe_detections_cache:
                                    self._update_person_tracking(self._ppe_detections_cache, face_results)

                                # 얼굴 인식 결과 처리
                                recognized = face_results.get('recognized_faces', [])
                                if recognized:
                                    for rec in recognized:
                                        name = rec.get('name', 'Unknown')
                                        if name and name != 'Unknown':
                                            self.preview_recognized_name = name
                                            self.face_recognition_done = True
                                            self.face_recognition_in_progress = False
                                            break
                                    else:
                                        # 얼굴은 있지만 등록된 사람이 아닌 경우
                                        if not self.face_recognition_done:
                                            self.face_recognition_done = True
                                            self.face_recognition_in_progress = False
                                elif face_results.get('faces'):
                                    # 얼굴은 감지되었지만 인식 결과가 없는 경우
                                    if not self.face_recognition_done:
                                        self.face_recognition_done = True
                                        self.face_recognition_in_progress = False
                    except Exception as e:
                        print(f"서명 화면: 얼굴 인식 오류: {e}")

            except Exception as e:
                print(f"서명 화면: 비동기 AI 감지 오류: {e}")
            finally:
                self._ai_detection_running = False

        threading.Thread(target=run_detection, daemon=True).start()

    def _start_countdown(self):
        """촬영 버튼 클릭 시 3초 카운트다운 시작"""
        if self.countdown_active:
            return

        self.countdown_active = True
        self.countdown_remaining = 3

        # 버튼 비활성화
        if self.btn_capture:
            self.btn_capture.configure(state="disabled", text="촬영 중...")

        # 카운트다운 시작
        self._do_countdown()

    def _do_countdown(self):
        """카운트다운 처리"""
        if not self.dialog or not self.dialog.winfo_exists():
            return

        if self.countdown_remaining > 0:
            self.countdown_remaining -= 1
            # 1초 후 다음 카운트
            self.dialog.after(1000, self._do_countdown)
        else:
            # 카운트다운 완료 - 촬영
            self._capture_face()

    def _capture_face(self):
        """실제 촬영 수행"""
        self.countdown_active = False

        if self.last_preview_frame is None:
            print("서명 화면: 촬영할 프레임이 없습니다.")
            # 버튼 복원
            if self.btn_capture:
                self.btn_capture.configure(
                    state="normal",
                    bg="#27AE60",
                    text="📷 촬영 (3초 후 자동촬영)"
                )
            return

        try:
            import datetime
            frame = self.last_preview_frame.copy()

            # 화면 반전 설정 읽기 (환경설정에서 저장된 값 사용)
            # 화면에 표시된 대로 저장하기 위해 반전 적용
            should_flip = True  # 기본값
            try:
                if self.config and hasattr(self.config, 'camera'):
                    should_flip = self.config.camera.get("flip_horizontal", True)
            except:
                should_flip = True

            if should_flip:
                frame = cv2.flip(frame, 1)

            # 촬영 시간 기록
            self.capture_datetime = datetime.datetime.now()

            # 인식된 이름 저장
            if self.preview_recognized_name:
                self.recognized_name = self.preview_recognized_name

            # BGR을 RGB로 변환하여 저장
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.face_image = Image.fromarray(frame_rgb)

            # 촬영된 이미지를 화면에 표시 (이름+일시 포함)
            self._display_captured_face_with_info(frame_rgb)

            # 버튼을 재촬영 버튼으로 변경
            if self.btn_capture:
                self.btn_capture.configure(
                    state="normal",
                    bg="#3498DB",
                    text="🔄 재촬영",
                    command=self._recapture_face
                )

            # 완료 버튼 상태 업데이트
            self._update_complete_button()

            print(f"서명 화면: 촬영 완료 (name={self.recognized_name})")

        except Exception as e:
            print(f"서명 화면: 촬영 오류: {e}")
            # 버튼 복원
            if self.btn_capture:
                self.btn_capture.configure(
                    state="normal",
                    bg="#27AE60",
                    text="📷 촬영 (3초 후 자동촬영)"
                )

    def _display_captured_face(self, frame_rgb):
        """촬영된 얼굴을 화면에 표시"""
        try:
            img = Image.fromarray(frame_rgb)

            # 디스플레이 크기 가져오기 (라벨 전체 영역)
            try:
                display_width = self.face_label.winfo_width()
                display_height = self.face_label.winfo_height()
                if display_width < 100 or display_height < 100:
                    display_width = 640
                    display_height = 480
            except Exception:
                display_width = 640
                display_height = 480

            # 영역에 맞게 리사이즈 (비율 유지, 잘리지 않게 - letterbox 방식)
            img_ratio = img.width / img.height
            display_ratio = display_width / display_height

            if img_ratio > display_ratio:
                # 이미지가 더 넓음 - 너비에 맞추고 상하 여백
                new_width = display_width
                new_height = int(display_width / img_ratio)
            else:
                # 이미지가 더 높음 - 높이에 맞추고 좌우 여백
                new_height = display_height
                new_width = int(display_height * img_ratio)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            # 검은색 배경에 중앙 배치
            final_img = Image.new("RGB", (display_width, display_height), (0, 0, 0))
            paste_x = (display_width - new_width) // 2
            paste_y = (display_height - new_height) // 2
            final_img.paste(img, (paste_x, paste_y))
            img = final_img

            # 녹색 테두리 추가 (촬영 완료 표시)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (img.width-1, img.height-1)], outline="#27AE60", width=5)

            photo = ImageTk.PhotoImage(img)

            if self.face_label and self.face_label.winfo_exists():
                self.face_label.configure(image=photo, text="")
                self.face_label.image = photo

        except Exception as e:
            print(f"서명 화면: 얼굴 표시 오류: {e}")

    def _try_recognize_face(self, frame):
        """얼굴 인식 시도 (백그라운드에서) - 실시간 최적화"""
        if self.safety_detector:
            def recognize_async():
                try:
                    results = self.safety_detector.detect_face_only(frame)
                    if results and results.get('recognized_faces'):
                        for face_info in results['recognized_faces']:
                            name = face_info.get('name', 'Unknown')
                            if name != 'Unknown':
                                self.recognized_name = name
                                print(f"서명 화면: 얼굴 인식됨 - {name}")
                                break
                except Exception as e:
                    print(f"서명 화면: 얼굴 인식 실패: {e}")

            threading.Thread(target=recognize_async, daemon=True).start()

    def _try_recognize_face_preview(self, frame):
        """미리보기 중 얼굴 인식 시도 (백그라운드에서)"""
        self.preview_recognized_name = None
        self.face_recognition_in_progress = True
        self.face_recognition_done = False

        if self.safety_detector:
            def recognize_async():
                try:
                    # 디버그: safety_detector 상태 확인
                    print(f"서명 화면: 얼굴 인식 시작...")
                    print(f"  - use_insightface: {getattr(self.safety_detector, 'use_insightface', 'N/A')}")
                    print(f"  - face_recognition_enabled: {getattr(self.safety_detector, 'face_recognition_enabled', 'N/A')}")
                    print(f"  - face_db: {self.safety_detector.face_db is not None if hasattr(self.safety_detector, 'face_db') else 'N/A'}")
                    print(f"  - face_app: {self.safety_detector.face_app is not None if hasattr(self.safety_detector, 'face_app') else 'N/A'}")

                    results = self.safety_detector.detect_face_only(frame)

                    # 디버그: 결과 확인
                    if results:
                        print(f"서명 화면: detect_face_only 결과 - recognized_faces: {results.get('recognized_faces', [])}")
                        # 얼굴 인식 결과 캐시에 저장 (박스 표시용)
                        self._face_results_cache = results

                    if results and results.get('recognized_faces'):
                        for face_info in results['recognized_faces']:
                            name = face_info.get('name', 'Unknown')
                            if name != 'Unknown':
                                self.preview_recognized_name = name
                                print(f"서명 화면: 얼굴 인식 성공 - {name}")
                                break
                    # 인식 완료 (등록된 사람이든 아니든)
                    self.face_recognition_done = True
                    self.face_recognition_in_progress = False
                    print(f"서명 화면: 얼굴 인식 완료 (name={self.preview_recognized_name})")
                except Exception as e:
                    import traceback
                    print(f"서명 화면: 얼굴 인식 실패: {e}")
                    traceback.print_exc()
                    # 오류 시에도 완료 처리 (미등록으로 간주)
                    self.face_recognition_done = True
                    self.face_recognition_in_progress = False

            threading.Thread(target=recognize_async, daemon=True).start()
        else:
            # safety_detector가 없으면 인식 완료 처리
            self.face_recognition_done = True
            self.face_recognition_in_progress = False
            print("서명 화면: safety_detector 없음 - 인식 스킵")

    def _display_captured_face_with_info(self, frame_rgb):
        """촬영된 얼굴을 화면에 표시 (이름+촬영일시 포함)"""
        try:
            img = Image.fromarray(frame_rgb)

            # 디스플레이 크기 가져오기 (라벨 전체 영역)
            try:
                display_width = self.face_label.winfo_width()
                display_height = self.face_label.winfo_height()
                if display_width < 100 or display_height < 100:
                    display_width = 640
                    display_height = 480
            except Exception:
                display_width = 640
                display_height = 480

            # 영역에 맞게 리사이즈 (비율 유지, 잘리지 않게 - letterbox 방식)
            img_ratio = img.width / img.height
            display_ratio = display_width / display_height

            if img_ratio > display_ratio:
                # 이미지가 더 넓음 - 너비에 맞추고 상하 여백
                new_width = display_width
                new_height = int(display_width / img_ratio)
            else:
                # 이미지가 더 높음 - 높이에 맞추고 좌우 여백
                new_height = display_height
                new_width = int(display_height * img_ratio)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            # 검은색 배경에 중앙 배치
            final_img = Image.new("RGB", (display_width, display_height), (0, 0, 0))
            paste_x = (display_width - new_width) // 2
            paste_y = (display_height - new_height) // 2
            final_img.paste(img, (paste_x, paste_y))
            img = final_img

            # 녹색 테두리 추가 (촬영 완료 표시)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (img.width-1, img.height-1)], outline="#27AE60", width=5)

            # 이름 + 촬영일시 텍스트 표시
            info_text = ""
            if self.recognized_name:
                info_text = self.recognized_name
            if hasattr(self, 'capture_datetime') and self.capture_datetime:
                datetime_str = self.capture_datetime.strftime("%Y-%m-%d %H:%M:%S")
                if info_text:
                    info_text += f"\n{datetime_str}"
                else:
                    info_text = datetime_str

            # 텍스트를 이미지 하단에 배경과 함께 표시
            if info_text:
                try:
                    # 한글 폰트 로드 시도
                    try:
                        from PIL import ImageFont
                        # 시스템 한글 폰트 경로들
                        font_paths = [
                            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        ]
                        font = None
                        for font_path in font_paths:
                            if os.path.exists(font_path):
                                font = ImageFont.truetype(font_path, 16)
                                break
                        if font is None:
                            font = ImageFont.load_default()
                    except:
                        font = ImageFont.load_default()

                    # 텍스트 크기 계산
                    lines = info_text.split('\n')
                    line_height = 20
                    text_height = len(lines) * line_height + 10

                    # 반투명 배경 그리기
                    bg_y = img.height - text_height - 5
                    draw.rectangle([(5, bg_y), (img.width-5, img.height-5)],
                                   fill=(0, 0, 0, 180))

                    # 텍스트 그리기
                    y_offset = bg_y + 5
                    for line in lines:
                        draw.text((10, y_offset), line, fill="#FFFFFF", font=font)
                        y_offset += line_height
                except Exception as e:
                    print(f"서명 화면: 텍스트 표시 오류: {e}")

            photo = ImageTk.PhotoImage(img)

            if self.face_label and self.face_label.winfo_exists():
                self.face_label.configure(image=photo, text="")
                self.face_label.image = photo

        except Exception as e:
            print(f"서명 화면: 얼굴 표시 오류: {e}")

    def _recapture_face(self):
        """재촬영 - 촬영된 사진 삭제하고 다시 프리뷰 시작"""
        # 촬영된 사진 삭제
        self.face_image = None
        self.recognized_name = None
        self.face_detected_time = None
        self.preview_recognized_name = None
        self.capture_datetime = None
        self.face_recognition_done = False
        self.face_recognition_in_progress = False
        self.face_recognition_start_time = None  # 타임아웃 리셋
        self.countdown_active = False
        self.countdown_remaining = 0
        self.last_preview_frame = None

        # 버튼을 촬영 버튼으로 변경 (비활성화 상태)
        if self.btn_capture:
            self.btn_capture.configure(
                state="disabled",
                bg="#95A5A6",
                text="📷 촬영 (얼굴을 인식해 주세요)",
                command=self._start_countdown
            )

        # 완료 버튼 상태 업데이트
        self._update_complete_button()

        # face_label 초기화
        if self.face_label:
            self.face_label.configure(image="", text="카메라 로딩 중...")

        # 프리뷰 다시 시작
        self._update_preview()

    def _on_pen_down(self, event):
        """펜 누름"""
        self.is_drawing = True
        self.last_x = event.x
        self.last_y = event.y
        self.preview_paused = True  # 서명 중 프리뷰 일시정지

    def _on_pen_motion(self, event):
        """펜 이동 (드래그)"""
        if self.is_drawing and self.last_x is not None:
            # 선 그리기
            line_id = self.signature_canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill="#000000", width=self.line_width, smooth=True,
                capstyle="round", joinstyle="round"
            )
            self.signature_lines.append(line_id)
            self.last_x = event.x
            self.last_y = event.y

    def _on_pen_up(self, event):
        """펜 뗌"""
        self.is_drawing = False
        self.last_x = None
        self.last_y = None
        self.preview_paused = False  # 프리뷰 재개

        # 완료 버튼 상태 업데이트
        self._update_complete_button()

    def _clear_signature(self):
        """서명 지우기"""
        for line_id in self.signature_lines:
            self.signature_canvas.delete(line_id)
        self.signature_lines.clear()

        # 완료 버튼 상태 업데이트
        self._update_complete_button()

    def _update_complete_button(self):
        """완료 버튼 상태 업데이트"""
        if not self.btn_complete:
            return

        # 조건 확인
        has_signature = len(self.signature_lines) > 0
        has_face = not self.photo_enabled or self.face_image is not None

        if has_signature and has_face:
            self.btn_complete.configure(state="normal", bg="#27AE60")
        else:
            self.btn_complete.configure(state="disabled", bg="#95A5A6")

    def _get_signature_image(self):
        """서명 캔버스를 이미지로 변환"""
        if not self.signature_lines:
            return None

        try:
            width = self.signature_canvas.winfo_width()
            height = self.signature_canvas.winfo_height()

            # 흰색 배경 이미지 생성
            img = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(img)

            # 캔버스의 모든 선 다시 그리기
            for line_id in self.signature_lines:
                coords = self.signature_canvas.coords(line_id)
                if len(coords) >= 4:
                    draw.line(coords, fill="black", width=self.line_width)

            return img

        except Exception as e:
            print(f"서명 이미지 생성 오류: {e}")
            return None

    def _complete(self):
        """완료"""
        # 서명 확인
        if not self.signature_lines:
            messagebox.showwarning("서명 필요", "서명을 해주세요.")
            return

        # 얼굴 촬영 확인 (활성화된 경우)
        if self.photo_enabled and self.face_image is None:
            messagebox.showwarning("사진 필요", "얼굴 사진을 촬영해 주세요.")
            return

        # 서명 이미지 생성
        signature_image = self._get_signature_image()
        if signature_image is None:
            messagebox.showerror("오류", "서명 이미지 생성에 실패했습니다.")
            return

        # 안전장구 정보 수집 (safety_detector가 있으면)
        safety_equipment = self._get_safety_equipment_info()

        # 결과 저장
        result = {
            "face_image": self.face_image,
            "signature_image": signature_image,
            "recognized_name": self.recognized_name,
            "safety_equipment": safety_equipment
        }

        # 저장 확인 팝업 표시 (서명 화면 위에서)
        self._show_save_confirm_popup(result)

    def _show_save_confirm_popup(self, result):
        """저장 확인 팝업 표시 - 확인 후 콜백 호출"""
        # 서명 화면 위에 팝업 표시
        popup = tk.Toplevel(self.dialog)
        popup.title("저장 확인")
        popup.configure(bg="#27AE60")

        # 화면 중앙 배치
        window_width = 600
        window_height = 400
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 포커스 설정
        popup.transient(self.dialog)
        popup.grab_set()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.focus_force()

        # 메시지
        recognized_name = result.get("recognized_name")
        if recognized_name:
            message_text = f"안전 교육 확인이 완료되었습니다!\n\n인식된 이름: {recognized_name}\n\n저장하시겠습니까?"
        else:
            message_text = "안전 교육 확인이 완료되었습니다!\n\n저장하시겠습니까?"

        msg_label = tk.Label(popup,
                           text=message_text,
                           font=("Pretendard", 18, "bold"),
                           fg="#FFFFFF", bg="#27AE60",
                           wraplength=550, justify="center")
        msg_label.pack(pady=50, padx=30)

        # 버튼 프레임
        btn_frame = tk.Frame(popup, bg="#27AE60")
        btn_frame.pack(pady=30)

        # 확인 버튼 클릭 시
        def on_confirm():
            # 팝업 먼저 닫기
            popup.grab_release()
            popup.destroy()

            # 콜백과 정리를 지연 호출 (이벤트 루프가 정리될 시간 확보)
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(100, lambda: self._finish_and_callback(result))
            else:
                # dialog가 이미 없으면 직접 호출
                self._finish_and_callback(result)

        # 취소 버튼 클릭 시
        def on_cancel():
            popup.grab_release()
            popup.destroy()
            # 팝업만 닫고 서명 화면으로 돌아감

        # 확인 버튼
        btn_ok = tk.Button(btn_frame, text="✓ 확인", command=on_confirm,
                          bg="#FFFFFF", fg="#27AE60",
                          font=("Pretendard", 16, "bold"),
                          relief="raised", bd=3, width=12, height=2,
                          activebackground="#ECF0F1", activeforeground="#27AE60")
        btn_ok.pack(side="left", padx=20)

        # 취소 버튼
        btn_cancel = tk.Button(btn_frame, text="✕ 취소", command=on_cancel,
                              bg="#E74C3C", fg="#FFFFFF",
                              font=("Pretendard", 16, "bold"),
                              relief="raised", bd=3, width=12, height=2,
                              activebackground="#C0392B", activeforeground="#FFFFFF")
        btn_cancel.pack(side="left", padx=20)

        # 확인 버튼에 포커스
        btn_ok.focus_set()

    def _finish_and_callback(self, result):
        """정리 및 콜백 호출 (지연 호출용)"""
        print("[서명 화면] 정리 및 콜백 호출 시작")

        # 콜백 저장 (cleanup에서 self.callback이 None이 될 수 있음)
        callback = self.callback

        # parent의 master (app) 저장 - 콜백 지연 호출에 사용
        app_master = None
        try:
            if self.parent and self.parent.winfo_exists():
                app_master = self.parent.master
        except Exception:
            pass

        # 콜백 함수 정의 (cleanup 전에 정의)
        def do_callback():
            try:
                print("[서명 화면] 콜백 실행 중...")
                callback(result)
                print("[서명 화면] 콜백 실행 완료")
            except Exception as e:
                print(f"[서명 화면] 콜백 실행 오류: {e}")
                import traceback
                traceback.print_exc()

        def cleanup_and_callback():
            """정리 후 콜백 실행"""
            try:
                # 정리 먼저 수행
                self._cleanup()
            except Exception as e:
                print(f"[서명 화면] cleanup 오류: {e}")

            # 콜백 실행
            if callback:
                do_callback()

        # app_master를 통해 지연 호출 (타이밍 문제 회피)
        try:
            if app_master and app_master.winfo_exists():
                print("[서명 화면] 지연 정리 및 콜백 호출 (app_master, 100ms)")
                app_master.after(100, cleanup_and_callback)
            else:
                # master 없으면 직접 실행
                print("[서명 화면] 직접 정리 및 콜백 호출")
                cleanup_and_callback()
        except Exception as e:
            print(f"[서명 화면] 콜백 예약 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시에도 직접 실행 시도
            cleanup_and_callback()

    def _detect_ppe_realtime(self, frame):
        """실시간 안전장구 감지 - YOLOv10 사용 + ID 추적 (거울보기와 동일)"""
        try:
            # 새로운 PPE 감지기 사용 (우선)
            if self.ppe_detector is not None and self.ppe_detector.is_available():
                detections = self.ppe_detector.detect(frame)
                if detections:
                    self._ppe_detections_cache = detections
                    ppe_status = detections[0].ppe_status
                    self._ppe_status_cache = ppe_status

                    # 헬멧 정보
                    self.ppe_status["helmet"]["worn"] = ppe_status.helmet
                    self.ppe_status["helmet"]["color"] = ppe_status.helmet_color_kr or ppe_status.helmet_color

                    # 조끼 정보
                    self.ppe_status["vest"]["worn"] = ppe_status.vest
                    self.ppe_status["vest"]["color"] = ppe_status.vest_color_kr or ppe_status.vest_color

                    # 마스크 정보
                    self.ppe_status["mask"]["worn"] = ppe_status.mask

                    # 보안경 정보
                    self.ppe_status["glasses"]["worn"] = ppe_status.glasses

                    # 장갑 정보 (좌/우 구분, 개수 정보 포함)
                    self.ppe_status["gloves"]["worn"] = ppe_status.gloves
                    self.ppe_status["gloves"]["count"] = ppe_status.gloves_count

                    # 안전화 정보
                    self.ppe_status["boots"]["worn"] = ppe_status.boots

                    # 얼굴 인식 (safety_detector에서 기존 DB 사용) - 실시간 최적화
                    if self.safety_detector is not None:
                        try:
                            face_results = self.safety_detector.detect_face_only(frame)
                            if face_results:
                                self._face_results_cache = face_results

                                # ID 추적: 사람 바운딩 박스와 얼굴을 매칭하여 추적
                                self._update_person_tracking(detections, face_results)

                                # 감지된 사람에 얼굴 정보 매핑 (추적 ID 기반)
                                for det in detections:
                                    matched_name = self._get_tracked_name_for_detection(det)
                                    if matched_name:
                                        det.face_detected = True
                                        det.face_name = matched_name
                        except Exception as e:
                            print(f"서명 화면: 얼굴 인식 오류: {e}")
                else:
                    self._ppe_detections_cache = None
                    self._ppe_status_cache = None
                return

            # 기존 safety_detector 사용 (fallback) - 실시간 최적화
            if self.safety_detector is None:
                return

            results = self.safety_detector.detect_face_only(frame)
            if results:
                self._face_results_cache = results  # 얼굴 인식 결과 캐시
                ppe_results = results.get('ppe', {})

                self.ppe_status["helmet"]["worn"] = ppe_results.get('helmet', False)
                self.ppe_status["helmet"]["color"] = ppe_results.get('helmet_color')
                self.ppe_status["vest"]["worn"] = ppe_results.get('vest', False)
                self.ppe_status["vest"]["color"] = ppe_results.get('vest_color')
                self.ppe_status["mask"]["worn"] = ppe_results.get('mask', False)
                self.ppe_status["glasses"]["worn"] = ppe_results.get('glasses', False)
                self.ppe_status["gloves"]["worn"] = ppe_results.get('gloves', False)
                self.ppe_status["boots"]["worn"] = ppe_results.get('boots', False)

        except Exception as e:
            # 오류 시 무시 (실시간이므로 다음 프레임에서 재시도)
            pass

    def _draw_ppe_status(self, frame):
        """프레임에 안전장구 상태 표시 - PPEVisualizer 사용 (거울보기와 동일한 설정 연동)"""
        try:
            # 새로운 PPE Visualizer 사용 (우선)
            if self.ppe_visualizer is not None and self._ppe_status_cache is not None:
                # 활성화된 항목 및 이름 (config에서 가져오기 - 거울보기와 동일)
                enabled_items = {
                    'helmet': self.ppe_helmet_enabled,
                    'vest': self.ppe_vest_enabled,
                    'mask': self.ppe_mask_enabled,
                    'glasses': self.ppe_glasses_enabled,
                    'gloves': self.ppe_gloves_enabled,
                    'boots': self.ppe_boots_enabled
                }
                item_names = {
                    'helmet': self.ppe_helmet_name,
                    'vest': self.ppe_vest_name,
                    'mask': self.ppe_mask_name,
                    'glasses': self.ppe_glasses_name,
                    'gloves': self.ppe_gloves_name,
                    'boots': self.ppe_boots_name
                }

                # 1) PPE 바운딩 박스 및 레이블 (ID 추적 정보 포함)
                if self._ppe_detections_cache:
                    frame = self.ppe_visualizer.draw_detections(frame, self._ppe_detections_cache)

                # 2) PPE 상태 오버레이
                frame = self.ppe_visualizer.draw_ppe_status_overlay(
                    frame, self._ppe_status_cache, enabled_items, item_names, 'top_left'
                )

                # 3) 안전률 표시 (좌측 상단, PPE 상태 박스 오른쪽)
                required_ppe = [k for k, v in enabled_items.items() if v]
                h, w = frame.shape[:2]
                # PPE 상태 박스 옆에 배치 (좌측 상단 영역, 위치 조정)
                frame = self.ppe_visualizer.draw_safety_rate(
                    frame, self._ppe_status_cache, required_ppe, (260, 10)
                )

                # 4) 얼굴 인식 박스 그리기 (ID 추적 정보 포함)
                if self._face_results_cache and self.face_recognition_done:
                    frame = self._draw_face_boxes(frame, self._face_results_cache)

                return frame

            # 기존 방식 (fallback)
            enabled_items = []
            if self.ppe_helmet_enabled:
                enabled_items.append("helmet")
            if self.ppe_vest_enabled:
                enabled_items.append("vest")
            if self.ppe_mask_enabled:
                enabled_items.append("mask")
            if self.ppe_glasses_enabled:
                enabled_items.append("glasses")
            if self.ppe_gloves_enabled:
                enabled_items.append("gloves")
            if self.ppe_boots_enabled:
                enabled_items.append("boots")

            if not enabled_items:
                return frame

            h, w = frame.shape[:2]
            box_height = 40 + len(enabled_items) * 30
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (250, box_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            frame = self._put_korean_text_on_frame(frame, "안전장구 상태", (15, 15), (255, 255, 255), 18)

            y_offset = 45

            if self.ppe_helmet_enabled:
                helmet_worn = self.ppe_status["helmet"]["worn"]
                helmet_color = self.ppe_status["helmet"]["color"]
                if helmet_worn:
                    helmet_text = f"✓ {self.ppe_helmet_name}: 착용"
                    if helmet_color:
                        helmet_text += f" ({helmet_color})"
                    text_color = (0, 255, 0)
                else:
                    helmet_text = f"✗ {self.ppe_helmet_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, helmet_text, (15, y_offset), text_color, 16)
                y_offset += 30

            if self.ppe_vest_enabled:
                vest_worn = self.ppe_status["vest"]["worn"]
                vest_color = self.ppe_status["vest"]["color"]
                if vest_worn:
                    vest_text = f"✓ {self.ppe_vest_name}: 착용"
                    if vest_color:
                        vest_text += f" ({vest_color})"
                    text_color = (0, 255, 0)
                else:
                    vest_text = f"✗ {self.ppe_vest_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, vest_text, (15, y_offset), text_color, 16)
                y_offset += 30

            if self.ppe_mask_enabled:
                mask_worn = self.ppe_status["mask"]["worn"]
                if mask_worn:
                    mask_text = f"✓ {self.ppe_mask_name}: 착용"
                    text_color = (0, 255, 0)
                else:
                    mask_text = f"✗ {self.ppe_mask_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, mask_text, (15, y_offset), text_color, 16)
                y_offset += 30

            if self.ppe_glasses_enabled:
                glasses_worn = self.ppe_status["glasses"]["worn"]
                if glasses_worn:
                    glasses_text = f"✓ {self.ppe_glasses_name}: 착용"
                    text_color = (0, 255, 0)
                else:
                    glasses_text = f"✗ {self.ppe_glasses_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, glasses_text, (15, y_offset), text_color, 16)
                y_offset += 30

            if self.ppe_gloves_enabled:
                gloves_worn = self.ppe_status["gloves"]["worn"]
                gloves_count = self.ppe_status["gloves"].get("count", 0)
                if gloves_worn:
                    gloves_text = f"✓ {self.ppe_gloves_name}: 착용"
                    if gloves_count > 0:
                        gloves_text += f" ({gloves_count}개)"
                    text_color = (0, 255, 0)
                else:
                    gloves_text = f"✗ {self.ppe_gloves_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, gloves_text, (15, y_offset), text_color, 16)
                y_offset += 30

            if self.ppe_boots_enabled:
                boots_worn = self.ppe_status["boots"]["worn"]
                if boots_worn:
                    boots_text = f"✓ {self.ppe_boots_name}: 착용"
                    text_color = (0, 255, 0)
                else:
                    boots_text = f"✗ {self.ppe_boots_name}: 미착용"
                    text_color = (0, 0, 255)
                frame = self._put_korean_text_on_frame(frame, boots_text, (15, y_offset), text_color, 16)

        except Exception as e:
            pass

        return frame

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
                frame = self._put_korean_text_on_frame(frame, text, (x1, y1 - 30), (0, 255, 0), 20)

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

    def _get_tracked_name_for_detection(self, detection):
        """detection에 매칭되는 추적 ID의 이름 반환"""
        if not hasattr(detection, 'track_id'):
            return None

        track_id = detection.track_id
        if track_id in self._tracked_persons:
            return self._tracked_persons[track_id].get('name', '')
        return None

    def _get_safety_equipment_info(self):
        """안전장구 착용 정보 수집"""
        safety_equipment = {
            "helmet": {"worn": False, "color": None},
            "vest": {"worn": False, "color": None},
            "mask": {"worn": False}
        }

        try:
            # safety_detector에서 마지막 감지 결과 가져오기
            if self.safety_detector is not None:
                # 마지막 프리뷰 프레임으로 안전장구 감지
                if self.last_preview_frame is not None:
                    results = self.safety_detector.detect_all(self.last_preview_frame)
                    if results:
                        # PPE 결과 파싱
                        ppe_results = results.get('ppe', {})

                        # 헬멧 정보
                        if ppe_results.get('helmet'):
                            safety_equipment["helmet"]["worn"] = True
                            safety_equipment["helmet"]["color"] = ppe_results.get('helmet_color')

                        # 조끼 정보
                        if ppe_results.get('vest'):
                            safety_equipment["vest"]["worn"] = True
                            safety_equipment["vest"]["color"] = ppe_results.get('vest_color')

                        # 마스크 정보
                        if ppe_results.get('mask'):
                            safety_equipment["mask"]["worn"] = True

                        print(f"서명 화면: 안전장구 정보 수집 완료 - {safety_equipment}")

        except Exception as e:
            print(f"서명 화면: 안전장구 정보 수집 실패 (무시): {e}")

        return safety_equipment

    def _cancel(self):
        """취소"""
        self._cleanup()

    def _cleanup(self):
        """정리"""
        # 카메라 업데이트 중지
        if self.camera_frame_id:
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after_cancel(self.camera_frame_id)
            except Exception:
                pass
            self.camera_frame_id = None

        # 화면 제거 (Frame)
        if self.dialog:
            try:
                self.dialog.destroy()
            except Exception:
                pass
            self.dialog = None
