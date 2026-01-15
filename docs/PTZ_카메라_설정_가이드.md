# PTZ 카메라 설정 가이드

## 개요

GARAMe Manager v1.9.8에서 Tapo PTZ 카메라를 설정하는 방법입니다.

---

## 지원 카메라

| 모델 | PTZ 지원 | 비고 |
|------|---------|------|
| Tapo C210 | ✅ | Pan/Tilt |
| Tapo C211 | ✅ | Pan/Tilt |
| Tapo C220 | ✅ | Pan/Tilt/Zoom |
| Tapo C225 | ✅ | Pan/Tilt |
| Tapo C100 | ❌ | 고정형 카메라 |
| Tapo C110 | ❌ | 고정형 카메라 |

---

## 계정 유형

Tapo 카메라는 **두 가지 계정**이 필요합니다:

### 1. RTSP 계정 (로컬 카메라 계정)

- **용도**: 영상 스트리밍 (RTSP)
- **설정 위치**: Tapo 앱 > 카메라 > 설정 > 고급 설정 > 카메라 계정
- **입력 위치**: 카메라 설정 > 사용자명/비밀번호

### 2. Tapo 클라우드 계정

- **용도**: PTZ 제어
- **설정 위치**: Tapo 앱 로그인에 사용하는 계정
- **입력 위치**: 카메라 설정 > PTZ 제어용 Tapo 계정

---

## 설정 방법

### 1단계: Tapo 앱에서 카메라 계정 생성

1. Tapo 앱 열기
2. 카메라 선택 > 설정 (톱니바퀴)
3. 고급 설정 > 카메라 계정
4. 사용자명과 비밀번호 설정 (RTSP용)

### 2단계: GARAMe Manager에서 카메라 추가

1. 도구 > 카메라 설정
2. IP 카메라 섹션 > **➕ 추가** 클릭

### 3단계: 카메라 정보 입력

```
카메라 이름: Tapo C211
프로토콜: RTSP
IP 주소: 192.168.0.26
포트: 554
스트림 경로: /stream1 (고화질) 또는 /stream2 (저화질)
사용자명: [카메라 계정 사용자명]
비밀번호: [카메라 계정 비밀번호]
```

### 4단계: PTZ 활성화

1. ✅ "PTZ (Pan-Tilt-Zoom) 제어 활성화" 체크
2. **PTZ 제어용 Tapo 계정** 섹션에:
   - Tapo 이메일: [Tapo 앱 로그인 이메일]
   - Tapo 비밀번호: [Tapo 앱 로그인 비밀번호]

### 5단계: 연결 테스트

1. **🔗 RTSP 테스트** 클릭 → 영상 스트리밍 확인
2. **🎮 PTZ 테스트** 클릭 → PTZ 제어 확인

---

## 문제 해결

### "Invalid authentication data" 오류

**원인**: 잘못된 계정 정보 입력

**해결 방법**:
1. PTZ Tapo 계정이 **Tapo 앱 로그인 계정**인지 확인
2. RTSP 계정과 Tapo 클라우드 계정이 **다른 계정**임을 인식
3. 비밀번호에 특수문자가 있으면 확인

### "Temporary Suspension" 오류

**원인**: 연속 인증 실패로 카메라 잠금

**해결 방법**:
1. 30분 대기 후 재시도
2. 올바른 계정 정보 확인 후 재시도

### PTZ 제어 안 됨

**원인**: PTZ 미지원 카메라 또는 연결 실패

**확인 사항**:
1. 카메라가 PTZ 지원 모델인지 확인
2. pytapo 라이브러리 설치 여부: `pip install pytapo`
3. 카메라와 같은 네트워크에 있는지 확인

---

## 인증 방식 (기술 정보)

GARAMe Manager는 4가지 인증 방식을 순차적으로 시도합니다:

1. **admin + password**: 신형 펌웨어 권장 방식
2. **admin + cloudPassword**: cloudPassword 파라미터 사용
3. **이메일 + password**: 사용자명으로 이메일 사용
4. **이메일 + cloudPassword**: 사용자명으로 이메일, cloudPassword 파라미터 사용

```python
# pytapo 인증 예시
from pytapo import Tapo

# 방법 1: 신형 펌웨어
tapo = Tapo("192.168.0.26", "admin", "cloud_password")

# 방법 2: cloudPassword 파라미터
tapo = Tapo("192.168.0.26", "admin", "", cloudPassword="cloud_password")
```

---

## 참고 자료

- [pytapo GitHub](https://github.com/JurajNyiri/pytapo)
- [pytapo 인증 이슈 #113](https://github.com/JurajNyiri/pytapo/issues/113)

---

**작성일**: 2024-12-24
**버전**: GARAMe Manager v1.9.8.2
