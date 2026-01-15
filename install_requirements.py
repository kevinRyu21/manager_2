#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
의존성 패키지 설치 스크립트

필수 패키지를 자동으로 설치합니다.
"""

import subprocess
import sys
import os
import platform

def install_package(package_name):
    """패키지 설치"""
    try:
        print(f"[설치 중] {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--quiet"])
        print(f"[완료] {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[실패] {package_name}: {e}")
        return False

# check_and_install_face_recognition 함수 제거됨
# v1.9.7에서는 InsightFace를 사용하므로 face_recognition(dlib) 불필요

def check_and_install_all():
    """모든 필수 패키지 확인 및 설치"""
    print("=== GARAMe MANAGER 의존성 확인 및 설치 (v1.9.7) ===\n")
    print("최신 AI 기술 적용:")
    print("  - InsightFace: 99.86% 얼굴 인식 정확도")
    print("  - YOLOv11: 92.7% mAP50 PPE 감지 정확도")
    print()

    # Ubuntu Linux 전용 체크
    if platform.system() != "Linux":
        print("ERROR: 이 프로그램은 Ubuntu Linux에서만 실행됩니다.")
        print(f"현재 시스템: {platform.system()}")
        return False

    # GPU 지원 여부 확인
    print("=" * 70)
    print("GPU 지원 옵션")
    print("=" * 70)
    print()
    print("NVIDIA GPU가 있는 경우 GPU 가속을 사용할 수 있습니다.")
    print("GPU 가속 사용 시 AI 처리 속도가 대폭 향상됩니다.")
    print()
    print("⚠️  주의: GPU 가속을 사용하려면 NVIDIA GPU + CUDA가 설치되어 있어야 합니다.")
    print("         CUDA가 없으면 프로그램 실행 시 오류가 발생합니다.")
    print()

    gpu_support = None
    while gpu_support is None:
        response = input("GPU 가속을 사용하시겠습니까? (y/n, 기본값: n): ").strip().lower()
        if response in ['', 'n', 'no']:
            gpu_support = False
            print("\n[선택] CPU 모드로 설치합니다.")
        elif response in ['y', 'yes']:
            gpu_support = True
            print("\n[선택] GPU 가속 모드로 설치합니다.")
            print("  ⚠️  CUDA가 설치되어 있지 않으면 오류가 발생할 수 있습니다.")
        else:
            print("❌ 잘못된 입력입니다. y 또는 n을 입력하세요.")

    print()

    # requirements.txt가 있으면 기본 패키지 설치
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file):
        print("[설치] requirements.txt에서 기본 패키지 설치 중...")
        print("  - InsightFace (얼굴 인식)")
        print("  - ONNX Runtime (추론 엔진 - CPU)")
        print("  - Ultralytics YOLOv11 (PPE 감지)")
        print("  - gTTS (음성 알림)")
        print("  - OpenCV, NumPy, Pillow 등")
        print()
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            print("✓ 기본 패키지 설치 완료")
        except Exception as e:
            print(f"[경고] 기본 패키지 설치 중 오류: {e}")

    # GPU 가속 패키지 설치
    if gpu_support:
        print("\n=== GPU 가속 패키지 설치 ===")
        try:
            # PyTorch GPU 버전 재설치
            print("  PyTorch GPU 버전 설치 중...")
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "torchvision",
                                 "--index-url", "https://download.pytorch.org/whl/cu121"])

            # ONNX Runtime GPU 버전 설치
            print("  ONNX Runtime GPU 버전 설치 중...")
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "onnxruntime-gpu>=1.16.0"])

            print("✓ GPU 가속 패키지 설치 완료")
            print()
            print("🎮 GPU 가속이 활성화되었습니다!")
            print("   - PyTorch: CUDA 12.1 버전")
            print("   - ONNX Runtime: GPU 버전")
            print("   프로그램 실행 시 CUDA가 감지되면 자동으로 GPU를 사용합니다.")
        except Exception as e:
            print(f"[경고] GPU 가속 패키지 설치 실패: {e}")
            print("        CPU 모드로 계속 진행합니다.")
            print()
            print("💡 CUDA를 설치한 후 다음 명령으로 GPU 가속을 활성화할 수 있습니다:")
            print("   pip uninstall torch torchvision onnxruntime")
            print("   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
            print("   pip install onnxruntime-gpu>=1.16.0")
    else:
        print("\n💻 CPU 모드로 설치되었습니다.")
        print("   - PyTorch: CPU 전용 버전")
        print("   - ONNX Runtime: CPU 버전")
        print()
        print("   나중에 GPU 가속을 사용하려면:")
        print("   1. NVIDIA GPU + CUDA 12.1 설치")
        print("   2. pip uninstall torch torchvision onnxruntime")
        print("   3. pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        print("   4. pip install onnxruntime-gpu>=1.16.0")

    # Linux에서 xdotool 설치 (한글 입력 조합 지원)
    print("\n=== xdotool 설치 (한글 입력 조합 지원) ===")
    try:
        subprocess.check_call(["xdotool", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[확인] xdotool 이미 설치됨")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[필요] xdotool이 설치되지 않았습니다.")
        print("       한글 입력 조합이 제대로 작동하려면 xdotool이 필요합니다.")
        response = input("xdotool을 설치하시겠습니까? (y/n, 기본값: y): ").strip().lower()

        if response in ['', 'y', 'yes']:
            print("  xdotool 설치 중...")
            try:
                subprocess.check_call(["sudo", "apt-get", "update"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "xdotool"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print("  ✓ xdotool 설치 완료")
            except subprocess.CalledProcessError as e:
                print(f"  ✗ xdotool 설치 실패: {e}")
                print("  수동으로 다음 명령을 실행하세요:")
                print("  sudo apt-get update")
                print("  sudo apt-get install -y xdotool")
            except FileNotFoundError:
                print("  ✗ sudo 명령을 찾을 수 없습니다.")
                print("  수동으로 다음 명령을 실행하세요:")
                print("  sudo apt-get update")
                print("  sudo apt-get install -y xdotool")
        else:
            print("  [건너뜀] xdotool 설치를 건너뜁니다.")
            print("  한글 입력 조합이 제대로 작동하지 않을 수 있습니다.")
            print("  나중에 설치하려면: sudo apt-get install xdotool")

    # v1.9.7: InsightFace 사용 (requirements.txt에 포함)
    # dlib/face_recognition은 더 이상 사용하지 않음

    print("\n=== 설치 완료 ===\n")
    print("✅ GARAMe MANAGER v1.9.7 의존성 설치가 완료되었습니다.")
    print("")
    print("📦 설치된 AI 모듈:")
    print("  - InsightFace (얼굴 인식, 99.86% 정확도)")
    print("  - YOLOv11 (PPE 감지, 92.7% mAP50)")
    print("  - gTTS (자연스러운 한국어 음성)")
    print("")
    print("🚀 프로그램 실행:")
    print("  ./run.sh")
    print("")

if __name__ == "__main__":
    check_and_install_all()
