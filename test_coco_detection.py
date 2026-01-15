#!/usr/bin/env python3
"""
IP 카메라 COCO 감지 테스트 스크립트

저장된 디버그 프레임으로 YOLO COCO 모델 테스트
"""

import cv2
from ultralytics import YOLO

def test_coco_detection():
    # 디버그 프레임 로드
    frame_path = "/tmp/coco_debug_frame.jpg"
    frame = cv2.imread(frame_path)

    if frame is None:
        print(f"프레임 로드 실패: {frame_path}")
        print("먼저 main.py를 실행하여 IP 카메라 프레임을 저장하세요.")
        return

    h, w = frame.shape[:2]
    print(f"프레임 크기: {w}x{h}")

    # COCO 모델 로드
    print("\nYOLO 모델 로드 중...")
    model = YOLO("yolo11m.pt")
    print(f"모델 클래스 수: {len(model.names)}")

    # 다양한 설정으로 테스트
    test_configs = [
        {"imgsz": 640, "conf": 0.1},
        {"imgsz": 1280, "conf": 0.1},
        {"imgsz": 1920, "conf": 0.1},
        {"imgsz": 2304, "conf": 0.1},  # 원본 해상도
        {"imgsz": 2304, "conf": 0.05},
        {"imgsz": 2304, "conf": 0.01},
    ]

    print("\n" + "="*60)
    print("COCO 감지 테스트 결과")
    print("="*60)

    for cfg in test_configs:
        results = model(frame, verbose=False, conf=cfg["conf"], imgsz=cfg["imgsz"])

        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                # 클래스별 카운트
                class_counts = {}
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    cls_name = model.names.get(cls_id, f"id_{cls_id}")
                    conf_val = float(boxes.conf[i].item())

                    if cls_name not in class_counts:
                        class_counts[cls_name] = []
                    class_counts[cls_name].append(conf_val)

                print(f"\nimgsz={cfg['imgsz']}, conf={cfg['conf']}: {len(boxes)}개 감지")
                for cls_name, confs in sorted(class_counts.items()):
                    max_conf = max(confs)
                    print(f"  - {cls_name}: {len(confs)}개 (max_conf={max_conf:.2f})")
            else:
                print(f"\nimgsz={cfg['imgsz']}, conf={cfg['conf']}: 0개 감지")
        else:
            print(f"\nimgsz={cfg['imgsz']}, conf={cfg['conf']}: 결과 없음")

    # 결과 이미지 저장
    print("\n결과 이미지 저장 중...")
    results = model(frame, verbose=False, conf=0.05, imgsz=2304)
    if results and len(results) > 0:
        result_frame = results[0].plot()
        output_path = "/tmp/coco_detection_result.jpg"
        cv2.imwrite(output_path, result_frame)
        print(f"결과 이미지 저장: {output_path}")
        print("이미지 뷰어로 열어서 감지 결과를 확인하세요.")

if __name__ == "__main__":
    test_coco_detection()
