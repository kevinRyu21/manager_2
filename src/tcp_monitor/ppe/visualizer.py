"""
PPE 시각화 모듈
카메라 프레임에 PPE 감지 결과를 오버레이합니다.

원본: ppe_detection/src/visualizer.py
GARAMe Manager 1.9.7 통합 버전
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .detector import PersonDetection, PPEStatus, BoundingBox


class PPEVisualizer:
    """PPE 감지 결과 시각화 클래스"""

    # 기본 색상 (BGR)
    DEFAULT_COLORS = {
        'person': (255, 128, 0),
        'helmet': (0, 255, 0),
        'glasses': (0, 255, 255),
        'mask': (255, 0, 255),
        'gloves': (0, 165, 255),
        'vest': (0, 255, 128),
        'boots': (128, 0, 255),
        'detected': (0, 255, 0),
        'not_detected': (0, 0, 255)
    }

    # PPE 한글 이름
    PPE_NAMES_KR = {
        'helmet': '헬멧',
        'glasses': '보안경',
        'mask': '마스크',
        'gloves': '장갑',
        'vest': '조끼',
        'boots': '안전화'
    }

    def __init__(self, font_size: int = 20):
        """
        시각화 모듈 초기화

        Args:
            font_size: 한글 폰트 크기
        """
        self.colors = self.DEFAULT_COLORS.copy()
        self.font_size = font_size
        self._korean_font = None
        self._korean_font_loaded = False

    def _load_korean_font(self, size: int = None):
        """한글 폰트 로드"""
        if not PIL_AVAILABLE:
            return None

        if self._korean_font_loaded and self._korean_font is not None:
            return self._korean_font

        size = size or self.font_size
        font_paths = [
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
            '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'C:/Windows/Fonts/malgun.ttf',
            '/System/Library/Fonts/AppleGothic.ttf',
        ]

        for font_path in font_paths:
            try:
                self._korean_font = ImageFont.truetype(font_path, size)
                self._korean_font_loaded = True
                return self._korean_font
            except:
                continue

        try:
            self._korean_font = ImageFont.load_default()
        except:
            self._korean_font = None
        self._korean_font_loaded = True
        return self._korean_font

    def put_korean_text(
        self,
        frame: np.ndarray,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int] = (255, 255, 255),
        font_size: int = None
    ) -> np.ndarray:
        """
        OpenCV 프레임에 한글 텍스트 추가

        Args:
            frame: BGR 이미지
            text: 표시할 텍스트
            position: (x, y) 위치
            color: BGR 색상
            font_size: 폰트 크기

        Returns:
            텍스트가 추가된 프레임
        """
        if not PIL_AVAILABLE:
            # PIL 없으면 OpenCV 텍스트 사용
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            return frame

        try:
            font = self._load_korean_font(font_size or self.font_size)
            if font is None:
                cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                return frame

            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            # BGR -> RGB
            color_rgb = (color[2], color[1], color[0])
            draw.text(position, text, font=font, fill=color_rgb)
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            return frame

    def draw_ppe_status_overlay(
        self,
        frame: np.ndarray,
        ppe_status: PPEStatus,
        enabled_items: Dict[str, bool] = None,
        item_names: Dict[str, str] = None,
        position: str = 'top_left'
    ) -> np.ndarray:
        """
        프레임에 PPE 상태 오버레이 표시

        Args:
            frame: BGR 이미지
            ppe_status: PPE 상태
            enabled_items: 활성화된 항목 {'helmet': True, ...}
            item_names: 항목 표시명 {'helmet': '안전모', ...}
            position: 표시 위치 ('top_left', 'top_right', 'bottom_left', 'bottom_right')

        Returns:
            오버레이가 추가된 프레임
        """
        if enabled_items is None:
            enabled_items = {
                'helmet': True, 'glasses': True, 'mask': True,
                'gloves': True, 'vest': True, 'boots': True
            }

        if item_names is None:
            item_names = self.PPE_NAMES_KR.copy()

        # 활성화된 항목 수집
        active_items = []
        for key in ['helmet', 'vest', 'mask', 'glasses', 'gloves', 'boots']:
            if enabled_items.get(key, False):
                active_items.append(key)

        if not active_items:
            return frame

        h, w = frame.shape[:2]

        # 상태 표시 영역 크기 계산
        box_width = 220
        box_height = 40 + len(active_items) * 28

        # 위치 결정
        if position == 'top_left':
            start_x, start_y = 10, 10
        elif position == 'top_right':
            start_x, start_y = w - box_width - 10, 10
        elif position == 'bottom_left':
            start_x, start_y = 10, h - box_height - 10
        else:  # bottom_right
            start_x, start_y = w - box_width - 10, h - box_height - 10

        # 반투명 배경
        overlay = frame.copy()
        cv2.rectangle(overlay, (start_x, start_y),
                     (start_x + box_width, start_y + box_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # 제목
        frame = self.put_korean_text(frame, "안전장구 상태",
                                     (start_x + 5, start_y + 5), (255, 255, 255), 18)

        # 각 항목 표시
        y_offset = start_y + 38
        status_dict = ppe_status.get_status_dict()

        for key in active_items:
            info = status_dict.get(key, {})
            detected = info.get('detected', False)
            name = item_names.get(key, self.PPE_NAMES_KR.get(key, key))

            if detected:
                icon = "✓"
                text_color = self.colors['detected']
                status_text = "착용"
                # 색상 정보 추가
                if key == 'helmet' and info.get('color_kr'):
                    status_text += f" ({info['color_kr']})"
                elif key == 'vest' and info.get('color_kr'):
                    status_text += f" ({info['color_kr']})"
                elif key == 'gloves' and info.get('count', 0) > 0:
                    status_text += f" ({info['count']}개)"
            else:
                icon = "✗"
                text_color = self.colors['not_detected']
                status_text = "미착용"

            text = f"{icon} {name}: {status_text}"
            frame = self.put_korean_text(frame, text,
                                        (start_x + 10, y_offset), text_color, 16)
            y_offset += 28

        return frame

    def draw_safety_rate(
        self,
        frame: np.ndarray,
        ppe_status: PPEStatus,
        required_ppe: List[str] = None,
        position: Tuple[int, int] = (10, 10)
    ) -> np.ndarray:
        """
        안전률 표시

        Args:
            frame: BGR 이미지
            ppe_status: PPE 상태
            required_ppe: 필수 PPE 목록
            position: 표시 위치 (x, y)

        Returns:
            안전률이 표시된 프레임
        """
        if required_ppe is None:
            required_ppe = ['helmet', 'vest', 'gloves']

        safety_rate = ppe_status.calculate_safety_rate(required_ppe)

        # 색상 결정
        if safety_rate >= 80:
            color = (0, 255, 0)
            status = "안전"
        elif safety_rate >= 50:
            color = (0, 165, 255)
            status = "주의"
        else:
            color = (0, 0, 255)
            status = "위험"

        x, y = position

        # 배경
        cv2.rectangle(frame, (x, y), (x + 200, y + 50), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 200, y + 50), color, 2)

        # 텍스트
        frame = self.put_korean_text(frame, f"안전률: {safety_rate:.0f}% ({status})",
                                     (x + 10, y + 10), color, 18)

        return frame

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[PersonDetection],
        draw_boxes: bool = True,
        draw_labels: bool = True
    ) -> np.ndarray:
        """
        감지 결과 그리기 (바운딩 박스)

        Args:
            frame: BGR 이미지
            detections: PersonDetection 리스트
            draw_boxes: 바운딩 박스 표시 여부
            draw_labels: 레이블 표시 여부

        Returns:
            시각화된 프레임
        """
        for i, detection in enumerate(detections):
            bbox = detection.bbox
            ppe_status = detection.ppe_status

            if draw_boxes:
                # 사람 박스
                cv2.rectangle(frame, (bbox.x1, bbox.y1), (bbox.x2, bbox.y2),
                             self.colors['person'], 2)

                # PPE 박스들
                status_dict = ppe_status.get_status_dict()
                for ppe_type, info in status_dict.items():
                    if not info.get('detected'):
                        continue
                    # bbox가 있으면 그리기
                    ppe_bbox = getattr(ppe_status, f'{ppe_type}_bbox', None)
                    if ppe_bbox:
                        color = self.colors.get(ppe_type, (0, 255, 0))
                        cv2.rectangle(frame, (ppe_bbox.x1, ppe_bbox.y1),
                                     (ppe_bbox.x2, ppe_bbox.y2), color, 2)

            if draw_labels:
                # 사람 레이블 (이름 표시 제거 - 얼굴인식 박스에서만 이름 표시)
                label = f"사람 {i+1}"

                frame = self.put_korean_text(frame, label,
                                            (bbox.x1, bbox.y1 - 25),
                                            self.colors['person'], 16)

        return frame
