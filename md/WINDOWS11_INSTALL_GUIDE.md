# 윈도우11 GARAMe MANAGER 1.8.4 완전 설치 가이드

## 📋 사전 요구사항

### 시스템 요구사항
- **운영체제**: Windows 11 (64비트)
- **Python**: 3.11.x 권장(본 가이드는 3.11.9 기준)
- **메모리**: 최소 4GB RAM (권장: 8GB 이상)
- **디스크 공간**: 최소 3GB 여유 공간 (OCR 모델 포함)
- **네트워크**: 인터넷 연결 (초기 설치 및 모델 다운로드용)

### 필요한 프로그램
1. **Python 3.11.x (64bit)** - https://www.python.org/downloads/
2. **Git** (선택사항) - https://git-scm.com/download/win

## 🚀 단계별 설치 과정

### 1단계: Python 3.11 설치

#### A. Python 다운로드 및 설치
1. **Python 공식 사이트** 방문: https://www.python.org/downloads/
2. **3.11.x 버전 다운로드** (예: 3.11.9, 64bit)
3. **설치 시 중요 설정**:
   - ✅ **"Add Python to PATH"** 체크박스 반드시 선택
   - ✅ **"Install for all users"** 선택 (관리자 권한으로 설치 시)
   - ✅ **pip 설치 옵션** 선택

#### B. 설치 확인
```cmd
# 명령 프롬프트(cmd) 또는 PowerShell 실행
python --version
pip --version
```

### 2단계: 프로젝트 다운로드

#### A. 프로젝트 폴더로 이동
```cmd
# 작업 디렉토리로 이동
cd C:\Users\%USERNAME%\Documents\GitHub

# 프로젝트 폴더로 이동
cd "GARAMe MANAGER\1.8.4"
```

#### B. 파일 구조 확인
```
GARAMe MANAGER/1.8.4/
├── main.py                    # 메인 프로그램
├── requirements.txt           # 의존성 패키지
├── config.conf.example        # 설정 파일 예제
├── download_ocr_models.py     # OCR 모델 다운로드 도구
├── offline_ocr_manager.py     # 오프라인 OCR 관리자
├── setup_ocr_models.bat       # OCR 모델 설정 도구
├── run.bat                    # 실행 배치 파일
├── setup_autostart.bat        # 자동 시작 설정 도구
├── watchdog.py                # 와치독 프로그램
└── src/                       # 소스 코드
```

### 3단계: 가상환경 생성 (권장)

```cmd
# (경로 문제 예방) 짧은 경로에 가상환경 생성
"%LocalAppData%\Programs\Python\Python311\python.exe" -m venv C:\venv311

# 가상환경 활성화
C:\venv311\Scripts\activate

# 버전/경로 확인
python -V
where python
where pip

# pip 업그레이드
python -m pip install --upgrade pip wheel setuptools
```

### 4단계: 필수 라이브러리 설치 (NumPy/Shapely/패들 순서 권장)

```cmd
# 0) 임시 폴더를 짧게 설정(현 세션 한정)
mkdir C:\piptmp
set TEMP=C:\piptmp
set TMP=C:\piptmp

# 1) NumPy를 OpenCV 호환 버전으로 먼저 설치 (opencv 4.12.0.88 => numpy<2.3)
C:\venv311\Scripts\pip install --no-cache-dir "numpy==2.2.6"

# 2) Shapely (바이너리 휠 강제, EasyOCR/Paddle 의존)
C:\venv311\Scripts\pip install --only-binary=:all: "shapely==2.0.6"

# 3) PaddlePaddle (CPU) - 공식 휠 페이지 사용
C:\venv311\Scripts\pip install --no-cache-dir --prefer-binary paddlepaddle==3.1.0 ^
  -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html

# 4) PaddleOCR
C:\venv311\Scripts\pip install --no-cache-dir paddleocr==3.3.0

# 5) 프로젝트 나머지 의존성 설치(현재 폴더가 1.8.5일 때)
dir requirements.txt
C:\venv311\Scripts\pip install -r .\requirements.txt --no-deps

# 또는 install_requirements.py 사용 (권장 - OCR/카메라 자동 설치 포함)
python install_requirements.py

# (절대 경로 예시)
C:\venv311\Scripts\pip install -r "C:\\Users\\HOST\\Documents\\GitHub\\GARAMe MANAGER\\1.8.4\\requirements.txt" --no-deps
```

주의
- 반드시 가상환경의 pip 경로(`C:\venv311\Scripts\pip`)로 설치하세요. Windows Store Python 경로로 설치되면 긴 경로 문제로 실패할 수 있습니다.

참고
- 경로가 길어 실패 시(Windows 긴 경로 제한): 가상환경을 C:\venv311 처럼 짧은 경로에 생성하고, 필요 시 관리자 PowerShell에서 Long Path 활성화:
  - `reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f` (재부팅 필요)

