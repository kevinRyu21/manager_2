"""
Linux 카메라 백엔드 구현
"""

import cv2
from ..base import CameraBackend


class LinuxCameraBackend(CameraBackend):
    """Linux용 카메라 백엔드"""
    
    def get_backend(self) -> int:
        """V4L2 백엔드 반환"""
        return cv2.CAP_V4L2
    
    def get_fallback_backend(self) -> int:
        """기본 백엔드 반환 (V4L2 실패 시)"""
        return cv2.CAP_ANY

