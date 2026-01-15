"""
GARAMe 안전장구 감지 시스템 v2.0 - 최신 AI 기술 적용
InsightFace (얼굴 인식) + YOLOv11 (PPE 감지)

주요 업그레이드:
✓ InsightFace: 99.86% 얼굴 인식 정확도 (기존 99.38% 대비 향상)
✓ YOLOv11: 92.7% mAP50 PPE 감지 정확도 (기존 Haar Cascade 70% 대비 대폭 향상)
✓ GPU 가속 지원 (ONNX Runtime)
✓ 실시간 처리 최적화

감지 항목:
✓ 안전모 (Helmet)
✓ 보안경 (Safety Glasses)
✓ 장갑 (Gloves)
✓ 안전화 (Safety Boots)
✓ 안전조끼 (Safety Vest)
✓ 얼굴 인식 (Face Recognition)
"""

import cv2
import numpy as np
from datetime import datetime
import json
import os
import platform
from pathlib import Path

from ..utils.helpers import get_base_dir, get_performance_settings

# PIL import (한글 텍스트 표시용)
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = ImageDraw = ImageFont = None

# InsightFace import (최신 얼굴 인식)
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_OK = True
except Exception as e:
    INSIGHTFACE_OK = False
    insightface = None
    FaceAnalysis = None
    print(f"[경고] InsightFace를 사용할 수 없습니다: {e}")

# InsightFace 싱글톤 인스턴스 (여러 번 로드 방지)
_shared_insightface_app = None
_shared_insightface_initialized = False
_shared_insightface_loading = False  # 로딩 중 플래그
_shared_insightface_lock = None  # 스레드 락
_shared_insightface_inference_lock = None  # 추론 시 스레드 안전성 락
_current_performance_mode = 2  # 현재 성능 모드 (전역)

import threading
_shared_insightface_lock = threading.Lock()
_shared_insightface_inference_lock = threading.Lock()  # InsightFace.get()은 스레드 안전하지 않음


def set_performance_mode(mode: int):
    """성능 모드 설정 (앱 시작 시 호출)"""
    global _current_performance_mode
    _current_performance_mode = max(1, min(3, mode))
    print(f"[성능 모드] 모드 {_current_performance_mode} 설정됨")


def get_current_performance_mode() -> int:
    """현재 성능 모드 반환"""
    global _current_performance_mode
    return _current_performance_mode


def get_shared_insightface_app():
    """공유 InsightFace 앱 반환 (싱글톤) - 성능 모드에 따라 최적화"""
    global _shared_insightface_app, _shared_insightface_initialized, _current_performance_mode

    if _shared_insightface_initialized:
        return _shared_insightface_app

    with _shared_insightface_lock:
        # 다시 확인 (락 획득 후)
        if _shared_insightface_initialized:
            return _shared_insightface_app

        _shared_insightface_initialized = True

        if not INSIGHTFACE_OK:
            return None

        try:
            # 성능 모드에 따른 설정 가져오기
            settings = get_performance_settings(_current_performance_mode)
            insight_cfg = settings.get('insightface', {})

            model_name = insight_cfg.get('model_name', 'buffalo_sc')
            det_size = insight_cfg.get('det_size', (320, 320))
            det_thresh = insight_cfg.get('det_thresh', 0.4)
            providers = insight_cfg.get('providers', ['CPUExecutionProvider'])

            # GPU 가용성 확인 (모드 3에서만 시도)
            actual_providers = providers.copy()
            if 'CUDAExecutionProvider' in providers:
                try:
                    import onnxruntime as ort
                    available_providers = ort.get_available_providers()
                    if 'CUDAExecutionProvider' not in available_providers:
                        actual_providers = ['CPUExecutionProvider']
                        print("[InsightFace] CUDA 미지원 - CPU 모드로 전환")
                except Exception:
                    actual_providers = ['CPUExecutionProvider']

            # ctx_id 설정: GPU 사용 시 0, CPU 시 -1
            ctx_id = 0 if 'CUDAExecutionProvider' in actual_providers else -1

            print(f"[InsightFace] 모드 {_current_performance_mode} 설정 적용:")
            print(f"  - 모델: {model_name}")
            print(f"  - det_size: {det_size}")
            print(f"  - det_thresh: {det_thresh}")
            print(f"  - providers: {actual_providers}")

            _shared_insightface_app = FaceAnalysis(
                name=model_name,
                providers=actual_providers,
                allowed_modules=['detection', 'recognition']  # landmark 제외 (속도 향상)
            )
            _shared_insightface_app.prepare(ctx_id=ctx_id, det_size=det_size, det_thresh=det_thresh)
            print(f"[InsightFace] 공유 모델 로드 성공 ({model_name}, det_size={det_size})")

        except Exception as e:
            print(f"[InsightFace] 공유 모델 로드 실패: {e}")
            # 폴백: 기본 설정으로 재시도
            try:
                _shared_insightface_app = FaceAnalysis(
                    name='buffalo_sc',
                    providers=['CPUExecutionProvider'],
                    allowed_modules=['detection', 'recognition']
                )
                _shared_insightface_app.prepare(ctx_id=-1, det_size=(320, 320), det_thresh=0.4)
                print("[InsightFace] 폴백 모델 로드 성공 (buffalo_sc)")
            except Exception as e2:
                print(f"[InsightFace] 폴백 모델 로드도 실패: {e2}")
                _shared_insightface_app = None

    return _shared_insightface_app


def preload_models_async(performance_mode: int = 2):
    """
    모델을 백그라운드에서 미리 로드 (앱 시작 시 호출)

    Args:
        performance_mode: 성능 설정 (1: 기본, 2: 표준, 3: 고급)
            1: 얼굴 인식만 (InsightFace)
            2: 얼굴 + 안전장구 6종 (InsightFace + YOLO PPE)
            3: 전체 (InsightFace + YOLO PPE + YOLO COCO)
    """
    # 전역 성능 모드 설정 (모델 로딩 전에 반드시 호출)
    set_performance_mode(performance_mode)

    def _preload():
        settings = get_performance_settings(performance_mode)
        print(f"[PreLoad] 모델 사전 로드 시작... (성능 모드: {performance_mode} - {settings['name']})")
        print(f"[PreLoad] 예상 성능: {settings.get('expected_fps', 'N/A')}, 지연시간: {settings.get('expected_latency', 'N/A')}")

        # 모드 1 이상: 얼굴 인식 (InsightFace) - 항상 로드
        get_shared_insightface_app()
        print(f"[PreLoad] 얼굴 인식 모델 로드 완료")

        # 모드 2 이상: 안전장구 인식 (YOLO PPE)
        if performance_mode >= 2:
            get_shared_yolo_model()
            print(f"[PreLoad] 안전장구 인식 모델 로드 완료")

        # 모드 3: 사물 인식 (YOLO COCO 80 클래스)
        if performance_mode >= 3:
            get_shared_yolo_person_model()  # yolo11m.pt - COCO 80 클래스
            print(f"[PreLoad] 사물 인식 모델 로드 완료")

        print(f"[PreLoad] 모델 사전 로드 완료 (모드 {performance_mode})")

    thread = threading.Thread(target=_preload, daemon=True)
    thread.start()
    return thread

# v1.9.5: face_recognition은 더 이상 사용하지 않음 (InsightFace로 대체)
FACE_RECOGNITION_OK = False
face_recognition = None

# YOLOv11 import (최신 객체 감지)
try:
    import torch
    import sys
    import ultralytics

    # PyTorch 2.6+ weights_only 문제 해결
    # ultralytics 모델 로드를 위해 필요한 모든 클래스들을 안전한 글로벌로 등록
    safe_globals = []

    # ultralytics 모델 클래스들
    try:
        from ultralytics.nn.tasks import DetectionModel, SegmentationModel, ClassificationModel, PoseModel
        safe_globals.extend([DetectionModel, SegmentationModel, ClassificationModel, PoseModel])
    except Exception:
        pass

    # torch.nn 모듈 클래스들 (모델 구조에 필요)
    try:
        import torch.nn as nn
        safe_globals.extend([
            nn.Sequential,
            nn.ModuleList,
            nn.ModuleDict,
            nn.Conv2d,
            nn.BatchNorm2d,
            nn.SiLU,
            nn.ReLU,
            nn.LeakyReLU,
            nn.MaxPool2d,
            nn.AdaptiveAvgPool2d,
            nn.Upsample,
            nn.Linear,
            nn.Dropout,
            nn.Identity,
        ])
    except Exception:
        pass

    # ultralytics 내부 모듈들 (다양한 import 경로 시도)
    try:
        # 최신 ultralytics 구조
        from ultralytics.nn import modules as nn_modules
        # 모듈에서 필요한 클래스들 가져오기
        module_classes = []
        for name in dir(nn_modules):
            obj = getattr(nn_modules, name)
            if isinstance(obj, type):
                module_classes.append(obj)
        safe_globals.extend(module_classes)
    except Exception:
        pass

    try:
        # 개별 클래스 import (구버전 호환)
        from ultralytics.nn.modules.conv import Conv, DWConv, ConvTranspose, Focus, GhostConv, LightConv, RepConv
        from ultralytics.nn.modules.block import C2f, C3, SPPF, Bottleneck, BottleneckCSP
        from ultralytics.nn.modules.head import Detect, Segment, Pose, Classify
        safe_globals.extend([
            Conv, DWConv, ConvTranspose, Focus, GhostConv, LightConv, RepConv,
            C2f, C3, SPPF, Bottleneck, BottleneckCSP,
            Detect, Segment, Pose, Classify,
        ])
    except Exception:
        pass

    # ultralytics.nn.modules 직접 등록 (PyTorch 2.6+ weights_only 문제 해결)
    try:
        import ultralytics.nn.modules
        for name in ['Conv', 'DWConv', 'ConvTranspose', 'Focus', 'GhostConv', 'LightConv', 'RepConv',
                     'C2f', 'C3', 'SPPF', 'Bottleneck', 'BottleneckCSP', 'Concat', 'Detect', 'Segment',
                     'Pose', 'Classify', 'DFL', 'Proto', 'Ensemble', 'C3k2', 'C2PSA', 'SCDown', 'Attention',
                     'CBAM', 'ChannelAttention', 'SpatialAttention', 'C3Ghost', 'C3TR', 'C3SPP', 'C3x',
                     'ResNetLayer', 'OBB', 'WorldDetect', 'ImagePoolingAttn', 'ContrastiveHead', 'BNContrastiveHead']:
            if hasattr(ultralytics.nn.modules, name):
                safe_globals.append(getattr(ultralytics.nn.modules, name))
    except Exception:
        pass

    # 안전한 글로벌 등록
    if safe_globals:
        torch.serialization.add_safe_globals(safe_globals)

    # ultralytics.yolo 호환성 패치 (구버전 모델 로드용)
    if 'ultralytics.yolo' not in sys.modules:
        sys.modules['ultralytics.yolo'] = ultralytics
        # engine 모듈이 있는 경우에만 패치 (최신 버전에서는 없을 수 있음)
        if hasattr(ultralytics, 'engine'):
            sys.modules['ultralytics.yolo.engine'] = ultralytics.engine
        if hasattr(ultralytics, 'utils'):
            sys.modules['ultralytics.yolo.utils'] = ultralytics.utils

    from ultralytics import YOLO
    YOLO_OK = True
except Exception as e:
    YOLO_OK = False
    YOLO = None
    print(f"Ultralytics YOLO를 사용할 수 없습니다. 기존 OpenCV 방식을 사용합니다. (에러: {e})")

# YOLO 싱글톤 인스턴스 (여러 번 로드 방지)
_shared_yolo_model = None  # 헬멧/조끼 모델 (ppe_helmet_vest.pt)
_shared_yolo_mask_model = None  # 마스크 모델 (ppe_yolov8m.pt)
_shared_yolo_person_model = None  # 사람 감지 전용 기본 모델 (yolo11n.pt)
_shared_yolo_initialized = False
_shared_yolo_mask_initialized = False
_shared_yolo_person_initialized = False
_shared_yolo_mask_lock = threading.Lock()
_shared_yolo_person_lock = threading.Lock()


