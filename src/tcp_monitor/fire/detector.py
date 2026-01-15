"""
화재 감지기 (Fire Detector)
GARAMe Manager v2.0

다중 센서 데이터를 융합하여 화재를 감지하고 5단계 경보를 발생합니다.
Dempster-Shafer 증거 이론과 퍼지 멤버십 함수를 사용합니다.
"""

from typing import Dict, List, Optional, Tuple, Deque
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import threading

from .models import (
    SensorReading,
    FireDetectionResult,
    FireAlertLevel,
    SENSOR_WEIGHTS,
    FIRE_PROBABILITY_THRESHOLDS,
    STANDARD_THRESHOLDS
)
from .dempster_shafer import (
    MassFunction,
    DempsterShaferCombiner,
    ImprovedDempsterShafer
)
from .fuzzy import FuzzyMembershipFunctions, FuzzyMembershipConfig


logger = logging.getLogger(__name__)


@dataclass
class SensorHistory:
    """센서 이력 (온도 상승률 계산용)"""
    max_size: int = 60  # 최근 60개 (1분 데이터 @ 1Hz)
    readings: Deque[Tuple[datetime, float]] = field(default_factory=deque)

    def add(self, timestamp: datetime, value: float):
        """측정값 추가"""
        self.readings.append((timestamp, value))
        while len(self.readings) > self.max_size:
            self.readings.popleft()

    def get_rate(self, seconds: int = 60) -> Optional[float]:
        """
        변화율 계산 (단위/분)

        Args:
            seconds: 계산 구간 (초)

        Returns:
            분당 변화율 또는 None (데이터 부족)
        """
        if len(self.readings) < 2:
            return None

        now = self.readings[-1][0]
        cutoff = now - timedelta(seconds=seconds)

        # 구간 내 첫 번째 값 찾기
        first_value = None
        first_time = None
        for ts, val in self.readings:
            if ts >= cutoff:
                first_value = val
                first_time = ts
                break

        if first_value is None:
            return None

        last_value = self.readings[-1][1]
        last_time = self.readings[-1][0]

        time_diff = (last_time - first_time).total_seconds()
        if time_diff < 10:  # 최소 10초 데이터 필요
            return None

        # 분당 변화율로 변환
        value_diff = last_value - first_value
        return (value_diff / time_diff) * 60


