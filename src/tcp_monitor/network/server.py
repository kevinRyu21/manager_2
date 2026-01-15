"""
TCP 서버 클래스 v2.0

TCP 수신 서버: 라즈베리에서 오는 JSON Lines 처리
v2.0 기능:
- 양방향 통신 (hello/hello_ack 핸드셰이크)
- 새 센서 필드 지원 (ch4, smoke, ext_input)
- HMAC-SHA256 메시지 서명
- 시간/설정 동기화
- TLS/SSL 지원 (선택적)
- v1.x 역호환
"""

import socket
import ssl
import threading
import json
import uuid
import time
import os
from typing import Optional, Dict, Any, Callable
from ..utils.helpers import now_local
from .protocol import (
    ProtocolHandler, MessageType, ProtocolVersion,
    HelloAckMessage, SensorAckMessage, HeartbeatAckMessage,
    TimeSyncResponse, ConfigResponse, AlertAckMessage, ErrorMessage
)


class ClientSession:
    """클라이언트 세션 정보"""

    def __init__(self, peer: str, conn: socket.socket):
        self.peer = peer
        self.conn = conn
        self.session_id = str(uuid.uuid4())
        self.sensor_id: Optional[str] = None
        self.protocol_version = "1.0"
        self.firmware_version: Optional[str] = None
        self.capabilities: list = []
        self.connected_at = time.time()
        self.last_rx = time.time()
        self.last_tx = time.time()
        self.sequence = 0
        self.authenticated = False

    def update_rx(self):
        """수신 시간 업데이트"""
        self.last_rx = time.time()

    def update_tx(self):
        """송신 시간 업데이트"""
        self.last_tx = time.time()


