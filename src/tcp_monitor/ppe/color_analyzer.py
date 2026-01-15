"""
색상 분석 모듈
헬멧과 조끼의 색상을 HSV 기반으로 분석합니다.

원본: ppe_detection/src/color_analyzer.py
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional


class ColorAnalyzer:
    """HSV 기반 색상 분석 클래스"""

    # 기본 HSV 색상 범위 (H: 0-180, S: 0-255, V: 0-255)
    # 노란색과 갈색의 구분을 명확히 함
    DEFAULT_COLOR_RANGES = {
        'yellow': {
            # 노란색: Hue 15~35, 채도와 명도가 높음
            'lower': np.array([15, 80, 120]),
            'upper': np.array([35, 255, 255])
        },
        'orange': {
            # 주황색: Hue 5~15
            'lower': np.array([5, 150, 120]),
            'upper': np.array([15, 255, 255])
        },
        'red': {
            # 빨간색: Hue 0~5 또는 165~180
            'lower1': np.array([0, 100, 100]),
            'upper1': np.array([5, 255, 255]),
            'lower2': np.array([165, 100, 100]),
            'upper2': np.array([180, 255, 255])
        },
        'brown': {
            # 갈색: Hue 5~20, 채도 50~180, 명도 40~150 (어둡고 탁한 색)
            'lower': np.array([5, 50, 40]),
            'upper': np.array([20, 180, 150])
        },
        'green': {
            'lower': np.array([40, 80, 80]),
            'upper': np.array([85, 255, 255])
        },
        'blue': {
            'lower': np.array([85, 80, 80]),
            'upper': np.array([130, 255, 255])
        },
        'white': {
            # 흰색: 채도가 낮고 명도가 높음
            'lower': np.array([0, 0, 180]),
            'upper': np.array([180, 50, 255])
        },
        'black': {
            # 검정: 명도가 낮음
            'lower': np.array([0, 0, 0]),
            'upper': np.array([180, 255, 45])
        }
    }

    # 색상 한글명 매핑
    COLOR_NAMES_KR = {
        'red': '빨강',
        'orange': '주황',
        'yellow': '노랑',
        'green': '초록',
        'blue': '파랑',
        'brown': '갈색',
        'white': '흰색',
        'black': '검정',
        'unknown': '알수없음'
    }

    # 색상 우선순위
    COLOR_PRIORITY = ['yellow', 'brown', 'orange', 'red', 'green', 'blue', 'white', 'black']

    def __init__(self, color_ranges: Optional[Dict] = None):
        """색상 분석기 초기화"""
        self.color_ranges = color_ranges or self.DEFAULT_COLOR_RANGES

    def analyze(self, image: np.ndarray) -> Tuple[str, str]:
        """
        이미지의 주요 색상 분석

        Args:
            image: BGR 이미지 (ROI)

        Returns:
            (영문 색상명, 한글 색상명)
        """
        if image is None or image.size == 0:
            return 'unknown', self.COLOR_NAMES_KR['unknown']

        # BGR -> HSV 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 이미지 중앙 영역만 분석
        h, w = hsv.shape[:2]
        margin_h, margin_w = h // 4, w // 4
        hsv_center = hsv[margin_h:h-margin_h, margin_w:w-margin_w]
        if hsv_center.size == 0:
            hsv_center = hsv

        # 각 색상별 픽셀 수 계산
        color_counts = {}

        for color_name, ranges in self.color_ranges.items():
            if color_name == 'red':
                mask1 = cv2.inRange(hsv_center, ranges['lower1'], ranges['upper1'])
                mask2 = cv2.inRange(hsv_center, ranges['lower2'], ranges['upper2'])
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv_center, ranges['lower'], ranges['upper'])

            color_counts[color_name] = cv2.countNonZero(mask)

        total_pixels = hsv_center.shape[0] * hsv_center.shape[1]
        if total_pixels == 0:
            return 'unknown', self.COLOR_NAMES_KR['unknown']

        min_threshold = total_pixels * 0.03
        valid_colors = {k: v for k, v in color_counts.items() if v > min_threshold}

        if not valid_colors:
            return 'unknown', self.COLOR_NAMES_KR['unknown']

        # 노란색과 갈색이 둘 다 감지되면 평균 명도/채도로 구분
        if 'yellow' in valid_colors and 'brown' in valid_colors:
            # 평균 H, S, V 계산
            h_mean = np.mean(hsv_center[:, :, 0])
            s_mean = np.mean(hsv_center[:, :, 1])
            v_mean = np.mean(hsv_center[:, :, 2])

            # 노란색: 높은 명도(V > 140)와 채도(S > 100)
            # 갈색: 낮은 명도(V < 140) 또는 낮은 채도
            if v_mean > 140 and s_mean > 100:
                return 'yellow', self.COLOR_NAMES_KR['yellow']
            elif v_mean < 140 or s_mean < 100:
                return 'brown', self.COLOR_NAMES_KR['brown']

        max_count = max(valid_colors.values())
        similar_colors = {k: v for k, v in valid_colors.items() if v >= max_count * 0.7}

        for priority_color in self.COLOR_PRIORITY:
            if priority_color in similar_colors:
                return priority_color, self.COLOR_NAMES_KR.get(priority_color, '알수없음')

        dominant_color = max(valid_colors, key=valid_colors.get)
        return dominant_color, self.COLOR_NAMES_KR.get(dominant_color, '알수없음')

    def get_color_bgr(self, color_name: str) -> Tuple[int, int, int]:
        """색상명에 해당하는 BGR 값 반환"""
        color_bgr = {
            'red': (0, 0, 255),
            'orange': (0, 165, 255),
            'yellow': (0, 255, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'brown': (42, 42, 165),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'unknown': (128, 128, 128)
        }
        return color_bgr.get(color_name, (128, 128, 128))
