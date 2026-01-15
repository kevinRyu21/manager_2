# GARAMe Manager 2.0 - Sensor 2.0 TCP 연동 가이드

> **문서 버전**: 2.0.0
> **최종 수정일**: 2025-01-15
> **호환 버전**: Manager 2.0+ / Sensor 2.0+

---

## 목차

1. [개요](#1-개요)
2. [연결 정보](#2-연결-정보)
3. [프로토콜 사양](#3-프로토콜-사양)
4. [메시지 타입](#4-메시지-타입)
5. [센서 데이터 스키마](#5-센서-데이터-스키마)
6. [시간 동기화](#6-시간-동기화)
7. [헬스체크 및 모니터링](#7-헬스체크-및-모니터링)
8. [인증 및 보안](#8-인증-및-보안)
9. [설정 동기화](#9-설정-동기화)
10. [확장성 설계](#10-확장성-설계)
11. [에러 처리](#11-에러-처리)
12. [구현 예제](#12-구현-예제)
13. [마이그레이션 가이드](#13-마이그레이션-가이드)
14. [부록](#14-부록)

---

## 1. 개요

### 1.1 문서 목적

본 문서는 GARAMe Manager 2.0과 GARAMe Sensor 2.0 간의 TCP 기반 양방향 통신 연동 방법을 정의합니다.

### 1.2 주요 변경 사항 (v1.x → v2.0)

| 항목 | v1.x | v2.0 |
|------|------|------|
| 통신 방향 | 단방향 (센서 → 매니저) | **양방향** (센서 ↔ 매니저) |
| 센서 개수 | 7종 (CO₂, CO, O₂, H₂S, 온도, 습도, 누수) | **9종** (+ 메탄, 연기, 외부접점) |
| 시간 동기화 | 없음 | **NTP-스타일 동기화 지원** |
| 헬스체크 | 단순 heartbeat | **상세 상태 보고 + 응답** |
| 설정 | 클라이언트 로컬 설정 | **서버-클라이언트 동기화** |
| 메시지 ID | 없음 | **UUID 기반 추적** |
| 압축 | 없음 | **선택적 gzip 압축** |
| 배치 전송 | 없음 | **다중 메시지 배치 지원** |
| 외부 접점 | 없음 | **5V~24V 접점 입력 지원** |

### 1.3 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      GARAMe Manager 2.0                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ TCP Server (Port 9000)                                  │ │
│  │  ├─ Connection Manager                                  │ │
│  │  ├─ Message Router                                      │ │
│  │  ├─ Time Sync Service                                   │ │
│  │  ├─ Config Distributor                                  │ │
│  │  └─ Health Monitor                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ TCP/IP (JSON Lines)
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Sensor 1 │ │ Sensor 2 │ │ Sensor N │
       │ (9개 채널) │ │ (9개 채널) │ │ (9개 채널) │
       └──────────┘ └──────────┘ └──────────┘
```

---

## 2. 연결 정보

### 2.1 서버 설정

| 항목 | 기본값 | 설명 | 설정 키 |
|------|--------|------|---------|
| 프로토콜 | TCP | 스트림 소켓 | - |
| 호스트 | 0.0.0.0 | 모든 인터페이스 수신 | `[LISTEN] host` |
| 포트 | 9000 | 연결 대기 포트 | `[LISTEN] port` |
| 최대 연결 | 32 | 동시 연결 수 (v2.0 확장) | `[LISTEN] max_connections` |
| Accept 타임아웃 | 1.0초 | 서버 수락 대기 | `[LISTEN] accept_timeout` |
| 연결 타임아웃 | 60초 | 클라이언트별 | `[LISTEN] connection_timeout` |

### 2.2 TCP Keep-Alive 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| TCP_KEEPIDLE | 60초 | 유휴 상태 후 첫 Keep-Alive |
| TCP_KEEPINTVL | 10초 | Keep-Alive 패킷 간격 |
| TCP_KEEPCNT | 3회 | 실패 허용 횟수 |

### 2.3 클라이언트(센서) 연결 설정

```ini
[TCP]
host = 192.168.0.7, 192.168.0.12    # 다중 매니저 지원 (쉼표 구분)
port = 9000
user = sensor001
password = mypassword
connect_timeout = 10.0              # 연결 시도 타임아웃
heartbeat_interval = 30.0           # 하트비트 주기
retry_delay_start = 1.0             # 재연결 초기 대기
retry_delay_max = 30.0              # 재연결 최대 대기
data_interval = 1.0                 # 데이터 전송 주기
compression = false                 # gzip 압축 사용 여부
```

---

## 3. 프로토콜 사양

### 3.1 메시지 형식

- **포맷**: JSON Lines (줄바꿈 구분 JSON)
- **인코딩**: UTF-8
- **라인 종료**: `\n` (LF, 0x0A)
- **버퍼 크기**: 8KB (v2.0 확장)

```
{"type":"...", "msg_id":"...", ...}\n
{"type":"...", "msg_id":"...", ...}\n
```

### 3.2 프로토콜 버전 협상

연결 직후 버전 협상 수행:

```
[센서] → [매니저]
{"type": "hello", "protocol_version": "2.0", "id": "sensor001", ...}

[매니저] → [센서]
{"type": "hello_ack", "protocol_version": "2.0", "server_time": ..., ...}
```

### 3.3 공통 메시지 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `type` | string | ✓ | 메시지 타입 |
| `msg_id` | string | ✓ | UUID v4 메시지 식별자 (추적용) |
| `id` | string | ✓ | 센서/장치 식별자 |
| `ts` | string | ✓ | ISO 8601 타임스탬프 (센서 로컬 시간) |
| `password` | string | △ | 인증 활성화 시 필수 |
| `version` | string | - | 센서 펌웨어 버전 |
| `compressed` | boolean | - | gzip 압축 여부 (기본: false) |

### 3.4 메시지 흐름

```
┌─────────┐                              ┌─────────┐
│  센서   │                              │ 매니저  │
└────┬────┘                              └────┬────┘
     │                                        │
     │──── hello ────────────────────────────▶│
     │◀─── hello_ack (+ server_time) ────────│
     │                                        │
     │──── config_request ───────────────────▶│
     │◀─── config_response ──────────────────│
     │                                        │
     │──── time_sync_request ────────────────▶│
     │◀─── time_sync_response ───────────────│
     │                                        │
     ├────────────── 운영 루프 ───────────────┤
     │                                        │
     │──── sensor_update ────────────────────▶│
     │◀─── ack (선택적) ─────────────────────│
     │                                        │
     │──── heartbeat ────────────────────────▶│
     │◀─── heartbeat_ack ────────────────────│
     │                                        │
     │◀─── config_push (설정 변경 시) ───────│
     │──── config_ack ───────────────────────▶│
     │                                        │
```

---

## 4. 메시지 타입

### 4.1 연결 초기화

#### 4.1.1 hello (센서 → 매니저)

연결 직후 센서 정보 전송:

```json
{
  "type": "hello",
  "msg_id": "550e8400-e29b-41d4-a716-446655440000",
  "id": "sensor001",
  "ts": "2025-01-15T10:30:00.000Z",
  "password": "mypassword",
  "protocol_version": "2.0",
  "version": "2.0.0",
  "capabilities": {
    "sensors": ["co2", "co", "o2", "h2s", "ch4", "smoke", "temperature", "humidity", "water", "ext_input"],
    "compression": true,
    "batch": true,
    "time_sync": true,
    "config_sync": true,
    "external_input": true
  },
  "device_info": {
    "model": "GARAMe-Sensor-Pro",
    "hardware_version": "2.0",
    "os": "Linux",
    "uptime": 3600
  }
}
```

#### 4.1.2 hello_ack (매니저 → 센서)

연결 확인 및 서버 정보 응답:

```json
{
  "type": "hello_ack",
  "msg_id": "550e8400-e29b-41d4-a716-446655440001",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440000",
  "protocol_version": "2.0",
  "server_time": "2025-01-15T10:30:00.123Z",
  "status": "accepted",
  "session_id": "sess_abc123",
  "config_version": "2025011510",
  "features": {
    "ack_mode": "on_error",
    "batch_max_size": 10,
    "compression_threshold": 1024
  }
}
```

### 4.2 센서 데이터 전송

#### 4.2.1 sensor_update (센서 → 매니저)

```json
{
  "type": "sensor_update",
  "msg_id": "550e8400-e29b-41d4-a716-446655440010",
  "id": "sensor001",
  "ts": "2025-01-15T10:30:45.123Z",
  "password": "mypassword",
  "version": "2.0.0",
  "sequence": 12345,
  "data": {
    "co2": 450,
    "co": 0,
    "o2": 20.9,
    "h2s": 0.0,
    "ch4": 0,
    "smoke": 0,
    "temperature": 24.5,
    "humidity": 55.0,
    "water": 0,
    "ext_input": 0
  },
  "sensor_status": {
    "co2": "normal",
    "co": "normal",
    "o2": "normal",
    "h2s": "warming_up",
    "ch4": "normal",
    "smoke": "normal"
  },
  "diagnostics": {
    "battery": 85,
    "signal_strength": -45,
    "error_count": 0
  }
}
```

#### 4.2.2 sensor_update_batch (센서 → 매니저)

여러 샘플을 한 번에 전송 (네트워크 효율화):

```json
{
  "type": "sensor_update_batch",
  "msg_id": "550e8400-e29b-41d4-a716-446655440011",
  "id": "sensor001",
  "ts": "2025-01-15T10:30:50.000Z",
  "password": "mypassword",
  "batch_size": 5,
  "samples": [
    {
      "ts": "2025-01-15T10:30:46.000Z",
      "sequence": 12346,
      "data": { "co2": 451, "o2": 20.9, ... }
    },
    {
      "ts": "2025-01-15T10:30:47.000Z",
      "sequence": 12347,
      "data": { "co2": 452, "o2": 20.8, ... }
    }
  ]
}
```

#### 4.2.3 ack (매니저 → 센서, 선택적)

오류 발생 시에만 응답 (on_error 모드):

```json
{
  "type": "ack",
  "msg_id": "550e8400-e29b-41d4-a716-446655440012",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440010",
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid sensor value: o2 out of range",
    "field": "data.o2"
  }
}
```

### 4.3 하트비트

#### 4.3.1 heartbeat (센서 → 매니저)

```json
{
  "type": "heartbeat",
  "msg_id": "550e8400-e29b-41d4-a716-446655440020",
  "id": "sensor001",
  "ts": "2025-01-15T10:31:00.000Z",
  "status": "healthy",
  "uptime": 7200,
  "memory_usage": 45.2,
  "cpu_usage": 12.5,
  "disk_usage": 23.0,
  "active_sensors": 9,
  "error_count": 0,
  "last_error": null
}
```

#### 4.3.2 heartbeat_ack (매니저 → 센서)

```json
{
  "type": "heartbeat_ack",
  "msg_id": "550e8400-e29b-41d4-a716-446655440021",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440020",
  "server_time": "2025-01-15T10:31:00.050Z",
  "status": "ok",
  "pending_commands": []
}
```

### 4.4 알림 메시지

#### 4.4.1 alert (센서 → 매니저)

```json
{
  "type": "alert",
  "msg_id": "550e8400-e29b-41d4-a716-446655440030",
  "id": "sensor001",
  "ts": "2025-01-15T10:32:00.000Z",
  "password": "mypassword",
  "alert_type": "water_leak",
  "alert_level": "critical",
  "message": "누수가 감지되었습니다",
  "data": {
    "water": 1,
    "location": "Zone A"
  },
  "acknowledged": false
}
```

**alert_type 종류:**

| alert_type | 설명 |
|------------|------|
| `water_leak` | 누수 감지 |
| `water_normal` | 누수 해제 |
| `gas_warning` | 가스 경보 |
| `gas_critical` | 가스 위험 |
| `smoke_detected` | 연기 감지 |
| `ext_input_triggered` | 외부 접점 입력 감지 |
| `ext_input_normal` | 외부 접점 입력 해제 |
| `sensor_fault` | 센서 고장 |
| `connection_lost` | 연결 끊김 |
| `power_low` | 배터리 부족 |
| `calibration_due` | 교정 필요 |

**alert_level 종류:**

| alert_level | 설명 | 색상 코드 |
|-------------|------|-----------|
| `info` | 정보 | #3498DB |
| `warning` | 경고 | #F1C40F |
| `critical` | 위험 | #E74C3C |
| `emergency` | 긴급 | #C0392B |

### 4.5 시간 동기화

#### 4.5.1 time_sync_request (센서 → 매니저)

```json
{
  "type": "time_sync_request",
  "msg_id": "550e8400-e29b-41d4-a716-446655440040",
  "id": "sensor001",
  "ts": "2025-01-15T10:33:00.000Z",
  "client_time": "2025-01-15T10:33:00.123Z"
}
```

#### 4.5.2 time_sync_response (매니저 → 센서)

```json
{
  "type": "time_sync_response",
  "msg_id": "550e8400-e29b-41d4-a716-446655440041",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440040",
  "client_time": "2025-01-15T10:33:00.123Z",
  "server_time": "2025-01-15T10:33:00.200Z",
  "server_receive_time": "2025-01-15T10:33:00.180Z"
}
```

### 4.6 설정 동기화

#### 4.6.1 config_request (센서 → 매니저)

```json
{
  "type": "config_request",
  "msg_id": "550e8400-e29b-41d4-a716-446655440050",
  "id": "sensor001",
  "ts": "2025-01-15T10:34:00.000Z",
  "current_version": "2025011500",
  "sections": ["STANDARD", "ENV", "SENSORS"]
}
```

#### 4.6.2 config_response (매니저 → 센서)

```json
{
  "type": "config_response",
  "msg_id": "550e8400-e29b-41d4-a716-446655440051",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440050",
  "config_version": "2025011510",
  "config": {
    "STANDARD": {
      "co2_normal_max": 1000,
      "co2_concern_max": 5000,
      "co2_caution_max": 10000,
      "co2_warning_max": 15000,
      "o2_normal_min": 19.5,
      "o2_normal_max": 23.0
    },
    "ENV": {
      "temp_min": 18,
      "temp_max": 28,
      "hum_min": 40,
      "hum_max": 60
    },
    "SENSORS": {
      "enabled": ["co2", "o2", "h2s", "co", "lel", "smoke", "ch4", "nh3", "no2"],
      "disabled": [],
      "intervals": {
        "default": 1.0,
        "water": 0.5
      }
    }
  }
}
```

#### 4.6.3 config_push (매니저 → 센서)

설정이 변경되었을 때 푸시:

```json
{
  "type": "config_push",
  "msg_id": "550e8400-e29b-41d4-a716-446655440052",
  "config_version": "2025011520",
  "changed_sections": ["STANDARD"],
  "config": {
    "STANDARD": {
      "co2_normal_max": 800
    }
  },
  "requires_restart": false
}
```

#### 4.6.4 config_ack (센서 → 매니저)

```json
{
  "type": "config_ack",
  "msg_id": "550e8400-e29b-41d4-a716-446655440053",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440052",
  "status": "applied",
  "applied_version": "2025011520"
}
```

### 4.7 명령 전송

#### 4.7.1 command (매니저 → 센서)

```json
{
  "type": "command",
  "msg_id": "550e8400-e29b-41d4-a716-446655440060",
  "command": "calibrate",
  "target": "co2",
  "params": {
    "reference_value": 400
  },
  "timeout": 60
}
```

**지원 명령:**

| command | 설명 | params |
|---------|------|--------|
| `calibrate` | 센서 교정 | `target`, `reference_value` |
| `restart` | 센서 재시작 | `delay` |
| `reset_config` | 설정 초기화 | `sections` |
| `update_firmware` | 펌웨어 업데이트 | `url`, `version` |
| `get_logs` | 로그 요청 | `start_time`, `end_time`, `level` |
| `set_interval` | 전송 주기 변경 | `interval` |

#### 4.7.2 command_result (센서 → 매니저)

```json
{
  "type": "command_result",
  "msg_id": "550e8400-e29b-41d4-a716-446655440061",
  "ref_msg_id": "550e8400-e29b-41d4-a716-446655440060",
  "status": "success",
  "result": {
    "calibration_offset": 15,
    "previous_value": 385,
    "new_value": 400
  },
  "execution_time": 5.2
}
```

---

## 5. 센서 데이터 스키마

### 5.1 센서 구성 개요

#### v1.x 기존 센서 (7종)
- 가스 센서: CO₂(이산화탄소), CO(일산화탄소), O₂(산소), H₂S(황화수소)
- 환경 센서: 온도, 습도
- 특수 센서: 누수

#### v2.0 신규 추가 (2종 + 외부 접점)
- 가스 센서: CH₄(메탄/가연성가스), Smoke(연기)
- 외부 접점: 5V~24V 외부 접점 입력

### 5.2 지원 센서 목록 (9종)

| 필드 | 센서 타입 | 단위 | 범위 | 정상 범위 | 버전 |
|------|-----------|------|------|-----------|------|
| `co2` | 이산화탄소 | ppm | 0~50000 | ≤ 1000 | v1.0+ |
| `co` | 일산화탄소 | ppm | 0~1000 | ≤ 9 | v1.0+ |
| `o2` | 산소 | % | 0~25 | 19.5~23.0 | v1.0+ |
| `h2s` | 황화수소 | ppm | 0~100 | ≤ 5 | v1.0+ |
| `ch4` | 메탄 (가연성가스) | %LEL | 0~100 | ≤ 10 | **v2.0 신규** |
| `smoke` | 연기 | %/m | 0~100 | 0 | **v2.0 신규** |
| `temperature` | 온도 | ℃ | -40~85 | 18~28 | v1.0+ |
| `humidity` | 습도 | %RH | 0~100 | 40~60 | v1.0+ |
| `water` | 누수 | 0/1 | 0~1 | 0 | v1.0+ |
| `ext_input` | 외부 접점 입력 | 0/1 | 0~1 | 0 | **v2.0 신규** |

### 5.3 외부 접점 입력 (ext_input)

v2.0에서 새로 추가된 외부 접점 입력 기능입니다.

#### 사양

| 항목 | 값 |
|------|-----|
| 입력 전압 범위 | 5V ~ 24V DC |
| 입력 타입 | 무전압 접점 (Dry Contact) 또는 전압 입력 |
| 논리 | 0 = 정상 (Open/Low), 1 = 감지 (Close/High) |
| 용도 | 외부 경보, 도어 센서, 비상 버튼 등 |

#### 데이터 형식

```json
{
  "ext_input": 0,           // 단일 접점 (기본)
  "ext_inputs": [0, 1, 0, 0] // 다중 접점 (확장, 최대 4채널)
}
```

#### 외부 접점 알림

```json
{
  "type": "alert",
  "alert_type": "ext_input_triggered",
  "alert_level": "warning",
  "message": "외부 접점 입력이 감지되었습니다",
  "data": {
    "ext_input": 1,
    "channel": 0,
    "trigger_time": "2025-01-15T10:30:00.000Z"
  }
}
```

### 5.4 5단계 경보 시스템

| 레벨 | 상태 | 색상 코드 | 설명 |
|:----:|------|-----------|------|
| 1 | 정상 (Normal) | `#2ECC71` | 안전 범위 |
| 2 | 관심 (Concern) | `#F1C40F` | 모니터링 필요 |
| 3 | 주의 (Caution) | `#E67E22` | 주의 환기 |
| 4 | 경계 (Warning) | `#E74C3C` | 조치 필요 |
| 5 | 심각 (Danger) | `#C0392B` | 즉시 대피 |

### 5.5 센서별 임계값 (기본값)

#### 가스 센서

| 센서 | 정상 | 관심 | 주의 | 경계 | 심각 |
|------|------|------|------|------|------|
| CO₂ (ppm) | ≤1000 | ≤5000 | ≤10000 | ≤15000 | >15000 |
| CO (ppm) | ≤9 | ≤25 | ≤30 | ≤50 | >50 |
| O₂ (%) | 19.5~23.0 | 19.0~23.0 | 18.5~23.3 | 18.0~23.5 | <18.0/>23.5 |
| H₂S (ppm) | ≤5 | ≤8 | ≤10 | ≤15 | >15 |
| CH₄ (%LEL) | ≤10 | ≤20 | ≤30 | ≤50 | >50 |
| Smoke (%/m) | 0 | ≤10 | ≤25 | ≤50 | >50 |

#### 환경 센서

| 센서 | 정상 | 관심 | 주의 | 경계 | 심각 |
|------|------|------|------|------|------|
| 온도 (℃) | 18~28 | 16~30 | 14~32 | 12~33 | <12/>33 |
| 습도 (%RH) | 40~60 | 30~70 | 20~80 | 15~85 | <15/>85 |

#### 특수 센서

| 센서 | 정상 | 경보 |
|------|------|------|
| 누수 (water) | 0 | 1 (감지) |
| 외부 접점 (ext_input) | 0 | 1 (트리거) |

### 5.6 센서 상태 코드

| 상태 | 설명 |
|------|------|
| `normal` | 정상 동작 |
| `warming_up` | 예열 중 |
| `calibrating` | 교정 중 |
| `error` | 오류 발생 |
| `offline` | 오프라인 |
| `maintenance` | 유지보수 모드 |
| `disabled` | 비활성화 |

---

## 6. 시간 동기화

### 6.1 동기화 프로토콜 (NTP-스타일)

```
T1: 클라이언트 요청 전송 시간 (client_time)
T2: 서버 요청 수신 시간 (server_receive_time)
T3: 서버 응답 전송 시간 (server_time)
T4: 클라이언트 응답 수신 시간 (로컬 측정)

왕복 지연(RTT) = (T4 - T1) - (T3 - T2)
시간 오프셋 = ((T2 - T1) + (T3 - T4)) / 2
```

### 6.2 동기화 주기

| 상황 | 주기 |
|------|------|
| 초기 연결 | 즉시 3회 수행 |
| 정상 운영 | 1시간마다 |
| 오프셋 > 1초 | 10분마다 |
| 수동 요청 | 즉시 |

### 6.3 타임스탬프 형식

모든 시간은 **ISO 8601** 형식 사용:

```
2025-01-15T10:30:45.123Z      (UTC)
2025-01-15T19:30:45.123+09:00 (KST)
```

### 6.4 시간 보정 적용

센서는 수신한 오프셋을 적용하여 데이터 전송:

```python
# 센서 측 구현 예시
def get_synced_time():
    local_time = datetime.utcnow()
    synced_time = local_time + timedelta(seconds=time_offset)
    return synced_time.isoformat() + 'Z'
```

---

## 7. 헬스체크 및 모니터링

### 7.1 헬스체크 체계

```
┌─────────────────────────────────────────────────────┐
│                 헬스체크 레벨                        │
├─────────────────────────────────────────────────────┤
│ L1: TCP Keep-Alive (OS 수준)                        │
│     - 60초 유휴 후 프로브 시작                       │
│     - 10초 간격, 3회 실패 시 연결 종료               │
├─────────────────────────────────────────────────────┤
│ L2: Heartbeat (애플리케이션 수준)                    │
│     - 30초 주기 (기본값)                            │
│     - 상세 상태 정보 포함                           │
│     - 응답으로 서버 시간 동기화                      │
├─────────────────────────────────────────────────────┤
│ L3: Sensor Status (데이터 수준)                     │
│     - 각 센서의 개별 상태 모니터링                   │
│     - sensor_update에 포함                         │
└─────────────────────────────────────────────────────┘
```

### 7.2 연결 상태 머신

```
        ┌─────────────────┐
        │    INITIAL      │
        └────────┬────────┘
                 │ connect()
                 ▼
        ┌─────────────────┐
        │   CONNECTING    │
        └────────┬────────┘
                 │ hello_ack received
                 ▼
        ┌─────────────────┐
        │   CONNECTED     │◀─────────────┐
        └────────┬────────┘              │
                 │ timeout/error         │ reconnect
                 ▼                       │
        ┌─────────────────┐              │
        │  DISCONNECTED   │──────────────┘
        └─────────────────┘
```

### 7.3 상태 판정 기준

| 상태 | 조건 | 동작 |
|------|------|------|
| Connected | `last_rx` < 60초 | 정상 표시 |
| Warning | 60초 < `last_rx` < 90초 | 경고 표시 |
| Disconnected | `last_rx` > 90초 | 회색 표시, 재연결 시도 |

### 7.4 Watchdog 시스템

```ini
[WATCHDOG]
enabled = true
health_check_interval = 30    # 상태 확인 주기 (초)
health_timeout = 90           # 응답 없음 허용 시간 (초)
max_restart_count = 10        # 최대 재시작 횟수
restart_delay = 5             # 재시작 대기 시간 (초)
```

---

## 8. 인증 및 보안

### 8.1 보안 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                       보안 계층 구조                              │
├─────────────────────────────────────────────────────────────────┤
│  L4: 메시지 무결성    │ HMAC-SHA256 서명, 시퀀스 번호 검증        │
├─────────────────────────────────────────────────────────────────┤
│  L3: 인증            │ ID/Password, JWT 토큰, API Key            │
├─────────────────────────────────────────────────────────────────┤
│  L2: 전송 암호화      │ TLS 1.2+ (선택적)                        │
├─────────────────────────────────────────────────────────────────┤
│  L1: 네트워크        │ IP 화이트리스트, 방화벽                    │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 TLS/SSL 암호화 (v2.0 신규)

#### 8.2.1 TLS 설정

```ini
[SECURITY]
# TLS 활성화
tls_enabled = true
tls_cert_file = /etc/garame/certs/server.crt
tls_key_file = /etc/garame/certs/server.key
tls_ca_file = /etc/garame/certs/ca.crt

# TLS 버전 (최소 TLS 1.2 권장)
tls_min_version = TLSv1.2

# 암호화 스위트 (강력한 암호화만 허용)
tls_ciphers = ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256

# 클라이언트 인증서 검증 (양방향 TLS)
tls_verify_client = false
```

#### 8.2.2 인증서 생성 (자체 서명)

```bash
# CA 인증서 생성
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=GARAMe-CA/O=GARAMe/C=KR"

# 서버 인증서 생성
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/CN=garame-manager/O=GARAMe/C=KR"
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt

# 클라이언트(센서) 인증서 생성 (양방향 TLS 시)
openssl genrsa -out sensor001.key 2048
openssl req -new -key sensor001.key -out sensor001.csr \
    -subj "/CN=sensor001/O=GARAMe/C=KR"
openssl x509 -req -days 365 -in sensor001.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out sensor001.crt
```

#### 8.2.3 TLS 연결 (Python 클라이언트)

```python
import ssl
import socket

def create_tls_connection(host, port, cert_file=None, key_file=None, ca_file=None):
    """TLS 암호화 연결 생성"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # CA 인증서 로드
    if ca_file:
        context.load_verify_locations(ca_file)
    else:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # 클라이언트 인증서 (양방향 TLS)
    if cert_file and key_file:
        context.load_cert_chain(cert_file, key_file)

    # TCP 소켓 생성 후 TLS 래핑
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tls_sock = context.wrap_socket(sock, server_hostname=host)
    tls_sock.connect((host, port))

    return tls_sock
```

### 8.3 메시지 서명 (HMAC-SHA256)

#### 8.3.1 서명 방식

모든 메시지에 HMAC-SHA256 서명을 추가하여 무결성 검증:

```json
{
  "type": "sensor_update",
  "msg_id": "550e8400-e29b-41d4-a716-446655440010",
  "id": "sensor001",
  "ts": "2025-01-15T10:30:45.123Z",
  "nonce": "abc123def456",
  "data": { ... },
  "signature": "a1b2c3d4e5f6..."
}
```

#### 8.3.2 서명 생성 알고리즘

```python
import hmac
import hashlib
import json
import secrets

def generate_signature(message: dict, secret_key: str) -> str:
    """HMAC-SHA256 서명 생성"""
    # 서명 대상 필드 (signature 제외)
    sign_data = {k: v for k, v in message.items() if k != "signature"}

    # 정렬된 JSON 문자열
    payload = json.dumps(sign_data, sort_keys=True, ensure_ascii=False)

    # HMAC-SHA256 계산
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature

def verify_signature(message: dict, secret_key: str) -> bool:
    """서명 검증"""
    received_sig = message.get("signature", "")
    expected_sig = generate_signature(message, secret_key)
    return hmac.compare_digest(received_sig, expected_sig)

def generate_nonce() -> str:
    """재전송 공격 방지용 nonce 생성"""
    return secrets.token_hex(16)
```

#### 8.3.3 서명 설정

```ini
[SECURITY]
# 메시지 서명 활성화
signature_enabled = true
signature_algorithm = HMAC-SHA256

# 공유 비밀 키 (센서별 또는 공통)
signature_key = your-secret-key-here
# 또는 센서별 키
signature_keys = sensor001:key1,sensor002:key2

# Nonce 검증 (재전송 공격 방지)
nonce_enabled = true
nonce_window = 300           # nonce 유효 시간 (초)
```

### 8.4 인증 방식

#### 8.4.1 기본 인증 (ID/Password)

```ini
[AUTH]
enabled = true
users = sensor001:password1,sensor002:password2,sensor003:password3
max_failed_attempts = 5       # 최대 실패 허용 횟수
lockout_duration = 300        # 잠금 시간 (초)
```

```json
{
  "type": "sensor_update",
  "id": "sensor001",
  "password": "mypassword",
  ...
}
```

#### 8.4.2 JWT 토큰 인증 (v2.0)

```json
{
  "type": "sensor_update",
  "id": "sensor001",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  ...
}
```

**토큰 발급 요청:**

```json
{
  "type": "auth_request",
  "id": "sensor001",
  "password": "mypassword",
  "grant_type": "password"
}
```

**토큰 발급 응답:**

```json
{
  "type": "auth_response",
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "expires_at": "2025-01-16T10:30:00.000Z"
}
```

**토큰 갱신:**

```json
{
  "type": "auth_request",
  "id": "sensor001",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
  "grant_type": "refresh_token"
}
```

#### 8.4.3 API Key 인증

```ini
[AUTH]
api_key_enabled = true
api_keys = sensor001:ak_live_xxxxxxxxxxxx,sensor002:ak_live_yyyyyyyyyyyy
```

```json
{
  "type": "sensor_update",
  "id": "sensor001",
  "api_key": "ak_live_xxxxxxxxxxxx",
  ...
}
```

### 8.5 재전송 공격 방지

#### 8.5.1 Nonce + Timestamp 검증

```json
{
  "type": "sensor_update",
  "msg_id": "550e8400-e29b-41d4-a716-446655440010",
  "id": "sensor001",
  "ts": "2025-01-15T10:30:45.123Z",
  "nonce": "a1b2c3d4e5f6g7h8",
  "sequence": 12345,
  ...
}
```

**검증 규칙:**

| 검증 항목 | 조건 | 실패 시 |
|-----------|------|---------|
| 타임스탬프 | `abs(server_time - ts) < 300초` | 메시지 거부 |
| Nonce | 최근 5분 내 중복 없음 | 메시지 거부 |
| Sequence | 이전 sequence보다 큼 | 경고 로그 |

#### 8.5.2 서버 측 구현

```python
from collections import OrderedDict
import time

class NonceValidator:
    def __init__(self, window_seconds=300, max_size=10000):
        self.window = window_seconds
        self.max_size = max_size
        self.nonces = OrderedDict()  # nonce -> timestamp

    def validate(self, nonce: str, timestamp: float) -> bool:
        """Nonce 검증 및 등록"""
        now = time.time()

        # 오래된 nonce 정리
        cutoff = now - self.window
        while self.nonces:
            oldest_nonce, oldest_ts = next(iter(self.nonces.items()))
            if oldest_ts < cutoff:
                del self.nonces[oldest_nonce]
            else:
                break

        # 타임스탬프 검증
        if abs(now - timestamp) > self.window:
            return False

        # 중복 검사
        if nonce in self.nonces:
            return False

        # 새 nonce 등록
        self.nonces[nonce] = timestamp

        # 크기 제한
        while len(self.nonces) > self.max_size:
            self.nonces.popitem(last=False)

        return True
```

### 8.6 IP 화이트리스트

```ini
[SECURITY]
# IP 화이트리스트 활성화
ip_whitelist_enabled = true

# 허용 IP 목록 (CIDR 지원)
ip_whitelist = 192.168.1.0/24,10.0.0.0/8,172.16.0.0/12

# 블랙리스트 (화이트리스트보다 우선)
ip_blacklist = 192.168.1.100
```

### 8.7 인증 실패 처리

| 실패 사유 | 응답 코드 | 동작 |
|-----------|----------|------|
| 잘못된 ID | `AUTH_FAILED` | 메시지 무시, 로그 기록 |
| 잘못된 비밀번호 | `AUTH_FAILED` | 메시지 무시, 실패 횟수 증가 |
| 계정 잠금 | `ACCOUNT_LOCKED` | 연결 거부, 잠금 시간 후 해제 |
| 만료된 토큰 | `TOKEN_EXPIRED` | 재인증 요청 |
| 유효하지 않은 서명 | `INVALID_SIGNATURE` | 메시지 거부 |
| IP 차단 | `IP_BLOCKED` | 연결 거부 |
| Nonce 중복 | `REPLAY_DETECTED` | 메시지 거부 |

### 8.8 보안 설정 전체 예시

```ini
# =============================================================================
# [SECURITY] 보안 설정 - v2.0
# =============================================================================
[SECURITY]
# --- TLS/SSL 암호화 ---
tls_enabled = true
tls_cert_file = /etc/garame/certs/server.crt
tls_key_file = /etc/garame/certs/server.key
tls_ca_file = /etc/garame/certs/ca.crt
tls_min_version = TLSv1.2
tls_verify_client = false

# --- 메시지 서명 ---
signature_enabled = true
signature_algorithm = HMAC-SHA256
signature_key = your-secret-key-minimum-32-characters

# --- 재전송 공격 방지 ---
nonce_enabled = true
nonce_window = 300
timestamp_tolerance = 60

# --- IP 제한 ---
ip_whitelist_enabled = false
ip_whitelist = 192.168.0.0/16,10.0.0.0/8
ip_blacklist =

# --- 감사 로그 ---
audit_log_enabled = true
audit_log_file = /var/log/garame/audit.log
log_auth_success = true
log_auth_failure = true
log_config_changes = true

# =============================================================================
# [AUTH] 인증 설정
# =============================================================================
[AUTH]
enabled = true
users = sensor001:StrongP@ssw0rd!,sensor002:An0th3rP@ss!

# 토큰 인증
token_enabled = true
token_expiry = 86400
token_algorithm = HS256
token_secret = jwt-secret-key-minimum-32-characters

# API Key 인증
api_key_enabled = false
api_keys =

# 계정 잠금
max_failed_attempts = 5
lockout_duration = 300
```

### 8.9 보안 수준별 권장 설정

| 환경 | TLS | 서명 | Nonce | IP제한 | 토큰 |
|------|:---:|:----:|:-----:|:------:|:----:|
| 개발/테스트 | - | - | - | - | - |
| 내부망 (폐쇄) | △ | ✓ | - | △ | △ |
| 내부망 (개방) | ✓ | ✓ | ✓ | ✓ | ✓ |
| 외부망/인터넷 | ✓ | ✓ | ✓ | ✓ | ✓ |

**범례:** ✓ 필수, △ 권장, - 선택

### 8.10 보안 체크리스트

- [ ] TLS 1.2 이상 사용 (프로덕션)
- [ ] 강력한 비밀번호 정책 (최소 12자, 특수문자)
- [ ] 비밀번호 주기적 변경 (90일)
- [ ] 메시지 서명 활성화
- [ ] Nonce 기반 재전송 방지
- [ ] 인증 실패 로그 모니터링
- [ ] IP 화이트리스트 설정 (필요시)
- [ ] 정기 보안 감사

---

## 9. 설정 동기화

### 9.1 설정 동기화 프로토콜

```
┌─────────┐                              ┌─────────┐
│  센서   │                              │ 매니저  │
└────┬────┘                              └────┬────┘
     │                                        │
     │──── config_request ───────────────────▶│
     │     (current_version: "v1")            │
     │                                        │
     │◀─── config_response ──────────────────│
     │     (config_version: "v2", config:{})  │
     │                                        │
     │     [설정 적용]                         │
     │                                        │
     │──── config_ack ───────────────────────▶│
     │     (applied_version: "v2")            │
```

### 9.2 설정 섹션

| 섹션 | 설명 | 센서 적용 |
|------|------|:--------:|
| `STANDARD` | 센서 임계값 | ✓ |
| `ENV` | 환경 설정 | ✓ |
| `SENSORS` | 센서 활성화/비활성화 | ✓ |
| `DISPLAY` | 표시 설정 | - |
| `NETWORK` | 네트워크 설정 | ✓ |
| `ALERT` | 알림 설정 | ✓ |

### 9.3 설정 버전 관리

설정 버전은 `YYYYMMDDHH` 형식:

```
2025011510 = 2025년 1월 15일 10시 버전
```

### 9.4 설정 충돌 해결

| 상황 | 해결 방법 |
|------|----------|
| 센서 버전 < 서버 버전 | 서버 설정으로 업데이트 |
| 센서 버전 > 서버 버전 | 서버에 설정 동기화 요청 |
| 동일 버전 | 변경 없음 |

---

## 10. 확장성 설계

### 10.1 센서 확장

#### 새 센서 타입 추가 방법

1. **데이터 필드 추가**: `data` 객체에 새 필드 추가
2. **capabilities 선언**: `hello` 메시지에 센서 목록 포함
3. **임계값 설정**: `STANDARD` 섹션에 임계값 추가
4. **하위 호환성**: 기존 필드 유지

```json
// 새 센서 타입 (예: VOC) 추가
{
  "type": "sensor_update",
  "data": {
    "co2": 450,
    "voc": 250,  // 새로 추가된 센서
    ...
  }
}
```

### 10.2 메시지 타입 확장

**확장 규칙:**

1. 새 `type` 값 정의
2. 필수 필드 문서화
3. 하위 호환 유지 (알 수 없는 타입은 무시)

```json
// 커스텀 메시지 타입 예시
{
  "type": "custom_event",
  "msg_id": "...",
  "id": "sensor001",
  "ts": "...",
  "event_name": "door_open",
  "event_data": { ... }
}
```

### 10.3 프로토콜 버전 협상

```json
// 클라이언트 hello
{
  "type": "hello",
  "protocol_version": "2.0",
  "min_protocol_version": "1.0",
  ...
}

// 서버 응답
{
  "type": "hello_ack",
  "protocol_version": "2.0",  // 협상된 버전
  "features": {
    "time_sync": true,        // v2.0+
    "config_sync": true,      // v2.0+
    "batch": true             // v2.0+
  }
}
```

### 10.4 다중 매니저 지원

센서는 여러 매니저에 동시 연결 가능:

```ini
[TCP]
host = 192.168.0.7, 192.168.0.12, 192.168.0.15
port = 9000
failover = true           # 장애 시 자동 전환
load_balance = false      # 부하 분산 (선택)
```

### 10.5 확장 필드 규칙

| 규칙 | 설명 |
|------|------|
| 알 수 없는 필드 무시 | 파싱 오류 없이 진행 |
| 필수 필드 검증 | 누락 시 에러 응답 |
| 타입 검증 | 잘못된 타입 시 에러 응답 |
| 범위 검증 | 범위 초과 시 경고 |

---

## 11. 에러 처리

### 11.1 에러 코드

| 코드 | 설명 | HTTP 등가 |
|------|------|----------|
| `SUCCESS` | 성공 | 200 |
| `AUTH_FAILED` | 인증 실패 | 401 |
| `FORBIDDEN` | 권한 없음 | 403 |
| `NOT_FOUND` | 리소스 없음 | 404 |
| `VALIDATION_ERROR` | 유효성 검증 실패 | 400 |
| `PARSE_ERROR` | JSON 파싱 오류 | 400 |
| `RATE_LIMITED` | 요청 제한 초과 | 429 |
| `INTERNAL_ERROR` | 서버 내부 오류 | 500 |
| `TIMEOUT` | 타임아웃 | 504 |

### 11.2 에러 응답 형식

```json
{
  "type": "error",
  "msg_id": "...",
  "ref_msg_id": "...",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid value for field 'o2': expected 0-25, got 30",
    "field": "data.o2",
    "details": {
      "expected_range": [0, 25],
      "received_value": 30
    }
  }
}
```

### 11.3 재시도 정책

| 에러 코드 | 재시도 | 대기 시간 |
|-----------|:------:|----------|
| `PARSE_ERROR` | ✗ | - |
| `VALIDATION_ERROR` | ✗ | - |
| `AUTH_FAILED` | ✗ | - |
| `RATE_LIMITED` | ✓ | 지수 백오프 |
| `INTERNAL_ERROR` | ✓ | 5초 |
| `TIMEOUT` | ✓ | 즉시 |

### 11.4 연결 복구

```python
# 재연결 로직 (지수 백오프)
retry_delay = 1.0
max_delay = 30.0

while not connected:
    try:
        connect()
    except ConnectionError:
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, max_delay)
```

---

## 12. 구현 예제

### 12.1 Python 센서 클라이언트 (v2.0)

```python
import socket
import json
import time
import threading
import uuid
from datetime import datetime, timezone

class SensorClientV2:
    """GARAMe Sensor 2.0 TCP 클라이언트"""

    PROTOCOL_VERSION = "2.0"

    def __init__(self, host, port, sensor_id, password=None):
        self.host = host
        self.port = port
        self.sensor_id = sensor_id
        self.password = password
        self.sock = None
        self.running = False
        self.time_offset = 0.0
        self.session_id = None
        self.sequence = 0
        self.config_version = None
        self.config = {}

    def generate_msg_id(self):
        """UUID v4 메시지 ID 생성"""
        return str(uuid.uuid4())

    def get_timestamp(self):
        """동기화된 ISO 8601 타임스탬프"""
        utc_now = datetime.now(timezone.utc)
        synced_time = utc_now.timestamp() + self.time_offset
        return datetime.fromtimestamp(synced_time, timezone.utc).isoformat()

    def connect(self):
        """서버에 연결 및 초기화"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10.0)
        self.sock.connect((self.host, self.port))
        self.running = True

        # TCP Keep-Alive 설정
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # Hello 메시지 전송
        self._send_hello()

        # 시간 동기화
        self.sync_time()

        # 설정 동기화
        self.sync_config()

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

    def receive_message(self, timeout=5.0):
        """메시지 수신"""
        self.sock.settimeout(timeout)
        try:
            buffer = b""
            while b"\n" not in buffer:
                chunk = self.sock.recv(4096)
                if not chunk:
                    return None
                buffer += chunk
            line = buffer.split(b"\n")[0]
            return json.loads(line.decode("utf-8"))
        except socket.timeout:
            return None

    def _send_hello(self):
        """Hello 메시지 전송"""
        msg = {
            "type": "hello",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "protocol_version": self.PROTOCOL_VERSION,
            "version": "2.0.0",
            "capabilities": {
                "sensors": ["co2", "co", "o2", "h2s", "ch4", "smoke",
                           "temperature", "humidity", "water", "ext_input"],
                "compression": False,
                "batch": True,
                "time_sync": True,
                "config_sync": True,
                "external_input": True
            }
        }
        if self.password:
            msg["password"] = self.password
        self.send_message(msg)

        # Hello ACK 수신
        response = self.receive_message(timeout=10.0)
        if response and response.get("type") == "hello_ack":
            self.session_id = response.get("session_id")
            self.config_version = response.get("config_version")
            print(f"Session established: {self.session_id}")
        else:
            raise ConnectionError("Hello handshake failed")

    def sync_time(self):
        """시간 동기화 수행"""
        t1 = time.time()

        msg = {
            "type": "time_sync_request",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "client_time": datetime.fromtimestamp(t1, timezone.utc).isoformat()
        }
        self.send_message(msg)

        response = self.receive_message(timeout=5.0)
        t4 = time.time()

        if response and response.get("type") == "time_sync_response":
            t2 = datetime.fromisoformat(
                response["server_receive_time"].replace("Z", "+00:00")
            ).timestamp()
            t3 = datetime.fromisoformat(
                response["server_time"].replace("Z", "+00:00")
            ).timestamp()

            # 오프셋 계산
            self.time_offset = ((t2 - t1) + (t3 - t4)) / 2
            print(f"Time synchronized, offset: {self.time_offset:.3f}s")

    def sync_config(self):
        """설정 동기화"""
        msg = {
            "type": "config_request",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "current_version": self.config_version or "",
            "sections": ["STANDARD", "ENV", "SENSORS"]
        }
        self.send_message(msg)

        response = self.receive_message(timeout=5.0)
        if response and response.get("type") == "config_response":
            self.config_version = response.get("config_version")
            self.config = response.get("config", {})
            print(f"Config synchronized: v{self.config_version}")

    def send_sensor_data(self, data, sensor_status=None, diagnostics=None):
        """센서 데이터 전송"""
        self.sequence += 1
        msg = {
            "type": "sensor_update",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "version": "2.0.0",
            "sequence": self.sequence,
            "data": data
        }
        if self.password:
            msg["password"] = self.password
        if sensor_status:
            msg["sensor_status"] = sensor_status
        if diagnostics:
            msg["diagnostics"] = diagnostics
        self.send_message(msg)

    def send_heartbeat(self, status="healthy", **kwargs):
        """하트비트 전송"""
        msg = {
            "type": "heartbeat",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "status": status,
            **kwargs
        }
        self.send_message(msg)

        # ACK 수신 (비동기 처리 권장)
        response = self.receive_message(timeout=2.0)
        if response and response.get("type") == "heartbeat_ack":
            # 서버 시간으로 미세 조정
            pass

    def send_alert(self, alert_type, alert_level, message, data=None):
        """알림 전송"""
        msg = {
            "type": "alert",
            "msg_id": self.generate_msg_id(),
            "id": self.sensor_id,
            "ts": self.get_timestamp(),
            "alert_type": alert_type,
            "alert_level": alert_level,
            "message": message,
            "data": data or {}
        }
        if self.password:
            msg["password"] = self.password
        self.send_message(msg)

    def start_heartbeat_thread(self, interval=30):
        """하트비트 스레드 시작"""
        def heartbeat_loop():
            while self.running:
                try:
                    self.send_heartbeat(
                        uptime=int(time.time()),
                        memory_usage=50.0,
                        cpu_usage=10.0,
                        active_sensors=9,
                        error_count=0
                    )
                except Exception as e:
                    print(f"Heartbeat error: {e}")
                time.sleep(interval)

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

    def start_time_sync_thread(self, interval=3600):
        """주기적 시간 동기화 스레드"""
        def sync_loop():
            while self.running:
                time.sleep(interval)
                try:
                    self.sync_time()
                except Exception as e:
                    print(f"Time sync error: {e}")

        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()


# 사용 예제
if __name__ == "__main__":
    client = SensorClientV2(
        host="192.168.1.100",
        port=9000,
        sensor_id="sensor001",
        password="mypassword"
    )

    try:
        client.connect()
        client.start_heartbeat_thread(interval=30)
        client.start_time_sync_thread(interval=3600)

        # 센서 데이터 전송 루프
        while True:
            sensor_data = {
                # 가스 센서 (기존)
                "co2": 450,       # 이산화탄소 (ppm)
                "co": 0,          # 일산화탄소 (ppm)
                "o2": 20.9,       # 산소 (%)
                "h2s": 0.0,       # 황화수소 (ppm)
                # 가스 센서 (v2.0 신규)
                "ch4": 0,         # 메탄/가연성가스 (%LEL)
                "smoke": 0,       # 연기 (%/m)
                # 환경 센서
                "temperature": 24.5,  # 온도 (℃)
                "humidity": 55.0,     # 습도 (%RH)
                # 특수 센서
                "water": 0,           # 누수 (0/1)
                "ext_input": 0        # 외부 접점 입력 (0/1) - v2.0 신규
            }

            sensor_status = {
                "co2": "normal",
                "co": "normal",
                "o2": "normal",
                "h2s": "normal",
                "ch4": "normal",
                "smoke": "normal"
            }

            diagnostics = {
                "battery": 85,
                "signal_strength": -45,
                "error_count": 0
            }

            client.send_sensor_data(
                sensor_data,
                sensor_status=sensor_status,
                diagnostics=diagnostics
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        client.disconnect()
```

### 12.2 설정 파일 예시 (config.conf)

```ini
# =============================================================================
# GARAMe Manager 2.0 / Sensor 2.0 Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# [LISTEN] TCP 서버 설정
# -----------------------------------------------------------------------------
[LISTEN]
host = 0.0.0.0
port = 9000
max_connections = 32
accept_timeout = 1.0
connection_timeout = 60

# -----------------------------------------------------------------------------
# [AUTH] 인증 설정
# -----------------------------------------------------------------------------
[AUTH]
enabled = true
users = sensor001:pass1,sensor002:pass2,sensor003:pass3,sensor004:pass4
token_expiry = 86400
max_failed_attempts = 5
lockout_duration = 300

# -----------------------------------------------------------------------------
# [STANDARD] 센서 임계값 (5단계 경보 시스템)
# -----------------------------------------------------------------------------
[STANDARD]
# CO2 (ppm) - 이산화탄소
co2_normal_max = 1000
co2_concern_max = 5000
co2_caution_max = 10000
co2_warning_max = 15000

# CO (ppm) - 일산화탄소
co_normal_max = 9
co_concern_max = 25
co_caution_max = 30
co_warning_max = 50

# O2 (%) - 산소
o2_normal_min = 19.5
o2_normal_max = 23.0
o2_concern_min = 19.0
o2_concern_max = 23.0
o2_caution_min = 18.5
o2_caution_max = 23.3
o2_warning_min = 18.0
o2_warning_max = 23.5

# H2S (ppm) - 황화수소
h2s_normal_max = 5
h2s_concern_max = 8
h2s_caution_max = 10
h2s_warning_max = 15

# CH4 (%LEL) - 메탄/가연성가스 (v2.0 신규)
ch4_normal_max = 10
ch4_concern_max = 20
ch4_caution_max = 30
ch4_warning_max = 50

# Smoke (%/m) - 연기 (v2.0 신규)
smoke_normal_max = 0
smoke_concern_max = 10
smoke_caution_max = 25
smoke_warning_max = 50

# -----------------------------------------------------------------------------
# [ENV] 환경 설정
# -----------------------------------------------------------------------------
[ENV]
temp_min = 18
temp_max = 28
hum_min = 40
hum_max = 60
max_sensors = 16
water_sensor_enabled = true
ext_input_enabled = true       # 외부 접점 입력 활성화 (v2.0 신규)
performance_mode = 2

# -----------------------------------------------------------------------------
# [SENSORS] 센서 활성화 설정 - v2.0 신규
# -----------------------------------------------------------------------------
[SENSORS]
# 기존 센서 (v1.x)
enabled = co2,co,o2,h2s,temperature,humidity,water
# 신규 센서 (v2.0)
enabled_v2 = ch4,smoke,ext_input
disabled =
default_interval = 1.0
water_interval = 0.5
ext_input_interval = 0.1       # 외부 접점 폴링 주기

# -----------------------------------------------------------------------------
# [EXT_INPUT] 외부 접점 설정 - v2.0 신규
# -----------------------------------------------------------------------------
[EXT_INPUT]
enabled = true
channels = 1                   # 접점 채널 수 (1~4)
voltage_min = 5                # 최소 입력 전압 (V)
voltage_max = 24               # 최대 입력 전압 (V)
debounce_ms = 50               # 디바운스 시간 (ms)
trigger_on_high = true         # HIGH 신호에서 트리거
alert_on_trigger = true        # 트리거 시 알림 전송
auto_reset = false             # 자동 리셋 여부

# -----------------------------------------------------------------------------
# [WATCHDOG] 워치독 설정
# -----------------------------------------------------------------------------
[WATCHDOG]
enabled = true
health_check_interval = 30
health_timeout = 90
max_restart_count = 10
restart_delay = 5

# -----------------------------------------------------------------------------
# [NETWORK] 네트워크 설정 - v2.0 신규
# -----------------------------------------------------------------------------
[NETWORK]
compression = false
compression_threshold = 1024
batch_enabled = true
batch_max_size = 10
time_sync_interval = 3600
```

---

## 13. 마이그레이션 가이드

### 13.1 v1.x → v2.0 마이그레이션

#### 호환성 모드

v2.0 매니저는 v1.x 센서와 호환됩니다:

| 기능 | v1.x 센서 | v2.0 센서 |
|------|:---------:|:---------:|
| 기본 데이터 전송 | ✓ | ✓ |
| 하트비트 | ✓ | ✓ |
| 시간 동기화 | ✗ | ✓ |
| 설정 동기화 | ✗ | ✓ |
| 양방향 통신 | ✗ | ✓ |
| 기존 7종 센서 | ✓ | ✓ |
| 메탄(CH₄) 센서 | ✗ | ✓ |
| 연기(Smoke) 센서 | ✗ | ✓ |
| 외부 접점 입력 | ✗ | ✓ |

#### 마이그레이션 단계

1. **매니저 업그레이드**
   - 기존 config.conf 백업
   - 매니저 2.0 설치
   - 설정 마이그레이션 (자동 변환 스크립트 제공)

2. **센서 업그레이드 (선택)**
   - 센서 2.0으로 업데이트
   - 새 프로토콜 기능 활성화

3. **설정 파일 변경**

```diff
  [LISTEN]
  host = 0.0.0.0
  port = 9000
+ max_connections = 32

  [AUTH]
  enabled = true
  users = sensor001:pass1
+ token_expiry = 86400

+ [SENSORS]
+ enabled = co2,co,o2,h2s,temperature,humidity,water
+ enabled_v2 = ch4,smoke,ext_input
+ default_interval = 1.0

+ [EXT_INPUT]
+ enabled = true
+ channels = 1
+ voltage_min = 5
+ voltage_max = 24

+ [NETWORK]
+ compression = false
+ batch_enabled = true
```

### 13.2 하위 호환성

v2.0 매니저는 v1.x 메시지를 자동 감지하고 처리합니다:

```json
// v1.x 형식 (hello 없이 바로 데이터 전송)
{"type": "sensor_update", "id": "sensor001", "data": {...}}

// v2.0 형식 (hello 핸드셰이크 후 데이터 전송)
{"type": "hello", "protocol_version": "2.0", ...}
{"type": "sensor_update", "msg_id": "...", ...}
```

---

## 14. 부록

### 14.1 메시지 타입 요약

| 타입 | 방향 | 설명 |
|------|:----:|------|
| `hello` | → | 연결 초기화 |
| `hello_ack` | ← | 연결 확인 |
| `sensor_update` | → | 센서 데이터 |
| `sensor_update_batch` | → | 배치 데이터 |
| `heartbeat` | → | 연결 유지 |
| `heartbeat_ack` | ← | 하트비트 응답 |
| `alert` | → | 알림 전송 |
| `time_sync_request` | → | 시간 동기화 요청 |
| `time_sync_response` | ← | 시간 동기화 응답 |
| `config_request` | → | 설정 요청 |
| `config_response` | ← | 설정 응답 |
| `config_push` | ← | 설정 푸시 |
| `config_ack` | → | 설정 적용 확인 |
| `command` | ← | 명령 전송 |
| `command_result` | → | 명령 결과 |
| `ack` | ← | 일반 응답 |
| `error` | ↔ | 에러 응답 |

### 14.2 상태 코드 요약

| 코드 | 설명 |
|------|------|
| `SUCCESS` | 성공 |
| `AUTH_FAILED` | 인증 실패 |
| `FORBIDDEN` | 권한 없음 |
| `NOT_FOUND` | 리소스 없음 |
| `VALIDATION_ERROR` | 유효성 검증 실패 |
| `PARSE_ERROR` | JSON 파싱 오류 |
| `RATE_LIMITED` | 요청 제한 초과 |
| `INTERNAL_ERROR` | 서버 내부 오류 |
| `TIMEOUT` | 타임아웃 |

### 14.3 문서 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2024-01 | 최초 작성 (7종 센서: CO₂, CO, O₂, H₂S, 온도, 습도, 누수) |
| 1.1 | 2024-12 | 5단계 경보 시스템 추가 |
| **2.0** | **2025-01** | **양방향 통신, 메탄/연기 센서 추가, 외부 접점 입력, 시간/설정 동기화** |

### 14.4 참고 자료

- GARAMe Manager 2.0 소스 코드
- GARAMe Sensor 2.0 소스 코드
- [JSON Lines 스펙](https://jsonlines.org/)
- [ISO 8601 타임스탬프](https://www.iso.org/iso-8601-date-and-time-format.html)
- [NTP 프로토콜](https://www.ntp.org/)

---

**문의:** GARAMe 개발팀
**최종 업데이트:** 2025-01-15
