# GARAMe Manager TCP 연동 가이드

## 개요

이 문서는 센서 장치(라즈베리파이 등)와 GARAMe Manager 간의 TCP 통신 연동 방법을 설명합니다.

---

## 1. 연결 정보

### 1.1 서버 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| 프로토콜 | TCP | 스트림 소켓 |
| 기본 호스트 | 0.0.0.0 | 모든 인터페이스에서 수신 |
| 기본 포트 | 9000 | config.conf에서 변경 가능 |
| 최대 동시 연결 | 16 | listen(16) |
| 연결 타임아웃 | 60초 | 클라이언트 연결당 |

### 1.2 연결 유지 설정 (TCP Keep-Alive)

서버는 TCP Keep-Alive를 다음과 같이 설정합니다:

| 항목 | 값 | 설명 |
|------|-----|------|
| TCP_KEEPIDLE | 60초 | 첫 Keep-Alive 패킷 전송 대기 시간 |
| TCP_KEEPINTVL | 10초 | Keep-Alive 패킷 전송 간격 |
| TCP_KEEPCNT | 3회 | 재시도 횟수 |

---

## 2. 메시지 프로토콜

### 2.1 형식

- **형식**: JSON Lines (줄바꿈으로 구분된 JSON)
- **인코딩**: UTF-8
- **구분자**: `\n` (개행 문자)

```
{"type": "sensor_update", "id": "sensor001", "password": "secret", "data": {...}}\n
{"type": "heartbeat", "id": "sensor001"}\n
```

### 2.2 필수 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| type | string | O | 메시지 타입 |
| id | string | O | 센서 식별자 |
| password | string | △ | 인증 활성화 시 필수 |
| data | object | △ | 센서 데이터 (sensor_update 시 필수) |
| version | string | X | 센서 펌웨어 버전 |

---

## 3. 메시지 타입

### 3.1 sensor_update (센서 데이터 전송)

센서 측정값을 전송합니다.

**요청 예시:**
```json
{
  "type": "sensor_update",
  "id": "sensor001",
  "password": "mypassword",
  "version": "1.0.0",
  "data": {
    "co2": 450,
    "o2": 20.9,
    "h2s": 0.0,
    "co": 0,
    "lel": 0,
    "smoke": 0,
    "temperature": 24.5,
    "humidity": 55.0,
    "water": 0
  }
}
```

### 3.2 heartbeat (연결 유지)

연결 상태를 유지하고 센서가 살아있음을 알립니다.

**요청 예시:**
```json
{
  "type": "heartbeat",
  "id": "sensor001"
}
```

**권장 전송 주기:** 10~30초

### 3.3 water_leak_alert (누수 경보)

누수가 감지되었을 때 전송합니다.

**요청 예시:**
```json
{
  "type": "water_leak_alert",
  "id": "sensor001",
  "password": "mypassword",
  "message": "누수가 감지되었습니다",
  "alert_level": "critical",
  "data": {
    "water": 1
  }
}
```

### 3.4 water_normal_alert (누수 해제)

누수 상태가 해제되었을 때 전송합니다.

**요청 예시:**
```json
{
  "type": "water_normal_alert",
  "id": "sensor001",
  "password": "mypassword",
  "message": "누수 상태가 해제되었습니다",
  "alert_level": "info",
  "data": {
    "water": 0
  }
}
```

---

## 4. 센서 데이터 필드 상세

### 4.1 센서 필드 목록

| 필드 | 타입 | 단위 | 설명 | 정상 범위 |
|------|------|------|------|-----------|
| co2 | number | ppm | 이산화탄소 | ≤ 1000 |
| o2 | number | % | 산소 | 19.5 ~ 23.0 |
| h2s | number | ppm | 황화수소 | ≤ 5 |
| co | number | ppm | 일산화탄소 | ≤ 9 |
| lel | number | %LEL | 가연성가스 | ≤ 10 |
| smoke | number | % | 연기 | 0 |
| temperature | number | ℃ | 온도 | 18 ~ 28 |
| humidity | number | %RH | 습도 | 40 ~ 60 |
| water | number | - | 누수 (0/1) | 0 |

### 4.2 5단계 경보 시스템

Manager는 5단계 경보 시스템을 사용합니다:

