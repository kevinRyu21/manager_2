"""
공통 헬퍼 함수들
"""

import os
import sys
import datetime


# 기본 디렉토리 캐시 (성능 향상)
_BASE_DIR_CACHE = None


def get_base_dir():
    """
    애플리케이션 기본 디렉토리 반환 (PyInstaller 호환)

    PyInstaller로 빌드된 실행 파일에서는 실행 파일이 있는 디렉토리를,
    일반 Python 실행에서는 프로젝트 루트 디렉토리를 반환합니다.

    중요: 데이터 저장용 경로는 반드시 이 함수를 사용해야 합니다.
    sys._MEIPASS는 임시 디렉토리이므로 데이터 저장에 사용하면 안됩니다.

    Returns:
        str: 애플리케이션 기본 디렉토리 경로
    """
    global _BASE_DIR_CACHE

    if _BASE_DIR_CACHE is not None:
        return _BASE_DIR_CACHE

    if getattr(sys, 'frozen', False):
        # PyInstaller 실행 파일: 실행 파일이 있는 디렉토리
        # 주의: sys._MEIPASS는 임시 디렉토리이므로 사용하지 않음
        _BASE_DIR_CACHE = os.path.dirname(sys.executable)
    else:
        # 일반 Python 실행: 프로젝트 루트 디렉토리
        # helpers.py 위치: src/tcp_monitor/utils/helpers.py
        # 프로젝트 루트: 4단계 상위
        _BASE_DIR_CACHE = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )

    return _BASE_DIR_CACHE


def get_data_dir(subdir: str = None):
    """
    데이터 저장용 디렉토리 경로 반환

    Args:
        subdir: 하위 디렉토리 이름 (예: 'face_db', 'safety_photos', 'logs')

    Returns:
        str: 데이터 디렉토리 경로 (자동 생성됨)
    """
    base = get_base_dir()
    if subdir:
        path = os.path.join(base, subdir)
    else:
        path = base

    # 디렉토리가 없으면 생성
    os.makedirs(path, exist_ok=True)
    return path


# 상수 정의
SENSOR_KEYS = ["co2", "o2", "h2s", "co", "lel", "smoke", "temperature", "humidity", "water"]

# 센서 아이콘 매핑
SENSOR_ICONS = {
    "co2": "🏭",        # 이산화탄소 - 공장/산업
    "o2": "💨",         # 산소 - 바람/공기
    "h2s": "☠️",        # 황화수소 - 독성
    "co": "🔥",         # 일산화탄소 - 연소가스
    "lel": "⚡",        # 가연성가스 - 폭발위험
    "smoke": "🌫️",     # 연기 - 안개/연기
    "temperature": "🌡️",  # 온도 - 온도계
    "humidity": "💧",   # 습도 - 물방울
    "water": "🚿"       # 누수 - 샤워기/물
}

# 센서 한글 이름 매핑
SENSOR_NAMES = {
    "co2": "이산화탄소",
    "o2": "산소",
    "h2s": "황화수소",
    "co": "일산화탄소",
    "lel": "가연성가스",
    "smoke": "연기",
    "temperature": "온도",
    "humidity": "습도",
    "water": "누수"
}

# 센서 단위 매핑
SENSOR_UNITS = {
    "co2": "ppm",
    "o2": "%",
    "h2s": "ppm",
    "co": "ppm",
    "lel": "%",
    "smoke": "ppm",
    "temperature": "℃",
    "humidity": "%",
    "water": ""
}

# 색상 상수
COLOR_BG = "#E3F2FD"  # 파랑색 계통 배경
COLOR_TILE_OK = "#2ECC71"  # 정상 상태 - 초록색
COLOR_ALARM = "#E53935"  # 경보 상태 - 빨간색
COLOR_FG = "#FFFFFF"  # 텍스트 색상을 흰색으로 변경

# 5단계 경보 색상 정의
ALERT_COLORS = {
    1: "#2ECC71",  # 정상 - 초록색
    2: "#F1C40F",  # 관심 - 노랑색
    3: "#E67E22",  # 주의 - 주황색
    4: "#E74C3C",  # 경계 - 빨간색
    5: "#C0392B"   # 심각 - 진홍색
}


def now_local():
    """현재 로컬 시간 반환"""
    return datetime.datetime.now()


def fmt_ts(ts=None):
    """타임스탬프를 포맷된 문자열로 변환"""
    d = datetime.datetime.fromtimestamp(ts) if ts else now_local()
    return d.strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path):
    """디렉토리가 존재하지 않으면 생성"""
    os.makedirs(path, exist_ok=True)


