# 카메라 좌우 반전 설정 수정

## 개요

거울보기 카메라와 안전교육 카메라의 좌우 반전 동작을 개선했습니다.

**수정 날짜**: 2025-11-05
**버전**: 1.9.0

---

## 주요 변경사항

### 1. 거울보기 카메라 (Mirror View)

#### 기본 동작
- **좌우 반전 체크박스 기본값**: `True` (체크됨)
- **체크됨 상태**: 거울처럼 좌우 반전된 화면 표시
- **체크 해제 상태**: 원본 카메라 화면 표시 (반전 안 함)

#### 설정 저장
- 설정 키: `mirror_flip_horizontal`
- 기본값: `True`
- 저장 위치: `config.conf` 파일의 `[CAMERA]` 섹션

#### 얼굴 인식 박스 및 텍스트
- 좌우 반전된 화면에서도 올바른 위치에 표시
- 한글 이름이 깨지지 않고 정상 표시
- `draw_results_on_flipped()` 메서드 사용

---

### 2. 안전교육 카메라 (Safety Education Camera)

#### 기본 동작
- **거울보기와 반대로 동작**
- 거울보기가 반전(체크됨)이면 → 안전교육은 반전 안 함
- 거울보기가 반전 해제(체크 해제)면 → 안전교육은 반전 적용

#### 적용 화면
1. **안전교육 대화상자** ([safety_education.py](src/tcp_monitor/ui/safety_education.py))
   - 안전교육 포스터 확인 후 얼굴 촬영 화면
   - 실시간 얼굴 인식 및 표시
2. **서명 캡처 대화상자** ([safety_signature.py](src/tcp_monitor/ui/safety_signature.py))
   - 서명 시 얼굴 촬영 프리뷰
   - 얼굴 감지 및 캡처

#### 얼굴 인식 박스 및 텍스트
- 프레임 반전 후 얼굴 인식 수행
- 이미 반전된 프레임에 박스와 텍스트 그리기
- 한글 이름 정상 표시

---

## 기술적 세부사항

### 설정 로직

#### 거울보기 (Mirror View)
```python
# panel.py: show_mirror_view()
flip_var = tk.BooleanVar()
flip_var.set(self.app.cfg.camera.get("mirror_flip_horizontal", True))  # 기본값: True

# panel.py: _update_mirror_frame()
flip_enabled = self.mirror_flip_var.get()
if flip_enabled:
    flipped_bgr = cv2.flip(frame, 1)  # 좌우 반전
else:
    flipped_bgr = frame  # 원본

# 반전된 프레임에 얼굴 인식 결과 그리기
flipped_bgr = self.safety_detector.draw_results_on_flipped(flipped_bgr, detection_results)
```

#### 안전교육 (Safety Education)
```python
# safety_education.py: _update_camera_frame()
mirror_flip = self.config.camera.get("mirror_flip_horizontal", True)
safety_flip = not mirror_flip  # 거울보기와 반대

if safety_flip:
    frame = cv2.flip(frame, 1)  # 좌우 반전

# 이미 반전된 프레임에 얼굴 인식 수행 및 결과 그리기
detection_results = self.safety_detector.detect_all(frame)
frame = self.safety_detector.draw_results(frame, detection_results)
```

#### 서명 캡처 (Safety Signature)
```python
# safety_signature.py: _update_preview() 및 _capture_face()
mirror_flip = self.config.camera.get("mirror_flip_horizontal", True)
flip_horizontal = not mirror_flip  # 거울보기와 반대

if flip_horizontal:
    frame = cv2.flip(frame, 1)  # 좌우 반전
```

---

## 파일 변경사항

### 1. [src/tcp_monitor/ui/panel.py](src/tcp_monitor/ui/panel.py)

**수정 위치**:
- Line 496: 거울보기 기본값 설정 (`mirror_flip_horizontal`)
- Line 532: 설정 저장 키 변경
- Line 748: 실시간 반전 설정 적용

**주요 변경**:
```python
# Before:
flip_var.set(self.app.cfg.camera.get("flip_horizontal", True))
self.app.cfg.camera["flip_horizontal"] = flip_enabled

# After:
flip_var.set(self.app.cfg.camera.get("mirror_flip_horizontal", True))
self.app.cfg.camera["mirror_flip_horizontal"] = flip_enabled
```

