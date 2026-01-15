# -*- mode: python ; coding: utf-8 -*-
"""
GARAMe Manager v1.9.8.4 - PyInstaller 설정 파일
Ubuntu 25.10 전용 빌드

사용법:
    pyinstaller garame_manager.spec

주의사항:
    - 이 .spec 파일은 Ubuntu Linux에서만 빌드해야 합니다
    - macOS에서 빌드하면 Ubuntu에서 실행 불가
    - 빌드 전 모든 종속성이 설치되어 있어야 함
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 데이터 파일 수집
# 주의: 대용량 모델 파일은 제외하고 런타임에 외부에서 로드
datas = [
    ('VERSION.txt', '.'),
]

# 설정 파일 포함 (존재하는 경우)
import os
if os.path.exists('config.conf.example'):
    datas.append(('config.conf.example', '.'))
if os.path.exists('standard_defaults.conf'):
    datas.append(('standard_defaults.conf', '.'))

# safety_posters 디렉토리 포함 (존재하는 경우)
if os.path.exists('safety_posters'):
    datas.append(('safety_posters', 'safety_posters'))

# assets 디렉토리 포함 (로고, 이미지 등)
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))
    print(f"✓ assets 디렉토리 추가")

# config.conf 포함 (설정 파일)
if os.path.exists('config.conf'):
    datas.append(('config.conf', '.'))
    print(f"✓ config.conf 추가")

# OpenCV Haar Cascade 데이터 파일 수집 (얼굴 인식 백업용)
try:
    import cv2
    cv2_data_path = os.path.join(os.path.dirname(cv2.__file__), 'data')
    if os.path.exists(cv2_data_path):
        datas.append((cv2_data_path, 'cv2/data'))
        print(f"✓ OpenCV data 디렉토리 추가: {cv2_data_path}")
except Exception as e:
    print(f"⚠ OpenCV data 수집 실패: {e}")

# InsightFace 데이터 파일 수집
try:
    import insightface
    datas += collect_data_files('insightface', include_py_files=False)
    print(f"✓ InsightFace 데이터 파일 수집 완료")
except Exception as e:
    print(f"⚠ InsightFace 데이터 수집 실패 (계속 진행): {e}")

# ONNX Runtime 데이터 파일 수집
try:
    datas += collect_data_files('onnxruntime', include_py_files=False)
    print(f"✓ ONNX Runtime 데이터 파일 수집 완료")
except Exception as e:
    print(f"⚠ ONNX Runtime 데이터 수집 실패 (계속 진행): {e}")

print(f"✓ 총 {len(datas)}개 데이터 파일 수집됨")

# InsightFace 및 YOLOv11 모델 제외 (대용량 파일)
# 이 모델들은 배포 디렉토리에 별도로 포함되어 런타임에 로드됨
excludes_patterns = [
    '*.onnx',  # InsightFace 모델 (buffalo_l 등)
    '*.pt',    # YOLOv11 weights
    '*.pth',   # PyTorch 모델
    '*.pkl',   # Pickle 모델
]

# OpenCV 및 기타 바이너리 수집
binaries = []
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    import cv2
    import os

    # OpenCV 바이너리 수집
    cv2_libs = collect_dynamic_libs('cv2')
    if cv2_libs:
        binaries += cv2_libs
        print(f"✓ OpenCV 바이너리 수집 완료: {len(cv2_libs)}개 파일")
    else:
        # 대체 방법: cv2 설치 경로에서 직접 .so 파일 수집
        cv2_path = os.path.dirname(cv2.__file__)
        for root, dirs, files in os.walk(cv2_path):
            for file in files:
                if file.endswith(('.so', '.so.*')):
                    full_path = os.path.join(root, file)
                    # cv2/ 디렉토리에 복사
                    rel_path = os.path.relpath(full_path, cv2_path)
                    binaries.append((full_path, os.path.join('cv2', os.path.dirname(rel_path))))
                    print(f"  + 추가: {file}")

    # NumPy 바이너리 수집
    numpy_libs = collect_dynamic_libs('numpy')
    if numpy_libs:
        binaries += numpy_libs
        print(f"✓ NumPy 바이너리 수집 완료: {len(numpy_libs)}개 파일")

    # ONNX Runtime 바이너리 수집 (InsightFace 추론 엔진)
    try:
        onnx_libs = collect_dynamic_libs('onnxruntime')
        if onnx_libs:
            binaries += onnx_libs
            print(f"✓ ONNX Runtime 바이너리 수집 완료: {len(onnx_libs)}개 파일")
    except:
        pass

    # Pillow 바이너리 수집
    try:
        pillow_libs = collect_dynamic_libs('PIL')
        if pillow_libs:
            binaries += pillow_libs
            print(f"✓ Pillow 바이너리 수집 완료: {len(pillow_libs)}개 파일")
    except:
        pass

except Exception as e:
    print(f"Warning: Could not collect binaries: {e}")
    import traceback
    traceback.print_exc()

# Hidden imports (PyInstaller가 자동으로 찾지 못하는 모듈들)
hiddenimports = [
    # 표준 라이브러리
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.scrolledtext',
    'queue',
    'threading',
    'socket',
    'json',
    'datetime',
    'time',
    'logging',
    'configparser',
    'argparse',
    'platform',
    'subprocess',
    'collections',
    'unittest',
    'unittest.mock',

    # NumPy
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.random',
    'numpy.linalg',

    # OpenCV
    'cv2',
    'cv2.cv2',
    'cv2.data',

    # Pillow
    'PIL',
    'PIL._tkinter_finder',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',

    # Matplotlib
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_tkagg',

    # InsightFace (v1.9.5 얼굴 인식)
    'insightface',
    'insightface.app',
    'insightface.model_zoo',
    'insightface.utils',
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',

    # Ultralytics YOLOv11 (v1.9.5 PPE 감지)
    'ultralytics',
    'ultralytics.engine',
    'ultralytics.models',
    'ultralytics.models.yolo',
    'ultralytics.nn',
    'ultralytics.utils',
    'dill',  # YOLO 모델 로딩에 필요
    'torch',
    'torch.nn',
    'torch.optim',
    'torchvision',
    'torchvision.transforms',

    # gTTS (v1.9.5 음성 알림)
    'gtts',
    'gtts.tts',
    'gtts.lang',
    'pydub',
    'pydub.playback',

    # 시스템 제어
    'psutil',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'keyboard',
    'pystray',

    # 데이터 처리
    'pandas',
    'openpyxl',
    'skimage',
    'imageio',

    # setuptools 및 pkg_resources 의존성
    'pkg_resources',
    # 'pkg_resources.py2_warn',  # Python 2 전용 - 제거됨
    'jaraco',
    'jaraco.text',
    'jaraco.functools',
    'jaraco.context',
]

# src 모듈의 모든 서브모듈 수집
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('src.tcp_monitor')

# EasyOCR, PaddleOCR 데이터 수집 (설치되어 있는 경우)
# 주의: OCR 모델은 매우 크므로(1-2GB) 런타임에 별도로 다운로드하도록 함
# 빌드 크기를 줄이기 위해 주석 처리
# try:
#     datas += collect_data_files('easyocr')
# except:
#     pass

# try:
#     datas += collect_data_files('paddleocr')
# except:
#     pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 프레임워크 (불필요)
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',

        # 웹 프레임워크 (불필요)
        'django',
        'flask',
        'tornado',
        'fastapi',
        'aiohttp',

        # 테스트 도구 (불필요)
        'test',
        'tests',
        'pytest',
        # 'unittest',  # InsightFace/Ultralytics 의존성 - 제외하면 안됨

        # 문서화 도구 (불필요)
        'sphinx',
        'docutils',

        # 빌드 도구 (불필요)
        # 'setuptools',  # pkg_resources 의존성 - 제외하면 안됨
        # 'distutils',  # Python 3.13에서 제거됨 - 제외 목록에서 제거
        'wheel',

        # 개발 도구 (불필요)
        'IPython',
        'jupyter',
        'notebook',

        # v1.9.5에서 제거된 라이브러리
        # dlib, face_recognition은 InsightFace로 대체됨
        'pyttsx3',  # gTTS로 교체됨
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 대용량 모델 파일 제외 (파일 크기 최적화)
print("=" * 70)
print("대용량 모델 파일 제외 중...")
print("=" * 70)

filtered_datas = []
excluded_count = 0
excluded_size = 0

for item in a.datas:
    # a.datas의 각 항목은 (src, dest, typecode) 튜플임
    src = item[0]
    dest = item[1]

    exclude = False
    for pattern in excludes_patterns:
        import fnmatch
        if fnmatch.fnmatch(src, f"*{pattern}"):
            exclude = True
            excluded_count += 1
            try:
                import os
                if os.path.exists(src):
                    excluded_size += os.path.getsize(src)
            except:
                pass
            print(f"  제외: {os.path.basename(src)} ({pattern})")
            break

    if not exclude:
        filtered_datas.append(item)

a.datas = filtered_datas

print(f"\n✓ {excluded_count}개 대용량 파일 제외됨 ({excluded_size / 1024 / 1024:.1f} MB)")
print("=" * 70)
print()

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # --onefile 모드: 바이너리 포함
    a.zipfiles,      # --onefile 모드: zip 파일 포함
    a.datas,         # --onefile 모드: 데이터 파일 포함
    [],
    name='garame_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Ubuntu에서 strip 비활성화 (호환성 향상)
    upx=False,  # Ubuntu에서 UPX 비활성화 (안정성 향상)
    upx_exclude=[],
    runtime_tmpdir=None,  # 시스템 임시 디렉토리 사용
    console=True,  # 콘솔 출력 활성화 (디버깅용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --onefile 모드에서는 COLLECT 불필요
# coll = COLLECT(...)
