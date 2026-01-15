"""
화재 감시 시스템 데이터 모델
GARAMe Manager v2.0

센서 데이터, 통계, 환경 프로파일 등의 데이터 구조 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from enum import Enum, auto


class FireAlertLevel(Enum):
    """화재 경보 단계"""
    NORMAL = 1      # 정상 (녹색)
    WATCH = 2       # 관심 (노랑)
    CAUTION = 3     # 주의 (주황)
    WARNING = 4     # 경계 (빨강)
    DANGER = 5      # 위험 (진홍)

    @property
    def korean_name(self) -> str:
        names = {
            FireAlertLevel.NORMAL: "정상",
            FireAlertLevel.WATCH: "관심",
            FireAlertLevel.CAUTION: "주의",
            FireAlertLevel.WARNING: "경계",
            FireAlertLevel.DANGER: "위험"
        }
        return names[self]

    @property
    def color(self) -> str:
        colors = {
            FireAlertLevel.NORMAL: "#00FF00",   # 녹색
            FireAlertLevel.WATCH: "#FFFF00",    # 노랑
            FireAlertLevel.CAUTION: "#FFA500",  # 주황
            FireAlertLevel.WARNING: "#FF0000",  # 빨강
            FireAlertLevel.DANGER: "#DC143C"    # 진홍
        }
        return colors[self]


class LearningPhase(Enum):
    """AI 학습 단계"""
    COLD_START = auto()   # 0~24시간
    WARMUP = auto()       # 1~7일
    LEARNING = auto()     # 7~30일
    ADAPTIVE = auto()     # 30일+


class EnvironmentType(Enum):
    """설치 환경 유형"""
    AUTO = "auto"
    OFFICE = "office"
    FACTORY = "factory"
    KITCHEN = "kitchen"
    UNDERGROUND = "underground"
    WAREHOUSE = "warehouse"
    ELECTRICAL = "electrical"


@dataclass
class SensorReading:
    """센서 측정값"""
    sensor_id: str
    timestamp: datetime

    # 센서 값들
    temperature: Optional[float] = None      # 온도 (°C)
    humidity: Optional[float] = None         # 습도 (%RH)
    co: Optional[float] = None               # 일산화탄소 (ppm)
    co2: Optional[float] = None              # 이산화탄소 (ppm)
    o2: Optional[float] = None               # 산소 (%)
    h2s: Optional[float] = None              # 황화수소 (ppm)
    ch4: Optional[float] = None              # 메탄/가연성가스 (%LEL)
    smoke: Optional[float] = None            # 연기 (%)
    water: Optional[int] = None              # 침수 (0/1)
    ext_input: Optional[int] = None          # 외부접점 (0/1)

    # 계산값
    temp_rate: Optional[float] = None        # 온도 상승률 (°C/min)

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'sensor_id': self.sensor_id,
            'timestamp': self.timestamp.isoformat(),
            'temperature': self.temperature,
            'humidity': self.humidity,
            'co': self.co,
            'co2': self.co2,
            'o2': self.o2,
            'h2s': self.h2s,
            'ch4': self.ch4,
            'smoke': self.smoke,
            'water': self.water,
            'ext_input': self.ext_input,
            'temp_rate': self.temp_rate
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SensorReading':
        """딕셔너리에서 생성"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            sensor_id=data.get('sensor_id', 'unknown'),
            timestamp=timestamp,
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            co=data.get('co'),
            co2=data.get('co2'),
            o2=data.get('o2'),
            h2s=data.get('h2s'),
            ch4=data.get('ch4'),
            smoke=data.get('smoke'),
            water=data.get('water'),
            ext_input=data.get('ext_input'),
            temp_rate=data.get('temp_rate')
        )


@dataclass
class FireDetectionResult:
    """화재 감지 결과"""
    sensor_id: str
    timestamp: datetime

    # 화재 확률 및 단계
    fire_probability: float              # 0.0 ~ 1.0
    alert_level: FireAlertLevel

    # Dempster-Shafer 결과
    belief_fire: float                   # 화재 신뢰도
    belief_normal: float                 # 정상 신뢰도
    uncertainty: float                   # 불확실성

    # 센서별 기여도
    sensor_contributions: Dict[str, float] = field(default_factory=dict)

    # 트리거된 규칙
    triggered_rules: List[str] = field(default_factory=list)

    # 메시지
    message: str = ""
    recommended_action: str = ""

    def to_dict(self) -> Dict:
        return {
            'sensor_id': self.sensor_id,
            'timestamp': self.timestamp.isoformat(),
            'fire_probability': self.fire_probability,
            'alert_level': self.alert_level.value,
            'alert_level_name': self.alert_level.korean_name,
            'alert_color': self.alert_level.color,
            'belief_fire': self.belief_fire,
            'belief_normal': self.belief_normal,
            'uncertainty': self.uncertainty,
            'sensor_contributions': self.sensor_contributions,
            'triggered_rules': self.triggered_rules,
            'message': self.message,
            'recommended_action': self.recommended_action
        }


