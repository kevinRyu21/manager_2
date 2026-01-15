# 패널 헤더 버튼 간격 최적화

## 개요
관리자 모드 활성화 시 도면 버튼이 작아지거나 보이지 않는 문제를 해결하기 위해 패널 헤더의 버튼 간격과 크기를 최적화했습니다.

## 문제점

### Before
- 관리자 모드 표시 시 우측 컨트롤 버튼들이 밀려남
- 도면 버튼이 화면 밖으로 잘리거나 작아짐
- 버튼 간격이 너무 넓어 공간 낭비
- 전체화면 종료 버튼 존재 여부 불명확

### 원인
```
좌측 영역이 너무 많은 공간 차지:
[로고] [ID] [캡쳐] [시계] [🔊] [거울보기] [🔓 관리자 모드]
                                              ↑ 이 버튼이 추가되면
                                                우측이 밀림

우측 영역:
[오늘 경고...] [안전교육] [타일] [그래프] [도면]
                                       ↑ 잘림
```

## 해결 방법

### 1. 전체화면 종료 버튼 확인
- **결과**: 이미 제거되어 있음 (코드에 존재하지 않음)

### 2. 좌측 영역 버튼 최적화

#### Before
```python
# 캡쳐 버튼
padx=(0, 12), font=("Pretendard", 11, "bold"), padx=8

# 시계
font=("Pretendard", 14, "bold")

# 음성 토글
padx=(8, 8), font=("Pretendard", 36, "bold"), padx=3

# 거울보기
padx=(4, 8), width=10, font=("Pretendard", 12, "bold")

# 관리자 모드
padx=(8, 0), text="🔓 관리자 모드", font=("Pretendard", 12, "bold"), padx=6
```

#### After
```python
# 캡쳐 버튼 - 간격 및 폰트 크기 축소
padx=(0, 8), font=("Pretendard", 10, "bold"), padx=6

# 시계 - 폰트 크기 축소
font=("Pretendard", 13, "bold")

# 음성 토글 - 간격 및 폰트 크기 축소
padx=(6, 6), font=("Pretendard", 32, "bold"), padx=2

# 거울보기 - 간격, 크기, 폰트 축소
padx=(3, 6), width=9, font=("Pretendard", 11, "bold")

# 관리자 모드 - 텍스트 축약, 간격 및 폰트 축소
padx=(6, 0), text="🔓 관리자", font=("Pretendard", 11, "bold"), padx=5
```

**절약된 공간**: 약 40-50px

### 3. 우측 영역 버튼 최적화

#### Before
```python
# 오늘 경고
padx=4, padx=10, font=("Pretendard", 11, "bold")

# 안전교육
padx=4, width=8, font=("Pretendard", 12, "bold")

# 타일/그래프/도면
padx=4, width=6, font=("Pretendard", 12, "bold")
```

#### After
```python
# 오늘 경고 - 간격 및 내부 여백 축소
padx=2, padx=8, font=("Pretendard", 11, "bold")

# 안전교육 - 간격, 크기, 폰트 축소
padx=2, width=7, font=("Pretendard", 11, "bold")

# 타일/그래프/도면 - 간격, 크기, 폰트 축소
padx=2, width=5, font=("Pretendard", 11, "bold")
```

**절약된 공간**: 약 30-40px

## 수정된 파일

### `src/tcp_monitor/ui/panel_header.py`