def ideal_fg(bg_hex):
    """배경색에 맞는 이상적인 전경색 반환"""
    try:
        bg = bg_hex.lstrip("#")
        r, g, b = int(bg[:2], 16), int(bg[2:4], 16), int(bg[4:], 16)
        return "#000000" if (0.299*r + 0.587*g + 0.114*b) > 160 else "#FFFFFF"
    except:
        return COLOR_FG


def find_asset(*names):
    """assets 폴더에서 파일 찾기 (PyInstaller 호환)"""
    import sys

    # 기준 디렉토리 결정
    if getattr(sys, 'frozen', False):
        # PyInstaller 실행 파일: 실행 파일이 있는 디렉토리
        base_dir = os.path.dirname(sys.executable)
    else:
        # 일반 Python: 현재 작업 디렉토리
        base_dir = os.getcwd()

    for n in names:
        if not n:
            continue
        # assets/ 폴더에서 먼저 찾기
        p = os.path.join(base_dir, "assets", n)
        if os.path.exists(p):
            return p
        # 기준 디렉토리에서 직접 찾기
        p = os.path.join(base_dir, n)
        if os.path.exists(p):
            return p
    return None


def get_system_specs():
    """
    시스템 사양 분석 및 추천 성능 모드 반환

    Returns:
        dict: {
            'cpu_name': CPU 이름,
            'cpu_cores': CPU 코어 수,
            'cpu_score': CPU 점수 (1-100),
            'ram_gb': RAM 용량 (GB),
            'gpu_name': GPU 이름 (없으면 None),
            'gpu_vram_gb': GPU VRAM (GB, 없으면 0),
            'gpu_available': GPU 사용 가능 여부,
            'recommended_mode': 추천 모드 (1, 2, 3),
            'recommended_reason': 추천 이유
        }
    """
    import platform
    import subprocess

    result = {
        'cpu_name': 'Unknown',
        'cpu_cores': 1,
        'cpu_score': 0,
        'ram_gb': 0,
        'gpu_name': None,
        'gpu_vram_gb': 0,
        'gpu_available': False,
        'recommended_mode': 1,
        'recommended_reason': ''
    }

    # === CPU 정보 ===
    try:
        import multiprocessing
        result['cpu_cores'] = multiprocessing.cpu_count()
    except:
        pass

    # Linux CPU 이름
    try:
        if platform.system() == 'Linux':
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        result['cpu_name'] = line.split(':')[1].strip()
                        break
        elif platform.system() == 'Windows':
            result['cpu_name'] = platform.processor()
    except:
        pass

    # CPU 점수 계산 (이름 기반)
    cpu_name_lower = result['cpu_name'].lower()
    cpu_score = 30  # 기본 점수

    # Intel CPU 점수
    if 'n5095' in cpu_name_lower or 'n5105' in cpu_name_lower or 'celeron' in cpu_name_lower:
        cpu_score = 20
    elif 'n100' in cpu_name_lower or 'n200' in cpu_name_lower:
        cpu_score = 25
    elif 'i3' in cpu_name_lower:
        if '12' in cpu_name_lower or '13' in cpu_name_lower or '14' in cpu_name_lower:
            cpu_score = 55
        elif '10' in cpu_name_lower or '11' in cpu_name_lower:
            cpu_score = 45
        else:
            cpu_score = 35
    elif 'i5' in cpu_name_lower:
        if '12' in cpu_name_lower or '13' in cpu_name_lower or '14' in cpu_name_lower:
            cpu_score = 70
        elif '10' in cpu_name_lower or '11' in cpu_name_lower:
            cpu_score = 60
        else:
            cpu_score = 50
    elif 'i7' in cpu_name_lower:
        if '12' in cpu_name_lower or '13' in cpu_name_lower or '14' in cpu_name_lower:
            cpu_score = 85
        elif '10' in cpu_name_lower or '11' in cpu_name_lower:
            cpu_score = 75
        else:
            cpu_score = 65
    elif 'i9' in cpu_name_lower:
        cpu_score = 95
    # AMD CPU 점수
    elif 'ryzen' in cpu_name_lower:
        if 'ryzen 3' in cpu_name_lower:
            cpu_score = 45
        elif 'ryzen 5' in cpu_name_lower:
            cpu_score = 65
        elif 'ryzen 7' in cpu_name_lower:
            cpu_score = 80
        elif 'ryzen 9' in cpu_name_lower:
            cpu_score = 95

    # 코어 수 보너스
    if result['cpu_cores'] >= 8:
        cpu_score = min(100, cpu_score + 10)
    elif result['cpu_cores'] >= 6:
        cpu_score = min(100, cpu_score + 5)

    result['cpu_score'] = cpu_score

    # === RAM 정보 ===
    try:
        if platform.system() == 'Linux':
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        result['ram_gb'] = round(kb / 1024 / 1024, 1)
                        break
        elif platform.system() == 'Windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulong = ctypes.c_ulong

            class MEMORYSTATUS(ctypes.Structure):
                _fields_ = [
                    ('dwLength', c_ulong),
                    ('dwMemoryLoad', c_ulong),
                    ('dwTotalPhys', c_ulong),
                    ('dwAvailPhys', c_ulong),
                    ('dwTotalPageFile', c_ulong),
                    ('dwAvailPageFile', c_ulong),
                    ('dwTotalVirtual', c_ulong),
                    ('dwAvailVirtual', c_ulong)
                ]

            memory_status = MEMORYSTATUS()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUS)
            kernel32.GlobalMemoryStatus(ctypes.byref(memory_status))
            result['ram_gb'] = round(memory_status.dwTotalPhys / 1024 / 1024 / 1024, 1)
    except:
        pass

    # === GPU 정보 (PyTorch/CUDA) ===
    try:
        import torch
        if torch.cuda.is_available():
            result['gpu_available'] = True
            result['gpu_name'] = torch.cuda.get_device_name(0)

            # VRAM 용량 (GB)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            result['gpu_vram_gb'] = round(vram_bytes / 1024 / 1024 / 1024, 1)
    except:
        pass

    # nvidia-smi로 추가 확인 (PyTorch 없는 경우)
    if not result['gpu_available']:
        try:
            output = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
                                            stderr=subprocess.DEVNULL, timeout=5)
            lines = output.decode().strip().split('\n')
            if lines and lines[0]:
                parts = lines[0].split(',')
                result['gpu_name'] = parts[0].strip()
                result['gpu_vram_gb'] = round(float(parts[1].strip()) / 1024, 1)
                result['gpu_available'] = True
        except:
            pass

    # === 추천 모드 결정 ===
    gpu_score = 0
    if result['gpu_available'] and result['gpu_name']:
        gpu_name_lower = result['gpu_name'].lower()
        # NVIDIA GPU 점수
        if 'rtx 40' in gpu_name_lower:
            gpu_score = 100
        elif 'rtx 30' in gpu_name_lower:
            if '3090' in gpu_name_lower or '3080' in gpu_name_lower:
                gpu_score = 90
            elif '3070' in gpu_name_lower:
                gpu_score = 80
            elif '3060' in gpu_name_lower:
                gpu_score = 70
            else:
                gpu_score = 60
        elif 'rtx 20' in gpu_name_lower:
            gpu_score = 55
        elif 'gtx 16' in gpu_name_lower:
            gpu_score = 45
        elif 'gtx 10' in gpu_name_lower:
            gpu_score = 35
        else:
            gpu_score = 30

        # VRAM 보너스
        if result['gpu_vram_gb'] >= 12:
            gpu_score = min(100, gpu_score + 10)
        elif result['gpu_vram_gb'] >= 8:
            gpu_score = min(100, gpu_score + 5)

    # 최종 추천 결정
    ram_ok = result['ram_gb'] >= 8
    ram_good = result['ram_gb'] >= 16

    if gpu_score >= 70 and cpu_score >= 65 and ram_good:
        # 고급 모드: GPU RTX 3060+, CPU i7급+, RAM 16GB+
        result['recommended_mode'] = 3
        result['recommended_reason'] = f"GPU {result['gpu_name']} ({result['gpu_vram_gb']}GB) + {result['cpu_cores']}코어 CPU 감지"
    elif cpu_score >= 50 and ram_ok:
        # 표준 모드: i5급 이상, RAM 8GB+
        result['recommended_mode'] = 2
        if gpu_score >= 45:
            result['recommended_reason'] = f"CPU {cpu_score}점 + GPU 지원 가능 (RAM {result['ram_gb']}GB)"
        else:
            result['recommended_reason'] = f"CPU {cpu_score}점 (i5/Ryzen5급), RAM {result['ram_gb']}GB"
    else:
        # 기본 모드: 저사양
        result['recommended_mode'] = 1
        result['recommended_reason'] = f"저사양 시스템 감지 (CPU {cpu_score}점, RAM {result['ram_gb']}GB)"

    return result