**설치되는 라이브러리들:**
- **카메라**: opencv-contrib-python==4.12.0.88, numpy==2.2.6
- **OCR**: paddlepaddle==3.1.0, paddleocr==3.3.0, easyocr>=1.6.0
- **이미지 처리**: Pillow, scikit-image, imageio
- **시스템 제어**: psutil, pynput, keyboard, pystray
- **파일 처리**: pandas, openpyxl
- **기타**: matplotlib, numpy, pyttsx3, requests

### 5단계: OCR 모듈 설치 및 모델 다운로드

**참고**: 프로그램 최초 실행 시 OCR 모듈이 자동으로 설치됩니다 (main.py에 포함됨)

#### A. 자동 설치 (권장)
```cmd
# 프로그램 실행 시 자동으로 OCR 모듈이 설치됩니다
python main.py
```

#### B. 수동 설치 (선택사항)
```cmd
# install_requirements.py 실행 (OCR 모듈 자동 설치)
python install_requirements.py

# 또는 OCR 모델 다운로드 도구 실행
setup_ocr_models.bat

# 또는 Python 스크립트 직접 실행
python download_ocr_models.py
```

**메뉴에서 선택:**
1. **"1. 모든 OCR 모델 다운로드"** - PaddleOCR과 EasyOCR 모델 모두 다운로드
2. **"3. 오프라인 패키지 생성"** - 모델을 ZIP 파일로 패키징

#### B. 인터넷이 없는 환경에서
```cmd
# 미리 다운로드된 오프라인 패키지 압축 해제
python download_ocr_models.py
# 메뉴에서 "4. 오프라인 패키지 압축 해제" 선택
```

### 6단계: 설정 파일 준비

```cmd
# 설정 파일 복사
copy config.conf.example config.conf
```

#### A. 설정 파일 편집 (선택사항)
`config.conf` 파일을 메모장으로 열어서 다음 항목들을 확인/수정:

```ini
[LISTEN]
host = 0.0.0.0
port = 9000

[UI]
tile_scale = 0.5
header_scale = 1.00
connection_timeout = 15.0  # 통신 타임아웃 (초) - 기본 15초

[ENV]
graph_enabled = True  # 그래프 기능 사용 여부
max_sensors = 4  # 최대 접속 센서 수

[VALUE]
text = 가람이엔지입니다. 밀폐공간 사고 방지를 위해서 공기질 측정중입니다.(참고자료로만 이용해 주세요)
```

### 7단계: 프로그램 실행 테스트

#### A. 기본 실행
```cmd
python main.py
```

문제 해결(설치/경로)
- Paddle 설치 중 긴 경로 오류 발생 시(Errno 2, long path):
  1) 위 4단계처럼 `C:\venv311\Scripts\pip`로 설치하고 TEMP/TMP를 `C:\piptmp`로 설정했는지 확인
  2) 관리자 PowerShell에서 Long Path 활성화 후 재부팅:
     - `reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f`
  3) 재부팅 후 4단계부터 재시도

문제 해결(경로 포함 공백)
- 경로에 공백이 있으므로 항상 큰따옴표로 감싸서 실행하세요.


#### B. 배치 파일 실행 (권장)
```cmd
run.bat
```

#### C. 자동 실행 모드
```cmd
run.bat auto
```

### 8단계: 자동 시작 설정 (권장)

방법 A) 시작프로그램(Startup) 폴더에 등록(사용자 로그인 시 실행)
1. Win+R → `shell:startup` 입력 → 엔터
2. 폴더 안에서 우클릭 → 새로 만들기 → 바로가기
3. 대상 입력:
   - `C:\venv311\Scripts\python.exe "C:\Users\HOST\Documents\GitHub\GARAMe MANAGER\1.8.4\main.py"`
4. 이름 지정: `GARAMe MANAGER`
5. 완료 후 바로가기 속성에서 아이콘/실행 위치 조정 가능

방법 B) 작업 스케줄러 등록(시스템 부팅/로그온 시 실행)
1. 시작 메뉴 → 작업 스케줄러 실행
2. 작업 만들기 → 이름: `GARAMe MANAGER`
3. 보안 옵션: "사용자가 로그온할 때만 실행" 또는 "사용자 로그온과 관계없이 실행"
4. 트리거: "로그온 시" 또는 "시스템 시작 시"
5. 동작: 프로그램 시작 → 프로그램/스크립트:
   - 프로그램: `C:\venv311\Scripts\python.exe`
   - 인수 추가: `"C:\Users\HOST\Documents\GitHub\GARAMe MANAGER\1.8.4\main.py"`
   - 시작 위치: `C:\Users\HOST\Documents\GitHub\GARAMe MANAGER\1.8.4`
6. 조건/설정 탭에서 필요 옵션 조정 후 확인

방법 C) 레지스트리 Run 등록(고급 사용자)
1. Win+R → `regedit`
2. 경로: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
3. 문자열 값 추가: 이름 `GARAMeMANAGER`, 데이터
   - `"C:\venv311\Scripts\python.exe" "C:\Users\HOST\Documents\GitHub\GARAMe MANAGER\1.8.1\main.py"`

### 9단계: 와치독 설정 (선택사항)

```cmd
# 와치독 실행 (자동 재시작 기능)
python watchdog.py
```

