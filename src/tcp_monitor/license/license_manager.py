"""
라이선스 관리 모듈

라이선스 상태 관리, 파일 저장/로드, 활성화 처리를 담당합니다.
"""

import json
import os
import base64
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Tuple
from enum import Enum
from pathlib import Path
import struct

from .hardware_id import HardwareID
from .key_validator import LicenseKeyValidator, LicenseType


@dataclass
class LicenseInfo:
    """라이선스 정보"""
    license_key: str
    license_type: str
    issue_date: str
    expiry_date: Optional[str]
    max_version: Optional[str]
    customer_id: int
    hardware_id: str
    activated_at: str
    days_remaining: int = -1

    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.expiry_date is None:
            return False
        try:
            expiry = datetime.fromisoformat(self.expiry_date)
            return datetime.now() > expiry
        except Exception:
            return True

    def get_days_remaining(self) -> int:
        """남은 일수 반환 (-1: 영구)"""
        if self.expiry_date is None:
            return -1
        try:
            expiry = datetime.fromisoformat(self.expiry_date)
            delta = expiry - datetime.now()
            return max(0, delta.days)
        except Exception:
            return 0


class LicenseStatus(Enum):
    """라이선스 상태"""
    VALID = "valid"              # 유효함
    EXPIRED = "expired"          # 만료됨
    INVALID = "invalid"          # 잘못된 키
    NOT_ACTIVATED = "not_activated"  # 미활성화
    HARDWARE_MISMATCH = "hardware_mismatch"  # 하드웨어 불일치
    VERSION_EXCEEDED = "version_exceeded"  # 버전 초과


