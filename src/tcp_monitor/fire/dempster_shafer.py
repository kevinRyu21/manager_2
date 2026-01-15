"""
Dempster-Shafer 증거 이론 기반 센서 융합
GARAMe Manager v2.0

다중 센서 데이터를 융합하여 화재 확률을 계산합니다.
참고: MDPI 2014 "Multi-Sensor Building Fire Alarm with D-S Theory"
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class MassFunction:
    """Basic Probability Assignment (BPA) / Mass Function"""
    fire: float = 0.0       # 화재 확률
    normal: float = 0.0     # 정상 확률
    uncertain: float = 1.0  # 불확실성 (Θ)

    def __post_init__(self):
        """정규화 및 검증"""
        total = self.fire + self.normal + self.uncertain
        if total > 0:
            self.fire /= total
            self.normal /= total
            self.uncertain /= total

    def to_dict(self) -> Dict[str, float]:
        return {
            'fire': self.fire,
            'normal': self.normal,
            'uncertain': self.uncertain
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'MassFunction':
        return cls(
            fire=data.get('fire', 0.0),
            normal=data.get('normal', 0.0),
            uncertain=data.get('uncertain', 1.0)
        )


class DempsterShaferCombiner:
    """
    Dempster-Shafer 증거 조합기

    여러 센서의 BPA를 조합하여 최종 화재 확률을 계산합니다.
    """

    def __init__(self, conflict_threshold: float = 0.99):
        """
        Args:
            conflict_threshold: 충돌 계수 임계값 (이 값을 넘으면 경고)
        """
        self.conflict_threshold = conflict_threshold
        self.last_conflict = 0.0

    def combine_two(self, m1: MassFunction, m2: MassFunction) -> MassFunction:
        """
        두 Mass Function을 Dempster's Rule로 조합

        Dempster's Combination Rule:
        m(A) = Σ m1(B) * m2(C) / (1 - K)
        where B ∩ C = A, and K is the conflict

        Args:
            m1: 첫 번째 Mass Function
            m2: 두 번째 Mass Function

        Returns:
            조합된 Mass Function
        """
        # 각 조합의 교집합 계산
        # fire ∩ fire = fire
        # fire ∩ normal = ∅ (conflict)
        # fire ∩ uncertain = fire
        # normal ∩ normal = normal
        # normal ∩ fire = ∅ (conflict)
        # normal ∩ uncertain = normal
        # uncertain ∩ fire = fire
        # uncertain ∩ normal = normal
        # uncertain ∩ uncertain = uncertain

        # 화재 지지 (fire를 결과로 하는 조합)
        fire_support = (
            m1.fire * m2.fire +
            m1.fire * m2.uncertain +
            m1.uncertain * m2.fire
        )

        # 정상 지지 (normal을 결과로 하는 조합)
        normal_support = (
            m1.normal * m2.normal +
            m1.normal * m2.uncertain +
            m1.uncertain * m2.normal
        )

        # 불확실성 지지 (uncertain을 결과로 하는 조합)
        uncertain_support = m1.uncertain * m2.uncertain

        # 충돌 계수 K (공집합을 결과로 하는 조합)
        conflict = (
            m1.fire * m2.normal +
            m1.normal * m2.fire
        )

        self.last_conflict = conflict

        # 충돌이 1에 가까우면 조합 불가
        if conflict >= 1.0:
            # 충돌이 너무 높으면 불확실성으로 반환
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        # 정규화 계수
        normalizer = 1.0 - conflict

        # 정규화된 결과
        return MassFunction(
            fire=fire_support / normalizer,
            normal=normal_support / normalizer,
            uncertain=uncertain_support / normalizer
        )

    def combine_multiple(self, mass_functions: List[MassFunction]) -> MassFunction:
        """
        여러 Mass Function을 순차적으로 조합

        Args:
            mass_functions: Mass Function 리스트

        Returns:
            조합된 Mass Function
        """
        if not mass_functions:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        if len(mass_functions) == 1:
            return mass_functions[0]

        # 순차적 조합
        result = mass_functions[0]
        for mf in mass_functions[1:]:
            result = self.combine_two(result, mf)

        return result

    def combine_weighted(
        self,
        mass_functions: List[Tuple[MassFunction, float]]
    ) -> MassFunction:
        """
        가중치를 적용한 조합

        센서별 신뢰도/중요도에 따라 가중치를 적용합니다.
        낮은 가중치의 센서는 불확실성 쪽으로 조정됩니다.

        Args:
            mass_functions: (MassFunction, weight) 튜플 리스트

        Returns:
            가중 조합된 Mass Function
        """
        if not mass_functions:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        # 가중치 정규화
        total_weight = sum(w for _, w in mass_functions)
        if total_weight == 0:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        # 가중치 적용된 Mass Function 생성
        weighted_mfs = []
        for mf, weight in mass_functions:
            normalized_weight = weight / total_weight

            # 가중치가 낮으면 불확실성 증가
            # m'(A) = w * m(A) + (1-w) * m(Θ)
            # 이는 낮은 신뢰도의 센서가 결과에 미치는 영향을 줄임
            discounted_fire = normalized_weight * mf.fire
            discounted_normal = normalized_weight * mf.normal
            discounted_uncertain = (
                normalized_weight * mf.uncertain +
                (1 - normalized_weight)
            )

            weighted_mf = MassFunction(
                fire=discounted_fire,
                normal=discounted_normal,
                uncertain=discounted_uncertain
            )
            weighted_mfs.append(weighted_mf)

        return self.combine_multiple(weighted_mfs)

    def get_belief_plausibility(
        self,
        combined: MassFunction
    ) -> Tuple[float, float, float, float]:
        """
        Belief와 Plausibility 계산

        Belief(A): A를 직접 지지하는 증거의 합
        Plausibility(A): A와 충돌하지 않는 모든 증거의 합

        Args:
            combined: 조합된 Mass Function

        Returns:
            (belief_fire, plausibility_fire, belief_normal, plausibility_normal)
        """
        # Belief (하한)
        belief_fire = combined.fire
        belief_normal = combined.normal

        # Plausibility (상한)
        # Pl(fire) = m(fire) + m(uncertain) (normal과 충돌하지 않는 것)
        # Pl(normal) = m(normal) + m(uncertain) (fire와 충돌하지 않는 것)
        plausibility_fire = combined.fire + combined.uncertain
        plausibility_normal = combined.normal + combined.uncertain

        return belief_fire, plausibility_fire, belief_normal, plausibility_normal

    def get_pignistic_probability(self, combined: MassFunction) -> float:
        """
        Pignistic 확률 계산 (의사결정용)

        불확실성을 각 가설에 균등 배분하여 단일 확률값으로 변환
        BetP(fire) = m(fire) + m(uncertain) / 2

        Args:
            combined: 조합된 Mass Function

        Returns:
            화재의 Pignistic 확률
        """
        return combined.fire + combined.uncertain / 2.0


class ImprovedDempsterShafer(DempsterShaferCombiner):
    """
    개선된 Dempster-Shafer 조합기

    참고: PMC 2024 "Tunnel Fire Detection with Improved D-S Theory"

    개선 사항:
    1. 센서 고장 감지 및 배제
    2. 충돌 처리 개선
    3. 시간적 연속성 고려
    """

    def __init__(
        self,
        conflict_threshold: float = 0.99,
        sensor_failure_threshold: float = 0.95,
        temporal_weight: float = 0.3
    ):
        super().__init__(conflict_threshold)
        self.sensor_failure_threshold = sensor_failure_threshold
        self.temporal_weight = temporal_weight
        self.previous_result: Optional[MassFunction] = None

    def detect_sensor_failure(
        self,
        current_reading: float,
        historical_mean: float,
        historical_std: float
    ) -> bool:
        """
        센서 고장 감지 (Z-score 기반)

        Args:
            current_reading: 현재 측정값
            historical_mean: 과거 평균
            historical_std: 과거 표준편차

        Returns:
            고장 여부
        """
        if historical_std == 0:
            return False

        z_score = abs(current_reading - historical_mean) / historical_std

        # Z-score가 매우 높으면 센서 고장으로 판단
        return z_score > 5.0

    def murphy_combination(
        self,
        mass_functions: List[MassFunction]
    ) -> MassFunction:
        """
        Murphy's 평균 기반 조합

        높은 충돌 상황에서 Dempster's Rule보다 안정적인 결과 제공

        Args:
            mass_functions: Mass Function 리스트

        Returns:
            조합된 Mass Function
        """
        if not mass_functions:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        n = len(mass_functions)

        # 평균 Mass Function 계산
        avg_fire = sum(mf.fire for mf in mass_functions) / n
        avg_normal = sum(mf.normal for mf in mass_functions) / n
        avg_uncertain = sum(mf.uncertain for mf in mass_functions) / n

        avg_mf = MassFunction(
            fire=avg_fire,
            normal=avg_normal,
            uncertain=avg_uncertain
        )

        # 평균 MF를 n번 자기 조합
        result = avg_mf
        for _ in range(n - 1):
            result = self.combine_two(result, avg_mf)

        return result

    def combine_with_temporal(
        self,
        current_mfs: List[MassFunction],
        weights: Optional[List[float]] = None
    ) -> MassFunction:
        """
        시간적 연속성을 고려한 조합

        이전 결과와 현재 결과를 가중 평균하여 급격한 변화 방지

        Args:
            current_mfs: 현재 시점의 Mass Function 리스트
            weights: 센서별 가중치 (없으면 균등)

        Returns:
            시간 보정된 Mass Function
        """
        # 현재 시점 조합
        if weights:
            weighted = list(zip(current_mfs, weights))
            current_result = self.combine_weighted(weighted)
        else:
            current_result = self.combine_multiple(current_mfs)

        # 이전 결과가 없으면 현재 결과만 반환
        if self.previous_result is None:
            self.previous_result = current_result
            return current_result

        # 시간적 가중 평균
        # 급격한 변화를 방지하면서도 새로운 정보를 반영
        temporal_result = MassFunction(
            fire=(
                (1 - self.temporal_weight) * current_result.fire +
                self.temporal_weight * self.previous_result.fire
            ),
            normal=(
                (1 - self.temporal_weight) * current_result.normal +
                self.temporal_weight * self.previous_result.normal
            ),
            uncertain=(
                (1 - self.temporal_weight) * current_result.uncertain +
                self.temporal_weight * self.previous_result.uncertain
            )
        )

        self.previous_result = temporal_result
        return temporal_result

    def adaptive_combine(
        self,
        mass_functions: List[MassFunction],
        weights: Optional[List[float]] = None
    ) -> MassFunction:
        """
        적응형 조합 (충돌 수준에 따라 방법 선택)

        - 낮은 충돌: Dempster's Rule
        - 높은 충돌: Murphy's Rule

        Args:
            mass_functions: Mass Function 리스트
            weights: 센서별 가중치

        Returns:
            조합된 Mass Function
        """
        if not mass_functions:
            return MassFunction(fire=0.0, normal=0.0, uncertain=1.0)

        # 먼저 Dempster's Rule로 시도
        if weights:
            weighted = list(zip(mass_functions, weights))
            dempster_result = self.combine_weighted(weighted)
        else:
            dempster_result = self.combine_multiple(mass_functions)

        # 충돌이 높으면 Murphy's Rule 사용
        if self.last_conflict > 0.5:
            murphy_result = self.murphy_combination(mass_functions)

            # 충돌 수준에 따라 두 결과를 혼합
            blend_factor = min(1.0, self.last_conflict * 2 - 1.0)

            return MassFunction(
                fire=(
                    (1 - blend_factor) * dempster_result.fire +
                    blend_factor * murphy_result.fire
                ),
                normal=(
                    (1 - blend_factor) * dempster_result.normal +
                    blend_factor * murphy_result.normal
                ),
                uncertain=(
                    (1 - blend_factor) * dempster_result.uncertain +
                    blend_factor * murphy_result.uncertain
                )
            )

        return dempster_result

    def reset_temporal(self):
        """시간적 상태 초기화"""
        self.previous_result = None
