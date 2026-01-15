# 카메라 실행 문제 해결 가이드

## 목차
1. [카메라가 실행되지 않는 경우](#카메라가-실행되지-않는-경우)
2. [Ubuntu/Linux 환경](#ubuntulinux-환경)
3. [카메라 권한 문제](#카메라-권한-문제)
4. [카메라 디바이스 확인](#카메라-디바이스-확인)

---

## 카메라가 실행되지 않는 경우

### 1. OpenCV 설치 확인

카메라 기능은 `opencv-contrib-python` 패키지에 의존합니다.

**확인 방법:**
```bash
source venv/bin/activate
python3 -c "import cv2; print('OpenCV 버전:', cv2.__version__)"
```

**예상 출력:**
```
OpenCV 버전: 4.9.0
```

**설치되지 않았다면:**
```bash
source venv/bin/activate
pip install opencv-contrib-python==4.9.0.80
```

---

### 2. 카메라 디바이스 확인

**테스트 스크립트 실행:**
```bash
source venv/bin/activate
python3 << 'EOF'
import cv2
print("사용 가능한 카메라 찾는 중...")
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"✓ 카메라 {i} 사용 가능")
        ret, frame = cap.read()
        if ret:
            print(f"  - 해상도: {frame.shape[1]}x{frame.shape[0]}")
        cap.release()
    else:
        print(f"✗ 카메라 {i} 사용 불가")
EOF
```

**예상 출력:**
```
사용 가능한 카메라 찾는 중...
✓ 카메라 0 사용 가능
  - 해상도: 640x480
✗ 카메라 1 사용 불가
...
```

---

## Ubuntu/Linux 환경

### 1. v4l2 확인

**v4l-utils 설치:**
```bash
sudo apt update
sudo apt install -y v4l-utils
```

**카메라 디바이스 목록 확인:**
```bash
v4l2-ctl --list-devices
```

**예상 출력:**
```
Integrated Camera: Integrated C (usb-0000:00:14.0-8):
        /dev/video0
        /dev/video1
```

**카메라 포맷 확인:**
```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

---

### 2. 카메라 권한 문제

현재 사용자가 `video` 그룹에 속해 있어야 합니다.

**그룹 확인:**
```bash
groups $USER
```

**video 그룹에 추가:**
```bash
sudo usermod -aG video $USER
```

**재로그인 필요:**
```bash
# 로그아웃 후 다시 로그인하거나
# 시스템 재부팅
sudo reboot
```

---

### 3. 시스템 패키지 확인

카메라 관련 라이브러리가 설치되어 있는지 확인:

```bash
sudo apt update
sudo apt install -y \
    libv4l-dev \
    v4l-utils \
    libopencv-dev \
    python3-opencv
```

---

## 카메라 디바이스 확인

### config.conf 설정

`config.conf` 파일에서 카메라 디바이스 번호를 확인하고 수정하세요.

```ini
[camera]
default_device = 0  # 0, 1, 2 등으로 변경 시도
flip_horizontal = true
```

**다른 카메라 디바이스 시도:**
```ini
[camera]
default_device = 1  # 0에서 1로 변경
```

---

## 카메라 실행 오류 메시지별 해결

### "Cannot open camera" 오류

**원인:**
- 카메라가 다른 프로그램에서 사용 중
- 카메라 권한 문제
- 잘못된 디바이스 번호

**해결 방법:**

1. **다른 프로그램 확인:**
   ```bash
   # Chrome, Zoom, Skype 등의 카메라 사용 프로그램 종료
   lsof /dev/video0
   ```

2. **권한 확인:**
   ```bash
   ls -l /dev/video*
   # 출력: crw-rw----+ 1 root video ... /dev/video0
   ```

3. **디바이스 번호 변경:**
   config.conf에서 `default_device` 값을 0, 1, 2로 순차적으로 시도

---

### "Video device or file not found" 오류

**원인:**
- 카메라가 연결되지 않음
- 드라이버 문제

**해결 방법:**

1. **카메라 연결 확인:**
   ```bash
   ls -l /dev/video*
   ```

   아무것도 출력되지 않으면 카메라가 인식되지 않은 것입니다.

2. **USB 카메라 재연결:**
   - USB 카메라를 뽑았다가 다시 꽂기
   - 다른 USB 포트 시도

3. **드라이버 재로드:**
   ```bash
   sudo modprobe -r uvcvideo
   sudo modprobe uvcvideo
   ```

---

### "VideoCapture API preference" 오류

**원인:**
- OpenCV 백엔드 문제

**해결 방법:**

main.py나 관련 코드에서 카메라 백엔드 지정:

```python
import cv2

# V4L2 백엔드 사용
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# 또는 기본 백엔드
cap = cv2.VideoCapture(0)
```

---

## 추가 디버깅

### 1. 로그 확인

프로그램 실행 시 로그를 확인하여 정확한 오류 메시지를 파악하세요.

```bash
./run.sh -d  # 디버그 모드로 실행
```

또는

```bash
tail -f logs/manager_*.log
tail -f logs/watchdog.log
```

---

### 2. 카메라 테스트 프로그램

간단한 테스트 프로그램으로 카메라 동작 확인:

```python
import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("카메라를 열 수 없습니다")
    exit()

print("카메라 열림 성공!")
print(f"해상도: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다")
        break

    cv2.imshow('Camera Test', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

**실행:**
```bash
source venv/bin/activate
python3 test_camera.py
```

---

## 자주 묻는 질문 (FAQ)

### Q: 카메라가 거꾸로 보입니다
**A:** config.conf에서 flip 옵션 조정:
```ini
[camera]
flip_horizontal = true  # 좌우 반전
flip_vertical = true    # 상하 반전
```

### Q: 카메라 해상도를 변경하고 싶습니다
**A:** 코드에서 해상도 설정:
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
```

### Q: 여러 카메라 중 특정 카메라만 사용하고 싶습니다
**A:** config.conf에서 디바이스 번호 지정:
```ini
[camera]
default_device = 1  # 두 번째 카메라 사용
```

---

## 문제가 계속되는 경우

1. 시스템 로그 확인:
   ```bash
   dmesg | grep video
   journalctl -xe | grep camera
   ```

2. OpenCV 재설치:
   ```bash
   source venv/bin/activate
   pip uninstall opencv-contrib-python opencv-python
   pip install opencv-contrib-python==4.9.0.80
   ```

3. GitHub Issues에 문제 보고
   - 오류 메시지
   - 시스템 정보 (Ubuntu 버전, 카메라 모델)
   - 로그 파일

---

**관련 문서:**
- [UBUNTU_INSTALLATION_GUIDE.md](UBUNTU_INSTALLATION_GUIDE.md)
- [README.md](README.md)