class LicenseManager:
    """라이선스 관리자"""

    # 라이선스 파일 경로
    LICENSE_DIR = os.path.expanduser("~/.garame")
    LICENSE_FILE = "license.dat"

    # 암호화 키 (실제 배포 시 변경)
    _ENCRYPT_KEY = b"GARAMe_License_Encrypt_Key_2026!"

    def __init__(self):
        self._license_info: Optional[LicenseInfo] = None
        self._status: LicenseStatus = LicenseStatus.NOT_ACTIVATED
        self._ensure_license_dir()

    def _ensure_license_dir(self):
        """라이선스 디렉토리 생성"""
        Path(self.LICENSE_DIR).mkdir(parents=True, exist_ok=True)

    @property
    def license_path(self) -> str:
        """라이선스 파일 전체 경로"""
        return os.path.join(self.LICENSE_DIR, self.LICENSE_FILE)

    def activate(self, license_key: str, current_version: str = "1.9.8.4") -> Tuple[bool, str]:
        """
        라이선스 활성화

        Args:
            license_key: 라이선스 키
            current_version: 현재 프로그램 버전

        Returns:
            (success, message)
        """
        # 키 검증
        is_valid, message, parsed = LicenseKeyValidator.validate_key(
            license_key, current_version
        )

        if not is_valid:
            self._status = LicenseStatus.INVALID
            return False, message

        # 하드웨어 ID 가져오기
        hardware_id = HardwareID.get_machine_id()

        # 라이선스 정보 생성
        license_type = parsed['type']
        expiry_date = parsed.get('expiry_date')

        self._license_info = LicenseInfo(
            license_key=license_key,
            license_type=license_type.value,
            issue_date=parsed['issue_date'].isoformat(),
            expiry_date=expiry_date.isoformat() if expiry_date else None,
            max_version=parsed.get('max_version'),
            customer_id=parsed.get('customer_id', 0),
            hardware_id=hardware_id,
            activated_at=datetime.now().isoformat()
        )

        # 파일 저장
        if not self._save_license():
            return False, "라이선스 파일 저장에 실패했습니다."

        self._status = LicenseStatus.VALID

        # 성공 메시지
        if license_type == LicenseType.TRIAL:
            days = parsed.get('days_valid', 7)
            return True, f"테스트 라이선스가 활성화되었습니다. ({days}일간 유효)"
        elif license_type == LicenseType.TIMED:
            days = self._license_info.get_days_remaining()
            return True, f"기간 제한 라이선스가 활성화되었습니다. ({days}일 남음)"
        elif license_type == LicenseType.PERPETUAL:
            return True, "영구 라이선스가 활성화되었습니다."
        elif license_type == LicenseType.VERSION:
            max_ver = parsed.get('max_version', '')
            return True, f"버전 제한 라이선스가 활성화되었습니다. (최대 {max_ver})"

        return True, "라이선스가 활성화되었습니다."

    def check_license(self, current_version: str = "1.9.8.4") -> Tuple[LicenseStatus, str, Optional[LicenseInfo]]:
        """
        라이선스 상태 확인

        Args:
            current_version: 현재 프로그램 버전

        Returns:
            (status, message, license_info)
        """
        # 라이선스 파일 로드
        if not self._load_license():
            self._status = LicenseStatus.NOT_ACTIVATED
            return self._status, "라이선스가 활성화되지 않았습니다.", None

        info = self._license_info

        # 하드웨어 ID 검증
        current_hardware = HardwareID.get_machine_id()
        if info.hardware_id != current_hardware:
            self._status = LicenseStatus.HARDWARE_MISMATCH
            return self._status, "다른 컴퓨터에서 활성화된 라이선스입니다.", info

        # 만료 확인
        if info.is_expired():
            self._status = LicenseStatus.EXPIRED
            return self._status, "라이선스가 만료되었습니다.", info

        # 버전 제한 확인
        if info.license_type == LicenseType.VERSION.value:
            max_version = info.max_version
            if max_version and not LicenseKeyValidator._is_version_allowed(current_version, max_version):
                self._status = LicenseStatus.VERSION_EXCEEDED
                return self._status, f"이 라이선스는 버전 {max_version}까지만 유효합니다.", info

        # 유효
        self._status = LicenseStatus.VALID
        info.days_remaining = info.get_days_remaining()

        if info.days_remaining == -1:
            msg = "영구 라이선스"
        elif info.days_remaining > 0:
            msg = f"라이선스 유효 ({info.days_remaining}일 남음)"
        else:
            msg = "라이선스 유효 (오늘 만료)"

        return self._status, msg, info

    def deactivate(self) -> bool:
        """라이선스 비활성화 (파일 삭제)"""
        try:
            if os.path.exists(self.license_path):
                os.remove(self.license_path)
            self._license_info = None
            self._status = LicenseStatus.NOT_ACTIVATED
            return True
        except Exception as e:
            print(f"[License] 비활성화 실패: {e}")
            return False

    def _save_license(self) -> bool:
        """라이선스 파일 저장 (암호화)"""
        if not self._license_info:
            return False

        try:
            # JSON 직렬화
            data = asdict(self._license_info)
            json_str = json.dumps(data, ensure_ascii=False)

            # 암호화
            encrypted = self._encrypt(json_str.encode('utf-8'))

            # 파일 저장
            with open(self.license_path, 'wb') as f:
                f.write(encrypted)

            return True
        except Exception as e:
            print(f"[License] 저장 실패: {e}")
            return False

    def _load_license(self) -> bool:
        """라이선스 파일 로드 (복호화)"""
        try:
            if not os.path.exists(self.license_path):
                return False

            with open(self.license_path, 'rb') as f:
                encrypted = f.read()

            # 복호화
            decrypted = self._decrypt(encrypted)
            if not decrypted:
                return False

            # JSON 파싱
            data = json.loads(decrypted.decode('utf-8'))
            self._license_info = LicenseInfo(**data)

            return True
        except Exception as e:
            print(f"[License] 로드 실패: {e}")
            return False

    def _encrypt(self, data: bytes) -> bytes:
        """간단한 XOR 암호화 + Base64"""
        key = self._ENCRYPT_KEY
        encrypted = bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

        # HMAC 추가 (무결성 검증)
        hmac_val = hashlib.sha256(key + encrypted).digest()[:16]

        # 버전 + HMAC + 데이터
        result = b'\x01' + hmac_val + encrypted
        return base64.b64encode(result)

    def _decrypt(self, data: bytes) -> Optional[bytes]:
        """복호화"""
        try:
            decoded = base64.b64decode(data)

            # 버전 확인
            if decoded[0] != 1:
                return None

            # HMAC 검증
            stored_hmac = decoded[1:17]
            encrypted = decoded[17:]

            expected_hmac = hashlib.sha256(self._ENCRYPT_KEY + encrypted).digest()[:16]
            if stored_hmac != expected_hmac:
                return None

            # XOR 복호화
            key = self._ENCRYPT_KEY
            return bytes(d ^ key[i % len(key)] for i, d in enumerate(encrypted))
        except Exception:
            return None

    @property
    def is_valid(self) -> bool:
        """라이선스 유효 여부"""
        return self._status == LicenseStatus.VALID

    @property
    def status(self) -> LicenseStatus:
        """현재 상태"""
        return self._status

    @property
    def info(self) -> Optional[LicenseInfo]:
        """라이선스 정보"""
        return self._license_info

    def get_status_display(self) -> str:
        """상태 표시 문자열"""
        if self._status == LicenseStatus.VALID:
            if self._license_info:
                days = self._license_info.get_days_remaining()
                if days == -1:
                    return "정품 인증됨 (영구)"
                elif days > 0:
                    return f"정품 인증됨 ({days}일 남음)"
                else:
                    return "정품 인증됨 (오늘 만료)"
            return "정품 인증됨"
        elif self._status == LicenseStatus.EXPIRED:
            return "라이선스 만료"
        elif self._status == LicenseStatus.NOT_ACTIVATED:
            return "미인증"
        elif self._status == LicenseStatus.HARDWARE_MISMATCH:
            return "하드웨어 불일치"
        elif self._status == LicenseStatus.VERSION_EXCEEDED:
            return "버전 초과"
        else:
            return "인증 실패"


# 전역 라이선스 관리자 인스턴스
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """전역 라이선스 관리자 반환 (싱글톤)"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


if __name__ == '__main__':
    # 테스트
    print("=== 라이선스 관리자 테스트 ===")

    manager = LicenseManager()

    # 상태 확인
    status, msg, info = manager.check_license()
    print(f"상태: {status.value}")
    print(f"메시지: {msg}")

    if info:
        print(f"라이선스 정보:")
        print(f"  타입: {info.license_type}")
        print(f"  발급일: {info.issue_date}")
        print(f"  만료일: {info.expiry_date}")
        print(f"  하드웨어 ID: {info.hardware_id}")
