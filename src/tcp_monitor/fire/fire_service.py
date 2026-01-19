"""
화재 감지 서비스

센서 데이터를 수신하여 화재 감지를 수행하고 UI에 결과를 전달합니다.
"""

import threading
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass


# 화재 감지 모듈 임포트
try:
    from .models import (
        FireAlertLevel,
        SensorReading,
        FireDetectionResult,
        FIRE_PROBABILITY_THRESHOLDS
    )
    from .detector import FireDetector, MultiSensorFireDetector
    from .adaptive import AdaptiveFireSystem
    FIRE_MODULE_AVAILABLE = True
except ImportError:
    FIRE_MODULE_AVAILABLE = False
    FireAlertLevel = None
    SensorReading = None
    FireDetectionResult = None


@dataclass
class FireServiceConfig:
    """화재 서비스 설정"""
    enabled: bool = True
    adaptive_learning: bool = True
    alert_threshold: int = 3  # 이 레벨 이상에서 경보 다이얼로그 표시
    update_interval_ms: int = 1000  # UI 업데이트 간격 (ms)


class FireDetectionService:
    """화재 감지 서비스 클래스"""

    def __init__(self, config: Optional[FireServiceConfig] = None):
        """
        Args:
            config: 서비스 설정
        """
        self.config = config or FireServiceConfig()
        self._lock = threading.Lock()

        # 화재 감지기
        self._detector = None
        self._multi_detector = None
        self._adaptive_system = None

        # 콜백 함수들
        self._on_fire_alert_callback = None
        self._on_level_change_callback = None
        self._on_ui_update_callback = None

        # 상태
        self._current_level = 1
        self._current_probability = 0.0
        self._triggered_sensors = []
        self._last_results = {}  # sensor_id -> FireDetectionResult

        # 초기화
        if FIRE_MODULE_AVAILABLE and self.config.enabled:
            self._initialize_detectors()

    def _initialize_detectors(self):
        """감지기 초기화"""
        try:
            self._detector = FireDetector()
            self._multi_detector = MultiSensorFireDetector()

            if self.config.adaptive_learning:
                self._adaptive_system = AdaptiveFireSystem()

            print("[FireService] 화재 감지 시스템 초기화 완료")
        except Exception as e:
            print(f"[FireService] 초기화 오류: {e}")

    def set_callbacks(
        self,
        on_fire_alert: Optional[Callable[[int, float, List[str], Dict], None]] = None,
        on_level_change: Optional[Callable[[int, int], None]] = None,
        on_ui_update: Optional[Callable[[Dict], None]] = None
    ):
        """콜백 함수 설정

        Args:
            on_fire_alert: 화재 경보 발생 시 콜백 (level, probability, triggered_sensors, sensor_values)
            on_level_change: 경보 레벨 변경 시 콜백 (old_level, new_level)
            on_ui_update: UI 업데이트용 콜백 (상태 딕셔너리)
        """
        self._on_fire_alert_callback = on_fire_alert
        self._on_level_change_callback = on_level_change
        self._on_ui_update_callback = on_ui_update

    def process_sensor_data(
        self,
        sensor_id: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        co: Optional[float] = None,
        co2: Optional[float] = None,
        o2: Optional[float] = None,
        smoke: Optional[float] = None,
        h2s: Optional[float] = None,
        ch4: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """센서 데이터 처리 및 화재 감지

        Args:
            sensor_id: 센서 ID
            temperature: 온도 (°C)
            humidity: 습도 (%)
            co: 일산화탄소 (ppm)
            co2: 이산화탄소 (ppm)
            o2: 산소 (%)
            smoke: 연기 농도
            h2s: 황화수소 (ppm)
            ch4: 메탄/가연성가스 (%LEL)

        Returns:
            화재 감지 결과 딕셔너리 또는 None
        """
        if not FIRE_MODULE_AVAILABLE or not self.config.enabled:
            return None

        if self._detector is None:
            return None

        try:
            # SensorReading 생성
            reading = SensorReading(
                sensor_id=sensor_id,
                timestamp=datetime.now(),
                temperature=temperature,
                humidity=humidity,
                co=co,
                co2=co2,
                o2=o2,
                smoke=smoke,
                h2s=h2s,
                ch4=ch4
            )

            # 화재 감지 수행
            result = self._detector.detect(reading)

            # 결과 저장
            with self._lock:
                self._last_results[sensor_id] = result

            # 적응형 시스템 처리
            if self._adaptive_system:
                self._adaptive_system.process_reading(reading, result.fire_probability)

            # 레벨 변경 확인 및 콜백
            new_level = result.alert_level.value if result.alert_level else 1
            old_level = self._current_level

            if new_level != old_level:
                self._current_level = new_level
                if self._on_level_change_callback:
                    self._on_level_change_callback(old_level, new_level)

            self._current_probability = result.fire_probability
            # sensor_contributions에서 기여도가 높은 센서를 triggered_sensors로 변환
            self._triggered_sensors = []
            if result.sensor_contributions:
                self._triggered_sensors = [k for k, v in result.sensor_contributions.items() if v >= 0.1]

            # 화재 경보 콜백 (임계값 이상일 때)
            if new_level >= self.config.alert_threshold:
                sensor_values = {
                    "temperature": temperature,
                    "humidity": humidity,
                    "co": co,
                    "co2": co2,
                    "o2": o2,
                    "smoke": smoke,
                }
                if self._on_fire_alert_callback:
                    self._on_fire_alert_callback(
                        new_level,
                        result.fire_probability,
                        self._triggered_sensors,
                        sensor_values
                    )

            # UI 업데이트 콜백
            if self._on_ui_update_callback:
                self._on_ui_update_callback(self.get_status())

            return self._result_to_dict(result)

        except Exception as e:
            print(f"[FireService] 처리 오류: {e}")
            return None

    def _result_to_dict(self, result: Any) -> Dict[str, Any]:
        """FireDetectionResult를 딕셔너리로 변환"""
        if not result:
            return {}

        return {
            "sensor_id": result.sensor_id,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            "fire_probability": result.fire_probability,
            "alert_level": result.alert_level.value if result.alert_level else 1,
            "alert_level_name": result.alert_level.korean_name if result.alert_level else "정상",
            "triggered_sensors": result.triggered_sensors or [],
            "combination_rules_triggered": result.combination_rules_triggered or [],
            "confidence": result.confidence,
        }

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        status = {
            "enabled": self.config.enabled and FIRE_MODULE_AVAILABLE,
            "current_level": self._current_level,
            "current_probability": self._current_probability,
            "triggered_sensors": self._triggered_sensors,
            "adaptive_learning": self.config.adaptive_learning,
        }

        # 적응형 시스템 상태 추가
        if self._adaptive_system:
            try:
                adaptive_status = self._adaptive_system.get_status()
                status["adaptive"] = adaptive_status
            except:
                pass

        return status

    def get_current_level(self) -> int:
        """현재 경보 레벨 반환"""
        return self._current_level

    def get_fire_probability(self) -> float:
        """현재 화재 확률 반환"""
        return self._current_probability

    def get_triggered_sensors(self) -> List[str]:
        """경보 발생 센서 목록 반환"""
        return self._triggered_sensors.copy()

    def reset(self):
        """상태 초기화"""
        with self._lock:
            self._current_level = 1
            self._current_probability = 0.0
            self._triggered_sensors = []
            self._last_results = {}

    def update_thresholds(self) -> bool:
        """적응형 임계값 업데이트 (수동 트리거)"""
        if not self._adaptive_system:
            return False

        try:
            success, message = self._adaptive_system.update_thresholds()
            print(f"[FireService] 임계값 업데이트: {message}")
            return success
        except Exception as e:
            print(f"[FireService] 임계값 업데이트 오류: {e}")
            return False

    def get_learning_summary(self) -> Optional[Dict[str, Any]]:
        """AI 학습 요약 정보 반환"""
        if not self._adaptive_system:
            return None

        try:
            return self._adaptive_system.get_learning_summary()
        except Exception as e:
            print(f"[FireService] 학습 요약 조회 오류: {e}")
            return None

    def get_sensor_learning_stats(self) -> Optional[Dict[str, Any]]:
        """센서별 학습 통계 반환"""
        if not self._adaptive_system:
            return None

        try:
            return self._adaptive_system.get_sensor_learning_stats()
        except Exception as e:
            print(f"[FireService] 학습 통계 조회 오류: {e}")
            return None


# 전역 서비스 인스턴스 (싱글톤 패턴)
_fire_service_instance: Optional[FireDetectionService] = None


def get_fire_service(config: Optional[FireServiceConfig] = None) -> FireDetectionService:
    """화재 감지 서비스 인스턴스 반환 (싱글톤)

    Args:
        config: 초기 설정 (첫 호출 시에만 적용)

    Returns:
        FireDetectionService 인스턴스
    """
    global _fire_service_instance

    if _fire_service_instance is None:
        _fire_service_instance = FireDetectionService(config)

    return _fire_service_instance


def reset_fire_service():
    """서비스 인스턴스 리셋 (테스트용)"""
    global _fire_service_instance
    _fire_service_instance = None
