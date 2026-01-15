# GARAMe MANAGER v1.9.8.4

센서 데이터 실시간 모니터링 및 관리 시스템 + 최신 AI 안전장구 감지

## 개요

GARAMe MANAGER는 다중 센서의 데이터를 실시간으로 수집, 모니터링, 분석하는 통합 관리 시스템입니다.

**플랫폼**: Ubuntu Linux 18.04 이상 (권장: Ubuntu 22.04 LTS, Debian 12/13)
**Python**: 3.8 이상

### 🆕 v1.9.8.4 주요 업그레이드

**센서 탭 닫기 버튼**:
- **탭 ✕ 표시**: 연결 끊김 상태의 탭에 닫기 버튼(✕) 표시
- **다양한 닫기 방법**: ✕ 클릭, 우클릭 메뉴, 중클릭(휠)으로 탭 닫기
- **안전 조치**: 연결된 탭은 닫을 수 없음 (연결 끊김만 가능)

**카메라 고급 설정 다이얼로그 수정**:
- **messagebox 문제 해결**: 중첩 모달에서 다이얼로그 표시 안됨 문제 수정
- **커스텀 다이얼로그**: 앱 테마에 맞는 다크 테마 다이얼로그

### v1.9.8.3-1 기능

**라이선스 키 시스템**:
- **하드웨어 바인딩**: 머신 UUID, MAC, 디스크 시리얼, CPU 기반 바인딩
- **키 타입**: 테스트(7일), 기간제한, 영구, 버전제한 키 지원

**IP 카메라 개선**:
- **COCO 사물 감지 복구**: 80클래스 사물 감지 정상화
- **카메라 전환 문제 해결**: IP ↔ USB 카메라 전환 시 감지 유지

### v1.9.8.2 기능

**안전화 감지 개선**:
- **듀얼 모델 구조**: 메인 PPE 모델 + 안전화 전용 모델
- **슬리퍼 오인식 해결**: 일반 신발/슬리퍼를 안전화로 인식하는 문제 수정

**PTZ 카메라 제어**:
- **다중 인증 방식**: Tapo 카메라 4가지 인증 방식 자동 시도
- **PTZ 테스트 버튼**: 카메라 설정에서 연결 테스트 기능

---

## 주요 기능

### 📊 센서 모니터링
- **실시간 데이터 수집**: 다중 센서 동시 연결 및 데이터 수집
- **Heartbeat 지원**: 센서 연결 상태 실시간 확인 (30초 간격)
- **자동 재연결**: 네트워크 불안정 시 자동 재연결
- **데이터 시각화**: 실시간 그래프 및 차트 표시

### 🎯 센서 관리
- **탭 기반 UI**: 센서별 독립 탭 관리
- **탭 삭제 기능**: 연결 끊김 센서 탭 제거
- **센서 설정**: 센서별 임계값 및 경보 설정

### 🔔 경보 시스템
- **실시간 경보**: 임계값 초과 시 즉시 알림
- **음성 경고**: gTTS 기반 자연스러운 한국어 여성 아나운서 목소리
- **정확한 발음**: 구글 음성 합성 기술로 명확한 한국어 경보
- **누수 감지**: 즉시 알림 및 기록
- **경보 이력**: 오늘/이번달/전체 경보 이력 조회

### 👤 얼굴 인식
- **InsightFace 기반**: 99.86% 정확도, ArcFace 알고리즘
- **실시간 얼굴 인식**: 이름, 사원번호, 부서, 신뢰도 표시
- **GPU 가속**: ONNX Runtime으로 빠른 처리

### 🦺 안전장구 감지
- **YOLOv10x PPE 감지**: 92.7% mAP50 정확도 (통합 모델)
- **감지 항목**: 안전모, 보안경, 마스크, 장갑(좌/우), 안전조끼, 안전화
- **색상 분석**: 헬멧/조끼 색상 자동 인식
- **실시간 경고**: 미착용 시 즉시 알림

### 📈 데이터 분석
- **그래프 시각화**: 시간대별 센서 데이터 그래프
- **한글 폰트 지원**: 자동 한글 폰트 탐지 및 적용
- **데이터 내보내기**: CSV/Excel 형식 지원

