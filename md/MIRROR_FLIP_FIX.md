# 거울 보기 반전 체크박스 동작 개선

## 개요
거울 보기 모드에서 "좌우 반전" 체크박스 토글 시, 얼굴 인식 박스와 텍스트의 위치가 올바르게 이동하도록 개선했습니다.

## 문제점

### 이전 동작
- 반전 체크박스를 해제해도 박스와 텍스트 위치가 반전된 상태로 유지됨
- `draw_results_on_flipped()` 함수가 항상 반전된 좌표로 그림
- 사용자 혼란 발생

### 개선된 동작
- **반전 체크 ON**: 화면 좌우 반전, 박스/텍스트 **위치만** 좌우로 이동 (글자는 반전되지 않음)
- **반전 체크 OFF**: 원본 화면, 박스/텍스트 원래 위치에 표시

## 수정된 파일

### `src/tcp_monitor/ui/panel.py` (라인 738-774)

#### Before
```python
# 2) 영상만 좌우 반전 (텍스트는 아직 그리지 않음)
try:
    if self.mirror_flip_var is not None:
        flip_enabled = self.mirror_flip_var.get()
    else:
        flip_enabled = self.app.cfg.camera.get("mirror_flip_horizontal", True)

    if flip_enabled:
        flipped_bgr = cv2.flip(frame, 1)
    else:
        flipped_bgr = frame
except Exception as e:
    # 오류 처리
    flipped_bgr = cv2.flip(frame, 1)

# 3) 반전된 프레임 위에 텍스트/박스를 올바른 위치에 그리기
if detection_results is not None:
    try:
        flipped_bgr = self.safety_detector.draw_results_on_flipped(flipped_bgr, detection_results)
    except Exception as e:
        # 오류 처리
```

**문제점**: 반전 여부와 관계없이 항상 `draw_results_on_flipped()` 호출

#### After
```python
# 2) 영상만 좌우 반전 (텍스트는 아직 그리지 않음)
# 체크박스에서 mirror_flip_horizontal 옵션 확인 (실시간 반영)
flip_enabled = True  # 기본값
try:
    if self.mirror_flip_var is not None:
        flip_enabled = self.mirror_flip_var.get()
    else:
        flip_enabled = self.app.cfg.camera.get("mirror_flip_horizontal", True)

    if flip_enabled:
        flipped_bgr = cv2.flip(frame, 1)
    else:
        flipped_bgr = frame
except Exception as e:
    if self.mirror_frame_count % 30 == 0:
        print(f"거울보기: 좌우 반전 오류: {e}")
    # 오류 시 기본값으로 반전 적용 (거울처럼 보이도록)
    try:
        flipped_bgr = cv2.flip(frame, 1)
        flip_enabled = True
    except:
        flipped_bgr = frame
        flip_enabled = False

# 3) 프레임 위에 텍스트/박스를 올바른 위치에 그리기
# flip_enabled에 따라 적절한 그리기 함수 호출
if detection_results is not None:
    try:
        if flip_enabled:
            # 반전된 프레임: draw_results_on_flipped 사용 (박스/텍스트 위치 좌우 이동)
            flipped_bgr = self.safety_detector.draw_results_on_flipped(flipped_bgr, detection_results)
        else:
            # 원본 프레임: 일반 draw_results 사용 (박스/텍스트 원래 위치)
            flipped_bgr = self.safety_detector.draw_results(flipped_bgr, detection_results)
    except Exception as e:
        if self.mirror_frame_count % 30 == 0:
            print(f"거울보기: 프레임 시각화 오류: {e}")
```

**개선점**: `flip_enabled` 플래그에 따라 적절한 그리기 함수 선택

## 기술 세부사항

### 좌표 변환 로직

#### 반전 체크 ON: `draw_results_on_flipped()`
```python
def mirror_box(box):
    x1, y1, x2, y2 = box
    # 박스를 좌우로 뒤집지 말고 위치만 이동
    mirrored_x1 = w - x2
    mirrored_x2 = w - x1
    return (mirrored_x1, y1, mirrored_x2, y2)
```

**예시**:
- 화면 너비: 640px
- 원본 박스: `(100, 50, 200, 150)` (좌측)
- 반전 박스: `(440, 50, 540, 150)` (우측)

#### 반전 체크 OFF: `draw_results()`
```python
# 원본 좌표 그대로 사용
cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
```

### 얼굴 인식 박스 및 텍스트