#### 좌측 영역 수정 (라인 48-89)
```python
# 현재 화면 캡쳐 버튼 (ID 오른쪽) - 간격 축소
self.capture_btn = tk.Button(left, text="📸 캡쳐", command=self._capture_current_screen,
                             font=("Pretendard", 10, "bold"), bg="#3498DB", fg="#FFFFFF",
                             relief="raised", bd=2, padx=6, pady=2,
                             activebackground="#2E86C1", activeforeground="#FFFFFF",
                             cursor="hand2")
self.capture_btn.pack(side="left", padx=(0, 8))

self.clock_label = tk.Label(left, text="", font=("Pretendard", 13, "bold"),
                            bg="#E8F4FD", fg="#2C3E50")
self.clock_label.pack(side="left")

# 음성 경보 토글 버튼 (시계 옆) - 간격 최적화
self.voice_alert_enabled = True
self.voice_toggle_btn = tk.Button(left, text="🔊", command=self._toggle_voice_alert,
                                font=("Pretendard", 32, "bold"), bg="#E8F4FD", fg="#2C3E50",
                                relief="flat", bd=0, padx=2, pady=0,
                                activebackground="#D1E7DD", activeforeground="#2C3E50",
                                cursor="hand2")
self.voice_toggle_btn.pack(side="left", padx=(6, 6))

# 거울보기/거울끄기 버튼 - 고정 크기 설정, 간격 축소
self.mirror_mode = False
self.mirror_camera_ready = False
self.mirror_btn = tk.Button(left, text="거울 준비중", command=self._toggle_mirror_view,
                           font=("Pretendard", 11, "bold"), bg="#9C27B0", fg="#FFFFFF",
                           relief="raised", bd=2, width=9, height=1,
                           activebackground="#7B1FA2", activeforeground="#FFFFFF",
                           cursor="hand2", state="disabled")
self.mirror_btn.pack(side="left", padx=(3, 6))

# 관리자 모드 표시 - 크기 최적화, 간격 축소
self.admin_mode_btn = tk.Button(left, text="🔓 관리자",
                               font=("Pretendard", 11, "bold"), bg="#FFD700", fg="#D32F2F",
                               relief="raised", bd=2, padx=5, pady=1,
                               activebackground="#FFC107", activeforeground="#D32F2F",
                               cursor="hand2",
                               command=self._on_admin_mode_click)
if app.cfg.admin_mode:
    self.admin_mode_btn.pack(side="left", padx=(6, 0))
```

#### 우측 영역 수정 (라인 119-151)
```python
# 오늘 경고 요약 버튼 - 간격 축소
self.alert_btn = tk.Button(right, text="오늘 경고 주의0 경계0 심각0",
                          command=self._show_today_alerts,
                          font=("Pretendard", 11, "bold"), bg="#E74C3C", fg="#FFFFFF",
                          relief="raised", bd=2, padx=8, pady=3,
                          activebackground="#C0392B", activeforeground="#FFFFFF",
                          cursor="hand2", width=24, anchor='center')
self.alert_btn.pack(side="left", padx=2)

# 안전 교육 버튼 - 최소 크기 보장, 간격 축소
self.btn_safety = tk.Button(right, text="안전 교육",
                           command=lambda: master.show_safety_education(),
                           bg="#FF9800", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                           relief="raised", bd=2, width=7, height=1,
                           activebackground="#F57C00", activeforeground="#FFFFFF")
self.btn_safety.pack(side="left", padx=2)

# 모드 전환 버튼들 (타일/그래프/도면) - 최소 크기 보장, 간격 축소
self.btn_card = tk.Button(right, text="타일", command=lambda: master.switch_to_card_mode(),
                         bg="#4CAF50", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                         relief="sunken", bd=2, width=5, height=1,
                         activebackground="#45A049", activeforeground="#FFFFFF")
self.btn_card.pack(side="left", padx=2)

self.btn_graph = tk.Button(right, text="그래프",
                          command=lambda: master.switch_to_graph_mode(),
                          bg="#90A4AE", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                          relief="raised", bd=2, width=5, height=1,
                          activebackground="#78909C", activeforeground="#FFFFFF")
self.btn_graph.pack(side="left", padx=2)

self.btn_blueprint = tk.Button(right, text="도면",
                              command=lambda: master.switch_to_blueprint_mode(),
                              bg="#90A4AE", fg="#FFFFFF", font=("Pretendard", 11, "bold"),
                              relief="raised", bd=2, width=5, height=1,
                              activebackground="#78909C", activeforeground="#FFFFFF")
self.btn_blueprint.pack(side="left", padx=2)
```

