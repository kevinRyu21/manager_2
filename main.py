#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP Monitor v1.9.8.4 - 메인 진입점

센서 데이터를 실시간으로 모니터링하는 TCP 기반 애플리케이션입니다.
Ubuntu Linux 전용 (Windows 지원 안 함)

사용법:
    python main.py [--config CONFIG_FILE]

의존성:
    - tkinter (Python 내장)
    - pillow (선택): 이미지 처리
    - matplotlib (선택): 그래프 표시
    - pyttsx3 (선택): 음성 알림
"""

import argparse
import queue
import threading
import os
import sys
import platform
import subprocess
import warnings

# NNPACK 경고 억제 (GPU 없는 환경에서 발생하는 무해한 경고)
warnings.filterwarnings("ignore", message=".*NNPACK.*")
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ["PYTORCH_JIT_LOG_LEVEL"] = "ERROR"

# Linux 전용 체크
if platform.system() != "Linux":
    print("ERROR: 이 프로그램은 Ubuntu Linux에서만 실행됩니다.")
    print(f"현재 시스템: {platform.system()}")
    sys.exit(1)

# CPU 호환성 문제 해결: NumPy와 PyTorch의 고급 최적화 비활성화
# Illegal instruction 오류 방지를 위해 환경 변수 설정
# (import 전에 설정해야 효과적)
if 'OPENBLAS_NUM_THREADS' not in os.environ:
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
if 'MKL_NUM_THREADS' not in os.environ:
    os.environ['MKL_NUM_THREADS'] = '1'
if 'NUMEXPR_NUM_THREADS' not in os.environ:
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
if 'OMP_NUM_THREADS' not in os.environ:
    os.environ['OMP_NUM_THREADS'] = '1'
# NumPy 최적화 레벨 낮추기 (CPU 호환성 개선)
if 'NPY_DISABLE_CPU_FEATURES' not in os.environ:
    os.environ['NPY_DISABLE_CPU_FEATURES'] = '1'
# PyTorch CPU 최적화 비활성화
if 'TORCH_USE_CUDA_DSA' not in os.environ:
    os.environ['TORCH_USE_CUDA_DSA'] = '0'
# PyTorch pin_memory 비활성화 (경고 제거)
if 'TORCH_CUDA_ARCH_LIST' not in os.environ:
    os.environ['TORCH_CUDA_ARCH_LIST'] = ''
# PyTorch NNPACK 비활성화 (CPU 호환성 문제 해결)
if 'USE_NNPACK' not in os.environ:
    os.environ['USE_NNPACK'] = '0'
if 'NNPACK_DISABLE' not in os.environ:
    os.environ['NNPACK_DISABLE'] = '1'
# PyTorch MPS 비활성화
if 'PYTORCH_ENABLE_MPS_FALLBACK' not in os.environ:
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
if 'PYTORCH_MPS_HIGH_WATERMARK_RATIO' not in os.environ:
    os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'

# 안전 가드는 Python 3.13+에서 _ThreadHandle 내부 동작과 충돌하여 제거함
# 모든 스레드 생성 코드는 이미 검증되었으므로 안전 가드 불필요

# PyInstaller 실행 파일 지원: 기본 경로 설정
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller --onefile 모드
    # _MEIPASS: 임시 폴더에 압축 해제된 파이썬 모듈들
    # 실행 파일 디렉토리: config.conf, assets/, logs/ 등 외부 파일 위치
    EXECUTABLE_DIR = os.path.dirname(sys.executable)
    BASE_DIR = EXECUTABLE_DIR  # 모든 외부 파일은 실행 파일 기준
    # 내부 모듈 경로 추가
    sys.path.insert(0, sys._MEIPASS)
    print(f"[PyInstaller 모드] 실행 파일 디렉토리: {EXECUTABLE_DIR}")
else:
    # 일반 Python 모드
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXECUTABLE_DIR = BASE_DIR

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, BASE_DIR)

# 작업 디렉토리를 실행 파일 디렉토리로 변경
os.chdir(EXECUTABLE_DIR)


from src.tcp_monitor import ConfigManager, App, TcpServer


def main():
    """메인 함수"""
    ap = argparse.ArgumentParser(description="TCP Monitor - Real-time sensor data monitoring")
    ap.add_argument("--config", type=str, default="config.conf", help="설정 파일 경로")
    args = ap.parse_args()

    # 스플래시 화면 표시
    splash = None
    try:
        from src.tcp_monitor.ui.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.update_status("시스템 초기화 중...", 0)
    except Exception as e:
        print(f"[경고] 스플래시 화면 로드 실패: {e}")

    # 설정 파일 경로 (실행 파일/소스 디렉토리 기준)
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(EXECUTABLE_DIR, config_path)

    if not os.path.exists(config_path):
        print(f"[경고] 설정 파일을 찾을 수 없습니다: {config_path}")

    # 스플래시 업데이트: 설정 로드
    if splash:
        splash.update_status("설정 파일 로드 중...", 15)

    # 설정 로드
    cfg = ConfigManager(config_path)

    # 스플래시 업데이트: AI 모델 로드
    if splash:
        splash.update_status("AI 모델 초기화 중...", 30)

    # AI 모델 사전 로드 (백그라운드에서 미리 로드하여 카메라 시작 속도 향상)
    # 성능 모드에 따라 필요한 모델만 로드 (1: 얼굴만, 2: 얼굴+PPE, 3: 전체)
    try:
        from src.tcp_monitor.sensor.safety_detector import preload_models_async, set_performance_mode
        performance_mode = int(cfg.env.get("performance_mode", 2))
        performance_mode = max(1, min(3, performance_mode))  # 1~3 범위 제한

        # 중요: 성능 모드를 먼저 동기적으로 설정 (싱글톤 모델 로딩 전에 반드시 필요)
        # preload_models_async가 백그라운드에서 실행되므로, 모드 설정이 누락될 수 있음
        set_performance_mode(performance_mode)
        print(f"[AI] 성능 모드 {performance_mode} 설정 완료")

        # PPEDetector 성능 모드도 설정 (싱글톤 인스턴스 생성 전에 호출)
        try:
            from src.tcp_monitor.ppe.detector import PPEDetector
            PPEDetector.set_performance_mode(performance_mode)
        except Exception:
            pass

        if splash:
            splash.update_status("AI 모델 로드 중...", 50)

        preload_models_async(performance_mode)
    except Exception as e:
        print(f"[경고] AI 모델 사전 로드 실패: {e}")

    # 스플래시 업데이트: 애플리케이션 생성
    if splash:
        splash.update_status("애플리케이션 생성 중...", 70)

    # 애플리케이션 생성
    print("[DEBUG] App 생성 시작...")
    app = App(cfg)
    print("[DEBUG] App 생성 완료")

    # 스플래시 업데이트: 완료
    if splash:
        splash.update_status("시작 준비 완료!", 100)
        # 잠시 대기 후 스플래시 닫기
        import time
        time.sleep(0.5)
        splash.close()

    # 데이터 큐 생성
    q = queue.Queue()

    def validate(sid, pw):
        """인증 검증"""
        if not cfg.auth_enabled():
            return True
        return cfg.auth_map().get(sid, "") == (pw or "")

    # TCP 서버 시작
    server = TcpServer(cfg.listen["host"], cfg.listen["port"], q, validate, logger=app.logs)
    server.start()

    def pump():
        """데이터 펌프 (메인 스레드에서 실행)"""
        try:
            while True:
                item = q.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    if item[0] == "__data__":
                        payload = item[1] or {}
                        sid = payload.get("sid")
                        peer = payload.get("peer", "")
                        data = payload.get("data", {})
                        version = payload.get("version", None)
                        if sid:
                            if version:
                                try:
                                    app.update_sensor_version(sid, peer, version)
                                except Exception:
                                    pass
                            app.on_data(sid, peer, data)
                    elif item[0] == "__water_alert__":
                        payload = item[1] or {}
                        sid = payload.get("sid")
                        peer = payload.get("peer", "")
                        data = payload.get("data", {})
                        alert_type = payload.get("alert_type")
                        message = payload.get("message", "")
                        alert_level = payload.get("alert_level", "info")
                        if sid:
                            app.on_water_alert(sid, peer, data, alert_type, message, alert_level)
                else:
                    try:
                        sid, data = item
                        app.on_data(sid, "", data)
                    except Exception:
                        pass
        except queue.Empty:
            pass
        app.after(16, pump)  # 약 60fps로 큐 폴링 (센서 응답 속도 향상)

    # 데이터 펌프 시작 (즉시 시작)
    app.after(10, pump)
    
    # 메인 루프 시작
    print("[DEBUG] mainloop 시작...")
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"[DEBUG] mainloop 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 서버 정리
        try:
            server.stop()
        except:
            pass


if __name__ == "__main__":
    main()
