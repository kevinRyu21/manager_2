# GARAMe Manager v1.9.5 - 빌드 크기 최적화

## 📦 변경 사항

### 이전 (--onefile 모드)
- **빌드 결과**: 단일 실행 파일 `garame_manager`
- **파일 크기**: **4.1GB** 🔴
- **문제점**:
  - 모든 라이브러리, 모델, 데이터를 하나의 파일에 압축
  - InsightFace 모델 (buffalo_l: ~1.5GB)
  - YOLOv11 weights (~500MB)
  - OpenCV, NumPy, Ultralytics 바이너리 (~2GB)
  - 실행 시 임시 디렉토리에 압축 해제 (느림)

### 현재 (--onedir 모드) ✅
- **빌드 결과**: `dist/garame_manager/` 디렉토리
- **예상 크기**: **~300-500MB** 🟢
- **장점**:
  - Python 바이트코드만 번들링
  - 대용량 모델 파일 제외 (외부 로드)
  - 빠른 시작 시간
  - 디버깅 용이

---

## 🗂️ 새로운 디렉토리 구조

```
dist/garame_manager/
├── garame_manager           # 메인 실행 파일 (작음)
├── _internal/               # 내부 라이브러리
│   ├── libpython3.so
│   ├── cv2/
│   ├── numpy/
│   └── ... (Python 런타임)
└── base_library.zip         # 표준 라이브러리
```

### 외부 파일 (배포시 함께 제공)
```
배포_디렉토리/
├── garame_manager/          # PyInstaller 빌드
│   ├── garame_manager       # 실행 파일
│   └── _internal/           # 런타임 라이브러리
├── models/                  # AI 모델 (외부)
│   ├── insightface/
│   │   └── buffalo_l/       # ~1.5GB
│   └── yolov11/
│       └── best.pt          # ~500MB
├── config/
│   └── config.ini
├── safety_posters/
├── safety_photos/
└── garame_manager.sh        # 실행 스크립트
```

---

## 🚀 사용 방법

### 1. 빌드

```bash
cd ~/바탕화면/1.9.5
source venv/bin/activate
pyinstaller --clean garame_manager.spec
```

**빌드 출력**:
```
Building EXE from EXE-00.toc completed successfully.
Building COLLECT COLLECT-00.toc
Building COLLECT COLLECT-00.toc completed successfully.
```

### 2. 실행

```bash
# 방법 1: 직접 실행
./dist/garame_manager/garame_manager

# 방법 2: 배포 스크립트 사용
./garame_manager.sh
```

### 3. 배포

```bash
# 배포 패키지 생성
./create_distribution.sh

# 결과:
# GARAMe_Manager_1.9.5_Ubuntu25_Distribution/
# ├── garame_manager/        (빌드 결과)
# ├── garame_manager.sh      (실행 스크립트)
# ├── models/                (외부 모델)
# └── ...
```

---

## 🔧 garame_manager.spec 변경 내역

### 1. --onefile → --onedir 모드

**이전**:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # ❌ 모든 바이너리 포함
    a.zipfiles,      # ❌ 모든 zip 파일 포함
    a.datas,         # ❌ 모든 데이터 포함
    ...
)
```

**현재**:
```python
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # ✅ 바이너리 분리
    ...
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    name='garame_manager',
)
```

### 2. 대용량 모델 파일 제외

```python
# 제외 패턴 정의
excludes_patterns = [
    '*.onnx',  # InsightFace 모델 (buffalo_l 등)
    '*.pt',    # YOLOv11 weights
    '*.pth',   # PyTorch 모델
    '*.pkl',   # Pickle 모델
]

# 빌드 시 필터링
filtered_datas = []
for src, dest in a.datas:
    exclude = False
    for pattern in excludes_patterns:
        if fnmatch.fnmatch(src, f"*{pattern}"):
            exclude = True
            print(f"  제외: {os.path.basename(src)} ({pattern})")
            break
    if not exclude:
        filtered_datas.append((src, dest))

a.datas = filtered_datas
```

### 3. 불필요한 패키지 제외

```python
excludes=[
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'wx',
    'django',
    'flask',
    'tornado',
    'test',        # ✅ 테스트 모듈
    'tests',       # ✅ 테스트 디렉토리
    'pytest',      # ✅ pytest
    'sphinx',      # ✅ 문서화 도구
    'setuptools',  # ✅ 빌드 도구
],
```

---

## 📊 크기 비교

| 항목 | --onefile (이전) | --onedir (현재) |
|------|-----------------|----------------|
| **실행 파일** | 4.1GB | ~50MB |
| **_internal/** | - | ~300MB |
| **모델 (외부)** | 포함됨 | ~2GB (별도) |
| **총 배포 크기** | 4.1GB | ~2.3GB |
| **시작 시간** | 느림 (압축 해제) | 빠름 |
| **디버깅** | 어려움 | 쉬움 |

---

## ⚠️ 주의사항

### 1. 모델 파일 경로

코드에서 모델 파일을 로드할 때 **상대 경로** 또는 **절대 경로**를 사용해야 합니다:

```python
# src/tcp_monitor/sensor/safety_detector.py

# 이전 (번들 내부)
model_path = "buffalo_l"

# 현재 (외부 파일)
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "..", "..", "..", "models", "insightface", "buffalo_l")
```

### 2. 배포 시 포함 파일

```bash
# 필수 파일
garame_manager/          # PyInstaller 빌드 결과
garame_manager.sh        # 실행 스크립트
models/                  # AI 모델 (2GB)
config/                  # 설정 파일
safety_posters/          # 안전 포스터
safety_photos/           # 안전 사진
```

### 3. 권한 설정

```bash
chmod +x garame_manager.sh
chmod +x garame_manager/garame_manager
```

---

## 🧪 테스트

### 1. 로컬 테스트

```bash
cd ~/바탕화면/1.9.5
pyinstaller --clean garame_manager.spec

# 빌드 성공 확인
ls -lh dist/garame_manager/

# 실행 테스트
./dist/garame_manager/garame_manager --help
```

### 2. 모델 로딩 테스트

```python
# 실행 중 로그 확인
[INFO] InsightFace 모델 로딩 중: /path/to/models/insightface/buffalo_l
[INFO] YOLOv11 모델 로딩 중: /path/to/models/yolov11/best.pt
```

### 3. 배포 패키지 테스트

```bash
./create_distribution.sh

# 압축 해제 테스트
tar -xzf GARAMe_Manager_1.9.5_Ubuntu25_Distribution.tar.gz
cd GARAMe_Manager_1.9.5_Ubuntu25_Distribution
./garame_manager.sh
```

---

## 🎯 기대 효과

1. **빌드 파일 크기**: 4.1GB → **500MB** (88% 감소) ✅
2. **배포 크기**: 4.1GB → **2.3GB** (44% 감소) ✅
3. **시작 시간**: 느림 → **빠름** ✅
4. **디버깅**: 어려움 → **쉬움** ✅
5. **유지보수**: 어려움 → **쉬움** ✅

---

## 📝 다음 단계

1. ✅ garame_manager.spec 수정 완료
2. ✅ create_distribution.sh 수정 완료
3. ⏳ Ubuntu 환경에서 빌드 테스트
4. ⏳ 모델 로딩 경로 확인
5. ⏳ 배포 패키지 생성 및 검증

---

생성일: 2025-11-18
작성자: Claude Code
버전: GARAMe Manager v1.9.5
