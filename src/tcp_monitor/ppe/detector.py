"""
PPE 감지 모듈
YOLOv10을 사용하여 사람과 PPE 장비를 감지합니다.

원본: ppe_detection/src/detector.py
GARAMe Manager 1.9.8.2 통합 버전 (GPU 자동 감지 지원)
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..utils.helpers import get_base_dir

# YOLO 모델 로드 시도
YOLO_AVAILABLE = False
CUDA_AVAILABLE = False
DEVICE = 'cpu'

try:
    import torch
    # PyTorch 2.6+ 호환성
    _original_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        kwargs.setdefault('weights_only', False)
        return _original_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load

    from ultralytics import YOLO
    YOLO_AVAILABLE = True

    # GPU 가용성 확인
    if torch.cuda.is_available():
        CUDA_AVAILABLE = True
        DEVICE = 'cuda'
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[PPE] GPU 감지: {gpu_name} (CUDA {torch.version.cuda})")
    else:
        print("[PPE] GPU 미감지 - CPU 모드로 실행")

except ImportError:
    print("[WARNING] ultralytics를 찾을 수 없습니다. PPE 감지가 비활성화됩니다.")

from .color_analyzer import ColorAnalyzer


@dataclass
class BoundingBox:
    """바운딩 박스 데이터 클래스"""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float = 0.0
    class_id: int = -1
    class_name: str = ""

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class PPEStatus:
    """PPE 착용 상태 데이터 클래스"""
    helmet: bool = False
    helmet_color: str = ""
    helmet_color_kr: str = ""
    helmet_bbox: Optional[BoundingBox] = None

    glasses: bool = False
    glasses_bbox: Optional[BoundingBox] = None

    mask: bool = False
    mask_bbox: Optional[BoundingBox] = None

    gloves: bool = False
    gloves_bbox: Optional[BoundingBox] = None
    gloves_left: bool = False
    gloves_left_bbox: Optional[BoundingBox] = None
    gloves_right: bool = False
    gloves_right_bbox: Optional[BoundingBox] = None
    gloves_count: int = 0

    vest: bool = False
    vest_color: str = ""
    vest_color_kr: str = ""
    vest_bbox: Optional[BoundingBox] = None

    boots: bool = False
    boots_bbox: Optional[BoundingBox] = None

    def get_status_dict(self) -> Dict[str, Dict]:
        """상태를 딕셔너리로 반환"""
        return {
            'helmet': {
                'detected': self.helmet,
                'color': self.helmet_color,
                'color_kr': self.helmet_color_kr,
            },
            'glasses': {'detected': self.glasses},
            'mask': {'detected': self.mask},
            'gloves': {
                'detected': self.gloves,
                'count': self.gloves_count,
                'left': self.gloves_left,
                'right': self.gloves_right,
            },
            'vest': {
                'detected': self.vest,
                'color': self.vest_color,
                'color_kr': self.vest_color_kr,
            },
            'boots': {'detected': self.boots}
        }

    def to_simple_dict(self) -> Dict[str, bool]:
        """단순 딕셔너리로 변환 (GARAMe Manager 호환)"""
        return {
            'helmet': self.helmet,
            'helmet_color': self.helmet_color_kr or self.helmet_color,
            'glasses': self.glasses,
            'mask': self.mask,
            'gloves': self.gloves,
            'vest': self.vest,
            'vest_color': self.vest_color_kr or self.vest_color,
            'boots': self.boots
        }

    def count_detected(self) -> int:
        """감지된 PPE 수 반환"""
        count = 0
        if self.helmet: count += 1
        if self.glasses: count += 1
        if self.mask: count += 1
        if self.gloves: count += 1
        if self.vest: count += 1
        if self.boots: count += 1
        return count

    def calculate_safety_rate(self, required_ppe: list = None) -> float:
        """
        안전률 계산

        가중치:
        - helmet: 40% (머리 보호 가장 중요)
        - vest: 25% (가시성 확보)
        - gloves: 15% (손 보호)
        - glasses: 10% (눈 보호)
        - mask: 5% (호흡 보호)
        - boots: 5% (발 보호)
        """
        weights = {
            'helmet': 40,
            'vest': 25,
            'gloves': 15,
            'glasses': 10,
            'mask': 5,
            'boots': 5
        }

        if required_ppe is None:
            required_ppe = ['helmet', 'vest', 'gloves', 'glasses', 'mask', 'boots']

        total_weight = sum(weights.get(ppe, 0) for ppe in required_ppe)
        if total_weight == 0:
            return 100.0

        score = 0
        ppe_status = {
            'helmet': self.helmet,
            'vest': self.vest,
            'gloves': self.gloves,
            'glasses': self.glasses,
            'mask': self.mask,
            'boots': self.boots
        }

        for ppe in required_ppe:
            if ppe_status.get(ppe, False):
                score += weights.get(ppe, 0)

        # 장갑 한손만 착용시 절반 점수
        if 'gloves' in required_ppe and self.gloves:
            if self.gloves_count == 1:
                score -= weights['gloves'] * 0.5

        return (score / total_weight) * 100


@dataclass
class PersonDetection:
    """사람 감지 결과 데이터 클래스"""
    bbox: BoundingBox
    ppe_status: PPEStatus = field(default_factory=PPEStatus)

    # 얼굴 인식 정보 (GARAMe Manager 호환)
    face_detected: bool = False
    face_name: str = ""
    face_user_id: str = ""
    face_department: str = ""
    face_confidence: float = 0.0
    face_bbox: Optional[Tuple[int, int, int, int]] = None


class PPEDetector:
    """PPE 감지 엔진 - YOLOv11/YOLOv10 기반 (SH17 17클래스 지원)"""

    # PPE 클래스 이름 매핑 (SH17 17클래스 + 기존 모델 호환)
    PPE_CLASSES = {
        # SH17 데이터셋 17클래스 (YOLOv11 학습 모델)
        'person': 'person',
        'head': 'head',
        'face': 'face',
        'glasses': 'glasses',
        'face-mask': 'mask',
        'face-guard': 'glasses',
        'ear': 'ear',
        'ear-mufs': 'ear_protection',
        'hands': 'hands',
        'gloves': 'gloves',
        'foot': 'foot',
        'shoes': 'boots',  # SH17에서는 shoes를 boots로 매핑 (YOLOv11 학습 후)
        'safety-vest': 'vest',
        'tools': 'tools',
        'helmet': 'helmet',
        'medical-suit': 'vest',
        'safety-suit': 'vest',
        # 기존 모델 호환성
        'Hardhat': 'helmet',
        'hard-hat': 'helmet',
        'Mask': 'mask',
        'Safety Vest': 'vest',
        'vest': 'vest',
        'Person': 'person',
        'Gloves': 'gloves',
        'boots': 'boots',
        'Boots': 'boots',
    }

    # Construction-PPE 모델 클래스 매핑 (boots 감지 전용)
    CONSTRUCTION_PPE_CLASSES = {
        'boots': 'boots',
        'no_boots': 'no_boots',  # 안전화 미착용
    }

    # Person 필터링 설정
    MIN_PERSON_RATIO = 0.08
    MIN_PERSON_HEIGHT_RATIO = 0.40
    MIN_PERSON_WIDTH_RATIO = 0.10

    # 싱글톤 인스턴스
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """싱글톤 인스턴스 리셋 (카메라 전환 시 재초기화용)"""
        cls._instance = None
        cls._initialized = False
        print("[PPE] PPEDetector 인스턴스 리셋됨")

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        color_analyzer: Optional[ColorAnalyzer] = None
    ):
        """
        PPE 감지기 초기화 (싱글톤)

        Args:
            model_path: YOLOv10 모델 경로 (없으면 자동 탐색)
            confidence_threshold: 감지 신뢰도 임계값
            iou_threshold: NMS IOU 임계값
            color_analyzer: 색상 분석기 인스턴스
        """
        if PPEDetector._initialized:
            return

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.color_analyzer = color_analyzer or ColorAnalyzer()
        self.model = None
        self.boots_model = None  # 안전화 감지 전용 모델
        self.class_names = {}
        self.boots_class_names = {}

        if not YOLO_AVAILABLE:
            print("[WARNING] YOLO 사용 불가 - PPE 감지 비활성화")
            PPEDetector._initialized = True
            return

        # 메인 모델 경로 탐색
        if model_path is None:
            model_path = self._find_model_path()

        if model_path and os.path.exists(model_path):
            try:
                print(f"[PPE] 메인 모델 로딩: {model_path}")
                self.model = YOLO(model_path)
                self.class_names = self.model.names
                print(f"[PPE] 메인 모델 로드 완료 - 클래스: {list(self.class_names.values())}")
            except Exception as e:
                print(f"[PPE] 메인 모델 로드 실패: {e}")
        else:
            print(f"[PPE] 메인 모델 파일을 찾을 수 없습니다: {model_path}")

        # 안전화 감지 모델 로드 (Construction-PPE)
        boots_model_path = self._find_boots_model_path()
        if boots_model_path and os.path.exists(boots_model_path):
            try:
                print(f"[PPE] 안전화 모델 로딩: {boots_model_path}")
                self.boots_model = YOLO(boots_model_path)
                self.boots_class_names = self.boots_model.names
                print(f"[PPE] 안전화 모델 로드 완료 - 클래스: {list(self.boots_class_names.values())}")
            except Exception as e:
                print(f"[PPE] 안전화 모델 로드 실패: {e}")
        else:
            print(f"[PPE] 안전화 모델 파일을 찾을 수 없습니다 (선택사항)")

        PPEDetector._initialized = True

    def _find_model_path(self) -> Optional[str]:
        """모델 경로 자동 탐색 (우선순위: YOLOv10 > YOLOv11 SH17)

        Note: SH17 학습 모델은 face-guard→glasses, medical-suit→vest 등
        오탐지 문제가 있어 YOLOv10 모델을 우선 사용
        """
        possible_paths = [
            # 기존 YOLOv10 모델 (안정적, 권장)
            'models/yolo10x.pt',
            './models/yolo10x.pt',
            '../models/yolo10x.pt',
            # YOLOv11 SH17 학습 모델 (오탐지 이슈 - 폴백용)
            # 'models/ppe-yolov11-sh17.pt',
            # './models/ppe-yolov11-sh17.pt',
            # '../models/ppe-yolov11-sh17.pt',
            'models/ppe_full.pt',
            'models/ppe_helmet_vest.pt',
        ]

        # 현재 파일 기준 경로
        base_dir = get_base_dir()
        for path in possible_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def _find_boots_model_path(self) -> Optional[str]:
        """안전화 모델 경로 자동 탐색"""
        possible_paths = [
            'models/construction-ppe.pt',
            './models/construction-ppe.pt',
            '../models/construction-ppe.pt',
        ]

        base_dir = get_base_dir()
        for path in possible_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def is_available(self) -> bool:
        """PPE 감지 가능 여부"""
        return self.model is not None

    def detect(self, frame: np.ndarray) -> List[PersonDetection]:
        """
        프레임에서 사람과 PPE 감지

        Args:
            frame: BGR 이미지

        Returns:
            PersonDetection 리스트
        """
        if frame is None or self.model is None:
            return []

        # IP 카메라 프레임 호환성: 연속 메모리 배열로 복사 (YOLO 호환성)
        # RTSP 스트림에서 읽은 프레임이 비연속 메모리일 수 있음
        if not frame.flags['C_CONTIGUOUS']:
            frame = np.ascontiguousarray(frame)

        h, w = frame.shape[:2]
        frame_area = h * w
        min_person_area = frame_area * self.MIN_PERSON_RATIO
        min_person_height = h * self.MIN_PERSON_HEIGHT_RATIO
        min_person_width = w * self.MIN_PERSON_WIDTH_RATIO

        detections = []
        persons = []
        ppe_items = []

        # YOLO 메인 모델 감지 수행
        try:
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=DEVICE,
                verbose=False
            )
        except Exception as e:
            print(f"[PPE] 감지 오류: {e}")
            return []

        # 메인 모델 결과 파싱
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.class_names.get(cls_id, str(cls_id))

                bbox = BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                    class_id=cls_id,
                    class_name=cls_name
                )

                normalized_name = self.PPE_CLASSES.get(cls_name, cls_name.lower())

                if normalized_name == 'person':
                    if (bbox.area >= min_person_area and
                        bbox.height >= min_person_height and
                        bbox.width >= min_person_width):
                        persons.append(bbox)
                elif normalized_name in ['helmet', 'glasses', 'mask', 'gloves', 'vest']:
                    ppe_items.append((normalized_name, bbox))

        # 안전화 모델로 boots 감지 (별도 모델)
        if self.boots_model is not None:
            try:
                boots_results = self.boots_model(
                    frame,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    device=DEVICE,
                    verbose=False
                )
                for result in boots_results:
                    boxes = result.boxes
                    if boxes is None:
                        continue

                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        cls_name = self.boots_class_names.get(cls_id, str(cls_id))

                        # boots 클래스만 처리 (no_boots는 무시)
                        if cls_name == 'boots':
                            bbox = BoundingBox(
                                x1=x1, y1=y1, x2=x2, y2=y2,
                                confidence=conf,
                                class_id=cls_id,
                                class_name=cls_name
                            )
                            ppe_items.append(('boots', bbox))
            except Exception as e:
                print(f"[PPE] 안전화 감지 오류: {e}")

        # 중복 Person 제거
        persons = self._remove_duplicate_persons(persons)

        # 사람별 PPE 매칭
        for person_bbox in persons:
            ppe_status = self._match_ppe_to_person(frame, person_bbox, ppe_items)
            detections.append(PersonDetection(bbox=person_bbox, ppe_status=ppe_status))

        # 사람 없이 PPE만 감지된 경우
        if not persons and ppe_items:
            virtual_person = BoundingBox(x1=0, y1=0, x2=w, y2=h, class_name='person')
            ppe_status = self._match_ppe_to_person(frame, virtual_person, ppe_items)
            detections.append(PersonDetection(bbox=virtual_person, ppe_status=ppe_status))

        return detections

    def detect_ppe_only(self, frame: np.ndarray) -> PPEStatus:
        """
        PPE만 감지 (사람 감지 없이) - GARAMe Manager 안전교육 화면용

        Args:
            frame: BGR 이미지

        Returns:
            PPEStatus
        """
        detections = self.detect(frame)
        if detections:
            return detections[0].ppe_status
        return PPEStatus()

    def _match_ppe_to_person(
        self,
        frame: np.ndarray,
        person_bbox: BoundingBox,
        ppe_items: List[Tuple[str, BoundingBox]]
    ) -> PPEStatus:
        """사람 영역에 PPE 매칭"""
        status = PPEStatus()

        # 사람 박스 확장 (장갑은 손에 있어서 박스 밖일 수 있음)
        expanded_person_bbox = BoundingBox(
            x1=max(0, person_bbox.x1 - person_bbox.width // 3),
            y1=person_bbox.y1,
            x2=min(frame.shape[1], person_bbox.x2 + person_bbox.width // 3),
            y2=person_bbox.y2
        )

        for ppe_type, ppe_bbox in ppe_items:
            cx, cy = ppe_bbox.center

            # 장갑과 부츠는 확장된 영역에서 찾기
            if ppe_type in ['gloves', 'boots']:
                if not self._is_inside(cx, cy, expanded_person_bbox):
                    continue
            else:
                if not self._is_inside(cx, cy, person_bbox):
                    continue

            if ppe_type == 'helmet' and not status.helmet:
                status.helmet = True
                status.helmet_bbox = ppe_bbox
                roi = self._extract_roi(frame, ppe_bbox)
                color, color_kr = self.color_analyzer.analyze(roi)
                status.helmet_color = color
                status.helmet_color_kr = color_kr

            elif ppe_type == 'glasses' and not status.glasses:
                status.glasses = True
                status.glasses_bbox = ppe_bbox

            elif ppe_type == 'mask' and not status.mask:
                status.mask = True
                status.mask_bbox = ppe_bbox

            elif ppe_type == 'gloves':
                person_center_x = (person_bbox.x1 + person_bbox.x2) // 2
                if cx < person_center_x:
                    if not status.gloves_left:
                        status.gloves_left = True
                        status.gloves_left_bbox = ppe_bbox
                        status.gloves_count += 1
                else:
                    if not status.gloves_right:
                        status.gloves_right = True
                        status.gloves_right_bbox = ppe_bbox
                        status.gloves_count += 1
                if status.gloves_left or status.gloves_right:
                    status.gloves = True
                    if status.gloves_bbox is None:
                        status.gloves_bbox = ppe_bbox

            elif ppe_type == 'vest' and not status.vest:
                status.vest = True
                status.vest_bbox = ppe_bbox
                roi = self._extract_roi(frame, ppe_bbox)
                color, color_kr = self.color_analyzer.analyze(roi)
                status.vest_color = color
                status.vest_color_kr = color_kr

            elif ppe_type == 'boots' and not status.boots:
                status.boots = True
                status.boots_bbox = ppe_bbox

        return status

    def _is_inside(self, x: int, y: int, bbox: BoundingBox) -> bool:
        """점이 바운딩 박스 내에 있는지 확인"""
        return bbox.x1 <= x <= bbox.x2 and bbox.y1 <= y <= bbox.y2

    def _extract_roi(self, frame: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """바운딩 박스 영역 추출"""
        h, w = frame.shape[:2]
        x1 = max(0, bbox.x1)
        y1 = max(0, bbox.y1)
        x2 = min(w, bbox.x2)
        y2 = min(h, bbox.y2)
        return frame[y1:y2, x1:x2]

    def _remove_duplicate_persons(self, persons: List[BoundingBox]) -> List[BoundingBox]:
        """중복 Person 박스 제거"""
        if len(persons) <= 1:
            return persons

        sorted_persons = sorted(persons, key=lambda b: b.area, reverse=True)
        filtered = []

        for bbox in sorted_persons:
            should_remove = False
            for kept in filtered:
                if self._is_contained_in(bbox, kept, threshold=0.5):
                    if bbox.area < kept.area * 0.4:
                        should_remove = True
                        break
                    iou = self._calculate_iou(bbox, kept)
                    if iou > 0.3:
                        should_remove = True
                        break
            if not should_remove:
                filtered.append(bbox)

        return filtered

    def _calculate_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        """IoU 계산"""
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = box1.area + box2.area - intersection

        return intersection / union if union > 0 else 0.0

    def _is_contained_in(self, small: BoundingBox, large: BoundingBox, threshold: float = 0.7) -> bool:
        """작은 박스가 큰 박스 안에 포함되어 있는지 확인"""
        x1 = max(small.x1, large.x1)
        y1 = max(small.y1, large.y1)
        x2 = min(small.x2, large.x2)
        y2 = min(small.y2, large.y2)

        if x2 <= x1 or y2 <= y1:
            return False

        intersection = (x2 - x1) * (y2 - y1)
        small_area = small.area

        if small_area == 0:
            return False

        return (intersection / small_area) >= threshold
