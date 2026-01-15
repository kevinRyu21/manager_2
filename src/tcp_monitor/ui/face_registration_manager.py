"""
얼굴 등록 관리 UI

사진을 업로드하여 얼굴을 학습시키고 관리하는 기능을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import platform
import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Optional, List
from datetime import datetime
import tempfile

# InsightFace 라이브러리 (v1.9.5 - dlib 대신 사용)
# safety_detector의 공유 인스턴스 사용 (여러 번 로드 방지)
def _get_insightface_app():
    """InsightFace 앱을 공유 인스턴스에서 반환"""
    try:
        from ..sensor.safety_detector import get_shared_insightface_app
        return get_shared_insightface_app()
    except ImportError:
        # 직접 로드 (fallback)
        try:
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            app.prepare(ctx_id=0, det_size=(640, 640))
            print("[얼굴 등록] InsightFace 모델 로드 성공 (fallback)")
            return app
        except Exception as e:
            print(f"[경고] InsightFace 라이브러리 로드 실패: {e}")
            return None


def detect_faces_insightface(image_path_or_array):
    """
    InsightFace를 사용하여 얼굴을 감지하고 임베딩을 추출합니다.

    Args:
        image_path_or_array: 이미지 파일 경로 또는 numpy 배열 (BGR)

    Returns:
        tuple: (face_locations, face_embeddings)
            - face_locations: [(top, right, bottom, left), ...] 형식
            - face_embeddings: [512-dim numpy array, ...] 형식
    """
    # 지연 초기화된 InsightFace 앱 가져오기
    app = _get_insightface_app()

    if app is None:
        return [], []

    try:
        # 이미지 로드
        if isinstance(image_path_or_array, str):
            img = cv2.imread(image_path_or_array)
            if img is None:
                return [], []
        else:
            img = image_path_or_array

        # BGR to RGB
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 얼굴 감지
        faces = app.get(rgb_img)

        if not faces:
            return [], []

        face_locations = []
        face_embeddings = []

        for face in faces:
            # bbox: [x1, y1, x2, y2]
            bbox = face.bbox.astype(int)
            # face_recognition 형식으로 변환: (top, right, bottom, left)
            top, right, bottom, left = bbox[1], bbox[2], bbox[3], bbox[0]
            face_locations.append((top, right, bottom, left))

            # 임베딩 (512-dim)
            face_embeddings.append(face.embedding)

        return face_locations, face_embeddings

    except Exception as e:
        print(f"[InsightFace] 얼굴 감지 오류: {e}")
        return [], []


# 플랫폼별 카메라 백엔드 import
from ..platform import CameraBackend

from ..sensor.face_database import FaceDatabase


class FaceRegistrationManager:
    """얼굴 등록 관리 대화상자"""
    
    def __init__(self, parent, app):
        """
        초기화
        
        Args:
            parent: 부모 위젯
            app: 메인 애플리케이션 객체
        """
        self.parent = parent
        self.app = app
        self.dialog = None
        try:
            self.face_db = FaceDatabase()
        except Exception as e:
            print(f"[얼굴 등록 관리] FaceDatabase 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
            raise
        self.current_image = None
        self.current_encodings = []
        self.current_face_locations = []
        self.selected_name = ""
        self.selected_face_index = 0  # 다중 얼굴 선택용
        
        # 카메라 관련 변수
        self.camera = None
        self.camera_active = False
        self.captured_frame = None
        
        # 임시 저장 관련 변수 (등록하기 전까지 보관)
        self.temp_face_data = None  # {'name': str, 'employee_id': str, 'department': str, 'encodings': list, 'photo_path': str}
        
    def show(self):
        """얼굴 등록 관리 대화상자 표시"""
        # InsightFace 사용 가능 여부 확인 (v1.9.5 - 지연 초기화 사용)
        app = _get_insightface_app()

        if app is None:
            messagebox.showerror(
                "라이브러리 오류",
                "InsightFace 라이브러리가 설치되지 않았습니다.\n\n"
                "설치 방법:\npip install insightface onnxruntime",
                parent=self.parent
            )
            return
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("얼굴 등록 관리")
        self.dialog.geometry("900x1030")  # 높이 추가 10% 확장 (935 -> 1030)
        self.dialog.resizable(True, True)
        
        try:
            self.dialog.attributes("-topmost", True)
            self.dialog.lift()
            self.dialog.focus_force()
        except Exception:
            pass
        
        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (1030 // 2)
        self.dialog.geometry(f"900x1030+{x}+{y}")  # 높이 추가 10% 확장 (935 -> 1030)
        
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 다이얼로그 종료 시 카메라 중지
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_widgets()
        self._load_face_list()
        
    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 상단: 제목
        title_label = tk.Label(
            main_frame,
            text="얼굴 등록 관리",
            font=("Pretendard", 16, "bold"),
            fg="#2C3E50"
        )
        title_label.pack(pady=(0, 20))
        
        # 좌우 분할
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)
        
        # 왼쪽: 등록된 얼굴 목록
        left_frame = ttk.Frame(paned, width=300)
        paned.add(left_frame, weight=1)
        
        # 얼굴 목록
        list_label = tk.Label(
            left_frame,
            text="등록된 얼굴 목록",
            font=("Pretendard", 12, "bold"),
            fg="#34495E"
        )
        list_label.pack(pady=(0, 10))
        
        # 리스트박스와 스크롤바
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.face_listbox = tk.Listbox(
            list_frame,
            font=("Pretendard", 11),
            yscrollcommand=scrollbar.set,
            selectmode="single"
        )
        self.face_listbox.pack(side="left", fill="both", expand=True)
        self.face_listbox.bind("<<ListboxSelect>>", self._on_face_selected)
        
        scrollbar.config(command=self.face_listbox.yview)
        
        # 삭제 버튼
        delete_btn = tk.Button(
            left_frame,
            text="선택 항목 삭제",
            command=self._delete_face,
            bg="#E74C3C",
            fg="#FFFFFF",
            font=("Pretendard", 10, "bold"),
            width=20
        )
        delete_btn.pack(pady=10)
        
        # 오른쪽: 얼굴 등록 영역
        right_frame = ttk.Frame(paned, width=600)
        paned.add(right_frame, weight=2)
        
        # 이름 입력
        name_frame = ttk.LabelFrame(right_frame, text="이름 정보", padding="10")
        name_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(name_frame, text="이름:", font=("Pretendard", 10)).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = tk.Entry(name_frame, font=("Pretendard", 11), width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        tk.Label(name_frame, text="사원번호:", font=("Pretendard", 10)).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.employee_id_entry = tk.Entry(name_frame, font=("Pretendard", 11), width=30)
        self.employee_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        tk.Label(name_frame, text="부서:", font=("Pretendard", 10)).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.department_entry = tk.Entry(name_frame, font=("Pretendard", 11), width=30)
        self.department_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        name_frame.columnconfigure(1, weight=1)
        
        # 사진 업로드 영역 (expand=False로 변경하여 하단 버튼 영역 확보)
        photo_frame = ttk.LabelFrame(right_frame, text="사진 등록", padding="10")
        photo_frame.pack(fill="x", pady=(0, 10))
        
        # 이미지 표시 영역 (고정 픽셀 크기)
        # 고정 크기: 480x360 (4:3 비율)
        self.FIXED_IMAGE_WIDTH = 480
        self.FIXED_IMAGE_HEIGHT = 360

        image_container = ttk.Frame(photo_frame)
        image_container.pack(pady=10)

        # 고정 크기 프레임 (크기 변경 방지)
        image_frame = tk.Frame(
            image_container,
            width=self.FIXED_IMAGE_WIDTH,
            height=self.FIXED_IMAGE_HEIGHT,
            bg="#2C3E50"
        )
        image_frame.pack_propagate(False)  # 내부 위젯에 의해 크기 변경 방지
        image_frame.pack()

        self.image_label = tk.Label(
            image_frame,
            text="카메라를 시작하여 사진을 촬영하세요",
            bg="#2C3E50",
            fg="#FFFFFF",
            font=("Pretendard", 11)
        )
        self.image_label.pack(fill="both", expand=True)
        
        # 버튼 프레임
        button_row = ttk.Frame(photo_frame)
        button_row.pack(pady=10)
        
        # 카메라 시작/중지 버튼
        self.camera_start_btn = tk.Button(
            button_row,
            text="📹 실시간 시작",
            command=self._toggle_camera,
            bg="#9B59B6",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=18,
            height=2
        )
        self.camera_start_btn.pack(side="left", padx=5)
        
        # 사진 촬영/재촬영 버튼 (항상 표시)
        self.capture_btn = tk.Button(
            button_row,
            text="📷 사진 촬영",
            command=self._capture_photo,
            bg="#E74C3C",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=18,
            height=2,
            state="disabled"
        )
        self.capture_btn.pack(side="left", padx=5)  # 항상 표시
        
        # 재촬영 버튼 (항상 표시)
        self.retake_btn = tk.Button(
            button_row,
            text="🔄 재촬영",
            command=self._retake_photo,
            bg="#F39C12",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=18,
            height=2,
            state="disabled"
        )
        self.retake_btn.pack(side="left", padx=5)  # 항상 표시

        # 두 번째 버튼 행 (사진 업로드)
        button_row2 = ttk.Frame(photo_frame)
        button_row2.pack(pady=5)

        # 사진 업로드 버튼
        self.upload_btn = tk.Button(
            button_row2,
            text="📁 사진 업로드",
            command=self._upload_photo,
            bg="#3498DB",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=18,
            height=2
        )
        self.upload_btn.pack(side="left", padx=5)

        # 일괄 업로드 버튼
        self.batch_upload_btn = tk.Button(
            button_row2,
            text="📂 일괄 업로드",
            command=self._batch_upload,
            bg="#2980B9",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=18,
            height=2
        )
        self.batch_upload_btn.pack(side="left", padx=5)

        # 크롭 버튼 (사진 로드 후 활성화)
        self.crop_btn = tk.Button(
            button_row2,
            text="✂️ 크롭",
            command=self._show_crop_dialog,
            bg="#E67E22",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=10,
            height=2,
            state="disabled"
        )
        self.crop_btn.pack(side="left", padx=5)

        # 하단: 등록/수정 버튼
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill="x", pady=10)

        register_btn = tk.Button(
            button_frame,
            text="✓ 등록하기",
            command=self._register_face,
            bg="#27AE60",
            fg="#FFFFFF",
            font=("Pretendard", 12, "bold"),
            width=12,
            height=2
        )
        register_btn.pack(side="left", padx=5)

        # 정보 수정 버튼 (선택된 사람의 정보 업데이트)
        self.update_btn = tk.Button(
            button_frame,
            text="✎ 정보 수정",
            command=self._update_face_info,
            bg="#3498DB",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=12,
            height=2,
            state="disabled"
        )
        self.update_btn.pack(side="left", padx=5)

        close_btn = tk.Button(
            button_frame,
            text="닫기",
            command=self._on_close,
            bg="#95A5A6",
            fg="#FFFFFF",
            font=("Pretendard", 11, "bold"),
            width=12,
            height=2
        )
        close_btn.pack(side="right", padx=5)
        
    def _load_face_list(self):
        """등록된 얼굴 목록 로드"""
        self.face_listbox.delete(0, tk.END)
        
        faces = self.face_db.get_all_faces()
        for face in faces:
            name = face['name']
            if face['employee_id']:
                name += f" ({face['employee_id']})"
            if face['department']:
                name += f" - {face['department']}"
            self.face_listbox.insert(tk.END, name)
            
            # 딕셔너리로 저장 (나중에 조회용)
            if not hasattr(self.face_listbox, '_face_data'):
                self.face_listbox._face_data = []
            self.face_listbox._face_data.append(face)
    
    def _on_face_selected(self, event):
        """얼굴 선택 이벤트 - 등록된 사람 정보 및 이미지 표시"""
        selection = self.face_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if hasattr(self.face_listbox, '_face_data') and idx < len(self.face_listbox._face_data):
            face = self.face_listbox._face_data[idx]

            # 현재 선택된 얼굴 정보 저장 (편집용)
            self._selected_face_id = face['id']
            self._selected_face_data = face

            # 입력 필드에 정보 표시
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, face['name'])
            self.employee_id_entry.delete(0, tk.END)
            if face['employee_id']:
                self.employee_id_entry.insert(0, face['employee_id'])
            self.department_entry.delete(0, tk.END)
            if face['department']:
                self.department_entry.insert(0, face['department'])

            # 등록된 사진 표시 (고정 크기 영역에)
            if face['photo_path'] and os.path.exists(face['photo_path']):
                self._display_image(face['photo_path'])
                self.current_image = face['photo_path']

                # 카메라 중지 (이미지 보기 모드)
                if self.camera_active:
                    self._stop_camera()
                    self.camera_start_btn.config(text="📹 실시간 시작")

                # 편집/크롭 버튼 활성화
                self.crop_btn.config(state="normal")
                self.retake_btn.config(state="normal")  # 새 사진으로 교체 가능
            else:
                # 사진 없음
                self.image_label.config(
                    image="",
                    text="등록된 사진이 없습니다\n새 사진을 촬영하세요"
                )
                self.image_label.image = None
                self.current_image = None
                self.crop_btn.config(state="disabled")

            # 정보 수정 버튼 활성화
            self.update_btn.config(state="normal")
    
    def _upload_photo(self):
        """사진 업로드 (카메라 촬영 대신 사용) - face_db 디렉토리로 복사"""
        try:
            # 카메라가 실행 중이면 중지
            if self.camera_active:
                self._stop_camera()
                self.camera_start_btn.config(text="📹 실시간 시작")

            # 다이얼로그를 최상위로 올려서 파일 다이얼로그가 앞에 표시되도록
            self.dialog.attributes("-topmost", True)
            self.dialog.update()

            file_path = filedialog.askopenfilename(
                parent=self.dialog,
                title="얼굴 사진 선택",
                filetypes=[
                    ("이미지 파일", "*.jpg *.jpeg *.png *.bmp"),
                    ("JPEG 파일", "*.jpg *.jpeg"),
                    ("PNG 파일", "*.png"),
                    ("모든 파일", "*.*")
                ]
            )

            # 최상위 속성 해제
            self.dialog.attributes("-topmost", False)
            
            if file_path:
                # 파일 존재 확인
                if not os.path.exists(file_path):
                    messagebox.showerror("오류", "선택한 파일을 찾을 수 없습니다.", parent=self.dialog)
                    return
                
                # 파일 크기 확인 (10MB 제한)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                if file_size > 10:
                    if not messagebox.askyesno(
                        "파일 크기 경고",
                        f"파일 크기가 {file_size:.1f}MB입니다.\n"
                        "처리 시간이 오래 걸릴 수 있습니다.\n\n"
                        "계속하시겠습니까?",
                        parent=self.dialog
                    ):
                        return
                
                # face_db 디렉토리 경로 가져오기
                face_db_dir = os.path.dirname(self.face_db.db_path)
                
                # temp_photos 디렉토리 생성 (임시 저장용)
                temp_photos_dir = os.path.join(face_db_dir, 'temp_photos')
                os.makedirs(temp_photos_dir, exist_ok=True)
                
                # 파일을 face_db/temp_photos로 복사
                import shutil
                from datetime import datetime
                file_ext = os.path.splitext(file_path)[1]  # 확장자
                temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
                temp_file_path = os.path.join(temp_photos_dir, temp_filename)
                
                try:
                    shutil.copy2(file_path, temp_file_path)
                    print(f"[얼굴 등록 관리] 사진이 임시 저장되었습니다: {temp_file_path}")
                except Exception as e:
                    messagebox.showerror("오류", f"파일 복사 실패: {str(e)}", parent=self.dialog)
                    print(f"[얼굴 등록 관리] 파일 복사 오류: {e}")
                    return
                
                # 이미지 처리 (임시 저장된 파일 경로 사용, DB 저장은 하지 않음)
                print(f"[얼굴 등록 관리] _process_image 호출 시작: {temp_file_path}")
                self._process_image(temp_file_path, save_to_db=False)
                print(f"[얼굴 등록 관리] _process_image 호출 완료")

                # 사진 업로드 후 버튼 상태 업데이트
                self.capture_btn.config(state="disabled")
                self.retake_btn.config(state="normal")  # 재촬영 버튼 활성화

        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"파일 업로드 오류: {str(e)}", parent=self.dialog)
            print(f"[얼굴 등록 관리] 업로드 오류:\n{traceback.format_exc()}")
    
    def _batch_upload(self):
        """CSV 파일 기반 일괄 등록

        CSV 파일 형식:
        이름,사원번호,부서,사진경로
        홍길동,EMP001,개발팀,/path/to/photo1.jpg
        김철수,EMP002,영업팀,/path/to/photo2.jpg
        """
        try:
            # 다이얼로그를 최상위로 올려서 파일 다이얼로그가 앞에 표시되도록
            self.dialog.attributes("-topmost", True)
            self.dialog.update()

            csv_path = filedialog.askopenfilename(
                parent=self.dialog,
                title="CSV 파일 선택 (이름,사원번호,부서,사진경로)",
                filetypes=[
                    ("CSV 파일", "*.csv"),
                    ("모든 파일", "*.*")
                ]
            )

            # 최상위 속성 해제
            self.dialog.attributes("-topmost", False)

            if not csv_path:
                return

            # CSV 파일 파싱
            import csv
            records = []
            csv_dir = os.path.dirname(csv_path)  # CSV 파일이 있는 디렉토리

            try:
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 필수 필드 확인
                        name = row.get('이름', '').strip()
                        if not name:
                            continue

                        photo_path = row.get('사진경로', '').strip()
                        if not photo_path:
                            continue

                        # 상대 경로인 경우 CSV 파일 기준으로 변환
                        if not os.path.isabs(photo_path):
                            photo_path = os.path.join(csv_dir, photo_path)

                        records.append({
                            'name': name,
                            'employee_id': row.get('사원번호', '').strip() or None,
                            'department': row.get('부서', '').strip() or None,
                            'photo_path': photo_path
                        })
            except UnicodeDecodeError:
                # EUC-KR로 재시도
                with open(csv_path, 'r', encoding='euc-kr') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get('이름', '').strip()
                        if not name:
                            continue

                        photo_path = row.get('사진경로', '').strip()
                        if not photo_path:
                            continue

                        if not os.path.isabs(photo_path):
                            photo_path = os.path.join(csv_dir, photo_path)

                        records.append({
                            'name': name,
                            'employee_id': row.get('사원번호', '').strip() or None,
                            'department': row.get('부서', '').strip() or None,
                            'photo_path': photo_path
                        })

            if not records:
                messagebox.showwarning(
                    "CSV 오류",
                    "CSV 파일에서 유효한 데이터를 찾을 수 없습니다.\n\n"
                    "CSV 파일 형식:\n"
                    "이름,사원번호,부서,사진경로\n"
                    "홍길동,EMP001,개발팀,photo1.jpg",
                    parent=self.dialog
                )
                return

            # 일괄 처리 대화상자
            batch_dialog = tk.Toplevel(self.dialog)
            batch_dialog.title("CSV 일괄 등록")
            batch_dialog.geometry("600x500")
            batch_dialog.transient(self.dialog)
            batch_dialog.grab_set()

            # 중앙 배치
            batch_dialog.update_idletasks()
            x = (batch_dialog.winfo_screenwidth() // 2) - (600 // 2)
            y = (batch_dialog.winfo_screenheight() // 2) - (500 // 2)
            batch_dialog.geometry(f"+{x}+{y}")

            # CSV 정보 표시
            info_frame = ttk.LabelFrame(batch_dialog, text="CSV 파일 정보", padding="10")
            info_frame.pack(fill="x", padx=10, pady=10)

            tk.Label(info_frame, text=f"파일: {os.path.basename(csv_path)}",
                    font=("Pretendard", 10)).pack(anchor="w")
            tk.Label(info_frame, text=f"등록 대상: {len(records)}명",
                    font=("Pretendard", 10, "bold")).pack(anchor="w")

            # 진행 상황 표시
            progress_frame = ttk.LabelFrame(batch_dialog, text="진행 상황", padding="10")
            progress_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # 텍스트와 스크롤바
            text_frame = ttk.Frame(progress_frame)
            text_frame.pack(fill="both", expand=True)

            progress_text = tk.Text(text_frame, height=15, font=("Pretendard", 9), wrap=tk.WORD)
            progress_scrollbar = ttk.Scrollbar(text_frame, command=progress_text.yview)
            progress_text.config(yscrollcommand=progress_scrollbar.set)

            progress_text.pack(side="left", fill="both", expand=True)
            progress_scrollbar.pack(side="right", fill="y")

            # 미리보기 출력
            progress_text.insert(tk.END, "=== 등록 대상 미리보기 ===\n\n")
            for i, rec in enumerate(records[:10], 1):
                progress_text.insert(tk.END, f"{i}. {rec['name']}")
                if rec['employee_id']:
                    progress_text.insert(tk.END, f" ({rec['employee_id']})")
                if rec['department']:
                    progress_text.insert(tk.END, f" - {rec['department']}")
                progress_text.insert(tk.END, f"\n   사진: {os.path.basename(rec['photo_path'])}\n")
            if len(records) > 10:
                progress_text.insert(tk.END, f"\n... 외 {len(records) - 10}명\n")
            progress_text.insert(tk.END, "\n[처리 시작] 버튼을 클릭하여 등록을 시작하세요.\n")

            def process_csv_batch():
                process_btn.config(state="disabled")
                progress_text.delete("1.0", tk.END)

                total = len(records)
                success_count = 0
                fail_count = 0

                progress_text.insert(tk.END, f"총 {total}명의 얼굴을 등록합니다...\n\n")
                batch_dialog.update()

                for i, rec in enumerate(records, 1):
                    try:
                        name = rec['name']
                        photo_path = rec['photo_path']

                        progress_text.insert(tk.END, f"[{i}/{total}] {name}: {os.path.basename(photo_path)}...\n")
                        batch_dialog.update()

                        # 파일 존재 확인
                        if not os.path.exists(photo_path):
                            progress_text.insert(tk.END, f"  → 파일 없음\n")
                            fail_count += 1
                            continue

                        # 이미지 처리 (InsightFace 사용)
                        face_locations, face_encodings = detect_faces_insightface(photo_path)

                        if not face_locations:
                            progress_text.insert(tk.END, f"  → 얼굴 미검출\n")
                            fail_count += 1
                            continue
                        if not face_encodings:
                            progress_text.insert(tk.END, f"  → 인코딩 실패\n")
                            fail_count += 1
                            continue

                        # DB에 등록
                        registered = 0
                        for encoding in face_encodings:
                            if np.isnan(encoding).any() or np.isinf(encoding).any():
                                continue
                            try:
                                self.face_db.add_face(
                                    name=name,
                                    encoding=encoding,
                                    employee_id=rec['employee_id'],
                                    department=rec['department'],
                                    photo_path=photo_path
                                )
                                registered += 1
                            except Exception as e:
                                progress_text.insert(tk.END, f"  → 등록 오류: {e}\n")

                        if registered > 0:
                            progress_text.insert(tk.END, f"  → 성공 ({registered}개 얼굴)\n")
                            success_count += 1
                        else:
                            progress_text.insert(tk.END, f"  → 실패\n")
                            fail_count += 1

                        progress_text.see(tk.END)
                        batch_dialog.update()

                    except Exception as e:
                        progress_text.insert(tk.END, f"  → 오류: {str(e)}\n")
                        fail_count += 1
                        import traceback
                        print(f"[CSV 일괄 등록] {rec['name']} 오류:\n{traceback.format_exc()}")

                progress_text.insert(tk.END, f"\n{'='*40}\n")
                progress_text.insert(tk.END, f"=== 등록 완료 ===\n")
                progress_text.insert(tk.END, f"성공: {success_count}명\n")
                progress_text.insert(tk.END, f"실패: {fail_count}명\n")
                progress_text.insert(tk.END, f"{'='*40}\n")
                progress_text.see(tk.END)

                # 닫기 버튼 활성화
                close_btn.config(state="normal")

                # 목록 새로고침
                self._load_face_list()

                messagebox.showinfo(
                    "등록 완료",
                    f"CSV 일괄 등록이 완료되었습니다.\n\n"
                    f"성공: {success_count}명\n"
                    f"실패: {fail_count}명",
                    parent=batch_dialog
                )

            # 버튼 프레임
            batch_button_frame = ttk.Frame(batch_dialog)
            batch_button_frame.pack(fill="x", padx=10, pady=10)

            process_btn = tk.Button(
                batch_button_frame,
                text="처리 시작",
                command=process_csv_batch,
                bg="#27AE60",
                fg="#FFFFFF",
                font=("Pretendard", 11, "bold"),
                width=15
            )
            process_btn.pack(side="left", padx=5)

            close_btn = tk.Button(
                batch_button_frame,
                text="닫기",
                command=batch_dialog.destroy,
                bg="#95A5A6",
                fg="#FFFFFF",
                font=("Pretendard", 11, "bold"),
                width=15
            )
            close_btn.pack(side="right", padx=5)

        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"CSV 일괄 업로드 오류: {str(e)}", parent=self.dialog)
            print(f"[얼굴 등록 관리] CSV 일괄 업로드 오류:\n{traceback.format_exc()}")
    
    def _toggle_camera(self):
        """카메라 시작/중지 토글"""
        if self.camera_active:
            # 카메라 중지
            self._stop_camera()
            self.camera_start_btn.config(text="📹 실시간 시작")
            # 버튼은 표시 유지하되 비활성화
            self.capture_btn.config(state="disabled")
            self.retake_btn.config(state="disabled")
        else:
            # 카메라 시작
            self._start_camera()
    
    def _start_camera(self):
        """카메라 시작 (실시간 화면 표시)"""
        if self.camera_active:
            return
        
        try:
            # 플랫폼별 카메라 백엔드 사용
            camera_backend = CameraBackend()
            
            # 카메라 인덱스 찾기
            camera_index = None
            for i in range(5):  # 0~4까지 카메라 인덱스 확인
                try:
                    backend = camera_backend.get_backend()
                    test_cap = cv2.VideoCapture(i, backend)
                    
                    if test_cap.isOpened():
                        ret, frame = test_cap.read()
                        if ret and frame is not None:
                            camera_index = i
                            test_cap.release()
                            break
                        test_cap.release()
                except:
                    continue
            
            if camera_index is None:
                messagebox.showerror("오류", "카메라를 찾을 수 없습니다.\n카메라가 연결되어 있는지 확인하세요.", parent=self.dialog)
                return
            
            # 플랫폼별 백엔드로 카메라 열기
            backend = camera_backend.get_backend()
            self.camera = cv2.VideoCapture(camera_index, backend)
            
            if not self.camera.isOpened():
                messagebox.showerror("오류", "카메라를 열 수 없습니다.", parent=self.dialog)
                return
            
            self.camera_active = True
            self.captured_frame = None
            
            # 버튼 상태 변경
            self.camera_start_btn.config(text="📹 실시간 중지")
            self.capture_btn.config(state="normal", text="📷 사진 촬영")
            self.retake_btn.config(state="disabled")  # 버튼은 표시 유지
            
            # 실시간 화면 업데이트 시작
            self._update_camera_frame()
            
        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"카메라 오류: {e}", parent=self.dialog)
            print(f"[얼굴 등록 관리] 카메라 시작 오류:\n{traceback.format_exc()}")
            self.camera_active = False
    
    def _update_camera_frame(self):
        """카메라 프레임 업데이트 (실시간 화면, 원본 크기 유지)"""
        if not self.camera_active or self.camera is None:
            return

        try:
            ret, frame = self.camera.read()
            if ret and frame is not None:
                # 원본 프레임 저장 (촬영용, 반전 전)
                self.captured_frame = frame.copy()

                # 화면 반전 설정 읽기 (환경설정에서 저장된 값 사용)
                should_flip = True  # 기본값
                if hasattr(self.app, 'cfg') and hasattr(self.app.cfg, 'camera'):
                    should_flip = self.app.cfg.camera.get("flip_horizontal", True)

                # 화면 표시용 프레임 (반전 적용)
                display_frame = frame.copy()
                if should_flip:
                    display_frame = cv2.flip(display_frame, 1)

                # RGB 변환
                frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                
                # 원본 크기 유지하되, 표시 영역에 맞게 비율 조정만
                # Label의 고정 크기(60x20 문자 단위)에 맞춰 실제 픽셀 크기 계산
                # 대략 384x240 픽셀 정도로 표시 (20% 감소: 480*0.8=384, 300*0.8=240)
                max_width = 384
                max_height = 240
                
                height, width = frame_rgb.shape[:2]
                aspect_ratio = width / height
                
                if width > max_width or height > max_height:
                    if aspect_ratio > 1:
                        # 가로가 더 긴 경우
                        display_width = max_width
                        display_height = int(max_width / aspect_ratio)
                    else:
                        # 세로가 더 긴 경우
                        display_height = max_height
                        display_width = int(max_height * aspect_ratio)
                    
                    frame_rgb = cv2.resize(frame_rgb, (display_width, display_height))
                else:
                    display_width = width
                    display_height = height
                
                # PIL Image로 변환
                img = Image.fromarray(frame_rgb)
                img_tk = ImageTk.PhotoImage(image=img)
                
                self.image_label.config(image=img_tk, text="", width=display_width, height=display_height)
                self.image_label.image = img_tk  # 참조 유지

                # 다음 프레임으로 계속 업데이트
                self.dialog.after(30, self._update_camera_frame)
            else:
                # 프레임 읽기 실패 시 카메라 중지
                self._stop_camera()
        except Exception as e:
            print(f"[얼굴 등록 관리] 카메라 프레임 업데이트 오류: {e}")
            self._stop_camera()
    
    def _capture_photo(self):
        """사진 촬영 (face_db 디렉토리로 임시 저장)"""
        if not self.camera_active or self.captured_frame is None:
            messagebox.showwarning("경고", "카메라가 실행 중이 아닙니다.", parent=self.dialog)
            return
        
        try:
            from PIL import Image as PILImage
            
            # face_db 디렉토리 경로 가져오기
            face_db_dir = os.path.dirname(self.face_db.db_path)
            
            # temp_photos 디렉토리 생성 (임시 저장용)
            temp_photos_dir = os.path.join(face_db_dir, 'temp_photos')
            os.makedirs(temp_photos_dir, exist_ok=True)
            
            # face_db/temp_photos에 저장 (PIL로 RGB 형식으로 저장)
            temp_filename = f"temp_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            temp_path = os.path.join(temp_photos_dir, temp_filename)
            
            # OpenCV는 BGR 형식이므로 RGB로 변환 후 PIL로 저장
            frame_rgb = cv2.cvtColor(self.captured_frame, cv2.COLOR_BGR2RGB)
            pil_image = PILImage.fromarray(frame_rgb)
            pil_image.save(temp_path, 'JPEG', quality=95)
            
            print(f"[얼굴 등록 관리] 촬영 사진이 임시 저장되었습니다 (RGB 형식): {temp_path}")
            
            # 카메라 중지
            self._stop_camera()
            
            # 이미지 처리 및 표시 (DB 저장은 하지 않음)
            self._process_image(temp_path, save_to_db=False)
            
            # 버튼 상태 변경: 사진 촬영 버튼이 재촬영으로 변경
            self.capture_btn.config(text="🔄 재촬영", command=self._retake_photo_from_capture, state="normal")
            # 별도 재촬영 버튼도 활성화
            self.retake_btn.config(state="normal")
            self.camera_start_btn.config(text="📹 실시간 시작")
            
        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"사진 촬영 오류: {e}", parent=self.dialog)
            print(f"[얼굴 등록 관리] 사진 촬영 오류:\n{traceback.format_exc()}")
    
    def _retake_photo_from_capture(self):
        """사진 촬영 버튼의 재촬영 (카메라 다시 시작)"""
        # 현재 이미지 초기화
        self.current_image = None
        self.current_encodings = []
        self.current_face_locations = []
        self.temp_face_data = None
        self.image_label.config(image="", text="카메라를 시작하거나 사진을 업로드하세요")
        
        # 버튼 상태 변경 (버튼은 표시 유지)
        self.capture_btn.config(text="📷 사진 촬영", command=self._capture_photo, state="normal")
        self.retake_btn.config(state="disabled")
        
        # 카메라 다시 시작
        self._start_camera()
    
    def _retake_photo(self):
        """재촬영 버튼 (카메라 다시 시작)"""
        # 현재 이미지 초기화
        self.current_image = None
        self.current_encodings = []
        self.current_face_locations = []
        self.temp_face_data = None
        self.image_label.config(image="", text="카메라를 시작하거나 사진을 업로드하세요")
        
        # 버튼 상태 변경 (버튼은 표시 유지)
        self.capture_btn.config(text="📷 사진 촬영", command=self._capture_photo, state="normal")
        self.retake_btn.config(state="disabled")
        
        # 카메라 다시 시작
        self._start_camera()
    
    def _stop_camera(self):
        """카메라 중지"""
        self.camera_active = False  # 먼저 플래그 설정하여 업데이트 루프 중지
        if self.camera is not None:
            try:
                self.camera.release()
            except:
                pass
        self.camera = None
        # 버튼 상태 초기화 (버튼은 표시 유지, 비활성화만)
        self.capture_btn.config(state="disabled", text="📷 사진 촬영", command=self._capture_photo)
        self.retake_btn.config(state="disabled")
    
    def _process_image(self, image_path: str, save_to_db: bool = False):
        """이미지 처리 및 얼굴 인코딩 추출 (v1.9.5 InsightFace 사용)

        Args:
            image_path: 이미지 파일 경로
            save_to_db: True이면 face_db에 임시 저장
        """
        print(f"[얼굴 등록 관리] _process_image 시작: {image_path}")
        try:
            # 파일 존재 확인
            if not os.path.exists(image_path):
                print(f"[얼굴 등록 관리] 파일이 존재하지 않음: {image_path}")
                messagebox.showerror("오류", f"파일이 존재하지 않습니다:\n{image_path}", parent=self.dialog)
                return

            # InsightFace로 얼굴 감지 및 인코딩 추출
            print(f"[얼굴 등록 관리] detect_faces_insightface 호출")
            face_locations, face_encodings = detect_faces_insightface(image_path)
            print(f"[얼굴 등록 관리] 얼굴 감지 결과: locations={len(face_locations)}, encodings={len(face_encodings)}")

            if not face_locations:
                # 얼굴이 감지되지 않아도 이미지는 표시
                print(f"[얼굴 등록 관리] 얼굴 미검출 - 이미지만 표시")
                self.current_image = image_path  # 크롭용으로 저장
                self._display_image(image_path, None)
                # 크롭 버튼 활성화
                self.crop_btn.config(state="normal")
                messagebox.showwarning(
                    "얼굴 미검출",
                    "사진에서 얼굴을 찾을 수 없습니다.\n\n"
                    "• 크롭 버튼을 눌러 얼굴 영역을 직접 선택하세요\n"
                    "• 또는 얼굴이 명확한 다른 사진을 사용하세요",
                    parent=self.dialog
                )
                return

            if not face_encodings:
                messagebox.showwarning(
                    "인코딩 실패",
                    "얼굴 인코딩을 추출할 수 없습니다.\n\n"
                    "얼굴이 명확하게 보이는 사진을 사용해주세요.",
                    parent=self.dialog
                )
                return

            # 유효한 인코딩만 필터링
            valid_encodings = []
            for encoding in face_encodings:
                if not (np.isnan(encoding).any() or np.isinf(encoding).any()):
                    valid_encodings.append(encoding)

            if not valid_encodings:
                messagebox.showerror(
                    "인코딩 오류",
                    "유효한 얼굴 인코딩이 없습니다.\n\n"
                    "다른 사진을 사용해주세요.",
                    parent=self.dialog
                )
                return

            # 모든 얼굴 저장 (다중 얼굴 지원)
            self.current_image = image_path
            self.current_encodings = valid_encodings
            self.current_face_locations = face_locations
            self.selected_face_index = 0  # 첫 번째 얼굴 선택

            # 이미지 표시
            print(f"[얼굴 등록 관리] _display_image 호출")
            self._display_image(image_path, face_locations)
            print(f"[얼굴 등록 관리] _display_image 완료")

            # 임시 데이터 저장 (등록하기 시 사용)
            self.temp_face_data = {
                'name': self.name_entry.get().strip() or None,
                'employee_id': self.employee_id_entry.get().strip() or None,
                'department': self.department_entry.get().strip() or None,
                'encodings': valid_encodings,
                'photo_path': image_path
            }

            # 사진 업로드인 경우 안내 메시지
            if save_to_db:
                messagebox.showinfo(
                    "사진 업로드 완료",
                    f"사진이 처리되었습니다.\n\n"
                    f"이름을 입력하고 등록하기 버튼을 클릭하여 최종 등록하세요.",
                    parent=self.dialog
                )

            # 버튼 상태 업데이트 (사진 업로드/촬영 후 재촬영 가능하도록)
            if not self.camera_active:
                self.capture_btn.config(state="disabled")
                self.retake_btn.config(state="normal")  # 재촬영 버튼은 활성화
                self.crop_btn.config(state="normal")  # 크롭 버튼 활성화

            # 다중 얼굴 처리 안내
            if len(valid_encodings) > 1:
                messagebox.showinfo(
                    "다중 얼굴 감지",
                    f"{len(valid_encodings)}개의 얼굴을 감지했습니다.\n\n"
                    "모든 얼굴이 등록되며, 각각 같은 이름으로 저장됩니다.\n"
                    "이름을 입력하고 등록하기 버튼을 클릭하세요.",
                    parent=self.dialog
                )
            else:
                if not save_to_db:
                    messagebox.showinfo(
                        "처리 완료",
                        "얼굴을 감지했습니다.\n"
                        "이름을 입력하고 등록하기 버튼을 클릭하세요.",
                        parent=self.dialog
                    )

        except Exception as e:
            import traceback
            error_msg = f"이미지 처리 오류: {str(e)}\n\n상세 정보는 콘솔을 확인하세요."
            messagebox.showerror("오류", error_msg, parent=self.dialog)
            print(f"[얼굴 등록 관리] 이미지 처리 오류:\n{traceback.format_exc()}")

    def _show_crop_dialog(self):
        """이미지 크롭 다이얼로그 표시"""
        if not self.current_image or not os.path.exists(self.current_image):
            messagebox.showwarning("경고", "크롭할 이미지가 없습니다.", parent=self.dialog)
            return

        try:
            # 원본 이미지 로드
            original_img = Image.open(self.current_image)
            orig_width, orig_height = original_img.size

            # 크롭 다이얼로그 생성
            crop_dialog = tk.Toplevel(self.dialog)
            crop_dialog.title("이미지 크롭 - 얼굴 영역 선택")
            crop_dialog.configure(bg="#2C3E50")
            crop_dialog.transient(self.dialog)
            crop_dialog.grab_set()

            # 화면 크기에 맞게 다이얼로그 크기 조정
            screen_width = crop_dialog.winfo_screenwidth()
            screen_height = crop_dialog.winfo_screenheight()

            # 이미지 표시 크기 계산 (최대 800x600)
            max_display_width = min(800, screen_width - 100)
            max_display_height = min(600, screen_height - 200)

            # 비율 유지하면서 크기 조정
            scale = min(max_display_width / orig_width, max_display_height / orig_height)
            display_width = int(orig_width * scale)
            display_height = int(orig_height * scale)

            # 다이얼로그 크기 설정
            dialog_width = display_width + 40
            dialog_height = display_height + 150
            x = (screen_width // 2) - (dialog_width // 2)
            y = (screen_height // 2) - (dialog_height // 2)
            crop_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

            # 최상위로 표시
            crop_dialog.attributes("-topmost", True)
            crop_dialog.lift()
            crop_dialog.focus_force()
            crop_dialog.after(100, lambda: crop_dialog.attributes("-topmost", False))

            # 안내 레이블
            info_label = tk.Label(
                crop_dialog,
                text="마우스로 드래그하여 크롭할 영역을 선택하세요",
                font=("Pretendard", 11, "bold"),
                bg="#2C3E50",
                fg="#FFFFFF"
            )
            info_label.pack(pady=10)

            # 캔버스 프레임
            canvas_frame = tk.Frame(crop_dialog, bg="#1A252F")
            canvas_frame.pack(padx=10, pady=5)

            # 캔버스 생성
            canvas = tk.Canvas(
                canvas_frame,
                width=display_width,
                height=display_height,
                bg="#1A252F",
                highlightthickness=2,
                highlightbackground="#3498DB"
            )
            canvas.pack()

            # 표시용 이미지 생성
            display_img = original_img.copy()
            display_img = display_img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            display_photo = ImageTk.PhotoImage(display_img)
            canvas.create_image(0, 0, anchor="nw", image=display_photo)
            canvas.image = display_photo  # 참조 유지

            # 선택 영역 변수
            selection = {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0, "rect_id": None}

            def on_mouse_down(event):
                """마우스 버튼 누름"""
                selection["start_x"] = event.x
                selection["start_y"] = event.y
                # 기존 사각형 제거
                if selection["rect_id"]:
                    canvas.delete(selection["rect_id"])
                    selection["rect_id"] = None

            def on_mouse_drag(event):
                """마우스 드래그"""
                # 기존 사각형 제거
                if selection["rect_id"]:
                    canvas.delete(selection["rect_id"])

                # 새 사각형 그리기
                selection["end_x"] = max(0, min(event.x, display_width))
                selection["end_y"] = max(0, min(event.y, display_height))

                selection["rect_id"] = canvas.create_rectangle(
                    selection["start_x"], selection["start_y"],
                    selection["end_x"], selection["end_y"],
                    outline="#E74C3C",
                    width=2,
                    dash=(5, 5)
                )

            def on_mouse_up(event):
                """마우스 버튼 놓음"""
                selection["end_x"] = max(0, min(event.x, display_width))
                selection["end_y"] = max(0, min(event.y, display_height))

                # 최종 사각형 그리기 (점선 → 실선)
                if selection["rect_id"]:
                    canvas.delete(selection["rect_id"])

                # 유효한 영역인지 확인
                width = abs(selection["end_x"] - selection["start_x"])
                height = abs(selection["end_y"] - selection["start_y"])

                if width > 20 and height > 20:
                    selection["rect_id"] = canvas.create_rectangle(
                        selection["start_x"], selection["start_y"],
                        selection["end_x"], selection["end_y"],
                        outline="#27AE60",
                        width=3
                    )
                    crop_btn.config(state="normal")
                    size_label.config(text=f"선택 영역: {width}x{height}px")
                else:
                    size_label.config(text="영역이 너무 작습니다 (최소 20x20)")
                    crop_btn.config(state="disabled")

            # 캔버스 이벤트 바인딩
            canvas.bind("<Button-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_drag)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)

            # 크기 정보 레이블
            size_label = tk.Label(
                crop_dialog,
                text="영역을 선택하세요",
                font=("Pretendard", 10),
                bg="#2C3E50",
                fg="#BDC3C7"
            )
            size_label.pack(pady=5)

            # 버튼 프레임
            btn_frame = tk.Frame(crop_dialog, bg="#2C3E50")
            btn_frame.pack(pady=10)

            def apply_crop():
                """크롭 적용"""
                # 좌표 정규화 (start < end)
                x1 = min(selection["start_x"], selection["end_x"])
                y1 = min(selection["start_y"], selection["end_y"])
                x2 = max(selection["start_x"], selection["end_x"])
                y2 = max(selection["start_y"], selection["end_y"])

                # 표시 좌표를 원본 좌표로 변환
                orig_x1 = int(x1 / scale)
                orig_y1 = int(y1 / scale)
                orig_x2 = int(x2 / scale)
                orig_y2 = int(y2 / scale)

                # 원본 이미지에서 크롭
                cropped = original_img.crop((orig_x1, orig_y1, orig_x2, orig_y2))

                # 크롭된 이미지 저장
                face_db_dir = os.path.dirname(self.face_db.db_path)
                temp_photos_dir = os.path.join(face_db_dir, 'temp_photos')
                os.makedirs(temp_photos_dir, exist_ok=True)

                from datetime import datetime
                cropped_filename = f"cropped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cropped_path = os.path.join(temp_photos_dir, cropped_filename)
                cropped.save(cropped_path, 'JPEG', quality=95)

                print(f"[얼굴 등록 관리] 크롭된 이미지 저장: {cropped_path}")

                # 다이얼로그 닫기
                crop_dialog.destroy()

                # 크롭된 이미지로 다시 처리
                self._process_image(cropped_path, save_to_db=False)

            crop_btn = tk.Button(
                btn_frame,
                text="✓ 크롭 적용",
                command=apply_crop,
                bg="#27AE60",
                fg="#FFFFFF",
                font=("Pretendard", 11, "bold"),
                width=12,
                height=1,
                state="disabled"
            )
            crop_btn.pack(side="left", padx=10)

            cancel_btn = tk.Button(
                btn_frame,
                text="취소",
                command=crop_dialog.destroy,
                bg="#95A5A6",
                fg="#FFFFFF",
                font=("Pretendard", 11, "bold"),
                width=10,
                height=1
            )
            cancel_btn.pack(side="left", padx=10)

        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"크롭 다이얼로그 오류: {e}", parent=self.dialog)
            print(f"[얼굴 등록 관리] 크롭 다이얼로그 오류:\n{traceback.format_exc()}")

    def _display_image(self, image_path: str, face_locations: List = None):
        """이미지 표시 (고정 크기: FIXED_IMAGE_WIDTH x FIXED_IMAGE_HEIGHT)"""
        try:
            # PIL Image 로드
            img = Image.open(image_path)
            original_width, original_height = img.size

            # 고정 크기에 맞게 비율 유지하면서 조정
            target_width = self.FIXED_IMAGE_WIDTH
            target_height = self.FIXED_IMAGE_HEIGHT

            # 비율 계산
            width_ratio = target_width / original_width
            height_ratio = target_height / original_height
            scale_ratio = min(width_ratio, height_ratio)

            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

            # 이미지 리사이즈
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 얼굴 위치에 박스 그리기 (있는 경우)
            if face_locations:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img_resized)
                for (top, right, bottom, left) in face_locations:
                    # 원본 이미지 기준 좌표를 리사이즈된 이미지 좌표로 변환
                    left_scaled = int(left * scale_ratio)
                    top_scaled = int(top * scale_ratio)
                    right_scaled = int(right * scale_ratio)
                    bottom_scaled = int(bottom * scale_ratio)

                    draw.rectangle(
                        [(left_scaled, top_scaled), (right_scaled, bottom_scaled)],
                        outline="red",
                        width=3
                    )

            # PhotoImage로 변환
            img_tk = ImageTk.PhotoImage(img_resized)
            self.image_label.config(image=img_tk, text="")
            self.image_label.image = img_tk  # 참조 유지

        except Exception as e:
            messagebox.showerror("오류", f"이미지 표시 오류: {e}", parent=self.dialog)
    
    def _register_face(self):
        """얼굴 최종 등록 (DB에 저장)"""
        print(f"[얼굴 등록 관리] 등록하기 버튼 클릭됨")
        print(f"  - current_encodings: {len(self.current_encodings) if self.current_encodings else 0}개")
        print(f"  - temp_face_data: {self.temp_face_data is not None}")
        
        if not self.current_encodings and not self.temp_face_data:
            messagebox.showwarning(
                "사진 없음",
                "먼저 사진을 촬영하세요.",
                parent=self.dialog
            )
            return
        
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(
                "이름 필요",
                "이름을 입력하세요.",
                parent=self.dialog
            )
            return
        
        try:
            employee_id = self.employee_id_entry.get().strip() or None
            department = self.department_entry.get().strip() or None
            
            print(f"[얼굴 등록 관리] 등록 정보:")
            print(f"  - 이름: {name}")
            print(f"  - 사원번호: {employee_id}")
            print(f"  - 부서: {department}")
            
            # 임시 저장된 데이터가 있으면 사용, 없으면 현재 인코딩 사용
            if self.temp_face_data:
                encodings_to_register = self.temp_face_data.get('encodings', [])
                photo_path = self.temp_face_data.get('photo_path', None)
                print(f"[얼굴 등록 관리] temp_face_data 사용: encodings={len(encodings_to_register)}개, photo_path={photo_path}")
            else:
                encodings_to_register = self.current_encodings
                photo_path = self.current_image
                print(f"[얼굴 등록 관리] current_encodings 사용: {len(encodings_to_register)}개, photo_path={photo_path}")
            
            if not encodings_to_register or len(encodings_to_register) == 0:
                messagebox.showerror(
                    "등록 실패",
                    "등록할 얼굴 인코딩이 없습니다.\n\n"
                    "다시 사진을 촬영하세요.",
                    parent=self.dialog
                )
                return
            
            # 얼굴 품질 검증
            valid_encodings = []
            for i, encoding in enumerate(encodings_to_register):
                # 인코딩이 유효한지 확인 (NaN이나 무한대 값 체크)
                if np.isnan(encoding).any() or np.isinf(encoding).any():
                    print(f"[얼굴 등록 관리] 얼굴 {i+1}의 인코딩이 유효하지 않습니다. 건너뜁니다.")
                    continue
                valid_encodings.append(encoding)
            
            if not valid_encodings:
                messagebox.showerror(
                    "등록 실패",
                    "유효한 얼굴 인코딩이 없습니다.\n\n"
                    "다른 사진을 사용해주세요.",
                    parent=self.dialog
                )
                return
            
            # 최종 등록: 모든 유효한 얼굴 인코딩을 DB에 저장
            registered_count = 0
            for encoding in valid_encodings:
                try:
                    face_id = self.face_db.add_face(
                        name=name,
                        encoding=encoding,
                        employee_id=employee_id,
                        department=department,
                        photo_path=photo_path
                    )
                    registered_count += 1
                except Exception as e:
                    print(f"[얼굴 등록 관리] 얼굴 등록 중 오류: {e}")
                    import traceback
                    traceback.print_exc()
            
            if registered_count > 0:
                # 목록 실시간 업데이트 (등록 후 즉시 반영)
                self._load_face_list()
                
                messagebox.showinfo(
                    "등록 완료",
                    f"{name}님의 얼굴 {registered_count}개가 최종 등록되었습니다.",
                    parent=self.dialog
                )
                
                # 초기화
                self.current_image = None
                self.current_encodings = []
                self.current_face_locations = []
                self.temp_face_data = None
                self.selected_face_index = 0
                self.name_entry.delete(0, tk.END)
                self.employee_id_entry.delete(0, tk.END)
                self.department_entry.delete(0, tk.END)
                
                # 이미지 라벨 초기화 (높이 유지하여 하단 버튼이 사라지지 않도록)
                self.image_label.config(image="", text="카메라를 시작하여 사진을 촬영하세요", width=60, height=20)
                # 이미지 참조 제거 (메모리 해제)
                self.image_label.image = None
                
                # 버튼 상태 초기화 (버튼은 표시 유지, 항상 보이도록)
                self.camera_start_btn.config(text="📹 실시간 시작", state="normal")
                self.capture_btn.config(text="📷 사진 촬영", command=self._capture_photo, state="disabled")
                self.retake_btn.config(state="disabled")
                self.crop_btn.config(state="disabled")  # 크롭 버튼도 초기화
                
                print(f"[얼굴 등록 관리] 등록 완료: {name}님, {registered_count}개 얼굴 등록됨")
            else:
                messagebox.showerror(
                    "등록 실패",
                    "얼굴 등록에 실패했습니다.\n\n"
                    "콘솔 로그를 확인하세요.",
                    parent=self.dialog
                )
            
        except Exception as e:
            import traceback
            error_msg = f"등록 오류: {str(e)}\n\n상세 정보는 콘솔을 확인하세요."
            messagebox.showerror("오류", error_msg, parent=self.dialog)
            print(f"[얼굴 등록 관리] 등록 오류:\n{traceback.format_exc()}")
    
    def _update_face_info(self):
        """선택된 사람의 정보 수정 및 저장"""
        # 선택된 얼굴이 있는지 확인
        if not hasattr(self, '_selected_face_id') or not self._selected_face_id:
            messagebox.showwarning(
                "선택 필요",
                "수정할 사람을 왼쪽 목록에서 선택하세요.",
                parent=self.dialog
            )
            return

        # 입력값 가져오기
        new_name = self.name_entry.get().strip()
        new_employee_id = self.employee_id_entry.get().strip()
        new_department = self.department_entry.get().strip()

        if not new_name:
            messagebox.showwarning(
                "이름 필요",
                "이름을 입력하세요.",
                parent=self.dialog
            )
            return

        try:
            # 변경 사항 확인
            old_data = self._selected_face_data
            changes = []

            if new_name != old_data['name']:
                changes.append(f"이름: {old_data['name']} → {new_name}")
            if new_employee_id != (old_data['employee_id'] or ''):
                changes.append(f"사원번호: {old_data['employee_id'] or '(없음)'} → {new_employee_id or '(없음)'}")
            if new_department != (old_data['department'] or ''):
                changes.append(f"부서: {old_data['department'] or '(없음)'} → {new_department or '(없음)'}")

            if not changes:
                messagebox.showinfo(
                    "변경 없음",
                    "수정된 내용이 없습니다.",
                    parent=self.dialog
                )
                return

            # 변경 확인
            if not messagebox.askyesno(
                "정보 수정 확인",
                f"다음 내용을 수정하시겠습니까?\n\n" + "\n".join(changes),
                parent=self.dialog
            ):
                return

            # DB 업데이트
            success = self.face_db.update_face(
                face_id=self._selected_face_id,
                name=new_name,
                employee_id=new_employee_id,
                department=new_department
            )

            if success:
                messagebox.showinfo(
                    "수정 완료",
                    f"{new_name}님의 정보가 수정되었습니다.",
                    parent=self.dialog
                )
                # 목록 새로고침
                self._load_face_list()
                # 선택 초기화
                self._selected_face_id = None
                self._selected_face_data = None
                self.update_btn.config(state="disabled")
            else:
                messagebox.showerror(
                    "수정 실패",
                    "정보 수정에 실패했습니다.\n콘솔 로그를 확인하세요.",
                    parent=self.dialog
                )

        except Exception as e:
            import traceback
            messagebox.showerror("오류", f"정보 수정 오류: {str(e)}", parent=self.dialog)
            print(f"[얼굴 등록 관리] 정보 수정 오류:\n{traceback.format_exc()}")

    def _on_close(self):
        """다이얼로그 종료 시 카메라 중지"""
        self._stop_camera()
        self.dialog.destroy()

    def _delete_face(self):
        """얼굴 삭제 (개선: 에러 처리 강화)"""
        selection = self.face_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "선택 필요",
                "삭제할 얼굴을 선택하세요.",
                parent=self.dialog
            )
            return
        
        idx = selection[0]
        if not hasattr(self.face_listbox, '_face_data') or idx >= len(self.face_listbox._face_data):
            messagebox.showerror("오류", "선택한 항목 정보를 찾을 수 없습니다.", parent=self.dialog)
            return
        
        face = self.face_listbox._face_data[idx]
        
        name_display = face['name']
        if face.get('employee_id'):
            name_display += f" ({face['employee_id']})"
        if face.get('department'):
            name_display += f" - {face['department']}"
        
        if messagebox.askyesno(
            "삭제 확인",
            f"{name_display}님의 얼굴 정보를 삭제하시겠습니까?\n\n"
            "이 작업은 되돌릴 수 없습니다.",
            parent=self.dialog
        ):
            try:
                self.face_db.delete_face(face['id'])
                messagebox.showinfo("삭제 완료", "삭제되었습니다.", parent=self.dialog)
                self._load_face_list()
            except Exception as e:
                import traceback
                error_msg = f"삭제 오류: {str(e)}\n\n상세 정보는 콘솔을 확인하세요."
                messagebox.showerror("오류", error_msg, parent=self.dialog)
                print(f"[얼굴 등록 관리] 삭제 오류:\n{traceback.format_exc()}")

