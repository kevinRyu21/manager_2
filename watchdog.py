#!/usr/bin/env python3
"""
GARAMe MANAGER Watchdog
프로그램을 감시하고 비정상 종료 시 자동 재시작하는 와치독 프로그램
Ubuntu Linux 전용 (Windows 지원 안 함)
"""

import os
import sys
import platform
import time
import subprocess
import logging
import signal
import threading
import configparser
from datetime import datetime
from pathlib import Path

# Linux 전용 체크
if platform.system() != "Linux":
    print("ERROR: 이 프로그램은 Ubuntu Linux에서만 실행됩니다.")
    print(f"현재 시스템: {platform.system()}")
    sys.exit(1)

class GARAMeManagerWatchdog:
    def __init__(self, program_dir=None):
        self.program_dir = Path(program_dir) if program_dir else Path(__file__).parent
        self.log_file = self.program_dir / "watchdog.log"
        self.config_file = self.program_dir / "config.conf"
        
        # 설정 파일 로드
        self.load_config()
        
        self.restart_count = 0
        self.running = True
        self.start_time = datetime.now()
        
        # 정상 종료 플래그 (정상 종료로 감지되면 재시작하지 않음)
        self._normal_exit_detected = False
        
        # GUI 참조 (매니저 실행 시 트레이로 숨기기 위해)
        self.gui_reference = None
        
        # 하트비트 스레드 참조
        self._heartbeat_thread = None
        self._heartbeat_running = True
        
        # 로깅 설정
        self.setup_logging()
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def load_config(self):
        """설정 파일 로드"""
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file, encoding='utf-8')
        
        # 와치독 설정 로드
        if 'WATCHDOG' in self.config:
            self.max_restart_count = self.config.getint('WATCHDOG', 'max_restart_count', fallback=10)
            self.restart_delay = self.config.getint('WATCHDOG', 'restart_delay', fallback=5)
            self.health_timeout = self.config.getint('WATCHDOG', 'health_timeout', fallback=90)
            self.health_check_interval = self.config.getint('WATCHDOG', 'health_check_interval', fallback=30)
        else:
            self.max_restart_count = 10
            self.restart_delay = 5
            self.health_timeout = 90
            self.health_check_interval = 30
            
    def save_config(self):
        """설정 파일 저장"""
        if 'WATCHDOG' not in self.config:
            self.config.add_section('WATCHDOG')
            
        self.config.set('WATCHDOG', 'max_restart_count', str(self.max_restart_count))
        self.config.set('WATCHDOG', 'restart_delay', str(self.restart_delay))
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        # 하트비트 파일 경로 설정
        self.watchdog_hb = self.program_dir / "watchdog_heartbeat.signal"
        self.manager_hb = self.program_dir / "manager_heartbeat.signal"

    def _heartbeat_loop(self):
        """와치독 하트비트 파일 주기적 갱신"""
        while self._heartbeat_running and self.running:
            try:
                with open(self.watchdog_hb, 'w', encoding='utf-8') as f:
                    f.write(str(int(time.time())))
            except Exception:
                pass
            time.sleep(self.health_check_interval)

    def _start_heartbeat(self):
        try:
            self._heartbeat_running = True
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
        except Exception:
            pass
        
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        self.logger.info(f"시그널 {signum} 수신. 와치독을 종료합니다.")
        self.running = False
        
    def log(self, message):
        """로그 메시지 출력"""
        self.logger.info(message)
        
    def find_program(self):
        """실행할 프로그램 찾기 (Linux 전용)"""
        py_file = self.program_dir / "main.py"
        
        if py_file.exists():
            return str(py_file), "python"
        else:
            return None, None
            
    def run_program(self):
        """프로그램 실행 (Linux 전용)"""
        program_path, program_type = self.find_program()
        
        if not program_path:
            self.log("오류: main.py 파일을 찾을 수 없습니다.")
            return -1

    def start_program_nonblocking(self):
        """프로그램을 백그라운드로 시작 (대기하지 않음, Linux 전용)"""
        program_path, program_type = self.find_program()
        if not program_path:
            self.log("오류: main.py 파일을 찾을 수 없습니다.")
            return None
        try:
            # Linux에서는 Python 스크립트만 실행
            proc = subprocess.Popen(
                [sys.executable, program_path, "--config", "config.conf"],
                cwd=str(self.program_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # 새 세션에서 실행하여 부모 프로세스 종료와 독립
            )
            self.log(f"프로그램을 백그라운드로 시작했습니다: {program_path} (PID: {proc.pid})")
            return proc
        except Exception as e:
            self.log(f"프로그램 시작 실패: {e}")
            return None
            
        self.log(f"프로그램 실행: {program_path}")
        
        try:
            # Linux에서는 Python 스크립트만 실행
            process = subprocess.Popen(
                [sys.executable, program_path, "--config", "config.conf"],
                cwd=str(self.program_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 프로세스 완료 대기
            exit_code = process.wait()
            self.log(f"프로그램 종료: 종료 코드 {exit_code}")
            
            # 정상 종료 신호 확인
            if self.check_normal_exit_signal():
                self.log("정상 종료 신호가 감지되었습니다.")
                return 0  # 정상 종료로 처리
            else:
                self.log("정상 종료 신호가 없습니다. 비정상 종료로 판단합니다.")
                return exit_code
            
        except Exception as e:
            self.log(f"프로그램 실행 중 오류 발생: {e}")
            return -1
            
    def check_normal_exit_signal(self):
        """정상 종료 신호 확인 (여러 번 시도하여 파일이 완전히 쓰여질 때까지 대기)"""
        signal_file = self.program_dir / "normal_exit.signal"

        # 파일이 완전히 쓰여질 때까지 최대 10번, 0.2초 간격으로 확인 (총 2초)
        for attempt in range(10):
            if signal_file.exists():
                try:
                    # 파일이 완전히 쓰여졌는지 확인 (파일 크기 확인)
                    file_size = signal_file.stat().st_size
                    if file_size > 0:
                        # 신호 파일 읽기
                        with open(signal_file, 'r', encoding='utf-8') as f:
                            signal_content = f.read().strip()

                        # 신호 파일 삭제
                        signal_file.unlink()

                        # 정상 종료 신호인지 확인
                        if signal_content.startswith("normal_exit_"):
                            self.log(f"정상 종료 신호를 감지했습니다. (시도 {attempt + 1}/10)")
                            return True
                        else:
                            self.log(f"정상 종료 신호 파일 내용이 올바르지 않습니다: {signal_content}")
                            return False
                except Exception as e:
                    # 파일이 아직 완전히 쓰여지지 않았을 수 있음
                    if attempt < 9:  # 마지막 시도가 아니면 대기
                        time.sleep(0.2)
                        continue
                    else:
                        self.log(f"정상 종료 신호 확인 중 오류: {e}")
            else:
                # 파일이 아직 생성되지 않았을 수 있음
                if attempt < 9:  # 마지막 시도가 아니면 대기
                    time.sleep(0.2)
                    continue

        return False

    def check_watchdog_exit_signal(self):
        """와치독 종료 신호 확인"""
        exit_file = self.program_dir / "watchdog_exit.signal"
        if exit_file.exists():
            try:
                # 신호 파일 읽기
                with open(exit_file, 'r', encoding='utf-8') as f:
                    signal_content = f.read().strip()

                # 신호 파일 삭제
                exit_file.unlink()

                # 와치독 종료 신호인지 확인
                if signal_content.startswith("watchdog_exit_"):
                    self.log("와치독 종료 신호를 감지했습니다.")
                    return True
            except Exception as e:
                self.log(f"와치독 종료 신호 확인 중 오류: {e}")

        return False
    
    def check_restart_signal(self):
        """재시작 신호 확인"""
        restart_file = self.program_dir / "restart.signal"
        if restart_file.exists():
            try:
                # 신호 파일 읽기
                with open(restart_file, 'r', encoding='utf-8') as f:
                    signal_content = f.read().strip()
                
                # 신호 파일 삭제
                restart_file.unlink()
                
                # 재시작 신호인지 확인
                if signal_content.startswith("restart_"):
                    self.log("재시작 신호를 감지했습니다.")
                    return True
            except Exception as e:
                self.log(f"재시작 신호 확인 중 오류: {e}")
        
        return False
            
    def is_manager_running(self):
        """매니저 프로그램 실행 상태 확인 (Linux 전용)"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or proc.cmdline()
                    if cmdline and any('main.py' in str(c) for c in cmdline):
                        # main.py가 실행 중인지 확인
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            return False
        except ImportError:
            # psutil이 없으면 ps 명령어 사용 (Linux)
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                return 'main.py' in result.stdout
            except:
                return False
            
    def start_watchdog(self):
        """와치독 시작"""
        self.log("=== GARAMe MANAGER 와치독 시작 ===")

        # PID 파일 생성
        try:
            pid_file = self.program_dir / "watchdog.pid"
            with open(pid_file, 'w', encoding='utf-8') as f:
                f.write(str(os.getpid()))
            self.log(f"와치독 PID 파일 생성: {pid_file} (PID: {os.getpid()})")
        except Exception as e:
            self.log(f"PID 파일 생성 실패: {e}")

        # 하트비트 시작
        self._start_heartbeat()
        
        # 매니저 프로그램이 없으면 대기
        # run.sh에서 watchdog를 먼저 실행하고 main.py를 나중에 실행하므로
        # 잠시 대기 후 프로그램이 시작되는지 확인
        if not self.is_manager_running():
            self.log("매니저 프로그램 실행을 기다리는 중... (최대 30초)")
            # run.sh에서 실행될 때까지 최대 30초 대기
            waited = 0
            while self.running and not self.is_manager_running() and waited < 30:
                time.sleep(1)
                waited += 1
            if waited >= 30 and not self.is_manager_running():
                self.log("매니저 프로그램이 30초 내에 시작되지 않았습니다. 계속 감시합니다...")
        
        # 프로그램이 실행될 때까지 대기
        while self.running and not self.is_manager_running():
            time.sleep(1)
        
        if not self.running:
            return
            
        self.log("매니저 프로그램이 실행되었습니다. 감시를 시작합니다.")
        
        # 매니저 프로그램이 다시 실행되면 정상 종료 플래그 리셋
        self._normal_exit_detected = False
        
        # 매니저 프로그램이 실행되면 와치독 창을 뒤로 보내기 (항상 화면에 표시)
        if self.gui_reference is not None:
            try:
                # 와치독 창을 뒤로 보내기 (매니저가 최우선 포커스를 받도록)
                self.gui_reference.root.after(0, lambda: self.gui_reference.root.lower())
                self.log("매니저 프로그램이 실행되어 와치독 창을 뒤로 보냈습니다.")
            except Exception as e:
                self.log(f"와치독 창 뒤로 보내기 실패: {e}")
        
        while self.running:
            # 와치독 종료 신호 확인 (최우선)
            if self.check_watchdog_exit_signal():
                self.log("와치독 종료 신호가 감지되었습니다. 와치독을 종료합니다.")
                self.running = False
                break

            # 정상 종료가 감지되었고 재시작 신호가 없으면 계속 대기
            if self._normal_exit_detected:
                # 재시작 신호 확인
                if self.check_restart_signal():
                    self.log("재시작 신호가 감지되었습니다. 정상 종료 플래그를 리셋하고 재시작합니다.")
                    self._normal_exit_detected = False
                    self.restart_count = 0
                    for i in range(self.restart_delay):
                        if not self.running:
                            break
                        time.sleep(1)
                    if self.running:
                        self.start_program_nonblocking()
                        time.sleep(1)
                else:
                    # 재시작 신호가 없으면 계속 대기
                    time.sleep(1)
                    continue

            # 매니저 프로그램 실행 상태 확인
            if not self.is_manager_running():
                # 정상 종료 플래그가 설정된 상태면 로그를 찍지 않고 대기
                if self._normal_exit_detected:
                    time.sleep(2)  # 정상 종료 후 안정화 대기
                    continue

                self.log("매니저 프로그램이 종료되었습니다.")

                # 정상 종료 신호 확인 (먼저 확인 - 재시작 신호보다 우선)
                # 파일이 완전히 쓰여질 시간을 주기 위해 지연 후 확인
                time.sleep(2.0)  # 1초 -> 2초로 증가
                if self.check_normal_exit_signal():
                    self.log("정상 종료로 감지되었습니다. 재시작 없이 대기합니다.")
                    self._normal_exit_detected = True  # 정상 종료 플래그 설정
                    # 프로세스 완전 종료 대기 (중복 감지 방지)
                    time.sleep(3)
                    # 정상 종료 시에는 자동 재시작하지 않음. 재시작 신호를 기다린다.
                    continue  # 다음 루프로

                # 재시작 신호 확인
                if self.check_restart_signal():
                    self.log("재시작 신호가 감지되었습니다. 프로그램을 재시작합니다.")
                    self.restart_count = 0  # 재시작 신호는 재시작 카운트 리셋
                    self._normal_exit_detected = False  # 플래그 리셋
                    for i in range(self.restart_delay):
                        if not self.running:
                            break
                        time.sleep(1)
                    if self.running:
                        self.start_program_nonblocking()
                        # 재시작 후 프로그램이 뜰 때까지 잠시 대기
                        time.sleep(3)  # 1초 -> 3초로 증가
                else:
                    # 비정상 종료로 판단
                    self.restart_count += 1
                    self.log(f"비정상 종료로 감지되었습니다. 재시작 시도 ({self.restart_count}/{self.max_restart_count}).")
                    if self.restart_count <= self.max_restart_count:
                        for i in range(self.restart_delay):
                            if not self.running:
                                break
                            time.sleep(1)
                        if self.running:
                            self.start_program_nonblocking()
                            # 재시작 후 프로그램이 뜰 때까지 잠시 대기
                            time.sleep(3)  # 1초 -> 3초로 증가
                    else:
                        self.log("최대 재시작 횟수에 도달했습니다. 프로그램 수동 실행을 대기합니다.")
                        # 사용자가 수동으로 실행할 때까지 대기
                        while self.running and not self.is_manager_running():
                            time.sleep(1)
            else:
                # 매니저 프로그램이 실행 중이면 정상 종료 플래그 리셋 및 대기
                if self._normal_exit_detected:
                    self.log("매니저 프로그램이 다시 실행되었습니다. 정상 종료 플래그를 리셋합니다.")
                    self._normal_exit_detected = False
                    self.restart_count = 0  # 재시작 카운트도 리셋
                time.sleep(1)
                # 헬스체크: 매니저 하트비트 파일이 일정 시간 갱신되지 않으면 비정상으로 판단
                try:
                    if self.manager_hb.exists():
                        mtime = self.manager_hb.stat().st_mtime
                        if (time.time() - mtime) > self.health_timeout:
                            if self.restart_count >= self.max_restart_count:
                                self.log(f"헬스체크 실패: 최대 재시작 횟수({self.max_restart_count})에 도달하여 재시작을 중단합니다.")
                            else:
                                self.restart_count += 1
                                self.log(f"헬스체크 실패로 재시작 시도 {self.restart_count}/{self.max_restart_count} (타임아웃 {self.health_timeout}s).")
                                # 재시작 전 지연
                                for i in range(self.restart_delay):
                                    if not self.running:
                                        break
                                    time.sleep(1)
                                # 가능한 경우 실행 중 프로세스를 종료 (Linux 전용)
                                try:
                                    import psutil
                                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                                        try:
                                            cmdline = proc.info.get('cmdline') or proc.cmdline()
                                            if cmdline and any('main.py' in str(c) for c in cmdline):
                                                self.log(f"헬스체크 실패: 프로세스 종료 시도 (PID: {proc.info['pid']})")
                                                proc.terminate()
                                                try:
                                                    proc.wait(timeout=5)
                                                except psutil.TimeoutExpired:
                                                    proc.kill()  # 강제 종료
                                                break
                                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                            continue
                                except Exception as e:
                                    self.log(f"프로세스 종료 시도 중 오류: {e}")
                                # 재시작
                                if self.running:
                                    self.start_program_nonblocking()
                                    time.sleep(1)
                except Exception:
                    pass

        # PID 파일 삭제
        try:
            pid_file = self.program_dir / "watchdog.pid"
            if pid_file.exists():
                pid_file.unlink()
                self.log("와치독 PID 파일 삭제")
        except Exception as e:
            self.log(f"PID 파일 삭제 실패: {e}")

        self.log("와치독 종료")
        
    def start_with_gui(self):
        """GUI와 함께 시작"""
        try:
            import tkinter as tk
            from tkinter import ttk, scrolledtext, messagebox
            # pystray import 시도 (X 서버 접근 필요)
            try:
                import pystray
                from PIL import Image, ImageDraw
            except (ImportError, Exception) as e:
                # pystray import 실패 시 (X 서버 접근 불가 등)
                self.log(f"pystray import 실패 ({e}). GUI 없이 실행합니다.")
                self.start_watchdog()
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.log("종료 신호를 받았습니다.")
                    self.running = False
                return
            
            class WatchdogGUI:
                def __init__(self, watchdog):
                    self.watchdog = watchdog
                    # watchdog에 GUI 참조 저장 (매니저 실행 시 트레이로 숨기기 위해)
                    watchdog.gui_reference = self
                    self.root = tk.Tk()
                    self.root.title("GARAMe MANAGER Watchdog")
                    self.root.geometry("500x300")
                    self.root.resizable(False, False)

                    # 항상 최상위 속성 제거 (매니저가 포커스를 가질 수 있도록)
                    # overrideredirect 제거 (정상적인 창 버튼 사용)
                    
                    # GUI 구성 (먼저 설정하여 컨텍스트 메뉴 준비)
                    self.setup_gui()
                    
                    # 시스템 트레이 아이콘 생성 (GUI 설정 후)
                    self.create_tray_icon()

                    # 와치독 창은 시작 시 트레이로 자동 숨김 (백그라운드로 실행)
                    # 트레이 아이콘으로만 접근 가능하도록
                    self.root.after(500, self.auto_hide_to_background)
                    
                    # 트레이 아이콘 관련 설정 제거됨 (트레이로 숨기기 기능 제거)
                    
                    # 윈도우 닫기 이벤트 처리 - 종료
                    self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
                    
                    # 트레이 아이콘 사용 가능 여부는 create_tray_icon에서 설정됨
                    self.tray_available = False  # 초기값: 트레이 아이콘 사용 불가
                    
                    # 와치독 스레드 시작
                    self.watchdog_thread = threading.Thread(target=self.watchdog.start_watchdog)
                    self.watchdog_thread.daemon = True
                    self.watchdog_thread.start()
                    
                    # 매니저 프로그램 실행 감지 및 뒤로 보내기 (주기적 체크)
                    self.check_manager_and_lower()
                    
                def start_move(self, event):
                    """윈도우 드래그 시작"""
                    self.x = event.x
                    self.y = event.y
                    
                def on_move(self, event):
                    """윈도우 드래그 중"""
                    deltax = event.x - self.x
                    deltay = event.y - self.y
                    x = self.root.winfo_x() + deltax
                    y = self.root.winfo_y() + deltay
                    self.root.geometry(f"+{x}+{y}")
                    
                def create_tray_icon(self):
                    """시스템 트레이 아이콘 생성"""
                    try:
                        # 기존 트레이 아이콘이 있으면 제거
                        if hasattr(self, 'tray_icon') and self.tray_icon is not None:
                            try:
                                self.tray_icon.stop()
                            except:
                                pass
                        
                        # 간단한 아이콘 이미지 생성
                        image = Image.new('RGB', (64, 64), color='red')
                        draw = ImageDraw.Draw(image)
                        draw.ellipse([16, 16, 48, 48], fill='white', outline='black')
                        draw.text((20, 20), "W", fill='black')
                        
                        # 트레이 아이콘 메뉴
                        menu = pystray.Menu(
                            pystray.MenuItem("Show", self.show_window),
                            pystray.MenuItem("Hide", self.hide_to_tray),
                            pystray.Menu.SEPARATOR,
                            pystray.MenuItem("Settings", self.show_settings),
                            pystray.MenuItem("Log View", self.show_log_window),
                            pystray.Menu.SEPARATOR,
                            pystray.MenuItem("Exit", self.force_exit)
                        )
                        
                        # 트레이 아이콘 생성
                        # 더블 클릭 지원을 위한 클릭 시간 추적
                        self._last_click_time = 0
                        self._click_count = 0
                        
                        def on_icon_click(icon, item):
                            """트레이 아이콘 클릭 핸들러 (더블 클릭 감지)"""
                            import time
                            current_time = time.time()
                            
                            # 기존 타이머 취소
                            if hasattr(self, '_click_timer'):
                                self.root.after_cancel(self._click_timer)
                            
                            # 0.5초 이내에 두 번 클릭되면 더블 클릭으로 간주
                            if current_time - self._last_click_time < 0.5:
                                self._click_count += 1
                            else:
                                self._click_count = 1
                            
                            # 더블 클릭 감지 (2번 클릭)
                            if self._click_count >= 2:
                                self._click_count = 0
                                self.show_window()
                            else:
                                # 단일 클릭: 타이머로 더블 클릭 대기
                                # 더블 클릭이 아니면 아무것도 하지 않음
                                def reset_click_count():
                                    self._click_count = 0
                                
                                # 0.5초 후에 클릭 카운트 리셋
                                self._click_timer = self.root.after(500, reset_click_count)
                            
                            self._last_click_time = current_time
                        
                        self.tray_icon = pystray.Icon(
                            "GARAMe Watchdog",
                            image,
                            "GARAMe MANAGER Watchdog\n더블클릭: 창 표시\n우클릭: 메뉴",
                            menu,
                            default_action=on_icon_click  # 클릭 시 더블 클릭 감지
                        )
                        
                        # 트레이 아이콘을 별도 스레드에서 실행
                        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                        self.tray_thread.start()
                        
                        self.tray_available = True  # 트레이 아이콘 사용 가능
                        print("트레이 아이콘이 생성되었습니다.")
                        self.watchdog.log("트레이 아이콘이 생성되었습니다.")
                        
                        # 와치독 창은 항상 화면에 표시 (트레이로 숨기지 않음)
                        
                    except ImportError as e:
                        print(f"pystray 라이브러리가 설치되지 않았습니다: {e}")
                        print("트레이 아이콘 없이 GUI 창만 사용합니다.")
                        self.tray_icon = None
                        self.tray_available = False
                    except Exception as e:
                        print(f"트레이 아이콘 생성 오류: {e}")
                        print("트레이 아이콘 없이 GUI 창만 사용합니다.")
                        self.tray_icon = None
                        self.tray_available = False
                    
                def show_context_menu(self, event):
                    """컨텍스트 메뉴 표시"""
                    try:
                        self.context_menu.tk_popup(event.x_root, event.y_root)
                    finally:
                        self.context_menu.grab_release()
                
                def show_window(self, icon=None, item=None):
                    """윈도우 표시"""
                    try:
                        self.root.deiconify()
                        self.root.lift()
                        self.root.focus_force()
                        self.watchdog.log("와치독 창이 표시되었습니다.")
                    except Exception as e:
                        self.watchdog.log(f"창 표시 중 오류: {e}")
                        # GUI 스레드에서 실행되도록 보장
                        self.root.after(0, lambda: (
                            self.root.deiconify(),
                            self.root.lift(),
                            self.root.focus_force()
                        ))
                    
                def on_window_close(self):
                    """윈도우 닫기 이벤트 처리"""
                    # 트레이 아이콘이 사용 가능하면 트레이로 숨기기
                    if hasattr(self, 'tray_available') and self.tray_available and hasattr(self, 'tray_icon') and self.tray_icon is not None:
                        self.hide_to_tray()
                    else:
                        # 트레이 아이콘이 없으면 강제 종료 확인
                        try:
                            from tkinter import messagebox
                            if messagebox.askyesno("와치독 종료", "와치독을 종료하시겠습니까?\n\n종료하면 매니저 프로그램을 감시하지 않습니다."):
                                self.force_exit()
                        except Exception:
                            # messagebox가 없으면 그냥 종료
                            self.force_exit()
                        # 아니오를 누르면 창 유지
                
                def hide_to_tray(self):
                    """트레이로 숨기기 (무조건 숨기기)"""
                    # 무조건 창을 숨기기
                    self.root.withdraw()
                    
                    if hasattr(self, 'tray_available') and self.tray_available and hasattr(self, 'tray_icon') and self.tray_icon is not None:
                        self.watchdog.log("와치독이 트레이로 숨겨졌습니다.")
                        self.watchdog.log("트레이 아이콘을 더블 클릭하거나 우클릭하여 메뉴에서 'Show'를 선택하면 창을 다시 열 수 있습니다.")
                    else:
                        # 트레이 아이콘이 없어도 창은 숨기기
                        self.watchdog.log("와치독 창이 숨겨졌습니다. (트레이 아이콘 없음)")
                
                def _show_tray_unavailable_message(self):
                    """트레이 아이콘이 사용 불가능하다는 메시지 표시"""
                    try:
                        from tkinter import messagebox
                        messagebox.showinfo(
                            "트레이 아이콘 사용 불가",
                            "트레이 아이콘이 사용할 수 없습니다.\n\n"
                            "pystray 라이브러리나 X 서버 접근 문제로 인해\n"
                            "트레이 아이콘 기능을 사용할 수 없습니다.\n\n"
                            "GUI 창을 계속 표시합니다."
                        )
                    except Exception:
                        print("트레이 아이콘이 사용할 수 없습니다. GUI 창을 계속 표시합니다.")
                
                def auto_hide_to_background(self):
                    """와치독 창을 백그라운드로 자동 숨김"""
                    try:
                        # 트레이 아이콘이 있으면 트레이로 숨김
                        if hasattr(self, 'tray_available') and self.tray_available:
                            self.root.withdraw()
                            self.watchdog.log("와치독이 백그라운드(트레이)로 숨겨졌습니다.")
                        else:
                            # 트레이 아이콘이 없으면 최소화만 함
                            self.root.iconify()
                            self.watchdog.log("와치독이 최소화되었습니다.")
                    except Exception as e:
                        self.watchdog.log(f"와치독 자동 숨김 실패: {e}")

                def check_manager_and_lower(self):
                    """매니저 프로그램 실행 여부를 주기적으로 확인하고 포커스 관리"""
                    # 매니저 프로그램이 실행 중일 때 와치독은 백그라운드 유지
                    # (이미 트레이로 숨겨져 있거나 최소화되어 있음)
                    # 매니저 창이 항상 포커스를 가질 수 있도록 와치독은 개입하지 않음

                    # 1초 후 다시 확인
                    self.root.after(1000, self.check_manager_and_lower)
                    
                def force_exit(self, icon=None, item=None):
                    """완전 종료 (재시작 방지)"""
                    try:
                        # 종료 확인
                        try:
                            from tkinter import messagebox
                            if not messagebox.askyesno("와치독 종료", "와치독을 완전히 종료하시겠습니까?\n\n종료하면 매니저 프로그램을 감시하지 않으며, 자동으로 재시작되지 않습니다."):
                                return  # 취소
                        except Exception:
                            pass  # messagebox가 없으면 그냥 진행

                        self.watchdog.log("와치독 완전 종료를 시작합니다...")

                        # 와치독 종료 신호 파일 생성 (메인 루프에서 확인)
                        try:
                            exit_file = self.watchdog.program_dir / "watchdog_exit.signal"
                            with open(exit_file, 'w', encoding='utf-8') as f:
                                f.write(f"watchdog_exit_{int(time.time())}\n")
                                f.flush()
                                os.fsync(f.fileno())
                            self.watchdog.log("와치독 종료 신호 파일을 생성했습니다.")
                        except Exception as e:
                            self.watchdog.log(f"와치독 종료 신호 파일 생성 실패: {e}")

                        # 와치독 실행 중지
                        self.watchdog.running = False

                        # 정상 종료 플래그 설정 (재시작 방지)
                        self.watchdog._normal_exit_detected = True

                        # 하트비트 스레드 종료
                        self.watchdog._heartbeat_running = False
                        if self.watchdog._heartbeat_thread is not None:
                            if self.watchdog._heartbeat_thread.is_alive():
                                # 스레드가 종료될 때까지 잠시 대기
                                self.watchdog._heartbeat_thread.join(timeout=1.0)

                        # 트레이 아이콘 종료
                        try:
                            if hasattr(self, 'tray_icon') and self.tray_icon is not None:
                                self.tray_icon.stop()
                        except Exception:
                            pass

                        # 와치독 스레드 종료 대기
                        if hasattr(self, 'watchdog_thread') and self.watchdog_thread is not None:
                            if self.watchdog_thread.is_alive():
                                # 스레드가 종료될 때까지 잠시 대기
                                self.watchdog_thread.join(timeout=2.0)

                        # 하트비트 파일 삭제
                        try:
                            if self.watchdog.watchdog_hb.exists():
                                self.watchdog.watchdog_hb.unlink()
                        except Exception:
                            pass

                        self.watchdog.log("와치독 완전 종료 완료.")

                        # GUI 종료
                        try:
                            self.root.quit()
                        except:
                            pass

                        try:
                            self.root.destroy()
                        except:
                            pass

                        # 프로세스 완전 종료
                        import sys
                        import os
                        os._exit(0)  # os._exit는 더 강력한 종료 (스레드나 다른 작업을 기다리지 않음)

                    except Exception as e:
                        print(f"종료 중 오류: {e}")
                        import traceback
                        traceback.print_exc()
                        # 오류가 나도 강제 종료
                        import sys
                        import os
                        os._exit(1)
                    
                def setup_gui(self):
                    """GUI 설정"""
                    # 우클릭 메뉴 추가 (트레이 아이콘 접근이 어려울 수 있으므로)
                    self.context_menu = tk.Menu(self.root, tearoff=0)
                    self.context_menu.add_command(label="설정", command=self.show_settings)
                    self.context_menu.add_command(label="로그 보기", command=self.show_log_window)
                    self.context_menu.add_separator()
                    # 트레이로 숨기기 메뉴 제거됨 (사용자 요청)
                    self.context_menu.add_command(label="종료", command=self.force_exit)
                    
                    # 우클릭 바인딩
                    self.root.bind("<Button-3>", self.show_context_menu)
                    # Alt+F4나 Ctrl+Q로도 창 표시 가능하도록
                    self.root.bind("<Alt-F4>", lambda e: self.show_window())
                    self.root.bind("<Control-q>", lambda e: self.show_window())
                    
                    # 제목
                    title_label = ttk.Label(self.root, text="GARAMe MANAGER Watchdog", font=("Arial", 12, "bold"))
                    title_label.pack(pady=5)
                    
                    # 안내 텍스트 추가
                    if hasattr(self, 'tray_available') and self.tray_available:
                        info_text = ttk.Label(self.root, 
                                             text="우클릭: 메뉴 표시\n트레이 아이콘: 우클릭으로 메뉴 접근", 
                                             font=("Arial", 8), 
                                             foreground="gray")
                    else:
                        info_text = ttk.Label(self.root, 
                                             text="GUI 창에서 우클릭하여 메뉴에 접근할 수 있습니다", 
                                             font=("Arial", 8), 
                                             foreground="gray")
                    info_text.pack(pady=2)
                    
                    # 정보 표시 프레임
                    info_frame = ttk.Frame(self.root)
                    info_frame.pack(fill="x", padx=10, pady=5)
                    
                    # 실행 시간 표시
                    self.runtime_label = ttk.Label(info_frame, text="실행 시간: 00:00:00", font=("Arial", 9))
                    self.runtime_label.pack(anchor="w")
                    
                    # 재시작 횟수 표시
                    self.restart_label = ttk.Label(info_frame, text="재시작 횟수: 0", font=("Arial", 9))
                    self.restart_label.pack(anchor="w")
                    
                    # 최대 재시작 설정 표시
                    self.max_restart_label = ttk.Label(info_frame, text=f"최대 재시작: {self.watchdog.max_restart_count}", font=("Arial", 9))
                    self.max_restart_label.pack(anchor="w")
                    
                    # 재시작 대기 시간 표시
                    self.delay_label = ttk.Label(info_frame, text=f"재시작 대기: {self.watchdog.restart_delay}초", font=("Arial", 9))
                    self.delay_label.pack(anchor="w")
                    
                    # 버튼 프레임
                    button_frame = tk.Frame(self.root, bg="#F0F0F0")
                    button_frame.pack(pady=30, fill="x", padx=20)  # 패딩 증가 및 fill 추가
                    
                    # 로그 보기 버튼 (좌우 30% 축소, 폰트 50% 축소)
                    btn_log = tk.Button(button_frame, text="로그 보기", command=self.show_log_window,
                                       font=("Arial", 7, "bold"), width=7, height=2,
                                       bg="#3498DB", fg="white", relief="raised", bd=3)
                    btn_log.pack(side="left", padx=5, fill="x", expand=True)

                    # 설정 버튼 (좌우 30% 축소, 폰트 50% 축소)
                    btn_settings = tk.Button(button_frame, text="설정", command=self.show_settings,
                                            font=("Arial", 7, "bold"), width=7, height=2,
                                            bg="#E67E22", fg="white", relief="raised", bd=3)
                    btn_settings.pack(side="left", padx=5, fill="x", expand=True)

                    # 트레이로 숨기기 버튼 제거됨 (사용자 요청)

                    # 종료 버튼 (좌우 30% 축소, 폰트 50% 축소)
                    self.btn_exit = tk.Button(button_frame, text="와치독 종료", command=self.force_exit,
                                            font=("Arial", 7, "bold"), width=7, height=2,
                                            bg="#E74C3C", fg="white", relief="raised", bd=3)
                    self.btn_exit.pack(side="left", padx=5, fill="x", expand=True)
                    
                    # 실행 시간 업데이트 타이머
                    self.update_runtime()
                    
                def show_settings(self):
                    """설정 창 표시"""
                    settings_window = tk.Toplevel(self.root)
                    settings_window.title("와치독 설정")
                    settings_window.geometry("700x900")  # 높이를 800에서 900으로 증가  # 더 크게 확장
                    settings_window.resizable(False, False)
                    
                    # 설정 프레임
                    settings_frame = ttk.Frame(settings_window)
                    settings_frame.pack(fill="both", expand=True, padx=20, pady=20)
                    
                    # 제목
                    title_label = ttk.Label(settings_frame, text="와치독 설정", font=("Arial", 18, "bold"))
                    title_label.pack(pady=(0, 30))
                    
                    # 최대 재시작 횟수 설정
                    max_restart_frame = ttk.Frame(settings_frame)
                    max_restart_frame.pack(fill="x", pady=10)
                    
                    ttk.Label(max_restart_frame, text="최대 재시작 횟수:", font=("Arial", 12)).pack(side="left")
                    max_restart_var = tk.StringVar(value=str(self.watchdog.max_restart_count))
                    max_restart_entry = tk.Entry(max_restart_frame, textvariable=max_restart_var, width=15, font=("Arial", 12))
                    max_restart_entry.pack(side="right")
                    
                    # 재시작 대기 시간 설정
                    delay_frame = ttk.Frame(settings_frame)
                    delay_frame.pack(fill="x", pady=10)
                    
                    ttk.Label(delay_frame, text="재시작 대기 시간(초):", font=("Arial", 12)).pack(side="left")
                    delay_var = tk.StringVar(value=str(self.watchdog.restart_delay))
                    delay_entry = tk.Entry(delay_frame, textvariable=delay_var, width=15, font=("Arial", 12))
                    delay_entry.pack(side="right")

                    # 숫자 패드 프레임
                    keypad_frame = ttk.LabelFrame(settings_frame, text="숫자 입력", padding=10)
                    keypad_frame.pack(fill="x", pady=20)
                    
                    # 현재 입력 필드 추적
                    current_entry = [max_restart_entry]  # 기본값
                    
                    def set_current_entry(entry):
                        current_entry[0] = entry
                        entry.focus_set()
                        print(f"입력 필드 선택됨: {entry.cget('textvariable')}")
                    
                    # 입력창에 클릭 이벤트 추가
                    max_restart_entry.bind("<Button-1>", lambda e: set_current_entry(max_restart_entry))
                    delay_entry.bind("<Button-1>", lambda e: set_current_entry(delay_entry))
                    
                    # 기본적으로 첫 번째 입력창 선택
                    set_current_entry(max_restart_entry)
                    
                    def insert_number(num):
                        current_entry[0].insert(tk.INSERT, str(num))
                    
                    def insert_dot():
                        current_entry[0].insert(tk.INSERT, ".")
                    
                    def clear_entry():
                        current_entry[0].delete(0, tk.END)
                    
                    def backspace():
                        current_text = current_entry[0].get()
                        if current_text:
                            current_entry[0].delete(len(current_text) - 1, tk.END)
                    
                    # 숫자 패드 버튼 생성 - 터치 전용 큰 버튼
                    pad_frame = tk.Frame(keypad_frame, bg="#F5F5F5")
                    pad_frame.pack()
                    
                    # 첫 번째 행: 7, 8, 9
                    btn7 = tk.Button(pad_frame, text="7", command=lambda: insert_number(7),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn7.grid(row=0, column=0, padx=5, pady=5)
                    
                    btn8 = tk.Button(pad_frame, text="8", command=lambda: insert_number(8),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn8.grid(row=0, column=1, padx=5, pady=5)
                    
                    btn9 = tk.Button(pad_frame, text="9", command=lambda: insert_number(9),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn9.grid(row=0, column=2, padx=5, pady=5)
                    
                    # 두 번째 행: 4, 5, 6
                    btn4 = tk.Button(pad_frame, text="4", command=lambda: insert_number(4),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn4.grid(row=1, column=0, padx=5, pady=5)
                    
                    btn5 = tk.Button(pad_frame, text="5", command=lambda: insert_number(5),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn5.grid(row=1, column=1, padx=5, pady=5)
                    
                    btn6 = tk.Button(pad_frame, text="6", command=lambda: insert_number(6),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn6.grid(row=1, column=2, padx=5, pady=5)
                    
                    # 세 번째 행: 1, 2, 3
                    btn1 = tk.Button(pad_frame, text="1", command=lambda: insert_number(1),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn1.grid(row=2, column=0, padx=5, pady=5)
                    
                    btn2 = tk.Button(pad_frame, text="2", command=lambda: insert_number(2),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn2.grid(row=2, column=1, padx=5, pady=5)
                    
                    btn3 = tk.Button(pad_frame, text="3", command=lambda: insert_number(3),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn3.grid(row=2, column=2, padx=5, pady=5)
                    
                    # 네 번째 행: 0, ., 백스페이스
                    btn0 = tk.Button(pad_frame, text="0", command=lambda: insert_number(0),
                                    font=("Arial", 16, "bold"), width=6, height=2,
                                    bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn0.grid(row=3, column=0, padx=5, pady=5)
                    
                    btn_dot = tk.Button(pad_frame, text=".", command=insert_dot,
                                       font=("Arial", 16, "bold"), width=6, height=2,
                                       bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=3)
                    btn_dot.grid(row=3, column=1, padx=5, pady=5)
                    
                    btn_backspace = tk.Button(pad_frame, text="⌫", command=backspace,
                                             font=("Arial", 16, "bold"), width=6, height=2,
                                             bg="#E74C3C", fg="white", relief="raised", bd=3)
                    btn_backspace.grid(row=3, column=2, padx=5, pady=5)
                    
                    
                    # 설명 텍스트
                    info_text = ttk.Label(settings_frame, 
                                        text="1. 입력창을 클릭하여 선택하세요\n2. 숫자 패드로 값을 입력하세요\n3. 설정을 변경한 후 '저장' 버튼을 클릭하세요",
                                        font=("Arial", 12), foreground="gray")
                    info_text.pack(pady=20)
                    
                    # 버튼 프레임
                    button_frame = tk.Frame(settings_frame, bg="#F0F0F0")
                    button_frame.pack(pady=50, fill="x", padx=20)  # 패딩 증가 및 fill 추가
                    
                    def save_settings():
                        try:
                            self.watchdog.max_restart_count = int(max_restart_var.get())
                            self.watchdog.restart_delay = int(delay_var.get())
                            self.watchdog.save_config()
                            
                            # GUI 업데이트
                            self.max_restart_label.config(text=f"최대 재시작: {self.watchdog.max_restart_count}")
                            self.delay_label.config(text=f"재시작 대기: {self.watchdog.restart_delay}초")
                            
                            settings_window.destroy()
                            
                        except ValueError:
                            tk.messagebox.showerror("오류", "숫자를 올바르게 입력해주세요.")
                    
                    # 저장/취소 버튼 (좌우 30% 축소, 폰트 50% 축소)
                    btn_save = tk.Button(button_frame, text="저장", command=save_settings,
                                        font=("Arial", 10, "bold"), width=10, height=3,
                                        bg="#27AE60", fg="white", relief="raised", bd=4)
                    btn_save.pack(side="left", padx=30, fill="x", expand=True)
                    
                    btn_cancel = tk.Button(button_frame, text="취소", command=settings_window.destroy,
                                          font=("Arial", 10, "bold"), width=10, height=3,
                                          bg="#E74C3C", fg="white", relief="raised", bd=4)
                    btn_cancel.pack(side="left", padx=30, fill="x", expand=True)
                    
                def show_log_window(self):
                    """로그 보기 창 표시"""
                    log_window = tk.Toplevel(self.root)
                    log_window.title("와치독 로그 보기")
                    log_window.geometry("800x600")
                    
                    # 로그 텍스트 영역
                    log_text_frame = ttk.Frame(log_window)
                    log_text_frame.pack(fill="both", expand=True, padx=10, pady=10)
                    
                    log_text = scrolledtext.ScrolledText(log_text_frame, height=30, width=90)
                    log_text.pack(fill="both", expand=True)
                    
                    # 로그 파일 내용 읽기
                    try:
                        if os.path.exists(self.watchdog.log_file):
                            with open(self.watchdog.log_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                log_text.insert(tk.END, content)
                                log_text.see(tk.END)
                        else:
                            log_text.insert(tk.END, "로그 파일이 없습니다.")
                    except Exception as e:
                        log_text.insert(tk.END, f"로그 파일 읽기 오류: {e}")
                    
                    # 버튼 프레임
                    button_frame = ttk.Frame(log_window)
                    button_frame.pack(pady=10)
                    
                    ttk.Button(button_frame, text="새로고침", command=lambda: self.refresh_log_window(log_text)).pack(side="left", padx=5)
                    ttk.Button(button_frame, text="닫기", command=log_window.destroy).pack(side="left", padx=5)
                    
                def refresh_log_window(self, log_text):
                    """로그 창 새로고침"""
                    log_text.delete(1.0, tk.END)
                    try:
                        if os.path.exists(self.watchdog.log_file):
                            with open(self.watchdog.log_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                log_text.insert(tk.END, content)
                                log_text.see(tk.END)
                        else:
                            log_text.insert(tk.END, "로그 파일이 없습니다.")
                    except Exception as e:
                        log_text.insert(tk.END, f"로그 파일 읽기 오류: {e}")
                    
                def update_runtime(self):
                    """실행 시간 업데이트"""
                    try:
                        # 실행 시간 계산
                        runtime = datetime.now() - self.watchdog.start_time
                        hours, remainder = divmod(runtime.total_seconds(), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        runtime_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
                        
                        # 실행 시간 업데이트
                        self.runtime_label.config(text=f"실행 시간: {runtime_str}")
                        
                        # 재시작 횟수 업데이트
                        self.restart_label.config(text=f"재시작 횟수: {self.watchdog.restart_count}")
                        
                        # 최대 재시작 설정 업데이트
                        self.max_restart_label.config(text=f"최대 재시작: {self.watchdog.max_restart_count}")
                        
                        # 재시작 대기 시간 업데이트
                        self.delay_label.config(text=f"재시작 대기: {self.watchdog.restart_delay}초")
                        
                    except Exception as e:
                        pass
                    
                    # 1초 후 다시 업데이트
                    self.root.after(1000, self.update_runtime)
                    
                def run(self):
                    """GUI 실행"""
                    self.root.mainloop()
            
            # GUI 시작
            gui = WatchdogGUI(self)
            gui.run()
            
        except ImportError:
            # tkinter가 없으면 콘솔 모드로 실행
            self.start_watchdog()

def main():
    """메인 함수"""
    print("=" * 50)
    print("    GARAMe MANAGER Watchdog")
    print("=" * 50)
    print()
    
    # 와치독 생성 및 시작
    watchdog = GARAMeManagerWatchdog()
    
    # DISPLAY 환경 변수 확인하여 GUI 모드 결정
    display = os.environ.get('DISPLAY')
    use_gui = True
    
    # DISPLAY가 없거나 GUI 접근이 불가능한 경우 (systemd 서비스 등)
    if not display or display == '':
        use_gui = False
        watchdog.log("DISPLAY 환경 변수가 없어 GUI 없이 실행합니다.")
    else:
        # X 서버 접근 테스트
        try:
            import tkinter as tk
            test_root = tk.Tk()
            test_root.withdraw()  # 숨기기
            test_root.destroy()
            watchdog.log(f"DISPLAY {display}에 접근 가능합니다. GUI 모드로 실행합니다.")
        except Exception as e:
            use_gui = False
            watchdog.log(f"GUI 접근 불가 ({e}). GUI 없이 실행합니다.")
    
    if use_gui:
        # GUI 모드로 시작
        watchdog.start_with_gui()
    else:
        # GUI 없이 시작 (백그라운드 모드)
        watchdog.log("GUI 없이 와치독을 시작합니다.")
        watchdog.start_watchdog()
        
        # 메인 루프 유지
        try:
            while watchdog.running:
                time.sleep(1)
        except KeyboardInterrupt:
            watchdog.log("종료 신호를 받았습니다.")
            watchdog.running = False

if __name__ == "__main__":
    main()