class FireDetector:
    """
    화재 감지기

    다중 센서 데이터를 융합하여 화재 확률을 계산하고
    5단계 경보를 발생합니다.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        sensor_weights: Optional[Dict[str, float]] = None,
        use_improved_ds: bool = True,
        temporal_weight: float = 0.3,
        history_size: int = 60
    ):
        """
        Args:
            thresholds: 커스텀 임계값 (없으면 표준값 사용)
            sensor_weights: 센서별 가중치 (없으면 기본값 사용)
            use_improved_ds: 개선된 D-S 알고리즘 사용 여부
            temporal_weight: 시간적 평활화 가중치 (0~1)
            history_size: 센서 이력 크기
        """
        self.thresholds = thresholds or STANDARD_THRESHOLDS.copy()
        self.sensor_weights = sensor_weights or SENSOR_WEIGHTS.copy()

        # 퍼지 멤버십 함수 초기화
        fuzzy_config = FuzzyMembershipConfig(self.thresholds)
        self.fuzzy = FuzzyMembershipFunctions(fuzzy_config)

        # Dempster-Shafer 조합기 초기화
        if use_improved_ds:
            self.ds_combiner = ImprovedDempsterShafer(
                temporal_weight=temporal_weight
            )
        else:
            self.ds_combiner = DempsterShaferCombiner()

        # 센서별 이력 관리
        self.history_size = history_size
        self.sensor_histories: Dict[str, Dict[str, SensorHistory]] = {}
        self._lock = threading.Lock()

        # 경보 이력
        self.alert_history: Deque[FireDetectionResult] = deque(maxlen=100)

        # 오경보 방지 필터
        self.consecutive_alerts = 0
        self.min_consecutive_for_alarm = 3  # 연속 3회 이상 시 경보

        # 센서 조합 규칙
        self.combination_rules = self._init_combination_rules()

    def _init_combination_rules(self) -> List[Dict]:
        """
        센서 조합 규칙 초기화

        특정 센서 조합이 동시에 발생하면 화재 확률을 높입니다.
        """
        return [
            {
                'name': 'smoke_and_temp_rise',
                'description': '연기 + 온도 상승',
                'conditions': {
                    'smoke': lambda v: v and v > 10,
                    'temp_rate': lambda v: v and v > 2
                },
                'boost': 0.2,
                'message': '연기와 급격한 온도 상승이 동시에 감지됨'
            },
            {
                'name': 'smoke_and_co',
                'description': '연기 + CO 상승',
                'conditions': {
                    'smoke': lambda v: v and v > 10,
                    'co': lambda v: v and v > 30
                },
                'boost': 0.25,
                'message': '연기와 일산화탄소가 동시에 상승 - 연소 진행 중'
            },
            {
                'name': 'co_and_o2_drop',
                'description': 'CO 상승 + O2 감소',
                'conditions': {
                    'co': lambda v: v and v > 50,
                    'o2': lambda v: v and v < 19.5
                },
                'boost': 0.2,
                'message': 'CO 상승과 O2 감소 - 밀폐 공간 연소 가능성'
            },
            {
                'name': 'rapid_temp_rise',
                'description': '급격한 온도 상승',
                'conditions': {
                    'temp_rate': lambda v: v and v > 5,
                    'temperature': lambda v: v and v > 35
                },
                'boost': 0.15,
                'message': '급격한 온도 상승 감지'
            },
            {
                'name': 'multi_gas_alert',
                'description': '다중 가스 이상',
                'conditions': {
                    'co': lambda v: v and v > 30,
                    'co2': lambda v: v and v > 2000,
                    'o2': lambda v: v and v < 19.5
                },
                'boost': 0.3,
                'message': '다중 가스 센서 동시 이상 - 화재 가능성 높음'
            },
            {
                'name': 'flashover_warning',
                'description': 'Flashover 임박',
                'conditions': {
                    'temperature': lambda v: v and v > 55,
                    'smoke': lambda v: v and v > 50,
                    'co': lambda v: v and v > 100
                },
                'boost': 0.4,
                'level_override': FireAlertLevel.DANGER,
                'message': '⚠️ Flashover 임박 - 즉시 대피 필요!'
            }
        ]

    def _get_sensor_history(
        self,
        sensor_id: str,
        sensor_type: str
    ) -> SensorHistory:
        """센서 이력 가져오기 (없으면 생성)"""
        with self._lock:
            if sensor_id not in self.sensor_histories:
                self.sensor_histories[sensor_id] = {}

            if sensor_type not in self.sensor_histories[sensor_id]:
                self.sensor_histories[sensor_id][sensor_type] = SensorHistory(
                    max_size=self.history_size
                )

            return self.sensor_histories[sensor_id][sensor_type]

    def _calculate_temp_rate(
        self,
        sensor_id: str,
        temperature: Optional[float],
        timestamp: datetime
    ) -> Optional[float]:
        """온도 상승률 계산"""
        if temperature is None:
            return None

        history = self._get_sensor_history(sensor_id, 'temperature')
        history.add(timestamp, temperature)
        return history.get_rate(seconds=60)

    def _get_sensor_mass_functions(
        self,
        reading: SensorReading
    ) -> List[Tuple[MassFunction, float, str]]:
        """
        센서 값들을 Mass Function으로 변환

        Returns:
            [(MassFunction, weight, sensor_name), ...] 리스트
        """
        results = []

        # 온도 상승률 계산
        temp_rate = self._calculate_temp_rate(
            reading.sensor_id,
            reading.temperature,
            reading.timestamp
        )

        # 센서별 처리
        sensor_values = {
            'smoke': reading.smoke,
            'co': reading.co,
            'temperature': reading.temperature,
            'temp_rate': temp_rate,
            'o2': reading.o2,
            'co2': reading.co2,
            'ch4': reading.ch4,
            'h2s': reading.h2s,
            'humidity': reading.humidity
        }

        for sensor_name, value in sensor_values.items():
            if value is None:
                continue

            weight = self.sensor_weights.get(sensor_name, 0.05)
            membership_func = self.fuzzy.get_membership_function(sensor_name)
            mass_function = membership_func(value)

            results.append((mass_function, weight, sensor_name))

        return results

    def _check_combination_rules(
        self,
        reading: SensorReading,
        temp_rate: Optional[float]
    ) -> Tuple[float, List[str], Optional[FireAlertLevel]]:
        """
        센서 조합 규칙 검사

        Returns:
            (boost_total, triggered_rules, level_override)
        """
        sensor_values = {
            'smoke': reading.smoke,
            'co': reading.co,
            'temperature': reading.temperature,
            'temp_rate': temp_rate,
            'o2': reading.o2,
            'co2': reading.co2,
            'ch4': reading.ch4,
            'h2s': reading.h2s,
            'humidity': reading.humidity
        }

        boost_total = 0.0
        triggered_rules = []
        level_override = None

        for rule in self.combination_rules:
            all_conditions_met = True

            for sensor_name, condition in rule['conditions'].items():
                value = sensor_values.get(sensor_name)
                if not condition(value):
                    all_conditions_met = False
                    break

            if all_conditions_met:
                boost_total += rule['boost']
                triggered_rules.append(rule['message'])

                if 'level_override' in rule:
                    if level_override is None or rule['level_override'].value > level_override.value:
                        level_override = rule['level_override']

        return boost_total, triggered_rules, level_override

    def _determine_alert_level(
        self,
        fire_probability: float,
        level_override: Optional[FireAlertLevel] = None
    ) -> FireAlertLevel:
        """화재 확률에 따른 경보 단계 결정"""
        if level_override:
            return level_override

        for level in reversed(list(FireAlertLevel)):
            threshold = FIRE_PROBABILITY_THRESHOLDS[level]
            if fire_probability >= threshold:
                return level

        return FireAlertLevel.NORMAL

    def _get_recommended_action(self, level: FireAlertLevel) -> str:
        """경보 단계별 권장 조치"""
        actions = {
            FireAlertLevel.NORMAL: "일상 모니터링 유지",
            FireAlertLevel.WATCH: "환기 상태 점검, 센서 주변 확인",
            FireAlertLevel.CAUTION: "현장 확인 필요, 대피 준비",
            FireAlertLevel.WARNING: "즉시 대피, 소방서 신고 (119)",
            FireAlertLevel.DANGER: "긴급 대피! 소방대 진입 금지 구역"
        }
        return actions.get(level, "")

    def detect(self, reading: SensorReading) -> FireDetectionResult:
        """
        화재 감지 수행

        Args:
            reading: 센서 측정값

        Returns:
            화재 감지 결과
        """
        # 1. 센서별 Mass Function 생성
        mass_functions = self._get_sensor_mass_functions(reading)

        if not mass_functions:
            # 센서 데이터 없음
            return FireDetectionResult(
                sensor_id=reading.sensor_id,
                timestamp=reading.timestamp,
                fire_probability=0.0,
                alert_level=FireAlertLevel.NORMAL,
                belief_fire=0.0,
                belief_normal=0.9,
                uncertainty=0.1,
                message="센서 데이터 없음"
            )

        # 2. Dempster-Shafer 융합
        mfs_with_weights = [(mf, w) for mf, w, _ in mass_functions]

        if isinstance(self.ds_combiner, ImprovedDempsterShafer):
            combined = self.ds_combiner.combine_with_temporal(
                [mf for mf, _ in mfs_with_weights],
                [w for _, w in mfs_with_weights]
            )
        else:
            combined = self.ds_combiner.combine_weighted(mfs_with_weights)

        # 3. 센서별 기여도 계산
        sensor_contributions = {}
        for mf, weight, name in mass_functions:
            contribution = mf.fire * weight
            sensor_contributions[name] = round(contribution, 4)

        # 4. 기본 화재 확률 (Pignistic)
        fire_probability = self.ds_combiner.get_pignistic_probability(combined)

        # 5. 센서 조합 규칙 적용
        temp_rate = self._calculate_temp_rate(
            reading.sensor_id,
            reading.temperature,
            reading.timestamp
        )
        boost, triggered_rules, level_override = self._check_combination_rules(
            reading, temp_rate
        )

        # 부스트 적용 (최대 0.95)
        fire_probability = min(0.95, fire_probability + boost)

        # 6. 경보 단계 결정
        alert_level = self._determine_alert_level(fire_probability, level_override)

        # 7. 오경보 방지 필터
        if alert_level.value >= FireAlertLevel.CAUTION.value:
            self.consecutive_alerts += 1
            if self.consecutive_alerts < self.min_consecutive_for_alarm:
                # 연속 경보가 충분하지 않으면 한 단계 낮춤
                alert_level = FireAlertLevel(max(1, alert_level.value - 1))
        else:
            self.consecutive_alerts = 0

        # 8. 메시지 생성
        if triggered_rules:
            message = " / ".join(triggered_rules)
        elif alert_level == FireAlertLevel.NORMAL:
            message = "모든 센서 정상 범위"
        else:
            message = f"화재 확률 {fire_probability:.1%}"

        # 9. 결과 생성
        result = FireDetectionResult(
            sensor_id=reading.sensor_id,
            timestamp=reading.timestamp,
            fire_probability=round(fire_probability, 4),
            alert_level=alert_level,
            belief_fire=round(combined.fire, 4),
            belief_normal=round(combined.normal, 4),
            uncertainty=round(combined.uncertain, 4),
            sensor_contributions=sensor_contributions,
            triggered_rules=triggered_rules,
            message=message,
            recommended_action=self._get_recommended_action(alert_level)
        )

        # 이력 저장
        self.alert_history.append(result)

        # 로깅 (경고 이상만)
        if alert_level.value >= FireAlertLevel.CAUTION.value:
            logger.warning(
                f"[{reading.sensor_id}] 화재 경보 {alert_level.korean_name}: "
                f"확률={fire_probability:.1%}, {message}"
            )

        return result

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """
        임계값 업데이트 (AI 적응형 시스템용)

        Args:
            new_thresholds: 새로운 임계값
        """
        self.thresholds.update(new_thresholds)
        self.fuzzy.update_thresholds(new_thresholds)
        logger.info(f"화재 감지 임계값 업데이트: {len(new_thresholds)}개 항목")

    def reset(self, sensor_id: Optional[str] = None):
        """
        상태 초기화

        Args:
            sensor_id: 특정 센서만 초기화 (None이면 전체)
        """
        with self._lock:
            if sensor_id:
                if sensor_id in self.sensor_histories:
                    del self.sensor_histories[sensor_id]
            else:
                self.sensor_histories.clear()

        if isinstance(self.ds_combiner, ImprovedDempsterShafer):
            self.ds_combiner.reset_temporal()

        self.consecutive_alerts = 0
        logger.info(f"화재 감지기 초기화: sensor_id={sensor_id or 'all'}")

    def get_statistics(self) -> Dict:
        """통계 정보 반환"""
        if not self.alert_history:
            return {
                'total_detections': 0,
                'alert_distribution': {},
                'max_probability': 0.0,
                'avg_probability': 0.0
            }

        alert_dist = {}
        for level in FireAlertLevel:
            count = sum(1 for r in self.alert_history if r.alert_level == level)
            alert_dist[level.korean_name] = count

        probabilities = [r.fire_probability for r in self.alert_history]

        return {
            'total_detections': len(self.alert_history),
            'alert_distribution': alert_dist,
            'max_probability': max(probabilities),
            'avg_probability': sum(probabilities) / len(probabilities),
            'consecutive_alerts': self.consecutive_alerts
        }


class MultiSensorFireDetector:
    """
    다중 센서 화재 감지기

    여러 센서의 데이터를 관리하고 전체 시스템의 화재 상태를 판단합니다.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        sensor_weights: Optional[Dict[str, float]] = None
    ):
        self.detectors: Dict[str, FireDetector] = {}
        self.thresholds = thresholds or STANDARD_THRESHOLDS.copy()
        self.sensor_weights = sensor_weights or SENSOR_WEIGHTS.copy()
        self._lock = threading.Lock()

    def _get_detector(self, sensor_id: str) -> FireDetector:
        """센서별 감지기 가져오기 (없으면 생성)"""
        with self._lock:
            if sensor_id not in self.detectors:
                self.detectors[sensor_id] = FireDetector(
                    thresholds=self.thresholds.copy(),
                    sensor_weights=self.sensor_weights.copy()
                )
            return self.detectors[sensor_id]

    def detect(self, reading: SensorReading) -> FireDetectionResult:
        """개별 센서 감지"""
        detector = self._get_detector(reading.sensor_id)
        return detector.detect(reading)

    def detect_all(
        self,
        readings: List[SensorReading]
    ) -> Tuple[List[FireDetectionResult], FireAlertLevel]:
        """
        모든 센서 감지 및 전체 경보 수준 결정

        Returns:
            (개별 결과 리스트, 전체 최대 경보 수준)
        """
        results = []
        max_level = FireAlertLevel.NORMAL

        for reading in readings:
            result = self.detect(reading)
            results.append(result)

            if result.alert_level.value > max_level.value:
                max_level = result.alert_level

        return results, max_level

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """모든 감지기의 임계값 업데이트"""
        self.thresholds.update(new_thresholds)

        with self._lock:
            for detector in self.detectors.values():
                detector.update_thresholds(new_thresholds)

    def get_all_statistics(self) -> Dict[str, Dict]:
        """모든 센서의 통계"""
        with self._lock:
            return {
                sensor_id: detector.get_statistics()
                for sensor_id, detector in self.detectors.items()
            }

    def reset(self, sensor_id: Optional[str] = None):
        """초기화"""
        with self._lock:
            if sensor_id:
                if sensor_id in self.detectors:
                    self.detectors[sensor_id].reset()
            else:
                for detector in self.detectors.values():
                    detector.reset()
