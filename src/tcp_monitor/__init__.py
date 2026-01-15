"""
TCP Monitor 패키지

센서 데이터를 실시간으로 모니터링하는 TCP 기반 애플리케이션입니다.
"""

import os
import sys

def _load_version():
    """VERSION.txt 파일에서 버전 정보 로드"""
    try:
        # PyInstaller 호환 경로 설정
        if getattr(sys, 'frozen', False):
            # PyInstaller 실행 파일: 실행 파일이 있는 디렉토리
            pkg_root = os.path.dirname(sys.executable)
        else:
            # 일반 Python 실행: 프로젝트 루트 디렉토리
            pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        version_file = os.path.join(pkg_root, "VERSION.txt")

        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass

    # 파일을 찾을 수 없으면 기본값 반환
    return "1.9.8.4"

__version__ = _load_version()
__author__ = "TCP Monitor Team"
__description__ = "Real-time sensor data monitoring application"

from .config import ConfigManager
from .logging import LogManager
from .network import TcpServer
from .sensor import SensorHistory, AlertManager
from .ui import App, SensorPanel
from .utils import (
    now_local, fmt_ts, ensure_dir, ideal_fg, find_asset,
    get_base_dir, get_data_dir,
    SENSOR_KEYS, SENSOR_ICONS, SENSOR_NAMES, SENSOR_UNITS,
    COLOR_BG, COLOR_TILE_OK, COLOR_ALARM, COLOR_FG,
    heat_index_c, discomfort_index
)

__all__ = [
    'ConfigManager',
    'LogManager',
    'TcpServer',
    'SensorHistory',
    'AlertManager',
    'App',
    'SensorPanel',
    'now_local',
    'fmt_ts',
    'ensure_dir',
    'ideal_fg',
    'find_asset',
    'get_base_dir',
    'get_data_dir',
    'SENSOR_KEYS',
    'SENSOR_ICONS',
    'SENSOR_NAMES',
    'SENSOR_UNITS',
    'COLOR_BG',
    'COLOR_TILE_OK',
    'COLOR_ALARM',
    'COLOR_FG',
    'heat_index_c',
    'discomfort_index',
]
