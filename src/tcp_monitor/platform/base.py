"""
플랫폼별 어댑터 베이스 클래스

각 플랫폼별 구현의 인터페이스를 정의합니다.
"""

import abc
from typing import Optional, Tuple


class CameraBackend(abc.ABC):
    """카메라 백엔드 추상 클래스"""
    
    @abc.abstractmethod
    def get_backend(self) -> int:
        """
        OpenCV 카메라 백엔드 반환
        
        Returns:
            int: cv2.CAP_* 상수 값
        """
        pass
    
    @abc.abstractmethod
    def get_fallback_backend(self) -> int:
        """
        대체 카메라 백엔드 반환
        
        Returns:
            int: cv2.CAP_* 상수 값
        """
        pass


class KeyboardManager(abc.ABC):
    """화상 키보드 관리 추상 클래스"""
    
    @abc.abstractmethod
    def open_virtual_keyboard(self, target_widget=None) -> bool:
        """
        가상 키보드 실행
        
        Args:
            target_widget: 포커스할 위젯 (선택적)
            
        Returns:
            bool: 실행 성공 여부
        """
        pass
    
    @abc.abstractmethod
    def force_korean_ime(self, target_widget) -> bool:
        """
        한글 IME 강제 설정 (Windows 전용, Linux에서는 무시)
        
        Args:
            target_widget: 대상 위젯
            
        Returns:
            bool: 성공 여부
        """
        pass


class SystemUtils(abc.ABC):
    """시스템 유틸리티 추상 클래스"""
    
    @abc.abstractmethod
    def open_file(self, file_path: str) -> bool:
        """
        파일을 기본 애플리케이션으로 열기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        pass
    
    @abc.abstractmethod
    def get_window_handle(self, window) -> Optional[int]:
        """
        윈도우 핸들 반환 (Windows 전용, Linux에서는 None)
        
        Args:
            window: Tkinter 윈도우 객체
            
        Returns:
            Optional[int]: 윈도우 핸들 또는 None
        """
        pass
    
    @abc.abstractmethod
    def block_unauthorized_windows(self) -> bool:
        """
        권한 없는 윈도우 차단 (Windows 전용, Linux에서는 무시)
        
        Returns:
            bool: 성공 여부
        """
        pass

