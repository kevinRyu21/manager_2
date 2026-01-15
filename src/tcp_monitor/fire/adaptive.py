"""
AI 기반 적응형 임계값 자동 조정 시스템
GARAMe Manager v2.0

설치 초기에는 표준 설정값을 사용하고, 운영 데이터가 축적되면
설치 환경에 맞게 임계값을 자동으로 최적화합니다.

참고: Welford's Algorithm, Reservoir Sampling
"""

from typing import Dict, List, Tuple, Optional, Deque
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import random
import json
import sqlite3
import threading
import math
import os

from .models import (
    SensorReading,
    SensorStatistics,
    SensorBaseline,
    EnvironmentProfile,
    EnvironmentType,
    LearningPhase,
    AIAdaptationConfig,
    ThresholdVersion,
    STANDARD_THRESHOLDS,
    FireDetectionResult
)

logger = logging.getLogger(__name__)


class OnlineStatistics:
    """
    온라인 증분 통계 계산기 (Welford's Algorithm)

    메모리 효율적인 평균/분산 계산 (O(1) 공간, O(1) 업데이트)
    """

    def __init__(self, reservoir_size: int = 10000):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0  # 분산 계산용
        self.min_val = float('inf')
        self.max_val = float('-inf')

        # 백분위수용 Reservoir Sampling
        self.reservoir_size = reservoir_size
        self.reservoir: List[float] = []

        # 시간대별 통계 (24시간)
        self.hourly_counts = [0] * 24
        self.hourly_sums = [0.0] * 24
        self.hourly_sq_sums = [0.0] * 24

        # 변화율 통계
        self.last_value: Optional[float] = None
        self.last_time: Optional[datetime] = None
        self.rate_n = 0
        self.rate_mean = 0.0
        self.rate_M2 = 0.0
        self.rate_max = 0.0

    def update(self, value: float, timestamp: Optional[datetime] = None):
        """
        새 값으로 통계 업데이트 (O(1) 복잡도)

        Args:
            value: 측정값
            timestamp: 측정 시간 (변화율 계산용)
        """
        self.n += 1

        # Welford's Algorithm for mean and variance
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.M2 += delta * delta2

        # Min/Max
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

        # Reservoir Sampling for percentiles
        if len(self.reservoir) < self.reservoir_size:
            self.reservoir.append(value)
        else:
            # 확률적 교체
            idx = random.randint(0, self.n - 1)
            if idx < self.reservoir_size:
                self.reservoir[idx] = value

        # 시간대별 통계
        if timestamp:
            hour = timestamp.hour
            self.hourly_counts[hour] += 1
            self.hourly_sums[hour] += value
            self.hourly_sq_sums[hour] += value * value

            # 변화율 계산
            if self.last_value is not None and self.last_time is not None:
                time_diff = (timestamp - self.last_time).total_seconds()
                if time_diff > 0:
                    rate = (value - self.last_value) / time_diff * 60  # 분당 변화율

                    self.rate_n += 1
                    rate_delta = rate - self.rate_mean
                    self.rate_mean += rate_delta / self.rate_n
                    rate_delta2 = rate - self.rate_mean
                    self.rate_M2 += rate_delta * rate_delta2
                    self.rate_max = max(self.rate_max, abs(rate))

            self.last_value = value
            self.last_time = timestamp

    @property
    def variance(self) -> float:
        """분산"""
        return self.M2 / self.n if self.n > 1 else 0.0

    @property
    def std(self) -> float:
        """표준편차"""
        return math.sqrt(self.variance)

    @property
    def rate_variance(self) -> float:
        """변화율 분산"""
        return self.rate_M2 / self.rate_n if self.rate_n > 1 else 0.0

    @property
    def rate_std(self) -> float:
        """변화율 표준편차"""
        return math.sqrt(self.rate_variance)

    def get_percentile(self, p: float) -> float:
        """
        백분위수 계산 (근사값)

        Args:
            p: 백분위 (0~100)
        """
        if not self.reservoir:
            return 0.0
        sorted_reservoir = sorted(self.reservoir)
        idx = int(len(sorted_reservoir) * p / 100)
        return sorted_reservoir[min(idx, len(sorted_reservoir) - 1)]

    def get_hourly_means(self) -> List[float]:
        """시간대별 평균 반환"""
        return [
            self.hourly_sums[h] / self.hourly_counts[h]
            if self.hourly_counts[h] > 0 else 0.0
            for h in range(24)
        ]

    def get_hourly_stds(self) -> List[float]:
        """시간대별 표준편차 반환"""
        result = []
        for h in range(24):
            if self.hourly_counts[h] > 1:
                mean = self.hourly_sums[h] / self.hourly_counts[h]
                variance = (
                    self.hourly_sq_sums[h] / self.hourly_counts[h] -
                    mean * mean
                )
                result.append(math.sqrt(max(0, variance)))
            else:
                result.append(0.0)
        return result

    def to_dict(self) -> Dict:
        """딕셔너리로 직렬화"""
        return {
            'n': self.n,
            'mean': self.mean,
            'M2': self.M2,
            'min_val': self.min_val if self.min_val != float('inf') else None,
            'max_val': self.max_val if self.max_val != float('-inf') else None,
            'hourly_counts': self.hourly_counts,
            'hourly_sums': self.hourly_sums,
            'rate_n': self.rate_n,
            'rate_mean': self.rate_mean,
            'rate_M2': self.rate_M2,
            'rate_max': self.rate_max
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'OnlineStatistics':
        """딕셔너리에서 복원"""
        stats = cls()
        stats.n = data.get('n', 0)
        stats.mean = data.get('mean', 0.0)
        stats.M2 = data.get('M2', 0.0)
        stats.min_val = data.get('min_val') or float('inf')
        stats.max_val = data.get('max_val') or float('-inf')
        stats.hourly_counts = data.get('hourly_counts', [0] * 24)
        stats.hourly_sums = data.get('hourly_sums', [0.0] * 24)
        stats.rate_n = data.get('rate_n', 0)
        stats.rate_mean = data.get('rate_mean', 0.0)
        stats.rate_M2 = data.get('rate_M2', 0.0)
        stats.rate_max = data.get('rate_max', 0.0)
        return stats


class AnomalyFilter:
    """이상치 필터 (학습 데이터 품질 보장)"""

    def __init__(self, z_threshold: float = 3.0):
        self.z_threshold = z_threshold

    def is_anomaly(self, value: float, stats: OnlineStatistics) -> bool:
        """
        Z-score 기반 이상치 판별

        화재 상황 데이터는 학습에서 제외해야 함
        """
        if stats.n < 100 or stats.std == 0:
            return False

        z_score = abs(value - stats.mean) / stats.std
        return z_score > self.z_threshold

    def is_fire_event(
        self,
        fire_probability: float,
        threshold: float = 0.5
    ) -> bool:
        """
        화재 이벤트 판별 (학습 제외 대상)

        화재 확률이 높으면 학습에서 제외
        """
        return fire_probability > threshold


class AdaptiveThresholdCalculator:
    """적응형 임계값 계산기"""

    # 안전 마진 계수 (표준편차 배수)
    SAFETY_MARGINS = {
        'watch': 2.0,      # 2σ → 95.4% 정상 범위
        'caution': 2.5,    # 2.5σ → 98.8% 정상 범위
        'warning': 3.0,    # 3σ → 99.7% 정상 범위
        'danger': 3.5      # 3.5σ → 99.95% 정상 범위
    }

    # 최대 조정 범위 (표준값 대비)
    MAX_ADJUSTMENT_RATIO = 0.30  # ±30%

    def calculate_adaptive_threshold(
        self,
        sensor_type: str,
        stats: OnlineStatistics,
        standard_threshold: float,
        level: str  # watch, caution, warning, danger
    ) -> float:
        """
        적응형 임계값 계산

        Args:
            sensor_type: 센서 유형
            stats: 센서 통계
            standard_threshold: 표준 임계값
            level: 경보 레벨

        Returns:
            조정된 임계값 (안전 범위 내)
        """
        if stats.n < 100:
            # 데이터 부족 시 표준값 사용
            return standard_threshold

        # 1. 기준선 + 안전마진 기반 계산
        margin = self.SAFETY_MARGINS.get(level, 2.5)
        adaptive_value = stats.mean + (margin * stats.std)

        # 2. 백분위수 기반 보정
        if level == 'watch':
            percentile_ref = stats.get_percentile(95)
        elif level == 'caution':
            percentile_ref = stats.get_percentile(99)
        else:
            percentile_ref = stats.max_val * 0.9 if stats.max_val != float('-inf') else adaptive_value

        # 3. 두 방법의 가중 평균
        adaptive_value = 0.6 * adaptive_value + 0.4 * percentile_ref

        # 4. 안전 범위 클램핑 (표준값의 ±30%)
        min_allowed = standard_threshold * (1 - self.MAX_ADJUSTMENT_RATIO)
        max_allowed = standard_threshold * (1 + self.MAX_ADJUSTMENT_RATIO)

        return max(min_allowed, min(max_allowed, adaptive_value))

    def calculate_all_thresholds(
        self,
        sensor_type: str,
        stats: OnlineStatistics,
        standard_config: Dict[str, float]
    ) -> Dict[str, float]:
        """모든 레벨의 임계값 계산"""
        result = {}

        for level in ['watch', 'caution', 'warning', 'danger']:
            key = f"{sensor_type}_{level}"
            if key in standard_config:
                result[key] = self.calculate_adaptive_threshold(
                    sensor_type, stats, standard_config[key], level
                )

        return result


class EnvironmentProfileDetector:
    """환경 프로파일 자동 감지"""

    def __init__(self):
        self.sensor_stats: Dict[str, OnlineStatistics] = {}
        self.detected_type: EnvironmentType = EnvironmentType.AUTO
        self.confidence: float = 0.0

    def update(self, reading: SensorReading):
        """센서 데이터로 환경 프로파일 업데이트"""
        sensor_values = {
            'temperature': reading.temperature,
            'humidity': reading.humidity,
            'co': reading.co,
            'co2': reading.co2,
            'o2': reading.o2,
            'smoke': reading.smoke,
            'ch4': reading.ch4
        }

        for sensor_type, value in sensor_values.items():
            if value is None:
                continue

            if sensor_type not in self.sensor_stats:
                self.sensor_stats[sensor_type] = OnlineStatistics()

            self.sensor_stats[sensor_type].update(value, reading.timestamp)

        # 환경 유형 재판별
        self._detect_environment_type()

    def _detect_environment_type(self):
        """환경 유형 자동 감지"""
        total_samples = sum(
            s.n for s in self.sensor_stats.values()
        )

        if total_samples < 1000:
            # 데이터 부족
            self.confidence = total_samples / 1000 * 0.5
            return

        scores = {env: 0.0 for env in EnvironmentType}

        # CO2 패턴으로 사무실 감지
        if 'co2' in self.sensor_stats:
            co2_stats = self.sensor_stats['co2']
            if 400 < co2_stats.mean < 1200 and co2_stats.std < 300:
                scores[EnvironmentType.OFFICE] += 0.3

        # 온도 변동으로 공장 감지
        if 'temperature' in self.sensor_stats:
            temp_stats = self.sensor_stats['temperature']
            if temp_stats.std > 5:
                scores[EnvironmentType.FACTORY] += 0.2
            if temp_stats.mean > 28:
                scores[EnvironmentType.ELECTRICAL] += 0.2

        # 연기 빈도로 주방 감지
        if 'smoke' in self.sensor_stats:
            smoke_stats = self.sensor_stats['smoke']
            if smoke_stats.max_val > 5 and smoke_stats.get_percentile(90) < 3:
                scores[EnvironmentType.KITCHEN] += 0.3

        # O2 변동으로 지하시설 감지
        if 'o2' in self.sensor_stats:
            o2_stats = self.sensor_stats['o2']
            if o2_stats.std > 0.5:
                scores[EnvironmentType.UNDERGROUND] += 0.3

        # 습도로 창고 감지
        if 'humidity' in self.sensor_stats:
            hum_stats = self.sensor_stats['humidity']
            if hum_stats.std < 10 and 30 < hum_stats.mean < 60:
                scores[EnvironmentType.WAREHOUSE] += 0.2

        # 최고 점수 환경 선택
        max_score = max(scores.values())
        if max_score > 0:
            for env, score in scores.items():
                if score == max_score:
                    self.detected_type = env
                    self.confidence = min(1.0, score + 0.5)
                    break

    def get_profile(self) -> EnvironmentProfile:
        """현재 환경 프로파일 반환"""
        baselines = {}
        normal_ranges = {}
        hourly_coefficients = {}

        for sensor_type, stats in self.sensor_stats.items():
            if stats.n < 100:
                continue

            # 기준선 계산
            baselines[sensor_type] = SensorBaseline(
                normal_mean=stats.mean,
                normal_std=stats.std,
                alert_threshold=stats.mean + 2.5 * stats.std,
                danger_threshold=stats.mean + 3.5 * stats.std
            )

            # 정상 범위
            normal_ranges[sensor_type] = (
                stats.get_percentile(5),
                stats.get_percentile(95)
            )

            # 시간대별 계수
            hourly_means = stats.get_hourly_means()
            if stats.mean > 0:
                hourly_coefficients[sensor_type] = [
                    m / stats.mean if m > 0 else 1.0
                    for m in hourly_means
                ]

        return EnvironmentProfile(
            profile_id="auto",
            profile_name=f"자동 감지: {self.detected_type.value}",
            detected_type=self.detected_type,
            baseline=baselines,
            normal_ranges=normal_ranges,
            hourly_coefficients=hourly_coefficients,
            confidence=self.confidence,
            samples_count=sum(s.n for s in self.sensor_stats.values()),
            last_updated=datetime.now()
        )


class AdaptationValidator:
    """적응 결과 검증기"""

    def validate_adaptation(
        self,
        old_thresholds: Dict[str, float],
        new_thresholds: Dict[str, float],
        stats: Dict[str, OnlineStatistics]
    ) -> Tuple[bool, str]:
        """
        새 임계값이 안전한지 검증

        검증 기준:
        1. 모든 임계값이 유효 범위 내
        2. 표준값 대비 과도한 변화 없음
        3. 위험 상황에서 감지 가능 확인
        """
        # 검증 1: 유효 범위 확인
        for key, value in new_thresholds.items():
            if value <= 0:
                return False, f"{key} 값이 0 이하입니다"

        # 검증 2: 과도한 변화 확인
        for key in new_thresholds:
            if key in old_thresholds:
                old_val = old_thresholds[key]
                new_val = new_thresholds[key]

                if old_val > 0:
                    change_ratio = abs(new_val - old_val) / old_val
                    if change_ratio > 0.5:  # 50% 이상 변화
                        return False, f"{key} 변화가 너무 큼 ({change_ratio:.1%})"

        # 검증 3: 극단값 테스트
        extreme_cases = [
            ('co', 500),      # 명백한 화재
            ('smoke', 80),
            ('temperature', 100),
        ]

        for sensor_type, extreme_value in extreme_cases:
            for level in ['watch', 'caution', 'warning', 'danger']:
                key = f"{sensor_type}_{level}"
                if key in new_thresholds:
                    if new_thresholds[key] > extreme_value:
                        return False, f"{key} 임계값이 극단 케이스보다 높음"

        return True, "검증 통과"


class ThresholdManager:
    """임계값 관리자 (버전 관리 및 롤백)"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.current_thresholds = STANDARD_THRESHOLDS.copy()
        self.history: List[ThresholdVersion] = []
        self.max_history = 10
        self._lock = threading.Lock()

        self._init_db()
        self._load_from_db()

    def _init_db(self):
        """데이터베이스 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threshold_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    thresholds_json TEXT NOT NULL,
                    reason TEXT,
                    validation_result TEXT,
                    applied_at TIMESTAMP,
                    rolled_back_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    stats_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(sensor_id, sensor_type)
                )
            """)
            conn.commit()

    def _load_from_db(self):
        """데이터베이스에서 이력 로드"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT version, thresholds_json, reason, validation_result,
                           applied_at, rolled_back_at, created_at
                    FROM threshold_history
                    ORDER BY version DESC
                    LIMIT ?
                """, (self.max_history,))

                for row in cursor.fetchall():
                    version = ThresholdVersion(
                        version=row[0],
                        thresholds=json.loads(row[1]),
                        reason=row[2],
                        validation_result=row[3],
                        applied_at=datetime.fromisoformat(row[4]) if row[4] else None,
                        rolled_back_at=datetime.fromisoformat(row[5]) if row[5] else None,
                        timestamp=datetime.fromisoformat(row[6]) if row[6] else datetime.now()
                    )
                    self.history.append(version)

                # 최신 임계값 적용
                if self.history:
                    self.current_thresholds = self.history[0].thresholds.copy()

        except Exception as e:
            logger.error(f"임계값 이력 로드 실패: {e}")

    def save_threshold_version(
        self,
        thresholds: Dict[str, float],
        reason: str,
        validation_result: str = "통과"
    ):
        """임계값 버전 저장"""
        with self._lock:
            version = len(self.history) + 1

            version_obj = ThresholdVersion(
                version=version,
                timestamp=datetime.now(),
                thresholds=thresholds.copy(),
                reason=reason,
                validation_result=validation_result,
                applied_at=datetime.now()
            )

            self.history.insert(0, version_obj)
            if len(self.history) > self.max_history:
                self.history.pop()

            self.current_thresholds = thresholds.copy()

            # DB 저장
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO threshold_history
                        (version, thresholds_json, reason, validation_result, applied_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        version,
                        json.dumps(thresholds),
                        reason,
                        validation_result,
                        datetime.now().isoformat()
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"임계값 저장 실패: {e}")

    def get_current(self) -> Dict[str, float]:
        """현재 임계값 반환"""
        with self._lock:
            return self.current_thresholds.copy()

    def rollback(self, steps: int = 1) -> Dict[str, float]:
        """이전 임계값으로 롤백"""
        with self._lock:
            if steps >= len(self.history):
                return STANDARD_THRESHOLDS.copy()

            target = self.history[steps]
            self.current_thresholds = target.thresholds.copy()

            # 롤백 기록
            if self.history:
                self.history[0].rolled_back_at = datetime.now()

            return self.current_thresholds.copy()

    def get_change_log(self) -> List[Dict]:
        """임계값 변경 이력 조회"""
        return [
            {
                'version': v.version,
                'timestamp': v.timestamp.isoformat(),
                'reason': v.reason,
                'validation_result': v.validation_result,
                'applied_at': v.applied_at.isoformat() if v.applied_at else None,
                'rolled_back_at': v.rolled_back_at.isoformat() if v.rolled_back_at else None
            }
            for v in self.history
        ]


class AdaptiveFireSystem:
    """
    AI 적응형 화재 감시 시스템

    센서 데이터를 수집하고 분석하여 설치 환경에 맞는
    최적의 임계값을 자동으로 조정합니다.
    """

    def __init__(
        self,
        config: Optional[AIAdaptationConfig] = None,
        db_path: str = "data/fire_adaptive.db"
    ):
        self.config = config or AIAdaptationConfig()
        self.db_path = db_path

        # 구성 요소 초기화
        self.stats_collector: Dict[str, Dict[str, OnlineStatistics]] = {}
        self.profile_detector = EnvironmentProfileDetector()
        self.threshold_calculator = AdaptiveThresholdCalculator()
        self.threshold_manager = ThresholdManager(db_path)
        self.validator = AdaptationValidator()
        self.anomaly_filter = AnomalyFilter()

        # 상태
        self.learning_phase = LearningPhase.COLD_START
        self.first_data_time: Optional[datetime] = None
        self.last_update_time: Optional[datetime] = None
        self.total_samples = 0

        self._lock = threading.Lock()

    def _get_learning_phase(self) -> LearningPhase:
        """현재 학습 단계 결정"""
        if self.first_data_time is None:
            return LearningPhase.COLD_START

        elapsed = datetime.now() - self.first_data_time
        days = elapsed.days

        if days < 1:
            return LearningPhase.COLD_START
        elif days < self.config.min_learning_days:
            return LearningPhase.WARMUP
        elif days < self.config.full_learning_days:
            return LearningPhase.LEARNING
        else:
            return LearningPhase.ADAPTIVE

    def _get_sensor_stats(
        self,
        sensor_id: str,
        sensor_type: str
    ) -> OnlineStatistics:
        """센서별 통계 객체 가져오기"""
        with self._lock:
            if sensor_id not in self.stats_collector:
                self.stats_collector[sensor_id] = {}

            if sensor_type not in self.stats_collector[sensor_id]:
                self.stats_collector[sensor_id][sensor_type] = OnlineStatistics()

            return self.stats_collector[sensor_id][sensor_type]

    def process_reading(
        self,
        reading: SensorReading,
        fire_probability: float = 0.0
    ):
        """
        센서 데이터 처리 및 학습

        Args:
            reading: 센서 측정값
            fire_probability: 현재 화재 확률 (화재 시 학습 제외)
        """
        if not self.config.enabled:
            return

        # 첫 데이터 시간 기록
        if self.first_data_time is None:
            self.first_data_time = reading.timestamp

        # 학습 단계 업데이트
        self.learning_phase = self._get_learning_phase()

        # 화재 이벤트는 학습에서 제외
        if self.anomaly_filter.is_fire_event(fire_probability):
            return

        # 학습 제외 시간대 확인
        if reading.timestamp.hour in self.config.exclude_hours:
            return

        # 센서별 통계 업데이트
        sensor_values = {
            'temperature': reading.temperature,
            'humidity': reading.humidity,
            'co': reading.co,
            'co2': reading.co2,
            'o2': reading.o2,
            'smoke': reading.smoke,
            'ch4': reading.ch4,
            'h2s': reading.h2s
        }

        for sensor_type, value in sensor_values.items():
            if value is None:
                continue

            stats = self._get_sensor_stats(reading.sensor_id, sensor_type)

            # 이상치 필터링
            if not self.anomaly_filter.is_anomaly(value, stats):
                stats.update(value, reading.timestamp)

        # 환경 프로파일 업데이트
        self.profile_detector.update(reading)

        self.total_samples += 1

    def update_thresholds(self) -> Tuple[bool, str]:
        """
        임계값 업데이트 (주기적 호출)

        Returns:
            (성공 여부, 메시지)
        """
        if not self.config.enabled:
            return False, "AI 적응 기능 비활성화됨"

        # 학습 단계 확인
        if self.learning_phase in [LearningPhase.COLD_START, LearningPhase.WARMUP]:
            return False, f"학습 중 ({self.learning_phase.name})"

        # 최소 신뢰도 확인
        profile = self.profile_detector.get_profile()
        if profile.confidence < self.config.min_confidence:
            return False, f"신뢰도 부족 ({profile.confidence:.1%})"

        # 새 임계값 계산
        new_thresholds = {}
        standard = STANDARD_THRESHOLDS.copy()

        for sensor_id, sensor_stats in self.stats_collector.items():
            for sensor_type, stats in sensor_stats.items():
                if stats.n < 1000:
                    continue

                calculated = self.threshold_calculator.calculate_all_thresholds(
                    sensor_type, stats, standard
                )
                new_thresholds.update(calculated)

        if not new_thresholds:
            return False, "계산된 임계값 없음"

        # 검증
        if self.config.require_validation:
            valid, reason = self.validator.validate_adaptation(
                self.threshold_manager.get_current(),
                new_thresholds,
                {
                    k: v
                    for sensor_stats in self.stats_collector.values()
                    for k, v in sensor_stats.items()
                }
            )
            if not valid:
                logger.warning(f"임계값 적응 실패: {reason}")
                return False, f"검증 실패: {reason}"

        # 적용
        self.threshold_manager.save_threshold_version(
            new_thresholds,
            f"자동 적응 (환경: {profile.detected_type.value}, 신뢰도: {profile.confidence:.1%})"
        )

        self.last_update_time = datetime.now()
        logger.info(f"임계값 업데이트 완료: {len(new_thresholds)}개 항목")

        return True, f"{len(new_thresholds)}개 임계값 업데이트됨"

    def get_current_thresholds(self) -> Dict[str, float]:
        """현재 적용 중인 임계값 반환"""
        if not self.config.enabled:
            return STANDARD_THRESHOLDS.copy()

        return self.threshold_manager.get_current()

    def reset_to_standard(self):
        """표준값으로 초기화"""
        self.threshold_manager.save_threshold_version(
            STANDARD_THRESHOLDS.copy(),
            "사용자 요청 - 표준값 복원"
        )

        with self._lock:
            self.stats_collector.clear()

        self.profile_detector = EnvironmentProfileDetector()
        self.first_data_time = None
        self.total_samples = 0
        self.learning_phase = LearningPhase.COLD_START

        logger.info("표준값으로 초기화됨")

    def get_status(self) -> Dict:
        """현재 상태 반환"""
        profile = self.profile_detector.get_profile()

        # 학습 진행률 계산
        if self.first_data_time:
            elapsed_days = (datetime.now() - self.first_data_time).days
            progress = min(1.0, elapsed_days / self.config.full_learning_days)
        else:
            progress = 0.0

        return {
            'enabled': self.config.enabled,
            'learning_phase': self.learning_phase.name,
            'progress': progress,
            'progress_days': elapsed_days if self.first_data_time else 0,
            'target_days': self.config.full_learning_days,
            'total_samples': self.total_samples,
            'environment_type': profile.detected_type.value,
            'environment_confidence': profile.confidence,
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'current_thresholds_count': len(self.threshold_manager.get_current()),
            'threshold_history_count': len(self.threshold_manager.history)
        }

    def get_threshold_comparison(self) -> List[Dict]:
        """표준값과 적응값 비교"""
        current = self.threshold_manager.get_current()
        standard = STANDARD_THRESHOLDS

        comparison = []
        for key in standard:
            if key in current:
                std_val = standard[key]
                cur_val = current[key]
                change_pct = ((cur_val - std_val) / std_val * 100) if std_val else 0

                comparison.append({
                    'key': key,
                    'standard': std_val,
                    'current': cur_val,
                    'change_percent': round(change_pct, 1),
                    'status': 'active' if cur_val != std_val else 'standard'
                })

        return comparison
