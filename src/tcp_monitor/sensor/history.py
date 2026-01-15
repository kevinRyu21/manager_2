"""
센서 데이터 히스토리 관리

센서별 시계열 버퍼(최근 1시간), 금일 통계(최저/평균/최고)
"""

import time
from collections import deque, defaultdict
from ..utils.helpers import SENSOR_KEYS, now_local


class SensorHistory:
    """센서별 시계열 버퍼(최근 1시간), 금일 통계(최저/평균/최고)"""
    
    def __init__(self):
        self.last_hour = {k: deque(maxlen=3600) for k in SENSOR_KEYS}
        self.today_sum = defaultdict(float)
        self.today_cnt = defaultdict(int)
        self.today_min = defaultdict(lambda: float("inf"))
        self.today_max = defaultdict(lambda: float("-inf"))
        self.today_date = now_local().date()

    def push(self, data):
        """새로운 센서 데이터 추가"""
        now_ts = time.time()
        now_date = now_local().date()

        # 날짜가 바뀌면 통계 초기화
        if now_date != self.today_date:
            self.today_sum.clear()
            self.today_cnt.clear()
            self.today_min = defaultdict(lambda: float("inf"))
            self.today_max = defaultdict(lambda: float("-inf"))
            self.today_date = now_date

        for k in SENSOR_KEYS:
            v = data.get(k, None)
            if v is None:
                continue
            try:
                fv = float(v)
            except:
                continue

            # -1은 "값 없음"으로 처리 (온도는 음수가 될 수 있으므로 예외)
            # 온도가 아닌 센서에서 -1은 유효하지 않은 값으로 간주
            if k != "temperature" and fv == -1:
                continue
            # 온도는 -1이 실제 온도일 수 있으므로, 극단적으로 낮은 값(-100 미만)만 필터링
            if k == "temperature" and fv < -100:
                continue

            self.last_hour[k].append((now_ts, fv))
            self.today_sum[k] += fv
            self.today_cnt[k] += 1
            if fv < self.today_min[k]:
                self.today_min[k] = fv
            if fv > self.today_max[k]:
                self.today_max[k] = fv

    def get_last_hour(self, key):
        """최근 1시간 데이터 반환"""
        now_ts = time.time()
        cutoff = now_ts - 3600
        return [(ts, v) for (ts, v) in self.last_hour[key] if ts >= cutoff]

    def get_last_hours(self, key, hours):
        """최근 N시간 데이터 반환"""
        now_ts = time.time()
        cutoff = now_ts - (3600 * hours)
        return [(ts, v) for (ts, v) in self.last_hour[key] if ts >= cutoff]

    def get_today(self, key):
        """오늘 데이터 반환 (통계용)"""
        return [(ts, v) for (ts, v) in self.last_hour[key]]

    def today_stats_text(self, key):
        """오늘 통계 텍스트 반환"""
        cnt = self.today_cnt.get(key, 0)
        if cnt <= 0:
            return "오늘 통계: - / - / -"
        mn = self.today_min.get(key, float("inf"))
        mx = self.today_max.get(key, float("-inf"))
        avg = self.today_sum.get(key, 0.0) / cnt
        fmt = lambda x: f"{x:.1f}" if key in ("o2", "temperature", "humidity") else f"{x:.0f}"
        return f"오늘 통계: 최저 {fmt(mn)} / 평균 {fmt(avg)} / 최고 {fmt(mx)}"
