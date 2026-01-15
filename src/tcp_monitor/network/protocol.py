"""
TCP 프로토콜 v2.0 핸들러

v2.0 새 기능:
- 양방향 통신 (hello/hello_ack 핸드셰이크)
- 새 센서 필드 (ch4, smoke, ext_input)
- 메시지 서명 (HMAC-SHA256)
- 메시지 ID (UUID) 및 시퀀스 번호
- 시간 동기화
- 설정 동기화
- TLS/SSL 지원
"""

import json
import uuid
import time
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class ProtocolVersion(Enum):
    """프로토콜 버전"""
    V1 = "1.0"
    V2 = "2.0"


class MessageType(Enum):
    """메시지 타입"""
    # 핸드셰이크
    HELLO = "hello"
    HELLO_ACK = "hello_ack"

    # 센서 데이터
    SENSOR_UPDATE = "sensor_update"
    SENSOR_ACK = "sensor_ack"

    # 하트비트
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

    # 알림
    WATER_LEAK_ALERT = "water_leak_alert"
    WATER_NORMAL_ALERT = "water_normal_alert"
    GAS_ALERT = "gas_alert"
    EXT_INPUT_ALERT = "ext_input_alert"
    ALERT_ACK = "alert_ack"

    # 시간 동기화
    TIME_SYNC_REQUEST = "time_sync_request"
    TIME_SYNC_RESPONSE = "time_sync_response"

    # 설정 동기화
    CONFIG_REQUEST = "config_request"
    CONFIG_RESPONSE = "config_response"
    CONFIG_PUSH = "config_push"
    CONFIG_ACK = "config_ack"

    # 상태
    STATUS_REQUEST = "status_request"
    STATUS_RESPONSE = "status_response"

    # 에러
    ERROR = "error"


@dataclass
class ProtocolMessage:
    """프로토콜 메시지 기본 클래스"""
    type: str = ""
    id: str = ""  # 센서 ID
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    protocol_version: str = "2.0"
    sequence: int = 0
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def sign(self, secret_key: str) -> str:
        """HMAC-SHA256 서명 생성"""
        # 서명용 데이터: type + id + msg_id + timestamp
        data = f"{self.type}:{self.id}:{self.msg_id}:{self.timestamp}"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        self.signature = signature
        return signature

    def verify_signature(self, secret_key: str) -> bool:
        """서명 검증"""
        if not self.signature:
            return False
        expected = f"{self.type}:{self.id}:{self.msg_id}:{self.timestamp}"
        expected_sig = hmac.new(
            secret_key.encode('utf-8'),
            expected.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)


@dataclass
class HelloMessage(ProtocolMessage):
    """연결 시작 핸드셰이크 메시지"""
    type: str = "hello"
    device_type: str = "sensor"  # sensor, manager
    firmware_version: str = ""
    capabilities: list = field(default_factory=list)
    supported_sensors: list = field(default_factory=list)


@dataclass
class HelloAckMessage(ProtocolMessage):
    """핸드셰이크 응답 메시지"""
    type: str = "hello_ack"
    status: str = "ok"  # ok, error
    server_time: float = field(default_factory=time.time)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config_version: str = ""
    message: str = ""


@dataclass
class SensorData:
    """센서 데이터 (v2.0 확장)"""
    # 기존 센서 (v1.x)
    co2: Optional[float] = None      # ppm
    co: Optional[float] = None       # ppm
    o2: Optional[float] = None       # %
    h2s: Optional[float] = None      # ppm
    temperature: Optional[float] = None  # ℃
    humidity: Optional[float] = None     # %RH
    water: Optional[int] = None      # 0/1

    # 신규 센서 (v2.0)
    ch4: Optional[float] = None      # %LEL (메탄/가연성 가스)
    smoke: Optional[float] = None    # % (연기)
    ext_input: Optional[int] = None  # 0/1 (외부 접점 입력)

    # 레거시 호환
    lel: Optional[float] = None      # %LEL (ch4와 동일)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (None 값 제외)"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SensorUpdateMessage(ProtocolMessage):
    """센서 데이터 전송 메시지"""
    type: str = "sensor_update"
    password: Optional[str] = None
    version: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_sensor_data(cls, sensor_id: str, data: SensorData, **kwargs):
        """SensorData 객체로부터 생성"""
        return cls(
            id=sensor_id,
            data=data.to_dict(),
            **kwargs
        )


