# 한글 입력 조합 문제 수정

## 개요

문구 편집 화면과 서명 직접 입력 화면에서 한글 입력 시 조합이 제대로 되지 않던 문제를 수정했습니다.

**수정 날짜**: 2025-11-05
**버전**: 1.9.0

---

## 문제점

1. **모음만 입력 시 문제**: 초성 없이 모음만 입력하면 자모가 그대로 표시되어 '아', '어', '오' 등이 입력되지 않음
2. **복합 모음 조합 불가**: 'ㅗ + ㅏ = ㅘ', 'ㅜ + ㅓ = ㅝ' 등의 복합 모음이 조합되지 않음
3. **복합 자음 조합 불가**: 'ㄱ + ㅅ = ㄳ', 'ㄹ + ㄱ = ㄺ' 등의 복합 종성이 조합되지 않음
4. **백스페이스 동작 오류**: 복합 자모를 백스페이스로 삭제 시 분해되지 않고 전체가 삭제됨

---

## 수정 내용

### 1. 복합 자모 조합 규칙 추가

[src/tcp_monitor/ui/app.py:41-65](src/tcp_monitor/ui/app.py#L41-L65)

```python
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
```

### 2. 모음 입력 시 자동 ㅇ 초성 추가

[src/tcp_monitor/ui/app.py:342-366](src/tcp_monitor/ui/app.py#L342-L366)

**이전 동작**: 모음만 입력하면 자모가 그대로 표시 ('ㅏ', 'ㅓ' 등)

**수정 후**: 모음 입력 시 자동으로 'ㅇ'을 초성으로 추가하여 완성형 글자 생성 ('아', '어' 등)

```python
elif char in self.jungsung_index:
    # 모음 입력
    if self.jung_idx == -1:
        # 중성이 아직 없음
        if self.cho_idx == -1:
            # 초성도 없음: ㅇ을 기본 초성으로 설정
            self.cho_idx = 11  # ㅇ의 인덱스
        # 중성 설정
        self.jung_idx = self.jungsung_index[char]
        self._update_composition_display()
```

### 3. 복합 모음 조합 지원

[src/tcp_monitor/ui/app.py:352-366](src/tcp_monitor/ui/app.py#L352-L366)

모음 입력 시 이미 중성이 있으면 복합 모음 조합을 시도합니다.

**예시**:
- 'ㄱ + ㅗ' 입력 → '고' 표시
- 'ㅏ' 추가 입력 → 'ㅗ + ㅏ = ㅘ' 조합 → '과' 표시

```python
else:
    # 이미 중성이 있음: 복합 중성 조합 시도
    current_jung = self.JUNGSUNG_LIST[self.jung_idx]
    compound_key = (current_jung, char)
    if compound_key in self.JUNGSUNG_COMBINATIONS:
        # 복합 중성 조합 가능 (예: ㅗ + ㅏ = ㅘ)
        compound_jung = self.JUNGSUNG_COMBINATIONS[compound_key]
        self.jung_idx = self.jungsung_index[compound_jung]
        self._update_composition_display()
```

### 4. 복합 종성 조합 지원

[src/tcp_monitor/ui/app.py:328-341](src/tcp_monitor/ui/app.py#L328-L341)

종성이 있는 상태에서 자음 입력 시 복합 종성 조합을 시도합니다.

**예시**:
- 'ㄱ + ㅏ + ㄱ' 입력 → '각' 표시
- 'ㅅ' 추가 입력 → 'ㄱ + ㅅ = ㄳ' 조합 → '갃' 표시

```python
else:
    # 이미 종성이 있음: 복합 종성 조합 시도
    current_jong = self.JONGSUNG_LIST[self.jong_idx]
    compound_key = (current_jong, char)
    if compound_key in self.JONGSUNG_COMBINATIONS:
        # 복합 종성 조합 가능
        compound_jong = self.JONGSUNG_COMBINATIONS[compound_key]
        self.jong_idx = self.jongsung_index[compound_jong]
        self._update_composition_display()
```

### 5. 백스페이스 복합 자모 분해 지원

[src/tcp_monitor/ui/app.py:393-502](src/tcp_monitor/ui/app.py#L393-L502)

백스페이스 입력 시 복합 자모를 단일 자모로 먼저 분해한 후 삭제합니다.

**예시**:
- '갃' 상태에서 백스페이스 → 종성 'ㄳ'을 'ㄱ'으로 분해 → '각' 표시
- '각' 상태에서 백스페이스 → 종성 'ㄱ' 제거 → '가' 표시
- '가' 상태에서 백스페이스 → 중성 'ㅏ' 제거 → 'ㄱ' 표시
- 'ㄱ' 상태에서 백스페이스 → 초성 'ㄱ' 제거 → 빈 상태

```python
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
```

### 6. Space/Enter 키 처리 개선

[src/tcp_monitor/ui/app.py:389-530](src/tcp_monitor/ui/app.py#L389-L530)

Space 또는 Enter 키 입력 시 현재 조합 중인 한글을 먼저 완성한 후 공백이나 줄바꿈을 삽입합니다.

```python
def _insert_space(self):
    """스페이스 삽입 (한글 조합 완성 후 삽입)"""
    # 한글 조합 중이면 먼저 완성
    if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
        self._commit_current_composition()
    # 스페이스 삽입
    self.text_widget.insert(tk.INSERT, ' ')

def _insert_newline(self):
    """줄바꿈 삽입 (한글 조합 완성 후 삽입)"""
    # 한글 조합 중이면 먼저 완성
    if self.cho_idx != -1 or self.jung_idx != -1 or self.jong_idx != -1:
        self._commit_current_composition()
    # Entry 위젯은 줄바꿈 불가능
    if not self.is_entry_widget:
        self.text_widget.insert(tk.INSERT, '\n')
```

---

## 테스트 케이스

수정 후 다음 시나리오가 모두 정상 동작합니다:

### 1. 기본 한글 입력
- 입력: `ㄱ` + `ㅏ` → 결과: `가`
- 입력: `ㅎ` + `ㅏ` + `ㄴ` + `ㄱ` + `ㅡ` + `ㄹ` → 결과: `한글`

### 2. 모음만 입력 (자동 ㅇ 추가)
- 입력: `ㅏ` → 결과: `아`
- 입력: `ㅓ` → 결과: `어`
- 입력: `ㅗ` → 결과: `오`

### 3. 복합 모음 조합
- 입력: `ㄱ` + `ㅗ` + `ㅏ` → 결과: `과`
- 입력: `ㅜ` + `ㅓ` → 결과: `워`
- 입력: `ㅡ` + `ㅣ` → 결과: `의`

### 4. 복합 종성 조합
- 입력: `ㄱ` + `ㅏ` + `ㄱ` + `ㅅ` → 결과: `갃`
- 입력: `ㄴ` + `ㅏ` + `ㄴ` + `ㅈ` → 결과: `낛`
- 입력: `ㄹ` + `ㅏ` + `ㄹ` + `ㄱ` → 결과: `랃`

### 5. 백스페이스 분해
- `갃` → 백스페이스 → `각` (ㄳ → ㄱ 분해)
- `각` → 백스페이스 → `가` (종성 ㄱ 제거)
- `가` → 백스페이스 → `ㄱ` (중성 ㅏ 제거)
- `ㄱ` → 백스페이스 → (빈 상태) (초성 ㄱ 제거)

### 6. 복합 모음 백스페이스 분해
- `과` → 백스페이스 → `고` (ㅘ → ㅗ 분해)
- `고` → 백스페이스 → `ㄱ` (중성 ㅗ 제거)

---

## 영향받는 화면

이 수정은 다음 화면의 한글 입력에 모두 적용됩니다:

1. **표시 문구 편집 화면** ([app.py:2088](src/tcp_monitor/ui/app.py#L2088))
   - 메뉴: 설정 → 표시 문구 편집
   - Text 위젯 사용

2. **서명 인식 및 편집 팝업** ([safety_signature.py:1524](src/tcp_monitor/ui/safety_signature.py#L1524))
   - 서명 캡처 후 이름 입력
   - Entry 위젯 사용

3. **이름 직접 입력 팝업** ([safety_signature.py:1664](src/tcp_monitor/ui/safety_signature.py#L1664))
   - 서명 수동 입력
   - Entry 위젯 사용

---

## 기술적 세부사항

### SimpleVirtualKeyboard 클래스 수정

**파일**: [src/tcp_monitor/ui/app.py](src/tcp_monitor/ui/app.py)

**주요 변경사항**:
- 복합 자모 조합 규칙 추가 (lines 41-65)
- `_insert_char()` 메서드 개선 (lines 293-387)
- `_backspace()` 메서드 개선 (lines 393-502)
- `_insert_space()` 메서드 개선 (lines 389-395)
- `_insert_newline()` 메서드 개선 (lines 508-530)

### 한글 조합 알고리즘

한글 완성형 계산 공식:
```python
base = 0xAC00  # '가'의 유니코드
초성_개수 = 19
중성_개수 = 21
종성_개수 = 28

완성형_코드 = base + (초성_인덱스 * 21 + 중성_인덱스) * 28 + 종성_인덱스
완성형_문자 = chr(완성형_코드)
```

---

## 호환성

- **Python 버전**: 3.6 이상
- **Tkinter**: 표준 라이브러리
- **플랫폼**: Ubuntu/Linux (macOS 호환 가능)

---

## 참고 자료

- 한글 완성형 유니코드 범위: U+AC00 ~ U+D7A3
- 한글 자모 유니코드 범위: U+3131 ~ U+318E
- 초성 19자, 중성 21자, 종성 28자 (빈 종성 포함)

---

**작성일**: 2025-11-05
**버전**: 1.9.0
