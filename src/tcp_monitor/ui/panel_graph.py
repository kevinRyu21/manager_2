"""
패널 그래프 렌더링 컴포넌트

Matplotlib을 사용한 그래프 렌더링 및 Canvas 폴백을 제공합니다.
"""

import time
import datetime
import traceback
import tkinter as tk

# Matplotlib 설정
MPL_OK = True
try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.font_manager as fm

    # 한글 폰트 설정 (Linux 환경 우선 지원)
    import platform
    families = [f.name for f in fm.fontManager.ttflist]
    system = platform.system()

    # 사용 가능한 한글 폰트 찾기
    korean_fonts = []
    for family in families:
        family_lower = family.lower()
        # Linux 한글 폰트
        if any(font in family_lower for font in ['nanum', 'noto', 'malgun', 'pretendard', 'gothic']):
            korean_fonts.append(family)

    # 우선순위: Nanum > Noto > Pretendard > Malgun Gothic > DejaVu Sans
    font_priority = ['NanumGothic', 'NanumBarunGothic', 'Noto Sans CJK KR', 'Noto Sans KR',
                     'Pretendard', 'Malgun Gothic', 'DejaVu Sans']

    selected_font = None
    for priority_font in font_priority:
        for korean_font in korean_fonts:
            if priority_font.lower() in korean_font.lower():
                selected_font = korean_font
                break
        if selected_font:
            break

    if selected_font:
        matplotlib.rcParams["font.family"] = [selected_font]
        print(f"[그래프 렌더러] 한글 폰트 설정: {selected_font}")
    else:
        # 한글 폰트를 찾지 못하면 시스템 기본 폰트 사용
        if korean_fonts:
            matplotlib.rcParams["font.family"] = [korean_fonts[0]]
            print(f"[그래프 렌더러] 기본 한글 폰트 사용: {korean_fonts[0]}")
        else:
            matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
            print(f"[그래프 렌더러 경고] 한글 폰트를 찾을 수 없습니다. DejaVu Sans 사용 (한글 깨짐 가능)")

    matplotlib.rcParams["axes.unicode_minus"] = False
    MPL_OK = True
except Exception as e:
    traceback.print_exc()
    MPL_OK = False


