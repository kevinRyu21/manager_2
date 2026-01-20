"""
패널 타일 그리드 UI 컴포넌트

3x2 센서 타일 그리드를 관리합니다.
"""

import tkinter as tk
from tkinter import ttk
from ..utils.helpers import SENSOR_KEYS, COLOR_TILE_OK, COLOR_ALARM, ideal_fg, fmt_ts
from ..utils.weather_api import WeatherAPI
import re
from urllib.request import Request, urlopen
import ssl


class PanelTiles(ttk.Frame):
    """3x2 센서 타일 그리드"""

    def __init__(self, master, app, on_tile_click):
        super().__init__(master)
        self.app = app
        self.on_tile_click = on_tile_click
        self.tiles = {}
        self._connection_status = "waiting"
        self._weather_panel = None  # 날씨 패널 별도 관리
        # 전역 스피커 상태에서 초기값 가져오기 (패널 재생성 시 상태 유지)
        self._voice_alert_enabled = getattr(app, 'global_voice_alert_enabled', True)
        
        # 기상청 API 초기화
        self._init_weather_api()
        
        self._build_grid()

    def _build_grid(self):
        """3x3 그리드 생성 (9개 센서 타일)"""
        # 날씨 패널 백업 (누수 타일 재생성 시 유지)
        weather_backup = None
        if self._weather_panel and "frame" in self._weather_panel:
            try:
                weather_backup = self._weather_panel.copy()
            except Exception:
                pass
        
        for w in self.grid_slaves():
            w.destroy()

        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")
        self.grid_rowconfigure((0, 1, 2), weight=1, uniform="row")
        
        # 날씨 패널 백업 복원
        if weather_backup:
            self._weather_panel = weather_backup

        def mk_tile(row, col, title, key, unit, icon=""):
            f = tk.Frame(self, bg=COLOR_TILE_OK, relief="raised", bd=3)
            f.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

            # 메인 프레임 (센서값과 기준값을 나누기 위해)
            main_frame = tk.Frame(f, bg=COLOR_TILE_OK)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # 좌측 프레임 (센서값 정보) - 투명하게
            left_frame = tk.Frame(main_frame, bg=COLOR_TILE_OK)
            left_frame.pack(side="left", fill="both", expand=True)

            # 우측 프레임 (5단계 경보 기준값) - 고정 크기로 통일, 크기 확대
            right_frame = tk.Frame(main_frame, bg="#1976D2", relief="raised", bd=2, width=250)
            right_frame.pack(side="right", fill="y", padx=(10, 0))
            right_frame.pack_propagate(False)  # 고정 크기 유지

            # 타이틀 프레임 (아이콘 + 텍스트 분리)
            title_frame = tk.Frame(left_frame, bg=COLOR_TILE_OK)

            self.tiles[key] = {
                "frame": f,
                "main_frame": main_frame,
                "left_frame": left_frame,
                "right_frame": right_frame,
                "title_frame": title_frame,
                "icon": tk.Label(title_frame, text=icon, bg=COLOR_TILE_OK, fg=ideal_fg(COLOR_TILE_OK), font=("Pretendard", 21, "bold")) if icon else None,
                "title": tk.Label(title_frame, text=title, bg=COLOR_TILE_OK, fg=ideal_fg(COLOR_TILE_OK), font=("Pretendard", 14, "bold"), compound="left"),
                "val": tk.Label(left_frame, text="--", bg=COLOR_TILE_OK, fg=ideal_fg(COLOR_TILE_OK), font=("Pretendard", 28, "bold")),
                "stat": tk.Label(left_frame, text="오늘 통계: - / - / -", bg=COLOR_TILE_OK, fg=ideal_fg(COLOR_TILE_OK), font=("Pretendard", 10)),
                "unit": unit,
                # 5단계 경보 기준값 라벨들
                "alert_levels": []
            }
            t = self.tiles[key]

            # 좌측 프레임에 기존 요소들 배치
            t["title_frame"].pack(pady=(10, 0))
            if t["icon"]:
                t["icon"].pack(side="left", padx=(0, 5))
            t["title"].pack(side="left")
            t["val"].pack()
            t["stat"].pack(pady=(0, 10))
            
            # 우측 프레임에 5단계 경보 기준값 배치
            self._create_alert_levels_display(t, key)

            # 누수 타일에 날씨 영역 추가
            if key == "water":
                self._init_weather_panel(t)

            f.bind("<Button-1>", lambda e, k=key: self.on_tile_click(k))
            for w in (t["title"], t["val"], t["stat"]):
                w.bind("<Button-1>", lambda e, k=key: self.on_tile_click(k))

            def on_resize(ev, k=key):
                self._autoscale_tile(k)
            f.bind("<Configure>", on_resize)

        mk_tile(0, 0, "이산화탄소 (ppm)", "co2", "ppm", "🏭")
        mk_tile(0, 1, "산소 (%)", "o2", "%", "💨")
        mk_tile(0, 2, "황화수소 (ppm)", "h2s", "ppm", "☠️")
        mk_tile(1, 0, "일산화탄소 (ppm)", "co", "ppm", "🔥")
        mk_tile(1, 1, "가연성가스 (%)", "lel", "%", "⚡")
        mk_tile(1, 2, "연기 (ppm)", "smoke", "ppm", "🌫️")
        mk_tile(2, 0, "온도 (℃)", "temperature", "℃", "🌡️")
        mk_tile(2, 1, "습도 (%)", "humidity", "%", "💧")
        mk_tile(2, 2, "누수 감지", "water", "", "🚿")

    def _create_alert_levels_display(self, tile, key):
        """5단계 경보 기준값 표시 생성"""
        # 5단계 경보 색상 정의
        alert_colors = {
            1: "#2ECC71",  # 정상 - 녹색
            2: "#F1C40F",  # 관심 - 노랑
            3: "#E67E22",  # 주의 - 주황
            4: "#E74C3C",  # 경계 - 빨강
            5: "#C0392B"   # 심각 - 진홍
        }
        
        alert_messages = {
            1: "정상",
            2: "관심", 
            3: "주의",
            4: "경계",
            5: "심각"
        }
        
        # 센서별 기준값 가져오기
        thresholds = self._get_sensor_thresholds(key)
        
        # 상단 프레임 (경보 기준값) - 누수 센서는 흰색 바탕으로 통합
        if key == "water":
            top_frame = tk.Frame(tile["right_frame"], bg="#FFFFFF", relief="raised", bd=2)
            top_frame.pack(fill="x", pady=(2, 2), padx=2)
        else:
            top_frame = tk.Frame(tile["right_frame"], bg="#FFFFFF", relief="raised", bd=2)
            top_frame.pack(fill="x", pady=(2, 3), padx=2)
        tile["top_frame"] = top_frame  # 나중에 배경색 유지를 위해 저장

        # 제목 라벨 - 개별 박스 제거, 흰색 바탕, 패딩 최소화
        title_label = tk.Label(top_frame, text="경보 기준",
                              bg="#FFFFFF", fg="#000000",
                              font=("Pretendard", 13, "bold"))
        title_label.pack(pady=(3, 2), anchor="center")
        tile["alert_title_label"] = title_label  # 나중에 배경색 유지를 위해 저장
        
        # 각 단계별 기준값 표시 - 개별 박스 제거, 흰색 바탕, 패딩 최소화
        for level in range(1, 6):
            if level in thresholds:
                threshold_text = thresholds[level]
                color = alert_colors[level]
                message = alert_messages[level]
                
                # 경보 기준 라벨 크기를 현재상태 문구 크기와 동일하게 연동
                base_size = 25
                scale = float(self.app.status_text_scale.get())
                scaled_size = max(12, int(base_size * scale))
                
                level_label = tk.Label(top_frame, 
                                      text=f"{message}: {threshold_text}",
                                      bg="#FFFFFF", fg=color,
                                      font=("Pretendard", scaled_size, "bold"))
                level_label.pack(pady=0, anchor="center")
                tile["alert_levels"].append(level_label)
        
        # 하단 프레임 (현재 상태) - 누수 센서는 별도(날씨)
        if key != "water":
            # 다른 센서들은 기존 방식
            bottom_frame = tk.Frame(tile["right_frame"], bg="#FFFFFF", relief="raised", bd=2)
            bottom_frame.pack(fill="x", pady=(1, 1), padx=1)  # 패딩 최소화
            tile["bottom_frame"] = bottom_frame  # 나중에 배경색 유지를 위해 저장

            # 현재 상태 표시 라벨만 - 제목 제거, 센서값과 같은 크기, 패딩 최소화
            base_size = 25
            scale = float(self.app.status_text_scale.get())
            scaled_size = max(12, int(base_size * scale))

            current_status_label = tk.Label(bottom_frame, text="측정 중...",
                                           bg="#FFFFFF", fg="#666666",
                                           font=("Pretendard", scaled_size, "bold"))
            current_status_label.pack(pady=(2, 2), anchor="center")  # 패딩 최소화
            tile["current_status"] = current_status_label
        else:
            # 누수는 현재 상태 라벨 대신 날씨 패널을 사용하므로 None
            tile["current_status"] = None
            tile["bottom_frame"] = None

    def _init_weather_api(self):
        """기상청 API 초기화"""
        try:
            # config에서 날씨 설정 읽기
            weather_config = self.app.cfg.get_section('WEATHER', {})
            
            api_key = weather_config.get('kma_api_key', 'YOUR_API_KEY_HERE')
            lat = float(weather_config.get('location_lat', 37.9129))
            lon = float(weather_config.get('location_lon', 127.7863))
            auto_detect = weather_config.get('auto_detect_location', 'True').lower() == 'true'
            
            # API 키가 설정되지 않은 경우 기본값 사용
            if api_key == 'YOUR_API_KEY_HERE':
                print("기상청 API 키가 설정되지 않았습니다. 기본 위치를 사용합니다.")
                self.weather_api = None
                return
            
            # 자동 위치 감지가 활성화된 경우 IP 기반 위치 감지 시도
            if auto_detect:
                temp_api = WeatherAPI(api_key, lat, lon)
                detected_location = temp_api.get_current_location_from_ip()
                if detected_location:
                    lat, lon = detected_location
                    print(f"IP 기반 위치 감지 성공: 위도 {lat}, 경도 {lon}")
            
            self.weather_api = WeatherAPI(api_key, lat, lon)
            print(f"기상청 API 초기화 완료: 위도 {lat}, 경도 {lon}")
            
        except Exception as e:
            print(f"기상청 API 초기화 실패: {e}")
            self.weather_api = None

    def _init_weather_panel(self, tile):
        # 기존 날씨 패널이 있으면 제거
        if self._weather_panel and "frame" in self._weather_panel:
            try:
                self._weather_panel["frame"].destroy()
            except:
                pass
        
        wf = tk.Frame(tile["right_frame"], bg="#1976D2", relief="raised", bd=2)
        wf.pack(fill="both", expand=True, pady=(2, 1), padx=2)

        # 상단: 아이콘 + 날씨상태 + 현재 온도
        top = tk.Frame(wf, bg="#1976D2")
        top.pack(pady=(3, 1))
        icon = tk.Label(top, text="☀️", bg="#1976D2", fg="#FFFFFF", font=("Pretendard", 20))
        icon.pack(side="left", padx=(0, 4))
        cond = tk.Label(top, text="맑음", bg="#1976D2", fg="#E3F2FD", font=("Pretendard", 12))
        cond.pack(side="left", padx=(0, 4))
        temp = tk.Label(top, text="--°C", bg="#1976D2", fg="#FFFFFF", font=("Pretendard", 20, "bold"))
        temp.pack(side="left")

        # 지역명
        loc = tk.Label(wf, text="강원특별자치도, 춘천시", bg="#1976D2", fg="#BBDEFB", font=("Pretendard", 11, "bold"))
        loc.pack(pady=(1, 0))

        # 갱신 정보
        refresh = tk.Label(wf, text="갱신주기: 15분", bg="#1976D2", fg="#BBDEFB", font=("Pretendard", 10))
        refresh.pack(pady=(2, 0))
        updated = tk.Label(wf, text="최종 갱신: -", bg="#1976D2", fg="#BBDEFB", font=("Pretendard", 10))
        updated.pack(pady=(0, 2))

        # 출처
        src = tk.Label(wf, text="기상청", bg="#1976D2", fg="#BBDEFB", font=("Pretendard", 7))
        src.pack(pady=(0, 3))

        # 날씨 패널을 클래스 변수로 저장
        self._weather_panel = {"frame": wf, "icon": icon, "temp": temp, "cond": cond, "refresh": refresh, "updated": updated, "loc": loc}
        tile["weather_panel"] = self._weather_panel

        # 생성 즉시 기본 표시를 보이게 하고 첫 갱신을 예약
        try:
            self._weather_panel["temp"].configure(text="--°C")
            self._weather_panel["cond"].configure(text="로딩 중…")
            self._weather_panel["icon"].configure(text="ℹ️")
            self._weather_panel["loc"].configure(text=self._weather_panel["loc"].cget("text") or "-")
            self._weather_panel["updated"].configure(text="최종 갱신: -")
        except Exception:
            pass

        # 클릭으로 즉시 갱신 기능 추가 (애니메이션 포함)
        def on_weather_click(event):
            # 클릭 애니메이션: 배경색 변경
            original_bg = wf.cget("bg")
            wf.configure(bg="#1565C0")  # 더 진한 파란색
            for widget in [icon, temp, cond, loc, refresh, updated, src]:
                widget.configure(bg="#1565C0")
            
            # 200ms 후 원래 색상으로 복원
            self.after(200, lambda: self._restore_weather_colors(wf, [icon, temp, cond, loc, refresh, updated, src], original_bg))
            
            # 즉시 날씨 갱신
            self._update_weather(tile)
        
        # 날씨 패널 전체에 클릭 이벤트 바인딩
        wf.bind("<Button-1>", on_weather_click)
        for widget in [icon, temp, cond, loc, refresh, updated, src]:
            widget.bind("<Button-1>", on_weather_click)

        # panel 생성 직후에도 날씨 갱신 시도 (초기 화면에서 비어 보이는 문제 방지)
        self.after(100, lambda: self._update_weather(tile))

    def _restore_weather_colors(self, frame, widgets, original_bg):
        """날씨 패널 색상 복원"""
        try:
            frame.configure(bg=original_bg)
            for widget in widgets:
                widget.configure(bg=original_bg)
        except Exception:
            pass

    def _toggle_voice_alert(self):
        """음성 경보 토글"""
        try:
            # 음성 경보 상태 토글
            if not hasattr(self, '_voice_alert_enabled'):
                self._voice_alert_enabled = True
            
            self._voice_alert_enabled = not self._voice_alert_enabled
            
            # 버튼 텍스트 업데이트
            if self._weather_panel and "voice_toggle" in self._weather_panel:
                button = self._weather_panel["voice_toggle"]
                if self._voice_alert_enabled:
                    button.configure(text="🔊")
                else:
                    button.configure(text="🔇")
            
            # 설정 저장 (선택사항)
            # self.app.cfg.set('voice_alerts', 'enabled', str(self._voice_alert_enabled))
            
        except Exception as e:
            print(f"음성 경보 토글 오류: {e}")

    def _get_weather_data(self):
        """기상청 API에서 날씨 데이터 조회"""
        if not self.weather_api:
            return None
            
        try:
            # 현재 날씨 조회
            current_weather = self.weather_api.get_current_weather()
            if not current_weather:
                return None
                
            # 예보 조회 (선택사항)
            forecast = self.weather_api.get_weather_forecast()
            
            # 데이터 포맷팅
            weather_data = {
                "temp": str(int(current_weather.get("temperature", 0))) if current_weather.get("temperature") else "--",
                "cond": current_weather.get("sky_condition", "정보없음"),
                "loc": self.weather_api.get_location_name(),
                "humidity": str(int(current_weather.get("humidity", 0))) if current_weather.get("humidity") else "--",
                "precipitation": current_weather.get("precipitation", "없음"),
                "wind_speed": str(current_weather.get("wind_speed", 0)) if current_weather.get("wind_speed") else "--"
            }
            
            return weather_data
            
        except Exception as e:
            print(f"날씨 데이터 조회 실패: {e}")
            return None

    # ===== MSN 날씨 폴백 =====
    def _pick_icon(self, condition_text):
        txt = condition_text or ""
        if re.search(r"(맑음|화창)", txt):
            return "☀️"
        if re.search(r"(구름|흐림)", txt):
            return "⛅"
        if re.search(r"(비|소나기)", txt):
            return "🌧️"
        if re.search(r"(눈|우박)", txt):
            return "🌨️"
        if re.search(r"(안개|미세|연무)", txt):
            return "🌫️"
        return "ℹ️"

    def _get_current_location_from_ip(self):
        """외부 IP를 통해 현재 위치 감지 (도시, 지역 반환)"""
        try:
            import requests
            
            # IP 기반 위치 서비스들
            services = [
                "http://ip-api.com/json/?lang=ko",
                "https://ipapi.co/json/",
                "http://ipinfo.io/json"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # 서비스별 데이터 파싱
                        if "ip-api.com" in service:
                            city = data.get("city", "")
                            region = data.get("regionName", "")
                            country = data.get("country", "")
                        elif "ipapi.co" in service:
                            city = data.get("city", "")
                            region = data.get("region", "")
                            country = data.get("country_name", "")
                        elif "ipinfo.io" in service:
                            city = data.get("city", "")
                            region = data.get("region", "")
                            country = data.get("country", "")
                        
                        # 한국인 경우에만 반환
                        if country and ("Korea" in country or "한국" in country or country == "KR"):
                            return (city, region)
                            
                except Exception as e:
                    print(f"위치 서비스 {service} 실패: {e}")
                    continue
                    
        except Exception as e:
            print(f"IP 기반 위치 감지 실패: {e}")
            
        return None

    def _fetch_msn_weather_html(self):
        try:
            # 자동 위치 감지 시도 (IP 기반)
            location_info = self._get_current_location_from_ip()
            
            if location_info:
                city, region = location_info
                print(f"IP 기반 위치 감지: {region}, {city}")
                # MSN 날씨 URL 생성 (위치 기반)
                msn_url = f"https://www.msn.com/ko-kr/weather/forecast/in-{city},{region}"
            else:
                # 폴백: 강원특별자치도 춘천시 (고정)
                print("IP 위치 감지 실패, 춘천시 기본값 사용")
                msn_url = (
                    "https://www.msn.com/ko-kr/weather/forecast/in-%EA%B0%95%EC%9B%90%ED%8A%B9%EB%B3%84%EC%9E%90%EC%B9%98%EB%8F%84,%EC%B6%98%EC%B2%9C%EC%8B%9C?loc=eyJsIjoi7LaY7LKc7IucIiwiciI6IuqwleybkO2KueuzhOyekOy5mOuPhCIsImMiOiLrjIDtlZzrr7zqta0iLCJpIjoiS1IiLCJnIjoia28ta3IiLCJ4IjoiMTI3Ljc4NjMiLCJ5IjoiMzcuOTEyOSJ9&weadegreetype=C&ocid=ansmsnweather"
                )
            
            ctx = ssl.create_default_context()
            req = Request(msn_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=7, context=ctx) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            return None

    def _parse_weather(self, html_text):
        if not html_text:
            return None
        m_temp = re.search(r"([\-]?\d{1,2})°C", html_text)
        temp_c = m_temp.group(1) if m_temp else "--"
        m_cond = re.search(r"(맑음|대체로\s*맑음|흐림|대체로\s*흐림|구름|비|소나기|약한\s*비|눈|약한\s*눈|안개)", html_text)
        cond = m_cond.group(1) if m_cond else "날씨 정보"
        m_loc = re.search(r"([가-힣A-Za-z\s,]{2,20}\s*,\s*[가-힣A-Za-z\s]{1,20})\s*\n?\s*현재 날씨", html_text)
        if not m_loc:
            m_loc = re.search(r"([가-힣]{2,}(?:특별자치도|광역시|도)?\s*,\s*[가-힣]{2,}시)", html_text)
        loc = m_loc.group(1) if m_loc else "강원특별자치도, 춘천시"
        return {"temp": temp_c, "cond": cond, "loc": loc}

    def _update_weather(self, tile):
        """기상청 API를 사용한 날씨 업데이트"""
        data = self._get_weather_data()
        
        if not data:
            # 폴백: MSN 스크래핑
            html = self._fetch_msn_weather_html()
            msn = self._parse_weather(html) if html else None
            if msn:
                data = msn
            
        if not data:
            # 실패 시 표시만 갱신하고 재시도 예약
            if self._weather_panel and "temp" in self._weather_panel:
                wp = self._weather_panel
                wp["temp"].configure(text="--°C")
                wp["cond"].configure(text="날씨 정보를 불러올 수 없음")
                wp["icon"].configure(text="ℹ️")
            self.after(300000, lambda: self._update_weather(tile))  # 5분 후 재시도
            return

        # 성공 시 업데이트
        if self._weather_panel and "temp" in self._weather_panel:
            wp = self._weather_panel

            # 온도 표시
            # data['temp']는 문자열(폴백) 또는 숫자 문자열(기상청)일 수 있음
            temp_text = data.get('temp')
            wp["temp"].configure(text=f"{temp_text}°C")

            # 날씨 상태 표시
            wp["cond"].configure(text=data.get("cond", "정보없음"))

            # 아이콘 설정
            if self.weather_api:
                icon = self.weather_api.get_weather_icon(data.get("cond", ""), data.get("precipitation", "없음"))
            else:
                icon = self._pick_icon(data.get("cond", ""))
            wp["icon"].configure(text=icon)

            # 지역명 표시
            wp["loc"].configure(text=data.get("loc", "강원특별자치도, 춘천시"))

            # 갱신 시간 표시
            try:
                wp["updated"].configure(text=f"최종 갱신: {fmt_ts()}")
            except Exception:
                pass

        # 헤더의 날씨 정보 업데이트
        try:
            if hasattr(self.master, 'header'):
                temp_val = None
                humidity_val = None
                temp_str = data.get('temp', '')
                if temp_str and temp_str != '--':
                    try:
                        temp_val = float(temp_str)
                    except (ValueError, TypeError):
                        pass
                hum_str = data.get('humidity', '')
                if hum_str and hum_str != '--':
                    try:
                        humidity_val = float(hum_str)
                    except (ValueError, TypeError):
                        pass
                condition = data.get("cond", "")
                self.master.header.update_weather_info(temp_val, condition, humidity_val)
                print(f"[헤더 날씨] 온도={temp_val}, 상태={condition}, 습도={humidity_val}")
        except Exception as e:
            print(f"헤더 날씨 업데이트 실패: {e}")

        # 다음 갱신 예약 (15분마다)
        self.after(900000, lambda: self._update_weather(tile))

    def _get_sensor_thresholds(self, key):
        """센서별 5단계 경보 기준값 반환"""
        cfg = self.app.cfg
        thresholds = {}
        
        if key == "co2":
            thresholds = {
                1: f"< {cfg.std.get('co2_normal_max', 1000):.0f}",
                2: f"< {cfg.std.get('co2_concern_max', 5000):.0f}",
                3: f"< {cfg.std.get('co2_caution_max', 10000):.0f}",
                4: f"< {cfg.std.get('co2_warning_max', 15000):.0f}",
                5: f"≥ {cfg.std.get('co2_danger_max', 20000):.0f}"
            }
        elif key == "o2":
            thresholds = {
                1: f"{cfg.std.get('o2_normal_min', 19.5):.1f}~{cfg.std.get('o2_normal_max', 23.0):.1f}",
                2: f"{cfg.std.get('o2_concern_min', 19.0):.1f}~{cfg.std.get('o2_concern_max', 23.0):.1f}",
                3: f"{cfg.std.get('o2_caution_min', 18.5):.1f}~{cfg.std.get('o2_caution_max', 23.3):.1f}",
                4: f"{cfg.std.get('o2_warning_min', 18.0):.1f}~{cfg.std.get('o2_warning_max', 23.5):.1f}",
                5: f"< {cfg.std.get('o2_danger_min', 17.0):.1f} 또는 > {cfg.std.get('o2_danger_max', 24.0):.1f}"
            }
        elif key == "h2s":
            thresholds = {
                1: f"< {cfg.std.get('h2s_normal_max', 5.0):.1f}",
                2: f"< {cfg.std.get('h2s_concern_max', 8.0):.1f}",
                3: f"< {cfg.std.get('h2s_caution_max', 10.0):.1f}",
                4: f"< {cfg.std.get('h2s_warning_max', 15.0):.1f}",
                5: f"≥ {cfg.std.get('h2s_danger_max', 50.0):.1f}"
            }
        elif key == "co":
            thresholds = {
                1: f"< {cfg.std.get('co_normal_max', 9.0):.1f}",
                2: f"< {cfg.std.get('co_concern_max', 25.0):.1f}",
                3: f"< {cfg.std.get('co_caution_max', 30.0):.1f}",
                4: f"< {cfg.std.get('co_warning_max', 50.0):.1f}",
                5: f"≥ {cfg.std.get('co_danger_max', 100.0):.1f}"
            }
        elif key == "lel":
            thresholds = {
                1: f"< {cfg.std.get('lel_normal_max', 10.0):.1f}",
                2: f"< {cfg.std.get('lel_concern_max', 20.0):.1f}",
                3: f"< {cfg.std.get('lel_caution_max', 50.0):.1f}",
                4: f"< {cfg.std.get('lel_warning_max', 50.0):.1f}",
                5: f"≥ {cfg.std.get('lel_danger_max', 100.0):.1f}"
            }
        elif key == "smoke":
            thresholds = {
                1: f"< {cfg.std.get('smoke_normal_max', 0.0):.1f}",
                2: f"< {cfg.std.get('smoke_concern_max', 10.0):.1f}",
                3: f"< {cfg.std.get('smoke_caution_max', 25.0):.1f}",
                4: f"< {cfg.std.get('smoke_warning_max', 50.0):.1f}",
                5: f"≥ {cfg.std.get('smoke_danger_max', 100.0):.1f}"
            }
        elif key == "temperature":
            thresholds = {
                1: f"{cfg.std.get('temp_normal_min', 18):.0f}~{cfg.std.get('temp_normal_max', 28):.0f}",
                2: f"{cfg.std.get('temp_concern_min', 16):.0f}~{cfg.std.get('temp_concern_max', 30):.0f}",
                3: f"{cfg.std.get('temp_caution_min', 14):.0f}~{cfg.std.get('temp_caution_max', 32):.0f}",
                4: f"{cfg.std.get('temp_warning_min', 12):.0f}~{cfg.std.get('temp_warning_max', 33):.0f}",
                5: f"< {cfg.std.get('temp_danger_min', 10):.0f} 또는 > {cfg.std.get('temp_danger_max', 35):.0f}"
            }
        elif key == "humidity":
            thresholds = {
                1: f"{cfg.std.get('hum_normal_min', 40):.0f}~{cfg.std.get('hum_normal_max', 60):.0f}",
                2: f"{cfg.std.get('hum_concern_min', 30):.0f}~{cfg.std.get('hum_concern_max', 70):.0f}",
                3: f"{cfg.std.get('hum_caution_min', 20):.0f}~{cfg.std.get('hum_caution_max', 80):.0f}",
                4: f"{cfg.std.get('hum_warning_min', 20):.0f}~{cfg.std.get('hum_warning_max', 80):.0f}",
                5: f"< {cfg.std.get('hum_danger_min', 15):.0f} 또는 > {cfg.std.get('hum_danger_max', 85):.0f}"
            }
        elif key == "water":
            thresholds = {
                1: "정상",
                5: "누수 감지"
            }
        
        return thresholds

    def _update_current_status(self, key, value, alert_level):
        """센서별 현재 상태 업데이트"""
        if key not in self.tiles or "current_status" not in self.tiles[key] or self.tiles[key]["current_status"] is None:
            return
            
        alert_messages = {
            1: "정상",
            2: "관심", 
            3: "주의",
            4: "경계",
            5: "심각"
        }
        
        alert_colors = {
            1: "#2ECC71",  # 정상 - 초록색
            2: "#F1C40F",  # 관심 - 노랑색
            3: "#E67E22",  # 주의 - 주황색
            4: "#E74C3C",  # 경계 - 빨간색
            5: "#C0392B"   # 심각 - 진홍색
        }
        
        status_text = alert_messages.get(alert_level, "측정 중...")
        status_color = alert_colors.get(alert_level, "#666666")
        
        # 현재상태 문구 크기 스케일 적용
        base_size = 25
        scale = float(self.app.status_text_scale.get())
        scaled_size = max(12, int(base_size * scale))
        
        self.tiles[key]["current_status"].configure(
            text=status_text,
            fg=status_color,
            font=("Pretendard", scaled_size, "bold")
        )

    def _autoscale_tile(self, key):
        """타일 자동 스케일링"""
        box = self.tiles.get(key)
        if not box:
            return
        f = box["frame"]
        w = max(f.winfo_width(), 1)
        h = max(f.winfo_height(), 1)

        sz_title = h * 0.14
        sz_val = h * 0.60
        sz_stat = h * 0.10  # 0.12에서 0.10으로 10% 축소

        s = float(self.app.tile_scale.get())
        sz_title = max(14, int(sz_title * s))
        sz_val = max(20, int(sz_val * s))
        sz_stat = max(8, int(sz_stat * s))  # 최소 크기도 9에서 8로 축소

        # 접속 대기 상태일 때 값(접속대기) 글자만 20% 축소
        # 가연성가스/연기 센서도 값이 "--"이거나 "센서 연결 대기중..." 텍스트인 경우 축소
        is_waiting = self._connection_status == "waiting"
        if not is_waiting:
            # 연결 상태이지만 값이 "--"이거나 텍스트가 "센서 연결 대기중..."인 경우 확인
            try:
                current_val = box["val"].cget("text")
                current_stat = box["stat"].cget("text")
                if current_val == "--" or current_val == "접속대기" or "센서 연결 대기중" in current_stat:
                    is_waiting = True
            except Exception:
                pass
        
        if is_waiting:
            sz_val = max(16, int(sz_val * 0.8))      # 20% 축소

        try:
            # 아이콘 크기는 타이틀의 1.5배 (50% 더 크게)
            sz_icon = max(21, int(sz_title * 1.5))
            if box.get("icon"):
                box["icon"].configure(font=("Pretendard", sz_icon, "bold"))
            box["title"].configure(font=("Pretendard", sz_title, "bold"))
            box["val"].configure(font=("Pretendard", sz_val, "bold"))
            box["stat"].configure(font=("Pretendard", sz_stat))
        except Exception:
            pass
        self._centerize_tile(key)

    def _centerize_tile(self, key):
        """타일 내부 라벨을 정중앙 기준 배치"""
        box = self.tiles.get(key)
        if not box:
            return
        try:
            for k in ("title_frame", "val", "stat"):
                if k in box and box[k]:
                    box[k].pack_forget()
            box["title_frame"].place(relx=0.5, rely=0.15, anchor="center")
            box["val"].place(relx=0.5, rely=0.50, anchor="center")
            box["stat"].place(relx=0.5, rely=0.85, anchor="center")
        except Exception:
            pass

    def set_connection_status(self, status):
        """접속 상태 설정"""
        old_status = self._connection_status
        self._connection_status = status
        if status == "waiting":
            for k in SENSOR_KEYS:
                # autoscale 수행되도록 skip_autoscale=False
                self.apply_gas_box(k, "--", "센서 연결 대기중...", False)
        elif status == "connected" and old_status == "waiting":
            # waiting -> connected 전환 시 타일 강제 갱신
            # "접속대기" 상태의 타일을 즉시 갱신할 수 있도록 함
            print(f"[PanelTiles] waiting -> connected 전환: 타일 강제 갱신")
            for k in SENSOR_KEYS:
                box = self.tiles.get(k)
                if box:
                    # 연결됨 상태로 전환 - 배경색을 기본 정상 색상으로 변경
                    bg = COLOR_TILE_OK
                    fg = ideal_fg(bg)
                    box["frame"].configure(bg=bg)
                    box["main_frame"].configure(bg=bg)
                    box["left_frame"].configure(bg=bg)
                    box["title_frame"].configure(bg=bg)
                    for lbl in ("val", "stat", "title"):
                        box[lbl].configure(bg=bg, fg=fg)
                    if box.get("icon"):
                        box["icon"].configure(bg=bg, fg=fg)
                    # 값은 데이터가 들어올 때까지 "--"로 표시
                    box["val"].configure(text="--")
                    # autoscale 적용
                    self._autoscale_tile(k)
        # disconnected는 SensorPanel에서 apply_gas_box_disconnected로 직접 처리

    def apply_gas_box(self, key, value, std_text, ok, skip_autoscale=False, alert_level=1):
        """가스 박스 적용"""
        box = self.tiles.get(key)
        if not box:
            return

        if self._connection_status == "waiting":
            bg = "#E8E8E8"
            fg = "#2C3E50"
            display_value = "접속대기"
            display_std = "센서 연결 대기중..."
            current_alert_level = 1  # 대기 상태는 정상으로 표시
        else:
            # connected 상태
            bg = COLOR_TILE_OK if ok else COLOR_ALARM
            fg = ideal_fg(bg)
            display_value = value
            display_std = std_text
            current_alert_level = alert_level

        # 배경색이 실제로 변경될 때만 업데이트
        current_bg = box["frame"].cget("bg")
        bg_changed = (current_bg != bg)

        if bg_changed:
            box["frame"].configure(bg=bg)
            box["main_frame"].configure(bg=bg)
            box["left_frame"].configure(bg=bg)
            box["title_frame"].configure(bg=bg)
            # 경보 기준 영역은 항상 진한 파랑색 유지
            box["right_frame"].configure(bg="#1976D2")
            # 배경색 변경 시 모든 라벨을 한 번에 업데이트 (개별 configure 호출 최소화)
            for k in ("val", "stat", "title"):
                box[k].configure(bg=bg, fg=fg)
            if box.get("icon"):
                box["icon"].configure(bg=bg, fg=fg)
            # 경보 기준 영역의 라벨들은 색상 유지를 위해 업데이트하지 않음

        # 텍스트만 변경 (배경색이 변하지 않았을 때)
        if box["val"].cget("text") != display_value:
            box["val"].configure(text=display_value)

        # autoscale은 필요할 때만 (리사이즈 이벤트 시)
        if not skip_autoscale:
            self._autoscale_tile(key)

        # 현재 상태 업데이트
        self._update_current_status(key, display_value, current_alert_level)

    def apply_gas_box_disconnected(self, key, value, std_text):
        """통신 끊김 상태로 가스 박스 표시 - 마지막 값을 회색으로"""
        box = self.tiles.get(key)
        if not box:
            return

        # 회색 배경 (좌측 센서값 영역만)
        bg = "#A0A0A0"
        fg = "#FFFFFF"

        # 좌측 센서값 영역만 회색으로 변경
        box["frame"].configure(bg=bg)
        box["main_frame"].configure(bg=bg)
        box["left_frame"].configure(bg=bg)
        box["title_frame"].configure(bg=bg)
        for k in ("val", "stat", "title"):
            box[k].configure(bg=bg, fg=fg)
        if box.get("icon"):
            box["icon"].configure(bg=bg, fg=fg)

        # 경보 기준 영역은 항상 파랑색/흰색 유지 (변경 없음)
        box["right_frame"].configure(bg="#1976D2")
        # top_frame, bottom_frame, alert_levels는 흰색 배경 유지
        if box.get("top_frame"):
            box["top_frame"].configure(bg="#FFFFFF")
        if box.get("bottom_frame"):
            box["bottom_frame"].configure(bg="#FFFFFF")
        if box.get("alert_title_label"):
            box["alert_title_label"].configure(bg="#FFFFFF", fg="#000000")
        for alert_label in box["alert_levels"]:
            alert_label.configure(bg="#FFFFFF")  # 흰색 배경 유지 (글자색은 원래 색상)
        if box.get("current_status"):
            box["current_status"].configure(bg="#FFFFFF")

        # 현재 상태 업데이트 (통신 끊김 상태)
        self._update_current_status(key, value, 1)  # 통신 끊김은 정상으로 표시

        # 값 업데이트 (마지막 값 유지)
        box["val"].configure(text=value if value != "--" else "---")

        # autoscale 적용
        self._autoscale_tile(key)

    def apply_gas_box_with_color(self, key, value, std_text, color, skip_autoscale=False, alert_level=1):
        """5단계 경보 색상으로 가스 박스 적용"""
        box = self.tiles.get(key)
        if not box:
            return

        if self._connection_status == "waiting":
            bg = "#E8E8E8"
            fg = "#2C3E50"
            display_value = "접속대기"
            display_std = "센서 연결 대기중..."
            current_alert_level = 1  # 대기 상태는 정상으로 표시
        else:
            # 5단계 경보 색상 사용
            bg = color
            fg = ideal_fg(color)
            display_value = value
            display_std = std_text
            current_alert_level = alert_level

        # 배경색이 실제로 변경될 때만 업데이트
        current_bg = box["frame"].cget("bg")
        bg_changed = (current_bg != bg)

        if bg_changed:
            box["frame"].configure(bg=bg)
            box["main_frame"].configure(bg=bg)
            box["left_frame"].configure(bg=bg)
            box["title_frame"].configure(bg=bg)
            # 경보 기준 영역은 항상 진한 파랑색 유지
            box["right_frame"].configure(bg="#1976D2")
            # 배경색 변경 시 모든 라벨을 한 번에 업데이트
            for k in ("val", "stat", "title"):
                box[k].configure(bg=bg, fg=fg)
            if box.get("icon"):
                box["icon"].configure(bg=bg, fg=fg)
            # 경보 기준 영역의 라벨들은 색상 유지를 위해 업데이트하지 않음

        # 텍스트만 변경 (배경색이 변하지 않았을 때)
        if box["val"].cget("text") != display_value:
            box["val"].configure(text=display_value)

        # autoscale은 필요할 때만 (리사이즈 이벤트 시)
        if not skip_autoscale:
            self._autoscale_tile(key)

        # 현재 상태 업데이트
        self._update_current_status(key, display_value, current_alert_level)

    def update_stat(self, key, stat_text):
        """통계 업데이트"""
        box = self.tiles.get(key)
        if box:
            box["stat"].configure(text=stat_text)

    def _update_status_text_scale(self):
        """현재상태 문구 크기 스케일 업데이트 (경보 기준 라벨도 함께 업데이트)"""
        try:
            scale = float(self.app.status_text_scale.get())
            base_size = 25
            scaled_size = max(12, int(base_size * scale))
            
            for key, tile in self.tiles.items():
                # 현재상태 문구 업데이트
                if "current_status" in tile and tile["current_status"] is not None:
                    try:
                        # 현재 텍스트와 색상 유지하면서 폰트 크기만 변경
                        current_text = tile["current_status"].cget("text")
                        current_fg = tile["current_status"].cget("fg")
                        
                        tile["current_status"].configure(
                            text=current_text,
                            fg=current_fg,
                            font=("Pretendard", scaled_size, "bold")
                        )
                    except Exception:
                        # 개별 타일 업데이트 실패는 무시
                        pass
                
                # 경보 기준 라벨들도 같은 크기로 업데이트
                if "alert_levels" in tile:
                    try:
                        for alert_label in tile["alert_levels"]:
                            current_text = alert_label.cget("text")
                            current_fg = alert_label.cget("fg")
                            alert_label.configure(
                                text=current_text,
                                fg=current_fg,
                                font=("Pretendard", scaled_size, "bold")
                            )
                    except Exception:
                        # 경보 기준 라벨 업데이트 실패는 무시
                        pass
        except Exception:
            # 전체 업데이트 실패는 무시
            pass

    def refresh_thresholds(self):
        """우측 경보 기준값 라벨을 현재 config 기준으로 갱신"""
        try:
            for key, tile in self.tiles.items():
                thresholds = self._get_sensor_thresholds(key)
                level_names = {1: "정상", 2: "관심", 3: "주의", 4: "경계", 5: "심각"}
                for idx, lbl in enumerate(tile.get("alert_levels", []), start=1):
                    if idx in thresholds:
                        lbl.configure(text=f"{level_names[idx]}: {thresholds[idx]}")
        except Exception:
            pass