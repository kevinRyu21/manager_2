"""
메인 애플리케이션 클래스

전체 애플리케이션의 메인 윈도우와 탭 관리를 담당합니다.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import time
import os
import threading
import subprocess
import psutil
import platform

# Ubuntu Linux 전용 체크
if platform.system() != "Linux":
    print("ERROR: 이 프로그램은 Ubuntu Linux에서만 실행됩니다.")
    print(f"현재 시스템: {platform.system()}")
    import sys
    sys.exit(1)

from ..utils.helpers import SENSOR_KEYS, COLOR_BG, get_base_dir
from ..logging.manager import LogManager
from .panel import SensorPanel
from .about_dialog import AboutDialog
from .. import __version__


class SimpleVirtualKeyboard:
    """간단한 가상 키보드 (Text 및 Entry 위젯용)"""
    
    # 클래스 변수: xdotool 경고 메시지를 한 번만 출력
    _xdotool_warning_shown = False
    
    # 한글 자모 정의
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    # 복합 중성 조합 규칙 (중성 + 중성 -> 복합 중성)
    JUNGSUNG_COMBINATIONS = {
        ('ㅗ', 'ㅏ'): 'ㅘ',  # ㅗ + ㅏ = ㅘ
        ('ㅗ', 'ㅐ'): 'ㅙ',  # ㅗ + ㅐ = ㅙ
        ('ㅗ', 'ㅣ'): 'ㅚ',  # ㅗ + ㅣ = ㅚ
        ('ㅜ', 'ㅓ'): 'ㅝ',  # ㅜ + ㅓ = ㅝ
        ('ㅜ', 'ㅔ'): 'ㅞ',  # ㅜ + ㅔ = ㅞ
        ('ㅜ', 'ㅣ'): 'ㅟ',  # ㅜ + ㅣ = ㅟ
        ('ㅡ', 'ㅣ'): 'ㅢ',  # ㅡ + ㅣ = ㅢ
    }

    # 복합 종성 조합 규칙 (종성 + 자음 -> 복합 종성)
    JONGSUNG_COMBINATIONS = {
        ('ㄱ', 'ㅅ'): 'ㄳ',  # ㄱ + ㅅ = ㄳ
        ('ㄴ', 'ㅈ'): 'ㄵ',  # ㄴ + ㅈ = ㄵ
        ('ㄴ', 'ㅎ'): 'ㄶ',  # ㄴ + ㅎ = ㄶ
        ('ㄹ', 'ㄱ'): 'ㄺ',  # ㄹ + ㄱ = ㄺ
        ('ㄹ', 'ㅁ'): 'ㄻ',  # ㄹ + ㅁ = ㄻ
        ('ㄹ', 'ㅂ'): 'ㄼ',  # ㄹ + ㅂ = ㄼ
        ('ㄹ', 'ㅅ'): 'ㄽ',  # ㄹ + ㅅ = ㄽ
        ('ㄹ', 'ㅌ'): 'ㄾ',  # ㄹ + ㅌ = ㄾ
        ('ㄹ', 'ㅍ'): 'ㄿ',  # ㄹ + ㅍ = ㄿ
        ('ㄹ', 'ㅎ'): 'ㅀ',  # ㄹ + ㅎ = ㅀ
        ('ㅂ', 'ㅅ'): 'ㅄ',  # ㅂ + ㅅ = ㅄ
    }
    
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.keyboard_frame = None
        self.is_visible = False
        
        # 위젯 타입 확인 (Text 또는 Entry)
        self.is_entry_widget = isinstance(text_widget, tk.Entry)
        
        # 한글/영문 모드 (True: 한글, False: 영문)
        self.is_korean = False
        
        # 한글 조합 상태 (초성/중성/종성 인덱스; -1이면 없음)
        self.cho_idx = -1
        self.jung_idx = -1
        self.jong_idx = -1
        
        # 조합 중인 문자의 화면 위치 추적 (None이면 화면에 표시되지 않음)
        self.composition_start_pos = None
        
        # 한글 자모 인덱스 매핑 (키보드에 표시된 자모 -> 인덱스)
        self.chosung_index = {ch: i for i, ch in enumerate(self.CHOSUNG_LIST)}
        self.jungsung_index = {ch: i for i, ch in enumerate(self.JUNGSUNG_LIST)}
        self.jongsung_index = {ch: i for i, ch in enumerate(self.JONGSUNG_LIST) if ch}
        
    def show(self):
        """키보드 표시 (항상 표시하도록 수정)"""
        if not self.is_visible:
            self._create_keyboard()
            self.is_visible = True
            
    def hide(self):
        """키보드 숨기기"""
        if self.keyboard_frame:
            self.keyboard_frame.pack_forget()
            self.is_visible = False
            
    def _create_keyboard(self):
        """키보드 UI 생성"""
        if self.keyboard_frame:
            self.keyboard_frame.pack_forget()
            
        # 키보드 프레임 (parent는 input_frame)
        self.keyboard_frame = tk.Frame(self.parent, bg="#E8E8E8", relief="raised", bd=2)
        
        # 키보드 프레임을 parent (input_frame)에 배치
        # text_widget 아래에 배치하기 위해 text_widget 다음에 pack
        self.keyboard_frame.pack(fill="x", padx=0, pady=(0, 10))
        
        # 모드 표시 및 전환 버튼
        mode_frame = tk.Frame(self.keyboard_frame, bg="#E8E8E8")
        mode_frame.pack(fill="x", padx=5, pady=2)
        
        mode_btn = tk.Button(mode_frame, text="한/영" if self.is_korean else "ENG",
                           command=self._toggle_language,
                           font=("Pretendard", 10, "bold"),
                           bg="#3498DB", fg="#FFFFFF",
                           width=8, height=1)
        mode_btn.pack(side="left", padx=2)
        
        # 닫기 버튼 제거 (항상 표시되도록)
        # 키보드 레이아웃 (영문 QWERTY 스타일)
        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/'],
            ['Space', 'Backspace', 'Enter']
        ]
        
        # 한글 키보드 레이아웃 (2벌식)
        korean_rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
            ['ㅂ', 'ㅈ', 'ㄷ', 'ㄱ', 'ㅅ', 'ㅛ', 'ㅕ', 'ㅑ', 'ㅐ', 'ㅔ', '[', ']'],
            ['ㅁ', 'ㄴ', 'ㅇ', 'ㄹ', 'ㅎ', 'ㅗ', 'ㅓ', 'ㅏ', 'ㅣ', ';', "'"],
            ['ㅋ', 'ㅌ', 'ㅊ', 'ㅍ', 'ㅠ', 'ㅜ', 'ㅡ', ',', '.', '/'],
            ['Space', 'Backspace', 'Enter']
        ]
        
        current_rows = korean_rows if self.is_korean else rows
        
        for row_keys in current_rows:
            row_frame = tk.Frame(self.keyboard_frame, bg="#E8E8E8")
            row_frame.pack(fill="x", padx=2, pady=1)
            
            for key in row_keys:
                if key == 'Space':
                    btn = tk.Button(row_frame, text="Space",
                                  command=self._insert_space,
                                  font=("Pretendard", 9),
                                  bg="#FFFFFF", fg="#2C3E50",
                                  width=15, height=2, relief="raised", bd=1)
                elif key == 'Backspace':
                    btn = tk.Button(row_frame, text="⌫ Backspace",
                                  command=self._backspace,
                                  font=("Pretendard", 9),
                                  bg="#E74C3C", fg="#FFFFFF",
                                  width=12, height=2, relief="raised", bd=1)
                elif key == 'Enter':
                    btn = tk.Button(row_frame, text="↵ Enter",
                                  command=self._insert_newline,
                                  font=("Pretendard", 9),
                                  bg="#27AE60", fg="#FFFFFF",
                                  width=12, height=2, relief="raised", bd=1)
                else:
                    # 대문자로 표시
                    display_key = key.upper() if len(key) == 1 and key.isalpha() else key
                    btn = tk.Button(row_frame, text=display_key,
                                  command=lambda k=key: self._insert_char(k),
                                  font=("Pretendard", 10),
                                  bg="#FFFFFF", fg="#2C3E50",
                                  width=4, height=2, relief="raised", bd=1,
                                  activebackground="#ECF0F1")
                
                btn.pack(side="left", padx=1, pady=1)
                
    def _toggle_language(self):
        """한글/영문 모드 전환"""
        # 모드 전환 시 현재 조합 중인 한글 완성
        if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
            self._commit_current_composition()
        # 조합 상태 완전 초기화
        self.cho_idx = -1
        self.jung_idx = -1
        self.jong_idx = -1
        self.composition_start_pos = None
        self.is_korean = not self.is_korean
        self._create_keyboard()
        
    def _get_current_composition_char(self):
        """현재 조합 상태를 한글 문자로 계산 (화면 표시용)"""
        if self.cho_idx == -1 and self.jung_idx == -1 and self.jong_idx == -1:
            return None
        
        if self.jung_idx == -1:
            # 중성이 없으면 초성만 반환
            if self.cho_idx != -1:
                return self.CHOSUNG_LIST[self.cho_idx]
            return None
        
        # 완성형 한글 계산
        base = 0xAC00
        cho = self.cho_idx if self.cho_idx != -1 else 11  # 기본값: ㅇ
        jung = self.jung_idx
        jong = self.jong_idx if self.jong_idx != -1 else 0
        
        syllable = chr(base + (cho * 21 + jung) * 28 + jong)
        return syllable
    
    def _update_composition_display(self):
        """조합 중인 한글을 화면에 실시간으로 표시"""
        try:
            current_char = self._get_current_composition_char()
            
            if current_char is None:
                # 조합 중인 문자가 없으면 화면에서 제거
                if self.composition_start_pos is not None:
                    try:
                        current_pos = self.text_widget.index(tk.INSERT)
                        # Entry 위젯은 compare()가 없으므로 숫자 비교 사용
                        if self.is_entry_widget:
                            if self.composition_start_pos <= current_pos:
                                self.text_widget.delete(self.composition_start_pos, current_pos)
                        else:
                            if self.text_widget.compare(self.composition_start_pos, "<=", current_pos):
                                self.text_widget.delete(self.composition_start_pos, current_pos)
                    except:
                        pass
                    self.composition_start_pos = None
                return
            
            # 조합 중인 문자가 있으면 화면에 표시/업데이트
            current_pos = self.text_widget.index(tk.INSERT)
            
            if self.composition_start_pos is None:
                # 처음 조합 시작: 커서 위치에 삽입
                self.composition_start_pos = current_pos
                self.text_widget.insert(tk.INSERT, current_char)
            else:
                # 기존 조합 업데이트: 이전 문자 삭제하고 새 문자 삽입
                try:
                    # 조합 시작 위치가 유효한지 확인
                    if self.is_entry_widget:
                        # Entry 위젯: 숫자 비교
                        if self.composition_start_pos <= current_pos:
                            self.text_widget.delete(self.composition_start_pos, current_pos)
                            new_pos = self.text_widget.index(tk.INSERT)
                            self.text_widget.insert(new_pos, current_char)
                    else:
                        # Text 위젯: compare() 메서드 사용
                        if self.text_widget.compare(self.composition_start_pos, "<=", current_pos):
                            self.text_widget.delete(self.composition_start_pos, current_pos)
                            new_pos = self.text_widget.index(tk.INSERT)
                            self.text_widget.insert(new_pos, current_char)
                except:
                    # 오류 발생 시 재시작
                    self.composition_start_pos = current_pos
                    self.text_widget.insert(tk.INSERT, current_char)
        except Exception as e:
            print(f"조합 표시 업데이트 오류: {e}")
    
    def _commit_current_composition(self):
        """현재 조합 중인 한글 글자를 완성하여 삽입"""
        # 조합 중인 문자가 이미 화면에 표시되어 있으므로 삭제하고 완성된 문자를 삽입
        try:
            if self.composition_start_pos is not None:
                current_pos = self.text_widget.index(tk.INSERT)
                # Entry 위젯은 compare()가 없으므로 숫자 비교 사용
                if self.is_entry_widget:
                    if self.composition_start_pos <= current_pos:
                        self.text_widget.delete(self.composition_start_pos, current_pos)
                else:
                    if self.text_widget.compare(self.composition_start_pos, "<=", current_pos):
                        self.text_widget.delete(self.composition_start_pos, current_pos)
                self.composition_start_pos = None
        except:
            pass
        
        current_char = self._get_current_composition_char()
        if current_char:
            self.text_widget.insert(tk.INSERT, current_char)
        
        # 조합 상태 초기화
        self.cho_idx = -1
        self.jung_idx = -1
        self.jong_idx = -1
    
    def _insert_char(self, char):
        """문자 삽입 (한글 조합 지원)"""
        try:
            # 포커스가 Text 위젯에 있도록 보장
            self.text_widget.focus_set()
            self.text_widget.update_idletasks()
            
            # 한글 자모인지 확인 (한글 자모 범위: U+3131-U+318E)
            is_korean_jamo = False
            if len(char) == 1:
                char_code = ord(char)
                is_korean_jamo = (0x3131 <= char_code <= 0x318E)
            
            # 한글 모드이고 한글 자모인 경우: 한글 조합 처리
            if self.is_korean and is_korean_jamo:
                # 자음인지 모음인지 확인
                if char in self.chosung_index or char in self.jongsung_index:
                    # 자음 입력
                    if self.jung_idx == -1:
                        # 아직 중성이 없음: 초성 설정/교체
                        self.cho_idx = self.chosung_index.get(char, self.cho_idx)
                        self._update_composition_display()  # 화면 업데이트
                    else:
                        # 중성이 있음: 종성 설정 또는 다음 음절로 넘김
                        if self.jong_idx == -1:
                            # 종성이 없음: 종성 설정 시도
                            if char in self.jongsung_index:
                                self.jong_idx = self.jongsung_index[char]
                                self._update_composition_display()  # 화면 업데이트
                            else:
                                # 종성으로 사용할 수 없는 자음이면 이전 글자 완성하고 새 초성으로 시작
                                self._commit_current_composition()
                                self.cho_idx = self.chosung_index.get(char, -1)
                                self._update_composition_display()  # 화면 업데이트
                        else:
                            # 이미 종성이 있음: 복합 종성 조합 시도
                            current_jong = self.JONGSUNG_LIST[self.jong_idx]
                            compound_key = (current_jong, char)
                            if compound_key in self.JONGSUNG_COMBINATIONS:
                                # 복합 종성 조합 가능
                                compound_jong = self.JONGSUNG_COMBINATIONS[compound_key]
                                self.jong_idx = self.jongsung_index[compound_jong]
                                self._update_composition_display()  # 화면 업데이트
                            else:
                                # 복합 종성 조합 불가능: 이전 글자 완성하고 새 초성으로 시작
                                self._commit_current_composition()
                                self.cho_idx = self.chosung_index.get(char, -1)
                                self._update_composition_display()  # 화면 업데이트
                elif char in self.jungsung_index:
                    # 모음 입력
                    if self.jung_idx == -1:
                        # 중성이 아직 없음
                        if self.cho_idx == -1:
                            # 초성도 없음: ㅇ을 기본 초성으로 설정
                            self.cho_idx = 11  # ㅇ의 인덱스
                        # 중성 설정
                        self.jung_idx = self.jungsung_index[char]
                        self._update_composition_display()  # 화면 업데이트
                    else:
                        # 이미 중성이 있음: 복합 중성 조합 시도
                        current_jung = self.JUNGSUNG_LIST[self.jung_idx]
                        compound_key = (current_jung, char)
                        if compound_key in self.JUNGSUNG_COMBINATIONS:
                            # 복합 중성 조합 가능 (예: ㅗ + ㅏ = ㅘ)
                            compound_jung = self.JUNGSUNG_COMBINATIONS[compound_key]
                            self.jung_idx = self.jungsung_index[compound_jung]
                            self._update_composition_display()  # 화면 업데이트
                        else:
                            # 복합 중성 조합 불가능: 이전 글자 완성하고 새 모음으로 시작
                            self._commit_current_composition()
                            self.cho_idx = 11  # ㅇ의 인덱스
                            self.jung_idx = self.jungsung_index[char]
                            self._update_composition_display()  # 화면 업데이트
                else:
                    # 한글 자모가 아니거나 매핑되지 않은 경우: 이전 글자 완성하고 직접 삽입
                    self._commit_current_composition()
                    self.text_widget.insert(tk.INSERT, char)
            else:
                # 영문 모드이거나 영문/숫자/특수문자인 경우: 이전 한글 조합 완성하고 직접 삽입
                if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
                    self._commit_current_composition()
                self.text_widget.insert(tk.INSERT, char)
        except Exception as e:
            print(f"문자 삽입 오류: {e}")
            # 오류 발생 시 조합 상태 초기화
            self.cho_idx = -1
            self.jung_idx = -1
            self.jong_idx = -1
            self.composition_start_pos = None
            # 최종 폴백: 직접 삽입
            try:
                self.text_widget.insert(tk.INSERT, char)
            except:
                pass
            
    def _insert_space(self):
        """스페이스 삽입 (한글 조합 완성 후 삽입)"""
        # 한글 조합 중이면 먼저 완성
        if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
            self._commit_current_composition()
        # 스페이스 삽입
        self.text_widget.insert(tk.INSERT, ' ')
            
    def _backspace(self):
        """백스페이스 (한글 조합 상태도 고려, 복합 자모 분해 지원)"""
        try:
            self.text_widget.focus_set()
            self.text_widget.update_idletasks()

            # 한글 조합 중인 경우: 조합 상태만 수정하고 화면 업데이트
            if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
                if self.jong_idx != -1:
                    # 종성이 있으면: 복합 종성인지 확인하고 분해 또는 제거
                    current_jong = self.JONGSUNG_LIST[self.jong_idx]
                    # 복합 종성을 단일 종성으로 분해
                    decomposed = None
                    for (base, add), compound in self.JONGSUNG_COMBINATIONS.items():
                        if compound == current_jong:
                            decomposed = base
                            break

                    if decomposed:
                        # 복합 종성을 기본 종성으로 분해
                        self.jong_idx = self.jongsung_index[decomposed]
                    else:
                        # 단일 종성이면 제거
                        self.jong_idx = -1
                    self._update_composition_display()
                    return
                elif self.jung_idx != -1:
                    # 중성이 있으면: 복합 중성인지 확인하고 분해 또는 제거
                    current_jung = self.JUNGSUNG_LIST[self.jung_idx]
                    # 복합 중성을 단일 중성으로 분해
                    decomposed = None
                    for (base, add), compound in self.JUNGSUNG_COMBINATIONS.items():
                        if compound == current_jung:
                            decomposed = base
                            break

                    if decomposed:
                        # 복합 중성을 기본 중성으로 분해
                        self.jung_idx = self.jungsung_index[decomposed]
                        self._update_composition_display()
                        return
                    else:
                        # 단일 중성이면 제거
                        self.jung_idx = -1
                        # 초성이 ㅇ이고 중성만 있었던 경우, 초성도 제거
                        if self.cho_idx == 11:  # ㅇ의 인덱스
                            self.cho_idx = -1
                            if self.composition_start_pos is not None:
                                try:
                                    current_pos = self.text_widget.index(tk.INSERT)
                                    if self.is_entry_widget:
                                        if self.composition_start_pos <= current_pos:
                                            self.text_widget.delete(self.composition_start_pos, current_pos)
                                    else:
                                        if self.text_widget.compare(self.composition_start_pos, "<=", current_pos):
                                            self.text_widget.delete(self.composition_start_pos, current_pos)
                                except:
                                    pass
                                self.composition_start_pos = None
                            return
                        self._update_composition_display()
                        return
                elif self.cho_idx != -1:
                    # 초성만 있으면 초성 제거하고 화면에서도 제거
                    self.cho_idx = -1
                    if self.composition_start_pos is not None:
                        try:
                            current_pos = self.text_widget.index(tk.INSERT)
                            # Entry 위젯은 compare()가 없으므로 숫자 비교 사용
                            if self.is_entry_widget:
                                if self.composition_start_pos <= current_pos:
                                    self.text_widget.delete(self.composition_start_pos, current_pos)
                            else:
                                if self.text_widget.compare(self.composition_start_pos, "<=", current_pos):
                                    self.text_widget.delete(self.composition_start_pos, current_pos)
                        except:
                            pass
                        self.composition_start_pos = None
                    return

            # 조합 중이 아니면 실제 문자 삭제
            cursor_pos = self.text_widget.index(tk.INSERT)
            # Entry 위젯은 숫자, Text 위젯은 문자열 인덱스 사용
            if self.is_entry_widget:
                if cursor_pos > 0:
                    prev_pos = cursor_pos - 1
                    self.text_widget.delete(prev_pos, cursor_pos)
            else:
                if cursor_pos != "1.0":
                    prev_pos = self.text_widget.index(f"{cursor_pos} -1c")
                    self.text_widget.delete(prev_pos, cursor_pos)
        except Exception as e:
            print(f"백스페이스 오류: {e}")
            # 오류 발생 시 조합 상태 초기화
            self.cho_idx = -1
            self.jung_idx = -1
            self.jong_idx = -1
            self.composition_start_pos = None
            try:
                cursor_pos = self.text_widget.index(tk.INSERT)
                if self.is_entry_widget:
                    if cursor_pos > 0:
                        prev_pos = cursor_pos - 1
                        self.text_widget.delete(prev_pos, cursor_pos)
                else:
                    if cursor_pos != "1.0":
                        prev_pos = self.text_widget.index(f"{cursor_pos} -1c")
                        self.text_widget.delete(prev_pos, cursor_pos)
            except:
                pass
            
    def _insert_newline(self):
        """줄바꿈 삽입 (한글 조합 완성 후 삽입)"""
        try:
            self.text_widget.focus_set()
            self.text_widget.update_idletasks()

            # 한글 조합 중이면 먼저 완성
            if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
                self._commit_current_composition()

            # Entry 위젯은 줄바꿈 불가능하므로 건너뜀
            if self.is_entry_widget:
                return

            # Text 위젯에만 줄바꿈 삽입
            self.text_widget.insert(tk.INSERT, '\n')
        except Exception as e:
            print(f"줄바꿈 삽입 오류: {e}")
            try:
                if not self.is_entry_widget:
                    self.text_widget.insert(tk.INSERT, '\n')
            except:
                pass


class App(tk.Tk):
    """메인 애플리케이션 클래스"""

    def __init__(self, cfg):
        super().__init__()

        # 빌드 번호 포함한 타이틀 설정
        try:
            from ..utils.build_info import get_build_info
            build_info = get_build_info()
            self.title(f"GARAMe MANAGER v{__version__} (Build {build_info.build})")
        except Exception:
            self.title(f"GARAMe MANAGER v{__version__}")

        self.geometry("1600x900")
        self.configure(bg=COLOR_BG)
        self.cfg = cfg

        # 전역 스피커(TTS) 상태 - 패널 재생성 시에도 유지됨
        self.global_voice_alert_enabled = True

        # 시작 시 전체화면으로 실행
        self._is_fullscreen = True
        try:
            self.attributes("-fullscreen", True)
            self.attributes("-topmost", True)
            # 최상단 포커스 설정
            self.lift()
            self.focus_force()
        except Exception:
            # 일부 플랫폼에서는 fullscreen이 지원되지 않음
            try:
                self.state("zoomed")
                self.lift()
                self.focus_force()
            except Exception:
                pass

        # 매니저 창이 항상 포커스를 유지하도록 주기적으로 확인
        self.after(1000, self._ensure_focus)

        # 런타임 폰트 스케일 변수 (초기값을 config에서 로드)
        try:
            init_tile = float(self.cfg.ui.get("tile_scale", "0.55"))
        except Exception:
            init_tile = 0.55
        try:
            init_header = float(self.cfg.ui.get("header_scale", "2.0"))
        except Exception:
            init_header = 2.0
        try:
            init_status = float(self.cfg.ui.get("status_text_scale", "0.8"))
        except Exception:
            init_status = 0.8
        self.tile_scale = tk.DoubleVar(value=init_tile)  # 0.5 ~ 2.0
        self.header_scale = tk.DoubleVar(value=init_header)  # 0.5 ~ 2.0
        self.status_text_scale = tk.DoubleVar(value=init_status)  # 0.5 ~ 0.9

        # 탭 스타일 설정 (완전히 새로운 접근)
        style = ttk.Style()
        
        # 모든 가능한 테마 시도
        themes = ['clam', 'alt', 'default', 'classic']
        for theme in themes:
            try:
                style.theme_use(theme)
                break
            except:
                continue
        
        # 탭 기본 설정 및 여백/테두리/마진 고정
        style.configure("TNotebook", tabposition="n", tabmargins=[0, 0, 0, 0])
        # 탭 높이/패딩을 고정하여 선택 시에도 크기 변동 없게 유지
        style.configure("TNotebook.Tab",
                       padding=[20, 12],
                       font=("Arial", 12, "bold"),
                       borderwidth=0,
                       focuscolor="",
                       lightcolor="",
                       darkcolor="")

        # 강제 색상 설정 (배경은 항상 흰색 고정, 전경만 상태에 따라 변동)
        style.configure("TNotebook.Tab",
                       background="white",
                       foreground="#2C3E50")

        # 선택 상태에서도 패딩/테두리 동일 유지, 전경색만 변경 (선택: 파랑, 비선택: 진회색)
        try:
            style.map("TNotebook.Tab",
                     background=[("selected", "white"), ("active", "white")],
                     foreground=[("selected", "#1976D2"), ("!selected", "#2C3E50"), ("active", "#2C3E50")],
                     bordercolor=[("selected", ""), ("!selected", "")],
                     lightcolor=[("selected", ""), ("!selected", "")],
                     darkcolor=[("selected", ""), ("!selected", "")],
                     focuscolor=[("selected", ""), ("!selected", "")],
                     padding=[("selected", [20, 12]), ("!selected", [20, 12])])
        except Exception:
            # 일부 테마에서는 map에 padding이 지원되지 않음
            style.map("TNotebook.Tab",
                     background=[("selected", "white"), ("active", "white")],
                     foreground=[("selected", "#1976D2"), ("!selected", "#2C3E50"), ("active", "#2C3E50")])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        # 탭 변경 시 외관 갱신
        try:
            self.nb.bind('<<NotebookTabChanged>>', lambda e: self._refresh_all_tabs())
        except Exception:
            pass

        # 탭 좌클릭 - ✕ 영역 클릭 시 탭 닫기
        self.nb.bind("<Button-1>", self._on_tab_click)
        # 탭 우클릭으로 닫기 (연결 끊김 탭만)
        self.nb.bind("<Button-3>", self._on_tab_right_click)
        # 탭 중클릭(휠 클릭)으로 닫기
        self.nb.bind("<Button-2>", self._on_tab_middle_click)

        # 개요 패널 제거됨

        # 메뉴바 크기 설정 (터치하기 쉽게 확대)
        self.menubar = tk.Menu(self, font=("Pretendard", 16, "bold"))
        self.menu_cfg = tk.Menu(self.menubar, tearoff=0, font=("Pretendard", 14))

        # 초기 메뉴 설정
        self._setup_menu()

        self.menubar.add_cascade(label="설정", menu=self.menu_cfg)

        # 보기 메뉴 설정
        self.menu_view = tk.Menu(self.menubar, tearoff=0, font=("Pretendard", 14))
        self._setup_view_menu()
        self.menubar.add_cascade(label="보기", menu=self.menu_view)

        self.config(menu=self.menubar)
        # X 버튼 클릭 시에도 정상 종료 핸들러 연결
        try:
            self.protocol("WM_DELETE_WINDOW", self._handle_window_close)
        except Exception:
            pass

        # 단축키 - 전체화면 토글 제거, 항상 전체화면 유지
        # self.bind("<F11>", lambda e: self._handle_fullscreen_toggle())  # 제거
        # self.bind("<Escape>", lambda e: self._handle_escape())  # 제거
        self.bind("<F10>", lambda e: self._handle_exit())

        # 헬스체크: 매니저 하트비트 시작
        try:
            self._heartbeat_running = True
            self._heartbeat_file = os.path.join(get_base_dir(), "manager_heartbeat.signal")
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
        except Exception:
            pass
        
        # 윈도우 최소화 이벤트 처리
        self.bind("<Unmap>", lambda e: self._handle_minimize())

        self.panels = {}
        self.states = {}
        self.tab_alert_states = {}  # 탭별 알림 상태 저장
        self.logs = LogManager(
            base_dir=os.getcwd(),
            server_host=self.cfg.listen["host"],
            server_port=self.cfg.listen["port"],
            config=self.cfg
        )
        self.logs.write_run("app started")

        # 오늘 경고 목록 (메모리, 패널별 집계)
        from collections import defaultdict
        self._today_alerts_by_key = defaultdict(list)  # key: panel key (sid@ip)
        
        # 센서 데이터 검증 상태 추적 (패널별, 센서별)
        # 구조: {panel_key: {sensor_key: {'first_value': bool, 'negative_count': int, 'last_negative_value': float}}}
        self._sensor_validation_states = {}

        # 탭 깜빡임 상태 토글러 시작
        self._blink_on = False
        try:
            self.after(600, self._blink_tick)
        except Exception:
            pass

        # 초기 대기 패널 생성 (데이터 수신 전에도 화면 표시)
        self._create_initial_waiting_panel()
        # 초기 탭 외관 갱신
        self.after(200, self._refresh_all_tabs)

        # 시스템 메시지 박스 차단/자동 처리 패치
        try:
            self._patch_messagebox()
        except Exception:
            pass

        # 알 수 없는 시스템 Toplevel 자동 차단/닫기 루프 시작
        try:
            self.after(800, self._suppress_system_toplevels)
        except Exception:
            pass

    def _patch_messagebox(self):
        """전역 messagebox를 차단하거나 자동 응답으로 대체"""
        try:
            import tkinter.messagebox as mb
        except Exception:
            return

        def _log(msg):
            try:
                self.logs.write_run(f"messagebox_suppressed: {msg}")
            except Exception:
                pass

        # 정보/경고/오류: 표시 차단
        def _showinfo(title, message, **kwargs):
            _log(f"info:{title}:{message}")
            return None

        def _showwarning(title, message, **kwargs):
            _log(f"warning:{title}:{message}")
            return None

        def _showerror(title, message, **kwargs):
            _log(f"error:{title}:{message}")
            return None

        # 확인/취소 류: 기본 긍정으로 자동 응답
        # 단, 종료 확인 다이얼로그는 예외 처리 (정상 작동하도록)
        def _askyesno(title, message, **kwargs):
            # 종료 확인 다이얼로그는 원래 동작 사용
            if title and ("종료" in str(title) or "종료" in str(message)):
                try:
                    import tkinter.messagebox as original_mb
                    return original_mb._show(title, message, original_mb.QUESTION, original_mb.YESNO, **kwargs) == original_mb.YES
                except Exception:
                    _log(f"askyesno (original):{title}:{message}")
                    return False
            _log(f"askyesno:{title}:{message} -> True")
            return True

        # 원본 함수 백업 (패치 전)
        _original_askokcancel = mb.askokcancel
        
        def _askokcancel(title, message, **kwargs):
            # 종료 확인 다이얼로그는 원본 함수 사용
            if title and ("종료" in str(title) or "종료" in str(message)):
                # 원본 함수 직접 호출
                try:
                    return _original_askokcancel(title, message, **kwargs)
                except Exception as e:
                    _log(f"askokcancel (original failed):{title}:{message}: {e}")
                    return False
            _log(f"askokcancel:{title}:{message} -> True")
            return True

        def _askretrycancel(title, message, **kwargs):
            _log(f"askretrycancel:{title}:{message} -> True")
            return True

        def _askquestion(title, message, **kwargs):
            _log(f"askquestion:{title}:{message} -> 'yes'")
            return 'yes'

        mb.showinfo = _showinfo
        mb.showwarning = _showwarning
        mb.showerror = _showerror
        mb.askyesno = _askyesno
        mb.askokcancel = _askokcancel
        mb.askretrycancel = _askretrycancel
        mb.askquestion = _askquestion

    def _suppress_system_toplevels(self):
        """시스템에서 뜨는 불필요한 Toplevel(예: 'toplevel', '방금')을 자동 닫기"""
        try:
            suspicious_keywords = ["toplevel", "방금"]
            for w in self.winfo_children():
                try:
                    if str(w.winfo_class()).lower() == 'toplevel':
                        title = ""
                        try:
                            title = (w.title() or "").strip()
                        except Exception:
                            title = ""
                        low = title.lower()
                        if any(k in low for k in suspicious_keywords) or any(k in title for k in suspicious_keywords):
                            try:
                                w.destroy()
                            except Exception:
                                pass
                except Exception:
                    continue
        except Exception:
            pass
        # 주기적으로 반복 실행
        try:
            self.after(1000, self._suppress_system_toplevels)
        except Exception:
            pass

    def _validate_and_filter_data(self, panel_key, data):
        """센서 데이터 검증 및 필터링
        - 최초에 오는 -1 값 무시
        - 0 이하 값이 3회 이상 연속으로 같은 값이 올 때만 수용
        """
        if not data:
            return data
        
        # 패널별 검증 상태 초기화 (없으면)
        if panel_key not in self._sensor_validation_states:
            self._sensor_validation_states[panel_key] = {}
        
        validation_state = self._sensor_validation_states[panel_key]
        filtered_data = {}
        
        for sensor_key, value in data.items():
            if sensor_key not in SENSOR_KEYS:
                # 센서 키가 아니면 그대로 통과
                filtered_data[sensor_key] = value
                continue
            
            # 센서별 검증 상태 초기화 (없으면)
            if sensor_key not in validation_state:
                validation_state[sensor_key] = {
                    'first_value': True,  # 첫 번째 값 여부
                    'negative_count': 0,  # 연속된 음수/0 값 카운트
                    'last_negative_value': None  # 마지막 음수/0 값
                }
            
            sensor_state = validation_state[sensor_key]
            
            try:
                val = float(value)
            except (ValueError, TypeError):
                # 숫자로 변환 불가능한 값은 무시
                continue
            
            # 1. 최초에 오는 -1 값 무시
            if sensor_state['first_value']:
                if val == -1:
                    # 첫 번째 값이 -1이면 무시
                    continue
                else:
                    # 첫 번째 유효 값이면 first_value를 False로 설정
                    sensor_state['first_value'] = False
                    filtered_data[sensor_key] = value
                    # 음수 카운트 초기화
                    sensor_state['negative_count'] = 0
                    sensor_state['last_negative_value'] = None
                continue
            
            # 2. 정상 값 (0보다 큰 값)은 항상 수용
            if val > 0:
                filtered_data[sensor_key] = value
                # 음수 카운트 초기화
                sensor_state['negative_count'] = 0
                sensor_state['last_negative_value'] = None
                continue
            
            # 3. 0 이하 값 처리
            if val <= 0:
                # 온도는 음수 가능하므로 예외 처리
                if sensor_key == "temperature" and val >= -100:
                    # 온도는 -100 이상이면 정상 값으로 처리
                    filtered_data[sensor_key] = value
                    sensor_state['negative_count'] = 0
                    sensor_state['last_negative_value'] = None
                    continue
                
                # 같은 음수/0 값이 연속으로 오는지 확인
                if sensor_state['last_negative_value'] == val:
                    sensor_state['negative_count'] += 1
                else:
                    # 다른 값이 오면 카운트 리셋
                    sensor_state['negative_count'] = 1
                    sensor_state['last_negative_value'] = val
                
                # 3회 이상 연속으로 같은 값이 오면 수용
                if sensor_state['negative_count'] >= 3:
                    filtered_data[sensor_key] = value
                    # 카운트는 유지 (다음 검증을 위해)
                # 3회 미만이면 무시
                else:
                    continue
            else:
                # 양수 값 (위에서 처리되었지만 안전장치)
                filtered_data[sensor_key] = value
        
        return filtered_data

    def enforce_graph_view_policy(self, trigger_key):
        """그래프 동시 보기 정책 적용: 항상 단일 그래프만 허용, 다른 패널은 타일 보기로 전환"""
        # 항상 단일 그래프만 허용: 트리거 외 다른 그래프를 모두 카드 모드로
        try:
            for key, panel in list(self.panels.items()):
                if key == trigger_key or key == "__waiting__":
                    continue
                try:
                    if hasattr(panel, 'view_mode') and panel.view_mode == "graph":
                        panel.switch_to_card_mode()
                except Exception:
                    continue
        except Exception:
            pass

    def _setup_menu(self):
        """메뉴 설정"""
        # 기존 메뉴 항목들 제거
        try:
            while self.menu_cfg.index("end") is not None:
                self.menu_cfg.delete(0)
        except:
            pass
        
        # 관리자 모드가 아닐 때는 관리자 진입만 표시 (요청사항: 나머지 메뉴 제거)
        if not self.cfg.admin_mode:
            self.menu_cfg.add_command(label="🔑 관리자 모드 진입", command=self.enter_admin_mode)
        else:
            # 관리자 모드일 때는 모든 설정 메뉴 표시
            self.menu_cfg.add_command(label="✏️ 표시 문구 편집", command=self.edit_text)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🚨 5단계 경보 시스템 설정", command=self.edit_alert_settings)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🖼️ 안전 교육 포스터 관리", command=self.manage_safety_posters)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🗺️ 도면 관리", command=self.manage_blueprints)
            self.menu_cfg.add_separator()

            # 얼굴 등록 관리: InsightFace 라이브러리 설치 여부 확인 (v1.9.5)
            try:
                from insightface.app import FaceAnalysis
                face_reg_label = "👤 얼굴 등록 관리"
            except ImportError:
                face_reg_label = "👤 얼굴 등록 관리 (라이브러리 설치 필요)"
            self.menu_cfg.add_command(label=face_reg_label, command=self.manage_face_registration)

            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="📷 카메라 설정", command=self.open_camera_settings)
            self.menu_cfg.add_command(label="🎛️ AI 고급 설정", command=self.open_ai_advanced_settings)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="⚙️ 환경설정", command=self.open_environment_settings)
            self.menu_cfg.add_command(label="🎯 성능 설정", command=self.open_performance_settings)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🔐 관리자 비밀번호 변경", command=self.change_admin_password)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🔄 프로그램 재시작", command=self.restart_app)
            self.menu_cfg.add_separator()
            self.menu_cfg.add_command(label="🔓 관리자 모드 종료", command=self.enter_admin_mode)

        # 타임아웃 설정 (초 단위, 기본 20초 - 센서 간격이 불규칙하거나 네트워크 지연 고려)
        # 센서 접속 타임아웃 (60초 - 기본값)
        try:
            self.connection_timeout = float(self.cfg.ui.get("connection_timeout", "60.0"))
        except Exception:
            self.connection_timeout = 60.0

        self.after(1000, self._status_tick)
        self.after(60*1000, self._minute_tick)
        
        # 탭 색상 강제 적용
        self.after(100, self._force_tab_colors)
        
        # 매니저 프로그램이 항상 최우선 포커스를 유지하도록 주기적 체크
        self.after(500, self._maintain_focus)
        
        # 윈도우 차단 기능 제거됨

    def _setup_view_menu(self):
        """보기 메뉴 설정"""
        # 기존 메뉴 항목들 제거
        try:
            while self.menu_view.index("end") is not None:
                self.menu_view.delete(0)
        except:
            pass

        # 화면 모드 전환 메뉴
        self.menu_view.add_command(label="🪞 거울보기", command=self._view_menu_mirror)
        self.menu_view.add_command(label="📊 타일 보기", command=self._view_menu_tiles)
        self.menu_view.add_command(label="📈 그래프 보기", command=self._view_menu_graph)
        self.menu_view.add_command(label="🗺️ 도면 보기", command=self._view_menu_blueprint)
        self.menu_view.add_separator()

        # 공통 메뉴 항목 (관리자 모드 여부와 무관): 글자 크기 조절
        self.menu_view.add_command(label="🔤 화면 글자 크기 조절...", command=self.edit_display_sizes)
        self.menu_view.add_separator()
        # 요청사항: 일반 모드에서는 안전교육 사진 관리 숨김
        # 기록 반출은 안전교육 사진 관리에 통합됨
        if self.cfg.admin_mode:
            self.menu_view.add_command(label="📷 안전교육 사진 관리", command=self.view_safety_photos)
            self.menu_view.add_command(label="📄 보고서 보기", command=self._show_report_viewer)
            self.menu_view.add_command(label="🔒 무결성 검증", command=self._show_integrity_verification)
            self.menu_view.add_command(label="📉 센서값 통계 검색", command=self._show_sensor_statistics)
        # 캡쳐 파일 관리는 관리자 전용 유지
        if self.cfg.admin_mode:
            self.menu_view.add_command(label="🖼️ 캡쳐 파일 관리", command=self.view_capture_files)
            self.menu_view.add_separator()

        # 전체화면 토글 (관리자 모드에서만 노출, 토글 레이블)
        if self.cfg.admin_mode:
            if self._is_fullscreen:
                self.menu_view.add_command(label="⬜ 전체화면 해제", command=self._handle_fullscreen_toggle)
            else:
                self.menu_view.add_command(label="⬛ 전체화면", command=self._handle_fullscreen_toggle)
            self.menu_view.add_separator()

        self.menu_view.add_command(label="ℹ️ About...", command=self.show_about)

        # 관리자 모드일 때만 종료 메뉴 표시
        if self.cfg.admin_mode:
            self.menu_view.add_separator()
            self.menu_view.add_command(label="🚪 종료 (F10)", command=self._handle_exit)

    def _view_menu_mirror(self):
        """보기 메뉴: 거울보기"""
        try:
            panel = self._get_current_panel()
            if panel:
                # 그래프/도면 모드에서는 거울보기 시작 불가 (끄기만 가능)
                current_view_mode = getattr(panel, 'view_mode', 'card')
                is_mirror_active = hasattr(panel, 'mirror_mode_active') and panel.mirror_mode_active

                if current_view_mode != "card" and not is_mirror_active:
                    messagebox.showinfo("알림", "타일 보기 모드에서만 거울보기를 사용할 수 있습니다.")
                    return

                # 패널에 show_mirror_view 메서드가 있으면 사용
                if hasattr(panel, 'show_mirror_view'):
                    if is_mirror_active:
                        panel.hide_mirror_view()
                    else:
                        panel.show_mirror_view()
                # 헤더의 _toggle_mirror_view 메서드도 지원
                elif hasattr(panel, 'header') and hasattr(panel.header, '_toggle_mirror_view'):
                    panel.header._toggle_mirror_view()
            else:
                messagebox.showinfo("알림", "현재 선택된 센서 패널이 없습니다.")
        except Exception as e:
            print(f"거울보기 전환 오류: {e}")

    def _view_menu_tiles(self):
        """보기 메뉴: 타일 보기"""
        try:
            panel = self._get_current_panel()
            if panel:
                if hasattr(panel, 'switch_to_card_mode'):
                    panel.switch_to_card_mode()
                else:
                    messagebox.showinfo("알림", "타일 보기 기능을 사용할 수 없습니다.")
            else:
                messagebox.showinfo("알림", "현재 선택된 센서 패널이 없습니다.")
        except Exception as e:
            print(f"타일 보기 전환 오류: {e}")

    def _view_menu_graph(self):
        """보기 메뉴: 그래프 보기"""
        try:
            panel = self._get_current_panel()
            if panel:
                if hasattr(panel, 'switch_to_graph_mode'):
                    panel.switch_to_graph_mode()
                else:
                    messagebox.showinfo("알림", "그래프 보기 기능을 사용할 수 없습니다.")
            else:
                messagebox.showinfo("알림", "현재 선택된 센서 패널이 없습니다.")
        except Exception as e:
            print(f"그래프 보기 전환 오류: {e}")

    def _view_menu_blueprint(self):
        """보기 메뉴: 도면 보기"""
        try:
            panel = self._get_current_panel()
            if panel:
                if hasattr(panel, 'switch_to_blueprint_mode'):
                    panel.switch_to_blueprint_mode()
                else:
                    messagebox.showinfo("알림", "도면 보기 기능을 사용할 수 없습니다.")
            else:
                messagebox.showinfo("알림", "현재 선택된 센서 패널이 없습니다.")
        except Exception as e:
            print(f"도면 보기 전환 오류: {e}")

    def _get_current_panel(self):
        """현재 선택된 탭의 패널 가져오기"""
        try:
            selected_tab = self.nb.select()
            if not selected_tab:
                return None

            # 선택된 탭의 프레임에서 SensorPanel 찾기
            tab_frame = self.nametowidget(selected_tab)

            # 프레임의 자식 위젯에서 SensorPanel 찾기
            for child in tab_frame.winfo_children():
                if isinstance(child, SensorPanel):
                    return child

            # self.panels에서 직접 탭과 연결된 패널 찾기
            for key, panel in self.panels.items():
                if hasattr(panel, 'master') and panel.master:
                    # 패널의 부모 프레임이 현재 선택된 탭 프레임인지 확인
                    if str(panel.master) == str(tab_frame):
                        return panel

        except Exception as e:
            print(f"현재 패널 가져오기 오류: {e}")
        return None

    def _create_initial_waiting_panel(self):
        """초기 대기 패널 생성"""
        # 기본 대기 패널 생성 (sid는 "대기중"으로 표시)
        frame = ttk.Frame(self.nb)
        p = SensorPanel(frame, "센서 접속 대기중...", self)
        p.pack(fill="both", expand=True)
        # 대기 탭은 항상 맨 오른쪽(끝)에 위치, (현재/최대) 표기
        wait_title = self._build_waiting_tab_title()
        self.nb.add(frame, text=wait_title)
        # 초기 탭 색상 설정
        try:
            self.nb.tab(0, background="#FFFFFF", foreground="#000000")
        except Exception:
            pass
        self.panels["__waiting__"] = p
        self.states["__waiting__"] = {"peer": "", "last_rx": None}
        # 대기 상태 표시
        p._show_waiting_status()

    def _get_waiting_tab_id(self):
        """Notebook에서 대기 탭의 탭 아이디를 반환 (없으면 None)"""
        try:
            wait_panel = self.panels.get("__waiting__")
            if not wait_panel:
                return None
            for tab_id in self.nb.tabs():
                try:
                    if self.nb.nametowidget(tab_id) == wait_panel.master:
                        return tab_id
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _build_waiting_tab_title(self):
        """대기 탭 제목 생성: '센서 접속 대기중... (cur/max)'"""
        try:
            cur = self._current_panel_count()
        except Exception:
            cur = 0
        try:
            max_s = int(self.cfg.env.get("max_sensors", 4))
        except Exception:
            max_s = 4
        max_s = max(1, min(4, max_s))
        return f"센서 접속 대기중... ({cur}/{max_s})"

    def _update_waiting_tab_title(self):
        """대기 탭이 있으면 (현재/최대) 카운터로 제목 업데이트"""
        try:
            tab_id = self._get_waiting_tab_id()
            if tab_id is None:
                return
            title = self._build_waiting_tab_title()
            self.nb.tab(tab_id, text=title)
        except Exception:
            pass

    def _current_panel_count(self):
        try:
            return len([k for k in self.panels.keys() if k != "__waiting__"])
        except Exception:
            return 0

    def _remove_waiting_panel_if_reached(self):
        """현재 패널 수가 설정한 최대값 이상이면 대기 탭을 제거"""
        try:
            try:
                max_sensors = int(self.cfg.env.get("max_sensors", 4))
            except Exception:
                max_sensors = 4
            max_sensors = max(1, min(4, max_sensors))

            if self._current_panel_count() >= max_sensors and "__waiting__" in self.panels:
                # 탭에서 '접속 대기중' 텍스트 포함된 항목 제거
                try:
                    for tab_id in range(self.nb.index("end")):
                        tab_text = self.nb.tab(tab_id, "text") or ""
                        if ("접속 대기중" in tab_text) or ("대기중" in tab_text):
                            self.nb.forget(tab_id)
                            break
                except Exception:
                    pass
                self.panels.pop("__waiting__", None)
                self.states.pop("__waiting__", None)
            else:
                # 아직 최대에 도달하지 않았으면 카운터만 갱신
                self._update_waiting_tab_title()
        except Exception:
            pass

    def _ensure_waiting_panel_if_needed(self):
        """현재 패널 수가 최대값보다 작고 대기 탭이 없으면 다시 추가"""
        try:
            try:
                max_sensors = int(self.cfg.env.get("max_sensors", 4))
            except Exception:
                max_sensors = 4
            max_sensors = max(1, min(4, max_sensors))

            if self._current_panel_count() < max_sensors and "__waiting__" not in self.panels:
                self._create_initial_waiting_panel()
        except Exception:
            pass

    # ---- 폰트 스케일 조절 ----
    def _clamp_scale(self, v):
        """스케일 값 제한"""
        return max(0.5, min(2.0, float(v)))

    def inc_tile_scale(self):
        """타일 스케일 증가"""
        self.edit_tile_scale()

    def dec_tile_scale(self):
        """타일 스케일 감소"""
        self.edit_tile_scale()

    def inc_header_scale(self):
        """헤더 스케일 증가"""
        self.edit_header_scale()

    def dec_header_scale(self):
        """헤더 스케일 감소"""
        self.edit_header_scale()

    def edit_tile_scale(self):
        """타일 크기 조절 - 통합 대화상자 호출"""
        self.edit_display_sizes()

    def edit_header_scale(self):
        """문구 크기 조절 - 통합 대화상자 호출"""
        self.edit_display_sizes()

    def edit_display_sizes(self):
        """화면 크기 조절 (문구 + 타일 + 현재상태 문구 통합)"""
        dialog = tk.Toplevel(self)
        dialog.title("화면 크기 조절")
        dialog.geometry("700x715")  # 높이 10% 확대
        dialog.resizable(False, False)
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (650 // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg="#F5F5F5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 설정 프레임
        settings_frame = tk.Frame(main_frame, bg="#F5F5F5")
        settings_frame.pack(fill="x", pady=(0, 20))

        # 안내 문구 크기
        header_frame = ttk.LabelFrame(settings_frame, text="안내 문구 크기", padding="10")
        header_frame.pack(fill="x", pady=5)

        current_header = self.header_scale.get()
        tk.Label(header_frame, text=f"현재: {current_header:.2f}",
                font=("Pretendard", 10)).pack(side="left", padx=5)

        header_entry = tk.Entry(header_frame, width=10, font=("Pretendard", 12))
        header_entry.insert(0, f"{current_header:.2f}")
        header_entry.pack(side="left", padx=5)

        tk.Label(header_frame, text="(0.5 ~ 2.0)",
                font=("Pretendard", 9), fg="#666666").pack(side="left", padx=5)

        # 타일 문구 크기
        tile_frame = ttk.LabelFrame(settings_frame, text="타일 문구 크기", padding="10")
        tile_frame.pack(fill="x", pady=5)

        current_tile = self.tile_scale.get()
        tk.Label(tile_frame, text=f"현재: {current_tile:.2f}",
                font=("Pretendard", 10)).pack(side="left", padx=5)

        tile_entry = tk.Entry(tile_frame, width=10, font=("Pretendard", 12))
        tile_entry.insert(0, f"{current_tile:.2f}")
        tile_entry.pack(side="left", padx=5)

        tk.Label(tile_frame, text="(0.3 ~ 0.7)",
                font=("Pretendard", 9), fg="#666666").pack(side="left", padx=5)

        # 현재상태 문구 크기
        status_frame = ttk.LabelFrame(settings_frame, text="현재상태 문구 크기", padding="10")
        status_frame.pack(fill="x", pady=5)

        current_status = self.status_text_scale.get()
        tk.Label(status_frame, text=f"현재: {current_status:.2f}",
                font=("Pretendard", 10)).pack(side="left", padx=5)

        status_entry = tk.Entry(status_frame, width=10, font=("Pretendard", 12))
        status_entry.insert(0, f"{current_status:.2f}")
        status_entry.pack(side="left", padx=5)

        tk.Label(status_frame, text="(0.5 ~ 0.9)",
                font=("Pretendard", 9), fg="#666666").pack(side="left", padx=5)

        # 초기값 저장 (취소 시 복원용)
        initial_values = {
            'header': current_header,
            'tile': current_tile,
            'status': current_status
        }
        
        # 실시간 적용 함수 (저장은 하지 않음)
        def apply_values_real_time(force_status=False):
            """값을 실시간으로 화면에만 적용 (저장하지 않음)"""
            try:
                header_val = float(header_entry.get())
                tile_val = float(tile_entry.get())
                status_val = float(status_entry.get())

                # 범위 검증
                if not (0.5 <= header_val <= 2.0):
                    return  # 범위 밖이면 적용하지 않음
                if not (0.3 <= tile_val <= 0.7):
                    return
                if not (0.5 <= status_val <= 0.9):
                    return

                # 값 적용 (화면에만 반영)
                self.header_scale.set(header_val)
                self.tile_scale.set(tile_val)
                self.status_text_scale.set(status_val)
                
                # 실시간으로 화면 업데이트
                self._rescale_all()
                
                # 현재상태 문구 크기는 항상 명시적으로 업데이트 (실시간 반영)
                if force_status or status_val != initial_values['status']:
                    # 모든 패널의 현재상태 문구 크기 업데이트
                    for p in self.panels.values():
                        if hasattr(p, 'tiles_container') and hasattr(p.tiles_container, '_update_status_text_scale'):
                            try:
                                p.tiles_container._update_status_text_scale()
                                # 강제로 업데이트
                                p.tiles_container.update_idletasks()
                            except Exception as e:
                                print(f"[현재상태 문구 크기 업데이트 오류] {e}")
                                pass
                else:
                    # force_status가 False일 때도 현재상태 문구는 업데이트
                    for p in self.panels.values():
                        if hasattr(p, 'tiles_container') and hasattr(p.tiles_container, '_update_status_text_scale'):
                            try:
                                p.tiles_container._update_status_text_scale()
                            except Exception:
                                pass
            except ValueError:
                pass  # 숫자가 아닌 경우 무시
            except Exception as e:
                print(f"[실시간 적용 오류] {e}")
                pass  # 기타 오류 무시

        # Entry 위젯에 실시간 반영 바인딩
        header_entry.bind("<KeyRelease>", lambda e: apply_values_real_time())
        tile_entry.bind("<KeyRelease>", lambda e: apply_values_real_time())
        status_entry.bind("<KeyRelease>", lambda e: apply_values_real_time(force_status=True))
        
        # 현재상태 문구 크기는 입력 즉시 반영 (추가 바인딩)
        status_entry.bind("<Key>", lambda e: dialog.after(10, lambda: apply_values_real_time(force_status=True)))
        status_entry.bind("<FocusOut>", lambda e: apply_values_real_time(force_status=True))
        status_entry.bind("<FocusIn>", lambda e: apply_values_real_time(force_status=True))

        # 숫자 패드 프레임 - 박스 크기 확대
        number_pad_frame = ttk.LabelFrame(main_frame, text="숫자 패드", padding="30")
        number_pad_frame.pack(fill="both", expand=True, pady=(0, 20))

        # 현재 선택된 입력 필드 추적
        current_entry = [header_entry]  # 리스트로 참조 유지

        def set_current_entry(entry):
            current_entry[0] = entry
            entry.focus()

        # 입력 필드 클릭 이벤트 바인딩
        header_entry.bind("<Button-1>", lambda e: set_current_entry(header_entry))
        tile_entry.bind("<Button-1>", lambda e: set_current_entry(tile_entry))
        status_entry.bind("<Button-1>", lambda e: set_current_entry(status_entry))

        # 숫자 패드 버튼들 - 2배 크기로 확대
        pad_frame = tk.Frame(number_pad_frame, bg="#F5F5F5")
        pad_frame.pack()

        def insert_number(num):
            entry = current_entry[0]
            # Entry 위젯에서 커서 위치에 삽입 (Entry의 경우 커서 위치가 올바르지 않을 수 있으므로 끝에 추가)
            try:
                cursor_pos = entry.index(tk.INSERT)
                if cursor_pos == entry.index(tk.END):
                    # 커서가 끝에 있으면 끝에 추가
                    entry.insert(tk.END, str(num))
                else:
                    # 커서가 중간에 있으면 커서 위치에 삽입
                    entry.insert(cursor_pos, str(num))
                    entry.icursor(int(cursor_pos) + 1)
            except:
                # 오류가 발생하면 끝에 추가
                entry.insert(tk.END, str(num))
            # 값이 업데이트되도록 강제
            entry.update_idletasks()
            # 약간의 지연 후 실시간 반영 (현재상태 문구는 강제 반영)
            is_status_entry = (entry == status_entry)
            if is_status_entry:
                # 현재상태 문구 Entry인 경우 즉시 강제 반영
                dialog.after(10, lambda: apply_values_real_time(force_status=True))
            else:
                entry.after(10, lambda: apply_values_real_time(force_status=False))

        def insert_dot():
            entry = current_entry[0]
            try:
                cursor_pos = entry.index(tk.INSERT)
                if cursor_pos == entry.index(tk.END):
                    entry.insert(tk.END, ".")
                else:
                    entry.insert(cursor_pos, ".")
                    entry.icursor(int(cursor_pos) + 1)
            except:
                entry.insert(tk.END, ".")
            entry.update_idletasks()
            # 약간의 지연 후 실시간 반영 (현재상태 문구는 강제 반영)
            is_status_entry = (entry == status_entry)
            if is_status_entry:
                # 현재상태 문구 Entry인 경우 즉시 강제 반영
                dialog.after(10, lambda: apply_values_real_time(force_status=True))
            else:
                entry.after(10, lambda: apply_values_real_time(force_status=False))

        def clear_entry():
            entry = current_entry[0]
            entry.delete(0, tk.END)
            # 약간의 지연 후 실시간 반영 (현재상태 문구는 강제 반영)
            is_status_entry = (entry == status_entry)
            if is_status_entry:
                # 현재상태 문구 Entry인 경우 즉시 강제 반영
                dialog.after(10, lambda: apply_values_real_time(force_status=True))
            else:
                entry.after(10, lambda: apply_values_real_time(force_status=False))

        def backspace():
            entry = current_entry[0]
            try:
                cursor_pos = entry.index(tk.INSERT)
                if cursor_pos > 0:
                    # 커서 앞의 문자 삭제
                    prev_pos = int(cursor_pos) - 1
                    entry.delete(prev_pos, cursor_pos)
                    entry.icursor(prev_pos)
                    entry.update_idletasks()
            except:
                # 오류가 발생하면 끝에서 하나 삭제
                current_text = entry.get()
                if current_text:
                    entry.delete(len(current_text) - 1, tk.END)
                    entry.update_idletasks()
            # 약간의 지연 후 실시간 반영 (현재상태 문구는 강제 반영)
            is_status_entry = (entry == status_entry)
            if is_status_entry:
                # 현재상태 문구 Entry인 경우 즉시 강제 반영
                dialog.after(10, lambda: apply_values_real_time(force_status=True))
            else:
                entry.after(10, lambda: apply_values_real_time(force_status=False))

        # 숫자 패드 버튼 생성 - 4행 3열로 명시적 배치, 버튼 크기 반으로 축소
        # 첫 번째 행: 7, 8, 9
        btn7 = tk.Button(pad_frame, text="7", command=lambda: insert_number(7),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn7.grid(row=0, column=0, padx=2, pady=2)
        
        btn8 = tk.Button(pad_frame, text="8", command=lambda: insert_number(8),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn8.grid(row=0, column=1, padx=2, pady=2)
        
        btn9 = tk.Button(pad_frame, text="9", command=lambda: insert_number(9),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn9.grid(row=0, column=2, padx=2, pady=2)

        # 두 번째 행: 4, 5, 6
        btn4 = tk.Button(pad_frame, text="4", command=lambda: insert_number(4),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn4.grid(row=1, column=0, padx=2, pady=2)
        
        btn5 = tk.Button(pad_frame, text="5", command=lambda: insert_number(5),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn5.grid(row=1, column=1, padx=2, pady=2)
        
        btn6 = tk.Button(pad_frame, text="6", command=lambda: insert_number(6),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn6.grid(row=1, column=2, padx=2, pady=2)

        # 세 번째 행: 1, 2, 3
        btn1 = tk.Button(pad_frame, text="1", command=lambda: insert_number(1),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn1.grid(row=2, column=0, padx=2, pady=2)
        
        btn2 = tk.Button(pad_frame, text="2", command=lambda: insert_number(2),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn2.grid(row=2, column=1, padx=2, pady=2)
        
        btn3 = tk.Button(pad_frame, text="3", command=lambda: insert_number(3),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn3.grid(row=2, column=2, padx=2, pady=2)

        # 네 번째 행: 0, 소수점, 백스페이스
        btn0 = tk.Button(pad_frame, text="0", command=lambda: insert_number(0),
                        font=("Pretendard", 12, "bold"), width=4, height=1,
                        bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn0.grid(row=3, column=0, padx=2, pady=2)
        
        btn_dot = tk.Button(pad_frame, text=".", command=insert_dot,
                           font=("Pretendard", 12, "bold"), width=4, height=1,
                           bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn_dot.grid(row=3, column=1, padx=2, pady=2)
        
        btn_backspace = tk.Button(pad_frame, text="⌫", command=backspace,
                                font=("Pretendard", 12, "bold"), width=4, height=1,
                                bg="#E8E8E8", fg="#2C3E50", relief="raised", bd=2)
        btn_backspace.grid(row=3, column=2, padx=2, pady=2)

        # 버튼 프레임
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=20)

        def on_save():
            """저장 버튼 - config.conf에 저장"""
            try:
                header_val = float(header_entry.get())
                tile_val = float(tile_entry.get())
                status_val = float(status_entry.get())

                # 범위 검증
                if not (0.5 <= header_val <= 2.0):
                    messagebox.showerror("오류", "안내 문구 크기는 0.5 ~ 2.0 범위여야 합니다.", parent=dialog)
                    return
                if not (0.3 <= tile_val <= 0.7):
                    messagebox.showerror("오류", "타일 문구 크기는 0.3 ~ 0.7 범위여야 합니다.", parent=dialog)
                    return
                if not (0.5 <= status_val <= 0.9):
                    messagebox.showerror("오류", "현재상태 문구 크기는 0.5 ~ 0.9 범위여야 합니다.", parent=dialog)
                    return

                # 값 적용 (저장 전에 화면에 반영)
                self.header_scale.set(header_val)
                self.tile_scale.set(tile_val)
                self.status_text_scale.set(status_val)
                self._rescale_all()
                
                # 현재상태 문구 크기도 명시적으로 업데이트
                for p in self.panels.values():
                    if hasattr(p, 'tiles_container') and hasattr(p.tiles_container, '_update_status_text_scale'):
                        try:
                            p.tiles_container._update_status_text_scale()
                        except Exception:
                            pass

                # config.conf에 저장
                try:
                    self.cfg.ui["tile_scale"] = f"{tile_val:.2f}"
                    self.cfg.ui["header_scale"] = f"{header_val:.2f}"
                    self.cfg.ui["status_text_scale"] = f"{status_val:.2f}"
                    self.cfg.save()
                    print(f"[화면 크기 조절] 저장 완료: header={header_val:.2f}, tile={tile_val:.2f}, status={status_val:.2f}")
                    
                    # 저장 성공 메시지 (선택사항)
                    messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=dialog)
                except Exception as e:
                    messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}", parent=dialog)
                    import traceback
                    traceback.print_exc()
                    return
                    
                dialog.destroy()
            except ValueError as ve:
                messagebox.showerror("오류", f"올바른 숫자를 입력하세요:\n{str(ve)}", parent=dialog)
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}", parent=dialog)
                import traceback
                traceback.print_exc()

        def on_cancel():
            """취소 버튼 - 입력값 무시하고 초기값으로 복원"""
            # 초기값으로 복원
            self.header_scale.set(initial_values['header'])
            self.tile_scale.set(initial_values['tile'])
            self.status_text_scale.set(initial_values['status'])
            
            # 화면 업데이트
            self._rescale_all()
            
            dialog.destroy()

        def on_close():
            """다이얼로그 닫기 - 현재 상태 유지 (저장하지 않음)"""
            dialog.destroy()

        def on_reset():
            """기본값으로 초기화"""
            if messagebox.askyesno("초기화", "기본값(안내 문구: 2.0, 타일 문구: 0.55, 현재상태 문구: 0.8)으로 초기화하시겠습니까?", parent=dialog):
                header_entry.delete(0, tk.END)
                header_entry.insert(0, "2.0")
                tile_entry.delete(0, tk.END)
                tile_entry.insert(0, "0.55")
                status_entry.delete(0, tk.END)
                status_entry.insert(0, "0.8")
                # 실시간 반영
                apply_values_real_time()

        # 다이얼로그 닫기 이벤트 바인딩
        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # 저장 버튼 (녹색)
        btn_save = tk.Button(button_frame, text="✓ 저장", command=on_save,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 width=12, height=2, relief="raised", bd=3,
                 activebackground="#229954", activeforeground="#FFFFFF")
        btn_save.pack(side="left", padx=5)

        # 닫기 버튼 (회색) - 현재 상태 유지 (저장하지 않음)
        btn_close = tk.Button(button_frame, text="✕ 닫기", command=on_close,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 width=12, height=2, relief="raised", bd=3,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF")
        btn_close.pack(side="left", padx=5)

        # 취소 버튼 (주황색) - 초기값으로 복원
        btn_cancel = tk.Button(button_frame, text="↺ 취소", command=on_cancel,
                 bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 12, "bold"),
                 width=12, height=2, relief="raised", bd=3,
                 activebackground="#D35400", activeforeground="#FFFFFF")
        btn_cancel.pack(side="left", padx=5)

        dialog.wait_window()

    def _rescale_all(self):
        """모든 패널 스케일 재적용"""
        for p in self.panels.values():
            p._apply_header_font()
            for k in SENSOR_KEYS:
                p.tiles_container._autoscale_tile(k)
            # 현재상태 문구 크기도 업데이트 (한 번만 호출)
            p.tiles_container._update_status_text_scale()

    # ---- 전체화면/종료 ----
    def full_btn_text(self):
        """전체화면 버튼 텍스트"""
        return "전체화면해제" if self._is_fullscreen else "전체화면"

    def update_fullscreen_buttons(self):
        """전체화면 버튼 업데이트 - 헤더에 버튼이 없으므로 패스"""
        pass

    def toggle_fullscreen(self):
        """전체화면 토글"""
        self._is_fullscreen = not self._is_fullscreen
        try:
            self.attributes("-fullscreen", self._is_fullscreen)
            self.attributes("-topmost", self._is_fullscreen)
            # 전체화면 모드일 때 최상단 포커스 유지
            if self._is_fullscreen:
                self.lift()
                self.focus_force()
        except Exception:
            pass
        if not self._is_fullscreen:
            try:
                self.state("zoomed")
            except Exception:
                pass
        self.update_fullscreen_buttons()
        # 메뉴 토글 레이블 갱신
        self._setup_view_menu()

    def exit_fullscreen(self):
        """전체화면 해제"""
        if self._is_fullscreen:
            self._is_fullscreen = False
            try:
                self.attributes("-fullscreen", False)
                self.attributes("-topmost", False)
                self.state("zoomed")
            except Exception:
                pass
            self.update_fullscreen_buttons()

    def _handle_window_close(self):
        """윈도우 닫기 이벤트 처리"""
        if not self.cfg.admin_mode:
            # 관리자 모드가 아닐 때는 종료 차단
            return
        self.exit_app()

    def _handle_fullscreen_toggle(self):
        """전체화면 토글 이벤트 처리"""
        if not self.cfg.admin_mode:
            # 관리자 모드가 아닐 때는 전체화면 토글 차단
            return
        self.toggle_fullscreen()

    def _handle_escape(self):
        """ESC 키 이벤트 처리"""
        if not self.cfg.admin_mode:
            # 관리자 모드가 아닐 때는 ESC 키 차단
            return
        self.exit_fullscreen()

    def _handle_exit(self):
        """종료 키 이벤트 처리"""
        if not self.cfg.admin_mode:
            # 관리자 모드가 아닐 때는 종료 차단
            return
        self.exit_app()

    def _handle_minimize(self):
        """최소화 이벤트 처리"""
        if not self.cfg.admin_mode:
            # 관리자 모드가 아닐 때는 최소화 차단
            self.after(100, lambda: self.deiconify())  # 최소화 취소
            return

    def _ensure_focus(self):
        """매니저 창이 항상 포커스를 유지하도록 확인"""
        try:
            # 전체화면 모드일 때만 포커스 유지 (일반 창 모드에서는 사용자가 다른 창 사용 가능)
            if self._is_fullscreen:
                # 현재 창이 보이는 상태인지 확인
                if self.state() == "normal" or self.state() == "zoomed":
                    # 포커스가 없으면 다시 가져오기
                    try:
                        focused_widget = self.focus_get()
                        if focused_widget is None or not str(focused_widget).startswith(str(self)):
                            # 포커스가 다른 애플리케이션으로 갔을 경우
                            self.lift()
                            self.focus_force()
                    except Exception:
                        # 포커스 확인 실패 시 강제로 포커스 가져오기
                        self.lift()
                        self.focus_force()
        except Exception:
            pass

        # 2초마다 확인 (너무 자주 확인하면 사용자 경험 저하)
        self.after(2000, self._ensure_focus)

    def _on_tab_click(self, event):
        """탭 좌클릭 - ✕ 영역 클릭 시 탭 닫기"""
        try:
            # 클릭된 탭 인덱스 확인
            clicked = self.nb.identify(event.x, event.y)
            if clicked != "label":
                return  # 탭 레이블이 아니면 무시

            tab_index = self.nb.index(f"@{event.x},{event.y}")
            if tab_index is None:
                return

            # 탭 텍스트 확인 - ✕가 포함되어 있는지 (연결 끊김 상태)
            tab_text = self.nb.tab(tab_index, "text") or ""
            if "✕" not in tab_text:
                return  # 닫기 버튼이 없는 탭

            # 탭의 우측 끝 영역 클릭인지 확인 (✕ 버튼 영역)
            # bbox로 탭 영역 확인
            try:
                tab_bbox = self.nb.bbox(tab_index)
                if tab_bbox:
                    tab_x, tab_y, tab_width, tab_height = tab_bbox
                    # 탭 우측 30px 영역을 ✕ 버튼 영역으로 간주
                    close_area_start = tab_x + tab_width - 35
                    if event.x >= close_area_start:
                        # ✕ 영역 클릭됨 - 탭 닫기
                        tab_widget = self.nb.nametowidget(self.nb.tabs()[tab_index])
                        sid_key = None
                        for key, panel in self.panels.items():
                            if panel.master == tab_widget:
                                sid_key = key
                                break

                        if sid_key:
                            panel = self.panels.get(sid_key)
                            if panel and hasattr(panel, '_connection_status'):
                                if panel._connection_status == "disconnected":
                                    self.delete_sensor_tab(sid_key)
                                    return "break"  # 이벤트 전파 중단
            except Exception:
                pass
        except Exception:
            pass

    def _on_tab_right_click(self, event):
        """탭 우클릭 시 닫기 메뉴 표시"""
        try:
            # 클릭된 탭 인덱스 확인
            tab_index = self.nb.index(f"@{event.x},{event.y}")
            if tab_index is None:
                return

            # 해당 탭의 패널 찾기
            tab_widget = self.nb.nametowidget(self.nb.tabs()[tab_index])
            sid_key = None
            for key, panel in self.panels.items():
                if panel.master == tab_widget:
                    sid_key = key
                    break

            if not sid_key:
                return

            # 연결 끊김 상태 확인
            panel = self.panels.get(sid_key)
            if not panel or not hasattr(panel, '_connection_status'):
                return

            if panel._connection_status != "disconnected":
                return  # 연결 중인 탭은 닫기 불가

            # 컨텍스트 메뉴 표시
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(
                label="❌ 탭 닫기",
                command=lambda: self._close_tab_with_confirm(sid_key)
            )
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    def _on_tab_middle_click(self, event):
        """탭 중클릭(휠 클릭) 시 탭 닫기"""
        try:
            # 클릭된 탭 인덱스 확인
            tab_index = self.nb.index(f"@{event.x},{event.y}")
            if tab_index is None:
                return

            # 해당 탭의 패널 찾기
            tab_widget = self.nb.nametowidget(self.nb.tabs()[tab_index])
            sid_key = None
            for key, panel in self.panels.items():
                if panel.master == tab_widget:
                    sid_key = key
                    break

            if not sid_key:
                return

            # 연결 끊김 상태 확인
            panel = self.panels.get(sid_key)
            if not panel or not hasattr(panel, '_connection_status'):
                return

            if panel._connection_status != "disconnected":
                return  # 연결 중인 탭은 닫기 불가

            # 바로 닫기 (확인 없이)
            self.delete_sensor_tab(sid_key)
        except Exception:
            pass

    def _close_tab_with_confirm(self, sid_key):
        """확인 후 탭 닫기"""
        try:
            from tkinter import messagebox
            base_sid = sid_key.split("@")[0].split("#")[0]
            if messagebox.askokcancel(
                "탭 닫기",
                f"'{base_sid}' 센서 탭을 닫으시겠습니까?",
                parent=self
            ):
                self.delete_sensor_tab(sid_key)
        except Exception:
            pass

    def delete_sensor_tab(self, sid_key):
        """센서 탭 삭제 (연결 끊김 상태일 때만)"""
        try:
            # 패널 찾기
            panel = self.panels.get(sid_key)
            if not panel:
                print(f"[탭 삭제] 패널을 찾을 수 없습니다: {sid_key}")
                return False

            # 연결 상태 확인
            if hasattr(panel, '_connection_status'):
                if panel._connection_status != "disconnected":
                    print(f"[탭 삭제] 연결 끊김 상태가 아닙니다: {sid_key}")
                    return False

            # 탭 인덱스 찾기
            tab_index = None
            try:
                for i in range(self.nb.index("end")):
                    if panel.master == self.nb.nametowidget(self.nb.tabs()[i]):
                        tab_index = i
                        break
            except Exception as e:
                print(f"[탭 삭제] 탭 인덱스 찾기 실패: {e}")
                return False

            if tab_index is None:
                print(f"[탭 삭제] 탭 인덱스를 찾을 수 없습니다: {sid_key}")
                return False

            # 다음 탭 선택 (또는 이전 탭)
            try:
                total_tabs = self.nb.index("end")
                if total_tabs > 1:
                    if tab_index < total_tabs - 1:
                        # 다음 탭 선택
                        self.nb.select(tab_index + 1)
                    elif tab_index > 0:
                        # 이전 탭 선택
                        self.nb.select(tab_index - 1)
            except Exception as e:
                print(f"[탭 삭제] 다음 탭 선택 실패: {e}")

            # 패널 정리
            try:
                # 거울보기 카메라 중지
                if hasattr(panel, 'mirror_camera') and panel.mirror_camera:
                    panel.mirror_camera.release()
                    panel.mirror_camera = None

                # 패널 파괴
                panel.destroy()
            except Exception as e:
                print(f"[탭 삭제] 패널 정리 실패: {e}")

            # 탭 제거
            try:
                self.nb.forget(tab_index)
            except Exception as e:
                print(f"[탭 삭제] 탭 제거 실패: {e}")
                return False

            # 내부 데이터 정리
            try:
                if sid_key in self.panels:
                    del self.panels[sid_key]
                if sid_key in self.states:
                    del self.states[sid_key]
                if sid_key in self.tab_alert_states:
                    del self.tab_alert_states[sid_key]
                if sid_key in self._today_alerts_by_key:
                    del self._today_alerts_by_key[sid_key]
                if sid_key in self._sensor_validation_states:
                    del self._sensor_validation_states[sid_key]
            except Exception as e:
                print(f"[탭 삭제] 내부 데이터 정리 실패: {e}")

            print(f"[탭 삭제] 탭이 삭제되었습니다: {sid_key}")

            # 로그 기록
            try:
                if hasattr(self, 'logs'):
                    self.logs.write_run(f"tab deleted: {sid_key}")
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"[탭 삭제] 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def exit_app(self):
        """애플리케이션 종료"""
        # 하트비트 중지 및 파일 정리
        try:
            self._heartbeat_running = False
            hb_path = os.path.abspath(self._heartbeat_file) if hasattr(self, "_heartbeat_file") else None
            if hb_path and os.path.exists(hb_path):
                os.remove(hb_path)
        except Exception:
            pass
        # 정상 종료 신호 파일 생성 (watchdog가 재시작하지 않도록)
        try:
            # get_base_dir()는 PyInstaller와 일반 모드 모두 올바른 경로를 반환
            signal_file = os.path.join(get_base_dir(), "normal_exit.signal")
            # 파일을 먼저 생성하고 명시적으로 flush 및 sync
            with open(signal_file, 'w', encoding='utf-8') as f:
                f.write(f"normal_exit_{int(time.time())}")
                f.flush()  # 버퍼 플러시
                os.fsync(f.fileno())  # 디스크에 강제 쓰기
            print(f"[정상 종료] 정상 종료 신호 파일 생성: {signal_file}")
            # 파일이 디스크에 완전히 쓰여질 시간 확보
            time.sleep(0.1)
        except Exception as e:
            print(f"[정상 종료] 정상 종료 신호 파일 생성 실패: {e}")
            pass
            
        # 윈도우 모니터링과 키보드 차단 기능 제거됨
        try:
            pass
        except Exception:
            pass
            
        # run.log에 종료 기록
        try:
            self.logs.write_run("app closed")
        except Exception:
            pass
        try:
            for p in self.panels.values():
                p._hide_overlay()
        except Exception:
            pass
        self.destroy()

    def _heartbeat_loop(self):
        """매니저 하트비트 파일 주기적 갱신"""
        try:
            path = os.path.abspath(self._heartbeat_file)
        except Exception:
            return
        while getattr(self, "_heartbeat_running", False):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(str(int(time.time())))
            except Exception:
                pass
            time.sleep(30)

    # ---- 탭/데이터 처리 ----
    def _panel_key(self, sid, peer):
        """패널 키 생성"""
        pol = self.cfg.ui.get("tab_id_policy", "by_ip")
        ip = peer.split(":")[0] if peer else ""
        if pol == "by_ip" and ip:
            return f"{sid}@{ip}"
        if pol == "by_conn" and peer:
            return f"{sid}#{peer}"
        return sid

    def update_sensor_version(self, sid: str, peer: str, version: str):
        """센서 버전을 상태에 반영하고 탭 제목 즉시 갱신"""
        try:
            key = self._panel_key(sid, peer)
            st = self.states.setdefault(key, {"peer": peer, "last_rx": None, "version": ""})
            st["peer"] = peer or st.get("peer", "")
            if version:
                st["version"] = str(version)
            p = self.panels.get(key)
            if p:
                self._update_tab_title(key, p)
        except Exception:
            pass

    def ensure_panel(self, sid, peer):
        """패널 생성/확보"""
        key = self._panel_key(sid, peer)
        if key in self.panels:
            return self.panels[key]

        # 최대 패널 수 제한 확인 (기본 4)
        try:
            max_sensors = int(self.cfg.env.get("max_sensors", 4))
        except Exception:
            max_sensors = 4
        max_sensors = max(1, min(4, max_sensors))
        if self._current_panel_count() >= max_sensors:
            # 최대치 도달 시 새 패널 생성하지 않음
            return None

        # 최대 수에 도달하는 순간에만 대기 탭 제거
        if "__waiting__" in self.panels:
            try:
                projected = self._current_panel_count() + 1
                if projected >= max_sensors:
                    self.panels.pop("__waiting__", None)
                    self.states.pop("__waiting__", None)
                    for tab_id in range(self.nb.index("end")):
                        tab_text = self.nb.tab(tab_id, "text") or ""
                        if tab_text.startswith("센서 접속 대기중") or tab_text.startswith("대기중"):
                            self.nb.forget(tab_id)
                            break
            except Exception:
                pass

        # states를 먼저 설정 (SensorPanel.__init__에서 참조함)
        st = self.states.setdefault(key, {"peer": peer, "last_rx": None, "version": ""})
        st["peer"] = peer

        frame = ttk.Frame(self.nb)
        p = SensorPanel(frame, key, self)
        p.pack(fill="both", expand=True)
        
        # 탭 제목을 아이디와 IP(+버전)로 설정
        ip = peer.split(":")[0] if peer else ""
        ver = st.get("version", "")
        if ip:
            initial_title = f"{sid} ({ip}{', ' + ver if ver else ''}) (연결중)"
        else:
            initial_title = f"{sid} ({ver}) (연결중)" if ver else f"{sid} (연결중)"
        
        # 대기 탭이 있다면, 대기 탭 바로 앞에 삽입하여 대기 탭이 항상 맨 오른쪽이 되도록 유지
        try:
            waiting_tab = self._get_waiting_tab_id()
            if waiting_tab is not None:
                self.nb.insert(waiting_tab, frame, text=initial_title)
            else:
                self.nb.add(frame, text=initial_title)
        except Exception:
            self.nb.add(frame, text=initial_title)

        # 탭 포커스는 자동으로 이동하지 않음 (사용자가 현재 보는 화면 유지)
        # 사용자가 직접 탭을 클릭해야 전환됨
        # 새 탭 색상 강제 설정
        try:
            tab_index = self.nb.index("end") - 1
            self.nb.tab(tab_index, background="white", foreground="black")
            # 추가로 스타일도 강제 적용
            self.after(50, lambda: self.nb.tab(tab_index, background="white", foreground="black"))
        except Exception:
            pass
        self.panels[key] = p

        # 대기 탭 카운터 갱신 (패널 등록 후 정확한 수로 갱신)
        try:
            self._update_waiting_tab_title()
        except Exception:
            pass

        # 패널 생성 직후 스케일 반영은 after_idle로 지연 (UI 렌더링 후)
        def apply_initial_scale():
            try:
                p._apply_header_font()
                # 리사이즈 이벤트가 자동으로 autoscale을 트리거하므로 여기서는 생략
            except Exception:
                pass
        self.after_idle(apply_initial_scale)

        # 개요 제거됨

        return p

    def on_data(self, sid, peer, data):
        """센서 데이터 수신 처리"""
        key = self._panel_key(sid, peer)
        p = self.ensure_panel(sid, peer)
        if p is None:
            return
        
        # 데이터 수신 시 타임스탬프 즉시 업데이트 (통신 연결 상태 확인용)
        # 중요: update_data 호출 전에 먼저 업데이트하여 통신 끊김 방지
        # 데이터 검증 실패 여부와 관계없이 last_rx는 항상 업데이트됨
        st = self.states.setdefault(key, {"peer": peer, "last_rx": None, "version": ""})
        st["peer"] = peer
        st["last_rx"] = time.time()  # 항상 업데이트 (데이터 검증과 무관)
        
        # 빈 데이터인 경우 (heartbeat 등) 연결 상태만 업데이트하고 종료
        if not data or not isinstance(data, dict) or len(data) == 0:
            # Heartbeat 등으로 인한 빈 데이터: 연결 상태만 업데이트
            if p._connection_status in ("waiting", "disconnected"):
                p._connection_status = "connected"
                p.header.set_connection_status("connected")
                p.tiles_container.set_connection_status("connected")
                # 거울보기 모드가 아닐 때만 status_msg_label 숨기기
                if not (hasattr(p, 'mirror_mode_active') and p.mirror_mode_active):
                    p.status_msg_label.pack_forget()
                # 새로 접속한 센서 탭으로 자동 포커싱
                try:
                    self.nb.select(p.master)
                    print(f"[탭 포커싱] 접속된 센서 탭 '{key}' 선택됨 (heartbeat)")
                except Exception as e:
                    print(f"[센서 접속] 탭 포커싱 오류: {e}")
            return
        
        # 데이터 검증 및 필터링
        filtered_data = self._validate_and_filter_data(key, data)

        # 데이터 수신 확인 (필터링 결과와 무관): 연결 상태 업데이트
        # 센서로부터 데이터를 받았으므로 연결 상태를 "connected"로 변경
        is_first_connect = p._connection_status in ("waiting", "disconnected")
        if is_first_connect:
            # 센서 접속 시:
            # - 타일(card) 또는 그래프(graph) 모드일 때만 타일로 전환
            # - 거울보기, 안전교육, 도면 등 다른 모드에서는 현재 화면 유지
            is_mirror_mode = hasattr(p, 'mirror_mode_active') and p.mirror_mode_active
            is_tile_or_graph = hasattr(p, 'view_mode') and p.view_mode in ("card", "graph")

            # 먼저 연결 상태를 connected로 변경 (tiles_container.set_connection_status 전에)
            p._connection_status = "connected"
            p.header.set_connection_status("connected")
            p.tiles_container.set_connection_status("connected")

            # 화재 패널 표시 (연결 시 자동)
            if hasattr(p, 'show_fire_panel'):
                try:
                    p.show_fire_panel()
                except Exception as e:
                    print(f"[Fire] 화재 패널 표시 실패: {e}")

            # 거울보기 모드가 아닐 때만 status_msg_label 숨기기
            if not is_mirror_mode:
                try:
                    p.status_msg_label.pack_forget()
                except Exception:
                    pass

            # 거울보기 모드인 경우 카메라 종료 후 타일로 전환
            if is_mirror_mode:
                print(f"[센서 접속] 패널 '{key}' 연결됨 - 거울보기 종료 후 타일 화면으로 전환")
                try:
                    p.hide_mirror_view()  # 거울보기 종료 (카메라 해제 포함)
                except Exception as e:
                    print(f"[센서 접속] 거울보기 종료 오류: {e}")

            # 타일 화면으로 전환
            print(f"[센서 접속] 패널 '{key}' 연결됨 (타일 화면으로 전환)")
            # 이미 card 모드여도 강제로 타일 표시 (접속 대기 화면에서 전환)
            if hasattr(p, 'view_mode') and p.view_mode == "card":
                # 타일 컨테이너 강제 재표시
                p.tiles_container.pack_forget()
                p.tiles_container.pack(side="top", fill="both", expand=True, padx=12, pady=12)
            else:
                p.switch_to_card_mode()

            # 새로 접속한 센서 탭으로 자동 포커싱
            try:
                self.nb.select(p.master)
                print(f"[탭 포커싱] 접속된 센서 탭 '{key}' 선택됨")
            except Exception as e:
                print(f"[센서 접속] 탭 포커싱 오류: {e}")

        # 검증 통과한 데이터만 업데이트 및 저장
        if filtered_data:
            p.update_data(filtered_data)

            # 첫 접속 시 타일 화면 강제 갱신 (접속 대기 상태에서 현재값으로 전환)
            if is_first_connect:
                try:
                    p.tiles_container.update_idletasks()
                except Exception:
                    pass

            # 로그 기록 (검증 통과한 데이터만)
            self.logs.on_data(sid, peer, filtered_data)
        # 주의: filtered_data가 비어있어도 last_rx는 이미 업데이트되었고
        # 연결 상태도 "connected"로 업데이트되었으므로 센서는 연결된 것으로 표시됨

        # 대기 탭 카운터 갱신 (연결 증가 시 즉시 반영)
        try:
            self._update_waiting_tab_title()
        except Exception:
            pass

        # 탭 제목 업데이트는 1초마다만 (성능 최적화)
        if not hasattr(self, '_last_tab_update'):
            self._last_tab_update = {}

        now = time.time()
        last_update = self._last_tab_update.get(key, 0)
        if now - last_update > 1.0:
            self._last_tab_update[key] = now
            self._update_tab_title(key, p)
            # 개요 제거됨

    def record_alert(self, panel_key, sid, peer, sensor_key, level, value):
        """오늘 경고 목록에 패널별로 기록 + SQLite 영구 저장"""
        try:
            ts_epoch = time.time()
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_epoch))
            self._today_alerts_by_key[panel_key].append({
                "ts": ts,
                "sid": sid,
                "key": sensor_key,
                "level": level,
                "value": value,
            })
            # DB에도 기록
            if hasattr(self, 'logs') and hasattr(self.logs, 'write_alert_event'):
                self.logs.write_alert_event(sid, peer, sensor_key, level, value, ts_epoch)
        except Exception:
            pass

    def get_today_alert_count_for(self, panel_key):
        """지정 패널의 오늘 경고 건수 반환"""
        try:
            return len(self._today_alerts_by_key.get(panel_key, []))
        except Exception:
            return 0

    def get_today_alerts_for(self, panel_key):
        """지정 패널의 오늘 경고 목록 반환 (메모리 + DB 병행 가능)"""
        # 우선 메모리 목록 반환
        alerts = list(self._today_alerts_by_key.get(panel_key, []))
        # DB에서 보강 (동일 sid/ip 기준)
        try:
            state = self.states.get(panel_key, {})
            peer = state.get('peer', '')
            base_sid = panel_key.split('@')[0].split('#')[0]
            if hasattr(self, 'logs') and hasattr(self.logs, 'get_today_alerts_for'):
                db_alerts = self.logs.get_today_alerts_for(base_sid, peer)
                # 간단 병합: DB 최신 → 메모리 뒤에 덧붙이되 중복 허용
                alerts = db_alerts or alerts
        except Exception:
            pass
        return alerts

    def clear_today_alerts_for(self, panel_key):
        """지정 패널의 오늘 경고 목록을 메모리와 DB에서 삭제"""
        try:
            base_sid = panel_key.split("@")[0].split("#")[0]
            state = self.states.get(panel_key, {})
            peer = state.get('peer', '')
            # 메모리 초기화
            try:
                self._today_alerts_by_key.pop(panel_key, None)
            except Exception:
                pass
            # DB 삭제
            if hasattr(self, 'logs') and hasattr(self.logs, 'delete_today_alerts_for'):
                self.logs.delete_today_alerts_for(base_sid, peer)
            # 헤더 버튼 카운트 갱신
            p = self.panels.get(panel_key)
            if p and hasattr(p, 'header'):
                p.header.update_alert_count()
            return True
        except Exception:
            return False

    def get_today_alert_level_counts_for(self, panel_key):
        """지정 패널의 오늘 경고 레벨별 집계 반환 {3:int,4:int,5:int}"""
        counts = {3: 0, 4: 0, 5: 0}
        try:
            alerts = self.get_today_alerts_for(panel_key)
            for a in alerts:
                lv = int(a.get('level', 0))
                if lv in counts:
                    counts[lv] += 1
        except Exception:
            pass
        return counts

    def on_water_alert(self, sid, peer, data, alert_type, message, alert_level):
        """누수 알림 처리"""
        key = self._panel_key(sid, peer)
        panel = self.panels.get(key)
        if panel:
            # 누수 알림을 패널에 전달
            panel.on_water_alert(alert_type, message, alert_level)
        
        # 로그에 기록
        self.logs.write_run(f"Water alert: {alert_type} from {sid} - {message}")

    def set_tab_alert(self, key, is_alert):
        """탭 알림 상태 설정"""
        self.tab_alert_states[key] = is_alert
        self._update_tab_appearance(key)

    def _update_tab_appearance(self, key):
        """탭 외관 업데이트 (색상 변경)"""
        try:
            panel = self.panels.get(key)
            if not panel:
                return
            
            # 탭 인덱스 찾기 (패널의 master 프레임으로 찾기)
            tab_index = None
            try:
                for i in range(self.nb.index("end")):
                    if self.nb.tab(i, "text") and panel.master == self.nb.nametowidget(self.nb.tabs()[i]):
                        tab_index = i
                        break
            except Exception:
                # 대안: 텍스트로 찾기
                base_name = key.split("@")[0].split("#")[0]
                for i in range(self.nb.index("end")):
                    tab_text = self.nb.tab(i, "text")
                    if tab_text and base_name in tab_text:
                        tab_index = i
                        break
            
            if tab_index is not None:
                # 선택된 탭 여부 확인
                try:
                    current_tab = self.nb.select()
                    is_selected = (self.nb.tabs()[tab_index] == current_tab)
                except Exception:
                    is_selected = False

                # 연결 상태 확인
                conn_status = getattr(panel, '_connection_status', 'waiting')

                # 최대 경보 레벨 기반 색상 계산
                max_level = 1
                alert_color = "#2ECC71"  # 기본: 정상 초록색
                try:
                    if conn_status == "connected" and hasattr(panel, 'data') and panel.data:
                        for sk, sv in panel.data.items():
                            try:
                                lvl = panel.alert_manager.get_alert_level(sk, sv)
                                if lvl > max_level:
                                    max_level = lvl
                            except Exception:
                                continue
                        alert_color = panel.alert_manager.alert_colors.get(max_level, "#2ECC71")
                    elif conn_status == "disconnected":
                        alert_color = "#95A5A6"  # 회색
                    elif conn_status == "waiting":
                        alert_color = "#7F8C8D"  # 진한 회색
                except Exception:
                    alert_color = "#2ECC71"

                # 선택된 탭: 파란색 (정상일 때) 또는 경고색
                # 비선택 탭: 검정색 (정상일 때) 또는 경고색
                if is_selected:
                    # 선택된 탭
                    if conn_status == "connected":
                        if max_level == 1:
                            fg = "#3498DB"  # 정상: 파란색
                        else:
                            fg = alert_color  # 경고 레벨 색상
                    else:
                        fg = alert_color  # 대기중/끊김: 회색
                else:
                    # 비선택 탭
                    if conn_status == "connected":
                        if max_level == 1:
                            fg = "#000000"  # 정상: 검정색
                        else:
                            fg = alert_color  # 경고 레벨 색상
                    else:
                        fg = alert_color  # 대기중/끊김: 회색

                # 깜박임은 경계(4) 이상일 때
                should_blink = (max_level >= 4)
                if should_blink and not getattr(self, '_blink_on', False):
                    fg = "#FFFFFF"  # 깜박임 off 순간에는 흰색으로 보이게

                self.nb.tab(tab_index, background="#FFFFFF", foreground=fg)
        except Exception:
            pass

    def _refresh_all_tabs(self):
        """모든 탭의 외관을 현재 상태에 맞게 갱신"""
        try:
            for k in list(self.panels.keys()):
                self._update_tab_appearance(k)
        except Exception:
            pass

        # 카메라 상태 동기화: 한 패널이라도 카메라 사용 가능하면 모든 패널에 반영
        try:
            camera_ready = False
            for panel in self.panels.values():
                if hasattr(panel, 'camera_available') and panel.camera_available:
                    camera_ready = True
                    break
                if hasattr(panel, 'mirror_mode_active') and panel.mirror_mode_active:
                    camera_ready = True
                    break

            if camera_ready:
                for panel in self.panels.values():
                    if hasattr(panel, 'camera_available'):
                        panel.camera_available = True
                    if hasattr(panel, 'header') and hasattr(panel.header, 'set_mirror_camera_ready'):
                        panel.header.set_mirror_camera_ready(True)
        except Exception:
            pass

    def _focus_first_connected_tab(self):
        """첫 번째 접속된 센서 탭으로 포커싱"""
        try:
            # 접속된 센서 탭 찾기
            for key, panel in self.panels.items():
                if hasattr(panel, '_connection_status') and panel._connection_status == "connected":
                    # 해당 탭 선택
                    try:
                        self.nb.select(panel.master)
                        print(f"[탭 포커싱] 첫 번째 접속된 센서 탭 '{key}' 선택됨")
                    except Exception as e:
                        print(f"[탭 포커싱] 탭 선택 실패: {e}")
                    break
        except Exception as e:
            print(f"[탭 포커싱] 오류: {e}")

    def _update_tab_title(self, key, panel):
        """탭 제목 업데이트"""
        state = self.states.get(key, {})
        peer = state.get("peer", "")
        ver = state.get("version", "")
        base = key.split("@")[0].split("#")[0]
        ip = peer.split(":")[0] if peer else ""

        # 경고 레벨 이름 매핑
        alert_level_names = {
            1: "정상",
            2: "관심",
            3: "주의",
            4: "경계",
            5: "심각"
        }

        # 연결 상태 가져오기
        conn_status = getattr(panel, '_connection_status', 'waiting')
        if conn_status == "connected":
            # 최대 경보 레벨 계산
            max_level = 1
            try:
                if hasattr(panel, 'data') and panel.data:
                    for sk, sv in panel.data.items():
                        try:
                            lvl = panel.alert_manager.get_alert_level(sk, sv)
                            if lvl > max_level:
                                max_level = lvl
                        except Exception:
                            continue
            except Exception:
                max_level = 1

            level_name = alert_level_names.get(max_level, "정상")
            status_text = f"(연결됨-{level_name})"
        elif conn_status == "disconnected":
            status_text = "(연결 끊김) ✕"  # X 표시 추가 (클릭/우클릭으로 탭 닫기 가능)
        else:
            status_text = "(대기중)"

        # 탭 제목에 센서 ID와 IP/버전, 연결 상태 표시
        if ip and ver:
            title = f"{base} ({ip}, {ver}) {status_text}"
        elif ip:
            title = f"{base} ({ip}) {status_text}"
        elif ver:
            title = f"{base} ({ver}) {status_text}"
        else:
            title = f"{base} {status_text}"

        try:
            self.nb.tab(panel.master, text=title)
            # 탭 외관도 업데이트
            self._update_tab_appearance(key)
        except:
            pass

    # ----- 설정 메뉴 동작 -----
    def _verify_settings_password(self):
        """설정 접근을 위한 비밀번호 검증"""
        import hashlib

        # 관리자 모드면 비밀번호 확인 생략
        if self.cfg.admin_mode:
            return True

        # config에서 해시된 비밀번호 가져오기 (없으면 None)
        settings_password_hash = self.cfg.ui.get("settings_password_hash", None)

        # 비밀번호가 설정되지 않았으면 바로 통과
        if not settings_password_hash:
            return True

        # 비밀번호 입력 다이얼로그
        dialog = tk.Toplevel(self)
        dialog.title("설정 접근")
        dialog.geometry("500x280")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self)
        dialog.grab_set()

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (140)
        dialog.geometry(f"500x280+{x}+{y}")

        result = [False]  # 결과를 저장할 리스트

        # 제목
        tk.Label(dialog, text="설정 접근 권한 확인",
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=20)

        # 입력 프레임
        input_frame = tk.Frame(dialog, bg="#F5F5F5")
        input_frame.pack(pady=15, padx=40, fill="x")

        tk.Label(input_frame, text="비밀번호:",
                font=("Pretendard", 13, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(anchor="w", pady=(0, 8))

        password_entry = tk.Entry(input_frame, font=("Pretendard", 14), show="*", width=30, relief="solid", bd=2)
        password_entry.pack(fill="x", ipady=10)
        password_entry.focus()

        # 버튼 프레임
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=40)

        def on_verify():
            password = password_entry.get()
            # SHA-256 해시 생성
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            if password_hash == settings_password_hash:
                result[0] = True
                dialog.destroy()
            else:
                messagebox.showerror("인증 실패", "비밀번호가 올바르지 않습니다.", parent=dialog)
                password_entry.delete(0, tk.END)
                password_entry.focus()

        def on_cancel():
            dialog.destroy()

        confirm_btn = tk.Button(button_frame, text="✓ 확인", command=on_verify,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF")
        confirm_btn.pack(side="left", padx=5, ipady=12)

        cancel_btn = tk.Button(button_frame, text="✕ 취소", command=on_cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF")
        cancel_btn.pack(side="right", padx=5, ipady=12)

        # Enter 키로 확인
        password_entry.bind("<Return>", lambda e: on_verify())

        dialog.wait_window()
        return result[0]

    def edit_text(self):
        """표시 문구 편집"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return
            
        if not self._verify_settings_password():
            return

        # 커스텀 다이얼로그 생성 (키보드와 버튼이 모두 보이도록 크기 조정)
        dialog = tk.Toplevel(self)
        dialog.title("표시 문구 편집")
        # 키보드(약 250px) + 텍스트 위젯(약 200px) + 제목/설명(약 80px) + 버튼(약 60px) + 패딩(약 160px) = 약 759px
        # 요청: 하단 10% 더 확장 (759 -> 835)
        dialog.geometry("900x835")
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450)
        y = (dialog.winfo_screenheight() // 2) - (418)
        dialog.geometry(f"900x835+{x}+{y}")

        result = [None]

        # 제목
        tk.Label(dialog, text="표시 문구 편집",
                font=("Pretendard", 20, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=20)

        # 설명
        tk.Label(dialog, text="쉼표(,) 또는 \\n 으로 줄바꿈",
                font=("Pretendard", 12), bg="#F5F5F5", fg="#7F8C8D").pack(pady=(0, 10))

        # 입력 프레임 (스크롤 가능 영역)
        input_frame = tk.Frame(dialog, bg="#F5F5F5")
        input_frame.pack(fill="both", expand=True, padx=40, pady=(10, 0))

        tk.Label(input_frame, text="문구 내용:",
                font=("Pretendard", 13, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(anchor="w", pady=(0, 8))

        # Text 위젯 사용 (여러 줄 입력) - 키보드 공간을 고려하여 높이 조정
        text_widget = tk.Text(input_frame, font=("Pretendard", 13), width=60, height=6,
                             relief="solid", bd=2, wrap="word")
        text_widget.insert("1.0", self.cfg.value_text)
        text_widget.pack(fill="both", expand=True, pady=(0, 10))
        text_widget.focus()
        
        # 내장 가상 키보드 생성 및 항상 표시
        virtual_keyboard = SimpleVirtualKeyboard(input_frame, text_widget)
        virtual_keyboard.show()  # 항상 표시

        # 버튼 프레임 (다이얼로그의 직접 자식으로, 항상 하단에 고정)
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=(10, 20), padx=40)

        def on_save():
            """저장 버튼 클릭 핸들러"""
            try:
                print("[표시 문구 편집] 저장 버튼 클릭됨")
                new_text = text_widget.get("1.0", "end-1c")
                print(f"[표시 문구 편집] 읽은 텍스트 길이: {len(new_text)}")
                result[0] = new_text
                print("[표시 문구 편집] result[0] 설정 완료, 다이얼로그 닫기")
                dialog.destroy()
            except Exception as e:
                print(f"[표시 문구 편집] 저장 버튼 오류: {e}")
                import traceback
                traceback.print_exc()
                from tkinter import messagebox
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}", parent=dialog)

        def on_cancel():
            """취소 버튼 클릭 핸들러"""
            print("[표시 문구 편집] 취소 버튼 클릭됨")
            dialog.destroy()

        btn_save = tk.Button(button_frame, text="✓ 저장", command=on_save,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF")
        btn_save.pack(side="left", padx=5, ipady=12)
        
        # 저장 버튼이 제대로 생성되었는지 확인
        print(f"[표시 문구 편집] 저장 버튼 생성 완료: {btn_save}")

        btn_cancel = tk.Button(button_frame, text="✕ 취소", command=on_cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF")
        btn_cancel.pack(side="right", padx=5, ipady=12)
        
        # Enter 키로 저장 (다이얼로그 레벨)
        dialog.bind("<Return>", lambda e: on_save())
        dialog.bind("<Escape>", lambda e: on_cancel())

        dialog.wait_window()

        if result[0] is not None:
            # 설정 저장
            self.cfg.value_text = result[0]
            try:
                self.cfg.save()
                print(f"[표시 문구 편집] 저장 완료: {result[0][:50]}...")
            except Exception as e:
                print(f"[표시 문구 편집] 저장 오류: {e}")
                from tkinter import messagebox
                messagebox.showerror("저장 오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")
            
            # 모든 패널에 실시간 반영
            for p in self.panels.values():
                try:
                    # 헤더에 통합된 안전문구 업데이트
                    if hasattr(p, 'header') and hasattr(p.header, 'update_safety_message'):
                        p.header.update_safety_message(result[0])
                except Exception as e:
                    print(f"[표시 문구 편집] 패널 반영 오류: {e}")

            print(f"[표시 문구 편집] 모든 패널에 반영 완료")

    def _show_virtual_keyboard_for_text(self, text_widget):
        """표시문구편집용 화상키보드 표시"""
        print("표시문구편집용 화상키보드 실행 시도 중...")
        
        try:
            import subprocess
            import os
            
            # Ubuntu: onboard 또는 florence 시도
            try:
                # 우선 onboard
                p = subprocess.Popen(['onboard'])
                print("onboard 실행 시도")
                try:
                    text_widget.focus_force()
                except Exception:
                    pass
                return
            except Exception as e:
                print(f"onboard 실행 실패: {e}")
            try:
                p = subprocess.Popen(['florence'])
                print("florence 실행 시도")
                try:
                    text_widget.focus_force()
                except Exception:
                    pass
                return
            except Exception as e:
                print(f"florence 실행 실패: {e}")
            print("Linux 화상키보드 실행 실패 - onboard/florence 설치 필요")
                    
        except Exception as e:
            print(f"화상키보드 실행 중 오류 (표시문구편집): {e}")

    def refresh_alert_thresholds(self):
        """경보 임계값 실시간 적용"""
        try:
            # 모든 패널의 경보 임계값 새로고침
            for panel in self.panels.values():
                if hasattr(panel, 'refresh_alert_thresholds'):
                    panel.refresh_alert_thresholds()
            print("경보 임계값이 실시간으로 적용되었습니다.")
        except Exception as e:
            print(f"경보 임계값 실시간 적용 오류: {e}")

    def edit_alert_settings(self):
        """5단계 경보 시스템 설정 편집"""
        from tkinter import messagebox
        if not self.cfg.admin_mode:
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return
            
        try:
            from .alert_settings import AlertSettingsDialog
            dialog = AlertSettingsDialog(self, self.cfg)
            dialog.show()
        except Exception as e:
            messagebox.showerror("오류", f"설정 창을 열 수 없습니다:\n{str(e)}")

    def edit_thresholds(self):
        """임계치/환경값 편집 - 통합 다이얼로그"""
        if not self._verify_settings_password():
            return

        dialog = tk.Toplevel(self)
        dialog.title("임계치 및 환경값 설정")
        dialog.geometry("700x825")  # 높이 10% 확대
        dialog.transient(self)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        # 다이얼로그 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (750 // 2)
        dialog.geometry(f"700x750+{x}+{y}")

        # 메인 프레임 (스크롤 가능)
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 설명 라벨
        ttk.Label(main_frame, text="센서 임계치 및 환경 설정값을 수정하세요").pack(pady=(0, 10))

        # 입력 필드와 기본값을 저장할 딕셔너리
        entries = {}
        defaults = {}  # 초기화 버튼용 기본값 저장

        def create_setting_row(parent_frame, key, label, current_value, default_value):
            """설정 행 생성 (현재값 표시 + 입력 박스 + 초기화 버튼)"""
            row = ttk.Frame(parent_frame)
            row.pack(fill="x", pady=3)

            # 라벨
            ttk.Label(row, text=label, width=20, anchor="w").pack(side="left")

            # 현재값 표시
            current_label = ttk.Label(row, text=f"현재: {current_value}",
                                     width=12, anchor="e", foreground="blue")
            current_label.pack(side="left", padx=(0, 5))

            # 입력 박스
            entry = ttk.Entry(row, width=12)
            entry.insert(0, str(current_value))
            entry.pack(side="left", padx=5)

            # 초기화 버튼
            def reset_value():
                entry.delete(0, tk.END)
                entry.insert(0, str(default_value))

            reset_btn = tk.Button(row, text="↺", command=reset_value,
                                 bg="#E67E22", fg="#FFFFFF", font=("Pretendard", 9, "bold"),
                                 relief="raised", bd=2, width=4, height=1,
                                 activebackground="#D35400", activeforeground="#FFFFFF")
            reset_btn.pack(side="left", padx=2)

            # 기본값 표시 (툴팁처럼)
            default_label = ttk.Label(row, text=f"(기본: {default_value})",
                                     foreground="gray")
            default_label.pack(side="left", padx=5)

            return entry

        # === 가스 센서 기준값 섹션 ===
        gas_frame = ttk.LabelFrame(main_frame, text="가스 센서 기준값", padding="10")
        gas_frame.pack(fill="x", pady=5)

        gas_settings = [
            ("co2", "이산화탄소 기준 (ppm)", self.cfg.std["co2"], 15000.0),
            ("h2s", "황화수소 기준 (ppm)", self.cfg.std["h2s"], 10.0),
            ("co", "일산화탄소 기준 (ppm)", self.cfg.std["co"], 30.0),
            ("o2_min", "산소 하한 (%)", self.cfg.std["o2_min"], 18.0),
            ("o2_max", "산소 상한 (%)", self.cfg.std["o2_max"], 23.5),
        ]

        for key, label, current, default in gas_settings:
            entry = create_setting_row(gas_frame, key, label, current, default)
            entries[("std", key)] = entry
            defaults[("std", key)] = default

        # === 온도 환경값 섹션 ===
        temp_frame = ttk.LabelFrame(main_frame, text="온도 환경값 (℃)", padding="10")
        temp_frame.pack(fill="x", pady=5)

        temp_settings = [
            ("temp_min", "권장 하한", self.cfg.env["temp_min"], 18.0),
            ("temp_max", "권장 상한", self.cfg.env["temp_max"], 30.0),
            ("temp_caution", "주의 레벨", self.cfg.env["temp_caution"], 33.0),
            ("temp_warning", "경고 레벨", self.cfg.env["temp_warning"], 35.0),
            ("temp_danger", "위험 레벨", self.cfg.env["temp_danger"], 38.0),
        ]

        for key, label, current, default in temp_settings:
            entry = create_setting_row(temp_frame, key, label, current, default)
            entries[("env", key)] = entry
            defaults[("env", key)] = default

        # === 습도 환경값 섹션 ===
        hum_frame = ttk.LabelFrame(main_frame, text="습도 환경값 (%)", padding="10")
        hum_frame.pack(fill="x", pady=5)

        hum_settings = [
            ("hum_min", "습도 하한", self.cfg.env["hum_min"], 40.0),
            ("hum_max", "습도 상한", self.cfg.env["hum_max"], 65.0),
        ]

        for key, label, current, default in hum_settings:
            entry = create_setting_row(hum_frame, key, label, current, default)
            entries[("env", key)] = entry
            defaults[("env", key)] = default

        # === 안전 교육 설정 섹션 ===
        safety_frame = ttk.LabelFrame(main_frame, text="안전 교육 설정", padding="10")
        safety_frame.pack(fill="x", pady=5)

        # 사진 촬영 체크박스
        photo_var = tk.BooleanVar(value=self.cfg.env.get("safety_education_photo", True))

        photo_row = ttk.Frame(safety_frame)
        photo_row.pack(fill="x", pady=5)

        ttk.Label(photo_row, text="얼굴 촬영 활성화", width=20, anchor="w").pack(side="left")

        photo_check = ttk.Checkbutton(photo_row, text="안전 교육 시 얼굴 촬영",
                                     variable=photo_var)
        photo_check.pack(side="left", padx=5)

        # 체크박스 변수를 entries에 저장 (특별 처리)
        entries[("env", "safety_education_photo")] = photo_var

        # === 버튼 영역 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))

        def on_reset_all():
            """전체 초기화 버튼"""
            if messagebox.askyesno("전체 초기화",
                                  "모든 값을 기본값으로 초기화하시겠습니까?",
                                  parent=dialog):
                for (category, key), entry in entries.items():
                    default_value = defaults[(category, key)]
                    entry.delete(0, tk.END)
                    entry.insert(0, str(default_value))

        def on_save():
            """저장 버튼 클릭"""
            try:
                # 모든 입력값 검증 및 적용
                for (category, key), entry in entries.items():
                    # 체크박스인 경우 (BooleanVar)
                    if isinstance(entry, tk.BooleanVar):
                        if category == "env":
                            self.cfg.env[key] = entry.get()
                    else:
                        # 숫자 입력인 경우
                        try:
                            value = float(entry.get())
                            if category == "std":
                                self.cfg.std[key] = value
                            elif category == "env":
                                self.cfg.env[key] = value
                        except ValueError:
                            messagebox.showerror("입력 오류",
                                               f"'{key}' 값이 올바르지 않습니다.\n숫자를 입력하세요.",
                                               parent=dialog)
                            return

                # 설정을 config 파일에 자동 저장
                self.cfg.save()

                messagebox.showinfo("설정 완료",
                                  "임계치/환경값이 적용되고 config.conf에 저장되었습니다.",
                                  parent=dialog)
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("오류", f"설정 저장 중 오류 발생:\n{e}", parent=dialog)

        def on_cancel():
            """취소 버튼 클릭"""
            dialog.destroy()

        # 버튼 배치: 왼쪽에 전체 초기화, 오른쪽에 저장/취소
        tk.Button(button_frame, text="전체 초기화", command=on_reset_all,
                 bg="#F39C12", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                 relief="raised", bd=2, width=18, height=2,
                 activebackground="#E67E22", activeforeground="#FFFFFF").pack(side="left", padx=8)

        right_buttons = tk.Frame(button_frame)
        right_buttons.pack(side="right")
        tk.Button(right_buttons, text="저장", command=on_save,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                 relief="raised", bd=2, width=18, height=2,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=8)
        tk.Button(right_buttons, text="취소", command=on_cancel,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 10, "bold"),
                 relief="raised", bd=2, width=18, height=2,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="left", padx=8)

        # 다이얼로그 모달 실행
        dialog.wait_window()

    def save_config(self):
        """설정 저장"""
        # 현재 타일 배율과 문구 배율을 config에 반영하여 저장
        self.cfg.ui["tile_scale"] = f"{self.tile_scale.get():.2f}"
        self.cfg.ui["header_scale"] = f"{self.header_scale.get():.2f}"
        self.cfg.ui["status_text_scale"] = f"{self.status_text_scale.get():.2f}"
        self.cfg.save()
        self.logs.write_run("config saved")
        messagebox.showinfo("저장", f"설정 저장 완료: {self.cfg.path}\n\n타일 크기: {self.tile_scale.get():.2f}\n문구 크기: {self.header_scale.get():.2f}\n현재상태 문구 크기: {self.status_text_scale.get():.2f}")

    def view_safety_photos(self):
        """안전 교육 사진 관리"""
        # 관리자 모드/비밀번호와 무관하게 사용 가능

        from .safety_photo_viewer import SafetyPhotoViewer
        viewer = SafetyPhotoViewer(self)
        viewer.show()

    def _show_integrity_verification(self):
        """무결성 검증 대화상자 표시"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .integrity_verification import IntegrityVerificationDialog
            # IntegrityVerificationDialog가 자체적으로 설치 디렉토리 기준 경로를 사용함
            dialog = IntegrityVerificationDialog(self)
            dialog.show()
        except Exception as e:
            from tkinter import messagebox
            import traceback
            traceback.print_exc()
            messagebox.showerror("오류", f"무결성 검증 창을 열 수 없습니다:\n{str(e)}")

    # 기록 반출 기능은 안전교육 사진 관리에 통합됨 (v1.9.7)
    # def _show_export_archive(self):
    #     """기록 반출 대화상자 표시"""
    #     pass

    def _show_sensor_statistics(self):
        """센서값 통계 검색 대화상자 표시"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .sensor_statistics import SensorStatisticsDialog
            dialog = SensorStatisticsDialog(self, self)
            dialog.show()
        except Exception as e:
            from tkinter import messagebox
            import traceback
            traceback.print_exc()
            messagebox.showerror("오류", f"센서값 통계 검색 창을 열 수 없습니다:\n{str(e)}")

    def view_capture_files(self):
        """캡쳐 파일 관리"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return
            
        if not self._verify_settings_password():
            return

        try:
            from .capture_manager import CaptureManager
            mgr = CaptureManager(self)
            mgr.show()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"캡쳐 파일 관리 창을 열 수 없습니다:\n{str(e)}")

    def manage_safety_posters(self):
        """안전 교육 포스터 관리"""
        # 관리자 모드/비밀번호와 무관하게 사용 가능

        from .safety_poster_manager import SafetyPosterManager
        manager = SafetyPosterManager(self)
        manager.show()

    def manage_blueprints(self):
        """도면 관리"""
        # 관리자 모드/비밀번호와 무관하게 사용 가능

        from .blueprint_manager import BlueprintManager
        manager = BlueprintManager(self)
        manager.show()
        # 다이얼로그 닫힌 후 모든 센서 패널의 도면 뷰 새로고침
        for panel in self.panels.values():
            if hasattr(panel, 'blueprint_view') and panel.blueprint_view is not None:
                panel.blueprint_view._load_blueprint_list()

    def manage_face_registration(self):
        """얼굴 등록 관리"""
        try:
            from .face_registration_manager import FaceRegistrationManager
            import traceback
            manager = FaceRegistrationManager(self, self)
            manager.show()
        except ImportError as e:
            from tkinter import messagebox

            # Ubuntu Linux 전용 설치 안내 메시지
            error_detail = str(e)

            error_msg = (
                "얼굴 등록 관리 기능을 사용하려면 InsightFace 라이브러리가 필요합니다.\n\n"
                f"오류 내용: {error_detail}\n\n"
                "📦 설치 방법:\n"
                "  터미널에서 다음 명령을 실행:\n"
                "  pip install insightface onnxruntime\n\n"
                "⚠️ 참고:\n"
                "  - 설치 완료 후 프로그램을 재시작하세요\n"
                "  - 인터넷 연결이 필요합니다"
            )
            messagebox.showerror("라이브러리 설치 필요", error_msg, parent=self)
            import traceback
            print(f"[얼굴 등록 관리] Import 오류:\n{traceback.format_exc()}")
        except Exception as e:
            from tkinter import messagebox
            import traceback
            error_msg = f"얼굴 등록 관리 창을 열 수 없습니다:\n{str(e)}\n\n상세 정보는 콘솔을 확인하세요."
            messagebox.showerror("오류", error_msg, parent=self)
            print(f"[얼굴 등록 관리] 실행 오류:\n{traceback.format_exc()}")

    def enter_admin_mode(self):
        """관리자 모드 진입 (숫자 패드 암호 입력)"""
        # 이미 관리자 모드면 일반 모드로 전환
        if self.cfg.admin_mode:
            if self._show_custom_confirm("일반 모드 전환", "관리자 모드를 종료하고\n일반 모드로 전환하시겠습니까?"):
                self.exit_admin_mode()
            return

        # 숫자 패드 암호 입력
        try:
            from .admin_password_dialog import AdminPasswordDialog
            from ..utils.password_hasher import PasswordHasher
            
            dialog = AdminPasswordDialog(self, stored_password_hash=self.cfg.admin["admin_password"])
            if dialog.show():
                # 입력된 비밀번호는 이미 AdminPasswordDialog에서 검증됨
                entered_password = dialog.password_var.get()
                
                # 관리자 모드 활성화
                self.cfg.admin_mode = True
                self.cfg.admin["admin_mode"] = True
                self.cfg.save()
                self._update_admin_mode_menu()
                self._update_admin_mode_indicator()
                
                # 윈도우 모니터링과 키보드 차단 기능 제거됨
                
                # 최초 진입 시 비밀번호 변경 강제
                if not self.cfg.admin["password_changed"]:
                    self._show_custom_info("비밀번호 변경 필요", "보안을 위해 관리자 비밀번호를 변경해주세요.")
                    self.change_admin_password()
                else:
                    self._show_custom_info("관리자 모드", "관리자 모드로 진입했습니다.\n\n설정 메뉴에 접근할 수 있습니다.")
            else:
                self._show_custom_info("취소", "관리자 모드 진입이 취소되었습니다.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"관리자 모드 진입 중 오류가 발생했습니다:\n{str(e)}")

    def open_camera_settings(self):
        """카메라 설정 열기"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .camera_settings import CameraSettingsDialog

            dialog = CameraSettingsDialog(self, self.cfg)
            result = dialog.show()

            if result:
                self._show_custom_info("완료", "카메라 설정이 저장되었습니다.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"카메라 설정 열기 중 오류가 발생했습니다:\n{str(e)}")

    def open_ai_advanced_settings(self):
        """AI 고급 설정 열기 (메인 메뉴에서 직접 접근)"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .camera_advanced_settings import CameraAdvancedSettingsDialog

            dialog = CameraAdvancedSettingsDialog(self, self.cfg)
            dialog.show()
            # 비차단 방식이므로 결과 처리는 다이얼로그 내부에서 수행

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"AI 고급 설정 열기 중 오류가 발생했습니다:\n{str(e)}")

    def open_environment_settings(self):
        """환경설정 열기"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .environment_settings import EnvironmentSettingsDialog

            dialog = EnvironmentSettingsDialog(self, self.cfg)
            result = dialog.show()

            if result:
                self._show_custom_info("완료", "환경설정이 저장되었습니다.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"환경설정 열기 중 오류가 발생했습니다:\n{str(e)}")

    def open_performance_settings(self):
        """성능 설정 열기"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return

        try:
            from .performance_settings import PerformanceSettingsDialog

            dialog = PerformanceSettingsDialog(self, self.cfg)
            result = dialog.show()

            if result:
                self._show_custom_info("완료", "성능 설정이 저장되었습니다.\n일부 설정은 프로그램 재시작 후 적용됩니다.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"성능 설정 열기 중 오류가 발생했습니다:\n{str(e)}")

    def change_admin_password(self):
        """관리자 비밀번호 변경"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return
            
        try:
            from .admin_password_change_dialog import AdminPasswordChangeDialog
            from ..utils.password_hasher import PasswordHasher
            
            dialog = AdminPasswordChangeDialog(self, current_password_hash=self.cfg.admin["admin_password"])
            result, new_password = dialog.show()
            
            if result and new_password:
                # 비밀번호 변경 성공 - 해시로 저장
                hashed_password = PasswordHasher.hash_password(new_password)
                self.cfg.admin["admin_password"] = hashed_password
                self.cfg.admin["password_changed"] = True
                self.cfg.save()
                self._show_custom_info("비밀번호 변경", f"관리자 비밀번호가 성공적으로 변경되었습니다.\n새 비밀번호: {new_password}")
            else:
                self._show_custom_info("취소", "비밀번호 변경이 취소되었습니다.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"비밀번호 변경 중 오류가 발생했습니다:\n{str(e)}")

    def exit_admin_mode(self):
        """관리자 모드 종료"""
        self.cfg.admin_mode = False
        self.cfg.admin["admin_mode"] = False
        self.cfg.save()
        self._update_admin_mode_menu()
        self._update_admin_mode_indicator()
        
        # 윈도우 모니터링과 키보드 차단 기능 제거됨
        
        self._show_custom_info("일반 모드", "일반 모드로 전환되었습니다.")

    def restart_app(self):
        """프로그램 재시작 (관리자 전용)"""
        if not self.cfg.admin_mode:
            from tkinter import messagebox
            messagebox.showerror("접근 거부", "관리자 모드에서만 접근할 수 있습니다.")
            return
        
        # 재시작 확인 다이얼로그
        if not self._show_custom_confirm("프로그램 재시작", "프로그램을 재시작하시겠습니까?\n\n재시작 후 자동으로 다시 시작됩니다."):
            return
        
        # 재시작 신호 파일 생성 (watchdog가 감지하여 재시작)
        try:
            restart_signal_file = os.path.join(get_base_dir(), "restart.signal")
            with open(restart_signal_file, 'w', encoding='utf-8') as f:
                f.write(f"restart_{int(time.time())}")
            print(f"[재시작] 재시작 신호 파일 생성: {restart_signal_file}")
        except Exception as e:
            print(f"[재시작] 재시작 신호 파일 생성 실패: {e}")
            from tkinter import messagebox
            messagebox.showerror("오류", f"재시작 신호 파일 생성 중 오류가 발생했습니다:\n{str(e)}")
            return
        
        # 로그 기록
        try:
            self.logs.write_run("program restart requested by admin")
        except Exception:
            pass
        
        # 프로그램 종료 (watchdog가 재시작 신호를 감지하고 자동으로 재시작)
        self.after(500, self.exit_app)  # 0.5초 후 종료

    def _update_admin_mode_menu(self):
        """관리자 모드 메뉴 업데이트"""
        self._setup_menu()
        self._setup_view_menu()  # 보기 메뉴도 업데이트
        
        # 모든 패널의 도면 뷰에서 관리자 모드 버튼 업데이트
        for panel in self.panels.values():
            if hasattr(panel, 'blueprint_view') and panel.blueprint_view is not None:
                panel.blueprint_view.update_admin_mode()

    def _update_admin_mode_indicator(self):
        """관리자 모드 표시 업데이트"""
        # 모든 패널의 헤더에 관리자 모드 표시 업데이트
        for panel in self.panels.values():
            if hasattr(panel, 'header'):
                panel.header.update_admin_mode_indicator()

    def _show_custom_confirm(self, title, message):
        """커스텀 확인 다이얼로그"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("500x290")  # 높이 20% 추가 확대 (242 * 1.2 = 290)
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (145)
        dialog.geometry(f"500x290+{x}+{y}")

        result = [False]

        # 제목
        tk.Label(dialog, text=title,
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=20)

        # 메시지
        tk.Label(dialog, text=message,
                font=("Pretendard", 13), bg="#F5F5F5", fg="#2C3E50",
                justify="center").pack(pady=15)

        # 버튼 프레임
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=40)

        def on_yes():
            result[0] = True
            dialog.destroy()

        def on_no():
            dialog.destroy()

        tk.Button(button_frame, text="✓ 예", command=on_yes,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(side="left", padx=5, ipady=13)

        tk.Button(button_frame, text="✕ 아니오", command=on_no,
                 bg="#95A5A6", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#7F8C8D", activeforeground="#FFFFFF").pack(side="right", padx=5, ipady=13)

        dialog.wait_window()
        return result[0]

    def _show_custom_info(self, title, message):
        """커스텀 정보 다이얼로그 (관리자 모드 취소 화면과 같은 구조, 높이 40% 확장)"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("500x317")  # 높이 40% 확장 (220 -> 264 -> 317)
        dialog.configure(bg="#F5F5F5")
        dialog.transient(self)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        # 중앙 배치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (158)
        dialog.geometry(f"500x317+{x}+{y}")

        # 제목
        tk.Label(dialog, text=title,
                font=("Pretendard", 18, "bold"), bg="#F5F5F5", fg="#2C3E50").pack(pady=20)

        # 메시지
        tk.Label(dialog, text=message,
                font=("Pretendard", 13), bg="#F5F5F5", fg="#2C3E50",
                justify="center").pack(pady=15)

        # 버튼 프레임 (하단 패딩 증가하여 버튼이 잘 보이도록)
        button_frame = tk.Frame(dialog, bg="#F5F5F5")
        button_frame.pack(side="bottom", fill="x", pady=(20, 30), padx=40)

        def on_ok():
            dialog.destroy()

        # 확인 버튼 (중앙 정렬, 관리자 모드 취소 화면과 같은 스타일)
        tk.Button(button_frame, text="✓ 확인", command=on_ok,
                 bg="#27AE60", fg="#FFFFFF", font=("Pretendard", 14, "bold"),
                 relief="raised", bd=3, width=15,
                 activebackground="#229954", activeforeground="#FFFFFF").pack(ipady=12)

        dialog.wait_window()

    def _force_tab_colors(self):
        """모든 탭의 색상을 강제로 적용"""
        try:
            for i in range(self.nb.index("end")):
                self.nb.tab(i, background="white", foreground="black")
        except Exception:
            pass

    # (reverted) 탭 텍스트는 원래대로 사용

    # (overview removed)

    # ----- 주기 작업 -----
    def _status_tick(self):
        """상태 틱 (1초마다) - 타임아웃 체크"""
        now = time.time()

        # 각 패널의 마지막 수신 시간 체크
        for key, state in list(self.states.items()):
            # 대기 패널은 건너뛰기
            if key == "__waiting__":
                continue

            last_rx = state.get("last_rx")
            if last_rx is None:
                continue

            panel = self.panels.get(key)
            if not panel:
                continue

            # 타임아웃 체크
            elapsed = now - last_rx
            if elapsed > self.connection_timeout:
                # 통신 끊김 상태로 변경
                if panel._connection_status != "disconnected":
                    panel._show_disconnected_status()
                    # 탭 제목 업데이트
                    self._update_tab_title(key, panel)
            else:
                # 정상 연결 상태
                if panel._connection_status == "disconnected":
                    # 재연결됨 (다음 데이터 수신 시 자동으로 connected로 변경됨)
                    pass

        self.after(1000, self._status_tick)

        # 탭 외관 주기적 업데이트(최대 경보 레벨 색 반영)
        try:
            for k in list(self.panels.keys()):
                self._update_tab_appearance(k)
        except Exception:
            pass

    def _blink_tick(self):
        """깜빡임 토글 및 탭 갱신"""
        try:
            self._blink_on = not getattr(self, '_blink_on', False)
            for k in list(self.panels.keys()):
                self._update_tab_appearance(k)
        except Exception:
            pass
        try:
            self.after(600, self._blink_tick)
        except Exception:
            pass

    def _minute_tick(self):
        """분 틱 (1분마다) - 현재는 사용하지 않음 (실시간 로깅으로 변경됨)"""
        # 데이터는 on_data에서 실시간으로 기록됨
        self.after(60*1000, self._minute_tick)
    
    def _maintain_focus(self):
        """매니저 프로그램이 항상 최우선 포커스를 유지하도록 주기적으로 체크"""
        try:
            # 매니저 프로그램이 최상단에 오도록 설정
            if self.winfo_exists():
                # 모든 다이얼로그가 최상단에 오도록 확인
                for child in self.winfo_children():
                    if isinstance(child, tk.Toplevel):
                        try:
                            if child.winfo_exists():
                                child.attributes("-topmost", True)
                                child.lift()
                        except:
                            pass
                
                # 매니저 메인 윈도우도 최상단 유지
                if self._is_fullscreen:
                    self.attributes("-topmost", True)
                self.lift()
                
                # 0.5초 후 다시 체크
                self.after(500, self._maintain_focus)
        except:
            # 오류 발생 시에도 계속 실행
            try:
                self.after(500, self._maintain_focus)
            except:
                pass

    def show_about(self):
        """About 다이얼로그 표시"""
        about_dialog = AboutDialog(self, config=self.cfg)
        about_dialog.show()
        return

    def _show_report_viewer(self):
        """보고서 보기 - 독립적인 PDF 보고서 뷰어"""
        try:
            from tkinter import filedialog
            from ..utils.helpers import get_base_dir

            # 보고서 디렉토리 기본 경로 - reports 폴더 우선
            base_dir = get_base_dir()
            reports_dir = os.path.join(base_dir, "reports")

            # reports 폴더가 없으면 생성
            if not os.path.exists(reports_dir):
                try:
                    os.makedirs(reports_dir, exist_ok=True)
                except Exception:
                    # 생성 실패 시 data/reports 시도
                    data_reports_dir = os.path.join(base_dir, "data", "reports")
                    if os.path.exists(data_reports_dir):
                        reports_dir = data_reports_dir
                    else:
                        # 둘 다 없으면 base_dir 사용
                        reports_dir = base_dir

            # 파일 선택 다이얼로그
            filepath = filedialog.askopenfilename(
                parent=self,
                title="보고서 파일 선택",
                initialdir=reports_dir,
                filetypes=[
                    ("PDF 파일", "*.pdf"),
                    ("모든 파일", "*.*")
                ]
            )

            if not filepath:
                return  # 사용자가 취소함

            if not os.path.exists(filepath):
                from tkinter import messagebox
                messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{filepath}", parent=self)
                return

            # 내장 PDF 뷰어 열기
            self._open_builtin_pdf_viewer(filepath)

        except Exception as e:
            import traceback
            print(f"보고서 보기 오류:\n{traceback.format_exc()}")
            from tkinter import messagebox
            messagebox.showerror("오류", f"보고서 보기 오류:\n{e}", parent=self)

    def _open_builtin_pdf_viewer(self, filepath: str):
        """내장 PDF 뷰어로 파일 열기"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror(
                "오류",
                "PDF 뷰어를 사용하려면 PyMuPDF가 필요합니다.\n"
                "설치 명령: pip install PyMuPDF",
                parent=self
            )
            return

        try:
            from PIL import Image, ImageTk
            from tkinter import ttk, messagebox

            # PDF 열기
            doc = fitz.open(filepath)
            total_pages = len(doc)

            if total_pages == 0:
                messagebox.showerror("오류", "PDF 파일에 페이지가 없습니다.", parent=self)
                doc.close()
                return

            # PDF 뷰어 다이얼로그 생성
            pdf_dialog = tk.Toplevel(self)
            pdf_dialog.title(f"📄 보고서 뷰어 - {os.path.basename(filepath)}")
            pdf_dialog.geometry("900x1000")
            pdf_dialog.configure(bg="#2C3E50")

            # 중앙 배치
            pdf_dialog.update_idletasks()
            x = (pdf_dialog.winfo_screenwidth() // 2) - (900 // 2)
            y = (pdf_dialog.winfo_screenheight() // 2) - (1000 // 2)
            pdf_dialog.geometry(f"900x1000+{x}+{y}")

            # 최상위로 표시 및 포커스
            pdf_dialog.attributes("-topmost", True)
            pdf_dialog.lift()
            pdf_dialog.focus_force()

            # 잠시 후 topmost 해제 (다른 창 사용 가능하도록)
            def release_topmost():
                try:
                    if pdf_dialog.winfo_exists():
                        pdf_dialog.attributes("-topmost", False)
                except:
                    pass
            pdf_dialog.after(200, release_topmost)

            # 모달 설정
            pdf_dialog.transient(self)
            pdf_dialog.grab_set()

            # 현재 페이지 변수
            current_page = [0]

            # 상단 툴바
            toolbar = tk.Frame(pdf_dialog, bg="#34495E", height=50)
            toolbar.pack(fill="x", padx=5, pady=5)
            toolbar.pack_propagate(False)

            # 파일 열기 버튼
            open_btn = tk.Button(
                toolbar,
                text="📂 다른 파일",
                font=("Pretendard", 10, "bold"),
                bg="#27AE60",
                fg="#FFFFFF",
                width=12,
                command=lambda: self._open_another_pdf(pdf_dialog, doc)
            )
            open_btn.pack(side="left", padx=5, pady=5)

            # 제목
            title_label = tk.Label(
                toolbar,
                text=f"📄 {os.path.basename(filepath)}",
                font=("Pretendard", 11, "bold"),
                bg="#34495E",
                fg="#FFFFFF"
            )
            title_label.pack(side="left", padx=10)

            # 페이지 컨트롤
            nav_frame = tk.Frame(toolbar, bg="#34495E")
            nav_frame.pack(side="right", padx=10)

            # 이전 페이지 버튼
            prev_btn = tk.Button(
                nav_frame,
                text="◀ 이전",
                font=("Pretendard", 10, "bold"),
                bg="#3498DB",
                fg="#FFFFFF",
                width=8,
                command=lambda: go_to_page(current_page[0] - 1)
            )
            prev_btn.pack(side="left", padx=5)

            # 페이지 표시 레이블
            page_label = tk.Label(
                nav_frame,
                text=f"1 / {total_pages}",
                font=("Pretendard", 11, "bold"),
                bg="#34495E",
                fg="#FFFFFF",
                width=10
            )
            page_label.pack(side="left", padx=10)

            # 다음 페이지 버튼
            next_btn = tk.Button(
                nav_frame,
                text="다음 ▶",
                font=("Pretendard", 10, "bold"),
                bg="#3498DB",
                fg="#FFFFFF",
                width=8,
                command=lambda: go_to_page(current_page[0] + 1)
            )
            next_btn.pack(side="left", padx=5)

            # PDF 표시 영역 (스크롤 가능)
            canvas_frame = tk.Frame(pdf_dialog, bg="#1A252F")
            canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # 캔버스와 스크롤바
            canvas = tk.Canvas(canvas_frame, bg="#1A252F", highlightthickness=0)
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)

            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            v_scrollbar.pack(side="right", fill="y")
            h_scrollbar.pack(side="bottom", fill="x")
            canvas.pack(side="left", fill="both", expand=True)

            # 이미지 레이블 (캔버스 내부)
            pdf_image_label = tk.Label(canvas, bg="#1A252F")
            canvas.create_window((0, 0), window=pdf_image_label, anchor="nw")

            # PDF 이미지 참조 유지
            pdf_dialog.pdf_image = None
            pdf_dialog.doc = doc  # 문서 참조 저장

            def render_page(page_num):
                """특정 페이지 렌더링"""
                if page_num < 0 or page_num >= total_pages:
                    return

                current_page[0] = page_num
                page_label.config(text=f"{page_num + 1} / {total_pages}")

                # 버튼 상태 업데이트
                prev_btn.config(state="normal" if page_num > 0 else "disabled")
                next_btn.config(state="normal" if page_num < total_pages - 1 else "disabled")

                try:
                    page = doc.load_page(page_num)
                    # 고해상도 렌더링 (2x 스케일)
                    zoom = 2.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    # PIL Image로 변환
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # 창 크기에 맞게 조정 (최대 850px 너비)
                    max_width = 850
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                    # Tkinter 이미지로 변환
                    pdf_dialog.pdf_image = ImageTk.PhotoImage(img)
                    pdf_image_label.config(image=pdf_dialog.pdf_image)

                    # 스크롤 영역 업데이트
                    pdf_image_label.update_idletasks()
                    canvas.config(scrollregion=canvas.bbox("all"))

                    # 스크롤 맨 위로
                    canvas.yview_moveto(0)
                    canvas.xview_moveto(0)

                except Exception as e:
                    print(f"페이지 렌더링 오류: {e}")
                    pdf_image_label.config(text=f"페이지 렌더링 오류: {e}", image="")

            def go_to_page(page_num):
                """특정 페이지로 이동"""
                if 0 <= page_num < total_pages:
                    render_page(page_num)

            # 키보드 바인딩
            def on_key(event):
                if event.keysym in ("Left", "Up", "Prior"):  # Prior = Page Up
                    go_to_page(current_page[0] - 1)
                elif event.keysym in ("Right", "Down", "Next"):  # Next = Page Down
                    go_to_page(current_page[0] + 1)
                elif event.keysym == "Home":
                    go_to_page(0)
                elif event.keysym == "End":
                    go_to_page(total_pages - 1)
                elif event.keysym == "Escape":
                    on_close()

            pdf_dialog.bind("<Key>", on_key)

            # 마우스 휠 스크롤
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            def on_mousewheel_linux(event):
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

            canvas.bind("<MouseWheel>", on_mousewheel)
            canvas.bind("<Button-4>", on_mousewheel_linux)
            canvas.bind("<Button-5>", on_mousewheel_linux)

            # 하단 버튼
            bottom_frame = tk.Frame(pdf_dialog, bg="#2C3E50", height=50)
            bottom_frame.pack(fill="x", padx=5, pady=5)

            # 닫기 버튼
            close_btn = tk.Button(
                bottom_frame,
                text="닫기",
                font=("Pretendard", 11, "bold"),
                bg="#E74C3C",
                fg="#FFFFFF",
                width=10,
                command=lambda: on_close()
            )
            close_btn.pack(side="right", padx=10, pady=5)

            # 다이얼로그 종료 시 PDF 닫기
            def on_close():
                try:
                    doc.close()
                except:
                    pass
                pdf_dialog.destroy()

            pdf_dialog.protocol("WM_DELETE_WINDOW", on_close)

            # 첫 페이지 렌더링
            render_page(0)

            # 포커스 설정
            pdf_dialog.focus_set()

        except Exception as e:
            import traceback
            print(f"PDF 뷰어 오류:\n{traceback.format_exc()}")
            from tkinter import messagebox
            messagebox.showerror("오류", f"PDF 뷰어 오류:\n{e}", parent=self)

    def _open_another_pdf(self, current_dialog, current_doc):
        """다른 PDF 파일 열기"""
        try:
            from tkinter import filedialog
            from ..utils.helpers import get_base_dir

            # 보고서 디렉토리 기본 경로
            base_dir = get_base_dir()
            reports_dir = os.path.join(base_dir, "data", "reports")
            if not os.path.exists(reports_dir):
                data_dir = os.path.join(base_dir, "data")
                reports_dir = data_dir if os.path.exists(data_dir) else base_dir

            # 파일 선택 다이얼로그
            filepath = filedialog.askopenfilename(
                parent=current_dialog,
                title="보고서 파일 선택",
                initialdir=reports_dir,
                filetypes=[
                    ("PDF 파일", "*.pdf"),
                    ("모든 파일", "*.*")
                ]
            )

            if not filepath:
                return

            if not os.path.exists(filepath):
                from tkinter import messagebox
                messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{filepath}", parent=current_dialog)
                return

            # 현재 다이얼로그 닫고 새 파일 열기
            try:
                current_doc.close()
            except:
                pass
            current_dialog.destroy()

            # 새 PDF 열기
            self._open_builtin_pdf_viewer(filepath)

        except Exception as e:
            import traceback
            print(f"다른 PDF 열기 오류:\n{traceback.format_exc()}")

    def _open_external_pdf_viewer(self, filepath: str):
        """외부 PDF 뷰어로 열기"""
        import subprocess
        import platform

        try:
            system = platform.system()
            if system == "Linux":
                subprocess.Popen(['xdg-open', filepath])
            elif system == "Darwin":
                subprocess.Popen(['open', filepath])
            elif system == "Windows":
                os.startfile(filepath)
            else:
                subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            print(f"외부 PDF 뷰어 열기 오류: {e}")