@dataclass
class SensorStatistics:
    """센서별 통계 데이터 (AI 학습용)"""
    sensor_id: str
    sensor_type: str  # temperature, co, co2, o2, h2s, ch4, smoke, humidity

    # 기본 통계
    count: int = 0
    mean: float = 0.0
    std: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')

    # 백분위수
    percentile_1: float = 0.0
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_50: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    percentile_99: float = 0.0

    # 시계열 특성
    daily_pattern: List[float] = field(default_factory=lambda: [0.0] * 24)
    weekly_pattern: List[float] = field(default_factory=lambda: [0.0] * 7)
    trend: float = 0.0
    seasonality: float = 0.0

    # 변화율 통계
    rate_mean: float = 0.0
    rate_std: float = 0.0
    rate_max: float = 0.0

    # 메타데이터
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    learning_phase: LearningPhase = LearningPhase.COLD_START


@dataclass
class SensorBaseline:
    """센서별 기준선"""
    normal_mean: float = 0.0
    normal_std: float = 0.0
    alert_threshold: float = 0.0
    danger_threshold: float = 0.0


@dataclass
class EnvironmentProfile:
    """환경 프로파일"""
    profile_id: str
    profile_name: str = ""
    detected_type: EnvironmentType = EnvironmentType.AUTO

    # 환경 기준선 (Baseline)
    baseline: Dict[str, SensorBaseline] = field(default_factory=dict)

    # 정상 범위 (학습된 값)
    normal_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # 시간대별 보정 계수
    hourly_coefficients: Dict[str, List[float]] = field(
        default_factory=lambda: {k: [1.0] * 24 for k in ['co', 'co2', 'temperature']}
    )

    # 요일별 보정 계수
    daily_coefficients: Dict[str, List[float]] = field(
        default_factory=lambda: {k: [1.0] * 7 for k in ['co', 'co2', 'temperature']}
    )

    # 신뢰도
    confidence: float = 0.0
    samples_count: int = 0
    last_updated: Optional[datetime] = None


@dataclass
class AIAdaptationConfig:
    """AI 적응 설정"""
    # 기능 활성화
    enabled: bool = True

    # 학습 설정
    min_learning_days: int = 7
    full_learning_days: int = 30
    update_interval_hours: int = 6

    # 안전 설정
    max_adjustment_percent: float = 30.0
    min_confidence: float = 0.7
    require_validation: bool = True

    # 롤백 설정
    auto_rollback_on_alarm_spike: bool = True
    alarm_spike_threshold: float = 2.0

    # 환경 설정
    environment_type: str = "auto"
    exclude_hours: List[int] = field(default_factory=list)


@dataclass
class ThresholdVersion:
    """임계값 버전 (롤백용)"""
    version: int
    timestamp: datetime
    thresholds: Dict[str, float]
    reason: str
    validation_result: Optional[str] = None
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None


# 센서 가중치 (화재 감지 기여도)
SENSOR_WEIGHTS = {
    'smoke': 0.25,      # 연기 - 가장 빠른 반응
    'co': 0.20,         # CO - 불완전 연소 지표
    'temp_rate': 0.18,  # 온도 상승률 - 화재 성장 속도
    'o2': 0.12,         # O2 - 연소 진행도
    'co2': 0.10,        # CO2 - 연소 확인
    'temperature': 0.08, # 온도 - 보조 지표
    'ch4': 0.05,        # CH4 - 폭발 위험
    'humidity': 0.02    # 습도 - 간접 지표
}


# 화재 단계별 확률 임계값
FIRE_PROBABILITY_THRESHOLDS = {
    FireAlertLevel.NORMAL: 0.0,
    FireAlertLevel.WATCH: 0.2,
    FireAlertLevel.CAUTION: 0.4,
    FireAlertLevel.WARNING: 0.6,
    FireAlertLevel.DANGER: 0.8
}


# 표준 임계값 (국가 기준 기반)
STANDARD_THRESHOLDS = {
    # 온도 (°C)
    'temperature_watch': 35.0,
    'temperature_caution': 45.0,
    'temperature_warning': 55.0,
    'temperature_danger': 65.0,

    # 온도 상승률 (°C/min)
    'temp_rate_watch': 2.0,
    'temp_rate_caution': 5.0,
    'temp_rate_warning': 8.0,
    'temp_rate_danger': 12.0,

    # CO (ppm)
    'co_watch': 30.0,
    'co_caution': 50.0,
    'co_warning': 100.0,
    'co_danger': 200.0,

    # CO2 (ppm)
    'co2_watch': 1500.0,
    'co2_caution': 2500.0,
    'co2_warning': 5000.0,
    'co2_danger': 10000.0,

    # O2 (%) - 역방향 (낮을수록 위험)
    'o2_watch': 19.5,
    'o2_caution': 18.5,
    'o2_warning': 17.5,
    'o2_danger': 16.0,

    # 연기 (%)
    'smoke_watch': 10.0,
    'smoke_caution': 25.0,
    'smoke_warning': 50.0,
    'smoke_danger': 75.0,

    # CH4/가연성가스 (%LEL)
    'ch4_watch': 10.0,
    'ch4_caution': 20.0,
    'ch4_warning': 35.0,
    'ch4_danger': 50.0,

    # H2S (ppm)
    'h2s_watch': 10.0,
    'h2s_caution': 20.0,
    'h2s_warning': 50.0,
    'h2s_danger': 100.0,

    # 습도 (%RH) - 낮을수록 위험 (연소 시 감소)
    'humidity_watch': 35.0,
    'humidity_caution': 25.0,
    'humidity_warning': 20.0,
    'humidity_danger': 15.0
}
