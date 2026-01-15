"""
About 다이얼로그

제품 정보를 표시하는 다이얼로그입니다.
"""

import tkinter as tk
from tkinter import ttk
import os
import socket
import platform
import subprocess
import re


class AboutDialog:
    """About 다이얼로그"""

    def __init__(self, parent, config=None):
        self.parent = parent
        self.config = config
        self.dialog = None

    def _get_eth0_ip(self):
        """eth0 (Linux) 또는 기본 이더넷 인터페이스의 IP 주소 가져오기"""
        try:
            system = platform.system().lower()
            
            if system == 'linux':
                # Linux: eth0 인터페이스의 IP 확인
                try:
                    result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        # ip addr show 출력에서 inet 주소 추출
                        match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if match:
                            return match.group(1)
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    pass
                
                # ip 명령어가 없으면 ifconfig 시도
                try:
                    result = subprocess.run(['ifconfig', 'eth0'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if match:
                            return match.group(1)
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    pass
            
            elif system == 'windows':
                # Windows: 이더넷 어댑터의 IP 확인
                try:
                    result = subprocess.run(['ipconfig'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        # 이더넷 어댑터 또는 Wi-Fi 어댑터의 IPv4 주소 찾기
                        lines = result.stdout.split('\n')
                        in_adapter_section = False
                        for line in lines:
                            if '이더넷 어댑터' in line or 'Ethernet adapter' in line or 'Wi-Fi' in line:
                                in_adapter_section = True
                                continue
                            if in_adapter_section and ('IPv4' in line or 'IP 주소' in line):
                                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                                if match:
                                    ip = match.group(1)
                                    # 로컬호스트 제외
                                    if ip != '127.0.0.1':
                                        return ip
                            if in_adapter_section and line.strip() == '':
                                in_adapter_section = False
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    pass
            
            # 위 방법들이 실패하면 socket을 사용한 기본 방법
            try:
                # 외부 연결을 시도하여 로컬 IP 확인
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                pass
            
        except Exception:
            pass
        
        return None

    def show(self):
        """다이얼로그 표시"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("About")
        self.dialog.geometry("500x580")  # 높이 확장하여 기능 설명이 다 보이도록
        # 배경색은 기본값으로 복구
        bg_color = "#F5F5F5"
        self.dialog.configure(bg=bg_color)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (250)
        y = (self.dialog.winfo_screenheight() // 2) - (290)
        self.dialog.geometry(f"500x580+{x}+{y}")

        # ESC로 닫기
        self.dialog.bind("<Escape>", lambda e: self._close())

        self._create_widgets()

        # 다이얼로그가 닫힐 때까지 대기
        self.dialog.wait_window()

    def _create_widgets(self):
        """위젯 생성"""
        # 메인 프레임 (패딩 축소)
        main_frame = tk.Frame(self.dialog, bg="#F5F5F5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        current_dir = os.path.dirname(__file__)  # src/tcp_monitor/ui
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 프로젝트 루트
        # PyInstaller(one-file) 환경 지원을 위한 경로 보정
        exe_dir = None
        meipass = None
        try:
            import sys
            exe_dir = getattr(sys, '_MEIPASS', None) or os.path.dirname(sys.executable)
            meipass = getattr(sys, '_MEIPASS', None)
        except Exception:
            pass

        # 1. 맨 위에 서버 IP와 포트 출력 (작은 크기)
        server_info = ""
        if self.config:
            try:
                port = self.config.listen.get("port", 9000)
                # 실제 네트워크 인터페이스 IP 가져오기
                actual_ip = self._get_eth0_ip()
                if actual_ip:
                    server_info = f"Server: {actual_ip}:{port}"
                else:
                    # IP를 가져오지 못한 경우 설정 파일의 host 사용
                    host = self.config.listen.get("host", "0.0.0.0")
                    server_info = f"Server: {host}:{port}"
            except Exception:
                server_info = "Server: 0.0.0.0:9000"
        
        if server_info:
            server_label = tk.Label(main_frame, text=server_info,
                                   font=("Pretendard", 9),
                                   bg="#F5F5F5", fg="#95A5A6")
            server_label.pack(anchor="w", pady=(0, 8))  # 간격 축소

        # 2. 제품 로고 출력
        # 제품 로고 경로 탐색: _MEIPASS/assets -> 실행파일 폴더/assets -> 프로젝트/assets
        candidate_logo_paths = []
        if meipass:
            candidate_logo_paths.append(os.path.join(meipass, "assets", "GARAMe.png"))
        if exe_dir:
            candidate_logo_paths.append(os.path.join(exe_dir, "assets", "GARAMe.png"))
        candidate_logo_paths.append(os.path.join(project_root, "assets", "GARAMe.png"))
        product_logo_path = next((p for p in candidate_logo_paths if os.path.exists(p)), None)
        logo_loaded = False

        # 제품 로고 로드
        if product_logo_path and os.path.exists(product_logo_path):
            try:
                from PIL import Image, ImageTk
                logo_img = Image.open(product_logo_path)

                # 원본 이미지의 가로세로 비율 유지하면서 크기 조정
                original_width, original_height = logo_img.size
                aspect_ratio = original_width / original_height

                # 크기를 더 축소 (180 -> 140)
                max_size = 140
                if aspect_ratio > 1:  # 가로가 더 긴 경우
                    new_width = max_size
                    new_height = int(max_size / aspect_ratio)
                else:  # 세로가 더 긴 경우
                    new_height = max_size
                    new_width = int(max_size * aspect_ratio)

                logo_img = logo_img.resize((new_width, new_height), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(main_frame, image=logo_photo, bg="#F5F5F5")
                logo_label.image = logo_photo  # 참조 유지
                logo_label.pack(pady=(0, 8))  # 간격 축소
                logo_loaded = True
            except Exception:
                logo_loaded = False

        # 3. 제품명 (로고 밑에)
        product_label = tk.Label(main_frame, text="GARAMe MANAGER",
                                font=("Pretendard", 18, "bold"),  # 더 축소 (22 -> 18)
                                bg="#F5F5F5", fg="#2C3E50")
        product_label.pack(pady=(0, 3))  # 간격 축소

        # 4. 버전 및 빌드 정보: VERSION.txt와 BUILD.txt에서 읽기 (제품명 밑에)
        version_text = "Version"
        build_text = ""
        try:
            # VERSION.txt 경로 탐색: _MEIPASS -> 실행파일 폴더 -> 프로젝트 루트
            candidate_version_paths = []
            if meipass:
                candidate_version_paths.append(os.path.join(meipass, "VERSION.txt"))
            if exe_dir:
                candidate_version_paths.append(os.path.join(exe_dir, "VERSION.txt"))
            candidate_version_paths.append(os.path.join(project_root, "VERSION.txt"))

            version_file = next((p for p in candidate_version_paths if os.path.exists(p)), None)
            if version_file:
                with open(version_file, 'r', encoding='utf-8') as vf:
                    ver = vf.read().strip()
                    if ver:
                        version_text = f"Version {ver}"
        except Exception:
            pass

        # 현재 성능 모드 읽기
        performance_mode = 2  # 기본값
        mode_names = {1: "기본 모드", 2: "표준 모드", 3: "고급 모드"}
        try:
            if self.config:
                performance_mode = int(self.config.env.get('performance_mode', 2))
        except Exception:
            pass

        # 버전 라벨
        version_label = tk.Label(main_frame, text=version_text,
                                font=("Pretendard", 11),  # 더 축소 (13 -> 11)
                                bg="#F5F5F5", fg="#7F8C8D")
        version_label.pack(pady=(0, 2))

        # 성능 모드 라벨 (build 대신 표시)
        mode_name = mode_names.get(performance_mode, "표준 모드")
        mode_label = tk.Label(main_frame, text=f"성능 모드: {mode_name} (모드 {performance_mode})",
                              font=("Pretendard", 10),
                              bg="#F5F5F5", fg="#3498DB")
        mode_label.pack(pady=(0, 10))

        # Copyright 정보 (제작사 제거)
        copyright_label = tk.Label(main_frame, text="Copyright © 2025 가람이엔지(주). All rights reserved.",
                                  font=("Pretendard", 10),  # 더 축소 (11 -> 10)
                                  bg="#F5F5F5", fg="#7F8C8D")
        copyright_label.pack(pady=(0, 12))

        # 설명
        description_frame = tk.Frame(main_frame, bg="#F5F5F5")
        description_frame.pack(fill="x", pady=(0, 10))

        desc_text = """GARAMe MANAGER는 산업용 가스 센서 모니터링 시스템입니다.
실시간 센서 데이터 수집, 분석 및 안전 교육 기능을 제공합니다.

주요 기능:
• 실시간 센서 데이터 모니터링
• 5단계 경보 시스템
• 안전 교육 및 서명 관리
• 데이터 로깅 및 그래프 분석"""

        desc_label = tk.Label(description_frame, text=desc_text,
                             font=("Pretendard", 10),
                             bg="#F5F5F5", fg="#34495E",
                             justify="left")
        desc_label.pack()

        # 확인 버튼
        button_frame = tk.Frame(main_frame, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=(15, 0))

        ok_btn = tk.Button(button_frame, text="확인",
                          command=self._close,
                          bg="#3498DB", fg="#FFFFFF",
                          font=("Pretendard", 12, "bold"),
                          relief="raised", bd=2, width=10, height=1,
                          activebackground="#2980B9", activeforeground="#FFFFFF")
        ok_btn.pack(ipady=5)

    def _close(self):
        """다이얼로그 닫기"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