def get_shared_yolo_mask_model():
    """마스크 감지용 보조 YOLO 모델 반환 (싱글톤)"""
    global _shared_yolo_mask_model, _shared_yolo_mask_initialized

    if _shared_yolo_mask_initialized:
        return _shared_yolo_mask_model

    with _shared_yolo_mask_lock:
        if _shared_yolo_mask_initialized:
            return _shared_yolo_mask_model

        _shared_yolo_mask_initialized = True

        if not YOLO_OK:
            return None

        try:
            # PyTorch 2.6+ weights_only 문제 해결
            original_load = None
            try:
                original_load = torch.load
                torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
            except Exception:
                pass

            # 마스크 감지용 모델 경로 (ppe_yolov8m.pt 만 사용)
            mask_model_paths = [
                os.path.join(get_base_dir(), 'models', 'ppe_yolov8m.pt'),
            ]

            for model_path in mask_model_paths:
                if os.path.exists(model_path):
                    _shared_yolo_mask_model = YOLO(model_path)
                    print(f"[YOLO-Mask] 마스크 감지 모델 로드 성공: {model_path}")
                    if hasattr(_shared_yolo_mask_model, 'names'):
                        print(f"[YOLO-Mask] 모델 클래스: {_shared_yolo_mask_model.names}")
                    if original_load:
                        torch.load = original_load
                    return _shared_yolo_mask_model

            print("[YOLO-Mask] 마스크 감지 모델 (ppe_yolov8m.pt) 없음")
            if original_load:
                torch.load = original_load

        except Exception as e:
            print(f"[YOLO-Mask] 모델 로드 실패: {e}")
            _shared_yolo_mask_model = None
            try:
                if original_load:
                    torch.load = original_load
            except Exception:
                pass

    return _shared_yolo_mask_model


def get_shared_yolo_person_model():
    """사람/사물 감지 전용 YOLO COCO 모델 반환 (싱글톤) - 성능 모드에 따라 최적화

    PPE 모델은 안전장비 위주로 훈련되어 사람 전체를 감지하지 못함.
    COCO 모델(yolo11n/m.pt)은 사람 전체와 80종 사물을 감지.
    """
    global _shared_yolo_person_model, _shared_yolo_person_initialized, _current_performance_mode

    if _shared_yolo_person_initialized:
        return _shared_yolo_person_model

    with _shared_yolo_person_lock:
        if _shared_yolo_person_initialized:
            return _shared_yolo_person_model

        _shared_yolo_person_initialized = True

        if not YOLO_OK:
            return None

        # 성능 모드에 따른 설정
        settings = get_performance_settings(_current_performance_mode)
        coco_cfg = settings.get('yolo_coco', {})

        # 모드 1, 2에서는 COCO 모델 사용 안 함 (사물 인식 비활성화)
        if not coco_cfg.get('enabled', False):
            print(f"[YOLO-COCO] 모드 {_current_performance_mode}에서 비활성화됨")
            return None

        try:
            # PyTorch 2.6+ weights_only 문제 해결
            original_load = None
            try:
                original_load = torch.load
                torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
            except Exception:
                pass

            # 성능 모드에 따른 모델 선택
            model_name = coco_cfg.get('model', 'yolo11n.pt')

            print(f"[YOLO-COCO] 모드 {_current_performance_mode} 설정:")
            print(f"  - 모델: {model_name}")
            print(f"  - imgsz: {coco_cfg.get('imgsz', 640)}")
            print(f"  - conf: {coco_cfg.get('conf', 0.3)}")
            print(f"  - half: {coco_cfg.get('half', False)}")

            _shared_yolo_person_model = YOLO(model_name)
            print(f"[YOLO-COCO] 모델 로드 성공: {model_name}")

            if original_load:
                torch.load = original_load

            return _shared_yolo_person_model

        except Exception as e:
            print(f"[YOLO-COCO] 모델 로드 실패: {e}")
            _shared_yolo_person_model = None
            try:
                if original_load:
                    torch.load = original_load
            except Exception:
                pass

    return _shared_yolo_person_model


def get_shared_yolo_model():
    """공유 YOLO PPE 모델 반환 (싱글톤) - 성능 모드에 따라 최적화"""
    global _shared_yolo_model, _shared_yolo_initialized, _current_performance_mode

    if _shared_yolo_initialized:
        return _shared_yolo_model

    _shared_yolo_initialized = True

    if not YOLO_OK:
        return None

    # 모드 1에서는 YOLO PPE 사용 안 함
    settings = get_performance_settings(_current_performance_mode)
    ppe_cfg = settings.get('yolo_ppe', {})

    if not ppe_cfg.get('enabled', True):
        print(f"[YOLO-PPE] 모드 {_current_performance_mode}에서 비활성화됨")
        return None

    try:
        # PyTorch 2.6+ weights_only 문제 해결: 임시로 기본값 변경
        original_load = None
        try:
            original_load = torch.load
            torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
        except Exception:
            pass

        # 성능 모드에 따른 모델 선택
        preferred_model = ppe_cfg.get('model', 'ppe_detect.pt')
        fallback_model = ppe_cfg.get('model_fallback', 'ppe_helmet_vest.pt')

        base = get_base_dir()

        # 선호 모델 경로 목록 (성능 모드에 따라 다름)
        model_paths = [
            os.path.join(base, 'models', preferred_model),    # 모드별 선호 모델
            os.path.join(base, 'models', fallback_model),     # 폴백 모델
            os.path.join(base, 'models', 'ppe_helmet_vest.pt'),
            os.path.join(base, 'models', 'ppe_yolov8m.pt'),
            os.path.join(base, 'models', 'ppe_full.pt'),
            os.path.join(base, 'models', 'ppe.pt'),
        ]

        print(f"[YOLO-PPE] 모드 {_current_performance_mode} 설정:")
        print(f"  - 선호 모델: {preferred_model}")
        print(f"  - imgsz: {ppe_cfg.get('imgsz', 640)}")
        print(f"  - conf: {ppe_cfg.get('conf', 0.25)}")
        print(f"  - half: {ppe_cfg.get('half', False)}")

        for model_path in model_paths:
            if os.path.exists(model_path):
                _shared_yolo_model = YOLO(model_path)
                print(f"[YOLO-PPE] 모델 로드 성공: {model_path}")
                if hasattr(_shared_yolo_model, 'names'):
                    print(f"[YOLO-PPE] 클래스: {_shared_yolo_model.names}")
                if original_load:
                    torch.load = original_load
                return _shared_yolo_model

        # 폴백: 기본 YOLO 모델
        _shared_yolo_model = YOLO('yolo11n.pt')  # nano (가벼움)
        print("[YOLO-PPE] 폴백 모델 로드 (yolo11n.pt)")

        if original_load:
            torch.load = original_load

    except Exception as e:
        print(f"[YOLO-PPE] 모델 로드 실패: {e}")
        _shared_yolo_model = None
        try:
            if original_load:
                torch.load = original_load
        except Exception:
            pass

    return _shared_yolo_model


