#!/usr/bin/env python3
"""고급 설정 다이얼로그 직접 테스트"""

import sys
sys.path.insert(0, '/home/garam/바탕화면/code/1.9.8.4')

import tkinter as tk
from tkinter import messagebox

# 모의 config 객체
class MockConfig:
    def __init__(self):
        self.camera = {}
    def save(self):
        print("Config saved")

def test_direct():
    """CameraAdvancedSettingsDialog 직접 테스트"""
    root = tk.Tk()
    root.title("테스트 메인")
    root.geometry("400x200")

    def open_advanced():
        print("고급 설정 열기...")
        from src.tcp_monitor.ui.camera_advanced_settings import CameraAdvancedSettingsDialog
        config = MockConfig()
        dialog = CameraAdvancedSettingsDialog(root, config)
        dialog.show()
        print("고급 설정 열림")

    btn = tk.Button(root, text="고급 설정 열기", command=open_advanced, font=("", 14))
    btn.pack(pady=50)

    root.mainloop()

if __name__ == "__main__":
    test_direct()
