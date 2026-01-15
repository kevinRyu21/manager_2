"""
PPE Detection Module for GARAMe Manager
YOLOv10 기반 개인보호장비(PPE) 감지 모듈

이 모듈은 ppe_detection 프로젝트를 GARAMe Manager에 통합한 버전입니다.
"""

from .detector import PPEDetector, PPEStatus, PersonDetection, BoundingBox
from .color_analyzer import ColorAnalyzer
from .visualizer import PPEVisualizer

__all__ = [
    'PPEDetector',
    'PPEStatus',
    'PersonDetection',
    'BoundingBox',
    'ColorAnalyzer',
    'PPEVisualizer'
]

__version__ = '1.0.0'