class SafetyEquipmentDetectorV2:
    """안전장구 착용 감지 시스템 v2.0 - 최신 AI 기술"""

    def __init__(self, camera=None, use_yolo=True, use_insightface=True):
        """
        초기화

        Args:
            camera: cv2.VideoCapture 객체
            use_yolo: YOLOv11 사용 여부 (False면 기존 OpenCV 사용)
            use_insightface: InsightFace 사용 여부 (False면 기존 face_recognition 사용)
        """
        self.camera = camera
        self.use_yolo = use_yolo and YOLO_OK
        self.use_insightface = use_insightface and INSIGHTFACE_OK

        # YOLOv11 모델 로드 (싱글톤 사용)
        self.yolo_model = None
        self.yolo_mask_model = None  # 마스크 감지용 보조 모델
        self.yolo_person_model = None  # 사람 감지 전용 기본 모델
        self.has_ppe_model = False  # PPE 전용 모델 여부
        self.has_mask_model = False  # 마스크 모델 여부
        if self.use_yolo:
            self.yolo_model = get_shared_yolo_model()
            if self.yolo_model is None:
                self.use_yolo = False
            else:
                # PPE 전용 모델인지 확인 (대소문자 무시)
                # 기본 모델도 사람 감지용으로 활성화 유지
                if hasattr(self.yolo_model, 'names'):
                    names_str = str(self.yolo_model.names).lower()
                    self.has_ppe_model = 'helmet' in names_str or 'glove' in names_str or 'goggle' in names_str
                    print(f"[PPE] 모델 감지: has_ppe_model={self.has_ppe_model}")

                    # 메인 모델에 마스크 클래스가 없으면 보조 모델 로드
                    if 'mask' not in names_str:
                        self.yolo_mask_model = get_shared_yolo_mask_model()
                        if self.yolo_mask_model and hasattr(self.yolo_mask_model, 'names'):
                            mask_names_str = str(self.yolo_mask_model.names).lower()
                            self.has_mask_model = 'mask' in mask_names_str
                            print(f"[PPE] 마스크 보조 모델 로드: has_mask_model={self.has_mask_model}")

                # 사람 감지 전용 기본 모델 로드 (PPE 모델은 사람 전체를 감지하지 못함)
                self.yolo_person_model = get_shared_yolo_person_model()
                if self.yolo_person_model:
                    print(f"[PPE] 사람 감지 보조 모델 로드 완료")

        # InsightFace 공유 인스턴스 사용 (여러 번 로드 방지)
        self.face_app = None
        if self.use_insightface:
            self.face_app = get_shared_insightface_app()
            if self.face_app is None:
                self.use_insightface = False

        # 기존 OpenCV Haar Cascade (항상 로드 - 얼굴 감지 보조용)
        self.face_cascade = None
        self.eye_cascade = None
        self.upper_body_cascade = None
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
            self.upper_body_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_upperbody.xml'
            )
            if not self.use_yolo:
                print("OpenCV Haar Cascade 모델 로드 (백업용)")
        except Exception as e:
            print(f"Haar Cascade 로딩 오류: {e}")

        # 감지 결과 저장
        self.last_results = None

        # 추적 기능
        self.tracking_enabled = True
        self.last_person_box = None
        self.frames_without_detection = 0
        self.max_tracking_frames = 30

        # === 인식 안정화를 위한 시간 기반 필터링 ===
        # PPE 상태 히스토리 (최근 N프레임의 결과 저장)
        self._ppe_history = {
            'helmet': [],
            'vest': [],
            'gloves': [],
            'glasses': [],
            'mask': [],
            'boots': []
        }
        self._ppe_history_size = 3  # 최근 3프레임 기준 (빠른 반응)
        self._ppe_stable_threshold = 2  # 3프레임 중 2번 이상 감지되어야 착용으로 판정

        # 프레임 스킵 설정 (성능 최적화) - 매 프레임 감지로 변경
        self._frame_count = 0
        self._detection_interval = 1  # 매 프레임 감지 (실시간 반응)
        self._last_stable_results = None  # 마지막 안정화된 결과

        # === 객체 추적 (IOU 기반) - 실시간 반응 ===
        self._last_face_bbox = None  # 마지막 얼굴 위치
        self._last_face_name = None  # 마지막 인식된 이름
        self._face_lost_frames = 0  # 얼굴 미감지 프레임 수
        self._face_tracking_threshold = 2  # 2프레임만 추적 유지 (실시간)
        self._iou_threshold = 0.3  # IOU 임계값 (위치 유사성)

        # PPE 위치 추적 - 실시간 반응
        self._last_ppe_boxes = {}  # 마지막 PPE 위치들
        self._ppe_lost_frames = {}  # PPE별 미감지 프레임 수
        self._ppe_tracking_threshold = 2  # 2프레임만 추적 유지 (실시간)

        # 얼굴 인식 데이터베이스
        self.face_db = None
        self.face_recognition_enabled = False
        if self.use_insightface or FACE_RECOGNITION_OK:
            try:
                from .face_database import FaceDatabase
                self.face_db = FaceDatabase()
                self.face_recognition_enabled = True
            except Exception as e:
                print(f"얼굴 인식 데이터베이스 로딩 오류: {e}")
                self.face_recognition_enabled = False

        # === 얼굴 인식 성능 최적화 (v1.9.7) ===
        # 스킵 프레임: 매 프레임 대신 N프레임마다 인식 수행
        self._face_recognition_interval = 3  # 3프레임마다 인식 (약 10fps에서 0.3초 간격)
        self._face_recognition_frame_count = 0
        self._cached_face_results = []  # 캐시된 얼굴 감지 결과
        self._cached_recognized_faces = []  # 캐시된 인식 결과

        # DB 임베딩 캐싱 (매번 DB 조회 방지)
        self._cached_db_embeddings = None
        self._db_cache_time = 0
        self._db_cache_ttl = 10.0  # 10초마다 DB 캐시 갱신

        # 한글 폰트
        self.korean_font = None
        if PIL_AVAILABLE:
            self.korean_font = self._load_korean_font()

        # YOLOv11 PPE 클래스 매핑 (동적으로 모델에서 가져옴)
        self.ppe_classes = {}
        self.ppe_no_classes = {}  # 미착용 클래스 (no_helmet, no_glove 등)
        self.ppe_class_names = {}  # class_id -> normalized_name
        self.person_class_id = -1  # person 클래스 ID
        if self.yolo_model and hasattr(self.yolo_model, 'names'):
            # 모델의 클래스 이름을 정규화하여 매핑
            for cls_id, cls_name in self.yolo_model.names.items():
                name_lower = cls_name.lower().replace('-', '_').replace(' ', '_')
                self.ppe_class_names[cls_id] = name_lower

                # person 클래스 감지
                if name_lower == 'person':
                    self.person_class_id = cls_id
                # 착용 클래스 매핑 (no가 포함되지 않은 것)
                elif 'helmet' in name_lower and 'no' not in name_lower:
                    self.ppe_classes['helmet'] = cls_id
                elif 'vest' in name_lower and 'no' not in name_lower:
                    self.ppe_classes['vest'] = cls_id
                elif 'glove' in name_lower and 'no' not in name_lower:
                    self.ppe_classes['gloves'] = cls_id
                elif ('boot' in name_lower or 'shoe' in name_lower) and 'no' not in name_lower:
                    self.ppe_classes['boots'] = cls_id
                elif ('glass' in name_lower or 'goggle' in name_lower) and 'no' not in name_lower:
                    self.ppe_classes['glasses'] = cls_id
                elif 'mask' in name_lower and 'no' not in name_lower:
                    self.ppe_classes['mask'] = cls_id
                # 미착용 클래스 매핑 (no_ 또는 no- 포함)
                elif 'no_helmet' in name_lower or 'no-helmet' in name_lower:
                    self.ppe_no_classes['helmet'] = cls_id
                elif 'no_vest' in name_lower or 'no-vest' in name_lower:
                    self.ppe_no_classes['vest'] = cls_id
                elif 'no_glove' in name_lower or 'no-glove' in name_lower:
                    self.ppe_no_classes['gloves'] = cls_id
                elif 'no_goggle' in name_lower or 'no-goggle' in name_lower or 'no_glass' in name_lower:
                    self.ppe_no_classes['glasses'] = cls_id
                elif 'no_shoe' in name_lower or 'no-shoe' in name_lower or 'no_boot' in name_lower:
                    self.ppe_no_classes['boots'] = cls_id
                elif 'no_mask' in name_lower or 'no-mask' in name_lower:
                    self.ppe_no_classes['mask'] = cls_id
            print(f"[PPE] 착용 클래스 매핑: {self.ppe_classes}")
            print(f"[PPE] 미착용 클래스 매핑: {self.ppe_no_classes}")
            print(f"[PPE] person 클래스 ID: {self.person_class_id}")
            print(f"[PPE] 모델 전체 클래스: {self.yolo_model.names}")

    def set_camera(self, camera):
        """카메라 설정"""
        self.camera = camera

    def enable_face_recognition(self, enable: bool = True):
        """얼굴 인식 활성화/비활성화"""
        self.face_recognition_enabled = enable
        if enable and self.face_db is None:
            try:
                from .face_database import FaceDatabase
                self.face_db = FaceDatabase()
            except Exception as e:
                print(f"얼굴 인식 데이터베이스 로딩 오류: {e}")
                self.face_recognition_enabled = False

    def _get_yolo_model_path(self):
        """YOLOv11 PPE 모델 경로 찾기"""
        # 가능한 모델 경로들
        base = get_base_dir()
        possible_paths = [
            os.path.join(base, 'models', 'yolo11_ppe.pt'),
            os.path.join(base, 'models', 'yolov11_ppe_best.pt'),
            os.path.expanduser('~/.garame/models/yolo11_ppe.pt')
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def _load_korean_font(self):
        """한글 폰트 로드"""
        if not PIL_AVAILABLE:
            return None

        try:
            system = platform.system()
            font_paths = []

            if system == "Linux":
                font_paths = [
                    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
            elif system == "Darwin":  # macOS
                font_paths = [
                    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                    "/System/Library/Fonts/AppleGothic.ttf",
                ]
            elif system == "Windows":
                windows_font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
                font_paths = [
                    os.path.join(windows_font_dir, "malgun.ttf"),
                    os.path.join(windows_font_dir, "gulim.ttc"),
                ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 24)
                        print(f"한글 폰트 로드 성공: {font_path}")
                        return font
                    except Exception:
                        continue

            return ImageFont.load_default()
        except Exception as e:
            print(f"한글 폰트 로드 오류: {e}")
            try:
                return ImageFont.load_default()
            except:
                return None

    def _put_korean_text(self, frame, text, position, color=(0, 255, 0), font_size=24):
        """
        한글 텍스트를 프레임에 그리기 (PIL 사용, 성능 최적화)

        Args:
            frame: OpenCV BGR 이미지
            text: 표시할 텍스트
            position: (x, y) 좌표
            color: BGR 색상 튜플
            font_size: 폰트 크기

        Returns:
            텍스트가 그려진 프레임
        """
        # 한글이 없으면 빠른 cv2.putText 사용
        has_korean = any('\uac00' <= c <= '\ud7a3' or '\u3131' <= c <= '\u3163' for c in text)
        if not has_korean or not PIL_AVAILABLE:
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            return frame

        try:
            # BGR -> RGB 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_img)

            # 폰트 캐시 사용 (성능 최적화)
            if not hasattr(self, '_font_cache'):
                self._font_cache = {}

            cache_key = font_size
            if cache_key not in self._font_cache:
                font = None
                if self.korean_font:
                    try:
                        font_path = self.korean_font.path if hasattr(self.korean_font, 'path') else None
                        if font_path:
                            font = ImageFont.truetype(font_path, font_size)
                        else:
                            font = self.korean_font
                    except:
                        font = self.korean_font
                self._font_cache[cache_key] = font

            font = self._font_cache[cache_key]

            if font is None:
                font = ImageFont.load_default()

            # BGR -> RGB 색상 변환
            rgb_color = (color[2], color[1], color[0])

            # 텍스트 그리기 (테두리 효과)
            x, y = position
            # 검은색 테두리
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
            # 메인 텍스트
            draw.text((x, y), text, font=font, fill=rgb_color)

            # RGB -> BGR 변환
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return frame

        except Exception as e:
            # 오류 시 cv2.putText 폴백
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            return frame

    def _is_small_person_box(self, person_box, frame_h, frame_w):
        """
        person_box가 너무 작은지 확인 (PPE 모델이 사람 전체를 감지하지 못한 경우)

        PPE 모델은 헬멧/조끼 영역만 감지하여 person_box가 작게 나옴.
        예: 머리 부분만 감지되어 상체/하체가 잘림

        Args:
            person_box: [x1, y1, x2, y2] 좌표
            frame_h: 프레임 높이
            frame_w: 프레임 너비

        Returns:
            bool: True면 너무 작음, False면 적절함
        """
        if person_box is None:
            return True

        x1, y1, x2, y2 = person_box
        box_w = x2 - x1
        box_h = y2 - y1

        # 박스 크기가 너무 작으면 True (프레임의 10% 미만)
        min_area_ratio = 0.10  # 프레임 면적의 10%
        box_area = box_w * box_h
        frame_area = frame_h * frame_w

        if box_area < frame_area * min_area_ratio:
            return True

        # 박스 높이가 너무 짧으면 True (프레임 높이의 30% 미만)
        # 사람 전체가 화면에 있으면 최소 30% 이상 차지
        min_height_ratio = 0.30
        if box_h < frame_h * min_height_ratio:
            return True

        # 박스 비율이 비정상적이면 True (너무 넓거나 너무 좁음)
        # 사람은 보통 세로가 더 긺 (높이 > 너비)
        aspect_ratio = box_h / max(box_w, 1)
        if aspect_ratio < 0.8:  # 너무 납작함 (얼굴만 감지된 경우)
            return True

        return False

    def _detect_color(self, frame, bbox):
        """
        바운딩 박스 영역의 주요 색상 감지

        Args:
            frame: BGR 이미지
            bbox: [x1, y1, x2, y2] 좌표

        Returns:
            dict: {'name': '색상명', 'name_kr': '한글색상명', 'rgb': (R, G, B), 'hsv': (H, S, V)}
        """
        try:
            x1, y1, x2, y2 = [int(x) for x in bbox]
            h, w = frame.shape[:2]

            # 경계 체크
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            if x2 <= x1 or y2 <= y1:
                return None

            # ROI 추출
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                return None

            # 중앙 50% 영역만 사용 (배경 노이즈 제거)
            roi_h, roi_w = roi.shape[:2]
            margin_x = roi_w // 4
            margin_y = roi_h // 4
            center_roi = roi[margin_y:roi_h-margin_y, margin_x:roi_w-margin_x]

            if center_roi.size == 0:
                center_roi = roi

            # HSV 변환
            hsv_roi = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)

            # 평균 색상 계산
            avg_h = np.mean(hsv_roi[:, :, 0])
            avg_s = np.mean(hsv_roi[:, :, 1])
            avg_v = np.mean(hsv_roi[:, :, 2])

            # 평균 BGR
            avg_b = np.mean(center_roi[:, :, 0])
            avg_g = np.mean(center_roi[:, :, 1])
            avg_r = np.mean(center_roi[:, :, 2])

            # 색상 분류 (HSV 기반)
            color_name, color_name_kr = self._classify_color(avg_h, avg_s, avg_v)

            return {
                'name': color_name,
                'name_kr': color_name_kr,
                'rgb': (int(avg_r), int(avg_g), int(avg_b)),
                'hsv': (int(avg_h), int(avg_s), int(avg_v))
            }

        except Exception as e:
            return None

    def _classify_color(self, h, s, v):
        """
        HSV 값으로 색상 분류

        Args:
            h: Hue (0-180)
            s: Saturation (0-255)
            v: Value (0-255)

        Returns:
            tuple: (영문 색상명, 한글 색상명)
        """
        # 무채색 판정 (검정, 회색, 흰색)
        # 1. 매우 어두운 색 → 검정
        if v < 50:
            return ('black', '검정')

        # 2. 채도가 낮으면 무채색
        # - 밝기가 낮을수록 채도 임계값을 높임 (어두운 회색 오탐 방지)
        # - v=50~100: s<50이면 무채색, v=100~150: s<40이면 무채색, v>150: s<30이면 무채색
        saturation_threshold = 50 if v < 100 else (40 if v < 150 else 30)
        if s < saturation_threshold:
            if v > 200:
                return ('white', '흰색')
            elif v > 100:
                return ('gray', '회색')
            else:
                return ('dark_gray', '진회색')

        # 3. 채도가 있어도 밝기가 낮고 채도가 낮은 편이면 진회색
        # RGB=(63,63,60) 같은 경우: 어두운 색인데 미세한 색조 차이로 유채색 판정되는 것 방지
        if v < 100 and s < 60:
            return ('dark_gray', '진회색')

        # 유채색 분류 (Hue 기반)
        # OpenCV HSV: H는 0-180 범위
        if h < 10 or h >= 170:
            return ('red', '빨강')
        elif h < 22:
            return ('orange', '주황')
        elif h < 35:
            return ('yellow', '노랑')
        elif h < 45:
            return ('lime', '연두')
        elif h < 75:
            return ('green', '초록')
        elif h < 95:
            return ('cyan', '청록')
        elif h < 125:
            return ('blue', '파랑')
        elif h < 145:
            return ('purple', '보라')
        elif h < 170:
            return ('pink', '분홍')
        else:
            return ('red', '빨강')

    def detect_ppe_with_yolo(self, frame):
        """
        YOLOv11로 PPE 감지

        Returns:
            dict: PPE 감지 결과
        """
        if not self.use_yolo or self.yolo_model is None:
            return None

        try:
            # 프레임 유효성 검사 (IP 카메라 호환성)
            if frame is None or len(frame.shape) < 2:
                return None

            # 입력 이미지 전처리
            h, w = frame.shape[:2]
            channels = frame.shape[2] if len(frame.shape) > 2 else 1

            # 그레이스케일 → BGR 변환
            if channels == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            # RGBA → BGR 변환
            elif channels == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            # 프레임이 비어있는지 확인
            if frame.size == 0 or h == 0 or w == 0:
                return None

            # IP 카메라 프레임 호환성: 연속 메모리 배열로 복사 (YOLO 호환성)
            # RTSP 스트림에서 읽은 프레임이 비연속 메모리일 수 있음
            if not frame.flags['C_CONTIGUOUS']:
                frame = np.ascontiguousarray(frame)

            # 고해상도 프레임 크기 제한 (4K → 1080p로 리사이즈)
            max_dim = 1920
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                h, w = new_h, new_w

            # 헬멧 감지를 위해 해상도 설정
            # 고해상도 카메라(IP카메라)는 1280, 일반 웹캠은 640
            # 1280은 작은 객체 감지에 유리하지만 속도가 느림
            if max(h, w) > 1500:  # 1080p 이상 (IP카메라)
                inference_size = 1280
            else:
                inference_size = 640

            # 비율 유지하며 리사이즈
            scale = inference_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # YOLOv11 추론
            # conf=0.01로 매우 낮춰서 더 많은 객체 감지 (나중에 필터링) - 1.9.7 최적값
            results = self.yolo_model(
                resized_frame,
                verbose=False,
                conf=0.01,  # 신뢰도 임계값 매우 낮춤 (1%) - 후처리에서 필터링
                iou=0.45,   # NMS IoU 임계값 (중복 제거)
                imgsz=inference_size,
                augment=False
            )

            ppe_detections = {
                'helmet': False,
                'helmet_color': None,  # 헬멧 색상
                'vest': False,
                'vest_color': None,  # 조끼 색상
                'gloves': False,
                'boots': False,
                'glasses': False,
                'mask': False,
                'person': None,
                'boxes': [],
                # 미착용 감지 (사람 존재 확인용)
                'no_helmet': False,
                'no_gloves': False,
                'no_glasses': False,
                'no_boots': False,
                'no_mask': False
            }

            # 좌표 복원을 위한 역스케일 계산
            inv_scale = max(h, w) / inference_size

            # 디버그용: 모든 감지 (낮은 신뢰도 포함) 카운트
            low_conf_count = 0
            very_low_conf_count = 0

            # 신뢰도 임계값 (인식률 향상을 위해 낮춤 - 1.9.7 최적값)
            MIN_CONF_THRESHOLD = 0.05  # boxes에 추가할 최소 신뢰도 (5%)
            WEARING_CONF_THRESHOLD = 0.30  # 착용 판정 신뢰도 (30%) - 흰색 헬멧 감지 개선

            # 착용/미착용 신뢰도 추적 (충돌 해결용)
            helmet_conf = 0.0
            no_helmet_conf = 0.0
            vest_conf = 0.0
            no_vest_conf = 0.0

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy()

                    # 좌표를 원본 이미지 크기로 복원
                    if inv_scale != 1.0:
                        xyxy = xyxy * inv_scale

                    # 클래스 이름 확인 (디버그용)
                    cls_name = self.ppe_class_names.get(cls, f"unknown_{cls}")

                    # 신뢰도 5% 이상인 모든 객체 저장
                    if conf >= MIN_CONF_THRESHOLD:
                        ppe_detections['boxes'].append({
                            'class': cls,
                            'class_name': cls_name,
                            'confidence': conf,
                            'bbox': xyxy.tolist()
                        })

                        # 미착용 클래스 감지 (사람이 있다는 증거)
                        # 미착용 클래스가 감지되면 person 영역도 추정
                        if cls == self.ppe_no_classes.get('helmet', -1):
                            ppe_detections['no_helmet'] = True
                            no_helmet_conf = max(no_helmet_conf, conf)  # 최고 신뢰도 추적
                            if ppe_detections['person'] is None:
                                ppe_detections['person'] = xyxy.tolist()
                        elif cls == self.ppe_no_classes.get('vest', -1):
                            no_vest_conf = max(no_vest_conf, conf)  # 최고 신뢰도 추적
                        elif cls == self.ppe_no_classes.get('gloves', -1):
                            ppe_detections['no_gloves'] = True
                        elif cls == self.ppe_no_classes.get('glasses', -1):
                            ppe_detections['no_glasses'] = True
                        elif cls == self.ppe_no_classes.get('boots', -1):
                            ppe_detections['no_boots'] = True
                        elif cls == self.ppe_no_classes.get('mask', -1):
                            ppe_detections['no_mask'] = True

                        # 착용 여부 업데이트 (더 높은 신뢰도 요구)
                        if conf >= WEARING_CONF_THRESHOLD:
                            if cls == self.ppe_classes.get('helmet', -1):
                                helmet_conf = max(helmet_conf, conf)  # 최고 신뢰도 추적
                                # 헬멧 색상 감지 (bbox의 상단 60%만 사용하여 조끼 색상 혼입 방지)
                                helmet_bbox = xyxy.copy()
                                helmet_height = helmet_bbox[3] - helmet_bbox[1]
                                helmet_bbox[3] = helmet_bbox[1] + helmet_height * 0.6  # 상단 60%만
                                color_info = self._detect_color(frame, helmet_bbox)
                                if color_info:
                                    ppe_detections['helmet_color'] = color_info
                                    # 헬멧 bbox 저장 (디버깅용)
                                    ppe_detections['helmet_bbox'] = xyxy.tolist()
                            elif cls == self.ppe_classes.get('vest', -1):
                                vest_conf = max(vest_conf, conf)  # 최고 신뢰도 추적
                                ppe_detections['vest'] = True
                                # 조끼 색상 감지
                                color_info = self._detect_color(frame, xyxy)
                                if color_info:
                                    ppe_detections['vest_color'] = color_info
                            elif cls == self.ppe_classes.get('gloves', -1):
                                ppe_detections['gloves'] = True
                            elif cls == self.ppe_classes.get('boots', -1):
                                ppe_detections['boots'] = True
                            elif cls == self.ppe_classes.get('glasses', -1):
                                ppe_detections['glasses'] = True
                            elif cls == self.ppe_classes.get('mask', -1):
                                ppe_detections['mask'] = True

                        # person 클래스 감지 (신뢰도 무관하게 저장)
                        if cls == self.person_class_id and ppe_detections['person'] is None:
                            ppe_detections['person'] = xyxy.tolist()
                    elif conf > 0.02:
                        low_conf_count += 1
                    else:
                        very_low_conf_count += 1

            # 디버그 카운터 초기화 (충돌 해결 로직에서도 사용)
            if not hasattr(self, '_yolo_debug_count'):
                self._yolo_debug_count = 0
            self._yolo_debug_count += 1

            # 착용/미착용 충돌 해결: 인식률 향상을 위해 임계값 완화
            # 안정화 로직(3프레임 중 2회)이 오탐을 필터링하므로 임계값 낮춤
            #
            # helmet 판정 기준:
            # - helmet + no_helmet 둘 다 감지: helmet > no_helmet이면 착용
            # - helmet만 감지: helmet >= 0.3이면 착용
            # - no_helmet만 감지 또는 아무것도 없음: 미착용

            if helmet_conf > 0 and no_helmet_conf > 0:
                # 둘 다 감지: helmet이 더 높으면 착용
                if helmet_conf > no_helmet_conf:
                    ppe_detections['helmet'] = True
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[PPE] 헬멧 착용 확인: helmet={helmet_conf:.2f} > no_helmet={no_helmet_conf:.2f}")
                else:
                    ppe_detections['helmet'] = False
                    ppe_detections['helmet_color'] = None
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[PPE] 헬멧 미착용: helmet={helmet_conf:.2f} <= no_helmet={no_helmet_conf:.2f}")
            elif helmet_conf > 0:
                # helmet만 감지: 30% 이상이면 착용 (안정화 로직이 오탐 필터링)
                if helmet_conf >= 0.3:
                    ppe_detections['helmet'] = True
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[PPE] 헬멧 착용: helmet={helmet_conf:.2f}")
                else:
                    ppe_detections['helmet'] = False
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[PPE] 헬멧 신뢰도 부족: helmet={helmet_conf:.2f} < 0.3")
            elif no_helmet_conf > 0:
                ppe_detections['helmet'] = False
            # else: 아무것도 감지 안됨 - 기본값 False 유지

            # vest 판정: 동일한 완화된 기준 적용
            if vest_conf > 0 and no_vest_conf > 0:
                if vest_conf > no_vest_conf:
                    ppe_detections['vest'] = True
                else:
                    ppe_detections['vest'] = False
                    ppe_detections['vest_color'] = None
            elif vest_conf > 0:
                if vest_conf >= 0.3:
                    ppe_detections['vest'] = True
                else:
                    ppe_detections['vest'] = False
            elif no_vest_conf > 0:
                ppe_detections['vest'] = False

            # 디버그: 감지된 모든 객체 출력 (30프레임마다 = 약 1초)

            if self._yolo_debug_count % 30 == 1:  # 약 1초마다
                orig_h, orig_w = frame.shape[:2] if frame is not None else (0, 0)
                resized_h, resized_w = resized_frame.shape[:2]
                print(f"[YOLO 디버그] 원본: {orig_w}x{orig_h}, 추론: {resized_w}x{resized_h}, imgsz={inference_size}")

                # 모든 감지 결과 출력 (신뢰도 1% 이상)
                all_detections = []
                for result in results:
                    for box in result.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        if conf >= 0.01:  # 1% 이상 모두 출력
                            cls_name = self.ppe_class_names.get(cls, f"cls_{cls}")
                            all_detections.append((cls_name, f"{conf:.2f}"))

                if all_detections:
                    print(f"[YOLO 디버그] 전체 감지 (conf>=1%): {all_detections}")

                if ppe_detections['boxes']:
                    detected_items = [(b.get('class_name', 'unknown'), f"{b.get('confidence', 0):.2f}") for b in ppe_detections['boxes']]
                    print(f"[YOLO 디버그] 유효 감지 (conf>={MIN_CONF_THRESHOLD}): {detected_items}")
                    # 착용 상태
                    wearing = f"helmet={ppe_detections['helmet']}, glasses={ppe_detections['glasses']}, gloves={ppe_detections['gloves']}, boots={ppe_detections['boots']}, mask={ppe_detections['mask']}"
                    # 미착용 상태 (사람 존재 증거)
                    not_wearing = f"no_helmet={ppe_detections.get('no_helmet', False)}, no_glasses={ppe_detections.get('no_glasses', False)}, no_gloves={ppe_detections.get('no_gloves', False)}, no_boots={ppe_detections.get('no_boots', False)}, no_mask={ppe_detections.get('no_mask', False)}"
                    print(f"[YOLO 디버그] 착용: {wearing}")
                    print(f"[YOLO 디버그] 미착용: {not_wearing}")
                    # 색상 정보 출력
                    if ppe_detections.get('helmet_color'):
                        hc = ppe_detections['helmet_color']
                        print(f"[YOLO 디버그] 헬멧 색상: {hc['name_kr']} ({hc['name']}) RGB={hc['rgb']}")
                    if ppe_detections.get('vest_color'):
                        vc = ppe_detections['vest_color']
                        print(f"[YOLO 디버그] 조끼 색상: {vc['name_kr']} ({vc['name']}) RGB={vc['rgb']}")
                else:
                    # Raw 결과도 출력
                    total_boxes = sum(len(r.boxes) for r in results)
                    print(f"[YOLO 디버그] 유효 감지 없음, 총 boxes: {total_boxes}, 낮은 신뢰도: {low_conf_count}")

            # 보조 모델로 마스크/보안경/장갑 감지 (메인 모델에 해당 클래스가 없는 경우)
            # 보조 모델 클래스: {0: 'glove', 1: 'goggles', 2: 'helmet', 3: 'mask', 4: 'no_glove', 5: 'no_goggles', 6: 'no_helmet', 7: 'no_mask', 8: 'no_shoes', 9: 'shoes'}
            if self.has_mask_model and self.yolo_mask_model:
                try:
                    aux_results = self.yolo_mask_model(
                        resized_frame,
                        verbose=False,
                        conf=0.25,  # 보조 모델 신뢰도 (1.9.7 값)
                        iou=0.5,
                        imgsz=inference_size,
                        augment=False
                    )

                    # 보조 모델 클래스 ID 찾기
                    aux_classes = {
                        'mask': -1, 'no_mask': -1,
                        'goggles': -1, 'no_goggles': -1,
                        'glove': -1, 'no_glove': -1,
                        'shoes': -1, 'no_shoes': -1
                    }
                    if hasattr(self.yolo_mask_model, 'names'):
                        for cls_id, cls_name in self.yolo_mask_model.names.items():
                            name_lower = cls_name.lower().replace('-', '_')
                            if name_lower in aux_classes:
                                aux_classes[name_lower] = cls_id

                    # 보조 모델 감지 결과 처리
                    aux_detections = []
                    aux_all_detections = []  # 디버그용 전체 감지
                    for result in aux_results:
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            cls_name = self.yolo_mask_model.names.get(cls, f"cls_{cls}") if hasattr(self.yolo_mask_model, 'names') else f"cls_{cls}"

                            # 디버그: 15% 이상인 모든 감지 기록
                            if conf >= 0.15:
                                aux_all_detections.append((cls_name, f"{conf:.2f}"))

                            # 마스크
                            if cls == aux_classes['mask'] and conf >= 0.30 and not ppe_detections['mask']:
                                ppe_detections['mask'] = True
                                aux_detections.append(('mask', conf))
                            elif cls == aux_classes['no_mask'] and conf >= 0.30:
                                ppe_detections['no_mask'] = True

                            # 보안경 (goggles → glasses로 매핑)
                            if cls == aux_classes['goggles'] and conf >= 0.30 and not ppe_detections['glasses']:
                                ppe_detections['glasses'] = True
                                aux_detections.append(('goggles', conf))
                            elif cls == aux_classes['no_goggles'] and conf >= 0.30:
                                ppe_detections['no_glasses'] = True

                            # 장갑
                            if cls == aux_classes['glove'] and conf >= 0.30 and not ppe_detections['gloves']:
                                ppe_detections['gloves'] = True
                                aux_detections.append(('glove', conf))
                            elif cls == aux_classes['no_glove'] and conf >= 0.30:
                                ppe_detections['no_gloves'] = True

                            # 안전화 (shoes → boots로 매핑)
                            if cls == aux_classes['shoes'] and conf >= 0.30 and not ppe_detections['boots']:
                                ppe_detections['boots'] = True
                                aux_detections.append(('shoes', conf))
                            elif cls == aux_classes['no_shoes'] and conf >= 0.30:
                                ppe_detections['no_boots'] = True

                    # 디버그 출력 (30프레임마다)
                    if self._yolo_debug_count % 30 == 1:
                        if aux_all_detections:
                            print(f"[YOLO-Aux] 보조모델 전체 감지 (conf>=15%): {aux_all_detections}")
                        if aux_detections:
                            print(f"[YOLO-Aux] 보조모델 유효 감지 (conf>=30%): {aux_detections}")
                        else:
                            total_aux_boxes = sum(len(r.boxes) for r in aux_results)
                            print(f"[YOLO-Aux] 보조모델 유효 감지 없음, 총 boxes: {total_aux_boxes}")

                except Exception as aux_e:
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[YOLO-Aux] 보조모델 감지 오류: {aux_e}")

            # 사람 감지 보조 모델: PPE 모델이 person을 감지하지 못한 경우 기본 YOLO로 사람 전체 감지
            # PPE 모델은 헬멧/조끼 영역만 감지하므로 person_box가 작거나 없음
            if self.yolo_person_model and (ppe_detections['person'] is None or self._is_small_person_box(ppe_detections['person'], h, w)):
                try:
                    # IP카메라(고해상도)는 낮은 신뢰도로 더 많은 사람 감지
                    person_conf = 0.15 if inference_size >= 1280 else 0.3
                    person_results = self.yolo_person_model(
                        resized_frame,
                        verbose=False,
                        conf=person_conf,  # 사람 감지 신뢰도
                        iou=0.5,
                        imgsz=inference_size,
                        classes=[0],  # person 클래스만 감지 (COCO: 0=person)
                        augment=False
                    )

                    # 가장 큰 사람 박스 찾기
                    largest_person_box = None
                    largest_area = 0
                    for result in person_results:
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            if cls == 0 and conf >= 0.3:  # person class
                                xyxy = box.xyxy[0].cpu().numpy()
                                # 좌표를 원본 이미지 크기로 복원
                                if inv_scale != 1.0:
                                    xyxy = xyxy * inv_scale
                                area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
                                if area > largest_area:
                                    largest_area = area
                                    largest_person_box = xyxy.tolist()

                    if largest_person_box:
                        # 기존 person_box와 비교하여 더 큰 것 사용
                        if ppe_detections['person'] is None:
                            ppe_detections['person'] = largest_person_box
                            if self._yolo_debug_count % 30 == 1:
                                print(f"[YOLO-Person] 사람 감지 (기본 모델): {largest_person_box}")
                        else:
                            # 기존 박스와 새 박스 면적 비교
                            old_box = ppe_detections['person']
                            old_area = (old_box[2] - old_box[0]) * (old_box[3] - old_box[1])
                            if largest_area > old_area * 1.5:  # 50% 이상 크면 교체
                                ppe_detections['person'] = largest_person_box
                                if self._yolo_debug_count % 30 == 1:
                                    print(f"[YOLO-Person] 사람 박스 교체 (더 큰 박스): {old_area:.0f} → {largest_area:.0f}")

                except Exception as person_e:
                    if self._yolo_debug_count % 30 == 1:
                        print(f"[YOLO-Person] 사람 감지 오류: {person_e}")

            # === 인식 안정화: 히스토리 기반 필터링 ===
            ppe_detections = self._stabilize_ppe_results(ppe_detections)

            return ppe_detections

        except Exception as e:
            print(f"YOLOv11 PPE 감지 오류: {e}")
            return None

    def _calculate_iou(self, box1, box2):
        """
        두 박스의 IOU (Intersection over Union) 계산

        Args:
            box1, box2: [x1, y1, x2, y2] 형태의 박스

        Returns:
            float: IOU 값 (0~1)
        """
        if box1 is None or box2 is None:
            return 0.0

        try:
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])

            # 교집합 영역
            intersection = max(0, x2 - x1) * max(0, y2 - y1)

            # 각 박스의 넓이
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

            # 합집합 영역
            union = area1 + area2 - intersection

            if union <= 0:
                return 0.0

            return intersection / union
        except:
            return 0.0

    def _track_face(self, current_faces, recognized_faces):
        """
        얼굴 추적 - 감지되지 않아도 일정 프레임 동안 이전 결과 유지

        Args:
            current_faces: 현재 프레임에서 감지된 얼굴들
            recognized_faces: 인식된 얼굴 정보

        Returns:
            tuple: (추적된 얼굴들, 추적된 인식 정보)
        """
        # 현재 얼굴이 감지된 경우
        if current_faces and len(current_faces) > 0:
            # 가장 큰 얼굴 선택
            largest_face = None
            largest_area = 0
            for f in current_faces:
                if isinstance(f, dict) and 'bbox' in f:
                    bbox = f['bbox']
                elif isinstance(f, (list, tuple)) and len(f) >= 4:
                    bbox = f[:4]
                else:
                    continue

                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                if area > largest_area:
                    largest_area = area
                    largest_face = [int(x) for x in bbox]

            if largest_face:
                self._last_face_bbox = largest_face
                self._face_lost_frames = 0

                # 인식된 이름 업데이트
                if recognized_faces and len(recognized_faces) > 0:
                    for rf in recognized_faces:
                        if isinstance(rf, dict) and rf.get('name') and rf['name'] != 'Unknown':
                            self._last_face_name = rf['name']
                            break

            return current_faces, recognized_faces

        # 얼굴이 감지되지 않았지만 추적 중인 경우
        self._face_lost_frames += 1

        if self._last_face_bbox is not None and self._face_lost_frames <= self._face_tracking_threshold:
            # 이전 얼굴 위치 재사용 (추적 유지)
            tracked_face = {'bbox': self._last_face_bbox, 'tracked': True}
            tracked_recognized = []

            if self._last_face_name:
                tracked_recognized = [{
                    'name': self._last_face_name,
                    'location': self._last_face_bbox,
                    'confidence': 0.8,  # 추적 중 신뢰도
                    'tracked': True
                }]

            return [tracked_face], tracked_recognized

        # 추적 시간 초과 - 초기화
        if self._face_lost_frames > self._face_tracking_threshold:
            self._last_face_bbox = None
            self._last_face_name = None

        return [], []

    def _track_ppe(self, ppe_results):
        """
        PPE 추적 - 감지되지 않아도 일정 프레임 동안 이전 결과 유지

        Args:
            ppe_results: 현재 프레임 PPE 감지 결과

        Returns:
            dict: 추적 적용된 PPE 결과
        """
        if ppe_results is None:
            ppe_results = {}

        ppe_items = ['helmet', 'vest', 'gloves', 'glasses', 'mask', 'boots']

        for item in ppe_items:
            current_detected = ppe_results.get(item, False)

            if current_detected:
                # 현재 감지됨 - 추적 카운터 리셋
                self._ppe_lost_frames[item] = 0
            else:
                # 현재 미감지
                lost_count = self._ppe_lost_frames.get(item, 0) + 1
                self._ppe_lost_frames[item] = lost_count

                # 추적 임계값 내이고, 히스토리에서 최근에 감지된 적 있으면 유지
                if lost_count <= self._ppe_tracking_threshold:
                    # 히스토리 확인 - 최근 감지된 적 있으면 True 유지
                    history = self._ppe_history.get(item, [])
                    if history and any(history[-3:]):  # 최근 3프레임 중 하나라도 True
                        ppe_results[item] = True

        return ppe_results

    def _stabilize_ppe_results(self, ppe_detections):
        """
        PPE 감지 결과 안정화 - 히스토리 기반 필터링으로 들쭉날쭉한 인식 방지

        원리: 최근 N프레임의 결과를 저장하고, M번 이상 감지되어야 착용으로 판정
        """
        if ppe_detections is None:
            return self._last_stable_results

        ppe_items = ['helmet', 'vest', 'gloves', 'glasses', 'mask', 'boots']

        for item in ppe_items:
            # 현재 프레임 결과를 히스토리에 추가
            current_value = ppe_detections.get(item, False)
            self._ppe_history[item].append(current_value)

            # 히스토리 크기 제한
            if len(self._ppe_history[item]) > self._ppe_history_size:
                self._ppe_history[item].pop(0)

            # 안정화된 결과 계산: N프레임 중 M번 이상 True여야 착용으로 판정
            true_count = sum(self._ppe_history[item])
            stable_result = true_count >= self._ppe_stable_threshold

            # 안정화된 결과로 교체
            ppe_detections[item] = stable_result

        # 마지막 안정화된 결과 저장
        self._last_stable_results = ppe_detections.copy()

        return ppe_detections

    def detect_faces_with_insightface(self, frame, force_detect=False):
        """
        InsightFace로 얼굴 감지 및 특징 추출 (실시간 최적화)

        Args:
            frame: 입력 프레임 (BGR)
            force_detect: True면 스킵 프레임 무시하고 즉시 감지

        Returns:
            list: 얼굴 정보 리스트
        """
        if not self.use_insightface or self.face_app is None:
            return []

        if frame is None or not hasattr(frame, 'shape') or len(frame.shape) < 2:
            return []

        # === 스킵 프레임 제거: 실시간 처리 ===
        # 대신 이미지 크기를 극도로 축소하여 속도 확보

        try:
            h, w = frame.shape[:2]

            # === 해상도에 따른 적응형 다운스케일 ===
            # IP 카메라(고해상도)는 640px, 일반 웹캠은 480px 사용
            # 너무 작은 크기는 임베딩 품질 저하 유발
            if max(h, w) > 1500:
                # IP 카메라 (2304x1296 등 고해상도)
                max_size = 640
            elif max(h, w) > 1000:
                # Full HD 웹캠
                max_size = 480
            else:
                # 일반 웹캠 (720p 이하)
                max_size = 480

            scale = max_size / max(h, w)
            # 스케일이 1 이상이면 리사이즈 불필요
            if scale >= 1.0:
                resized_frame = frame
                scale = 1.0
            else:
                new_w = int(w * scale)
                new_h = int(h * scale)
                # INTER_AREA: 축소 시 가장 좋은 품질 (얼굴 디테일 보존)
                resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # RGB 변환
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

            # 얼굴 감지 및 분석 (스레드 안전성 확보)
            # InsightFace.get()은 스레드 안전하지 않으므로 락 필요
            with _shared_insightface_inference_lock:
                faces = self.face_app.get(rgb_frame)

            face_results = []
            for face in faces:
                bbox = face.bbox.astype(int)

                # 스케일 복원
                bbox = (bbox / scale).astype(int)

                face_results.append({
                    'bbox': bbox.tolist(),
                    'embedding': face.embedding,
                    'age': getattr(face, 'age', None),
                    'gender': getattr(face, 'gender', None),
                    'score': face.det_score
                })

            self._cached_face_results = face_results
            return face_results

        except Exception as e:
            return self._cached_face_results if self._cached_face_results else []

    def _get_cached_db_embeddings(self):
        """DB 임베딩 캐시 반환 (numpy 배열로 최적화)"""
        import time
        current_time = time.time()

        # 캐시가 없거나 만료됐으면 갱신
        if self._cached_db_embeddings is None or (current_time - self._db_cache_time) > self._db_cache_ttl:
            try:
                import sqlite3
                import pickle

                conn = sqlite3.connect(self.face_db.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT fe.face_id, fe.encoding, f.name, f.employee_id, f.department
                    FROM face_encodings fe
                    INNER JOIN faces f ON fe.face_id = f.id
                    WHERE f.is_active = 1
                ''')

                rows = cursor.fetchall()
                conn.close()

                if rows:
                    # numpy 배열로 변환 (배치 연산용)
                    embeddings_list = []
                    info_list = []
                    for row in rows:
                        emb = pickle.loads(row[1])
                        emb_norm = emb / np.linalg.norm(emb)
                        embeddings_list.append(emb_norm)
                        info_list.append({
                            'face_id': row[0],
                            'name': row[2],
                            'employee_id': row[3],
                            'department': row[4]
                        })

                    # 2D numpy 배열로 저장 (N x 512)
                    self._cached_db_embeddings = {
                        'embeddings': np.array(embeddings_list, dtype=np.float32),
                        'info': info_list
                    }
                else:
                    self._cached_db_embeddings = {'embeddings': None, 'info': []}

                self._db_cache_time = current_time

            except Exception as e:
                print(f"DB 캐시 로드 오류: {e}")
                self._cached_db_embeddings = {'embeddings': None, 'info': []}

        return self._cached_db_embeddings

    def recognize_faces_insightface(self, face_embeddings):
        """
        InsightFace 임베딩으로 얼굴 인식 (실시간 최적화)

        Args:
            face_embeddings: 얼굴 특징 벡터 리스트

        Returns:
            list: 인식된 얼굴 정보
        """
        if not self.face_recognition_enabled or self.face_db is None:
            return []

        if not face_embeddings:
            return self._cached_recognized_faces if self._cached_recognized_faces else []

        # 캐시된 DB 임베딩 사용
        db_cache = self._get_cached_db_embeddings()
        db_embeddings = db_cache.get('embeddings')
        db_info = db_cache.get('info', [])

        if db_embeddings is None or len(db_info) == 0:
            return []

        recognized_faces = []
        # 설정에서 tolerance 읽기 (기본값: 0.7, 범위: 0.5~0.9)
        # IP 카메라 등 고해상도 카메라에서는 더 높은 값 필요
        try:
            tolerance = float(self.config.env.get('face_recognition_tolerance', 0.7))
            tolerance = max(0.5, min(0.9, tolerance))  # 범위 제한
        except Exception:
            tolerance = 0.7

        # 디버그 카운터 (로그 빈도 제어)
        if not hasattr(self, '_face_recog_debug_count'):
            self._face_recog_debug_count = 0
        self._face_recog_debug_count += 1

        for face_data in face_embeddings:
            embedding = face_data['embedding']
            bbox = face_data['bbox']

            try:
                # 정규화
                emb_norm = embedding / np.linalg.norm(embedding)

                # === numpy 배치 연산으로 모든 DB와 한번에 비교 ===
                # (1 x 512) @ (512 x N) = (1 x N) 코사인 유사도
                similarities = np.dot(db_embeddings, emb_norm)
                best_idx = np.argmax(similarities)
                best_similarity = similarities[best_idx]
                best_distance = 1 - best_similarity

                # 디버그 로그 (30프레임마다)
                if self._face_recog_debug_count % 30 == 1:
                    best_name = db_info[best_idx]['name'] if best_idx < len(db_info) else 'N/A'
                    print(f"[얼굴인식] distance={best_distance:.3f}, similarity={best_similarity:.3f}, "
                          f"tolerance={tolerance}, 후보={best_name}, 결과={'인식' if best_distance <= tolerance else 'Unknown'}")

                if best_distance <= tolerance:
                    best_info = db_info[best_idx]
                    recognized_faces.append({
                        'name': best_info['name'],
                        'employee_id': best_info['employee_id'],
                        'department': best_info['department'],
                        'confidence': 1.0 - min(best_distance, 1.0),
                        'location': bbox,
                        'age': face_data.get('age'),
                        'gender': face_data.get('gender')
                    })

            except Exception as e:
                continue

        # 캐시 업데이트
        if recognized_faces:
            self._cached_recognized_faces = recognized_faces

        return recognized_faces

    def detect_face_only(self, frame):
        """
        얼굴 인식만 수행 (실시간 최적화, ~50ms)

        PPE 감지 없이 얼굴 감지와 인식만 수행합니다.

        Args:
            frame: 입력 프레임 (BGR)

        Returns:
            dict: {'faces': [...], 'recognized_faces': [...]}
        """
        if frame is None or not hasattr(frame, 'shape') or len(frame.shape) < 2:
            return {'faces': [], 'recognized_faces': []}

        try:
            # InsightFace로 얼굴 감지 + 임베딩
            face_results = self.detect_faces_with_insightface(frame)

            # DB와 비교하여 인식
            recognized_faces = self.recognize_faces_insightface(face_results)

            # bbox 형식 변환
            faces_list = []
            for f in face_results:
                if isinstance(f, dict) and 'bbox' in f:
                    faces_list.append(f['bbox'])

            return {
                'faces': faces_list,
                'recognized_faces': recognized_faces
            }
        except Exception as e:
            return {'faces': [], 'recognized_faces': []}

    def detect_objects_coco(self, frame, enabled_categories=None, confidence_threshold=0.5):
        """
        COCO 80 클래스 일반 사물 감지 (YOLO 기본 모델 사용)

        PPE 이외의 일반 사물(동물, 차량, 가구 등)을 감지합니다.

        Args:
            frame: 입력 프레임 (BGR)
            enabled_categories: 활성화된 카테고리 dict {'animals': True, 'vehicles': True, ...}
            confidence_threshold: 신뢰도 임계값 (기본 0.5)

        Returns:
            list: 감지된 사물 리스트 [{'class': str, 'class_kr': str, 'confidence': float, 'bbox': [x1,y1,x2,y2]}, ...]
        """
        if frame is None or not hasattr(frame, 'shape') or len(frame.shape) < 2:
            return []

        # IP 카메라 프레임 호환성: 연속 메모리 배열로 복사 (YOLO 호환성)
        # RTSP 스트림에서 읽은 프레임이 비연속 메모리일 수 있음
        if not frame.flags['C_CONTIGUOUS']:
            frame = np.ascontiguousarray(frame)

        # COCO 기본 모델 사용 (yolo_person_model은 yolo11m.pt로 COCO 80 클래스 지원)
        # PPE 전용 모델(yolo_model)은 COCO 클래스가 없으므로 사물 인식 불가
        coco_model = getattr(self, 'yolo_person_model', None)

        # 디버그: 모델 상태 확인 (최초 1회)
        if not hasattr(self, '_coco_model_checked'):
            self._coco_model_checked = True
            print(f"[COCO] yolo_person_model 상태: {coco_model is not None}")
            if coco_model:
                print(f"[COCO] 모델 클래스 수: {len(coco_model.names) if hasattr(coco_model, 'names') else 'N/A'}")

        if coco_model is None:
            # fallback: yolo_model이 COCO 모델인 경우 사용
            if hasattr(self, 'yolo_model') and self.yolo_model is not None:
                if hasattr(self.yolo_model, 'names') and len(self.yolo_model.names) >= 80:
                    coco_model = self.yolo_model

        if coco_model is None:
            return []

        # COCO 클래스 카테고리 매핑
        coco_categories = {
            'animals': {
                'bird': '새', 'cat': '고양이', 'dog': '개', 'horse': '말',
                'sheep': '양', 'cow': '소', 'elephant': '코끼리', 'bear': '곰',
                'zebra': '얼룩말', 'giraffe': '기린'
            },
            'vehicles': {
                'bicycle': '자전거', 'car': '자동차', 'motorcycle': '오토바이',
                'airplane': '비행기', 'bus': '버스', 'train': '기차',
                'truck': '트럭', 'boat': '보트'
            },
            'furniture': {
                'chair': '의자', 'couch': '소파', 'bed': '침대',
                'dining table': '식탁', 'toilet': '변기'
            },
            'electronics': {
                'tv': 'TV', 'laptop': '노트북', 'cell phone': '휴대폰',
                'keyboard': '키보드', 'mouse': '마우스', 'remote': '리모컨'
            },
            'food': {
                'banana': '바나나', 'apple': '사과', 'sandwich': '샌드위치',
                'orange': '오렌지', 'pizza': '피자', 'donut': '도넛', 'cake': '케이크'
            },
            'sports': {
                'sports ball': '공', 'baseball bat': '야구배트',
                'tennis racket': '테니스라켓', 'skateboard': '스케이트보드',
                'surfboard': '서핑보드', 'frisbee': '원반'
            },
            'accessories': {
                'backpack': '백팩', 'umbrella': '우산', 'handbag': '핸드백',
                'suitcase': '여행가방', 'tie': '넥타이'
            },
            'kitchen': {
                'bottle': '병', 'cup': '컵', 'fork': '포크',
                'knife': '나이프', 'spoon': '숟가락', 'bowl': '그릇'
            }
        }

        # 활성화된 클래스 목록 생성
        enabled_classes = set()
        all_category_classes = set()  # 모든 카테고리에 정의된 클래스
        for cat_classes in coco_categories.values():
            all_category_classes.update(cat_classes.keys())

        if enabled_categories is None:
            # 모든 카테고리 활성화
            enabled_classes = all_category_classes.copy()
        else:
            for cat_name, is_enabled in enabled_categories.items():
                if is_enabled and cat_name in coco_categories:
                    enabled_classes.update(coco_categories[cat_name].keys())

        # 클래스 이름 -> 한글 매핑
        class_to_korean = {}
        for cat_classes in coco_categories.values():
            class_to_korean.update(cat_classes)

        try:
            # 디버그: 프레임 정보 (최초 1회)
            if not hasattr(self, '_coco_frame_checked'):
                self._coco_frame_checked = True
                print(f"[COCO] 입력 프레임: {frame.shape}, dtype={frame.dtype}")
                # 프레임 픽셀 값 확인 (검은 화면인지 체크)
                import numpy as np
                mean_val = np.mean(frame)
                min_val = np.min(frame)
                max_val = np.max(frame)
                print(f"[COCO] 프레임 픽셀: mean={mean_val:.1f}, min={min_val}, max={max_val}")
                # 채널별 평균 확인 (BGR vs RGB 구분용)
                b_mean = np.mean(frame[:,:,0])
                g_mean = np.mean(frame[:,:,1])
                r_mean = np.mean(frame[:,:,2])
                print(f"[COCO] 채널 평균: B={b_mean:.1f}, G={g_mean:.1f}, R={r_mean:.1f}")

                # 디버그: 프레임을 파일로 저장하여 실제 내용 확인
                try:
                    debug_path = "/tmp/coco_debug_frame.jpg"
                    cv2.imwrite(debug_path, frame)
                    print(f"[COCO] 디버그 프레임 저장: {debug_path}")
                except Exception as save_err:
                    print(f"[COCO] 디버그 프레임 저장 실패: {save_err}")

            # YOLO 추론 (COCO 80 클래스 모델 사용)
            # IP 카메라 고해상도 프레임 처리
            h, w = frame.shape[:2]

            # IP 카메라 고해상도 처리 최적화
            # 초고해상도(2K 이상)는 리사이즈 후 추론
            inference_frame = frame
            if max(h, w) > 1920:
                # 1920 기준으로 비율 유지 리사이즈
                scale = 1920 / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                inference_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                if not hasattr(self, '_coco_resize_logged'):
                    self._coco_resize_logged = True
                    print(f"[COCO] 고해상도 리사이즈: {w}x{h} -> {new_w}x{new_h}")

            # imgsz 설정 - 테스트 결과 imgsz=640이 가장 좋은 감지율을 보여줌
            # IP 카메라 2304x1296에서 imgsz=640: 33개 감지 vs imgsz=2304: 28개 감지
            # YOLO는 내부적으로 최적화된 리사이즈를 수행하므로 작은 imgsz가 효율적
            ih, iw = inference_frame.shape[:2]
            if max(h, w) > 1920:  # IP 카메라 고해상도
                # v1.9.8.3-1: 테스트 결과 imgsz=640이 최적 (더 많은 객체 감지)
                imgsz = 640
            elif max(ih, iw) > 1000:
                imgsz = 1280
            else:
                imgsz = 640

            # 원본 프레임 사용 (YOLO 내부에서 최적화된 리사이즈 수행)
            use_frame = frame

            results = coco_model(use_frame, verbose=False, conf=confidence_threshold, imgsz=imgsz)

            detected_objects = []
            all_detections = []  # 디버그용

            # 디버그: 결과 구조 확인 (최초 1회)
            if not hasattr(self, '_coco_result_checked'):
                self._coco_result_checked = True
                is_high_res = max(h, w) > 1920
                print(f"[COCO] 추론 설정: imgsz={imgsz}, conf={confidence_threshold}, high_res={is_high_res}")
                print(f"[COCO] 원본 프레임: {w}x{h}")
                print(f"[COCO] 추론 결과: results={len(results) if results else 0}개")
                if results and len(results) > 0:
                    result = results[0]
                    boxes_count = len(result.boxes) if hasattr(result, 'boxes') and result.boxes is not None else 0
                    print(f"[COCO] 첫 번째 결과: boxes={boxes_count}개")

                    # 더 낮은 conf로 다시 시도하여 감지되는지 확인
                    if boxes_count == 0:
                        test_results = coco_model(use_frame, verbose=False, conf=0.01, imgsz=imgsz)
                        if test_results and len(test_results) > 0:
                            test_boxes = len(test_results[0].boxes) if test_results[0].boxes is not None else 0
                            print(f"[COCO] conf=0.01 테스트: {test_boxes}개 감지됨")
                            if test_boxes > 0:
                                # 상위 5개 클래스 출력
                                for i in range(min(5, test_boxes)):
                                    cls_id = int(test_results[0].boxes.cls[i].item())
                                    conf_val = float(test_results[0].boxes.conf[i].item())
                                    cls_name = coco_model.names.get(cls_id, f"id_{cls_id}")
                                    print(f"[COCO] 테스트 감지: {cls_name} (conf={conf_val:.3f})")

            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    for i in range(len(boxes)):
                        cls_id = int(boxes.cls[i].item())
                        conf = float(boxes.conf[i].item())
                        xyxy = boxes.xyxy[i].cpu().numpy()

                        # 클래스 이름 가져오기
                        if hasattr(coco_model, 'names') and cls_id in coco_model.names:
                            class_name = coco_model.names[cls_id]
                        else:
                            continue

                        # 디버그: 모든 감지 기록
                        all_detections.append((class_name, f"{conf:.2f}"))

                        # 사람(person) 제외
                        if class_name == 'person':
                            continue

                        # 활성화된 카테고리에 정의된 클래스만 필터링
                        # 카테고리에 정의되지 않은 COCO 클래스는 기타로 표시 (umbrella, book 등)
                        if class_name in all_category_classes:
                            # 정의된 클래스 중 활성화된 것만
                            if class_name not in enabled_classes:
                                continue
                            class_kr = class_to_korean.get(class_name, class_name)
                        else:
                            # 카테고리에 정의되지 않은 COCO 클래스 (기타)
                            # 기타 카테고리로 처리 (기본 활성화)
                            class_kr = class_name  # 영어 이름 그대로 사용

                        detected_objects.append({
                            'class': class_name,
                            'class_kr': class_kr,
                            'confidence': conf,
                            'bbox': [int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])]
                        })

            # 디버그 로그 (30번마다)
            if not hasattr(self, '_coco_call_count'):
                self._coco_call_count = 0
            self._coco_call_count += 1
            if self._coco_call_count % 30 == 1:
                print(f"[COCO] 호출 #{self._coco_call_count}: 전체감지={len(all_detections)}, 필터후={len(detected_objects)}, conf={confidence_threshold}")
                if all_detections[:5]:
                    print(f"[COCO] 상위5개: {all_detections[:5]}")

                # 감지 결과가 적을 때 낮은 conf로 테스트 (100번마다)
                if self._coco_call_count % 100 == 1 and len(all_detections) <= 1:
                    try:
                        test_results = coco_model(use_frame, verbose=False, conf=0.05, imgsz=imgsz)
                        if test_results and len(test_results) > 0 and test_results[0].boxes is not None:
                            test_boxes = test_results[0].boxes
                            test_count = len(test_boxes)
                            if test_count > 0:
                                test_detections = []
                                for i in range(min(10, test_count)):
                                    cls_id = int(test_boxes.cls[i].item())
                                    conf_val = float(test_boxes.conf[i].item())
                                    cls_name = coco_model.names.get(cls_id, f"id_{cls_id}")
                                    test_detections.append(f"{cls_name}:{conf_val:.2f}")
                                print(f"[COCO] conf=0.05 테스트: {test_count}개 감지 - {test_detections}")
                    except Exception as e:
                        print(f"[COCO] 테스트 오류: {e}")

            return detected_objects

        except Exception as e:
            if hasattr(self, '_coco_debug_count'):
                self._coco_debug_count += 1
            else:
                self._coco_debug_count = 1
            if self._coco_debug_count % 30 == 1:
                print(f"[COCO] 사물 감지 오류: {e}")
            return []

    def detect_all(self, frame):
        """
        전체 안전장구 감지 수행 (v2.0)

        Args:
            frame: 입력 프레임 (BGR)

        Returns:
            dict: 감지 결과
        """
        # frame이 None이거나 유효하지 않으면 None 반환
        if frame is None or not hasattr(frame, 'shape') or len(frame.shape) < 2:
            return None

        # === 프레임 스킵 최적화 (성능 향상) ===
        self._frame_count += 1

        # N프레임마다만 전체 감지 수행, 나머지는 캐시된 결과 반환
        if self._frame_count % self._detection_interval != 0:
            if self._last_stable_results is not None:
                # 캐시된 결과에 현재 프레임 정보만 업데이트
                return self.last_results
            # 캐시가 없으면 감지 수행

        try:
            # YOLOv11로 PPE 감지
            ppe_results = None
            if self.use_yolo:
                ppe_results = self.detect_ppe_with_yolo(frame)

            # InsightFace로 얼굴 감지 (먼저 실행하여 face_bbox 확보)
            if self.use_insightface:
                face_results = self.detect_faces_with_insightface(frame)
                recognized_faces = self.recognize_faces_insightface(face_results)
            else:
                face_results = []
                recognized_faces = []

            # 기존 방식 백업 (InsightFace 실패 시)
            if not face_results and not recognized_faces:
                legacy_faces, legacy_names = self._detect_faces_legacy(frame)
                # Legacy 결과를 InsightFace 형식으로 변환
                face_results = [{'bbox': list(f)} for f in legacy_faces]
                recognized_faces = [{'name': n, 'location': list(f)} for f, n in zip(legacy_faces, legacy_names)]

            # === 얼굴 추적 적용 (감지 안 되어도 일정 프레임 유지) ===
            face_results, recognized_faces = self._track_face(face_results, recognized_faces)

            # 얼굴 bbox 추출 (1명만 존재한다고 가정 - 가장 큰 얼굴 선택)
            face_bbox = None
            if face_results:
                # 가장 큰 얼굴 선택 (1명만 존재)
                largest_face = None
                largest_area = 0
                for f in face_results:
                    if isinstance(f, dict) and 'bbox' in f:
                        bbox = f['bbox']
                        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                        if area > largest_area:
                            largest_area = area
                            largest_face = bbox
                face_bbox = largest_face

            # PPE 전용 모델이 아니면 Legacy 방식으로 안전장구 감지 (항상 실행)
            # YOLO 기본 모델은 person만 감지하므로 헬멧/조끼는 Legacy로 감지
            if not self.has_ppe_model:
                legacy_ppe = self._detect_ppe_legacy(frame, face_bbox)
                if ppe_results:
                    # YOLO person + Legacy PPE 결합
                    ppe_results['helmet'] = legacy_ppe.get('helmet', False)
                    ppe_results['helmet_color'] = legacy_ppe.get('helmet_color')  # 헬멧 색상
                    ppe_results['vest'] = legacy_ppe.get('vest', False)
                    ppe_results['vest_color'] = legacy_ppe.get('vest_color')  # 조끼 색상
                    ppe_results['glasses'] = legacy_ppe.get('glasses', False)
                    ppe_results['gloves'] = legacy_ppe.get('gloves', False)
                    ppe_results['boots'] = legacy_ppe.get('boots', False)
                    # person이 없으면 legacy에서 가져오기
                    if not ppe_results.get('person'):
                        ppe_results['person'] = legacy_ppe.get('person')
                else:
                    ppe_results = legacy_ppe
            else:
                # PPE 모델이 있어도 조끼/헬멧 색상이 없으면 Legacy 방식으로 보완
                # - vest가 모델에 없는 경우
                # - YOLO가 vest를 감지하지 못한 경우 (vest_color가 None)
                # - YOLO가 helmet을 감지하지 못한 경우 (helmet_color가 None)
                need_legacy = False
                if ppe_results:
                    if 'vest' not in self.ppe_classes:
                        need_legacy = True
                    elif not ppe_results.get('vest_color'):
                        # vest가 모델에 있지만 감지되지 않음 → Legacy로 색상 보완
                        need_legacy = True

                if need_legacy and ppe_results:
                    legacy_ppe = self._detect_ppe_legacy(frame, face_bbox)
                    # vest 색상이 없으면 Legacy에서 가져오기
                    if not ppe_results.get('vest_color'):
                        ppe_results['vest_color'] = legacy_ppe.get('vest_color')
                        # Legacy는 vest=True로 설정되어 있음 (상의 색상 표시용)
                    # 헬멧 색상도 Legacy에서 가져오기 (YOLO에서 색상 정보가 없는 경우)
                    if not ppe_results.get('helmet_color'):
                        ppe_results['helmet_color'] = legacy_ppe.get('helmet_color')

            # 기존 방식 백업 (YOLO 실패 시)
            if not ppe_results:
                ppe_results = self._detect_ppe_legacy(frame, face_bbox)

            # === PPE 추적 적용 (감지 안 되어도 일정 프레임 유지) ===
            ppe_results = self._track_ppe(ppe_results)

            # === PPE 인식 안정화 적용 (히스토리 기반 필터링) ===
            ppe_results = self._stabilize_ppe_results(ppe_results)

            # 결과 통합
            # face_results 형식 통일: InsightFace와 Legacy 모두 [{'bbox': [x1,y1,x2,y2]}, ...] 형태
            faces_list = []
            for f in face_results:
                if isinstance(f, dict) and 'bbox' in f:
                    faces_list.append([int(x) for x in f['bbox']])
                elif isinstance(f, (list, tuple)) and len(f) >= 4:
                    faces_list.append([int(x) for x in f[:4]])

            results = {
                'timestamp': datetime.now().isoformat(),
                'person_detected': ppe_results.get('person') is not None if ppe_results else False,
                'person_box': ppe_results.get('person') if ppe_results else None,
                'faces': faces_list,
                'recognized_faces': recognized_faces,
                'hard_hat': {
                    'wearing': ppe_results.get('helmet', False) if ppe_results else False,
                    'color': ppe_results.get('helmet_color') if ppe_results else None
                },
                'safety_vest': {
                    'wearing': ppe_results.get('vest', False) if ppe_results else False,
                    'color': ppe_results.get('vest_color') if ppe_results else None
                },
                'mask': {'wearing': ppe_results.get('mask', False) if ppe_results else False},
                'safety_glasses': {'wearing': ppe_results.get('glasses', False) if ppe_results else False},
                'gloves': {'wearing': ppe_results.get('gloves', False) if ppe_results else False},
                'safety_shoes': {'wearing': ppe_results.get('boots', False) if ppe_results else False},
                'safety_score': 0,
                'detection_method': 'YOLOv11+InsightFace' if (self.use_yolo and self.use_insightface) else 'Legacy'
            }

            # 안전 점수 계산
            items = [
                results['hard_hat']['wearing'],
                results['safety_glasses']['wearing'],
                results['gloves']['wearing'],
                results['safety_shoes']['wearing']
            ]
            results['safety_score'] = int(sum(items) / len(items) * 100)

            self.last_results = results
            return results

        except Exception as e:
            print(f"안전장구 감지 오류: {e}")
            return None

    def _detect_ppe_legacy(self, frame, face_bbox=None):
        """
        기존 OpenCV 방식으로 PPE 감지 (백업)

        Args:
            frame: 입력 프레임
            face_bbox: 얼굴 바운딩 박스 [x1, y1, x2, y2] (있으면 이 기준으로 헬멧/조끼 감지)
        """
        result = {
            'helmet': False,
            'helmet_color': None,  # 헬멧 색상 정보
            'vest': True,  # 조끼는 무조건 True (상의 색상 표시용)
            'vest_color': None,  # 조끼(상의) 색상 정보
            'gloves': False,
            'boots': False,
            'glasses': False,
            'person': None
        }

        if frame is None:
            return result

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = frame.shape[:2]

            # 색상 정보 매핑 (공통 사용)
            color_info_map = {
                'orange': {'name': 'orange', 'name_kr': '주황', 'rgb': (255, 165, 0), 'hsv': (17, 255, 255)},
                'yellow': {'name': 'yellow', 'name_kr': '노랑', 'rgb': (255, 255, 0), 'hsv': (30, 255, 255)},
                'lime': {'name': 'lime', 'name_kr': '연두', 'rgb': (0, 255, 0), 'hsv': (55, 255, 255)},
                'green': {'name': 'green', 'name_kr': '녹색', 'rgb': (0, 128, 0), 'hsv': (85, 255, 128)},
                'blue': {'name': 'blue', 'name_kr': '파랑', 'rgb': (0, 0, 255), 'hsv': (120, 255, 255)},
                'white': {'name': 'white', 'name_kr': '흰색', 'rgb': (255, 255, 255), 'hsv': (0, 0, 255)},
                'gray': {'name': 'gray', 'name_kr': '회색', 'rgb': (128, 128, 128), 'hsv': (0, 0, 128)},
                'black': {'name': 'black', 'name_kr': '검정', 'rgb': (0, 0, 0), 'hsv': (0, 0, 0)},
                'red': {'name': 'red', 'name_kr': '빨강', 'rgb': (255, 0, 0), 'hsv': (0, 255, 255)},
                'purple': {'name': 'purple', 'name_kr': '보라', 'rgb': (128, 0, 128), 'hsv': (140, 255, 128)},
                'pink': {'name': 'pink', 'name_kr': '분홍', 'rgb': (255, 192, 203), 'hsv': (160, 100, 255)},
                'brown': {'name': 'brown', 'name_kr': '갈색', 'rgb': (139, 69, 19), 'hsv': (15, 200, 139)}
            }

            # 얼굴 박스가 전달되면 그 기준으로 헬멧/조끼 감지
            if face_bbox is not None:
                fx1, fy1, fx2, fy2 = [int(x) for x in face_bbox]
                face_w = fx2 - fx1
                face_h = fy2 - fy1
                face_center_x = (fx1 + fx2) // 2

                # person 영역 설정 (얼굴 기준으로 상체 추정)
                person_x1 = max(0, face_center_x - face_w)
                person_x2 = min(w, face_center_x + face_w)
                person_y1 = fy1
                person_y2 = min(h, fy2 + face_h * 3)  # 얼굴 아래로 3배
                result['person'] = (person_x1, person_y1, person_x2, person_y2)

                # 헬멧 감지 (얼굴 바로 위 영역만)
                head_y1 = max(0, fy1 - face_h)  # 얼굴 위로 얼굴 높이만큼
                head_y2 = fy1  # 얼굴 시작점까지
                head_x1 = max(0, fx1 - face_w // 4)
                head_x2 = min(w, fx2 + face_w // 4)

                if head_y2 > head_y1 and head_x2 > head_x1:
                    head_region_color = frame[head_y1:head_y2, head_x1:head_x2]
                    head_region_gray = gray[head_y1:head_y2, head_x1:head_x2]

                    if head_region_gray.size > 0 and head_region_color.size > 0:
                        # 헬멧 감지 조건 (매우 엄격하게):
                        # 머리카락(검은색)은 평균 밝기 < 80, 흰색 헬멧은 > 180
                        avg_brightness = np.mean(head_region_gray)
                        # 매우 밝은 영역 비율 (헬멧은 대부분 밝음)
                        very_bright_ratio = np.sum(head_region_gray > 200) / head_region_gray.size
                        # 어두운 영역 비율 (머리카락은 대부분 어두움)
                        dark_ratio = np.sum(head_region_gray < 80) / head_region_gray.size

                        # HSV로 색상 분석
                        hsv_head = cv2.cvtColor(head_region_color, cv2.COLOR_BGR2HSV)
                        saturation_avg = np.mean(hsv_head[:, :, 1])
                        value_avg = np.mean(hsv_head[:, :, 2])  # 밝기

                        # 헬멧 조건 (매우 엄격):
                        # 1. 흰색/밝은 헬멧: 평균 밝기 > 150 AND 매우 밝은 영역 > 50% AND 어두운 영역 < 20%
                        # 2. 유채색 헬멧: 채도 > 100 AND 밝기 > 120 AND 어두운 영역 < 30%
                        is_bright_helmet = (avg_brightness > 150 and very_bright_ratio > 0.5 and dark_ratio < 0.2)
                        is_colored_helmet = (saturation_avg > 100 and value_avg > 120 and dark_ratio < 0.3)

                        is_helmet = is_bright_helmet or is_colored_helmet

                        if is_helmet:
                            result['helmet'] = True
                            # 헬멧 색상 분석
                            helmet_color = self._get_dominant_color(head_region_color)
                            if helmet_color:
                                result['helmet_color'] = color_info_map.get(helmet_color, color_info_map['white'])

                # 상의(조끼) 색상 감지 (얼굴 아래 영역)
                body_y1 = fy2  # 얼굴 끝
                body_y2 = min(h, fy2 + face_h * 2)  # 얼굴 아래로 2배
                body_x1 = max(0, face_center_x - face_w)
                body_x2 = min(w, face_center_x + face_w)

                if body_y2 > body_y1 and body_x2 > body_x1:
                    body_region = frame[body_y1:body_y2, body_x1:body_x2]
                    if body_region.size > 0:
                        body_color = self._get_dominant_color(body_region)
                        if body_color:
                            result['vest_color'] = color_info_map.get(body_color, color_info_map['gray'])

            else:
                # 얼굴 박스가 없으면 기존 방식 (상체 감지)
                if self.upper_body_cascade is not None:
                    bodies = self.upper_body_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=3, minSize=(60, 60)
                    )
                    if len(bodies) > 0:
                        # 가장 큰 상체 선택 (1명만 존재한다고 가정)
                        largest = max(bodies, key=lambda b: b[2] * b[3])
                        x, y, bw, bh = largest
                        result['person'] = (x, y, x + bw, y + bh)

                        # 상의 색상 감지 (상체 영역)
                        body_region = frame[y:y + bh, x:x + bw]
                        if body_region.size > 0:
                            body_color = self._get_dominant_color(body_region)
                            if body_color:
                                result['vest_color'] = color_info_map.get(body_color, color_info_map['gray'])

            # 얼굴 감지로 안경 확인
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                if len(faces) > 0 and self.eye_cascade is not None:
                    # 가장 큰 얼굴만 확인 (1명만 존재)
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, fw, fh = largest_face
                    face_roi = gray[y:y + fh, x:x + fw]
                    eyes = self.eye_cascade.detectMultiScale(face_roi)
                    if len(eyes) == 0:
                        result['glasses'] = True

        except Exception as e:
            print(f"Legacy PPE 감지 오류: {e}")

        return result

    def _get_dominant_color(self, region):
        """
        영역의 주요(대표) 색상 반환

        Args:
            region: BGR 이미지 영역

        Returns:
            str: 색상 이름 (orange, yellow, lime, green, blue, white, gray, black, red, purple, pink, brown)
        """
        if region is None or region.size == 0:
            return None

        try:
            hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            total_pixels = region.size // 3  # BGR 3채널

            # 색상별 마스크 생성 (회색/흰색 구분 강화)
            # HSV: H(0-180), S(0-255), V(0-255)
            # 무채색: S가 낮음 (< 50), V로 밝기 구분
            # 유채색: S가 높음 (>= 50)
            masks = {
                'red': cv2.bitwise_or(
                    cv2.inRange(hsv, (0, 80, 80), (10, 255, 255)),
                    cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
                ),
                'orange': cv2.inRange(hsv, (10, 80, 80), (22, 255, 255)),
                'yellow': cv2.inRange(hsv, (22, 80, 80), (35, 255, 255)),
                'lime': cv2.inRange(hsv, (35, 80, 80), (55, 255, 255)),
                'green': cv2.inRange(hsv, (55, 80, 80), (85, 255, 255)),
                'blue': cv2.inRange(hsv, (85, 80, 80), (130, 255, 255)),
                'purple': cv2.inRange(hsv, (130, 80, 80), (150, 255, 255)),
                'pink': cv2.inRange(hsv, (150, 50, 80), (170, 255, 255)),
                'brown': cv2.inRange(hsv, (10, 80, 50), (22, 255, 150)),
                # 무채색: S < 50으로 구분, V로 밝기 결정
                'white': cv2.inRange(hsv, (0, 0, 220), (180, 50, 255)),   # 매우 밝음 (V >= 220)
                'gray': cv2.inRange(hsv, (0, 0, 70), (180, 50, 220)),     # 중간 밝기 (70 <= V < 220)
                'black': cv2.inRange(hsv, (0, 0, 0), (180, 50, 70))       # 어두움 (V < 70)
            }

            # 각 색상 비율 계산
            color_ratios = {}
            for color_name, mask in masks.items():
                ratio = np.sum(mask > 0) / total_pixels
                color_ratios[color_name] = ratio

            # 가장 많은 색상 반환
            max_color = max(color_ratios, key=color_ratios.get)
            return max_color

        except Exception as e:
            return None

    def _detect_faces_legacy(self, frame):
        """기존 OpenCV Haar Cascade 방식으로 얼굴 감지 (백업)"""
        face_locations = []
        face_names = []

        if frame is None or self.face_cascade is None:
            return face_locations, face_names

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            for (x, y, w, h) in faces:
                # OpenCV 형식 (x, y, w, h) -> (x1, y1, x2, y2)
                face_locations.append((x, y, x + w, y + h))
                face_names.append("Unknown")  # Haar Cascade는 인식 불가

        except Exception as e:
            print(f"Legacy 얼굴 감지 오류: {e}")

        return face_locations, face_names

    def draw_results(self, frame, results):
        """감지 결과 시각화"""
        if results is None:
            return frame

        display = frame.copy()

        # 사람 박스
        person_box = results.get('person_box')
        if person_box:
            x1, y1, x2, y2 = [int(x) for x in person_box]
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 얼굴 박스 및 인식 결과
        for face_info in results.get('recognized_faces', []):
            bbox = face_info.get('location', [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = [int(x) for x in bbox]
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 3)

                # 이름 및 정보 표시 (한글 지원) - Unknown은 표시하지 않음
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

                    # 한글 지원 텍스트 출력 (PIL 사용)
                    display = self._put_korean_text(display, text, (x1, y1 - 30), (0, 255, 0), 20)

        # PPE 상태 표시 제거 (v2.0) - 좌측 별도 패널에서 표시
        # 카메라 영상 위에 오버레이하지 않음

        return display

    def draw_results_on_frame(self, frame, results):
        """감지 결과를 프레임에 그리기 (draw_results의 별칭)"""
        return self.draw_results(frame, results)

    def draw_results_on_flipped(self, flipped_frame, results):
        """
        좌우 반전된 프레임에 감지 결과 그리기 (거울 모드용)

        Args:
            flipped_frame: 좌우 반전된 프레임
            results: 감지 결과 (원본 프레임 기준)

        Returns:
            결과가 그려진 반전 프레임
        """
        if results is None:
            return flipped_frame

        display = flipped_frame.copy()
        frame_width = display.shape[1]

        # 좌표 반전 함수
        def flip_x(x):
            return frame_width - x

        # 사람 박스 (좌우 반전)
        person_box = results.get('person_box')
        if person_box:
            x1, y1, x2, y2 = [int(x) for x in person_box]
            # 좌우 반전
            x1_flipped = flip_x(x2)
            x2_flipped = flip_x(x1)
            cv2.rectangle(display, (x1_flipped, y1), (x2_flipped, y2), (0, 255, 0), 2)

        # 얼굴 박스 및 인식 결과 (좌우 반전)
        for face_info in results.get('recognized_faces', []):
            bbox = face_info.get('location', [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = [int(x) for x in bbox]
                # 좌우 반전
                x1_flipped = flip_x(x2)
                x2_flipped = flip_x(x1)
                cv2.rectangle(display, (x1_flipped, y1), (x2_flipped, y2), (0, 255, 0), 3)

                # 이름 및 정보 표시 (한글 지원) - Unknown은 표시하지 않음
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

                    # 한글 지원 텍스트 출력 (PIL 사용)
                    display = self._put_korean_text(display, text, (x1_flipped, y1 - 30), (0, 255, 0), 20)

        # PPE 상태 표시 제거 (v2.0) - 좌측 별도 패널에서 표시
        # 카메라 영상 위에 오버레이하지 않음

        return display


# Backward compatibility alias
SafetyEquipmentDetector = SafetyEquipmentDetectorV2
