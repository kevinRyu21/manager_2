#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARAMe Manager 라이선스 키 생성기

관리자용 키 생성 도구입니다.
암호로 보호되며, 첫 실행 시 암호를 설정합니다.

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
import secrets
import getpass
import os
import json
from datetime import datetime
from enum import Enum
import csv


class LicenseType(Enum):
    """라이선스 타입"""
    TRIAL = "TRIAL"      # 테스트 키 (7일)
    TIMED = "TIMED"      # 기간 제한 키
    PERPETUAL = "PERPT"  # 영구 키
    VERSION = "VERSN"    # 버전 제한 키


class PasswordManager:
    """암호 관리자"""

    _PASSWORD_FILE = os.path.join(os.path.dirname(__file__), '.generator_auth')

    @classmethod
    def is_password_set(cls) -> bool:
        """암호가 설정되어 있는지 확인"""
        return os.path.exists(cls._PASSWORD_FILE)

    @classmethod
    def set_password(cls, password: str) -> bool:
        """암호 설정 (SHA-256 해시로 저장)"""
        try:
            # 솔트 생성
            salt = secrets.token_hex(16)
            # 비밀번호 해시
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

            # 저장
            with open(cls._PASSWORD_FILE, 'w') as f:
                json.dump({
                    'salt': salt,
                    'hash': password_hash
                }, f)

            # 파일 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(cls._PASSWORD_FILE, 0o600)
            return True
        except Exception as e:
            print(f"암호 설정 실패: {e}")
            return False

    @classmethod
    def verify_password(cls, password: str) -> bool:
        """암호 검증"""
        try:
            with open(cls._PASSWORD_FILE, 'r') as f:
                data = json.load(f)

            salt = data['salt']
            stored_hash = data['hash']

            # 입력된 비밀번호 해시
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

            return password_hash == stored_hash
        except Exception as e:
            print(f"암호 검증 실패: {e}")
            return False


class LicenseKeyGenerator:
    """라이선스 키 생성기"""

    # 비밀 키 (key_validator.py와 동일해야 함!)
    _SECRET_KEY = "GARAMe2026!"

    # 인코딩용 문자 세트 (혼동 방지 문자 제외)
    _CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def __init__(self):
        self._generated_keys = []

    def generate_trial_key(self, hardware_id: str, customer_id: int = 0, days: int = 7) -> str:
        """
        테스트 키 생성 (기본 7일)

        Args:
            hardware_id: 대상 머신의 하드웨어 ID (32자리 16진수)
            customer_id: 고객 ID (0~65535)
            days: 유효 기간 (기본 7일)

        Returns:
            라이선스 키 문자열
        """
        return self._generate_key(LicenseType.TRIAL, hardware_id, customer_id, days)

    def generate_timed_key(self, hardware_id: str, customer_id: int, days: int) -> str:
        """
        기간 제한 키 생성

        Args:
            hardware_id: 대상 머신의 하드웨어 ID
            customer_id: 고객 ID
            days: 유효 기간 (일)

        Returns:
            라이선스 키 문자열
        """
        return self._generate_key(LicenseType.TIMED, hardware_id, customer_id, days)

    def generate_perpetual_key(self, hardware_id: str, customer_id: int) -> str:
        """
        영구 키 생성

        Args:
            hardware_id: 대상 머신의 하드웨어 ID
            customer_id: 고객 ID

        Returns:
            라이선스 키 문자열
        """
        return self._generate_key(LicenseType.PERPETUAL, hardware_id, customer_id, 0)

    def generate_version_key(self, hardware_id: str, customer_id: int, max_version: str) -> str:
        """
        버전 제한 키 생성

        Args:
            hardware_id: 대상 머신의 하드웨어 ID
            customer_id: 고객 ID
            max_version: 최대 허용 버전 (예: "1.9.8.4")

        Returns:
            라이선스 키 문자열
        """
        version_int = self._encode_version(max_version)
        return self._generate_key(LicenseType.VERSION, hardware_id, customer_id, version_int)

    def _generate_key(self, license_type: LicenseType, hardware_id: str, customer_id: int, expiry_value: int) -> str:
        """키 생성 내부 메서드"""
        # 1. Salt 생성 (랜덤 4자리)
        salt = ''.join(secrets.choice(self._CHARSET) for _ in range(4))

        # 2. XOR 키 유도
        xor_key = self._derive_xor_key(salt)

        # 3. 하드웨어 ID 인코딩 (처음 8자리 사용)
        hwid_int = int(hardware_id[:8], 16) % (32 ** 4)
        hwid_enc = self._encode_base32((hwid_int ^ xor_key) % (32 ** 4))

        # 4. 발급일 인코딩 (2024-01-01 기준 일수)
        issue_days = (datetime.now() - datetime(2024, 1, 1)).days
        issue_enc = self._encode_base32((issue_days ^ xor_key) % (32 ** 4))

        # 5. 유효기간/버전 인코딩
        expiry_enc = self._encode_base32((expiry_value ^ xor_key) % (32 ** 4))

        # 6. 고객 ID 인코딩
        customer_enc = self._encode_base32((customer_id ^ xor_key) % (32 ** 4))

        # 7. 체크섬 계산
        data_part = f"{license_type.value}-{salt}-{hwid_enc}-{issue_enc}-{expiry_enc}-{customer_enc}"
        checksum = self._calculate_checksum(data_part, salt)

        # 8. 최종 키 조합
        key = f"{license_type.value}-{salt}-{hwid_enc}-{issue_enc}-{expiry_enc}-{customer_enc}-{checksum}"

        # 생성 기록 저장
        self._generated_keys.append({
            'key': key,
            'type': license_type.value,
            'hardware_id': hardware_id[:16] + '...',  # 보안을 위해 일부만 저장
            'customer_id': customer_id,
            'created_at': datetime.now().isoformat(),
            'expiry_value': expiry_value
        })

        return key

    def _derive_xor_key(self, salt: str) -> int:
        """Salt에서 XOR 키 유도 (20비트)"""
        combined = salt + self._SECRET_KEY
        hash_val = hashlib.md5(combined.encode()).hexdigest()
        return int(hash_val[:5], 16)  # 20비트 (0-1048575)

    def _calculate_checksum(self, data: str, salt: str) -> str:
        """체크섬 계산"""
        combined = data + salt + self._SECRET_KEY
        hash_val = hashlib.md5(combined.encode()).hexdigest()
        checksum_int = int(hash_val[:5], 16) % (32 ** 4)
        return self._encode_base32(checksum_int)

    def _encode_base32(self, value: int) -> str:
        """정수를 4자리 Base32 문자열로 인코딩"""
        chars = self._CHARSET
        result = ""
        value = value % (32 ** 4)  # 범위 제한
        for _ in range(4):
            result = chars[value % 32] + result
            value //= 32
        return result

    def _encode_version(self, version_str: str) -> int:
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

    def export_to_csv(self, filepath: str) -> bool:
        """생성된 키를 CSV로 내보내기"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['key', 'type', 'hardware_id', 'customer_id', 'created_at', 'expiry_value'])
                writer.writeheader()
                writer.writerows(self._generated_keys)
            return True
        except Exception as e:
            print(f"CSV 내보내기 실패: {e}")
            return False

    def export_to_json(self, filepath: str) -> bool:
        """생성된 키를 JSON으로 내보내기"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._generated_keys, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"JSON 내보내기 실패: {e}")
            return False

    @property
    def generated_keys(self) -> list:
        """생성된 키 목록"""
        return self._generated_keys.copy()


