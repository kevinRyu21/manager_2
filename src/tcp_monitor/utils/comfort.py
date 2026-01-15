"""
체감온도 및 불쾌지수 계산 함수들
"""


def heat_index_c(temp_c: float, rh: float) -> float:
    """
    NOAA Heat Index (섭씨 근사). 통상 T>=26°C & RH>=40%에서 유효.
    그 외 영역에서는 temp_c를 그대로 반환합니다.
    """
    try:
        T = float(temp_c)
        R = float(rh)
    except Exception:
        return temp_c
    
    if T < 26 or R < 40:
        return round(T, 1)
    
    c1 = -8.78469475556
    c2 = 1.61139411
    c3 = 2.33854883889
    c4 = -0.14611605
    c5 = -0.012308094
    c6 = -0.0164248277778
    c7 = 0.002211732
    c8 = 0.00072546
    c9 = -0.000003582
    
    hi = (c1 + (c2 * T) + (c3 * R) + (c4 * T * R) +
          (c5 * (T ** 2)) + (c6 * (R ** 2)) +
          (c7 * (T ** 2) * R) + (c8 * T * (R ** 2)) +
          (c9 * (T ** 2) * (R ** 2)))
    
    return round(hi, 1)


def discomfort_index(temp_c: float, rh: float) -> float:
    """불쾌지수 계산"""
    try:
        T = float(temp_c)
        R = float(rh)
    except Exception:
        return 0.0
    
    di = 0.81*T + 0.01*R*(0.99*T - 14.3) + 46.3
    return round(di, 0)
