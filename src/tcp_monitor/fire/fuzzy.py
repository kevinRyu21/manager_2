"""
퍼지 멤버십 함수
GARAMe Manager v2.0

센서 값을 화재 확률(BPA)로 변환하는 퍼지 멤버십 함수들을 정의합니다.
각 센서의 특성에 맞는 비선형 변환을 제공합니다.
"""

from typing import Dict, Optional, Callable
from dataclasses import dataclass
import math

from .dempster_shafer import MassFunction
from .models import STANDARD_THRESHOLDS


@dataclass
class FuzzyMembershipConfig:
    """퍼지 멤버십 함수 설정"""
    # 임계값 (커스터마이징 가능)
    thresholds: Dict[str, float]

    # 센서 활성화 여부
    sensor_enabled: Dict[str, bool]

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or STANDARD_THRESHOLDS.copy()
        self.sensor_enabled = {
            'temperature': True,
            'temp_rate': True,
            'humidity': True,
            'co': True,
            'co2': True,
            'o2': True,
            'smoke': True,
            'ch4': True,
            'h2s': True
        }


class FuzzyMembershipFunctions:
    """
    센서별 퍼지 멤버십 함수

    각 센서 값을 화재/정상/불확실성에 대한 Basic Probability Assignment (BPA)로 변환합니다.
    S자형(시그모이드) 및 삼각형 멤버십 함수를 사용합니다.
    """

    def __init__(self, config: Optional[FuzzyMembershipConfig] = None):
        self.config = config or FuzzyMembershipConfig()
        self.thresholds = self.config.thresholds

    def _sigmoid(self, x: float, midpoint: float, steepness: float = 0.5) -> float:
        """
        시그모이드 함수

        Args:
            x: 입력값
            midpoint: 0.5가 되는 지점
            steepness: 기울기 (클수록 급격한 변화)

        Returns:
            0~1 사이의 값
        """
        try:
            return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
        except OverflowError:
            return 0.0 if x < midpoint else 1.0

    def _inverse_sigmoid(self, x: float, midpoint: float, steepness: float = 0.5) -> float:
        """역방향 시그모이드 (낮을수록 높은 값 반환)"""
        return 1.0 - self._sigmoid(x, midpoint, steepness)

    def _linear_membership(
        self,
        value: float,
        low: float,
        high: float
    ) -> float:
        """
        선형 멤버십 함수

        Args:
            value: 입력값
            low: 0이 되는 하한
            high: 1이 되는 상한

        Returns:
            0~1 사이의 값
        """
        if value <= low:
            return 0.0
        elif value >= high:
            return 1.0
        else:
            return (value - low) / (high - low)

    def smoke_membership(self, value: float) -> MassFunction:
        """
        연기 센서 BPA 계산

        연기는 화재의 가장 빠른 지표입니다.
        0~10%: 정상, 10~50%: 의심, 50%+: 화재

        Args:
            value: 연기 농도 (%)

        Returns:
            Mass Function (fire, normal, uncertain)
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('smoke_watch', 10.0)
        caution = self.thresholds.get('smoke_caution', 25.0)
        warning = self.thresholds.get('smoke_warning', 50.0)
        danger = self.thresholds.get('smoke_danger', 75.0)

        if value <= 0:
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            # 약간의 연기 - 대부분 정상
            fire = value / watch * 0.1
            return MassFunction(fire=fire, normal=0.8 - fire, uncertain=0.2)
        elif value <= caution:
            # 관심 구간
            ratio = (value - watch) / (caution - watch)
            fire = 0.1 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value <= warning:
            # 주의 구간
            ratio = (value - caution) / (warning - caution)
            fire = 0.3 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value <= danger:
            # 경계 구간
            ratio = (value - warning) / (danger - warning)
            fire = 0.6 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 구간
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def co_membership(self, value: float) -> MassFunction:
        """
        CO (일산화탄소) 센서 BPA 계산

        CO는 불완전 연소의 핵심 지표입니다.
        정상 실내: <9ppm, 화재 초기: 50~100ppm, 화재 진행: >200ppm

        Args:
            value: CO 농도 (ppm)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('co_watch', 30.0)
        caution = self.thresholds.get('co_caution', 50.0)
        warning = self.thresholds.get('co_warning', 100.0)
        danger = self.thresholds.get('co_danger', 200.0)

        if value <= 9:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            # 약간 상승
            ratio = (value - 9) / (watch - 9)
            fire = ratio * 0.15
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif value <= caution:
            # 관심 구간
            ratio = (value - watch) / (caution - watch)
            fire = 0.15 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value <= warning:
            # 주의 구간
            ratio = (value - caution) / (warning - caution)
            fire = 0.4 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value <= danger:
            # 경계 구간
            ratio = (value - warning) / (danger - warning)
            fire = 0.7 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 구간
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def temperature_membership(self, value: float) -> MassFunction:
        """
        온도 센서 BPA 계산

        온도는 화재의 직접적 지표이지만 반응이 느립니다.
        정상: 18~28°C, 화재 초기: 35~50°C, 화재 진행: >60°C

        Args:
            value: 온도 (°C)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('temperature_watch', 35.0)
        caution = self.thresholds.get('temperature_caution', 45.0)
        warning = self.thresholds.get('temperature_warning', 55.0)
        danger = self.thresholds.get('temperature_danger', 65.0)

        if value <= 28:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            # 약간 높음 (더운 날씨일 수 있음)
            ratio = (value - 28) / (watch - 28)
            fire = ratio * 0.1
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif value <= caution:
            # 관심 구간
            ratio = (value - watch) / (caution - watch)
            fire = 0.1 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value <= warning:
            # 주의 구간
            ratio = (value - caution) / (warning - caution)
            fire = 0.3 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value <= danger:
            # 경계 구간
            ratio = (value - warning) / (danger - warning)
            fire = 0.6 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 구간
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def temp_rate_membership(self, rate: float) -> MassFunction:
        """
        온도 상승률 BPA 계산 (°C/min)

        온도 상승률은 화재 성장 속도를 직접 반영하는 핵심 지표입니다.
        정상: <1°C/min, 의심: 2~5°C/min, 화재: >10°C/min

        Args:
            rate: 온도 상승률 (°C/min)

        Returns:
            Mass Function
        """
        if rate is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('temp_rate_watch', 2.0)
        caution = self.thresholds.get('temp_rate_caution', 5.0)
        warning = self.thresholds.get('temp_rate_warning', 8.0)
        danger = self.thresholds.get('temp_rate_danger', 12.0)

        if rate <= 1:
            # 정상 변화율
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif rate <= watch:
            # 약간 빠른 상승
            ratio = (rate - 1) / (watch - 1)
            fire = ratio * 0.15
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif rate <= caution:
            # 관심 구간 - 빠른 상승
            ratio = (rate - watch) / (caution - watch)
            fire = 0.15 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.4, uncertain=0.6 - fire)
        elif rate <= warning:
            # 주의 구간 - 매우 빠른 상승
            ratio = (rate - caution) / (warning - caution)
            fire = 0.4 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.2, uncertain=0.8 - fire)
        elif rate <= danger:
            # 경계 구간
            ratio = (rate - warning) / (danger - warning)
            fire = 0.7 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 - 급격한 온도 상승
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def o2_membership(self, value: float) -> MassFunction:
        """
        O2 (산소) 센서 BPA 계산

        산소는 연소 시 소비되므로 감소합니다.
        정상: 20.9%, 화재 초기: 19~19.5%, 화재 진행: <18%

        Args:
            value: 산소 농도 (%)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('o2_watch', 19.5)
        caution = self.thresholds.get('o2_caution', 18.5)
        warning = self.thresholds.get('o2_warning', 17.5)
        danger = self.thresholds.get('o2_danger', 16.0)

        # O2는 역방향 (낮을수록 위험)
        if value >= 20.5:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value >= watch:
            # 약간 낮음
            ratio = (20.5 - value) / (20.5 - watch)
            fire = ratio * 0.1
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif value >= caution:
            # 관심 구간
            ratio = (watch - value) / (watch - caution)
            fire = 0.1 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value >= warning:
            # 주의 구간
            ratio = (caution - value) / (caution - warning)
            fire = 0.3 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value >= danger:
            # 경계 구간
            ratio = (warning - value) / (warning - danger)
            fire = 0.6 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 구간 - 심각한 산소 부족
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def co2_membership(self, value: float) -> MassFunction:
        """
        CO2 (이산화탄소) 센서 BPA 계산

        CO2는 연소의 생성물이지만 사람의 호흡으로도 증가합니다.
        정상 실내: 400~1000ppm, 밀집 공간: 1000~2000ppm
        화재: 5000~10000ppm+

        Args:
            value: CO2 농도 (ppm)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('co2_watch', 1500.0)
        caution = self.thresholds.get('co2_caution', 2500.0)
        warning = self.thresholds.get('co2_warning', 5000.0)
        danger = self.thresholds.get('co2_danger', 10000.0)

        if value <= 1000:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            # 약간 높음 (환기 부족 가능)
            ratio = (value - 1000) / (watch - 1000)
            fire = ratio * 0.05
            return MassFunction(fire=fire, normal=0.75, uncertain=0.25 - fire)
        elif value <= caution:
            # 관심 구간
            ratio = (value - watch) / (caution - watch)
            fire = 0.05 + ratio * 0.15
            return MassFunction(fire=fire, normal=0.55, uncertain=0.45 - fire)
        elif value <= warning:
            # 주의 구간
            ratio = (value - caution) / (warning - caution)
            fire = 0.2 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.35, uncertain=0.65 - fire)
        elif value <= danger:
            # 경계 구간
            ratio = (value - warning) / (danger - warning)
            fire = 0.5 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.15, uncertain=0.85 - fire)
        else:
            # 위험 구간
            return MassFunction(fire=0.9, normal=0.0, uncertain=0.1)

    def ch4_membership(self, value: float) -> MassFunction:
        """
        CH4/가연성가스 센서 BPA 계산 (%LEL)

        메탄 및 가연성 가스는 폭발 위험의 지표입니다.
        정상: <10%LEL, 관심: 10~20%LEL, 위험: >50%LEL

        Args:
            value: 가연성 가스 농도 (%LEL)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('ch4_watch', 10.0)
        caution = self.thresholds.get('ch4_caution', 20.0)
        warning = self.thresholds.get('ch4_warning', 35.0)
        danger = self.thresholds.get('ch4_danger', 50.0)

        if value <= 5:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            # 약간 검출
            ratio = (value - 5) / (watch - 5)
            fire = ratio * 0.1
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif value <= caution:
            # 관심 구간
            ratio = (value - watch) / (caution - watch)
            fire = 0.1 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value <= warning:
            # 주의 구간
            ratio = (value - caution) / (warning - caution)
            fire = 0.3 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value <= danger:
            # 경계 구간
            ratio = (value - warning) / (danger - warning)
            fire = 0.6 + ratio * 0.25
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            # 위험 구간 - 폭발 위험
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def h2s_membership(self, value: float) -> MassFunction:
        """
        H2S (황화수소) 센서 BPA 계산

        H2S는 유독 가스로, 화재보다는 가스 누출/위험 상황 지표입니다.
        정상: <5ppm, 관심: 5~10ppm, 위험: >50ppm

        Args:
            value: H2S 농도 (ppm)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('h2s_watch', 10.0)
        caution = self.thresholds.get('h2s_caution', 20.0)
        warning = self.thresholds.get('h2s_warning', 50.0)
        danger = self.thresholds.get('h2s_danger', 100.0)

        if value <= 5:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value <= watch:
            ratio = (value - 5) / (watch - 5)
            fire = ratio * 0.1
            return MassFunction(fire=fire, normal=0.7, uncertain=0.3 - fire)
        elif value <= caution:
            ratio = (value - watch) / (caution - watch)
            fire = 0.1 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value <= warning:
            ratio = (value - caution) / (warning - caution)
            fire = 0.3 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.3, uncertain=0.7 - fire)
        elif value <= danger:
            ratio = (value - warning) / (danger - warning)
            fire = 0.6 + ratio * 0.3
            return MassFunction(fire=fire, normal=0.1, uncertain=0.9 - fire)
        else:
            return MassFunction(fire=0.95, normal=0.0, uncertain=0.05)

    def humidity_membership(self, value: float) -> MassFunction:
        """
        습도 센서 BPA 계산

        습도는 화재 시 연소로 인해 감소하는 간접 지표입니다.
        정상: 40~60%RH, 화재 시: <30%RH

        Args:
            value: 상대 습도 (%RH)

        Returns:
            Mass Function
        """
        if value is None:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        watch = self.thresholds.get('humidity_watch', 35.0)
        caution = self.thresholds.get('humidity_caution', 25.0)
        warning = self.thresholds.get('humidity_warning', 20.0)
        danger = self.thresholds.get('humidity_danger', 15.0)

        # 습도는 역방향 (낮을수록 의심)
        if value >= 40:
            # 정상 범위
            return MassFunction(fire=0.0, normal=0.9, uncertain=0.1)
        elif value >= watch:
            # 약간 낮음
            ratio = (40 - value) / (40 - watch)
            fire = ratio * 0.05
            return MassFunction(fire=fire, normal=0.8, uncertain=0.2 - fire)
        elif value >= caution:
            ratio = (watch - value) / (watch - caution)
            fire = 0.05 + ratio * 0.1
            return MassFunction(fire=fire, normal=0.65, uncertain=0.35 - fire)
        elif value >= warning:
            ratio = (caution - value) / (caution - warning)
            fire = 0.15 + ratio * 0.15
            return MassFunction(fire=fire, normal=0.5, uncertain=0.5 - fire)
        elif value >= danger:
            ratio = (warning - value) / (warning - danger)
            fire = 0.3 + ratio * 0.2
            return MassFunction(fire=fire, normal=0.35, uncertain=0.65 - fire)
        else:
            # 매우 낮은 습도
            return MassFunction(fire=0.6, normal=0.2, uncertain=0.2)

    def get_membership_function(self, sensor_type: str) -> Callable[[float], MassFunction]:
        """
        센서 유형에 맞는 멤버십 함수 반환

        Args:
            sensor_type: 센서 유형 문자열

        Returns:
            해당 센서의 멤버십 함수
        """
        functions = {
            'smoke': self.smoke_membership,
            'co': self.co_membership,
            'temperature': self.temperature_membership,
            'temp_rate': self.temp_rate_membership,
            'o2': self.o2_membership,
            'co2': self.co2_membership,
            'ch4': self.ch4_membership,
            'h2s': self.h2s_membership,
            'humidity': self.humidity_membership
        }
        return functions.get(sensor_type, lambda x: MassFunction())

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """
        임계값 업데이트 (AI 적응형 시스템용)

        Args:
            new_thresholds: 새로운 임계값 딕셔너리
        """
        self.thresholds.update(new_thresholds)
