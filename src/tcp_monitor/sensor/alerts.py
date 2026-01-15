"""
센서 알림 관리

센서 값 임계치 검사 및 알림 처리
"""

import threading
import os
import tempfile
from pathlib import Path

try:
    import winsound  # Windows 내장
    WINSOUND_OK = True
except Exception:
    WINSOUND_OK = False

# Python 3.13에서 audioop 모듈 제거로 pydub 사용 불가
# gTTS만 사용하고, 재생은 시스템 명령어로 처리
try:
    from gtts import gTTS
    TTS_OK = True
    TTS_ENGINE = "gTTS"
except Exception as e:
    print(f"[TTS] gTTS 로드 실패: {e}")
    TTS_OK = False
    TTS_ENGINE = "None"

# 현재 재생 중인 프로세스 추적 (음성 중지용)
_current_audio_process = None
_audio_process_lock = threading.Lock()

def _stop_current_audio():
    """현재 재생 중인 오디오 중지"""
    global _current_audio_process
    with _audio_process_lock:
        if _current_audio_process is not None:
            try:
                _current_audio_process.terminate()
                _current_audio_process.wait(timeout=1)
                print("[TTS] 현재 재생 중인 오디오 중지됨")
            except Exception as e:
                print(f"[TTS] 오디오 중지 오류: {e}")
            _current_audio_process = None

# 오디오 재생 함수 (pydub 없이 직접 재생)
def _play_audio_file(file_path):
    """MP3 파일 재생 (시스템 명령어 사용)"""
    global _current_audio_process
    import subprocess
    import platform

    try:
        system = platform.system()

        if system == "Linux":
            # Linux: mpg123 또는 ffplay 사용 (Popen으로 프로세스 추적)
            try:
                with _audio_process_lock:
                    _current_audio_process = subprocess.Popen(
                        ["mpg123", "-q", str(file_path)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                _current_audio_process.wait(timeout=30)
                with _audio_process_lock:
                    _current_audio_process = None
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                with _audio_process_lock:
                    _current_audio_process = None
                pass

            try:
                with _audio_process_lock:
                    _current_audio_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)]
                    )
                _current_audio_process.wait(timeout=30)
                with _audio_process_lock:
                    _current_audio_process = None
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                with _audio_process_lock:
                    _current_audio_process = None
                pass

            # aplay는 wav만 지원하므로 mpv 시도
            try:
                with _audio_process_lock:
                    _current_audio_process = subprocess.Popen(
                        ["mpv", "--no-video", "--really-quiet", str(file_path)]
                    )
                _current_audio_process.wait(timeout=30)
                with _audio_process_lock:
                    _current_audio_process = None
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                with _audio_process_lock:
                    _current_audio_process = None
                pass

        elif system == "Darwin":  # macOS
            try:
                subprocess.run(["afplay", str(file_path)], check=True, timeout=30)
                return True
            except Exception:
                pass

        elif system == "Windows":
            try:
                # Windows Media Player를 통한 재생
                os.startfile(str(file_path))
                return True
            except Exception:
                pass

        return False
    except Exception as e:
        print(f"[TTS] 오디오 재생 오류: {e}")
        return False


