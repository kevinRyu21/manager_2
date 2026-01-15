# 카메라 리셋 기능 추가

## 개요
다른 프로그램에서 카메라를 사용 중일 때 발생하는 카메라 접근 문제를 해결하기 위한 카메라 리셋 기능을 환경설정에 추가했습니다.

## 추가된 기능

### 1. 환경설정에 카메라 리셋 버튼
- **위치**: 설정 > 환경설정 > 패널/센서 설정 섹션
- **버튼**: "모든 카메라 리셋"

### 2. 카메라 리셋 동작
1. 모든 패널의 거울보기 카메라 해제
2. 시스템의 모든 카메라 장치 강제 해제 (0~9번 카메라)
3. 거울보기가 활성화되어 있던 패널 자동 재시작
4. 완료 메시지로 결과 표시 (해제된 카메라 수, 재시작된 거울보기 수)

### 3. 사용 시나리오
- 다른 프로그램(Cheese, Zoom, OBS 등)에서 카메라를 사용 중일 때
- 카메라가 응답하지 않거나 "이미 사용 중" 오류가 발생할 때
- 거울보기 모드에서 카메라 연결이 끊어졌을 때

## 수정된 파일

### `src/tcp_monitor/ui/environment_settings.py`

#### UI 추가 (라인 231-257)
```python
# 카메라 리셋 버튼
camera_reset_frame = tk.Frame(panel_frame, bg="#F5F5F5")
camera_reset_frame.pack(fill="x", pady=15)
tk.Label(camera_reset_frame, text="카메라 리셋",
         font=("Pretendard", 12, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(anchor="w")
reset_btn_wrap = tk.Frame(camera_reset_frame, bg="#F5F5F5")
reset_btn_wrap.pack(anchor="w", pady=(8, 0))

self.camera_reset_btn = tk.Button(
    reset_btn_wrap,
    text="모든 카메라 리셋",
    command=self._reset_cameras,
    bg="#E67E22",
    fg="#FFFFFF",
    font=("Pretendard", 11, "bold"),
    relief="raised",
    bd=2,
    width=18,
    height=1,
    activebackground="#D35400",
    activeforeground="#FFFFFF"
)
self.camera_reset_btn.pack(side="left")

tk.Label(reset_btn_wrap,
        text="다른 프로그램에서 카메라를 사용 중일 때 클릭하세요.",
        font=("Pretendard", 9), bg="#F5F5F5", fg="#666666").pack(side="left", padx=10)
```

#### 카메라 리셋 함수 구현 (라인 426-494)
```python
def _reset_cameras(self):
    """모든 카메라 리셋 (다른 프로그램에서 사용 중일 때)"""
    try:
        import cv2

        # 확인 대화상자
        confirm = messagebox.askyesno(
            "카메라 리셋",
            "모든 카메라를 리셋하시겠습니까?\n\n"
            "현재 사용 중인 카메라가 모두 해제되고 재초기화됩니다.\n"
            "거울보기 모드가 활성화되어 있다면 자동으로 재시작됩니다.",
            parent=self.dialog
        )

        if not confirm:
            return

        # 카메라 리셋 시작
        reset_count = 0

        # 모든 패널의 거울보기 카메라 중지
        for key, panel in list(self.parent.panels.items()):
            try:
                if hasattr(panel, 'mirror_camera') and panel.mirror_camera is not None:
                    panel.mirror_camera.release()
                    panel.mirror_camera = None
                    reset_count += 1
                    print(f"카메라 리셋: 패널 '{key}' 거울보기 카메라 해제")
            except Exception as e:
                print(f"카메라 리셋: 패널 '{key}' 카메라 해제 오류: {e}")

        # 시스템의 모든 카메라 장치 강제 해제 (0~9번)
        for i in range(10):
            try:
                cam = cv2.VideoCapture(i)
                if cam.isOpened():
                    cam.release()
                    reset_count += 1
                    print(f"카메라 리셋: 카메라 {i}번 해제")
            except Exception:
                pass

        # 모든 패널의 거울보기 모드 재시작
        restart_count = 0
        for key, panel in list(self.parent.panels.items()):
            try:
                if hasattr(panel, 'mirror_mode_active') and panel.mirror_mode_active:
                    # 거울보기가 활성화되어 있었다면 재시작
                    if hasattr(panel, '_start_mirror_camera'):
                        panel._start_mirror_camera()
                        restart_count += 1
                        print(f"카메라 리셋: 패널 '{key}' 거울보기 재시작")
            except Exception as e:
                print(f"카메라 리셋: 패널 '{key}' 거울보기 재시작 오류: {e}")

        # 완료 메시지
        msg = f"카메라 리셋이 완료되었습니다.\n\n"
        msg += f"해제된 카메라: {reset_count}개"
        if restart_count > 0:
            msg += f"\n재시작된 거울보기: {restart_count}개"

        messagebox.showinfo("완료", msg, parent=self.dialog)

    except Exception as e:
        messagebox.showerror(
            "오류",
            f"카메라 리셋 중 오류가 발생했습니다:\n{str(e)}",
            parent=self.dialog
        )
```

