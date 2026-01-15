"""
설정 관리자 클래스

config.conf 파일의 로드/저장 및 설정값 관리를 담당합니다.
"""

import os
import json
import configparser


class ConfigManager:
    """
    config.conf 로드/저장 관리
    [LISTEN] host, port
    [UI] tab_id_policy, layout, grid_cols, tile_scale
    [STANDARD] co2, co, h2s, o2_min, o2_max
    [ENV] temp_min, temp_max, temp_caution, temp_warning, temp_danger, hum_min, hum_max
    [VALUE] text
    [AUTH] enabled, users
    """
    
    def __init__(self, path):
        self.path = path or "config.conf"
        
        # 기본값 설정
        self.listen = {"host": "0.0.0.0", "port": 9000}
        self.ui = {
            "tab_id_policy": "by_ip", 
            "layout": "tabs", 
            "grid_cols": "3", 
            "tile_scale": "1.0"
        }
        # 5단계 경보 시스템 기본값
        self.std = {
            # 산소 (O₂)
            "o2_normal_min": 19.5, "o2_normal_max": 23.0,
            "o2_concern_min": 19.0, "o2_concern_max": 23.0,
            "o2_caution_min": 18.5, "o2_caution_max": 23.3,
            "o2_warning_min": 18.0, "o2_warning_max": 23.5,
            "o2_danger_min": 17.0, "o2_danger_max": 24.0,
            
            # 이산화탄소 (CO₂)
            "co2_normal_max": 1000, "co2_concern_max": 5000,
            "co2_caution_max": 10000, "co2_warning_max": 15000, "co2_danger_max": 20000,
            
            # 일산화탄소 (CO)
            "co_normal_max": 9, "co_concern_max": 25,
            "co_caution_max": 30, "co_warning_max": 50, "co_danger_max": 100,
            
            # 황화수소 (H₂S)
            "h2s_normal_max": 5, "h2s_concern_max": 8,
            "h2s_caution_max": 10, "h2s_warning_max": 15, "h2s_danger_max": 50,
            
            # 온도 (℃)
            "temp_normal_min": 18, "temp_normal_max": 28,
            "temp_concern_min": 16, "temp_concern_max": 30,
            "temp_caution_min": 14, "temp_caution_max": 32,
            "temp_warning_min": 12, "temp_warning_max": 33,
            "temp_danger_min": 10, "temp_danger_max": 35,
            
            # 습도 (RH%)
            "hum_normal_min": 40, "hum_normal_max": 60,
            "hum_concern_min": 30, "hum_concern_max": 70,
            "hum_caution_min": 20, "hum_caution_max": 80,
            "hum_warning_min": 20, "hum_warning_max": 80,
            "hum_danger_min": 15, "hum_danger_max": 85,
            
            # 체감온도 (HI)
            "hi_normal_max": 27, "hi_concern_max": 32,
            "hi_caution_max": 39, "hi_warning_max": 40, "hi_danger_max": 45,
            
            # 불쾌지수 (DI)
            "di_normal_max": 68, "di_concern_max": 75,
            "di_caution_max": 80, "di_warning_max": 80, "di_danger_max": 85,
            
            # 연기센서 (Smoke)
            "smoke_normal_max": 0, "smoke_concern_max": 10,
            "smoke_caution_max": 25, "smoke_warning_max": 50, "smoke_danger_max": 100,
            
            # 가연성가스/메탄 (LEL%/CH4) - v2.0에서 ch4로 통합
            "lel_normal_max": 10, "lel_concern_max": 20,
            "lel_caution_max": 50, "lel_warning_max": 50, "lel_danger_max": 100,

            # 메탄가스 (CH4 %LEL) - v2.0 신규
            "ch4_normal_max": 10, "ch4_concern_max": 20,
            "ch4_caution_max": 50, "ch4_warning_max": 50, "ch4_danger_max": 100
        }
        self.env = {
            "temp_min": 18, "temp_max": 26, "temp_caution": 28,
            "temp_warning": 30, "temp_danger": 32,
            "hum_min": 30, "hum_max": 70,
            "safety_education_photo": True,
            "signature_recognition": True,
            "water_sensor_enabled": True,
            # v2.0: 외부 접점 입력 설정
            "ext_input_enabled": True,  # 외부 접점 입력 사용 여부
            "ext_input_name": "외부접점",  # 외부 접점 표시 이름
            # v2.0: 메탄/가연성 가스 센서
            "ch4_sensor_enabled": True,  # 메탄 센서 사용 여부
            "smoke_sensor_enabled": True,  # 연기 센서 사용 여부
            "screen_size": "1280x720",
            # 그래프 기능 사용 여부 (기본: 활성화)
            "graph_enabled": True,
            # 동시에 그래프 보기 허용 여부 (기본: 비허용)
            "allow_multi_graph_view": False,
            # 최대 접속 센서 수 (레거시 호환용 기본값)
            "max_sensors": 4,
            # 안전장구 인식 설정
            "ppe_detection_enabled": True,  # 안전장구 인식 사용 여부
            "ppe_helmet_enabled": True,     # 헬멧 인식 사용
            "ppe_vest_enabled": True,       # 조끼 인식 사용
            "ppe_mask_enabled": True,       # 마스크 인식 사용
            "ppe_glasses_enabled": True,    # 보안경 인식 사용
            "ppe_gloves_enabled": True,     # 장갑 인식 사용
            "ppe_boots_enabled": True,      # 안전화 인식 사용
            "ppe_helmet_name": "헬멧",      # 헬멧 표시 이름
            "ppe_vest_name": "조끼",        # 조끼 표시 이름
            "ppe_mask_name": "마스크",      # 마스크 표시 이름
            "ppe_glasses_name": "보안경",   # 보안경 표시 이름
            "ppe_gloves_name": "장갑",      # 장갑 표시 이름
            "ppe_boots_name": "안전화",     # 안전화 표시 이름
            # 성능 설정 (1: 기본, 2: 얼굴+안전장구, 3: 전체+사물인식)
            # 1: N5095 등 저사양 - 얼굴 인식만
            # 2: i7 이상 CPU - 얼굴 + 안전장구 6종
            # 3: i7 + RTX 3060 이상 - 얼굴 + 안전장구 + 사물 인식
            "performance_mode": 2
        }
        self.camera = {
            "device_id": 0,
            "device_index": 0,  # USB 카메라 인덱스
            "resolution_width": 1920,
            "resolution_height": 1080,
            "fps": 30,
            "auto_focus": True,
            "flip_horizontal": True,  # 거울보기 좌우 반전 기본값: true
            "ip_cameras": [],  # IP 카메라 목록 (JSON 문자열로 저장)
            "use_ip_camera": False,  # IP 카메라 사용 여부
            "selected_ip_camera": "",  # 선택된 IP 카메라 이름
            "ip_camera_url": "",  # 선택된 IP 카메라 RTSP URL
            "ip_camera_name": ""  # 선택된 IP 카메라 표시 이름
        }
        self.value_text = "특고압 전기실입니다,관계자외 출입을 금합니다,공기질 측정중입니다"
        self.auth = {"enabled": "false", "users": ""}
        
        # 관리자 설정
        self.admin = {
            "admin_password": "8925b87e7c8387c1b51a1eea7e5bd33eb9edac6b42feb6947fb77cf5e3f26188:90e66e1c380098f7ae44eaa232b13791eae1692790864f3a4e8f485df145312a",
            "password_changed": False,
            "admin_mode": False
        }
        
        self.admin_mode = False  # 관리자 모드 상태 (런타임)

        # 표준 기본값 파일은 '국가 기준값 초기화' 미리보기/적용 시에만 사용
        # 런타임 임계값은 항상 config.conf의 [STANDARD] 값을 사용

        self.load()

    def _load_standard_defaults(self):
        """표준 기본값 파일(standard_defaults.conf)에서 초기값 로드"""
        try:
            defaults_path = os.path.join(os.path.dirname(self.path), "standard_defaults.conf")
            if os.path.exists(defaults_path):
                cfg = configparser.ConfigParser()
                cfg.read(defaults_path, encoding="utf-8")
                
                if cfg.has_section("STANDARD"):
                    print(f"표준 기본값 파일에서 초기값 로드: {defaults_path}")
                    for key in self.std.keys():
                        if cfg.has_option("STANDARD", key):
                            try:
                                self.std[key] = cfg.getfloat("STANDARD", key)
                            except ValueError:
                                # 숫자가 아닌 경우 문자열로 저장
                                self.std[key] = cfg.get("STANDARD", key)
                    print(f"표준 기본값 로드 완료: {len(self.std)}개 항목")
                else:
                    print("표준 기본값 파일에 [STANDARD] 섹션이 없습니다.")
            else:
                print(f"표준 기본값 파일이 없습니다: {defaults_path}")
        except Exception as e:
            print(f"표준 기본값 파일 로드 실패: {e}")

    def load(self):
        """설정 파일에서 설정값 로드"""
        if not os.path.exists(self.path):
            return
            
        cfg = configparser.ConfigParser()
        with open(self.path, encoding="utf-8") as f:
            cfg.read_file(f)

        g = lambda s, k, fb: cfg.get(s, k, fallback=fb)
        gf = lambda s, k, fb: cfg.getfloat(s, k, fallback=fb)
        gi = lambda s, k, fb: cfg.getint(s, k, fallback=fb)

        gb = lambda s, k, fb: g(s, k, str(fb)).lower() in ("1", "true", "yes", "on")

        self.listen = {
            "host": g("LISTEN", "host", self.listen["host"]),
            "port": gi("LISTEN", "port", self.listen["port"]),
            # v2.0 TLS 설정
            "tls_enabled": gb("LISTEN", "tls_enabled", False),
            "tls_cert": g("LISTEN", "tls_cert", ""),
            "tls_key": g("LISTEN", "tls_key", ""),
            # v2.0 HMAC 설정
            "hmac_enabled": gb("LISTEN", "hmac_enabled", False),
            "hmac_secret": g("LISTEN", "hmac_secret", ""),
            "require_signature": gb("LISTEN", "require_signature", False)
        }
        
        # UI 섹션의 모든 값을 읽어옴
        if cfg.has_section("UI"):
            for key in cfg.options("UI"):
                self.ui[key] = cfg.get("UI", key)

        # 필수 값들은 소문자로 변환
        if "tab_id_policy" in self.ui:
            self.ui["tab_id_policy"] = self.ui["tab_id_policy"].lower()
        if "layout" in self.ui:
            self.ui["layout"] = self.ui["layout"].lower()
        
        # STANDARD 섹션: 런타임 임계값은 config.conf의 값을 우선 사용
        if cfg.has_section("STANDARD"):
            # 5단계 경보 시스템 모든 값 로드
            for key in self.std.keys():
                self.std[key] = gf("STANDARD", key, self.std[key])
            
        if cfg.has_section("ENV"):
            # 기존 ENV 모든 키를 먼저 병합하여 보존
            try:
                existing_env = {}
                for key in cfg.options("ENV"):
                    try:
                        existing_env[key] = cfg.get("ENV", key)
                    except Exception:
                        continue
                self.env.update(existing_env)
            except Exception:
                pass

            # 알려진 키 타입 보정
            gb = lambda s, k, fb: cfg.get(s, k, fallback=str(fb)).lower() in ("1", "true", "yes", "on")
            try:
                # 기본값은 __init__에서 정의된 하드코딩된 값 사용 (self.env의 기존 값은 타입이 잘못될 수 있음)
                self.env["temp_min"] = gf("ENV", "temp_min", 18.0)
                self.env["temp_max"] = gf("ENV", "temp_max", 26.0)
                self.env["temp_caution"] = gf("ENV", "temp_caution", 28.0)
                self.env["temp_warning"] = gf("ENV", "temp_warning", 30.0)
                self.env["temp_danger"] = gf("ENV", "temp_danger", 32.0)
                self.env["hum_min"] = gf("ENV", "hum_min", 30.0)
                self.env["hum_max"] = gf("ENV", "hum_max", 70.0)
                self.env["safety_education_photo"] = gb("ENV", "safety_education_photo", True)
            except Exception:
                pass
        
        # CAMERA 섹션 로드
        if cfg.has_section("CAMERA"):
            gb = lambda s, k, fb: cfg.get(s, k, fallback=str(fb)).lower() in ("1", "true", "yes", "on")
            gi = lambda s, k, fb: cfg.getint(s, k, fallback=fb)
            gs = lambda s, k, fb: cfg.get(s, k, fallback=fb)
            try:
                self.camera["device_id"] = gi("CAMERA", "device_id", self.camera["device_id"])
                self.camera["device_index"] = gi("CAMERA", "device_index", self.camera["device_index"])
                self.camera["resolution_width"] = gi("CAMERA", "resolution_width", self.camera["resolution_width"])
                self.camera["resolution_height"] = gi("CAMERA", "resolution_height", self.camera["resolution_height"])
                self.camera["fps"] = gi("CAMERA", "fps", self.camera["fps"])
                self.camera["auto_focus"] = gb("CAMERA", "auto_focus", self.camera["auto_focus"])
                self.camera["flip_horizontal"] = gb("CAMERA", "flip_horizontal", self.camera["flip_horizontal"])
                self.camera["use_ip_camera"] = gb("CAMERA", "use_ip_camera", self.camera["use_ip_camera"])
                self.camera["selected_ip_camera"] = gs("CAMERA", "selected_ip_camera", self.camera["selected_ip_camera"])
                self.camera["ip_camera_url"] = gs("CAMERA", "ip_camera_url", self.camera["ip_camera_url"])
                self.camera["ip_camera_name"] = gs("CAMERA", "ip_camera_name", self.camera["ip_camera_name"])

                # IP 카메라 목록 로드 (JSON 문자열)
                ip_cameras_json = gs("CAMERA", "ip_cameras", "[]")
                try:
                    self.camera["ip_cameras"] = json.loads(ip_cameras_json)
                    if not isinstance(self.camera["ip_cameras"], list):
                        self.camera["ip_cameras"] = []
                except (json.JSONDecodeError, TypeError):
                    self.camera["ip_cameras"] = []
            except Exception as e:
                print(f"CAMERA 섹션 로드 오류: {e}")
            
        self.value_text = g("VALUE", "text", self.value_text)
        self.auth = {
            "enabled": g("AUTH", "enabled", self.auth["enabled"]), 
            "users": g("AUTH", "users", self.auth["users"])
        }
        
        # 관리자 설정 로드
        if cfg.has_section("ADMIN"):
            self.admin["admin_password"] = g("ADMIN", "admin_password", self.admin["admin_password"])
            self.admin["password_changed"] = cfg.getboolean("ADMIN", "password_changed", fallback=self.admin["password_changed"])
            self.admin["admin_mode"] = cfg.getboolean("ADMIN", "admin_mode", fallback=self.admin["admin_mode"])

    def save(self):
        """현재 설정을 파일에 저장 (비파괴 병합 저장)"""
        # 1) 기존 파일 로드 (존재 시)
        base = configparser.ConfigParser()
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    base.read_file(f)
            except Exception:
                base = configparser.ConfigParser()

        # 2) 섹션 보장
        for sec in ("LISTEN", "UI", "STANDARD", "ENV", "CAMERA", "VALUE", "AUTH", "ADMIN"):
            if not base.has_section(sec):
                base.add_section(sec)

        # 3) 섹션별로 '해당 키만' 업데이트 (기존 키는 유지)
        # LISTEN
        for k, v in self.listen.items():
            base.set("LISTEN", k, str(v))

        # UI (기존 키 유지)
        for k, v in self.ui.items():
            base.set("UI", k, str(v))

        # STANDARD (기존 키 유지)
        for k, v in self.std.items():
            base.set("STANDARD", k, str(v))

        # ENV (기존 키 유지)
        for k, v in self.env.items():
            base.set("ENV", k, str(v))

        # CAMERA (기존 키 유지)
        for k, v in self.camera.items():
            # ip_cameras는 JSON으로 직렬화
            if k == "ip_cameras":
                base.set("CAMERA", k, json.dumps(v, ensure_ascii=False))
            else:
                base.set("CAMERA", k, str(v))

        # VALUE
        base.set("VALUE", "text", self.value_text)

        # AUTH
        for k, v in self.auth.items():
            base.set("AUTH", k, str(v))

        # ADMIN
        for k, v in self.admin.items():
            base.set("ADMIN", k, str(v))

        # 4) 기록 (기존의 다른 섹션/키는 그대로 보존됨)
        with open(self.path, "w", encoding="utf-8") as f:
            base.write(f)

    def auth_enabled(self):
        """인증이 활성화되어 있는지 확인"""
        return self.auth.get("enabled", "false").lower() in ("1", "true", "yes", "on")
    
    def auth_map(self):
        """사용자 인증 맵 반환"""
        m = {}
        for pair in (self.auth.get("users", "") or "").split(","):
            pair = pair.strip()
            if pair and ":" in pair:
                a, b = pair.split(":", 1)
                m[a.strip()] = b.strip()
        return m
    
    def get_section(self, section_name, default=None):
        """특정 섹션의 모든 설정값을 딕셔너리로 반환"""
        if not os.path.exists(self.path):
            return default or {}
            
        cfg = configparser.ConfigParser()
        with open(self.path, encoding="utf-8") as f:
            cfg.read_file(f)
            
        if not cfg.has_section(section_name):
            return default or {}
            
        result = {}
        for key in cfg.options(section_name):
            result[key] = cfg.get(section_name, key)
        return result