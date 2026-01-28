# GARAMe MANAGER v2.1.0

센서 데이터 실시간 모니터링 및 관리 시스템 + AI 화재 감시 + 안전장구 감지

## 개요

GARAMe MANAGER는 다중 센서의 데이터를 실시간으로 수집, 모니터링, 분석하는 통합 관리 시스템입니다.
v2.0부터 Dempster-Shafer 증거 이론 기반 5단계 화재 감시 시스템이 추가되었습니다.

**플랫폼**: Ubuntu Linux 18.04 이상 (권장: Ubuntu 22.04 LTS, Debian 12/13)
**Python**: 3.10 이상 (Python 3.13 완전 지원)

### 🆕 v2.1.0 주요 업그레이드 (2026-01-28)

**Python 3.13 호환성**:
- **이미지 로딩 문제 해결**: PhotoImage 가비지 컬렉션 문제 수정, 모든 이미지 정상 표시
- **프로그램 종료 개선**: Tcl 명령 오류 해결, 깨끗한 종료 처리
- **UI 컴포넌트 수정**: 5단계 경고 설정 버튼 표시 문제 해결

**UI 개선**:
- **화재 레벨 아이콘**: 전문 디자인의 5단계 화재 레벨 아이콘 (PNG 이미지)
  - 레벨별 색상 구분 (초록/노랑/주황/빨강/진한빨강)
  - 레벨 번호 표시 및 투명 배경 지원

**테스트 도구**:
- **센서 시뮬레이터**: 센서 없이 모든 기능 테스트 가능
  - 센서 ID 1-4 동시 접속
  - 13가지 시나리오 프리셋 (화재, 가스 누출, 질식 등)
  - TCP v2.0 프로토콜 지원
  - GUI 컨트롤 패널

**상세 변경사항**: [CHANGELOG_v2.1.0.md](CHANGELOG_v2.1.0.md) 참조

### v2.0.1 주요 업그레이드

**UI 개선**:
- **안전점검 기능**: 거울보기 → 안전점검으로 명칭 변경, 안전장구 착용 상태 확인
- **불쾌지수 시인성 개선**: 레벨별 배경색+글자색 조합으로 가독성 향상
- **경고 버튼 텍스트 개선**: `주의0/경계0/심각0` 형식으로 의미 명확화
- **센서전체보기**: 2개 이상 센서 접속 시 분할 화면으로 모든 센서 동시 확인
- **화면 캡쳐 기능**: Linux/Wayland 호환 캡쳐 기능 (scrot/gnome-screenshot 지원)

**버그 수정**:
- **안전점검 종료 오류 수정**: TclError 오류 해결
- **종료 확인 다이얼로그**: 불쾌지수 10번 클릭 시 확인 후 종료

### v2.0.0 주요 기능

**화재 감시 5단계 경보 시스템**:
- **5단계 경보**: 정상(🟢) → 관심(🟡) → 주의(🟠) → 경계(🔴) → 위험(🟣)
- **Dempster-Shafer 증거 이론**: 8개 센서 데이터 융합 분석
- **AI 적응형 임계값**: 설치 환경 자동 학습 및 최적화

**TCP 프로토콜 v2.0**:
- **양방향 통신**: 센서 ↔ 매니저 양방향 메시지 지원
- **시간 동기화**: NTP 스타일 시간 동기화
- **TLS/SSL 암호화**: 선택적 보안 통신 지원

**신규 센서 지원**:
- **CH4 (메탄/가연성 가스)**: %LEL 단위
- **Smoke (연기 센서)**: % 단위
- **ext_input (외부 접점 입력)**: 5V~24V DC 접점 신호

### 이전 버전 기능

**라이선스 키 시스템** (v1.9.8.3-1):
- **하드웨어 바인딩**: 머신 UUID, MAC, 디스크 시리얼, CPU 기반 바인딩
- **키 타입**: 테스트(7일), 기간제한, 영구, 버전제한 키 지원

**IP 카메라 개선** (v1.9.8.3-1):
- **COCO 사물 감지 복구**: 80클래스 사물 감지 정상화
- **카메라 전환 문제 해결**: IP ↔ USB 카메라 전환 시 감지 유지

**안전화 감지 개선** (v1.9.8.2):
- **듀얼 모델 구조**: 메인 PPE 모델 + 안전화 전용 모델
- **슬리퍼 오인식 해결**: 일반 신발/슬리퍼를 안전화로 인식하는 문제 수정

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

#### 화면 캡쳐 (선택)
- **flameshot**: GNOME/Wayland 환경에서 화면 캡쳐 기능 사용 시 필요
```bash
# Ubuntu/Debian
sudo apt install flameshot
```

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

- [CHANGELOG_v2.1.0.md](CHANGELOG_v2.1.0.md) - v2.1.0 변경사항
- [CHANGELOG.md](CHANGELOG.md) - 전체 변경 이력

---

## 테스트 도구

### 센서 시뮬레이터
센서 없이 Manager의 모든 기능을 테스트할 수 있는 시뮬레이터를 제공합니다.

```bash
# Manager 실행
python3 main.py

# 별도 터미널에서 시뮬레이터 실행
python3 sensor_simulator.py
```

**기능**:
- 센서 ID 1-4 동시 접속
- 13가지 시나리오 (정상, 화재 4단계, 가스 누출, 질식, 누수 등)
- 실시간 센서 데이터 전송
- GUI 컨트롤 패널

**사용법**:
1. 서버 주소/포트 설정 (기본: 127.0.0.1:9000)
2. 각 센서에서 시나리오 선택
3. "연결" 버튼 클릭
4. "전송 시작" 버튼 클릭

---

## 라이선스

Copyright © 2025 가람이엔지(주). All rights reserved.