def get_system_specs_summary():
    """시스템 사양 요약 문자열 반환"""
    specs = get_system_specs()

    lines = []
    lines.append(f"CPU: {specs['cpu_name'][:40]}... ({specs['cpu_cores']}코어)" if len(specs['cpu_name']) > 40 else f"CPU: {specs['cpu_name']} ({specs['cpu_cores']}코어)")
    lines.append(f"RAM: {specs['ram_gb']} GB")

    if specs['gpu_available']:
        lines.append(f"GPU: {specs['gpu_name']} ({specs['gpu_vram_gb']}GB VRAM)")
    else:
        lines.append("GPU: 없음 (CPU 모드)")

    return '\n'.join(lines), specs['recommended_mode'], specs['recommended_reason']


# ============================================================
# 성능 모드별 최적화 설정
# ============================================================
# 모드 1: 기본 (저사양 - N5095, Celeron 등)
# 모드 2: 표준 (중사양 - i5, i7, Ryzen 5/7)
# 모드 3: 고급 (고사양 - i7/i9 + RTX 3060+)

PERFORMANCE_MODE_SETTINGS = {
    # === 모드 1: 기본 (얼굴 인식만) - 저사양 최적화 ===
    1: {
        'name': '기본 모드',
        'description': '얼굴 인식만 수행 (저사양 PC용)',

        # InsightFace 설정
        'insightface': {
            'model_name': 'buffalo_sc',      # 경량 모델 (가장 빠름)
            'det_size': (320, 320),           # 작은 감지 크기 (빠름)
            'det_thresh': 0.4,                # 낮은 임계값 (인식률↑)
            'providers': ['CPUExecutionProvider'],
        },

        # YOLO 설정 (모드 1에서는 사용 안 함)
        'yolo_ppe': {
            'enabled': False,
            'model': None,
            'imgsz': 640,
            'conf': 0.25,
            'half': False,
        },

        # YOLO COCO 설정 (모드 1에서는 사용 안 함)
        'yolo_coco': {
            'enabled': False,
            'model': None,
            'imgsz': 640,
            'conf': 0.25,
            'half': False,
        },

        # 예상 성능
        'expected_fps': '15-25 FPS',
        'expected_latency': '0.2-0.4초',
    },

    # === 모드 2: 표준 (얼굴 + 안전장구) - 중사양 최적화 ===
    2: {
        'name': '표준 모드',
        'description': '얼굴 + 안전장구 6종 인식',

        # InsightFace 설정
        'insightface': {
            'model_name': 'buffalo_sc',      # 경량 모델 (속도 우선)
            'det_size': (320, 320),           # 균형 잡힌 크기
            'det_thresh': 0.4,                # 표준 임계값
            'providers': ['CPUExecutionProvider'],
        },

        # YOLO PPE 설정 (안전장구 6종)
        'yolo_ppe': {
            'enabled': True,
            'model': 'ppe_full.pt',           # PPE 전체 모델 (helmet, vest, gloves, goggles, mask)
            'model_fallback': 'ppe_helmet_vest.pt',  # 폴백: 경량 모델
            'imgsz': 640,                     # 표준 해상도
            'conf': 0.25,                     # 표준 신뢰도
            'half': False,                    # CPU에서는 FP32
        },

        # YOLO COCO 설정 (모드 2에서는 사용 안 함)
        'yolo_coco': {
            'enabled': False,
            'model': None,
            'imgsz': 640,
            'conf': 0.25,
            'half': False,
        },

        # 예상 성능
        'expected_fps': '8-15 FPS',
        'expected_latency': '0.3-0.5초',
    },

    # === 모드 3: 고급 (전체 AI) - 고사양 GPU 최적화 ===
    3: {
        'name': '고급 모드',
        'description': '얼굴 + 안전장구 + 사물 80종 인식',

        # InsightFace 설정 (GPU 가속)
        'insightface': {
            'model_name': 'buffalo_l',        # 고정밀 모델 (98.34%)
            'det_size': (640, 640),           # 고해상도 (정확도↑)
            'det_thresh': 0.35,               # 낮은 임계값 (더 많이 감지)
            'providers': ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        },

        # YOLO PPE 설정 (안전장구 고정밀)
        'yolo_ppe': {
            'enabled': True,
            'model': 'ppe_full.pt',           # 고정밀 모델 (50MB)
            'model_fallback': 'ppe_yolov8m.pt',
            'imgsz': 1280,                    # 고해상도
            'conf': 0.2,                      # 낮은 신뢰도 (더 많이 감지)
            'half': True,                     # FP16 (GPU 최적화)
        },

        # YOLO COCO 설정 (사물 80종)
        'yolo_coco': {
            'enabled': True,
            'model': 'yolo11m.pt',            # Medium 모델 (균형)
            'imgsz': 640,                     # 표준 해상도
            'conf': 0.3,                      # 표준 신뢰도
            'half': True,                     # FP16 (GPU 최적화)
        },

        # 예상 성능
        'expected_fps': '15-30 FPS (GPU)',
        'expected_latency': '0.2-0.4초',
    },
}


def get_performance_settings(mode: int = 2) -> dict:
    """
    성능 모드에 따른 설정 반환

    Args:
        mode: 성능 모드 (1: 기본, 2: 표준, 3: 고급)

    Returns:
        해당 모드의 설정 딕셔너리
    """
    mode = max(1, min(3, mode))  # 1~3 범위 제한
    return PERFORMANCE_MODE_SETTINGS.get(mode, PERFORMANCE_MODE_SETTINGS[2])
