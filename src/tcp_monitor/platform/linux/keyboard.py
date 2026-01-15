"""
Linux 화상 키보드 관리 구현
"""

import subprocess
from typing import Optional


class LinuxKeyboardManager:
    """Linux용 화상 키보드 관리"""
    
    def open_virtual_keyboard(self, target_widget=None) -> bool:
        """
        Linux 가상 키보드 실행 (onboard 또는 florence, 중복 실행 방지)
        
        Args:
            target_widget: 포커스할 위젯 (선택적)
            
        Returns:
            bool: 실행 성공 여부
        """
        # onboard 프로세스 확인 (이미 실행 중인지 체크)
        try:
            result = subprocess.run(['pgrep', '-x', 'onboard'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                # 이미 실행 중이면 새로 실행하지 않음
                print("onboard가 이미 실행 중입니다.")
                if target_widget:
                    try:
                        target_widget.focus_force()
                    except Exception:
                        pass
                return True
        except Exception:
            pass  # pgrep 실패 시 계속 진행
        
        # onboard 시도
        try:
            # 백그라운드로 실행 (stdout/stderr 리다이렉션하여 경고 메시지 억제)
            subprocess.Popen(['onboard'],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            print("onboard 실행 성공")
            if target_widget:
                try:
                    target_widget.focus_force()
                except Exception:
                    pass
            return True
        except FileNotFoundError:
            print("onboard를 찾을 수 없습니다.")
        except Exception as e:
            print(f"onboard 실행 실패: {e}")
        
        # florence 프로세스 확인 (이미 실행 중인지 체크)
        try:
            result = subprocess.run(['pgrep', '-x', 'florence'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                # 이미 실행 중이면 새로 실행하지 않음
                print("florence가 이미 실행 중입니다.")
                if target_widget:
                    try:
                        target_widget.focus_force()
                    except Exception:
                        pass
                return True
        except Exception:
            pass  # pgrep 실패 시 계속 진행
        
        # florence 시도
        try:
            # 백그라운드로 실행
            subprocess.Popen(['florence'],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            print("florence 실행 성공")
            if target_widget:
                try:
                    target_widget.focus_force()
                except Exception:
                    pass
            return True
        except FileNotFoundError:
            print("florence를 찾을 수 없습니다.")
            print("가상 키보드를 설치하려면: sudo apt-get install onboard 또는 florence")
        except Exception as e:
            print(f"florence 실행 실패: {e}")
        
        return False
    
    def force_korean_ime(self, target_widget) -> bool:
        """
        Linux에서는 IME 강제 설정이 필요 없음
        
        Args:
            target_widget: 대상 위젯
            
        Returns:
            bool: 항상 True (Linux에서는 무시)
        """
        # Linux에서는 IME 설정이 필요 없음
        return True