#### 반전 체크 ON
```python
# 얼굴 인식 결과 표시
recognized_faces = results.get('recognized_faces', [])
for face_info in recognized_faces:
    location = face_info.get('location', None)
    if location:
        # location은 (x1, y1, x2, y2) 형식 (원본 좌표 기준)
        x1, y1, x2, y2 = location
        # 좌우 반전 좌표로 변환 (위치만 이동)
        mx1 = w - x2
        mx2 = w - x1
        my1 = y1
        my2 = y2

        # 얼굴 박스 그리기 (초록색으로 인식된 얼굴 표시)
        cv2.rectangle(display, (mx1, my1), (mx2, my2), (0, 255, 0), 3)

        # 이름 표시 (한글 텍스트, 위치만 이동)
        display = self._put_korean_text(
            display,
            name_text,
            (mx1, my1),
            font_size=28,
            color=(0, 0, 0),  # 검은색 텍스트
            bg_color=(0, 255, 0)  # 초록색 배경
        )
```

**중요**: 텍스트는 `_put_korean_text()` 함수로 그려지며, 글자 자체는 반전되지 않고 위치만 이동합니다.

#### 반전 체크 OFF
- 원본 좌표로 박스와 텍스트 그리기
- 좌표 변환 없음

## 동작 확인

### 1. 반전 체크 ON (기본값)
1. 거울보기 모드 시작
2. 얼굴 인식 박스가 좌우 반전된 위치에 표시
3. 이름 텍스트가 박스 위에 올바른 방향으로 표시 (한글 정상)
4. 화면 전체가 거울처럼 좌우 반전

### 2. 반전 체크 OFF
1. "좌우 반전" 체크박스 해제
2. 화면이 원본으로 복원 (좌우 반전 해제)
3. 얼굴 인식 박스가 원래 위치에 표시
4. 이름 텍스트가 원래 위치에 표시

### 3. 실시간 토글
1. 거울보기 모드 중 체크박스 토글
2. 즉시 화면 반전/해제 적용
3. 박스와 텍스트 위치 즉시 변경
4. 설정 파일에 자동 저장

## 관련 함수

### `draw_results_on_flipped()` - 반전된 프레임용
**파일**: `src/tcp_monitor/sensor/safety_detector.py`
**라인**: 794-930

- 좌우 반전된 프레임에 박스/텍스트 그리기
- 좌표만 좌우로 이동, 모양/방향은 유지
- 한글 텍스트 지원 (PIL)

### `draw_results()` - 원본 프레임용
**파일**: `src/tcp_monitor/sensor/safety_detector.py`
**라인**: 707-792

- 원본 프레임에 박스/텍스트 그리기
- 좌표 변환 없음
- 일반적인 감지 결과 시각화

## 사용자 경험 개선

### Before
- 반전 체크 해제 시 박스 위치가 이상함
- 사용자가 체크박스 기능을 이해하기 어려움
- 얼굴 인식 결과를 신뢰하기 어려움

### After
- 반전 체크 ON/OFF 시 즉각적인 피드백
- 직관적인 동작으로 사용자 이해도 향상
- 거울 보기 모드의 실용성 증가

## 테스트 시나리오

### 1. 기본 동작 테스트
- [ ] 거울보기 모드 시작 (반전 체크 ON)
- [ ] 얼굴 인식 박스가 좌우 반전된 위치에 표시되는지 확인
- [ ] 이름 텍스트가 올바른 방향(한글 정상)으로 표시되는지 확인

### 2. 체크박스 토글 테스트
- [ ] "좌우 반전" 체크박스 해제
- [ ] 화면이 원본으로 복원되는지 확인
- [ ] 박스와 텍스트가 원래 위치로 이동하는지 확인
- [ ] 다시 체크 시 반전되는지 확인

### 3. 설정 저장 테스트
- [ ] 반전 체크 해제 후 거울보기 종료
- [ ] 거울보기 재시작
- [ ] 이전 설정(반전 OFF)이 유지되는지 확인

### 4. 한글 텍스트 테스트
- [ ] 얼굴 인식 시 한글 이름이 표시되는지 확인
- [ ] 반전 ON/OFF 시 한글 텍스트가 깨지지 않는지 확인
- [ ] PIL이 없는 환경에서 기본 폰트로 대체되는지 확인

## 주의사항

1. **PIL(Pillow) 필요**
   - 한글 텍스트를 올바르게 표시하려면 Pillow 설치 필요
   - Ubuntu: `pip install Pillow`
   - 없으면 OpenCV 기본 폰트로 대체 (한글 "????" 표시)

2. **한글 폰트 필요**
   - Ubuntu: `sudo apt-get install -y fonts-nanum`
   - 폰트가 없으면 기본 폰트 사용

3. **성능 영향**
   - `_put_korean_text()`는 PIL을 사용하여 텍스트 그리기
   - 매 프레임마다 BGR↔RGB 변환 수행
   - 저사양 시스템에서 약간의 성능 저하 가능

## 관련 문서
- [CAMERA_FLIP_SETTINGS.md](CAMERA_FLIP_SETTINGS.md) - 카메라 반전 설정 가이드
- [CAMERA_RESET_FEATURE.md](CAMERA_RESET_FEATURE.md) - 카메라 리셋 기능

## 버전 정보
- **수정 버전**: v1.9.0
- **수정 날짜**: 2025-11-05
- **작성자**: Claude Code