### 🔧 시스템 관리
- **Watchdog**: 프로그램 자동 재시작
- **systemd 지원**: 부팅 시 자동 시작
- **로그 관리**: 상세 로그 기록 및 관리

---

## 빠른 시작

### 요구사항

#### 필수
- Ubuntu Linux 18.04 이상
- Python 3.8 이상
- 4GB RAM 이상
- 10GB 디스크 여유 공간

#### 선택 (GPU 가속)
- NVIDIA GPU (GTX 1050 Ti 이상 권장)
- CUDA 11.8 이상
- 4GB VRAM 이상

**💡 참고**: GPU가 없어도 CPU 모드로 정상 작동합니다.

### 설치

```bash
# 저장소 클론
git clone https://github.com/your-org/garame-manager.git
cd garame-manager

# 설치 실행 (GPU 옵션 선택 가능)
./install.sh

# GPU 가속을 사용하시겠습니까? (y/n, 기본값: n):
# - n: CPU 모드 (모든 시스템에서 작동)
# - y: GPU 가속 (NVIDIA GPU + CUDA 필요)
```

**💡 GPU 설치 관련**: [GPU 설치 가이드](md/GPU_INSTALLATION_GUIDE.md) 참조

### 실행

```bash
# 일반 실행
./run.sh

# Watchdog와 함께 실행 (자동 재시작)
./run_with_watchdog.sh

# systemd 서비스로 실행
sudo systemctl start garame-manager
```

---

## 설정

### config/settings.json 주요 설정

```json
{
  "tcp_port": 5000,
  "heartbeat_timeout": 90,
  "auto_reconnect": true,
  "voice_alert": true,
  "voice_speed": 140
}
```

### 센서 연결 설정

센서에서 Manager IP와 포트를 설정:
```ini
[TCP]
host = 192.168.0.100  # Manager IP
port = 5000
```

---

## 호환성

### GARAMe Sensor
- **v1.1.6**: ✅ 100% 호환 (권장)
- **v1.1.5**: ✅ 호환
- **v1.1.4**: ✅ 호환

### 통신 프로토콜
- TCP JSON 프로토콜
- 지원 메시지:
  - `sensor_update`: 센서 데이터
  - `heartbeat`: 연결 상태 확인
  - `water_leak_alert`: 누수 알림
  - `water_normal_alert`: 누수 해제

---

## 키보드 단축키

- **F1**: 도움말
- **F5**: 센서 임계값 수정
- **F11**: 전체화면 토글
- **ESC**: 프로그램 종료

---

## 문서

### 설치 및 설정
- [INSTALLATION_AND_TROUBLESHOOTING.md](md/INSTALLATION_AND_TROUBLESHOOTING.md) - 설치 및 문제 해결
- [AUTOSTART_GUIDE.md](md/AUTOSTART_GUIDE.md) - 자동 시작 설정
- [SYSTEMD_SERVICE_GUIDE.md](md/SYSTEMD_SERVICE_GUIDE.md) - systemd 서비스

### 기능 가이드
- [CAMERA_FLIP_SETTINGS.md](md/CAMERA_FLIP_SETTINGS.md) - 카메라 반전 설정
- [BACKGROUND_LEARNING_FEATURE.md](md/BACKGROUND_LEARNING_FEATURE.md) - 배경 학습 기능
- [DISK_CLEANUP_FEATURE.md](md/DISK_CLEANUP_FEATURE.md) - 디스크 정리

### 문제 해결
- [CV2_TROUBLESHOOTING.md](CV2_TROUBLESHOOTING.md) - OpenCV 문제 해결
- [CAMERA_TROUBLESHOOTING.md](md/CAMERA_TROUBLESHOOTING.md) - 카메라 문제
- [CPU_COMPATIBILITY_FIX.md](md/CPU_COMPATIBILITY_FIX.md) - CPU 호환성

---

## 변경 이력

자세한 변경 이력은 [CHANGELOG.md](md/CHANGELOG.md) 참조

---

## 라이선스

Copyright © 2025 GARAMe Project
