# GARAMe Manager v1.9.8.2 변경 이력

## 버전 정보
- **버전**: 1.9.8.2
- **릴리스**: 2024-12-24
- **플랫폼**: Ubuntu Linux 18.04+
- **Python**: 3.8 ~ 3.13

---

## v1.9.8.2 주요 변경사항

### 1. 안전화(Boots) 감지 개선

#### 문제점
- 기존 SH17 데이터셋 모델의 `shoes` 클래스가 슬리퍼/일반 신발도 안전화로 오인식

#### 해결책
- **듀얼 모델 구조** 적용
  - 메인 모델 (yolo10x.pt): helmet, vest, gloves, glasses, mask 감지
  - 안전화 모델 (construction-ppe.pt): boots 전용 감지

#### 변경 파일
- `models/construction-ppe.pt` - 신규 안전화 감지 모델 (5.5MB, YOLOv10n)
- `src/tcp_monitor/ppe/detector.py` - 듀얼 모델 지원 업데이트

#### 성능
| 지표 | 값 |
|------|-----|
| 모델 | YOLOv10n |
| 데이터셋 | Construction-PPE (Ultralytics) |
| mAP50 | 51.3% |
| Precision | 70.0% |
| Recall | 46.2% |

---

### 2. GPU 자동 감지 및 설치 지원

#### 변경사항
- **install.sh GPU 자동 감지**: NVIDIA GPU가 감지되면 자동으로 GPU 패키지 설치
  - PyTorch CUDA 12.4/11.8 자동 설치 (순차 시도)
  - onnxruntime-gpu 자동 설치
  - GPU 미감지 시 CPU 버전 설치
- **detector.py GPU 지원**: YOLO 모델 추론 시 GPU 자동 사용
- **성능 모드 3 완전 지원**: GPU 가속 모든 기능 활성화

#### 변경 파일
- `install.sh` - GPU 감지 함수 추가, PyTorch/ONNX GPU 설치 분기
- `requirements.txt` - GPU 패키지 설명 추가
- `src/tcp_monitor/ppe/detector.py` - GPU/CPU 자동 감지 및 device 설정

#### GPU 설치 자동화
```bash
# NVIDIA GPU 감지 시
pip install onnxruntime-gpu
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# GPU 미감지 시
pip install onnxruntime
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

---

### 3. PTZ 카메라 제어 개선

#### 문제점
- Tapo 카메라 PTZ 인증 실패 ("Invalid authentication data")
- RTSP 로컬 계정과 Tapo 클라우드 계정 혼동

#### 해결책
- pytapo 공식 해결책 적용: `admin` + 클라우드 비밀번호 방식
- 4가지 인증 방식 순차 시도 (신형/구형 펌웨어 호환)
- UI에서 RTSP 계정과 PTZ Tapo 계정 분리

#### 변경 파일
- `src/tcp_monitor/sensor/tapo_ptz.py` - 다중 인증 방식 지원
- `src/tcp_monitor/ui/camera_settings.py` - PTZ Tapo 계정 입력 UI 개선

#### PTZ 인증 방식 (순서대로 시도)
1. admin + 클라우드 비밀번호 (password 파라미터)
2. admin + 클라우드 비밀번호 (cloudPassword 파라미터)
3. 사용자명 + 클라우드 비밀번호 (password 파라미터)
4. 사용자명 + 클라우드 비밀번호 (cloudPassword 파라미터)

---

### 4. 성능 설정 UI 개선

#### 변경사항
- 폰트 크기 25% 축소 (가독성 유지하면서 컴팩트화)
- 다이얼로그 높이 940px로 조정

#### 변경 파일
- `src/tcp_monitor/ui/performance_settings.py`

---

### 5. PPE 모델 정리

#### 변경사항
- 잘못된 모델 이름 수정: `ppe_detect.pt` → `yolo_coco_80.pt`
  - 실제로 COCO 80 클래스 모델이었음 (PPE 모델 아님)
- `helpers.py`에서 PPE 모델을 `ppe_full.pt`로 변경

#### 현재 모델 구조
```
models/
├── yolo10x.pt              # 메인 PPE 모델 (61MB)
├── ppe_full.pt             # PPE 전체 모델 (52MB)
├── ppe_helmet_vest.pt      # 경량 PPE 모델 (6MB)
├── construction-ppe.pt     # 안전화 전용 모델 (5.5MB) [신규]
├── yolo_coco_80.pt         # COCO 80 클래스 (일반 사물)
└── ppe_yolov8m.pt          # YOLOv8m PPE 모델
```

---

## v1.9.8 변경사항 (이전 버전)

### 카메라 설정 시스템
- USB/IP 카메라 통합 관리
- IP 카메라 지원 (RTSP/HTTP/HTTPS)
- PTZ 카메라 제어 기능

### 거울보기 개선
- 카메라 이름 표시
- 바운딩 박스 오버레이
- 센서 접속 시 자동 종료

---

## 설치/업데이트 방법

### 신규 설치
```bash
# 전체 패키지 설치
./install.sh
```

### 1.9.8에서 업그레이드
```bash
# boots-model-update 패키지 사용
cd boots-model-update
chmod +x INSTALL.sh
./INSTALL.sh /path/to/1.9.8.2
```

---

## 호환성

### 이전 버전과의 호환
- v1.9.7/v1.9.8 설정 파일 100% 호환
- 기존 PPE 모델 계속 사용 가능

### PTZ 카메라 호환
| 카메라 모델 | 지원 |
|------------|------|
| Tapo C210 | ✅ |
| Tapo C211 | ✅ |
| Tapo C220 | ✅ |
| Tapo C225 | ✅ |

---

## 알려진 이슈

### PTZ 인증
- Tapo 카메라는 연속 인증 실패 시 30분간 잠금 (Temporary Suspension)
- 잠금 해제 후 재시도 필요

### 안전화 감지
- construction-ppe.pt 모델은 작업 현장 이미지로 학습됨
- 일반 환경에서는 감지율이 다소 낮을 수 있음

---

## 문의
- 기술 지원: GARAMe Project
- 버전: 1.9.8.2
- 작성일: 2024-12-24
