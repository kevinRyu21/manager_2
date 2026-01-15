"""
기상청 API 연동 유틸리티

외부 IP 기반 위치 감지 및 기상청 API를 통한 날씨 정보 수집
"""

import requests
import json
import time
from datetime import datetime, timedelta
import re
from typing import Dict, Optional, Tuple


class WeatherAPI:
    """기상청 API 연동 클래스"""
    
    def __init__(self, api_key: str, lat: float = 37.9129, lon: float = 127.7863):
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.base_url = "http://apis.data.go.kr/1360000"
        
        # 기상청 격자 좌표 변환
        self.nx, self.ny = self._convert_latlon_to_grid(lat, lon)
        
        # 캐시 설정
        self._cache = {}
        self._cache_timeout = 600  # 10분
        
    def _convert_latlon_to_grid(self, lat: float, lon: float) -> Tuple[int, int]:
        """위도/경도를 기상청 격자 좌표로 변환"""
        # 기상청 격자 변환 공식
        re = 6371.00877  # 지구 반경
        grid = 5.0
        slat1 = 30.0
        slat2 = 60.0
        olon = 126.0
        olat = 38.0
        
        sn = math.tan(math.pi * (0.25 + slat2 / 360.0))
        sn = math.log(math.cos(slat1 * math.pi / 180.0) / math.cos(slat2 * math.pi / 180.0)) / math.log(sn)
        sf = math.tan(math.pi * (0.25 + slat1 / 360.0))
        sf = math.pow(sf, sn) * math.cos(slat1 * math.pi / 180.0) / sn
        ro = math.tan(math.pi * (0.25 + olat / 360.0))
        ro = re * sf / math.pow(ro, sn)
        
        ra = math.tan(math.pi * (0.25 + lat / 360.0))
        theta = lon - olon
        if theta > math.pi:
            theta -= 2.0 * math.pi
        if theta < -math.pi:
            theta += 2.0 * math.pi
        theta *= sn
        
        x = math.floor(ra * math.sin(theta) + (self.nx / 2.0) + 0.5)
        y = math.floor(ro - ra * math.cos(theta) + (self.ny / 2.0) + 0.5)
        
        return int(x), int(y)
    
    def get_current_location_from_ip(self) -> Optional[Tuple[float, float]]:
        """외부 IP를 통해 현재 위치 감지"""
        try:
            # IP 기반 위치 서비스 (여러 서비스 시도)
            services = [
                "http://ip-api.com/json/",
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
                            lat = data.get("lat")
                            lon = data.get("lon")
                        elif "ipapi.co" in service:
                            lat = data.get("latitude")
                            lon = data.get("longitude")
                        elif "ipinfo.io" in service:
                            loc = data.get("loc", "").split(",")
                            if len(loc) == 2:
                                lat = float(loc[0])
                                lon = float(loc[1])
                            else:
                                continue
                        
                        if lat and lon:
                            print(f"IP 기반 위치 감지: 위도 {lat}, 경도 {lon}")
                            return lat, lon
                            
                except Exception as e:
                    print(f"위치 서비스 {service} 실패: {e}")
                    continue
                    
        except Exception as e:
            print(f"IP 기반 위치 감지 실패: {e}")
            
        return None
    
    def get_current_weather(self) -> Optional[Dict]:
        """현재 날씨 정보 조회"""
        cache_key = "current_weather"
        current_time = time.time()
        
        # 캐시 확인
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if current_time - cached_time < self._cache_timeout:
                return cached_data
        
        try:
            # 현재 시간 기준으로 API 호출
            now = datetime.now()
            base_date = now.strftime("%Y%m%d")
            base_time = self._get_base_time(now)
            
            # 초단기실황 API
            url = f"{self.base_url}/VilageFcstInfoService_2.0/getUltraSrtNcst"
            params = {
                "serviceKey": self.api_key,
                "numOfRows": 100,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": self.nx,
                "ny": self.ny
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                    items = data["response"]["body"]["items"]["item"]
                    
                    weather_data = self._parse_current_weather(items)
                    
                    # 캐시 저장
                    self._cache[cache_key] = (weather_data, current_time)
                    return weather_data
                else:
                    print(f"기상청 API 오류: {data.get('response', {}).get('header', {}).get('resultMsg', 'Unknown error')}")
                    
        except Exception as e:
            print(f"현재 날씨 조회 실패: {e}")
            
        return None
    
    def get_weather_forecast(self) -> Optional[Dict]:
        """날씨 예보 조회"""
        cache_key = "weather_forecast"
        current_time = time.time()
        
        # 캐시 확인
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if current_time - cached_time < self._cache_timeout:
                return cached_data
        
        try:
            # 현재 시간 기준으로 API 호출
            now = datetime.now()
            base_date = now.strftime("%Y%m%d")
            base_time = self._get_base_time(now)
            
            # 초단기예보 API
            url = f"{self.base_url}/VilageFcstInfoService_2.0/getUltraSrtFcst"
            params = {
                "serviceKey": self.api_key,
                "numOfRows": 1000,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": self.nx,
                "ny": self.ny
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                    items = data["response"]["body"]["items"]["item"]
                    
                    forecast_data = self._parse_forecast(items)
                    
                    # 캐시 저장
                    self._cache[cache_key] = (forecast_data, current_time)
                    return forecast_data
                else:
                    print(f"기상청 예보 API 오류: {data.get('response', {}).get('header', {}).get('resultMsg', 'Unknown error')}")
                    
        except Exception as e:
            print(f"날씨 예보 조회 실패: {e}")
            
        return None
    
    def _get_base_time(self, now: datetime) -> str:
        """API 호출을 위한 기준 시간 계산"""
        hour = now.hour
        minute = now.minute
        
        # 기상청 API는 매시 30분에 데이터 갱신
        if minute < 30:
            hour = (hour - 1) % 24
            
        return f"{hour:02d}00"
    
    def _parse_current_weather(self, items: list) -> Dict:
        """현재 날씨 데이터 파싱"""
        weather_data = {
            "temperature": None,
            "humidity": None,
            "sky_condition": None,
            "precipitation": None,
            "wind_speed": None,
            "wind_direction": None
        }
        
        for item in items:
            category = item.get("category")
            value = item.get("obsrValue")
            
            if category == "T1H":  # 기온
                weather_data["temperature"] = float(value)
            elif category == "REH":  # 습도
                weather_data["humidity"] = float(value)
            elif category == "SKY":  # 하늘상태
                weather_data["sky_condition"] = self._get_sky_condition(int(value))
            elif category == "PTY":  # 강수형태
                weather_data["precipitation"] = self._get_precipitation_type(int(value))
            elif category == "WSD":  # 풍속
                weather_data["wind_speed"] = float(value)
            elif category == "VEC":  # 풍향
                weather_data["wind_direction"] = int(value)
                
        return weather_data
    
    def _parse_forecast(self, items: list) -> Dict:
        """예보 데이터 파싱"""
        forecast_data = {
            "hourly": [],
            "daily": []
        }
        
        # 시간별 예보 (최대 6시간)
        hourly_data = {}
        
        for item in items:
            fcst_date = item.get("fcstDate")
            fcst_time = item.get("fcstTime")
            category = item.get("category")
            value = item.get("fcstValue")
            
            time_key = f"{fcst_date}_{fcst_time}"
            
            if time_key not in hourly_data:
                hourly_data[time_key] = {
                    "date": fcst_date,
                    "time": fcst_time,
                    "temperature": None,
                    "sky_condition": None,
                    "precipitation": None,
                    "humidity": None
                }
            
            if category == "T1H":  # 기온
                hourly_data[time_key]["temperature"] = float(value)
            elif category == "SKY":  # 하늘상태
                hourly_data[time_key]["sky_condition"] = self._get_sky_condition(int(value))
            elif category == "PTY":  # 강수형태
                hourly_data[time_key]["precipitation"] = self._get_precipitation_type(int(value))
            elif category == "REH":  # 습도
                hourly_data[time_key]["humidity"] = float(value)
        
        # 시간순 정렬
        forecast_data["hourly"] = sorted(hourly_data.values(), key=lambda x: (x["date"], x["time"]))[:6]
        
        return forecast_data
    
    def _get_sky_condition(self, sky_code: int) -> str:
        """하늘상태 코드를 한글 설명으로 변환"""
        sky_conditions = {
            1: "맑음",
            3: "구름많음", 
            4: "흐림"
        }
        return sky_conditions.get(sky_code, "정보없음")
    
    def _get_precipitation_type(self, pty_code: int) -> str:
        """강수형태 코드를 한글 설명으로 변환"""
        precipitation_types = {
            0: "없음",
            1: "비",
            2: "비/눈",
            3: "눈",
            4: "소나기"
        }
        return precipitation_types.get(pty_code, "정보없음")
    
    def get_weather_icon(self, sky_condition: str, precipitation: str) -> str:
        """날씨 상태에 따른 아이콘 반환"""
        if precipitation and precipitation != "없음":
            if "비" in precipitation:
                return "🌧️"
            elif "눈" in precipitation:
                return "🌨️"
            elif "소나기" in precipitation:
                return "⛈️"
        
        if sky_condition == "맑음":
            return "☀️"
        elif sky_condition == "구름많음":
            return "⛅"
        elif sky_condition == "흐림":
            return "☁️"
        
        return "ℹ️"
    
    def get_location_name(self) -> str:
        """현재 위치의 지역명 반환"""
        # 강원특별자치도 춘천시 동면 기준
        return "강원특별자치도, 춘천시"


# 수학 모듈 import 추가
import math
