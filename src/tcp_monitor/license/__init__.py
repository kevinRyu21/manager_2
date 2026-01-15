"""
GARAMe Manager 라이선스 모듈

정품 등록 및 불법 복사 방지 시스템
"""

from .key_validator import LicenseKeyValidator
from .hardware_id import HardwareID
from .license_manager import LicenseManager, LicenseInfo, LicenseType

__all__ = [
    'LicenseKeyValidator',
    'HardwareID',
    'LicenseManager',
    'LicenseInfo',
    'LicenseType'
]