def authenticate():
    """암호 인증"""
    print("=" * 60)
    print("GARAMe Manager 라이선스 키 생성기")
    print("=" * 60)

    if not PasswordManager.is_password_set():
        # 첫 실행 - 암호 설정
        print("\n[첫 실행] 관리자 암호를 설정해 주세요.")
        print("(이 암호는 키 생성기 실행 시 필요합니다)")

        while True:
            password = getpass.getpass("새 암호 입력: ")
            if len(password) < 4:
                print("암호는 최소 4자 이상이어야 합니다.")
                continue

            confirm = getpass.getpass("암호 확인: ")
            if password != confirm:
                print("암호가 일치하지 않습니다. 다시 시도해 주세요.")
                continue

            if PasswordManager.set_password(password):
                print("\n암호가 설정되었습니다.")
                return True
            else:
                return False
    else:
        # 암호 확인
        for attempt in range(3):
            password = getpass.getpass("암호 입력: ")
            if PasswordManager.verify_password(password):
                print("\n인증 성공!")
                return True
            else:
                remaining = 2 - attempt
                if remaining > 0:
                    print(f"암호가 틀렸습니다. (남은 시도: {remaining}회)")
                else:
                    print("인증 실패. 프로그램을 종료합니다.")
                    return False

    return False


def main():
    """CLI 인터페이스"""
    import argparse

    # 먼저 인증
    if not authenticate():
        return

    parser = argparse.ArgumentParser(description="GARAMe Manager 라이선스 키 생성기")
    parser.add_argument('--type', '-t', choices=['trial', 'timed', 'perpetual', 'version'],
                        default='trial', help='라이선스 타입')
    parser.add_argument('--hwid', '-H', type=str, required=True,
                        help='대상 머신의 하드웨어 ID (32자리 16진수)')
    parser.add_argument('--customer', '-c', type=int, default=0, help='고객 ID')
    parser.add_argument('--days', '-d', type=int, default=7, help='유효 기간 (일)')
    parser.add_argument('--version', '-v', type=str, default='1.9.8.4', help='최대 버전')
    parser.add_argument('--count', '-n', type=int, default=1, help='생성 개수')
    parser.add_argument('--export', '-e', type=str, help='내보내기 파일 경로 (CSV/JSON)')

    args = parser.parse_args()

    # 하드웨어 ID 검증
    hwid = args.hwid.lower().replace('-', '').replace(' ', '')
    if len(hwid) != 32 or not all(c in '0123456789abcdef' for c in hwid):
        print("오류: 하드웨어 ID는 32자리 16진수여야 합니다.")
        print("예: 0fa3830468abd63dd985dd584540147d")
        return

    generator = LicenseKeyGenerator()

    print("\n" + "=" * 60)
    print(f"하드웨어 ID: {hwid[:8].upper()}-{hwid[8:16].upper()}-...")
    print("=" * 60)

    for i in range(args.count):
        if args.type == 'trial':
            key = generator.generate_trial_key(hwid, args.customer + i, args.days)
            print(f"\n테스트 키 ({args.days}일):")
        elif args.type == 'timed':
            key = generator.generate_timed_key(hwid, args.customer + i, args.days)
            print(f"\n기간 제한 키 ({args.days}일):")
        elif args.type == 'perpetual':
            key = generator.generate_perpetual_key(hwid, args.customer + i)
            print(f"\n영구 키:")
        elif args.type == 'version':
            key = generator.generate_version_key(hwid, args.customer + i, args.version)
            print(f"\n버전 제한 키 (최대 {args.version}):")

        print(f"  {key}")

    if args.export:
        ext = os.path.splitext(args.export)[1].lower()
        if ext == '.csv':
            generator.export_to_csv(args.export)
            print(f"\nCSV 내보내기: {args.export}")
        else:
            generator.export_to_json(args.export)
            print(f"\nJSON 내보내기: {args.export}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
