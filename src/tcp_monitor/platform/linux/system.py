"""
Linux 시스템 유틸리티 구현
"""

import subprocess
from typing import Optional
from ..base import SystemUtils


class LinuxSystemUtils(SystemUtils):
    """Linux용 시스템 유틸리티"""
    
    def open_file(self, file_path: str) -> bool:
        """
        Linux에서 파일을 기본 애플리케이션으로 열기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            subprocess.run(["xdg-open", file_path], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"파일 열기 실패: {e}")
            return False
        except FileNotFoundError:
            print("xdg-open을 찾을 수 없습니다. xdg-utils 패키지를 설치하세요.")
            return False
    
    def get_window_handle(self, window) -> Optional[int]:
        """
        Linux에서는 윈도우 핸들 개념이 없음
        
        Args:
            window: Tkinter 윈도우 객체
            
        Returns:
            None: 항상 None
        """
        return None
    
    def block_unauthorized_windows(self) -> bool:
        """
        Linux에서는 윈도우 차단 기능이 없음
        
        Returns:
            bool: 항상 True (Linux에서는 무시)
        """
        return True

