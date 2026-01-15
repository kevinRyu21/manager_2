# PyArmor 암호화 제한 사항

## 문제 상황

### PyArmor Trial 라이선스 제한

배포 패키지 생성 중 다음 오류가 발생했습니다:

```
ERROR    out of license
```

## 원인

**PyArmor Trial 버전의 제약**:
- Trial 라이선스는 **일정 횟수 또는 기간** 제한이 있음
- 이전에 이미 암호화를 수행했기 때문에 Trial 할당량이 소진됨
- 추가 암호화를 수행하려면 정식 라이선스가 필요

## 현재 배포 패키지 상태

### ❌ 암호화되지 않은 파일들

1. **main.py**: 원본 소스 코드 (7.5KB)
   ```python
   #!/usr/bin/env python3
   # -*- coding: utf-8 -*-
   """
   TCP Monitor v1.9.1 - 메인 진입점
   ...
   ```

2. **src/ 디렉토리**: 모든 Python 소스 파일 원본
   - `src/tcp_monitor/sensor/alerts.py`
   - `src/tcp_monitor/ui/...`
   - 기타 모든 모듈

### ⚠️ pyarmor_runtime_000000 디렉토리

배포 패키지에 `pyarmor_runtime_000000` 디렉토리가 포함되어 있지만:
- **main.py가 암호화되지 않음** → 런타임 불필요
- 이전 암호화 시도의 잔여물

## ✅ 완료된 작업

### 1. MD 파일 정리
**47개의 MD 파일**을 `md/` 디렉토리로 이동:
```bash
/Users/cyber621/Desktop/develop/garam/manager/1.9.2/md/
├── AUTOSTART_GUIDE.md
├── BACKGROUND_LEARNING_FEATURE.md
├── CAMERA_FLIP_SETTINGS.md
...
├── VERSION_1.9.2_CHANGES.md
└── WINDOWS11_INSTALL_GUIDE.md
```

### 2. 배포 스크립트 수정
`create_distribution.sh`가 md 디렉토리에서 파일을 읽도록 수정됨:
```bash
# 설명 문서 복사 (md 디렉토리에서)
cp md/README.md "$DIST_DIR/" 2>/dev/null || true
cp md/VERSION_1.9.2_CHANGES.md "$DIST_DIR/" 2>/dev/null || true
cp md/INSTALL_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp md/DISK_SPACE_GUIDE.md "$DIST_DIR/" 2>/dev/null || true
cp md/DISTRIBUTION_README.md "$DIST_DIR/" 2>/dev/null || true
```

## 해결 방법

### 옵션 1: PyArmor 정식 라이선스 구매 (권장)

**상업용 라이선스**:
- 가격: $99 ~ $299 (용도에 따라)
- 무제한 암호화
- 상업적 배포 가능

**구매 링크**: https://pyarmor.dashingsoft.com/pricing.html

```bash
# 라이선스 구매 후
pyarmor reg pyarmor-regcode-XXXX.txt

# 암호화 재실행
cd /Users/cyber621/Desktop/develop/garam/manager/1.9.2
./create_distribution.sh
```

### 옵션 2: 대체 암호화 도구 사용

#### 2-1. Cython으로 컴파일
Python 코드를 C로 변환 후 바이너리로 컴파일:

```bash
# Cython 설치
pip install cython

# 모든 .py 파일을 .so로 컴파일
find src -name "*.py" -exec cython --embed {} \;
```

**장점**:
- 완전한 바이너리 컴파일
- 역공학 거의 불가능
- 성능 향상

**단점**:
- 설정 복잡
- 플랫폼별 컴파일 필요
- 디버깅 어려움

#### 2-2. PyInstaller로 실행 파일 생성
전체 애플리케이션을 단일 실행 파일로 패키징:

```bash
pip install pyinstaller

pyinstaller --onefile \
            --windowed \
            --add-data "src:src" \
            --add-data "safety_posters:safety_posters" \
            main.py
```

**장점**:
- 설정 간단
- 단일 실행 파일
- Python 설치 불필요

**단점**:
- 파일 크기 큼 (100MB+)
- 완벽한 난독화는 아님
- 압축 해제 후 임시 디렉토리에서 실행

### 옵션 3: 원본 소스 배포 (현재 상태)

**장점**:
- 추가 작업 불필요
- 설치 및 디버깅 용이

**단점**:
- 소스 코드 노출
- 지적 재산권 보호 안 됨

## 현재 배포 패키지 사용

**PyArmor 없이도 정상 동작합니다**:

```bash
# 배포 패키지 압축 해제
tar -xzf GARAMe_Manager_1.9.2_Ubuntu25_Distribution.tar.gz
cd GARAMe_Manager_1.9.2_Ubuntu25_Distribution

# 설치
./install.sh

# 실행
./run.sh
```

**참고**: `pyarmor_runtime_000000` 디렉토리가 있지만 main.py가 암호화되지 않았으므로 무시됩니다.

## 권장 사항

### 단기 (즉시)
- **현재 패키지 그대로 사용**
- 소스 보호가 중요하지 않다면 원본 배포
- 내부 사용 목적이라면 문제없음

### 중기 (1-2주)
- **PyArmor 라이선스 구매 검토**
- 상업적 배포 계획이 있다면 필수
- $99 Pro 라이선스로 충분

### 장기 (향후)
- **Cython 컴파일 고려**
- 더 강력한 보호
- 성능 최적화도 가능

## ✅ 최종 해결 방법 (2025-11-11)

### PyArmor 완전 제거로 플랫폼 호환성 확보

**결정**: PyArmor 암호화를 완전히 제거하고 원본 소스 배포로 전환

**이유**:
1. **플랫폼 의존성**: PyArmor 런타임은 플랫폼별로 컴파일됨
   - macOS에서 빌드 → Mach-O 바이너리
   - Ubuntu에서 실행 → ELF 바이너리 필요
   - 크로스 플랫폼 빌드 복잡도 높음

2. **Trial 라이선스 제한**: 추가 암호화 불가

3. **배포 우선순위**: 안정적인 동작이 소스 보호보다 중요

**변경 사항**:
```bash
# create_distribution.sh 수정
# OLD: 120+ 라인의 PyArmor 설치 및 암호화 로직
# NEW: 간단한 소스 복사
cp -r src "$DIST_DIR/"
cp main.py "$DIST_DIR/"
```

## 정리

| 항목 | 상태 |
|------|------|
| main.py 암호화 | ❌ 제거됨 (플랫폼 호환성 우선) |
| src/ 암호화 | ❌ 제거됨 (플랫폼 호환성 우선) |
| MD 파일 정리 | ✅ 완료 (47개 → md/) |
| assets 포함 | ✅ 완료 (5개 이미지 파일) |
| 배포 패키지 생성 | ✅ 완료 (15MB) |
| Ubuntu 25 동작 | ✅ 정상 (PyArmor 에러 해결) |
| 소스 보호 | ❌ 원본 노출 |

---

**결론**: PyArmor 암호화를 제거하여 Ubuntu 25.10에서 정상 동작하는 배포 패키지를 생성했습니다. 향후 소스 보호가 필요하다면 Ubuntu에서 직접 PyArmor 빌드하거나 Cython 컴파일을 고려해야 합니다.
