#!/usr/bin/env python3
"""
SH17 데이터셋 준비 스크립트
- train_files.txt / val_files.txt 기반으로 폴더 분리
- YOLO 학습용 구조로 변환

사용법:
    python prepare_sh17_dataset.py
"""

import os
import shutil
from pathlib import Path

# 경로 설정
DATASET_DIR = Path('/home/garam/바탕화면/code/1.9.8.2/datasets/sh17')
IMAGES_DIR = DATASET_DIR / 'images'
LABELS_DIR = DATASET_DIR / 'labels'

# 출력 디렉토리
TRAIN_IMAGES = DATASET_DIR / 'images_split' / 'train'
VAL_IMAGES = DATASET_DIR / 'images_split' / 'val'
TRAIN_LABELS = DATASET_DIR / 'labels_split' / 'train'
VAL_LABELS = DATASET_DIR / 'labels_split' / 'val'

def main():
    print("=" * 60)
    print("  SH17 데이터셋 준비")
    print("=" * 60)

    # 파일 목록 읽기
    train_files_path = DATASET_DIR / 'train_files.txt'
    val_files_path = DATASET_DIR / 'val_files.txt'

    if not train_files_path.exists():
        print(f"[ERROR] {train_files_path} 파일이 없습니다.")
        return

    if not val_files_path.exists():
        print(f"[ERROR] {val_files_path} 파일이 없습니다.")
        return

    with open(train_files_path, 'r') as f:
        train_files = [line.strip() for line in f if line.strip()]

    with open(val_files_path, 'r') as f:
        val_files = [line.strip() for line in f if line.strip()]

    print(f"  Train 파일: {len(train_files)}개")
    print(f"  Val 파일: {len(val_files)}개")
    print()

    # 출력 디렉토리 생성
    for d in [TRAIN_IMAGES, VAL_IMAGES, TRAIN_LABELS, VAL_LABELS]:
        d.mkdir(parents=True, exist_ok=True)

    # Train 파일 복사/링크
    print("[1/2] Train 데이터 처리 중...")
    copied = 0
    skipped = 0
    for filename in train_files:
        # 이미지
        src_img = IMAGES_DIR / filename
        dst_img = TRAIN_IMAGES / filename

        # 라벨 (확장자를 .txt로 변경)
        label_name = Path(filename).stem + '.txt'
        src_label = LABELS_DIR / label_name
        dst_label = TRAIN_LABELS / label_name

        if src_img.exists():
            if not dst_img.exists():
                # 심볼릭 링크 생성 (용량 절약)
                os.symlink(src_img, dst_img)
            if src_label.exists() and not dst_label.exists():
                os.symlink(src_label, dst_label)
            copied += 1
        else:
            skipped += 1

    print(f"    복사됨: {copied}, 스킵: {skipped}")

    # Val 파일 복사/링크
    print("[2/2] Val 데이터 처리 중...")
    copied = 0
    skipped = 0
    for filename in val_files:
        src_img = IMAGES_DIR / filename
        dst_img = VAL_IMAGES / filename

        label_name = Path(filename).stem + '.txt'
        src_label = LABELS_DIR / label_name
        dst_label = VAL_LABELS / label_name

        if src_img.exists():
            if not dst_img.exists():
                os.symlink(src_img, dst_img)
            if src_label.exists() and not dst_label.exists():
                os.symlink(src_label, dst_label)
            copied += 1
        else:
            skipped += 1

    print(f"    복사됨: {copied}, 스킵: {skipped}")

    print()
    print("=" * 60)
    print("  완료!")
    print("=" * 60)
    print()
    print("데이터셋 구조:")
    print(f"  {DATASET_DIR}/")
    print(f"  ├── images_split/")
    print(f"  │   ├── train/  ({len(train_files)}개)")
    print(f"  │   └── val/    ({len(val_files)}개)")
    print(f"  └── labels_split/")
    print(f"      ├── train/")
    print(f"      └── val/")
    print()
    print("이제 다음 명령어로 학습을 시작하세요:")
    print("  python train_ppe_yolov11.py --data sh17.yaml --epochs 150")

if __name__ == '__main__':
    main()
