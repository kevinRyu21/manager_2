"""
하드웨어 ID 생성 모듈

머신 고유 식별자를 생성하여 라이선스를 특정 컴퓨터에 바인딩합니다.

고정된 하드웨어 값만 사용:
- 머신 UUID (/etc/machine-id)
- MAC 주소
- 디스크 시리얼 번호

변경 가능한 값 (사용 안 함):
- IP 주소 (유동적)
- 호스트명 (변경 가능)
- 사용자명 (변경 가능)
"""

import hashlib
import platform
import subprocess
import uuid
import os
import re
from typing import Optional, List


class HardwareID:
    """하드웨어 기반 머신 고유 ID 생성"""

    _cached_id: Optional[str] = None
    _cached_components: Optional[List[str]] = None

    @classmethod
    def get_machine_id(cls) -> str:
        """
        머신 고유 ID 반환 (캐싱됨)

        고정된 하드웨어 값만 사용하여 생성:
        - 머신 UUID
        - MAC 주소
        - 디스크 시리얼 번호

        Returns:
            32자리 16진수 문자열 (MD5 해시)
        """
        if cls._cached_id:
            return cls._cached_id

        # 고정된 하드웨어 정보만 수집 (변경되지 않는 값들)
        components = []

        # 1. 머신 UUID (Linux - /etc/machine-id)
        # OS 설치 시 생성되며 재설치 전까지 변경되지 않음
        machine_uuid = cls._get_linux_machine_uuid()
        if machine_uuid:
            components.append(f"uuid:{machine_uuid}")

        # 2. MAC 주소 (네트워크 카드 하드웨어 고유 값)
        # 네트워크 카드 교체 전까지 변경되지 않음
        mac_address = cls._get_mac_address()
        if mac_address:
            components.append(f"mac:{mac_address}")

        # 3. 디스크 시리얼 번호 (루트 파티션 디스크)
        # 디스크 교체 전까지 변경되지 않음
        disk_serial = cls._get_disk_serial()
        if disk_serial:
            components.append(f"disk:{disk_serial}")

        # 4. CPU 정보 (고정값 - 모델명만)
        cpu_info = cls._get_cpu_info()
        if cpu_info:
            components.append(f"cpu:{cpu_info}")

        # 최소 2개 이상의 하드웨어 값이 필요
        if len(components) < 2:
            # 폴백: 시스템 정보 추가
            system_info = f"{platform.system()}-{platform.machine()}"
            components.append(f"sys:{system_info}")

        # 캐시 저장 (디버깅용)
        cls._cached_components = components.copy()

        # 모든 컴포넌트 합쳐서 해시 생성
        combined = "|".join(sorted(components))
        cls._cached_id = hashlib.md5(combined.encode()).hexdigest()

        return cls._cached_id

    @classmethod
    def get_display_id(cls) -> str:
        """
        표시용 머신 ID (8자리 그룹)

        Returns:
            "XXXX-XXXX-XXXX-XXXX" 형식
        """
        machine_id = cls.get_machine_id()
        return f"{machine_id[:4]}-{machine_id[4:8]}-{machine_id[8:12]}-{machine_id[12:16]}".upper()

    @staticmethod
    def _get_linux_machine_uuid() -> Optional[str]:
        """Linux 머신 UUID 가져오기"""
        try:
            # /etc/machine-id (systemd)
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()

            # /var/lib/dbus/machine-id (fallback)
            if os.path.exists('/var/lib/dbus/machine-id'):
                with open('/var/lib/dbus/machine-id', 'r') as f:
                    return f.read().strip()

            # dmidecode (root 권한 필요)
            result = subprocess.run(
                ['sudo', 'dmidecode', '-s', 'system-uuid'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except Exception:
            pass

        return None

    @staticmethod
    def _get_mac_address() -> Optional[str]:
        """주 네트워크 인터페이스 MAC 주소 가져오기"""
        try:
            # uuid.getnode()는 MAC 주소를 정수로 반환
            mac = uuid.getnode()
            # 가상 MAC 주소 체크 (첫 바이트 LSB가 1이면 가상)
            if (mac >> 40) & 1:
                return None
            return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(40, -1, -8))
        except Exception:
            return None

    @staticmethod
    def _get_disk_serial() -> Optional[str]:
        """루트 파티션 디스크의 시리얼 번호 가져오기"""
        try:
            # 방법 1: lsblk로 루트 디바이스 찾기
            result = subprocess.run(
                ['lsblk', '-no', 'SERIAL', '-d'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                serials = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
                if serials:
                    return serials[0]

            # 방법 2: /sys/block에서 직접 읽기
            for device in ['sda', 'nvme0n1', 'vda', 'hda']:
                serial_path = f'/sys/block/{device}/device/serial'
                if os.path.exists(serial_path):
                    with open(serial_path, 'r') as f:
                        serial = f.read().strip()
                        if serial:
                            return serial

            # 방법 3: hdparm 사용 (root 권한 필요할 수 있음)
            result = subprocess.run(
                ['hdparm', '-I', '/dev/sda'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Serial Number' in line:
                        serial = line.split(':')[-1].strip()
                        if serial:
                            return serial

        except Exception:
            pass

        return None

    @staticmethod
    def _get_cpu_info() -> Optional[str]:
        """CPU 모델 정보 가져오기 (고정값)"""
        try:
            # /proc/cpuinfo에서 모델명 추출
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            # "model name : Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz"
                            model = line.split(':')[-1].strip()
                            # 공백 정규화
                            model = re.sub(r'\s+', ' ', model)
                            return model
        except Exception:
            pass

        return None

    @classmethod
    def verify_hardware(cls, stored_id: str) -> bool:
        """
        저장된 하드웨어 ID와 현재 머신 비교

        Args:
            stored_id: 저장된 머신 ID

        Returns:
            True if match, False otherwise
        """
        current_id = cls.get_machine_id()
        return current_id == stored_id

    @classmethod
    def get_hardware_info(cls) -> dict:
        """
        디버깅/표시용 하드웨어 정보 반환
        """
        # ID 생성을 위해 get_machine_id 호출 (캐시가 없으면 생성)
        _ = cls.get_machine_id()

        return {
            'machine_id': cls.get_display_id(),
            'components': cls._cached_components or [],
            'component_count': len(cls._cached_components or []),
            'system': platform.system(),
            'machine': platform.machine(),
            'python_version': platform.python_version()
        }

    @classmethod
    def get_binding_salt(cls) -> str:
        """
        라이선스 키 생성용 하드웨어 바인딩 Salt 반환

        Returns:
            8자리 16진수 문자열 (하드웨어 ID의 일부)
        """
        machine_id = cls.get_machine_id()
        # 하드웨어 ID의 처음 8자리 사용
        return machine_id[:8].upper()

    @classmethod
    def clear_cache(cls):
        """캐시 초기화 (테스트용)"""
        cls._cached_id = None
        cls._cached_components = None


if __name__ == '__main__':
    # 테스트
    print("=" * 60)
    print("하드웨어 ID 테스트")
    print("=" * 60)

    # 캐시 초기화 (테스트를 위해)
    HardwareID.clear_cache()

    print(f"\n[Machine ID] {HardwareID.get_machine_id()}")
    print(f"[Display ID] {HardwareID.get_display_id()}")
    print(f"[Binding Salt] {HardwareID.get_binding_salt()}")

    print("\n[수집된 하드웨어 컴포넌트]")
    info = HardwareID.get_hardware_info()
    for comp in info['components']:
        print(f"  - {comp}")

    print(f"\n[컴포넌트 수] {info['component_count']}개")
    print(f"[시스템] {info['system']} / {info['machine']}")
    print(f"[Python] {info['python_version']}")

    # 개별 하드웨어 값 테스트
    print("\n[개별 하드웨어 값 테스트]")
    print(f"  UUID: {HardwareID._get_linux_machine_uuid()}")
    print(f"  MAC: {HardwareID._get_mac_address()}")
    print(f"  Disk Serial: {HardwareID._get_disk_serial()}")
    print(f"  CPU: {HardwareID._get_cpu_info()}")

    print("\n" + "=" * 60)
