#!/usr/bin/env python3
"""
PPE 감지 모델 학습 스크립트 - YOLOv11 + SH17 데이터셋
GARAMe Manager v1.9.8.2

사용법:
    python train_ppe_yolov11.py --data /path/to/sh17/data.yaml --epochs 150

SH17 데이터셋 클래스 (17개):
    0: person      - 사람
    1: head        - 머리
    2: face        - 얼굴
    3: glasses     - 보안경
    4: face-mask   - 마스크
    5: face-guard  - 안면보호구
    6: ear         - 귀
    7: ear-mufs    - 귀마개
    8: hands       - 손
    9: gloves      - 장갑
    10: foot       - 발
    11: shoes      - 신발
    12: safety-vest - 안전조끼
    13: tools      - 도구
    14: helmet     - 안전모
    15: medical-suit - 의료복
    16: safety-suit - 안전복
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='YOLOv11 PPE 모델 학습')
    parser.add_argument('--data', type=str, required=True,
                        help='데이터셋 YAML 파일 경로 (예: sh17/data.yaml)')
    parser.add_argument('--model', type=str, default='yolo11m.pt',
                        help='기본 모델 (yolo11n.pt, yolo11s.pt, yolo11m.pt, yolo11l.pt)')
    parser.add_argument('--epochs', type=int, default=150,
                        help='학습 에폭 수 (기본: 150)')
    parser.add_argument('--batch', type=int, default=16,
                        help='배치 크기 (기본: 16, GPU 메모리 부족시 8로 감소)')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='입력 이미지 크기 (기본: 640)')
    parser.add_argument('--device', type=str, default='0',
                        help='GPU 디바이스 (0, 1, cpu)')
    parser.add_argument('--name', type=str, default='ppe-yolov11',
                        help='실험 이름')
    parser.add_argument('--resume', action='store_true',
                        help='이전 학습 이어서 진행')

    args = parser.parse_args()

    # Ultralytics 임포트
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics가 설치되지 않았습니다.")
        print("  pip install ultralytics")
        sys.exit(1)

    # 데이터셋 파일 확인
    if not os.path.exists(args.data):
        print(f"[ERROR] 데이터셋 파일을 찾을 수 없습니다: {args.data}")
        sys.exit(1)

    print("=" * 60)
    print("  YOLOv11 PPE 모델 학습")
    print("=" * 60)
    print(f"  모델: {args.model}")
    print(f"  데이터셋: {args.data}")
    print(f"  에폭: {args.epochs}")
    print(f"  배치 크기: {args.batch}")
    print(f"  이미지 크기: {args.imgsz}")
    print(f"  디바이스: {args.device}")
    print("=" * 60)
    print()

    # GPU 확인
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"[GPU] {gpu_name} ({gpu_memory:.1f}GB)")
    else:
        print("[CPU] GPU 미감지 - CPU 모드로 학습 (매우 느림)")
        args.device = 'cpu'
    print()

    # 모델 로드
    print(f"[1/3] 모델 로딩: {args.model}")
    model = YOLO(args.model)

    # 학습 시작
    print(f"[2/3] 학습 시작...")
    print()

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project='runs/detect',
        name=args.name,
        exist_ok=True,
        patience=20,          # 조기 종료 (20 에폭 동안 개선 없으면)
        save=True,
        save_period=10,       # 10 에폭마다 체크포인트 저장
        pretrained=True,
        optimizer='AdamW',
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        plots=True,
        val=True,
        resume=args.resume,
        amp=True,             # Mixed Precision (GPU 메모리 절약)
        verbose=True,
    )

    print()
    print("=" * 60)
    print("[3/3] 학습 완료!")
    print("=" * 60)

    # 결과 경로
    save_dir = Path(f'runs/detect/{args.name}')
    best_model = save_dir / 'weights' / 'best.pt'

    print(f"  최적 모델: {best_model}")
    print(f"  결과 폴더: {save_dir}")
    print()

    # 모델 복사 (models 폴더로)
    if best_model.exists():
        import shutil
        dest = Path('../models/ppe-yolov11-sh17.pt')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_model, dest)
        print(f"  모델 복사됨: {dest}")

    # 성능 요약
    print()
    print("=" * 60)
    print("  성능 요약")
    print("=" * 60)

    # 검증 결과 출력
    metrics = model.val()
    print(f"  mAP50: {metrics.box.map50:.4f}")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    print(f"  Precision: {metrics.box.mp:.4f}")
    print(f"  Recall: {metrics.box.mr:.4f}")
    print()

    print("학습이 완료되었습니다!")
    print("models/ppe-yolov11-sh17.pt 파일을 사용하세요.")

if __name__ == '__main__':
    main()