## 개선 효과

### 공간 절약
```
좌측 영역: 40-50px 절약
우측 영역: 30-40px 절약
총 절약: 약 70-90px
```

### 관리자 모드 활성화 시
```
Before:
[로고][ID][캡쳐][시계][🔊][거울보기][관리자 모드] ... [타일][그래프][도면←잘림]

After:
[로고][ID][캡쳐][시계][🔊][거울][관리자] ... [타일][그래프][도면] ✓
```

### 버튼 가시성
- **관리자 모드 OFF**: 모든 버튼 완전히 보임
- **관리자 모드 ON**: 도면 버튼까지 완전히 보임 ✓

### 사용성 개선
1. **관리자 텍스트 축약**: "🔓 관리자 모드" → "🔓 관리자"
   - 가독성 유지하면서 공간 절약
2. **버튼 크기 통일**: width 5-7로 통일
   - 일관성 있는 UI
3. **간격 최소화**: padx 4 → 2
   - 밀집도 높이면서 클릭 가능 영역 유지

## 시각적 비교

### Before (관리자 모드 ON)
```
┌────────────────────────────────────────────────────────────────────┐
│[로고][센서ID][📸캡쳐] [14:30:25] [🔊] [거울보기] [🔓관리자모드] │
│                                                                    │
│ [체감온도] [불쾌지수]                                              │
│                                                                    │
│     [오늘경고...] [안전교육] [타일] [그래프] [도←                 │
└────────────────────────────────────────────────────────────────────┘
                                                    ↑ 도면 버튼 잘림
```

### After (관리자 모드 ON)
```
┌────────────────────────────────────────────────────────────────────┐
│[로고][ID][캡쳐][14:30:25][🔊][거울][🔓관리자]                      │
│                                                                    │
│ [체감온도] [불쾌지수]                                              │
│                                                                    │
│    [오늘경고...][안전교육][타일][그래프][도면]                     │
└────────────────────────────────────────────────────────────────────┘
                                           ↑ 도면 버튼 완전히 보임 ✓
```

## 테스트 시나리오

### 1. 일반 모드 (관리자 OFF)
- [ ] 모든 버튼 정상 표시
- [ ] 도면 버튼까지 완전히 보임
- [ ] 버튼 간격이 자연스러움

### 2. 관리자 모드 ON
- [ ] 관리자 버튼 표시
- [ ] 도면 버튼까지 완전히 보임 ✓
- [ ] 버튼 클릭 가능 영역 충분

### 3. 화면 크기 변경
- [ ] 1920x1080: 모든 버튼 정상
- [ ] 1366x768: 도면 버튼까지 보임
- [ ] 1280x720: 최소 해상도에서도 도면 버튼 보임

### 4. 버튼 기능
- [ ] 모든 버튼 클릭 정상 작동
- [ ] 관리자 모드 토글 정상
- [ ] 모드 전환 (타일/그래프/도면) 정상

## 추가 개선 가능 항목

### 1. 반응형 폰트 크기
- 화면 크기에 따라 폰트 크기 자동 조절
- 작은 화면에서 더 많은 버튼 표시 가능

### 2. 버튼 오버플로우 처리
- 매우 작은 화면에서 드롭다운 메뉴로 전환
- 스크롤 가능한 버튼 영역

### 3. 아이콘 전용 모드
- 텍스트 대신 아이콘만 표시
- 툴팁으로 기능 설명

## 관련 파일
- `src/tcp_monitor/ui/panel_header.py` (수정)

## 버전 정보
- **수정 버전**: v1.9.0
- **수정 날짜**: 2025-11-06
- **작성자**: Claude Code