class TcpServer:
    """TCP 수신 서버 v2.0: 라즈베리에서 오는 JSON Lines 처리"""

    # 프로토콜 버전
    PROTOCOL_VERSION = "2.0"

    def __init__(self, host, port, out_q, auth_validator=None, logger=None,
                 config_manager=None, tls_enabled=False, tls_cert=None, tls_key=None,
                 hmac_secret=None, require_signature=False):
        self.host = host
        self.port = port
        self.q = out_q
        self.auth = auth_validator
        self._stop_evt = threading.Event()
        self.log = logger
        self.config = config_manager
        self._server_thread = None

        # TLS 설정
        self.tls_enabled = tls_enabled
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.ssl_context: Optional[ssl.SSLContext] = None

        # 프로토콜 핸들러
        self.protocol = ProtocolHandler(
            secret_key=hmac_secret,
            require_signature=require_signature
        )

        # 세션 관리
        self.sessions: Dict[str, ClientSession] = {}
        self._sessions_lock = threading.Lock()

        # 첫 센서값 스킵 추적 (peer 기준)
        self._first_sample_skipped = set()

        # 설정 버전 (설정 동기화용)
        self._config_version = str(int(time.time()))

    def start(self):
        """서버 시작"""
        # TLS 컨텍스트 설정
        if self.tls_enabled:
            self._setup_tls()

        self._server_thread = threading.Thread(target=self._run, daemon=True)
        self._server_thread.start()

    def stop(self):
        """서버 중지"""
        self._stop_evt.set()
        if self._server_thread:
            self._server_thread.join(timeout=2.0)

    def _setup_tls(self):
        """TLS/SSL 설정"""
        if not self.tls_cert or not self.tls_key:
            print("[TcpServer] TLS enabled but cert/key not provided, falling back to plain TCP")
            self.tls_enabled = False
            return

        if not os.path.exists(self.tls_cert) or not os.path.exists(self.tls_key):
            print(f"[TcpServer] TLS cert/key files not found, falling back to plain TCP")
            self.tls_enabled = False
            return

        try:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(self.tls_cert, self.tls_key)
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            print("[TcpServer] TLS enabled with TLS 1.2+")
        except Exception as e:
            print(f"[TcpServer] TLS setup failed: {e}, falling back to plain TCP")
            self.tls_enabled = False
            self.ssl_context = None

    def _run(self):
        """서버 실행"""
        srv = None
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.port))
            srv.listen(16)
            srv.settimeout(1.0)

            proto_info = "TLS" if self.tls_enabled else "TCP"
            print(f"[TcpServer v2.0] listening on {self.host}:{self.port} ({proto_info})")
            if self.log:
                self.log.write_run(f"server v2.0 started ({proto_info})")

            while not self._stop_evt.is_set():
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue

                # TLS 래핑
                if self.tls_enabled and self.ssl_context:
                    try:
                        conn = self.ssl_context.wrap_socket(conn, server_side=True)
                    except ssl.SSLError as e:
                        print(f"[TcpServer] TLS handshake failed from {addr}: {e}")
                        conn.close()
                        continue

                t = threading.Thread(target=self._handle, args=(conn, addr), daemon=True)
                t.start()
        finally:
            try:
                srv and srv.close()
            except:
                pass
            if self.log:
                self.log.write_run("server stopped")

    def _handle(self, conn, addr):
        """클라이언트 연결 처리"""
        peer = f"{addr[0]}:{addr[1]}"
        buf = b""

        # 세션 생성
        session = ClientSession(peer, conn)
        with self._sessions_lock:
            self.sessions[peer] = session

        if self.log:
            self.log.write_run(f"client connected {peer}")

        # TCP Keep-Alive 설정
        self._setup_keepalive(conn, peer)

        try:
            conn.settimeout(60.0)
            while not self._stop_evt.is_set():
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        self._process_message(line, session)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.log:
                        self.log.write_run(f"connection error {peer}: {e}")
                    break
        finally:
            try:
                conn.close()
            except:
                pass

            # 세션 제거
            with self._sessions_lock:
                if peer in self.sessions:
                    del self.sessions[peer]

            if self.log:
                self.log.write_run(f"client disconnected {peer}")

    def _setup_keepalive(self, conn, peer):
        """TCP Keep-Alive 설정"""
        try:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            except (AttributeError, OSError):
                pass
        except Exception as e:
            if self.log:
                self.log.write_run(f"Keep-Alive setup failed {peer}: {e}")

    def _process_message(self, raw: bytes, session: ClientSession):
        """메시지 처리"""
        try:
            obj = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return

        if not isinstance(obj, dict):
            return

        session.update_rx()

        # 프로토콜 버전 감지
        version = self.protocol.detect_protocol_version(obj)
        session.protocol_version = version

        msg_type = obj.get("type", "")

        # v2.0 핸드셰이크
        if msg_type == "hello":
            self._handle_hello(obj, session)
            return

        # v2.0 시간 동기화
        if msg_type == "time_sync_request":
            self._handle_time_sync(obj, session)
            return

        # v2.0 설정 요청
        if msg_type == "config_request":
            self._handle_config_request(obj, session)
            return

        # 하트비트
        if msg_type == "heartbeat":
            self._handle_heartbeat(obj, session)
            return

        # 센서 데이터 / 알림
        if msg_type in ["sensor_update", "water_leak_alert", "water_normal_alert",
                        "gas_alert", "ext_input_alert"]:
            self._handle_sensor_data(obj, session)
            return

    def _handle_hello(self, obj: Dict, session: ClientSession):
        """Hello 핸드셰이크 처리"""
        sid = obj.get("id", session.peer.split(":")[0])
        session.sensor_id = sid
        session.firmware_version = obj.get("firmware_version")
        session.capabilities = obj.get("capabilities", [])

        if self.log:
            self.log.write_run(
                f"hello {session.peer} id={sid} "
                f"v={session.firmware_version} caps={session.capabilities}"
            )

        # Hello ACK 응답
        ack = self.protocol.create_hello_ack(
            sensor_id=sid,
            session_id=session.session_id,
            config_version=self._config_version,
            status="ok",
            message="Connected to GARAMe Manager v2.0"
        )
        self._send_message(session, ack.to_dict())

    def _handle_time_sync(self, obj: Dict, session: ClientSession):
        """시간 동기화 처리"""
        sid = obj.get("id", session.sensor_id or session.peer.split(":")[0])
        client_time = obj.get("client_time", 0)
        msg_id = obj.get("msg_id", "")

        response = self.protocol.create_time_sync_response(
            sensor_id=sid,
            client_time=client_time,
            ref_msg_id=msg_id,
            session_id=session.session_id
        )
        self._send_message(session, response.to_dict())

        if self.log:
            self.log.write_run(f"time_sync {session.peer} id={sid}")

    def _handle_config_request(self, obj: Dict, session: ClientSession):
        """설정 요청 처리"""
        sid = obj.get("id", session.sensor_id or session.peer.split(":")[0])
        msg_id = obj.get("msg_id", "")
        config_type = obj.get("config_type", "all")

        # 설정 수집
        config = self._get_sensor_config(config_type)

        response = self.protocol.create_config_response(
            sensor_id=sid,
            config=config,
            config_version=self._config_version,
            ref_msg_id=msg_id,
            session_id=session.session_id
        )
        self._send_message(session, response.to_dict())

        if self.log:
            self.log.write_run(f"config_request {session.peer} id={sid} type={config_type}")

    def _handle_heartbeat(self, obj: Dict, session: ClientSession):
        """하트비트 처리"""
        sid = obj.get("id", session.sensor_id or session.peer.split(":")[0])
        session.sensor_id = sid

        if self.log:
            self.log.write_run(f"heartbeat {session.peer} id={sid}")

        # 큐에 빈 데이터 전송 (연결 상태 업데이트)
        self.q.put(("__data__", {"sid": sid, "peer": session.peer, "data": {}, "version": None}))

        # v2.0: 하트비트 응답 전송
        if session.protocol_version == "2.0":
            msg_id = obj.get("msg_id", "")
            ack = self.protocol.create_heartbeat_ack(
                sensor_id=sid,
                ref_msg_id=msg_id,
                session_id=session.session_id
            )
            self._send_message(session, ack.to_dict())

    def _handle_sensor_data(self, obj: Dict, session: ClientSession):
        """센서 데이터 처리"""
        sid = obj.get("id", session.sensor_id or session.peer.split(":")[0])
        pw = obj.get("password")
        data = obj.get("data", {})
        version = obj.get("version")
        msg_type = obj.get("type")
        msg_id = obj.get("msg_id", "")

        session.sensor_id = sid

        # 인증 검사
        if self.auth and not self.auth(sid, pw):
            if self.log:
                self.log.write_run(f"auth NG {session.peer} id={sid}")
            # v2.0: 에러 응답
            if session.protocol_version == "2.0":
                error = self.protocol.create_error(
                    sensor_id=sid,
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed",
                    ref_msg_id=msg_id,
                    session_id=session.session_id
                )
                self._send_message(session, error.to_dict())
            return

        session.authenticated = True

        # 센서 데이터 정규화 (v1 → v2 호환)
        normalized_data = self.protocol.normalize_sensor_data(data)

        # 알림 처리
        if msg_type in ["water_leak_alert", "water_normal_alert"]:
            self.q.put(("__water_alert__", {
                "sid": sid,
                "peer": session.peer,
                "data": normalized_data,
                "alert_type": msg_type,
                "message": obj.get("message", ""),
                "alert_level": obj.get("alert_level", "info")
            }))
        elif msg_type in ["gas_alert", "ext_input_alert"]:
            self.q.put(("__gas_alert__", {
                "sid": sid,
                "peer": session.peer,
                "data": normalized_data,
                "alert_type": msg_type,
                "sensor_type": obj.get("sensor_type", ""),
                "message": obj.get("message", ""),
                "alert_level": obj.get("alert_level", "warning"),
                "current_value": obj.get("current_value", 0),
                "threshold_value": obj.get("threshold_value", 0)
            }))
        else:
            # 일반 센서 데이터
            if version and self.log:
                self.log.write_run(f"recv version {session.peer} id={sid} v={version}")
            self.q.put(("__data__", {
                "sid": sid,
                "peer": session.peer,
                "data": normalized_data,
                "version": version
            }))

        # 첫 샘플 스킵 로직
        try:
            key = f"{sid}@{session.peer.split(':')[0]}"
            if key not in self._first_sample_skipped:
                self._first_sample_skipped.add(key)
            else:
                if self.log:
                    self.log.on_data(sid, session.peer, normalized_data)
        except Exception:
            if self.log:
                self.log.on_data(sid, session.peer, normalized_data)

        # v2.0: 센서 데이터 수신 확인 전송
        if session.protocol_version == "2.0":
            alerts = self._check_thresholds(normalized_data)
            ack = self.protocol.create_sensor_ack(
                sensor_id=sid,
                ref_msg_id=msg_id,
                alerts=alerts,
                session_id=session.session_id
            )
            self._send_message(session, ack.to_dict())

    def _send_message(self, session: ClientSession, msg: Dict):
        """메시지 전송"""
        try:
            data = json.dumps(msg, ensure_ascii=False) + "\n"
            session.conn.sendall(data.encode("utf-8"))
            session.update_tx()
        except Exception as e:
            if self.log:
                self.log.write_run(f"send error {session.peer}: {e}")

    def _get_sensor_config(self, config_type: str = "all") -> Dict:
        """센서 설정 반환"""
        config = {}

        if not self.config:
            return config

        if config_type in ("all", "thresholds"):
            config["thresholds"] = {
                # 산소
                "o2": {
                    "normal_min": self.config.std.get("o2_normal_min", 19.5),
                    "normal_max": self.config.std.get("o2_normal_max", 23.0),
                    "concern_min": self.config.std.get("o2_concern_min", 19.0),
                    "concern_max": self.config.std.get("o2_concern_max", 23.0),
                    "caution_min": self.config.std.get("o2_caution_min", 18.5),
                    "caution_max": self.config.std.get("o2_caution_max", 23.3),
                    "warning_min": self.config.std.get("o2_warning_min", 18.0),
                    "warning_max": self.config.std.get("o2_warning_max", 23.5),
                    "danger_min": self.config.std.get("o2_danger_min", 17.0),
                    "danger_max": self.config.std.get("o2_danger_max", 24.0),
                },
                # 이산화탄소
                "co2": {
                    "normal_max": self.config.std.get("co2_normal_max", 1000),
                    "concern_max": self.config.std.get("co2_concern_max", 5000),
                    "caution_max": self.config.std.get("co2_caution_max", 10000),
                    "warning_max": self.config.std.get("co2_warning_max", 15000),
                    "danger_max": self.config.std.get("co2_danger_max", 20000),
                },
                # 일산화탄소
                "co": {
                    "normal_max": self.config.std.get("co_normal_max", 9),
                    "concern_max": self.config.std.get("co_concern_max", 25),
                    "caution_max": self.config.std.get("co_caution_max", 30),
                    "warning_max": self.config.std.get("co_warning_max", 50),
                    "danger_max": self.config.std.get("co_danger_max", 100),
                },
                # 황화수소
                "h2s": {
                    "normal_max": self.config.std.get("h2s_normal_max", 5),
                    "concern_max": self.config.std.get("h2s_concern_max", 8),
                    "caution_max": self.config.std.get("h2s_caution_max", 10),
                    "warning_max": self.config.std.get("h2s_warning_max", 15),
                    "danger_max": self.config.std.get("h2s_danger_max", 50),
                },
                # 메탄/가연성 가스 (v2.0)
                "ch4": {
                    "normal_max": self.config.std.get("lel_normal_max", 10),
                    "concern_max": self.config.std.get("lel_concern_max", 20),
                    "caution_max": self.config.std.get("lel_caution_max", 50),
                    "warning_max": self.config.std.get("lel_warning_max", 50),
                    "danger_max": self.config.std.get("lel_danger_max", 100),
                },
                # 연기 (v2.0)
                "smoke": {
                    "normal_max": self.config.std.get("smoke_normal_max", 0),
                    "concern_max": self.config.std.get("smoke_concern_max", 10),
                    "caution_max": self.config.std.get("smoke_caution_max", 25),
                    "warning_max": self.config.std.get("smoke_warning_max", 50),
                    "danger_max": self.config.std.get("smoke_danger_max", 100),
                },
                # 온도
                "temperature": {
                    "normal_min": self.config.std.get("temp_normal_min", 18),
                    "normal_max": self.config.std.get("temp_normal_max", 28),
                    "concern_min": self.config.std.get("temp_concern_min", 16),
                    "concern_max": self.config.std.get("temp_concern_max", 30),
                    "caution_min": self.config.std.get("temp_caution_min", 14),
                    "caution_max": self.config.std.get("temp_caution_max", 32),
                    "warning_min": self.config.std.get("temp_warning_min", 12),
                    "warning_max": self.config.std.get("temp_warning_max", 33),
                    "danger_min": self.config.std.get("temp_danger_min", 10),
                    "danger_max": self.config.std.get("temp_danger_max", 35),
                },
                # 습도
                "humidity": {
                    "normal_min": self.config.std.get("hum_normal_min", 40),
                    "normal_max": self.config.std.get("hum_normal_max", 60),
                    "concern_min": self.config.std.get("hum_concern_min", 30),
                    "concern_max": self.config.std.get("hum_concern_max", 70),
                    "caution_min": self.config.std.get("hum_caution_min", 20),
                    "caution_max": self.config.std.get("hum_caution_max", 80),
                    "warning_min": self.config.std.get("hum_warning_min", 20),
                    "warning_max": self.config.std.get("hum_warning_max", 80),
                    "danger_min": self.config.std.get("hum_danger_min", 15),
                    "danger_max": self.config.std.get("hum_danger_max", 85),
                },
            }

        if config_type in ("all", "alerts"):
            config["alerts"] = {
                "water_sensor_enabled": self.config.env.get("water_sensor_enabled", True),
            }

        return config

    def _check_thresholds(self, data: Dict) -> list:
        """임계값 확인하여 경보 목록 반환"""
        alerts = []

        if not self.config:
            return alerts

        # CO2 체크
        co2 = data.get("co2")
        if co2 is not None:
            if co2 > self.config.std.get("co2_danger_max", 20000):
                alerts.append({"sensor": "co2", "level": "danger", "value": co2})
            elif co2 > self.config.std.get("co2_warning_max", 15000):
                alerts.append({"sensor": "co2", "level": "warning", "value": co2})

        # O2 체크
        o2 = data.get("o2")
        if o2 is not None:
            o2_min = self.config.std.get("o2_danger_min", 17.0)
            o2_max = self.config.std.get("o2_danger_max", 24.0)
            if o2 < o2_min or o2 > o2_max:
                alerts.append({"sensor": "o2", "level": "danger", "value": o2})

        # H2S 체크
        h2s = data.get("h2s")
        if h2s is not None:
            if h2s > self.config.std.get("h2s_danger_max", 50):
                alerts.append({"sensor": "h2s", "level": "danger", "value": h2s})
            elif h2s > self.config.std.get("h2s_warning_max", 15):
                alerts.append({"sensor": "h2s", "level": "warning", "value": h2s})

        # CO 체크
        co = data.get("co")
        if co is not None:
            if co > self.config.std.get("co_danger_max", 100):
                alerts.append({"sensor": "co", "level": "danger", "value": co})
            elif co > self.config.std.get("co_warning_max", 50):
                alerts.append({"sensor": "co", "level": "warning", "value": co})

        # CH4/LEL 체크 (v2.0)
        ch4 = data.get("ch4") or data.get("lel")
        if ch4 is not None:
            if ch4 > self.config.std.get("lel_danger_max", 100):
                alerts.append({"sensor": "ch4", "level": "danger", "value": ch4})
            elif ch4 > self.config.std.get("lel_warning_max", 50):
                alerts.append({"sensor": "ch4", "level": "warning", "value": ch4})

        # Smoke 체크 (v2.0)
        smoke = data.get("smoke")
        if smoke is not None:
            if smoke > self.config.std.get("smoke_danger_max", 100):
                alerts.append({"sensor": "smoke", "level": "danger", "value": smoke})
            elif smoke > self.config.std.get("smoke_warning_max", 50):
                alerts.append({"sensor": "smoke", "level": "warning", "value": smoke})

        # Water 체크
        water = data.get("water")
        if water is not None and water == 1:
            if self.config.env.get("water_sensor_enabled", True):
                alerts.append({"sensor": "water", "level": "critical", "value": water})

        # ext_input 체크 (v2.0)
        ext_input = data.get("ext_input")
        if ext_input is not None and ext_input == 1:
            alerts.append({"sensor": "ext_input", "level": "warning", "value": ext_input})

        return alerts

    def push_config(self, sensor_id: str = None):
        """설정을 센서에 푸시"""
        config = self._get_sensor_config("all")
        self._config_version = str(int(time.time()))

        with self._sessions_lock:
            for peer, session in self.sessions.items():
                if sensor_id and session.sensor_id != sensor_id:
                    continue
                if session.protocol_version != "2.0":
                    continue

                push = self.protocol.create_config_push(
                    sensor_id=session.sensor_id or "unknown",
                    config=config,
                    config_version=self._config_version,
                    session_id=session.session_id
                )
                self._send_message(session, push.to_dict())

    def get_connected_sensors(self) -> list:
        """연결된 센서 목록 반환"""
        with self._sessions_lock:
            return [
                {
                    "peer": s.peer,
                    "sensor_id": s.sensor_id,
                    "protocol_version": s.protocol_version,
                    "firmware_version": s.firmware_version,
                    "connected_at": s.connected_at,
                    "last_rx": s.last_rx,
                    "authenticated": s.authenticated
                }
                for s in self.sessions.values()
            ]
