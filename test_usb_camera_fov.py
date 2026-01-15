#!/usr/bin/env python3
"""
USB 카메라 화각(FOV) 테스트 스크립트

카메라의 지원 해상도 및 화각 관련 속성 확인
"""

import cv2

def test_camera_fov():
    print("USB 카메라 화각(FOV) 테스트")
    print("=" * 60)

    # 카메라 열기
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    # 현재 설정 확인
    print("\n[현재 카메라 설정]")
    current_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    current_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    current_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"현재 해상도: {current_w}x{current_h}")
    print(f"현재 FPS: {current_fps}")

    # 줌 관련 속성 확인
    print("\n[줌/화각 관련 속성]")
    zoom = cap.get(cv2.CAP_PROP_ZOOM)
    focus = cap.get(cv2.CAP_PROP_FOCUS)
    autofocus = cap.get(cv2.CAP_PROP_AUTOFOCUS)
    print(f"줌: {zoom} (-1은 미지원)")
    print(f"포커스: {focus}")
    print(f"오토포커스: {autofocus}")

    # 다양한 해상도 테스트
    print("\n[지원 해상도 테스트]")
    test_resolutions = [
        (640, 480),
        (800, 600),
        (1024, 768),
        (1280, 720),
        (1280, 960),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    ]

    supported = []
    for w, h in test_resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if actual_w == w and actual_h == h:
            status = "✓ 지원"
            supported.append((w, h))
        else:
            status = f"✗ → {actual_w}x{actual_h}"

        print(f"  {w}x{h}: {status}")

    # 최대 해상도로 설정
    if supported:
        max_res = max(supported, key=lambda x: x[0] * x[1])
        print(f"\n[최대 지원 해상도: {max_res[0]}x{max_res[1]}]")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, max_res[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, max_res[1])

    # 줌을 0으로 설정 시도 (화각 최대)
    print("\n[줌 0 설정 시도 (화각 최대화)]")
    result = cap.set(cv2.CAP_PROP_ZOOM, 0)
    new_zoom = cap.get(cv2.CAP_PROP_ZOOM)
    print(f"설정 결과: {result}, 현재 줌: {new_zoom}")

    # 프레임 캡처 및 저장
    print("\n[테스트 프레임 저장]")
    ret, frame = cap.read()
    if ret:
        h, w = frame.shape[:2]
        print(f"캡처 프레임 크기: {w}x{h}")

        output_path = "/tmp/usb_camera_fov_test.jpg"
        cv2.imwrite(output_path, frame)
        print(f"저장 완료: {output_path}")
        print("이미지 뷰어로 화각을 확인하세요.")
    else:
        print("프레임 캡처 실패")

    cap.release()
    print("\n테스트 완료")

if __name__ == "__main__":
    test_camera_fov()