**와치독 기능:**
- 프로그램 비정상 종료 시 자동 재시작
- 시스템 트레이에서 백그라운드 실행
- 최대 재시작 횟수 제한

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Python 설치 오류
```cmd
# Python PATH 확인
echo %PATH%

# 수동 PATH 추가 (필요시)
setx PATH "%PATH%;C:\Python39;C:\Python39\Scripts"
```

#### 2. 패키지 설치 오류
```cmd
# pip 업그레이드
python -m pip install --upgrade pip

# 캐시 클리어 후 재설치
pip install --no-cache-dir -r requirements.txt
```

#### 2-1. Paddle 설치 중 긴 경로 오류(Errno 2)
```cmd
# venv pip 강제 사용 + 임시 폴더 단축
C:\venv311\Scripts\pip install --no-cache-dir --prefer-binary paddlepaddle==3.1.0 ^
  -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html

# 여전히 실패하면(긴 경로) 관리자 PowerShell에서 Long Path 활성화 후 재부팅
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

#### 3. OCR 모델 다운로드 실패
```cmd
# 인터넷 연결 확인
ping google.com

# 모델 상태 확인
python -c "from offline_ocr_manager import OfflineOCRManager; manager = OfflineOCRManager(); print(manager.check_model_availability())"
```

#### 4. 카메라 경고/검출 실패 (OpenCV DSHOW 경고)
- 증상: `[ WARN:... VIDEOIO(DSHOW) ... can't be used to capture by index]`
- 원인: 카메라 인덱스/백엔드 미스매치, 권한/점유 문제
- 조치 순서:
  1) Windows 설정 → 개인정보/보안 → 카메라 → 앱에서 카메라 사용 허용
  2) Teams/Zoom 등 카메라 점유 앱 종료
  3) 카메라 인덱스 바꿔 테스트(0 → 1)
  4) 백엔드 `MSMF` 권장: 코드/설정에서 `cv2.VideoCapture(0, cv2.CAP_MSMF)` 사용
  5) OpenCV 패키지 통일(권장: contrib만 유지)
     ```cmd
     pip uninstall -y opencv-python opencv-contrib-python
     pip install opencv-contrib-python==4.12.0.88
     ```

#### 5. 날씨 API 키 미설정
- 메시지: `기상청 API 키가 설정되지 않았습니다. 기본 위치를 사용합니다.`
- 동작: 키가 없어도 기본 위치로 표시. 키 사용 시 정확도/기능 향상
- 설정 방법: `config.conf`에 API 키 추가
  ```ini
  [WEATHER]
  provider = KMA
  kma_api_key = YOUR_KMA_API_KEY
  ```

#### 4. 권한 문제
- **관리자 권한으로 실행**: 명령 프롬프트를 관리자 권한으로 실행
- **방화벽 설정**: Windows 방화벽에서 Python 허용

### 로그 확인

문제 발생 시 다음 로그 파일들을 확인:
- `logs/run/run_YYYYMMDD.log` - 실행 로그
- `logs/data/data_YYYYMMDD.log` - 데이터 로그
- `logs/warning/warning_YYYYMMDD.log` - 경고 로그
- `watchdog.log` - 와치독 로그

## 📁 설치 완료 후 폴더 구조

```
GARAMe MANAGER/1.8.1/
├── main.py                    # 메인 프로그램
├── config.conf                # 설정 파일
├── (외부) C:\venv311\        # 권장 가상환경 경로
├── ocr_models/                # OCR 모델 저장 폴더
├── logs/                      # 로그 폴더
│   ├── run/                   # 실행 로그
│   ├── data/                  # 데이터 로그
│   └── warning/               # 경고 로그
├── safety_photos/             # 안전교육 사진
├── safety_posters/            # 안전교육 포스터
└── assets/                    # 이미지 리소스
```

## 🎯 실행 방법

### 일반 실행
```cmd
python main.py
```

### 배치 파일 실행 (권장)
```cmd
run.bat
```

### 자동 실행 모드
```cmd
run.bat auto
```

### 와치독과 함께 실행
```cmd
python watchdog.py
```

## 📞 지원 및 문의

설치 과정에서 문제가 발생하면:
1. **로그 파일 확인** - 위의 로그 파일들 확인
2. **Python 버전 확인** - `python --version`
3. **PATH 설정 확인** - `echo %PATH%`
4. **방화벽 설정 확인** - Windows 방화벽에서 Python 허용
5. **관리자 권한으로 실행** - 명령 프롬프트를 관리자 권한으로 실행

## 🎉 설치 완료!

이제 GARAMe MANAGER 1.8.1이 윈도우11에서 완전히 설치되었습니다!

**주요 기능:**
- ✅ 실시간 센서 데이터 모니터링
- ✅ 카메라 및 OCR 기능
- ✅ 오프라인 모드 지원
- ✅ 자동 재시작 (와치독)
- ✅ 터치 전용 인터페이스
- ✅ 자동 시작 설정

프로그램을 실행하고 센서 데이터를 모니터링해보세요! 🚀
