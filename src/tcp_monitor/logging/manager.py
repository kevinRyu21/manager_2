"""
로그 관리자 클래스

logs/run/run_YYYYMMDD.log (일별 실행 로그)
logs/data/data_YYYYMMDD.log (일별 데이터 로그)
logs/warning/warning_YYYYMMDD.log (일별 경고 로그 - 임계값 초과)
"""

import os
import json
import sqlite3
import time
from collections import defaultdict
from ..utils.helpers import now_local, fmt_ts, ensure_dir


class LogManager:
    """
    logs/run/run_YYYYMMDD.log (일별 실행 로그)
    logs/data/data_YYYYMMDD.log (일별 데이터 로그, 실시간 기록)
    logs/warning/warning_YYYYMMDD.log (일별 경고 로그, 임계값 초과 시)
    """

    def __init__(self, base_dir, server_host, server_port, config=None):
        self.base = os.path.join(base_dir, "logs")
        self.run_dir = os.path.join(self.base, "run")
        self.data_dir = os.path.join(self.base, "data")
        self.warning_dir = os.path.join(self.base, "warning")

        # 하위 폴더 생성
        ensure_dir(self.run_dir)
        ensure_dir(self.data_dir)
        ensure_dir(self.warning_dir)

        # 기존 로그 파일 마이그레이션
        self._migrate_old_logs()

        self.srv = f"{server_host}:{server_port}"
        self.config = config

        self._run_fp = None
        self._data_fp = None
        self._warning_fp = None

        self._run_tag = None
        self._data_tag = None
        self._warning_tag = None

        # 통계 캐시 (메모리 캐시)
        self._stats_cache = {}
        self._stats_cache_time = {}
        self._cache_ttl = 2.0  # 2초간 캐시 유지

        # 시간별 데이터 캐시 (더 긴 TTL)
        self._data_cache = {}
        self._data_cache_time = {}
        self._data_cache_ttl = 5.0  # 5초간 캐시 유지

        # SQLite 데이터베이스 초기화
        self.db_path = os.path.join(self.base, "sensor_data.db")
        self._init_database()
        self._db_conn = None
        self._db_tag = None

    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 센서 데이터 테이블 생성 (인덱스 최적화)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                date TEXT NOT NULL,
                sid TEXT NOT NULL,
                peer_ip TEXT NOT NULL,
                co2 REAL,
                h2s REAL,
                co REAL,
                o2 REAL,
                temperature REAL,
                humidity REAL,
                lel REAL,
                smoke REAL,
                water REAL
            )
        """)

        # 조회 성능을 위한 복합 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_query
            ON sensor_data(sid, peer_ip, date, timestamp)
        """)
        
        # 기존 테이블에 새로운 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE sensor_data ADD COLUMN lel REAL")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우
            
        try:
            cursor.execute("ALTER TABLE sensor_data ADD COLUMN smoke REAL")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우
            
        try:
            cursor.execute("ALTER TABLE sensor_data ADD COLUMN water REAL")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우

        # 센서별 빠른 조회를 위한 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date_sid
            ON sensor_data(date, sid, peer_ip)
        """)

        # 경보 이벤트 테이블 (영구 저장)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                date TEXT NOT NULL,
                sid TEXT NOT NULL,
                peer_ip TEXT NOT NULL,
                sensor_key TEXT NOT NULL,
                level INTEGER NOT NULL,
                value REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_date_sid
            ON alert_events(date, sid, peer_ip)
        """)

        conn.commit()
        conn.close()

    def _get_db_connection(self):
        """SQLite 연결 가져오기 (일별 회전)"""
        tag = now_local().strftime("%Y%m%d")
        if self._db_conn is None or self._db_tag != tag:
            if self._db_conn:
                try:
                    self._db_conn.close()
                except:
                    pass
            # WAL 모드로 성능 향상
            self._db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA synchronous=NORMAL")
            self._db_tag = tag
        return self._db_conn

    def _migrate_old_logs(self):
        """기존 로그 파일을 적절한 하위 폴더로 이동"""
        import shutil

        try:
            # logs 폴더 내의 모든 파일 확인
            for filename in os.listdir(self.base):
                filepath = os.path.join(self.base, filename)

                # 디렉토리는 건너뛰기
                if os.path.isdir(filepath):
                    continue

                # run_ 로그 파일 이동
                if filename.startswith("run_") and filename.endswith(".log"):
                    dest = os.path.join(self.run_dir, filename)
                    if not os.path.exists(dest):
                        shutil.move(filepath, dest)

                # data_ 로그 파일 이동
                elif filename.startswith("data_") and filename.endswith(".log"):
                    dest = os.path.join(self.data_dir, filename)
                    if not os.path.exists(dest):
                        shutil.move(filepath, dest)
        except Exception as e:
            # 마이그레이션 실패 시 조용히 무시 (기존 파일이 남아있어도 문제없음)
            pass

    def _rotate_run(self):
        """실행 로그 파일 로테이션 (일별)"""
        tag = now_local().strftime("%Y%m%d")
        if self._run_tag != tag or self._run_fp is None:
            if self._run_fp:
                try:
                    self._run_fp.close()
                except:
                    pass
            path = os.path.join(self.run_dir, f"run_{tag}.log")
            self._run_fp = open(path, "a", encoding="utf-8", buffering=1)
            self._run_tag = tag

    def _rotate_data(self):
        """데이터 로그 파일 로테이션 (일별)"""
        tag = now_local().strftime("%Y%m%d")
        if self._data_tag != tag or self._data_fp is None:
            if self._data_fp:
                try:
                    self._data_fp.close()
                except:
                    pass
            path = os.path.join(self.data_dir, f"data_{tag}.log")
            self._data_fp = open(path, "a", encoding="utf-8", buffering=1)
            self._data_tag = tag

    def _rotate_warning(self):
        """경고 로그 파일 로테이션 (일별)"""
        tag = now_local().strftime("%Y%m%d")
        if self._warning_tag != tag or self._warning_fp is None:
            if self._warning_fp:
                try:
                    self._warning_fp.close()
                except:
                    pass
            path = os.path.join(self.warning_dir, f"warning_{tag}.log")
            self._warning_fp = open(path, "a", encoding="utf-8", buffering=1)
            self._warning_tag = tag

    def write_run(self, text):
        """실행 로그 작성"""
        self._rotate_run()
        ts = fmt_ts()
        self._run_fp.write(f"{ts} | {self.srv} | {text}\n")

    def write_warning(self, sid, peer, sensor_key, value, threshold_info):
        """경고 로그 작성 (임계값 초과 시)"""
        self._rotate_warning()
        ts = fmt_ts()
        self._warning_fp.write(f"{ts} | {self.srv} | {peer} | {sid} | {sensor_key} | 값: {value} | {threshold_info}\n")

    def on_data(self, sid, peer, data):
        """센서 데이터 수신 시 호출 - SQLite와 텍스트 로그에 기록"""
        # 텍스트 로그 (백업용)
        self._rotate_data()
        ts_str = fmt_ts()

        try:
            s = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            s = str(data)

        # 텍스트 로그에 기록
        self._data_fp.write(f"{ts_str} | {self.srv} | {peer} | {sid} | {s}\n")

        # SQLite에 저장 (주 저장소)
        self._save_to_database(sid, peer, data)

        # 임계값 초과 검사 및 경고 로그 작성
        if self.config:
            self._check_and_log_warnings(sid, peer, data)

    def write_alert_event(self, sid, peer, sensor_key, level, value, ts=None):
        """경보 이벤트를 SQLite alert_events 테이블에 기록"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            peer_ip = peer.split(":")[0] if peer else ""
            timestamp = ts if isinstance(ts, (int, float)) else time.time()
            date = now_local().strftime("%Y%m%d")

            cursor.execute(
                """
                INSERT INTO alert_events (timestamp, date, sid, peer_ip, sensor_key, level, value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, date, sid, peer_ip, sensor_key, int(level), value)
            )
            conn.commit()
        except Exception:
            pass

    def get_today_alerts_for(self, sid, peer):
        """오늘의 경보 이벤트 목록 반환 (최신순)"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            peer_ip = peer.split(":")[0] if peer else ""
            date = now_local().strftime("%Y%m%d")

            cursor.execute(
                """
                SELECT timestamp, sensor_key, level, value
                FROM alert_events
                WHERE date = ? AND sid = ? AND peer_ip = ?
                ORDER BY timestamp DESC
                """,
                (date, sid, peer_ip)
            )
            rows = cursor.fetchall()
            return [
                {"ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r[0])),
                 "sid": sid, "key": r[1], "level": r[2], "value": r[3]} for r in rows
            ]
        except Exception:
            return []

    def delete_today_alerts_for(self, sid, peer):
        """해당 패널의 오늘 경보 이벤트를 모두 삭제"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            peer_ip = peer.split(":")[0] if peer else ""
            date = now_local().strftime("%Y%m%d")

            cursor.execute(
                """
                DELETE FROM alert_events
                WHERE date = ? AND sid = ? AND peer_ip = ?
                """,
                (date, sid, peer_ip)
            )
            conn.commit()
            return True
        except Exception:
            return False

    def _save_to_database(self, sid, peer, data):
        """SQLite 데이터베이스에 센서 데이터 저장"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # peer에서 IP만 추출
            peer_ip = peer.split(":")[0] if peer else ""
            timestamp = time.time()
            date = now_local().strftime("%Y%m%d")

            cursor.execute("""
                INSERT INTO sensor_data
                (timestamp, date, sid, peer_ip, co2, h2s, co, o2, temperature, humidity, lel, smoke, water)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                date,
                sid,
                peer_ip,
                data.get("co2"),
                data.get("h2s"),
                data.get("co"),
                data.get("o2"),
                data.get("temperature"),
                data.get("humidity"),
                data.get("lel"),
                data.get("smoke"),
                data.get("water")
            ))

            conn.commit()
        except Exception as e:
            # SQLite 오류 시 조용히 무시 (텍스트 로그는 이미 저장됨)
            pass

    def _check_and_log_warnings(self, sid, peer, data):
        """임계값 초과 검사 및 경고 로그 작성"""
        from ..utils.helpers import SENSOR_KEYS

        for key in SENSOR_KEYS:
            value = data.get(key)
            if value is None:
                continue

            try:
                fv = float(value)
            except:
                continue

            # 임계값 검사
            ok = self._check_threshold(key, fv)
            if not ok:
                # 임계값 초과 시 경고 로그 작성
                threshold_info = self._get_threshold_info(key, fv)
                self.write_warning(sid, peer, key, fv, threshold_info)

    def _check_threshold(self, key, value):
        """5단계 경보 시스템 임계값 체크"""
        try:
            x = float(value)
        except:
            return True

        s = self.config.std

        if key == "o2":
            # 산소: 정상 범위 체크
            return s.get("o2_normal_min", 19.5) <= x <= s.get("o2_normal_max", 23.0)
        elif key == "h2s":
            # 황화수소: 정상 최대값 체크
            return x <= s.get("h2s_normal_max", 5)
        elif key == "co":
            # 일산화탄소: 정상 최대값 체크
            return x <= s.get("co_normal_max", 9)
        elif key == "co2":
            # 이산화탄소: 정상 최대값 체크
            return x <= s.get("co2_normal_max", 1000)
        elif key == "temperature":
            # 온도: 정상 범위 체크
            return s.get("temp_normal_min", 18) <= x <= s.get("temp_normal_max", 28)
        elif key == "humidity":
            # 습도: 정상 범위 체크
            return s.get("hum_normal_min", 40) <= x <= s.get("hum_normal_max", 60)
        elif key == "lel":
            # 가연성가스: 정상 최대값 체크
            return x <= s.get("lel_normal_max", 10)
        elif key == "smoke":
            # 연기: 정상 최대값 체크
            return x <= s.get("smoke_normal_max", 0)
        elif key == "water":
            # 누수: 정상 상태 체크 (0이 정상)
            return x == 0

        return True

    def _get_threshold_info(self, key, value):
        """5단계 경보 시스템 임계값 정보 반환"""
        s = self.config.std

        if key == "o2":
            return f"정상 범위: {s.get('o2_normal_min', 19.5):.1f}~{s.get('o2_normal_max', 23.0):.1f}% (현재: {value:.1f}%)"
        elif key == "h2s":
            return f"정상 최대: ≤ {s.get('h2s_normal_max', 5):.1f} ppm (현재: {value:.1f} ppm)"
        elif key == "co":
            return f"정상 최대: ≤ {s.get('co_normal_max', 9):.1f} ppm (현재: {value:.1f} ppm)"
        elif key == "co2":
            return f"정상 최대: ≤ {s.get('co2_normal_max', 1000):.0f} ppm (현재: {value:.0f} ppm)"
        elif key == "temperature":
            return f"정상 범위: {s.get('temp_normal_min', 18):.0f}~{s.get('temp_normal_max', 28):.0f}℃ (현재: {value:.1f}℃)"
        elif key == "humidity":
            return f"정상 범위: {s.get('hum_normal_min', 40):.0f}~{s.get('hum_normal_max', 60):.0f}% (현재: {value:.1f}%)"
        elif key == "lel":
            return f"정상 최대: ≤ {s.get('lel_normal_max', 10):.1f}% (현재: {value:.1f}%)"
        elif key == "smoke":
            return f"정상 최대: ≤ {s.get('smoke_normal_max', 0):.1f} ppm (현재: {value:.1f} ppm)"
        elif key == "water":
            return f"정상 상태: 정상 (현재: {'정상' if value == 0 else '누수감지'})"

        return f"임계값 초과 (현재: {value})"

    def get_today_stats(self, sid, peer, sensor_key):
        """오늘의 센서 데이터 통계 계산 (SQLite에서)

        Returns:
            dict: {"min": float, "max": float, "avg": float, "count": int} 또는 None
        """
        # 캐시 키 생성
        peer_ip = peer.split(":")[0] if peer else ""
        cache_key = f"{sid}|{peer_ip}|{sensor_key}"

        # 캐시 확인
        current_time = time.time()
        if cache_key in self._stats_cache:
            cache_time = self._stats_cache_time.get(cache_key, 0)
            if current_time - cache_time < self._cache_ttl:
                return self._stats_cache[cache_key]

        # SQLite에서 통계 계산 (훨씬 빠름)
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            date = now_local().strftime("%Y%m%d")

            # 유효한 값 필터링 조건
            if sensor_key == "temperature":
                filter_condition = f"AND {sensor_key} IS NOT NULL AND {sensor_key} != -1 AND {sensor_key} BETWEEN -50 AND 50"
            else:
                filter_condition = f"AND {sensor_key} IS NOT NULL AND {sensor_key} != -1 AND {sensor_key} >= 0"

            query = f"""
                SELECT
                    MIN({sensor_key}) as min_val,
                    MAX({sensor_key}) as max_val,
                    AVG({sensor_key}) as avg_val,
                    COUNT({sensor_key}) as count_val
                FROM sensor_data
                WHERE date = ? AND sid = ? AND peer_ip = ?
                {filter_condition}
            """

            cursor.execute(query, (date, sid, peer_ip))
            row = cursor.fetchone()

            if row and row[3] > 0:  # count > 0
                result = {
                    "min": row[0],
                    "max": row[1],
                    "avg": row[2],
                    "count": row[3]
                }
            else:
                result = None

        except Exception:
            result = None

        # 캐시 저장
        self._stats_cache[cache_key] = result
        self._stats_cache_time[cache_key] = current_time

        return result

    def get_sensor_data_for_hours(self, sid, peer, sensor_key, hours):
        """지정된 시간 동안의 센서 데이터 반환 (timestamp, value) 튜플 리스트 - SQLite에서

        Args:
            sid: 센서 ID
            peer: 피어 주소
            sensor_key: 센서 키 (co2, temperature 등)
            hours: 최근 몇 시간

        Returns:
            list: [(timestamp, value), ...] 튜플 리스트
        """
        # 캐시 키 생성
        peer_ip = peer.split(":")[0] if peer else ""
        cache_key = f"{sid}|{peer_ip}|{sensor_key}|{hours}"

        # 캐시 확인
        current_time = time.time()
        if cache_key in self._data_cache:
            cache_time = self._data_cache_time.get(cache_key, 0)
            if current_time - cache_time < self._data_cache_ttl:
                return self._data_cache[cache_key]

        # SQLite에서 데이터 조회 (훨씬 빠름)
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cutoff_time = current_time - (hours * 3600)

            # 유효한 값 필터링 조건
            if sensor_key == "temperature":
                filter_condition = f"AND {sensor_key} IS NOT NULL AND {sensor_key} != -1 AND {sensor_key} BETWEEN -50 AND 50"
            else:
                filter_condition = f"AND {sensor_key} IS NOT NULL AND {sensor_key} != -1 AND {sensor_key} >= 0"

            query = f"""
                SELECT timestamp, {sensor_key}
                FROM sensor_data
                WHERE sid = ? AND peer_ip = ? AND timestamp >= ?
                {filter_condition}
                ORDER BY timestamp ASC
            """

            cursor.execute(query, (sid, peer_ip, cutoff_time))
            result = cursor.fetchall()

        except Exception:
            result = []

        # 캐시 저장
        self._data_cache[cache_key] = result
        self._data_cache_time[cache_key] = current_time

        return result

    def get_sensor_history_hours(self, sid, peer, hours):
        """지정된 시간 동안의 모든 센서 데이터 반환 - SQLite에서

        Args:
            sid: 센서 ID
            peer: 피어 주소
            hours: 최근 몇 시간

        Returns:
            list: [{"timestamp": datetime, "co2": float, "h2s": float, ...}, ...] 딕셔너리 리스트
        """
        from datetime import datetime

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            peer_ip = peer.split(":")[0] if peer else ""
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)

            query = """
                SELECT timestamp, co2, h2s, co, o2, temperature, humidity
                FROM sensor_data
                WHERE sid = ? AND peer_ip = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """

            cursor.execute(query, (sid, peer_ip, cutoff_time))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                entry = {
                    "timestamp": datetime.fromtimestamp(row[0]),
                    "co2": row[1],
                    "h2s": row[2],
                    "co": row[3],
                    "o2": row[4],
                    "temperature": row[5],
                    "humidity": row[6]
                }
                result.append(entry)

            return result

        except Exception:
            return []
