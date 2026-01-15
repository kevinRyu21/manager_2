# YOLOv11 PPE 모델 학습 가이드

## 개요

SH17 데이터셋을 사용하여 YOLOv11 PPE 감지 모델을 학습합니다.

**예상 성능 향상**: 기존 대비 15-25% mAP 향상

## 1. 데이터셋 준비

### 1.1 SH17 데이터셋 위치

데이터셋이 이미 준비되어 있습니다:
```
/home/garam/바탕화면/code/1.9.8.2/datasets/sh17/
├── images/          (8,099개 원본 이미지)
├── labels/          (8,099개 라벨 파일)
├── images_split/    (train/val 분리됨)
│   ├── train/       (6,479개)
│   └── val/         (1,620개)
├── labels_split/    (train/val 분리됨)
│   ├── train/
│   └── val/
├── train_files.txt
└── val_files.txt
```

### 1.2 데이터셋 재준비 (필요시)

```bash
cd /home/garam/바탕화면/code/1.9.8.2
source venv/bin/activate
cd training
python prepare_sh17_dataset.py
```

## 2. 학습 실행

### 2.1 기본 학습 (권장)

```bash
cd /home/garam/바탕화면/code/1.9.8.2
source venv/bin/activate
cd training

# YOLOv11m 모델로 학습 (균형 잡힌 성능)
python train_ppe_yolov11.py \
    --data sh17.yaml \
    --model yolo11m.pt \
    --epochs 150 \
    --batch 16 \
    --device 0
```

### 2.2 GPU 메모리 부족 시

```bash
# 배치 크기 줄이기
python train_ppe_yolov11.py \
    --data sh17.yaml \
    --model yolo11m.pt \
    --epochs 150 \
    --batch 8 \
    --device 0

# 더 작은 모델 사용
python train_ppe_yolov11.py \
    --data sh17.yaml \
    --model yolo11s.pt \
    --epochs 150 \
    --batch 16 \
    --device 0
```

### 2.3 CPU 학습 (매우 느림)

```bash
python train_ppe_yolov11.py \
    --data sh17.yaml \
    --model yolo11n.pt \
    --epochs 50 \
    --batch 4 \
    --device cpu
```

## 3. 학습 시간 예상

| GPU | 모델 | 배치 | 에폭 | 예상 시간 |
|-----|------|------|------|----------|
| RTX 3060 | yolo11m | 16 | 150 | 5-7시간 |
| RTX 3060 | yolo11s | 16 | 150 | 3-4시간 |
| RTX 4060 | yolo11m | 8 | 150 | 6-8시간 |
| CPU | yolo11n | 4 | 50 | 24-48시간 |

## 4. 학습 결과

### 4.1 출력 파일

```
runs/detect/ppe-yolov11/
├── weights/
│   ├── best.pt          # 최적 모델 (사용!)
│   └── last.pt          # 마지막 체크포인트
├── results.csv          # 학습 기록
├── results.png          # 학습 그래프
├── confusion_matrix.png # 혼동 행렬
└── ...
```

### 4.2 모델 적용

학습 완료 후 자동으로 복사됨:
- `models/ppe-yolov11-sh17.pt`

## 5. 모델 적용 (detector.py 수정)

학습 완료 후 `src/tcp_monitor/ppe/detector.py` 수정:

```python
# 기존
model_path = 'models/yolo10x.pt'

# 변경
model_path = 'models/ppe-yolov11-sh17.pt'
```

## 6. 학습 중 모니터링

### TensorBoard 사용

```bash
tensorboard --logdir runs/detect
```

브라우저에서 http://localhost:6006 접속

## 7. 문제 해결

### CUDA Out of Memory

```bash
# 배치 크기 줄이기
--batch 8  # 또는 4

# 이미지 크기 줄이기
--imgsz 416  # 기본 640
```

### 학습 재개

```bash
python train_ppe_yolov11.py \
    --data sh17.yaml \
    --resume
```

## 8. SH17 클래스 매핑

| ID | 클래스 | GARAMe 매핑 |
|----|--------|------------|
| 0 | person | person |
| 3 | glasses | glasses |
| 4 | face-mask | mask |
| 9 | gloves | gloves |
| 11 | shoes | boots |
| 12 | safety-vest | vest |
| 14 | helmet | helmet |

---

**작성일**: 2024-12-24
**버전**: GARAMe Manager v1.9.8.2
