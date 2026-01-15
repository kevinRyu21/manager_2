# GARAMe MANAGER v1.8.8

센서 데이터 실시간 모니터링 시스템

## 🚀 빠른 시작

### Ubuntu/Linux

```bash
# 실행 권한 부여
chmod +x run_ubuntu.sh

# 실행 (자동 설치 및 실행)
./run_ubuntu.sh
```

### 오프라인 설치

```bash
# 1. 인터넷이 있는 환경에서 wheel 파일 다운로드
./download_wheels.sh

# 2. 오프라인 환경으로 wheels/ 디렉토리 복사

# 3. 오프라인 설치
./install_offline.sh
```

## 📚 주요 문서

- **[INSTALLATION_AND_TROUBLESHOOTING.md](INSTALLATION_AND_TROUBLESHOOTING.md)**: 설치 및 문제 해결 종합 가이드
- **[UBUNTU_INSTALL_GUIDE.md](UBUNTU_INSTALL_GUIDE.md)**: Ubuntu 설치 상세 가이드
- **[CPU_COMPATIBILITY_FIX.md](CPU_COMPATIBILITY_FIX.md)**: CPU 호환성 문제 해결
- **[FACE_RECOGNITION_INSTALL_GUIDE.md](FACE_RECOGNITION_INSTALL_GUIDE.md)**: 얼굴 인식 설치 가이드

## ✨ v1.8.8 주요 변경사항

### 기능 개선
- ✅ 문자 크기 조절 실시간 반영
- ✅ 서명 인식 기능 개선 및 화면 통합
- ✅ 오프라인 실행 지원
- ✅ CPU 호환성 개선

### 버그 수정
- ✅ evdev 설치 오류 수정 (python3-dev 자동 설치)
- ✅ 프리뷰 업데이트 오류 수정
- ✅ 표시 문구 편집 저장 개선

## 📋 시스템 요구사항

- **OS**: Ubuntu 20.04 이상, Debian 기반 배포판
- **Python**: 3.8 이상 (권장: 3.11-3.13)
- **메모리**: 최소 4GB RAM
- **디스크**: 약 2GB 여유 공간

## 🛠️ 설치 스크립트

### `run_ubuntu.sh`
- 자동 시스템 패키지 설치
- 가상환경 생성 및 관리
- 오프라인 모드 자동 감지
- 얼굴 인식 기능 선택적 설치

### `download_wheels.sh`
- 오프라인 설치용 wheel 파일 다운로드
- 인터넷이 있는 환경에서 실행

### `install_offline.sh`
- 오프라인 환경에서 패키지 설치
- wheels/ 디렉토리에서 설치

### `fix_cpu_compatibility.sh`
- CPU 호환성 문제 해결
- NumPy 재설치 및 환경 설정

## 🔧 문제 해결

자세한 문제 해결 방법은 [INSTALLATION_AND_TROUBLESHOOTING.md](INSTALLATION_AND_TROUBLESHOOTING.md)를 참조하세요.

### 주요 문제 해결

1. **Illegal instruction 오류**: `main.py`에 자동 설정됨
2. **evdev 설치 오류**: `python3-dev` 자동 설치됨
3. **NumPy 버전 오류**: 얼굴 인식 사용 시 자동 다운그레이드

## 📝 라이선스

자세한 내용은 `LICENSE` 파일을 참조하세요.

---

**버전**: 1.8.8  
**최종 업데이트**: 2025-11-04