## 사용 방법

1. **환경설정 열기**
   - 메인 화면에서 "설정" 메뉴 선택
   - "환경설정" 클릭

2. **카메라 리셋 실행**
   - "패널/센서 설정" 섹션으로 스크롤
   - "모든 카메라 리셋" 버튼 클릭
   - 확인 대화상자에서 "예" 선택

3. **결과 확인**
   - 완료 메시지에서 해제된 카메라 수 확인
   - 거울보기가 자동으로 재시작되었는지 확인

## 기술 세부사항

### 카메라 해제 로직
- OpenCV `cv2.VideoCapture`를 사용하여 카메라 인스턴스 생성 및 해제
- 0~9번 카메라 인덱스를 순회하며 열려있는 카메라 모두 해제
- Linux V4L2 백엔드와 호환

### 거울보기 재시작
- 패널의 `mirror_mode_active` 플래그 확인
- `_start_mirror_camera()` 메서드 호출하여 재초기화
- 오류 발생 시에도 다른 패널의 재시작 계속 진행

## 주의사항

1. **카메라 리셋 중 주의**
   - 거울보기가 일시적으로 중단될 수 있습니다
   - 안전교육 진행 중에는 사용을 피하세요

2. **권한 문제**
   - 시스템에 카메라 접근 권한이 필요합니다
   - Ubuntu에서 `/dev/video*` 장치 접근 권한 확인

3. **재시작 실패**
   - 카메라가 물리적으로 연결되어 있는지 확인
   - 다른 프로그램이 여전히 카메라를 사용 중인지 확인

## 테스트 시나리오

### 1. 정상 동작 테스트
- [ ] 거울보기 모드 활성화
- [ ] 카메라 리셋 실행
- [ ] 거울보기가 자동으로 재시작되는지 확인

### 2. 다중 패널 테스트
- [ ] 여러 센서 패널에서 거울보기 활성화
- [ ] 카메라 리셋 실행
- [ ] 모든 패널의 거울보기가 재시작되는지 확인

### 3. 카메라 충돌 해결 테스트
- [ ] 다른 프로그램(Cheese 등)에서 카메라 사용
- [ ] 거울보기 시작 시 오류 발생 확인
- [ ] 다른 프로그램 종료 후 카메라 리셋 실행
- [ ] 거울보기가 정상 작동하는지 확인

## 관련 이슈
- 카메라가 "이미 사용 중" 오류로 거울보기 시작 실패
- 다른 프로그램 종료 후에도 카메라가 해제되지 않는 문제
- 거울보기 재시작이 필요한 상황

## 버전 정보
- **추가 버전**: v1.9.0
- **수정 날짜**: 2025-11-05
- **작성자**: Claude Code