class AlertManager:
    """센서 알림 관리자 - 5단계 경보 시스템"""

    def __init__(self, config):
        self.config = config
        self._last_alarm_state = {k: None for k in ["co2", "o2", "h2s", "co", "lel", "smoke", "temperature", "humidity", "water"]}
        self._tts_lock = threading.Lock() if TTS_OK else None
        self._tts_enabled = TTS_OK  # TTS 활성화 여부
        self._tts_cache_dir = Path(tempfile.gettempdir()) / "garame_tts_cache"

        # 음성 알림 큐 (순차적 재생용)
        import queue
        self._tts_queue = queue.Queue()
        self._tts_worker_running = False
        self._tts_worker_thread = None

        # TTS 캐시 디렉토리 생성
        if TTS_OK:
            try:
                self._tts_cache_dir.mkdir(parents=True, exist_ok=True)
                print(f"[TTS] gTTS 엔진 초기화 완료 (캐시: {self._tts_cache_dir})")
                # TTS 워커 스레드 시작
                self._start_tts_worker()
            except Exception as e:
                print(f"[TTS] 캐시 디렉토리 생성 실패: {e}")
        
        # 5단계 경보 색상 정의 (국가 기준)
        self.alert_colors = {
            1: "#2ECC71",  # 정상 - 녹색
            2: "#F1C40F",  # 관심 - 노랑
            3: "#E67E22",  # 주의 - 주황
            4: "#E74C3C",  # 경계 - 빨강
            5: "#C0392B"   # 심각 - 진홍
        }
        
        # 5단계 경보 메시지
        self.alert_messages = {
            1: "정상",
            2: "관심",
            3: "주의",
            4: "경계",
            5: "심각"
        }

    def get_alert_level(self, key, value):
        """5단계 경보 레벨 반환 (1:정상, 2:관심, 3:주의, 4:경계, 5:심각)"""
        try:
            x = float(value)
        except:
            return 1  # 기본값: 정상
            
        s = self.config.std
        e = self.config.env
        
        if key == "o2":
            # 산소: 범위 체크
            if s.get("o2_normal_min", 19.5) <= x <= s.get("o2_normal_max", 23.0):
                return 1  # 정상
            elif s.get("o2_concern_min", 19.0) <= x <= s.get("o2_concern_max", 23.0):
                return 2  # 관심
            elif s.get("o2_caution_min", 18.5) <= x <= s.get("o2_caution_max", 23.3):
                return 3  # 주의
            elif s.get("o2_warning_min", 18.0) <= x <= s.get("o2_warning_max", 23.5):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "co2":
            # 이산화탄소: 상한값 체크
            if x <= s.get("co2_normal_max", 1000):
                return 1  # 정상
            elif x <= s.get("co2_concern_max", 5000):
                return 2  # 관심
            elif x <= s.get("co2_caution_max", 10000):
                return 3  # 주의
            elif x <= s.get("co2_warning_max", 15000):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "co":
            # 일산화탄소: 상한값 체크
            if x <= s.get("co_normal_max", 9):
                return 1  # 정상
            elif x <= s.get("co_concern_max", 25):
                return 2  # 관심
            elif x <= s.get("co_caution_max", 30):
                return 3  # 주의
            elif x <= s.get("co_warning_max", 50):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "h2s":
            # 황화수소: 상한값 체크
            if x <= s.get("h2s_normal_max", 5):
                return 1  # 정상
            elif x <= s.get("h2s_concern_max", 8):
                return 2  # 관심
            elif x <= s.get("h2s_caution_max", 10):
                return 3  # 주의
            elif x <= s.get("h2s_warning_max", 15):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "temperature":
            # 온도: 범위 체크
            if s.get("temp_normal_min", 18) <= x <= s.get("temp_normal_max", 28):
                return 1  # 정상
            elif s.get("temp_concern_min", 16) <= x <= s.get("temp_concern_max", 30):
                return 2  # 관심
            elif s.get("temp_caution_min", 14) <= x <= s.get("temp_caution_max", 32):
                return 3  # 주의
            elif s.get("temp_warning_min", 12) <= x <= s.get("temp_warning_max", 33):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "humidity":
            # 습도: 범위 체크
            if s.get("hum_normal_min", 40) <= x <= s.get("hum_normal_max", 60):
                return 1  # 정상
            elif s.get("hum_concern_min", 30) <= x <= s.get("hum_concern_max", 70):
                return 2  # 관심
            elif s.get("hum_caution_min", 20) <= x <= s.get("hum_caution_max", 80):
                return 3  # 주의
            elif s.get("hum_warning_min", 20) <= x <= s.get("hum_warning_max", 80):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "lel":
            # 가연성가스: 상한값 체크
            if x <= s.get("lel_normal_max", 10):
                return 1  # 정상
            elif x <= s.get("lel_concern_max", 20):
                return 2  # 관심
            elif x <= s.get("lel_caution_max", 50):
                return 3  # 주의
            elif x <= s.get("lel_warning_max", 50):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "smoke":
            # 연기: 상한값 체크
            if x <= s.get("smoke_normal_max", 0):
                return 1  # 정상
            elif x <= s.get("smoke_concern_max", 10):
                return 2  # 관심
            elif x <= s.get("smoke_caution_max", 25):
                return 3  # 주의
            elif x <= s.get("smoke_warning_max", 50):
                return 4  # 경계
            else:
                return 5  # 심각
                
        elif key == "water":
            # 누수: 0이면 정상, 1이면 심각
            return 1 if x == 0 else 5
        
        return 1  # 기본값: 정상

    def check_threshold(self, key, value):
        """임계치 검사 (5단계 시스템 호환)"""
        alert_level = self.get_alert_level(key, value)
        return alert_level <= 2  # 정상(1) 또는 관심(2)이면 True, 주의(3) 이상이면 False

    def refresh_thresholds(self):
        """경보 임계값 실시간 새로고침"""
        try:
            # 설정 파일에서 최신 임계값 다시 로드 (load 사용)
            if hasattr(self.config, 'load'):
                self.config.load()
            print("경보 임계값이 새로고침되었습니다.")
        except Exception as e:
            print(f"경보 임계값 새로고침 오류: {e}")

    def check_alarm_state_change(self, key, is_alarm):
        """알림 상태 변화 확인"""
        prev = self._last_alarm_state.get(key)
        cur = is_alarm
        self._last_alarm_state[key] = cur
        
        # 알림 상태로 변경된 경우
        if cur and (prev is False or prev is None):
            return True
        return False

    def _start_tts_worker(self):
        """TTS 워커 스레드 시작 (순차적 음성 재생)"""
        if self._tts_worker_running:
            return

        self._tts_worker_running = True

        def worker():
            while self._tts_worker_running:
                try:
                    # 큐에서 메시지 가져오기 (타임아웃 1초)
                    message = self._tts_queue.get(timeout=1.0)
                    if message is None:
                        continue

                    # 음성이 비활성화되었으면 재생하지 않고 스킵
                    if not self._tts_enabled:
                        print(f"[TTS] 음성 비활성화됨 - 메시지 스킵: {message[:20]}...")
                        self._tts_queue.task_done()
                        continue

                    # 음성 파일 생성 및 재생
                    self._generate_and_play_tts(message)
                    self._tts_queue.task_done()
                except Exception:
                    # 타임아웃 또는 기타 오류 - 계속 대기
                    pass

        self._tts_worker_thread = threading.Thread(target=worker, daemon=True, name="TTS-Worker")
        self._tts_worker_thread.start()
        print("[TTS] 워커 스레드 시작 (순차적 음성 재생 활성화)")

    def _generate_and_play_tts(self, message):
        """TTS 음성 생성 및 재생 (동기식)"""
        try:
            import hashlib

            # 캐시 파일 경로 생성 (메시지 해시 기반)
            message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
            cache_file = self._tts_cache_dir / f"tts_{message_hash}.mp3"

            # 캐시 확인 및 생성
            if not cache_file.exists():
                print(f"[TTS] 새 음성 파일 생성 중: {cache_file.name}")
                try:
                    tts = gTTS(text=message, lang='ko', slow=False)
                    tts.save(str(cache_file))
                    print(f"[TTS] 음성 파일 생성 완료")
                except Exception as e:
                    print(f"[TTS] 음성 파일 생성 실패: {e}")
                    return
            else:
                print(f"[TTS] 캐시된 음성 파일 사용: {cache_file.name}")

            # 오디오 재생 (동기식 - 완료될 때까지 대기)
            if _play_audio_file(str(cache_file)):
                print(f"[TTS] 음성 재생 완료: {message[:30]}...")
            else:
                print(f"[TTS] 음성 재생 실패 - mpg123, ffplay, 또는 mpv를 설치하세요")
        except Exception as e:
            print(f"[TTS] 음성 생성/재생 오류: {e}")

    def disable_tts(self):
        """TTS 비활성화"""
        self._tts_enabled = False

    def enable_tts(self):
        """TTS 활성화"""
        self._tts_enabled = TTS_OK

    def speak_alert(self, key, value=None, voice_enabled=True):
        """음성 알림 (gTTS 기반 - 순차적 재생)"""
        print(f"[TTS] 경보음성 호출: key={key}, value={value}, voice_enabled={voice_enabled}, engine={TTS_ENGINE}")

        if not voice_enabled:
            print("[TTS] 음성 경보가 비활성화되어 있습니다.")
            return

        if WINSOUND_OK:
            try:
                # 더 명확한 경고음
                winsound.Beep(1000, 500)
                winsound.Beep(1500, 300)
                winsound.Beep(2000, 200)
                print(f"[BEEP] 경고음 재생 완료: {key} = {value}")
            except Exception as e:
                print(f"[BEEP] 경고음 재생 실패: {e}")

        if self._tts_enabled and TTS_OK:
            try:
                # 메시지 생성
                msg_map = {
                    "co2": "이산화탄소", "o2": "산소", "h2s": "황화수소",
                    "co": "일산화탄소", "lel": "가연성가스", "smoke": "연기",
                    "temperature": "온도", "humidity": "습도", "water": "누수"
                }
                label = msg_map.get(key, key)

                # 5단계 경보 레벨에 따른 메시지
                if value is not None:
                    try:
                        val = float(value)
                        alert_level = self.get_alert_level(key, val)
                        alert_msg = self.alert_messages[alert_level]

                        if key == "water":
                            if alert_level == 5:
                                message = "누수가 감지되었습니다. 즉시 확인하세요."
                            else:
                                message = f"{label} 상태가 {alert_msg} 단계입니다."
                        else:
                            # 소수점 처리
                            if key in ("o2", "temperature", "humidity"):
                                val_str = f"{val:.1f}"
                            else:
                                val_str = f"{val:.0f}"

                            if alert_level == 5:
                                message = f"{label} 현재값 {val_str} 입니다. 심각한 위험 상태입니다. 즉시 대피하세요."
                            elif alert_level == 4:
                                message = f"{label} 현재값 {val_str} 입니다. 경계 단계입니다. 즉각 조치가 필요합니다."
                            elif alert_level == 3:
                                message = f"{label} 현재값 {val_str} 입니다. 주의 단계입니다."
                            else:
                                message = f"{label} 현재값 {val_str} 입니다. {alert_msg} 상태입니다."
                    except:
                        if key == "water":
                            message = "누수가 감지되었습니다. 즉시 확인하세요."
                        else:
                            message = f"{label} 현재값 확인이 필요합니다."
                else:
                    if key == "water":
                        message = "누수가 감지되었습니다. 즉시 확인하세요."
                    else:
                        message = f"{label} 현재값 확인이 필요합니다."

                print(f"[TTS] 큐에 메시지 추가: {message}")

                # 큐에 메시지 추가 (워커 스레드에서 순차적으로 재생)
                try:
                    self._tts_queue.put_nowait(message)
                except Exception as e:
                    print(f"[TTS] 큐 추가 실패: {e}")

            except Exception as e:
                print(f"[TTS] speak_alert 오류: {e}")
