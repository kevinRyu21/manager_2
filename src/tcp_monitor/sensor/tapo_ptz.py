#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tapo 카메라 PTZ (Pan-Tilt-Zoom) 제어 모듈

Tapo C210, C211, C220, C225 등 PTZ 지원 카메라 제어
pytapo 라이브러리 사용
"""

import threading
import time
from typing import Optional, Callable

# pytapo 라이브러리 로드 시도
PYTAPO_AVAILABLE = False
try:
    from pytapo import Tapo
    PYTAPO_AVAILABLE = True
except ImportError:
    print("[PTZ] pytapo 라이브러리가 설치되지 않았습니다. pip install pytapo")


class TapoPTZController:
    """Tapo 카메라 PTZ 제어기"""

    # PTZ 이동 속도 (1-100)
    DEFAULT_SPEED = 50

    # PTZ 이동 각도
    PAN_ANGLE = 10  # 좌우 이동 각도
    TILT_ANGLE = 10  # 상하 이동 각도

    def __init__(
        self,
        ip: str,
        username: str,
        password: str,
        on_status_change: Optional[Callable[[str], None]] = None
    ):
        """
        PTZ 제어기 초기화

        Args:
            ip: 카메라 IP 주소
            username: Tapo 계정 사용자명 (이메일)
            password: Tapo 계정 비밀번호 (클라우드 비밀번호)
            on_status_change: 상태 변경 콜백 함수
        """
        self.ip = ip
        self.username = username
        self.password = password
        self.on_status_change = on_status_change

        self.tapo: Optional[Tapo] = None
        self.connected = False
        self.ptz_supported = False
        self.last_error = ""

        self._lock = threading.Lock()
        self._moving = False

    def connect(self) -> bool:
        """카메라 연결 - 단일 인증 방식 (계정 잠금 방지)"""
        if not PYTAPO_AVAILABLE:
            self.last_error = "pytapo 라이브러리 없음"
            return False

        # 단일 인증 방식만 사용 (여러 번 시도하면 계정이 잠김)
        # pytapo 공식 권장: admin + 클라우드 비밀번호
        try:
            self._update_status("연결 시도...")
            self.tapo = Tapo(
                self.ip,
                "admin",
                self.password,
                cloudPassword=""
            )

            # 연결 테스트
            basic_info = self.tapo.getBasicInfo()
            if basic_info:
                device_info = basic_info.get('device_info', {}).get('basic_info', {})
                model = device_info.get('device_model', 'Unknown')
                print(f"[PTZ] 카메라 연결 성공: {model} ({self.ip})")

                self.ptz_supported = hasattr(self.tapo, 'moveMotor')
                if self.ptz_supported:
                    print(f"[PTZ] PTZ 기능 지원됨")
                else:
                    print(f"[PTZ] PTZ 기능 미지원 (고정 카메라)")

                self.connected = True
                self._update_status("연결됨" if self.ptz_supported else "PTZ 미지원")
                return True

        except Exception as e:
            self.last_error = str(e)
            # Temporary Suspension 시 안내 메시지
            if "Temporary Suspension" in self.last_error:
                print(f"[PTZ] 계정 일시 잠금됨 - 30분 후 재시도하세요")
                self._update_status("계정 잠금")
            else:
                print(f"[PTZ] 연결 실패: {self.last_error}")
                self._update_status("연결 실패")

        return False

    def disconnect(self):
        """카메라 연결 해제"""
        self.tapo = None
        self.connected = False
        self._update_status("연결 끊김")

    def move_up(self, angle: int = None) -> bool:
        """위로 이동"""
        return self._move(0, angle or self.TILT_ANGLE)

    def move_down(self, angle: int = None) -> bool:
        """아래로 이동"""
        return self._move(0, -(angle or self.TILT_ANGLE))

    def move_left(self, angle: int = None) -> bool:
        """왼쪽으로 이동"""
        return self._move(-(angle or self.PAN_ANGLE), 0)

    def move_right(self, angle: int = None) -> bool:
        """오른쪽으로 이동"""
        return self._move(angle or self.PAN_ANGLE, 0)

    def move_home(self) -> bool:
        """홈 위치로 이동"""
        if not self._check_ready():
            return False

        try:
            with self._lock:
                self._update_status("홈으로 이동...")
                # 프리셋 0번 = 홈 위치
                if hasattr(self.tapo, 'setPreset'):
                    self.tapo.setPreset(0)
                    self._update_status("홈 이동 완료")
                    return True
                else:
                    self.last_error = "홈 기능 미지원"
                    self._update_status("홈 미지원")
                    return False
        except Exception as e:
            self.last_error = str(e)
            print(f"[PTZ] 홈 이동 실패: {e}")
            self._update_status("홈 이동 실패")
            return False

    def _move(self, pan: int, tilt: int) -> bool:
        """
        PTZ 이동 실행

        Args:
            pan: 좌우 이동 각도 (양수=오른쪽, 음수=왼쪽)
            tilt: 상하 이동 각도 (양수=위, 음수=아래)

        Returns:
            성공 여부
        """
        if not self._check_ready():
            return False

        if self._moving:
            return False

        try:
            with self._lock:
                self._moving = True
                direction = self._get_direction_name(pan, tilt)
                self._update_status(f"{direction} 이동...")

                # moveMotor(x, y) - x: pan, y: tilt
                self.tapo.moveMotor(pan, tilt)

                self._update_status("준비")
                return True

        except Exception as e:
            self.last_error = str(e)
            print(f"[PTZ] 이동 실패: {e}")
            self._update_status("이동 실패")
            return False
        finally:
            self._moving = False

    def _check_ready(self) -> bool:
        """PTZ 사용 가능 상태 확인"""
        if not PYTAPO_AVAILABLE:
            self.last_error = "pytapo 없음"
            return False

        if not self.connected or self.tapo is None:
            self.last_error = "연결 안 됨"
            return False

        if not self.ptz_supported:
            self.last_error = "PTZ 미지원"
            return False

        return True

    def _get_direction_name(self, pan: int, tilt: int) -> str:
        """이동 방향 이름 반환"""
        if tilt > 0:
            return "위로"
        elif tilt < 0:
            return "아래로"
        elif pan > 0:
            return "오른쪽"
        elif pan < 0:
            return "왼쪽"
        return "이동"

    def _update_status(self, status: str):
        """상태 업데이트 및 콜백 호출"""
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def get_presets(self) -> list:
        """저장된 프리셋 목록 조회"""
        if not self._check_ready():
            return []

        try:
            presets = self.tapo.getPresets()
            return presets if presets else []
        except Exception as e:
            print(f"[PTZ] 프리셋 조회 실패: {e}")
            return []

    def goto_preset(self, preset_id: int) -> bool:
        """프리셋 위치로 이동"""
        if not self._check_ready():
            return False

        try:
            self._update_status(f"프리셋 {preset_id}로 이동...")
            self.tapo.setPreset(preset_id)
            self._update_status("이동 완료")
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[PTZ] 프리셋 이동 실패: {e}")
            self._update_status("프리셋 이동 실패")
            return False

    def save_preset(self, preset_id: int, name: str = "") -> bool:
        """현재 위치를 프리셋으로 저장"""
        if not self._check_ready():
            return False

        try:
            self._update_status(f"프리셋 {preset_id} 저장...")
            if hasattr(self.tapo, 'savePreset'):
                self.tapo.savePreset(preset_id, name)
                self._update_status("프리셋 저장됨")
                return True
            else:
                self.last_error = "프리셋 저장 미지원"
                return False
        except Exception as e:
            self.last_error = str(e)
            print(f"[PTZ] 프리셋 저장 실패: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """PTZ 사용 가능 여부"""
        return PYTAPO_AVAILABLE and self.connected and self.ptz_supported


def test_ptz_controller():
    """PTZ 컨트롤러 테스트"""
    if not PYTAPO_AVAILABLE:
        print("pytapo가 설치되지 않았습니다.")
        return

    # 테스트용 (실제 사용 시 값 변경 필요)
    controller = TapoPTZController(
        ip="192.168.0.26",
        username="your_email@example.com",
        password="your_password"
    )

    if controller.connect():
        print("연결 성공!")
        print(f"PTZ 지원: {controller.ptz_supported}")

        if controller.ptz_supported:
            # 상하좌우 테스트
            print("위로 이동...")
            controller.move_up()
            time.sleep(1)

            print("아래로 이동...")
            controller.move_down()
            time.sleep(1)

        controller.disconnect()
    else:
        print(f"연결 실패: {controller.last_error}")


if __name__ == "__main__":
    test_ptz_controller()
