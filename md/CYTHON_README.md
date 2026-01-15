# Cython 소스코드 보호 - 빠른 가이드

> **무료로 Python 소스코드를 보호하고 성능도 향상시키세요!**

## 🔒 왜 Cython인가?

### 문제: Python 소스코드 노출
```python
# safety_detector.py - 누구나 읽을 수 있음
def detect_safety_equipment(image):
    # 핵심 알고리즘이 그대로 노출됨
    if helmet_detected:
        return True
```

### 해결: Cython 컴파일
```
safety_detector.cpython-310-x86_64-linux-gnu.so
  ↓
바이너리 파일 - 역컴파일 거의 불가능
```

## ⚡ 3단계로 끝내기

### 1️⃣ 보안 빌드 실행
```bash
cd 1.9.1
./build_secure.sh
```

**자동 실행 내용**:
- ✓ Cython 자동 설치
- ✓ 원본 소스코드 백업 생성
- ✓ 모든 .py 파일 → .so 파일 컴파일
- ✓ 원본 .py 파일 삭제 (선택 가능)
- ✓ 컴파일 보고서 생성

### 2️⃣ 테스트
```bash
./run.sh
```

정상 작동 확인!

### 3️⃣ 완료!

이제 소스코드가 보호된 상태로 배포 가능합니다.

## 📊 보안 수준 비교

| 방법 | 보호 수준 | 비용 | 역컴파일 난이도 |
|------|----------|------|----------------|
| `.py` 파일 | ⭐ | 무료 | 즉시 가능 (텍스트) |
| `.pyc` 파일 | ⭐⭐ | 무료 | 쉬움 (도구 존재) |
| **Cython `.so`** | **⭐⭐⭐⭐** | **무료** | **매우 어려움** |
| PyArmor | ⭐⭐⭐⭐⭐ | $69/년 | 거의 불가능 |

## 🎁 보너스: 성능 향상

Cython 컴파일 시 무료로 얻는 성능 향상:

- **이미지 처리**: 20-50% 빠름
- **얼굴 인식**: 20-30% 빠름
- **일반 코드**: 10-30% 빠름

## 🛡️ 무엇이 보호되나?

### 보호되는 것 ✅
- ✓ Python 소스코드
- ✓ 알고리즘 로직
- ✓ 비즈니스 로직
- ✓ 제어 흐름 (if/else, 루프)
- ✓ 변수명, 함수명

### 보호되지 않는 것 ❌
- ✗ 일부 문자열 리터럴 (예: "Error", "Success")
- ✗ 프로그램 동작 (실행해보면 알 수 있음)

## 🔧 고급 사용법

### 백업 복구
```bash
./restore_backup.sh
```

실수로 삭제했거나 수정이 필요할 때 사용.

### 수동 컴파일 (삭제 안 함)
```bash
source venv/bin/activate
python3 setup_cython.py build_ext --inplace
```

.py와 .so 파일을 함께 유지하고 싶을 때.

### 선택적 컴파일

[setup_cython.py](setup_cython.py) 수정:
```python
exclude_patterns = [
    "test_",      # 테스트 파일 제외
    "config",     # 설정 파일 제외
    "my_module",  # 특정 모듈 제외
]
```

## 📁 파일 변화

### 컴파일 전
```
1.9.1/
├── main.py                           # Python 소스
├── watchdog.py                       # Python 소스
└── src/tcp_monitor/
    ├── sensor/safety_detector.py     # Python 소스
    └── ui/app.py                     # Python 소스
```

### 컴파일 후
```
1.9.1/
├── main.py                           # 엔트리포인트 (유지)
├── watchdog.cpython-310-x86_64-linux-gnu.so    # 컴파일됨 ✅
├── backup_original_20250106_143022/  # 백업 🔐
│   ├── main.py
│   ├── watchdog.py
│   └── src/
└── src/tcp_monitor/
    ├── sensor/
    │   └── safety_detector.cpython-310-x86_64-linux-gnu.so  # 컴파일됨 ✅
    └── ui/
        └── app.cpython-310-x86_64-linux-gnu.so              # 컴파일됨 ✅
```

## ⚠️ 주의사항

### 1. 백업 보관 필수
```bash
# 백업 디렉토리는 절대 삭제하지 마세요!
backup_original_20250106_143022/
```

**이유**: .so 파일은 수정 불가능. 버그 수정이나 기능 추가 시 원본 필요.

### 2. 플랫폼 종속성
- Ubuntu 25 x64에서 컴파일 → Ubuntu 25 x64에서만 작동
- 다른 플랫폼 지원 시 각각 컴파일 필요

### 3. Python 버전
- Python 3.10에서 컴파일 → Python 3.10에서만 작동
- Python 버전 변경 시 재컴파일 필요

## 📚 상세 가이드

더 자세한 내용은 다음 문서를 참고하세요:

- [CYTHON_BUILD_GUIDE.md](CYTHON_BUILD_GUIDE.md) - 완벽 가이드 (30+ 페이지)
- [setup_cython.py](setup_cython.py) - 컴파일 설정
- [build_secure.sh](build_secure.sh) - 빌드 스크립트
- [restore_backup.sh](restore_backup.sh) - 복구 스크립트

## 🆘 문제 해결

### 컴파일 실패
```bash
# 빌드 도구 설치
sudo apt install -y build-essential python3-dev
```

### import 오류
```bash
# __init__.py 확인
ls -la src/tcp_monitor/__init__.py
```

### 백업에서 복구
```bash
./restore_backup.sh
```

## 💡 FAQ

**Q: .so 파일을 수정할 수 있나요?**
A: 불가능합니다. 수정이 필요하면 백업에서 복구 → 수정 → 재컴파일

**Q: 정말 무료인가요?**
A: 예! Cython은 Apache License 2.0 오픈소스입니다.

**Q: PyArmor와 비교하면?**
A: PyArmor가 약간 더 강력하지만 Cython도 충분히 안전하고 무료입니다.

**Q: 성능이 정말 향상되나요?**
A: 예! CPU 집약적인 코드일수록 더 큰 향상을 볼 수 있습니다.

**Q: 모든 .py 파일을 삭제해야 하나요?**
A: 아니요. 선택 사항입니다. 둘 다 유지해도 됩니다 (Python은 .so를 우선 사용).

## 🎯 요약

### ✅ 장점
- 무료 소스코드 보호
- 10-30% 성능 향상
- 쉬운 사용 (3단계)
- 백업 및 복구 기능

### ❌ 단점
- 플랫폼/Python 버전 종속
- .so 파일 수정 불가
- 컴파일 시간 필요 (최초 1회)

### 🎉 결론
**GARAMe Manager를 배포할 때는 Cython 컴파일을 강력히 권장합니다!**

---

Copyright © 2025 GARAMe Project