@dataclass
class SensorAckMessage(ProtocolMessage):
    """센서 데이터 수신 확인 메시지"""
    type: str = "sensor_ack"
    status: str = "ok"
    ref_msg_id: str = ""  # 원본 메시지 ID
    alerts: list = field(default_factory=list)  # 경보 목록


@dataclass
class HeartbeatMessage(ProtocolMessage):
    """하트비트 메시지"""
    type: str = "heartbeat"


@dataclass
class HeartbeatAckMessage(ProtocolMessage):
    """하트비트 응답 메시지"""
    type: str = "heartbeat_ack"
    server_time: float = field(default_factory=time.time)
    ref_msg_id: str = ""


@dataclass
class TimeSyncRequest(ProtocolMessage):
    """시간 동기화 요청"""
    type: str = "time_sync_request"
    client_time: float = field(default_factory=time.time)


@dataclass
class TimeSyncResponse(ProtocolMessage):
    """시간 동기화 응답"""
    type: str = "time_sync_response"
    client_time: float = 0.0
    server_time: float = field(default_factory=time.time)
    ref_msg_id: str = ""


@dataclass
class ConfigRequest(ProtocolMessage):
    """설정 요청"""
    type: str = "config_request"
    config_type: str = "all"  # all, thresholds, alerts


@dataclass
class ConfigResponse(ProtocolMessage):
    """설정 응답"""
    type: str = "config_response"
    config_version: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    ref_msg_id: str = ""


@dataclass
class ConfigPush(ProtocolMessage):
    """설정 푸시 (매니저 → 센서)"""
    type: str = "config_push"
    config_version: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigAck(ProtocolMessage):
    """설정 수신 확인"""
    type: str = "config_ack"
    status: str = "ok"
    config_version: str = ""
    ref_msg_id: str = ""


@dataclass
class AlertMessage(ProtocolMessage):
    """알림 메시지"""
    type: str = "gas_alert"
    alert_level: str = "warning"  # info, warning, critical
    sensor_type: str = ""  # co2, co, o2, h2s, ch4, smoke, water, ext_input
    current_value: float = 0.0
    threshold_value: float = 0.0
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertAckMessage(ProtocolMessage):
    """알림 수신 확인"""
    type: str = "alert_ack"
    ref_msg_id: str = ""
    status: str = "received"


@dataclass
class ErrorMessage(ProtocolMessage):
    """에러 메시지"""
    type: str = "error"
    error_code: str = ""
    error_message: str = ""
    ref_msg_id: str = ""