---

### 2. [src/tcp_monitor/ui/safety_education.py](src/tcp_monitor/ui/safety_education.py)

**수정 위치**:
- Line 490-504: 안전교육 카메라 반전 로직 추가

**주요 변경**:
```python
# 안전교육 카메라는 거울보기와 반대로 설정
mirror_flip = self.config.camera.get("mirror_flip_horizontal", True)
safety_flip = not mirror_flip  # 거울보기가 반전이면 안전교육은 반전 안 함

if safety_flip:
    frame = cv2.flip(frame, 1)
```

---

### 3. [src/tcp_monitor/ui/safety_signature.py](src/tcp_monitor/ui/safety_signature.py)

**수정 위치**:
- Line 782-796: 서명 프리뷰 반전 로직
- Line 1004-1018: 얼굴 캡처 반전 로직

**주요 변경**:
```python
# Before:
flip_horizontal = self.config.camera.get("flip_horizontal", True)

# After:
mirror_flip = self.config.camera.get("mirror_flip_horizontal", True)
flip_horizontal = not mirror_flip  # 거울보기와 반대
```

---

## 사용자 경험

### 거울보기 사용 시나리오

1. **센서 패널 헤더에서 "거울보기" 버튼 클릭**
2. **좌우 반전 체크박스가 기본으로 체크됨** (거울처럼 보임)
3. 사용자가 손을 왼쪽으로 움직이면 화면에서도 왼쪽으로 이동 (거울과 동일)
4. 얼굴 인식 시 이름이 올바른 위치에 한글로 표시됨
5. 체크박스 해제 시 원본 카메라 화면으로 전환

### 안전교육 사용 시나리오

1. **안전교육 화면 진입 (얼굴 촬영 활성화 시)**
2. **거울보기가 반전 상태이면 안전교육은 반전되지 않음**
3. 일반 카메라처럼 동작 (사용자가 왼쪽으로 움직이면 화면에서는 오른쪽으로 이동)
4. 얼굴 인식 시 이름이 올바른 위치에 한글로 표시됨
5. 얼굴 촬영 및 서명 캡처 화면도 동일한 반전 설정 적용

---

## 설정 예시

### config.conf 파일

```ini
[CAMERA]
mirror_flip_horizontal = True
```

- `True`: 거울보기는 좌우 반전, 안전교육은 반전 안 함 (기본값)
- `False`: 거울보기는 원본, 안전교육은 좌우 반전

---

## 호환성

- **Python 버전**: 3.6 이상
- **필요 라이브러리**:
  - OpenCV (cv2)
  - PIL/Pillow (한글 텍스트 렌더링)
  - face_recognition (선택적)

---

## 테스트 시나리오

### 1. 거울보기 테스트
- [ ] 거울보기 진입 시 좌우 반전 체크박스가 체크됨
- [ ] 체크된 상태에서 손을 움직이면 거울처럼 동작
- [ ] 얼굴 인식 시 한글 이름이 올바른 위치에 표시
- [ ] 체크 해제 시 원본 화면으로 전환
- [ ] 설정이 `config.conf`에 저장됨

### 2. 안전교육 테스트
- [ ] 거울보기가 반전 상태일 때 안전교육 카메라는 반전 안 됨
- [ ] 거울보기가 원본 상태일 때 안전교육 카메라는 반전됨
- [ ] 얼굴 인식 박스와 텍스트가 올바른 위치에 표시
- [ ] 한글 이름이 깨지지 않음

### 3. 서명 캡처 테스트
- [ ] 서명 시 얼굴 프리뷰가 안전교육과 동일한 반전 설정 적용
- [ ] 얼굴 감지 박스가 올바른 위치에 표시
- [ ] 얼굴 캡처 시 정상적으로 저장

---

## 알려진 이슈

없음

---

## 참고 자료

- 한글 텍스트 렌더링: [KOREAN_INPUT_FIX.md](KOREAN_INPUT_FIX.md)
- 얼굴 인식 시스템: [src/tcp_monitor/sensor/safety_detector.py](src/tcp_monitor/sensor/safety_detector.py)
- 거울보기 구현: [src/tcp_monitor/ui/panel.py](src/tcp_monitor/ui/panel.py)

---

**작성일**: 2025-11-05
**버전**: 1.9.0