| 레벨 | 상태 | 색상 | 설명 |
|------|------|------|------|
| 1 | 정상 | 녹색 (#2ECC71) | 정상 범위 |
| 2 | 관심 | 노랑 (#F1C40F) | 주의 필요 |
| 3 | 주의 | 주황 (#E67E22) | 조치 권고 |
| 4 | 경계 | 빨강 (#E74C3C) | 즉각 조치 필요 |
| 5 | 심각 | 진홍 (#C0392B) | 긴급 대피 |

### 4.3 센서별 임계값 (기본값)

#### 이산화탄소 (CO₂)
| 레벨 | 범위 (ppm) |
|------|------------|
| 정상 | ≤ 1,000 |
| 관심 | ≤ 5,000 |
| 주의 | ≤ 10,000 |
| 경계 | ≤ 15,000 |
| 심각 | > 15,000 |

#### 산소 (O₂)
| 레벨 | 범위 (%) |
|------|----------|
| 정상 | 19.5 ~ 23.0 |
| 관심 | 19.0 ~ 23.0 |
| 주의 | 18.5 ~ 23.3 |
| 경계 | 18.0 ~ 23.5 |
| 심각 | < 18.0 또는 > 23.5 |

#### 황화수소 (H₂S)
| 레벨 | 범위 (ppm) |
|------|------------|
| 정상 | ≤ 5 |
| 관심 | ≤ 8 |
| 주의 | ≤ 10 |
| 경계 | ≤ 15 |
| 심각 | > 15 |

#### 일산화탄소 (CO)
| 레벨 | 범위 (ppm) |
|------|------------|
| 정상 | ≤ 9 |
| 관심 | ≤ 25 |
| 주의 | ≤ 30 |
| 경계 | ≤ 50 |
| 심각 | > 50 |

#### 가연성가스 (LEL)
| 레벨 | 범위 (%LEL) |
|------|-------------|
| 정상 | ≤ 10 |
| 관심 | ≤ 20 |
| 주의 | ≤ 50 |
| 경계 | ≤ 50 |
| 심각 | > 50 |

#### 연기 (Smoke)
| 레벨 | 범위 (%) |
|------|----------|
| 정상 | 0 |
| 관심 | ≤ 10 |
| 주의 | ≤ 25 |
| 경계 | ≤ 50 |
| 심각 | > 50 |

#### 온도 (Temperature)
| 레벨 | 범위 (℃) |
|------|----------|
| 정상 | 18 ~ 28 |
| 관심 | 16 ~ 30 |
| 주의 | 14 ~ 32 |
| 경계 | 12 ~ 33 |
| 심각 | < 12 또는 > 33 |

#### 습도 (Humidity)
| 레벨 | 범위 (%RH) |
|------|-----------|
| 정상 | 40 ~ 60 |
| 관심 | 30 ~ 70 |
| 주의 | 20 ~ 80 |
| 경계 | 20 ~ 80 |
| 심각 | < 20 또는 > 80 |

---

## 5. 인증

### 5.1 인증 설정

config.conf 파일의 `[AUTH]` 섹션에서 설정합니다:

```ini
[AUTH]
enabled = true
users = sensor001:password1,sensor002:password2
```

### 5.2 인증 방식

- **enabled**: `true` / `false`로 인증 활성화 여부 설정
- **users**: `센서ID:비밀번호` 형식으로 쉼표로 구분하여 등록

### 5.3 인증 실패 시

인증 실패 시 해당 메시지는 무시되며, 로그에 `auth NG` 메시지가 기록됩니다.

---

## 6. 구현 예제

### 6.1 Python 클라이언트 예제

```python
import socket
import json
import time
import threading

class SensorClient:
    def __init__(self, host, port, sensor_id, password=None):
        self.host = host
        self.port = port
        self.sensor_id = sensor_id
        self.password = password
        self.sock = None
        self.running = False

    def connect(self):
        """서버에 연결"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.running = True
        print(f"Connected to {self.host}:{self.port}")

    def disconnect(self):
        """연결 종료"""
        self.running = False
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_message(self, msg):
        """메시지 전송"""
        if self.sock:
            data = json.dumps(msg, ensure_ascii=False) + "\n"
            self.sock.sendall(data.encode("utf-8"))

    def send_sensor_data(self, data, version=None):
        """센서 데이터 전송"""
        msg = {
            "type": "sensor_update",
            "id": self.sensor_id,
            "data": data
        }
        if self.password:
            msg["password"] = self.password
        if version:
            msg["version"] = version
        self.send_message(msg)

    def send_heartbeat(self):
        """하트비트 전송"""
        msg = {
            "type": "heartbeat",
            "id": self.sensor_id
        }
        self.send_message(msg)

    def send_water_alert(self, is_leak):
        """누수 알림 전송"""
        msg = {
            "type": "water_leak_alert" if is_leak else "water_normal_alert",
            "id": self.sensor_id,
            "message": "누수 감지" if is_leak else "누수 해제",
            "alert_level": "critical" if is_leak else "info",
            "data": {"water": 1 if is_leak else 0}
        }
        if self.password:
            msg["password"] = self.password
        self.send_message(msg)

    def start_heartbeat(self, interval=30):
        """하트비트 스레드 시작"""
        def heartbeat_loop():
            while self.running:
                try:
                    self.send_heartbeat()
                except Exception as e:
                    print(f"Heartbeat error: {e}")
                    break
                time.sleep(interval)

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()


# 사용 예제
if __name__ == "__main__":
    client = SensorClient(
        host="192.168.1.100",  # Manager IP
        port=9000,
        sensor_id="sensor001",
        password="mypassword"  # 인증 사용 시
    )

    try:
        client.connect()
        client.start_heartbeat(interval=30)

        # 센서 데이터 전송 루프
        while True:
            sensor_data = {
                "co2": 450,
                "o2": 20.9,
                "h2s": 0.0,
                "co": 0,
                "lel": 0,
                "smoke": 0,
                "temperature": 24.5,
                "humidity": 55.0,
                "water": 0
            }
            client.send_sensor_data(sensor_data, version="1.0.0")
            time.sleep(5)  # 5초마다 전송

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        client.disconnect()
```

### 6.2 라즈베리파이 센서 읽기 예제

```python
import time
import board
import busio
from adafruit_scd30 import SCD30  # CO2 센서 예시

def read_sensors():
    """센서 값 읽기 (예시)"""
    # I2C 초기화
    i2c = busio.I2C(board.SCL, board.SDA)
    scd30 = SCD30(i2c)

    # 센서 값 읽기
    if scd30.data_available:
        return {
            "co2": scd30.CO2,
            "temperature": scd30.temperature,
            "humidity": scd30.relative_humidity,
            # 다른 센서 값들...
            "o2": 20.9,  # 별도 센서 필요
            "h2s": 0.0,
            "co": 0,
            "lel": 0,
            "smoke": 0,
            "water": 0
        }
    return None
```

---

## 7. 문제 해결

### 7.1 연결 문제

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| Connection refused | Manager 미실행 | Manager 실행 확인 |
| Connection timeout | 네트워크 문제 | 방화벽, IP 주소 확인 |
| 연결 끊김 | 타임아웃 | 하트비트 전송 주기 단축 |

### 7.2 데이터 전송 문제

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| 데이터 미표시 | 인증 실패 | ID/비밀번호 확인 |
| JSON 파싱 오류 | 형식 오류 | JSON 형식 검증 |
| 첫 데이터 미저장 | 의도된 동작 | 두 번째 데이터부터 저장됨 |

### 7.3 로그 확인

Manager는 다음 로그를 기록합니다:
- `client connected`: 클라이언트 연결
- `client disconnected`: 클라이언트 연결 해제
- `heartbeat`: 하트비트 수신
- `auth NG`: 인증 실패
- `recv version`: 버전 정보 수신

---

## 8. config.conf 설정 예시

```ini
[LISTEN]
host = 0.0.0.0
port = 9000

[AUTH]
enabled = true
users = sensor001:pass1,sensor002:pass2,sensor003:pass3

[STANDARD]
co2_normal_max = 1000
co2_concern_max = 5000
co2_caution_max = 10000
co2_warning_max = 15000
o2_normal_min = 19.5
o2_normal_max = 23.0
# ... 기타 임계값

[ENV]
max_sensors = 4
water_sensor_enabled = true
```

---

## 9. 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2024-01 | 최초 작성 |
| 1.1 | 2024-12 | 5단계 경보 시스템 추가 |

---

**문의:** GARAMe Manager 개발팀