class ProtocolHandler:
    """프로토콜 핸들러"""

    # v2.0 지원 센서 필드
    SENSOR_FIELDS_V2 = [
        'co2', 'co', 'o2', 'h2s', 'temperature', 'humidity',
        'water', 'ch4', 'smoke', 'ext_input', 'lel'
    ]

    # v1.x 호환 센서 필드
    SENSOR_FIELDS_V1 = [
        'co2', 'co', 'o2', 'h2s', 'temperature', 'humidity',
        'water', 'lel', 'smoke'
    ]

    def __init__(self, secret_key: Optional[str] = None, require_signature: bool = False):
        self.secret_key = secret_key
        self.require_signature = require_signature
        self.sequence_counter = 0
        self.session_sequences: Dict[str, int] = {}  # 세션별 시퀀스 추적

    def get_next_sequence(self, session_id: str = "default") -> int:
        """다음 시퀀스 번호 반환"""
        if session_id not in self.session_sequences:
            self.session_sequences[session_id] = 0
        self.session_sequences[session_id] += 1
        return self.session_sequences[session_id]

    def parse_message(self, raw: bytes) -> Tuple[Optional[Dict], str]:
        """
        원시 데이터를 메시지로 파싱

        Returns:
            (parsed_dict, protocol_version)
        """
        try:
            text = raw.decode('utf-8', 'replace').strip()
            obj = json.loads(text)

            if not isinstance(obj, dict):
                return None, ""

            # 프로토콜 버전 감지
            version = obj.get('protocol_version', '1.0')

            return obj, version

        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, ""

    def detect_protocol_version(self, msg: Dict) -> str:
        """메시지에서 프로토콜 버전 감지"""
        # 명시적 버전
        if 'protocol_version' in msg:
            return msg['protocol_version']

        # v2.0 특징 감지
        if any(k in msg for k in ['msg_id', 'sequence', 'signature']):
            return '2.0'

        # v2.0 메시지 타입
        v2_types = ['hello', 'hello_ack', 'heartbeat_ack', 'sensor_ack',
                    'time_sync_request', 'time_sync_response',
                    'config_request', 'config_response', 'config_push']
        if msg.get('type') in v2_types:
            return '2.0'

        # v2.0 센서 필드
        data = msg.get('data', {})
        if any(k in data for k in ['ch4', 'ext_input']):
            return '2.0'

        return '1.0'

    def create_hello_ack(self, sensor_id: str, session_id: str,
                         config_version: str = "", status: str = "ok",
                         message: str = "") -> HelloAckMessage:
        """Hello 응답 생성"""
        return HelloAckMessage(
            id=sensor_id,
            status=status,
            session_id=session_id,
            config_version=config_version,
            message=message,
            sequence=self.get_next_sequence(session_id)
        )

    def create_sensor_ack(self, sensor_id: str, ref_msg_id: str,
                          alerts: list = None, session_id: str = "default") -> SensorAckMessage:
        """센서 데이터 수신 확인 생성"""
        return SensorAckMessage(
            id=sensor_id,
            ref_msg_id=ref_msg_id,
            alerts=alerts or [],
            sequence=self.get_next_sequence(session_id)
        )

    def create_heartbeat_ack(self, sensor_id: str, ref_msg_id: str,
                             session_id: str = "default") -> HeartbeatAckMessage:
        """하트비트 응답 생성"""
        return HeartbeatAckMessage(
            id=sensor_id,
            ref_msg_id=ref_msg_id,
            sequence=self.get_next_sequence(session_id)
        )

    def create_time_sync_response(self, sensor_id: str, client_time: float,
                                  ref_msg_id: str, session_id: str = "default") -> TimeSyncResponse:
        """시간 동기화 응답 생성"""
        return TimeSyncResponse(
            id=sensor_id,
            client_time=client_time,
            ref_msg_id=ref_msg_id,
            sequence=self.get_next_sequence(session_id)
        )

    def create_config_response(self, sensor_id: str, config: Dict,
                               config_version: str, ref_msg_id: str,
                               session_id: str = "default") -> ConfigResponse:
        """설정 응답 생성"""
        return ConfigResponse(
            id=sensor_id,
            config=config,
            config_version=config_version,
            ref_msg_id=ref_msg_id,
            sequence=self.get_next_sequence(session_id)
        )

    def create_config_push(self, sensor_id: str, config: Dict,
                           config_version: str, session_id: str = "default") -> ConfigPush:
        """설정 푸시 생성"""
        return ConfigPush(
            id=sensor_id,
            config=config,
            config_version=config_version,
            sequence=self.get_next_sequence(session_id)
        )

    def create_alert_ack(self, sensor_id: str, ref_msg_id: str,
                         session_id: str = "default") -> AlertAckMessage:
        """알림 수신 확인 생성"""
        return AlertAckMessage(
            id=sensor_id,
            ref_msg_id=ref_msg_id,
            sequence=self.get_next_sequence(session_id)
        )

    def create_error(self, sensor_id: str, error_code: str,
                     error_message: str, ref_msg_id: str = "",
                     session_id: str = "default") -> ErrorMessage:
        """에러 메시지 생성"""
        return ErrorMessage(
            id=sensor_id,
            error_code=error_code,
            error_message=error_message,
            ref_msg_id=ref_msg_id,
            sequence=self.get_next_sequence(session_id)
        )

    def sign_message(self, msg: ProtocolMessage) -> ProtocolMessage:
        """메시지에 서명 추가"""
        if self.secret_key:
            msg.sign(self.secret_key)
        return msg

    def verify_message(self, msg: Dict) -> bool:
        """메시지 서명 검증"""
        if not self.require_signature:
            return True

        if not self.secret_key:
            return True

        signature = msg.get('signature')
        if not signature:
            return False

        # 서명 검증용 데이터 생성
        data = f"{msg.get('type')}:{msg.get('id')}:{msg.get('msg_id')}:{msg.get('timestamp')}"
        expected_sig = hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_sig)

    def normalize_sensor_data(self, data: Dict) -> Dict:
        """센서 데이터 정규화 (v1 → v2 호환)"""
        normalized = {}

        for field in self.SENSOR_FIELDS_V2:
            if field in data:
                normalized[field] = data[field]

        # lel → ch4 매핑 (레거시 호환)
        if 'lel' in data and 'ch4' not in normalized:
            normalized['ch4'] = data['lel']

        return normalized