class GraphRenderer:
    """그래프 렌더링 클래스"""

    def __init__(self, container, canvas_widget, log_manager, sid, peer):
        self.container = container
        self.canvas_widget = canvas_widget
        self.log_manager = log_manager
        self.sid = sid
        self.peer = peer

        # Matplotlib 관련 멤버
        self._mpl_canvas = None
        self._mpl_fig = None
        self._mpl_ax = None
        self._mpl_lines = {}
        self._graph_last_redraw = 0.0
        # 최대 포인트 수 (다운샘플링 상한)
        self._max_points = 1200

        # 시간 범위 설정
        self._time_ranges = [1, 24, 168, 720]
        self._current_time_range_index = 0

    def set_time_range_index(self, index):
        """시간 범위 인덱스 설정"""
        self._current_time_range_index = index

    def get_time_range_hours(self):
        """현재 시간 범위 (시간 단위) 반환"""
        return self._time_ranges[self._current_time_range_index]

    def cleanup(self):
        """Matplotlib 캔버스 정리"""
        if self._mpl_canvas:
            try:
                self._mpl_canvas.get_tk_widget().pack_forget()
                self._mpl_canvas.get_tk_widget().destroy()
            except:
                pass
            self._mpl_canvas = None
            self._mpl_fig = None
            self._mpl_ax = None
            self._mpl_lines = {}

    def draw_graph(self, key, force=False):
        """그래프 그리기"""
        hours = self.get_time_range_hours()
        data = self.log_manager.get_sensor_data_for_hours(self.sid, self.peer, key, hours)

        now = time.time()
        if not force and now - self._graph_last_redraw < 1.0:
            return
        self._graph_last_redraw = now

        if not data:
            self.cleanup()
            self.canvas_widget.pack(side="top", fill="both", expand=True, padx=10, pady=10)
            self.canvas_widget.delete("all")
            self.canvas_widget.create_text(10, 10, anchor="nw", fill="#FFFFFF", text="데이터 없음", font=("Pretendard", 12))
            return

        # 다운샘플링: 포인트 수가 많으면 간격 샘플링
        xs_raw = [ts for ts, _ in data]
        ys_raw = [v for _, v in data]
        xs_ds, ys_ds = self._downsample(xs_raw, ys_raw, self._max_points)
        xs = [datetime.datetime.fromtimestamp(ts) for ts in xs_ds]
        ys = ys_ds

        if MPL_OK:
            self._draw_matplotlib_graph(key, data, xs, ys)
        else:
            self._draw_canvas_graph(key, data, xs, ys)

    def _draw_matplotlib_graph(self, key, data, xs, ys):
        """Matplotlib을 사용한 그래프 그리기"""
        self.canvas_widget.pack_forget()

        # 현재 범위 값에서 -1 필터링 (온도는 음수 가능)
        if key != "temperature":
            ys_filtered = [v for v in ys if v != -1]
        else:
            ys_filtered = [v for v in ys if v >= -100]

        current_max = max(ys_filtered) if ys_filtered else 1
        current_min = min(ys_filtered) if ys_filtered else 0
        current_avg = sum(ys_filtered) / len(ys_filtered) if ys_filtered else 0.5

        # 항상 현재 데이터 범위의 통계 표시
        display_min = current_min
        display_max = current_max
        show_today_lines = True

        # Y축 스케일 자동 계산
        data_range = display_max - display_min
        scale = self._auto_calculate_scale(data_range)

        y_min = (display_min // scale) * scale - scale
        y_max = ((display_max // scale) + 1) * scale + scale

        import numpy as np
        yticks = np.arange(y_min, y_max + scale, scale)

        # 기존 그래프가 있으면 업데이트, 없으면 새로 생성
        if self._mpl_canvas is None:
            self._create_matplotlib_graph(key, xs, ys, data, current_max, current_min,
                                         current_avg, show_today_lines, y_min, y_max, yticks, scale)
        else:
            self._update_matplotlib_graph(key, xs, ys, data, current_max, current_min,
                                         current_avg, show_today_lines, y_min, y_max, yticks, scale)

    def _create_matplotlib_graph(self, key, xs, ys, today_data, today_current_max, today_current_min,
                                 current_avg, show_today_lines, y_min, y_max, yticks, scale):
        """새 Matplotlib 그래프 생성"""
        fig = Figure(figsize=(10, 5), dpi=100)
        ax = fig.add_subplot(111)

        line_data, = ax.plot(xs, ys, color='#2196F3', linewidth=2, label='실시간 데이터')

        if show_today_lines and today_data:
            line_max = ax.axhline(y=today_current_max, xmin=0, xmax=1, color='#FF6B6B', linestyle='--', linewidth=2, alpha=0.3, label=f'최고: {today_current_max:.2f}')
            line_avg = ax.axhline(y=current_avg, xmin=0, xmax=1, color='#FFD700', linestyle='--', linewidth=2, alpha=0.3, label=f'평균: {current_avg:.2f}')
            line_min = ax.axhline(y=today_current_min, xmin=0, xmax=1, color='#4ECDC4', linestyle='--', linewidth=2, alpha=0.3, label=f'최저: {today_current_min:.2f}')
            self._mpl_lines = {"data": line_data, "max": line_max, "avg": line_avg, "min": line_min}
        else:
            self._mpl_lines = {"data": line_data}

        hours = self.get_time_range_hours()
        time_text = self._get_time_text(hours)

        unit_map = {
            "co2": "ppm", "h2s": "ppm", "co": "ppm",
            "o2": "%", "temperature": "℃", "humidity": "%"
        }
        unit = unit_map.get(key, "")

        ax.set_title(f"{time_text} (Y축 한 칸당: {scale}{unit})")
        ax.set_xlabel("시간")
        ax.set_ylabel(f"값 ({unit})")
        ax.set_ylim(y_min, y_max)
        ax.set_yticks(yticks)
        ax.grid(True, linestyle=':', alpha=0.5, linewidth=1.5)
        ax.legend(loc='upper left', fontsize=9)
        fig.autofmt_xdate()
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)
        fig.tight_layout()

        self._mpl_fig = fig
        self._mpl_ax = ax
        self._mpl_canvas = FigureCanvasTkAgg(fig, master=self.container)
        self._mpl_canvas.draw_idle()
        self._mpl_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    def _update_matplotlib_graph(self, key, xs, ys, today_data, today_current_max, today_current_min,
                                 current_avg, show_today_lines, y_min, y_max, yticks, scale):
        """기존 Matplotlib 그래프 업데이트"""
        try:
            self._mpl_lines["data"].set_xdata(xs)
            self._mpl_lines["data"].set_ydata(ys)

            if show_today_lines and today_data and "max" in self._mpl_lines:
                self._mpl_lines["max"].set_ydata([today_current_max, today_current_max])
                self._mpl_lines["avg"].set_ydata([current_avg, current_avg])
                self._mpl_lines["min"].set_ydata([today_current_min, today_current_min])

                self._mpl_lines["max"].set_label(f'최고: {today_current_max:.2f}')
                self._mpl_lines["avg"].set_label(f'평균: {current_avg:.2f}')
                self._mpl_lines["min"].set_label(f'최저: {today_current_min:.2f}')
            elif show_today_lines and today_data and "max" not in self._mpl_lines:
                line_max = self._mpl_ax.axhline(y=today_current_max, xmin=0, xmax=1, color='#FF6B6B', linestyle='--', linewidth=2, alpha=0.3, label=f'최고: {today_current_max:.2f}')
                line_avg = self._mpl_ax.axhline(y=current_avg, xmin=0, xmax=1, color='#FFD700', linestyle='--', linewidth=2, alpha=0.3, label=f'평균: {current_avg:.2f}')
                line_min = self._mpl_ax.axhline(y=today_current_min, xmin=0, xmax=1, color='#4ECDC4', linestyle='--', linewidth=2, alpha=0.3, label=f'최저: {today_current_min:.2f}')
                self._mpl_lines.update({"max": line_max, "avg": line_avg, "min": line_min})
            elif "max" in self._mpl_lines and not show_today_lines:
                for line_key in ["max", "avg", "min"]:
                    if line_key in self._mpl_lines:
                        self._mpl_lines[line_key].remove()
                self._mpl_lines = {"data": self._mpl_lines["data"]}

            hours = self.get_time_range_hours()
            time_text = self._get_time_text(hours)

            unit_map = {
                "co2": "ppm", "h2s": "ppm", "co": "ppm",
                "o2": "%", "temperature": "℃", "humidity": "%"
            }
            unit = unit_map.get(key, "")

            self._mpl_ax.set_ylim(y_min, y_max)
            self._mpl_ax.set_yticks(yticks)
            self._mpl_ax.set_title(f"{time_text} (Y축 한 칸당: {scale}{unit})")
            self._mpl_ax.relim()
            self._mpl_ax.autoscale_view(scalex=True, scaley=False)
            self._mpl_ax.legend(loc='upper left', fontsize=9)
            self._mpl_fig.autofmt_xdate()
            self._mpl_fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)
            self._mpl_fig.tight_layout()

            self._mpl_canvas.draw_idle()
        except Exception:
            self.cleanup()
            self.draw_graph(key, force=True)

    def _draw_canvas_graph(self, key, data, xs, ys):
        """Canvas를 사용한 폴백 그래프 그리기"""
        self.canvas_widget.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.canvas_widget.delete("all")

        W = self.canvas_widget.winfo_width() or 800
        H = self.canvas_widget.winfo_height() or 500
        pad_left = 60
        pad_right = 20
        pad_top = 40
        pad_bottom = 60

        t0, t1 = data[0][0], data[-1][0]

        # 캔버스 드로잉용 다운샘플링 (너무 많은 라인 그리기 방지)
        if len(data) > 2000:
            step = max(1, len(data)//2000)
            data = data[::step]

        # -1 값 필터링 (온도는 음수 가능)
        if key != "temperature":
            ys_filtered = [v for v in ys if v != -1]
        else:
            ys_filtered = [v for v in ys if v >= -100]

        current_max = max(ys_filtered) if ys_filtered else 1
        current_min = min(ys_filtered) if ys_filtered else 0

        today_stats = self.log_manager.get_today_stats(self.sid, self.peer, key)
        today_current_max = current_max
        today_current_min = current_min
        if today_stats:
            today_current_max = today_stats["max"]
            today_current_min = today_stats["min"]

        display_min = current_min
        display_max = current_max

        show_today_lines = True
        current_range = current_max - current_min

        if today_current_min < current_min:
            diff_ratio = (current_min - today_current_min) / max(current_range, 1)
            if diff_ratio <= 0.5:
                display_min = today_current_min
            else:
                show_today_lines = False

        if today_current_max > current_max:
            diff_ratio = (today_current_max - current_max) / max(current_range, 1)
            if diff_ratio <= 0.5:
                display_max = today_current_max
            else:
                show_today_lines = False

        data_range = display_max - display_min
        scale = self._auto_calculate_scale(data_range)

        y_min = (display_min // scale) * scale - scale
        y_max = ((display_max // scale) + 1) * scale + scale

        def X(ts):
            return pad_left + (ts - t0)/(t1 - t0) * (W - pad_left - pad_right) if t1 > t0 else pad_left

        def Y(v):
            return H - pad_bottom - (v - y_min)/(y_max - y_min) * (H - pad_top - pad_bottom)

        self.canvas_widget.create_rectangle(pad_left, pad_top, W-pad_right, H-pad_bottom, outline="#666666", width=2)

        num_y_ticks = 5
        for i in range(num_y_ticks + 1):
            y_val = y_min + (y_max - y_min) * i / num_y_ticks
            y_pos = Y(y_val)
            self.canvas_widget.create_line(pad_left, y_pos, W - pad_right, y_pos, fill="#444444", dash=(3, 5), width=1)
            self.canvas_widget.create_text(pad_left - 10, y_pos, anchor="e", fill="#CCCCCC", text=f"{y_val:.1f}", font=("Pretendard", 9))

        num_x_ticks = 6
        for i in range(num_x_ticks + 1):
            ts = t0 + (t1 - t0) * i / num_x_ticks
            x_pos = X(ts)
            self.canvas_widget.create_line(x_pos, pad_top, x_pos, H - pad_bottom, fill="#444444", dash=(3, 5), width=1)
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M')
            self.canvas_widget.create_text(x_pos, H - pad_bottom + 10, anchor="n", fill="#CCCCCC", text=time_str, font=("Pretendard", 9))

        last = None
        for ts, v in data:
            x, y = X(ts), Y(v)
            if last:
                self.canvas_widget.create_line(last[0], last[1], x, y, fill="#4A9EFF", width=3)
            last = (x, y)

        self.canvas_widget.create_text((pad_left + W - pad_right) / 2, H - 20, anchor="center",
                                      fill="#FFFFFF", text="시간", font=("Pretendard", 10, "bold"))

        unit_map = {
            "co2": "ppm", "h2s": "ppm", "co": "ppm",
            "o2": "%", "temperature": "℃", "humidity": "%"
        }
        unit = unit_map.get(key, "")
        self.canvas_widget.create_text(20, (pad_top + H - pad_bottom) / 2, anchor="center",
                                      fill="#FFFFFF", text=f"값 ({unit})", font=("Pretendard", 10, "bold"), angle=90)

    def _downsample(self, xs, ys, max_points):
        """간단한 decimation: 최대 포인트 수를 초과하면 간격 샘플링"""
        try:
            n = len(xs)
            if n <= max_points:
                return xs, ys
            k = max(1, n // max_points)
            xs_ds = xs[::k]
            ys_ds = ys[::k]
            if xs_ds[-1] != xs[-1]:
                xs_ds.append(xs[-1])
                ys_ds.append(ys[-1])
            return xs_ds, ys_ds
        except Exception:
            return xs, ys

    def _auto_calculate_scale(self, data_range):
        """Y축 스케일 자동 계산"""
        if data_range <= 0:
            return 10

        import math
        magnitude = 10 ** math.floor(math.log10(data_range))

        candidates = []
        for mult in [1, 2, 5]:
            mag = max(10, magnitude)
            while mag <= data_range * 2:
                candidates.append(mult * mag)
                mag *= 10

        candidates = sorted(set(candidates))
        candidates = [c for c in candidates if c >= 10]

        for scale in candidates:
            num_ticks = data_range / scale
            if num_ticks >= 2 and num_ticks <= 8:
                return scale

        calculated = max(10, math.ceil(data_range / 6 / 10) * 10)
        return calculated

    def _get_time_text(self, hours):
        """시간 범위 텍스트 반환"""
        if hours == 1:
            return "최근 1시간"
        elif hours == 24:
            return "최근 24시간"
        elif hours == 168:
            return "최근 7일"
        else:
            return "최근 1달"
