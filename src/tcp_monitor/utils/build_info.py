"""
빌드 정보 관리 유틸리티
"""
import os
import json
from pathlib import Path


class BuildInfo:
    """빌드 정보 관리 클래스"""

    def __init__(self):
        """빌드 정보 초기화"""
        self.base_dir = Path(os.getcwd())
        self.version_file = self.base_dir / "VERSION.txt"
        self.build_file = self.base_dir / "BUILD.txt"
        self.version_info_file = self.base_dir / "VERSION_INFO.json"

        self._version = None
        self._build = None
        self._version_info = None

    @property
    def version(self):
        """버전 번호 가져오기"""
        if self._version is None:
            self._load_version()
        return self._version

    @property
    def build(self):
        """빌드 번호 가져오기"""
        if self._build is None:
            self._load_build()
        return self._build

    @property
    def version_info(self):
        """버전 정보 가져오기"""
        if self._version_info is None:
            self._load_version_info()
        return self._version_info

    def _load_version(self):
        """VERSION.txt에서 버전 읽기"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    self._version = f.read().strip()
            else:
                self._version = "Unknown"
        except Exception as e:
            print(f"버전 정보 로드 실패: {e}")
            self._version = "Unknown"

    def _load_build(self):
        """BUILD.txt에서 빌드 번호 읽기"""
        try:
            if self.build_file.exists():
                with open(self.build_file, 'r', encoding='utf-8') as f:
                    self._build = int(f.read().strip())
            else:
                self._build = 0
        except Exception as e:
            print(f"빌드 번호 로드 실패: {e}")
            self._build = 0

    def _load_version_info(self):
        """VERSION_INFO.json에서 상세 정보 읽기"""
        try:
            if self.version_info_file.exists():
                with open(self.version_info_file, 'r', encoding='utf-8') as f:
                    self._version_info = json.load(f)
            else:
                self._version_info = {
                    "version": self.version,
                    "build": self.build,
                    "release_date": "Unknown",
                    "description": "No description"
                }
        except Exception as e:
            print(f"버전 정보 JSON 로드 실패: {e}")
            self._version_info = {
                "version": self.version,
                "build": self.build,
                "release_date": "Unknown",
                "description": "No description"
            }

    def get_full_version_string(self):
        """전체 버전 문자열 반환 (예: v1.9.3 (Build 25251112))"""
        return f"v{self.version} (Build {self.build})"

    def get_short_version_string(self):
        """짧은 버전 문자열 반환 (예: 1.9.3-25251112)"""
        return f"{self.version}-{self.build}"

    def is_newer_than(self, other_build):
        """다른 빌드보다 최신인지 확인"""
        try:
            return self.build > int(other_build)
        except:
            return False

    def is_compatible_with(self, target_version, target_build):
        """특정 버전/빌드와 호환되는지 확인"""
        # 같은 메이저.마이너 버전이면 호환
        try:
            current_parts = self.version.split('.')
            target_parts = target_version.split('.')

            if len(current_parts) >= 2 and len(target_parts) >= 2:
                return (current_parts[0] == target_parts[0] and
                       current_parts[1] == target_parts[1])
            return False
        except:
            return False


# 싱글톤 인스턴스
_build_info_instance = None

def get_build_info():
    """빌드 정보 싱글톤 인스턴스 가져오기"""
    global _build_info_instance
    if _build_info_instance is None:
        _build_info_instance = BuildInfo()
    return _build_info_instance
