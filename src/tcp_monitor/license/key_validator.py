"""
라이선스 키 검증 모듈

키 형식 검증, 복호화, 유효성 확인을 담당합니다.

키 형식: TYPE-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (33자)
- TYPE: 라이선스 타입 (5자)
- SALT: 랜덤 Salt (4자)
- HWID: 하드웨어 바인딩 값 (4자)
- ISSUE: 발급일 인코딩 (4자)
- EXPIRY: 유효기간/버전 (4자)
- CUSTOMER: 고객 ID (4자)
- CHECKSUM: 체크섬 (4자)
"""

import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple, Dict, Any


class LicenseType(Enum):
    """라이선스 타입"""
    TRIAL = "TRIAL"      # 테스트 키 (7일)
    TIMED = "TIMED"      # 기간 제한 키
    PERPETUAL = "PERPT"  # 영구 키
    VERSION = "VERSN"    # 버전 제한 키


class LicenseKeyValidator:
    """라이선스 키 검증기"""

    # 키 형식: TYPE-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (33자 - 하드웨어 바인딩 포함)
    KEY_PATTERN = re.compile(
        r'^(TRIAL|TIMED|PERPT|VERSN)-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})$'
    )

    # 이전 형식 지원 (하드웨어 바인딩 없음)
    KEY_PATTERN_OLD = re.compile(
        r'^(TRIAL|TIMED|PERPT|VERSN)-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})-([A-Z0-9]{4})$'
    )

    # 기본 비밀 키 (실제 배포 시 변경 필요)
    _SECRET_KEY = "GARAMe2026!"

    # 인코딩용 문자 세트 (혼동 방지 문자 제외)
    _CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    @classmethod
    def validate_format(cls, key: str) -> bool:
        """키 형식 검증 (신규 및 이전 형식 모두 지원)"""
        if not key:
            return False
        key_upper = key.strip().upper()
        return bool(cls.KEY_PATTERN.match(key_upper) or cls.KEY_PATTERN_OLD.match(key_upper))

    @classmethod
    def _is_new_format(cls, key: str) -> bool:
        """신규 형식인지 확인 (하드웨어 바인딩 포함)"""
        return bool(cls.KEY_PATTERN.match(key.strip().upper()))

    @classmethod
    def parse_key(cls, key: str, hardware_id: str = None) -> Optional[Dict[str, Any]]:
        """
        키 파싱 및 복호화

        Args:
            key: 라이선스 키
            hardware_id: 현재 머신의 하드웨어 ID (검증용)

        Returns:
            파싱된 라이선스 정보 또는 None
        """
        key = key.strip().upper()

        if not cls.validate_format(key):
            return None

        # 신규 형식 (하드웨어 바인딩 포함)
        match = cls.KEY_PATTERN.match(key)
        is_new_format = bool(match)

        if not match:
            # 이전 형식 (하드웨어 바인딩 없음)
            match = cls.KEY_PATTERN_OLD.match(key)

        if not match:
            return None

        try:
            if is_new_format:
                # 신규 형식: TYPE-SALT-HWID-ISSUE-EXPIRY-CUSTOMER-CHECKSUM
                license_type = match.group(1)
                salt = match.group(2)
                hwid_enc = match.group(3)
                issue_enc = match.group(4)
                expiry_enc = match.group(5)
                customer_enc = match.group(6)
                checksum = match.group(7)

                # 체크섬 검증
                data_part = f"{license_type}-{salt}-{hwid_enc}-{issue_enc}-{expiry_enc}-{customer_enc}"
            else:
                # 이전 형식: TYPE-SALT-ISSUE-EXPIRY-CUSTOMER-CHECKSUM
                license_type = match.group(1)
                salt = match.group(2)
                hwid_enc = None
                issue_enc = match.group(3)
                expiry_enc = match.group(4)
                customer_enc = match.group(5)
                checksum = match.group(6)

                # 체크섬 검증
                data_part = f"{license_type}-{salt}-{issue_enc}-{expiry_enc}-{customer_enc}"

            expected_checksum = cls._calculate_checksum(data_part, salt)
            if checksum != expected_checksum:
                print(f"[License] 체크섬 불일치: {checksum} != {expected_checksum}")
                return None

            # XOR 키 생성
            xor_key = cls._derive_xor_key(salt)

            # 발급일 복호화 (2024년 기준 일수)
            issue_days = cls._decode_base32(issue_enc) ^ xor_key
            issue_date = datetime(2024, 1, 1) + timedelta(days=issue_days)

            # 유효기간/버전 복호화
            expiry_value = cls._decode_base32(expiry_enc) ^ xor_key

            # 고객 ID 복호화
            customer_id = cls._decode_base32(customer_enc) ^ xor_key

            # 결과 구성
            result = {
                'type': LicenseType(license_type),
                'issue_date': issue_date,
                'customer_id': customer_id,
                'raw_key': key,
                'salt': salt,
                'is_hardware_bound': is_new_format
            }

            # 하드웨어 ID 검증 (신규 형식이고 hardware_id가 제공된 경우)
            if is_new_format and hwid_enc:
                stored_hwid = cls._decode_base32(hwid_enc) ^ xor_key
                result['stored_hwid'] = stored_hwid
                result['hwid_enc'] = hwid_enc

                # 현재 하드웨어 ID와 비교
                if hardware_id:
                    # hardware_id의 처음 8자리를 정수로 변환
                    current_hwid = int(hardware_id[:8], 16) % (32 ** 4)
                    result['hardware_match'] = (stored_hwid == current_hwid)
                else:
                    result['hardware_match'] = None  # 검증 불가

            # 타입별 추가 정보
            if license_type == "TRIAL":
                result['expiry_date'] = issue_date + timedelta(days=7)
                result['days_valid'] = 7
            elif license_type == "TIMED":
                result['expiry_date'] = issue_date + timedelta(days=expiry_value)
                result['days_valid'] = expiry_value
            elif license_type == "PERPT":
                result['expiry_date'] = None
                result['days_valid'] = -1
            elif license_type == "VERSN":
                result['max_version'] = cls._decode_version(expiry_value)
                result['expiry_date'] = None

            return result

        except Exception as e:
            print(f"[License] 키 파싱 오류: {e}")
            return None

    @classmethod
    def validate_key(cls, key: str, current_version: str = None, hardware_id: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        키 전체 검증

        Args:
            key: 라이선스 키
            current_version: 현재 앱 버전 (버전 제한 키 검증용)
            hardware_id: 현재 머신의 하드웨어 ID (하드웨어 바인딩 검증용)

        Returns:
            (유효 여부, 메시지, 파싱 결과)
        """
        if not cls.validate_format(key):
            return False, "잘못된 키 형식입니다.", None

        parsed = cls.parse_key(key, hardware_id)
        if not parsed:
            return False, "키 복호화에 실패했습니다.", None

        now = datetime.now()
        license_type = parsed['type']

        # 하드웨어 바인딩 검증 (신규 형식이고 hardware_id가 제공된 경우)
        if parsed.get('is_hardware_bound') and hardware_id:
            if parsed.get('hardware_match') is False:
                return False, "이 키는 다른 컴퓨터에서 발급된 키입니다.", parsed

        # 유효기간 확인
        if license_type in [LicenseType.TRIAL, LicenseType.TIMED]:
            expiry_date = parsed.get('expiry_date')
            if expiry_date and now > expiry_date:
                days_expired = (now - expiry_date).days
                return False, f"라이선스가 만료되었습니다. ({days_expired}일 경과)", parsed

        # 버전 제한 확인
        if license_type == LicenseType.VERSION and current_version:
            max_version = parsed.get('max_version', '')
            if not cls._is_version_allowed(current_version, max_version):
                return False, f"이 키는 버전 {max_version}까지만 유효합니다.", parsed

        return True, "유효한 라이선스입니다.", parsed

    @classmethod
    def _derive_xor_key(cls, salt: str) -> int:
        """Salt에서 XOR 키 유도 (20비트)"""
        combined = salt + cls._SECRET_KEY
        hash_val = hashlib.md5(combined.encode()).hexdigest()
        return int(hash_val[:5], 16)  # 20비트 (0-1048575)

    @classmethod
    def _calculate_checksum(cls, data: str, salt: str) -> str:
        """체크섬 계산"""
        combined = data + salt + cls._SECRET_KEY
        hash_val = hashlib.md5(combined.encode()).hexdigest()
        # 해시에서 4자리 추출
        checksum_int = int(hash_val[:5], 16) % (32 ** 4)
        return cls._encode_base32(checksum_int)

    @classmethod
    def _encode_base32(cls, value: int) -> str:
        """정수를 4자리 Base32 문자열로 인코딩"""
        chars = cls._CHARSET
        result = ""
        value = value % (32 ** 4)  # 범위 제한
        for _ in range(4):
            result = chars[value % 32] + result
            value //= 32
        return result

    @classmethod
    def _decode_base32(cls, encoded: str) -> int:
        """Base32 문자열을 정수로 디코딩"""
        chars = cls._CHARSET
        value = 0
        for c in encoded:
            idx = chars.find(c)
            if idx < 0:
                raise ValueError(f"Invalid character: {c}")
            value = value * 32 + idx
        return value

    @classmethod
    def _decode_version(cls, version_int: int) -> str:
        """정수를 버전 문자열로 변환"""
        # 20000 -> 2.0.0
        major = version_int // 10000
        minor = (version_int // 1000) % 10
        patch = (version_int // 100) % 10
        sub = (version_int // 10) % 10
        build = version_int % 10

        if sub > 0 or build > 0:
            return f"{major}.{minor}.{patch}.{sub}-{build}"
        return f"{major}.{minor}.{patch}"

    @classmethod
    def _encode_version(cls, version_str: str) -> int:
        """버전 문자열을 정수로 변환"""
        try:
            parts = version_str.replace('-', '.').split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            sub = int(parts[3]) if len(parts) > 3 else 0
            build = int(parts[4]) if len(parts) > 4 else 0

            return major * 10000 + minor * 1000 + patch * 100 + sub * 10 + build
        except Exception:
            return 0

    @classmethod
    def _is_version_allowed(cls, current: str, max_allowed: str) -> bool:
        """버전 비교"""
        current_int = cls._encode_version(current)
        max_int = cls._encode_version(max_allowed)
        return current_int <= max_int


if __name__ == '__main__':
    print("=== 라이선스 키 검증기 테스트 ===")
    print(f"버전 변환: 1.9.8.4 -> {LicenseKeyValidator._encode_version('1.9.8.4')}")
    print(f"버전 복원: 19831 -> {LicenseKeyValidator._decode_version(19831)}")
