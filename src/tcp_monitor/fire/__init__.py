"""
화재 감시 5단계 경보 시스템
GARAMe Manager v2.0

다중 센서 융합 기반 지능형 화재 감지 시스템
- Dempster-Shafer 증거 이론
- 퍼지 멤버십 함수
- AI 기반 적응형 임계값

주요 기능:
1. 5단계 화재 경보 (정상/관심/주의/경계/위험)
2. 다중 센서 데이터 융합
3. 센서 조합 규칙 기반 화재 확률 부스트
4. AI 기반 설치 환경 적응
5. 오경보 방지 필터

사용 예시:
```python
from tcp_monitor.fire import (
    FireDetector,
    MultiSensorFireDetector,
    AdaptiveFireSystem,
    SensorReading,
    FireAlertLevel
)

# 화재 감지기 생성
detector = FireDetector()

# 센서 데이터로 화재 감지
reading = SensorReading(
    sensor_id="sensor01",
    timestamp=datetime.now(),
    temperature=25.0,
    humidity=50.0,
    co=5.0,
    co2=800.0,
    o2=20.9,
    smoke=0.0
)

result = detector.detect(reading)
print(f"화재 확률: {result.fire_probability:.1%}")
print(f"경보 단계: {result.alert_level.korean_name}")

# AI 적응형 시스템
adaptive = AdaptiveFireSystem()
adaptive.process_reading(reading, result.fire_probability)
```
"""

from .models import (
    # Enums
    FireAlertLevel,
    LearningPhase,
    EnvironmentType,

    # Data Classes
    SensorReading,
    FireDetectionResult,
    SensorStatistics,
    SensorBaseline,
    EnvironmentProfile,
    AIAdaptationConfig,
    ThresholdVersion,

    # Constants
    SENSOR_WEIGHTS,
    FIRE_PROBABILITY_THRESHOLDS,
    STANDARD_THRESHOLDS
)

from .dempster_shafer import (
    MassFunction,
    DempsterShaferCombiner,
    ImprovedDempsterShafer
)

from .fuzzy import (
    FuzzyMembershipFunctions,
    FuzzyMembershipConfig
)

from .detector import (
    FireDetector,
    MultiSensorFireDetector,
    SensorHistory
)

from .adaptive import (
    OnlineStatistics,
    AnomalyFilter,
    AdaptiveThresholdCalculator,
    EnvironmentProfileDetector,
    AdaptationValidator,
    ThresholdManager,
    AdaptiveFireSystem
)

from .fire_service import (
    FireDetectionService,
    FireServiceConfig,
    get_fire_service,
    reset_fire_service
)

__all__ = [
    # Enums
    'FireAlertLevel',
    'LearningPhase',
    'EnvironmentType',

    # Data Classes
    'SensorReading',
    'FireDetectionResult',
    'SensorStatistics',
    'SensorBaseline',
    'EnvironmentProfile',
    'AIAdaptationConfig',
    'ThresholdVersion',

    # Constants
    'SENSOR_WEIGHTS',
    'FIRE_PROBABILITY_THRESHOLDS',
    'STANDARD_THRESHOLDS',

    # Dempster-Shafer
    'MassFunction',
    'DempsterShaferCombiner',
    'ImprovedDempsterShafer',

    # Fuzzy
    'FuzzyMembershipFunctions',
    'FuzzyMembershipConfig',

    # Detector
    'FireDetector',
    'MultiSensorFireDetector',
    'SensorHistory',

    # Adaptive
    'OnlineStatistics',
    'AnomalyFilter',
    'AdaptiveThresholdCalculator',
    'EnvironmentProfileDetector',
    'AdaptationValidator',
    'ThresholdManager',
    'AdaptiveFireSystem',

    # Service
    'FireDetectionService',
    'FireServiceConfig',
    'get_fire_service',
    'reset_fire_service',
]

__version__ = '2.0.0'
