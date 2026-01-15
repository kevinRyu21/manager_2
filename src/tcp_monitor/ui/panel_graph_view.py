"""
패널 그래프 뷰 컴포넌트

최근 1시간 데이터를 9개(3x3) 그래프로 표시합니다.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import font_manager as fm
from ..utils.helpers import SENSOR_KEYS

# 한글 폰트 설정 (Linux 환경 우선 지원)
try:
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
        print(f"[그래프] 한글 폰트 설정: {selected_font}")
    else:
        # 한글 폰트를 찾지 못하면 시스템 기본 폰트 사용
        if korean_fonts:
            matplotlib.rcParams["font.family"] = [korean_fonts[0]]
            print(f"[그래프] 기본 한글 폰트 사용: {korean_fonts[0]}")
        else:
            matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
            print(f"[그래프 경고] 한글 폰트를 찾을 수 없습니다. DejaVu Sans 사용 (한글 깨짐 가능)")

    matplotlib.rcParams["axes.unicode_minus"] = False
except Exception as e:
    print(f"[그래프] 폰트 설정 오류: {e}")
    matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


class PanelGraphView(ttk.Frame):
    """최근 1시간 데이터를 표시하는 그래프 뷰"""

    def __init__(self, master, logs, sid, peer, config):
        super().__init__(master)
        self.logs = logs
        self.sid = sid
        self.peer = peer
        self.config = config

        # 센서 이름 한글 매핑 (matplotlib 호환)
        self.sensor_names = {
            "co2": "이산화탄소 CO₂ (ppm)",
            "h2s": "황화수소 H₂S (ppm)",
            "co": "일산화탄소 CO (ppm)",
            "o2": "산소 O₂ (%)",
            "lel": "가연성가스 LEL (%)",
            "smoke": "연기 (ppm)",
            "temperature": "온도 (℃)",
            "humidity": "습도 (%)",
            "water": "누수 감지"
        }

        # 센서 색상 매핑 (더 진한 색상으로 가독성 향상)
        self.sensor_colors = {
            "co2": "#1976D2",
            "h2s": "#F57C00",
            "co": "#D32F2F",
            "o2": "#388E3C",
            "lel": "#FF9800",
            "smoke": "#9C27B0",
            "temperature": "#7B1FA2",
            "humidity": "#0097A7",
            "water": "#E91E63"
        }

        # 마커 테두리 색상 매핑 (각 그래프 색상보다 조금 더 어두운 색)
        self.marker_edge_colors = {
            "co2": "#0D47A1",
            "h2s": "#E65100",
            "co": "#B71C1C",
            "o2": "#1B5E20",
            "lel": "#F57F17",
            "smoke": "#6A1B9A",
            "temperature": "#4A148C",
            "humidity": "#006064",
            "water": "#AD1457"
        }

        # Figure 생성 (3x3 그리드) - 밝은 배경
        self.figure = Figure(figsize=(20, 14), facecolor="#F5F5F5")
        self.figure.subplots_adjust(left=0.05, right=0.995, top=0.92, bottom=0.12, hspace=0.45, wspace=0.15)

        # 각 센서별 subplot 생성
        self.axes = {}
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]

        for idx, key in enumerate(SENSOR_KEYS):
            row, col = positions[idx]
            ax = self.figure.add_subplot(3, 3, idx + 1)
            ax.set_facecolor("#FFFFFF")
            ax.tick_params(colors="#333333", labelsize=9, pad=1)
            ax.tick_params(axis='y', which='major', pad=1)
            ax.yaxis.labelpad = 1
            ax.grid(True, color="#BDBDBD", linestyle="-", linewidth=0.8, alpha=0.5)
            ax.spines["bottom"].set_color("#757575")
            ax.spines["top"].set_color("#757575")
            ax.spines["left"].set_color("#757575")
            ax.spines["right"].set_color("#757575")
            ax.spines["bottom"].set_linewidth(1.5)
            ax.spines["left"].set_linewidth(1.5)
            ax.spines["top"].set_linewidth(0.5)
            ax.spines["right"].set_linewidth(0.5)

            # 제목 설정 (더 큰 폰트)
            title = self.sensor_names.get(key, key)
            ax.set_title(title, color="#212121", fontsize=12, fontweight="bold", pad=8)

            self.axes[key] = ax

        # Canvas 생성
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # 초기 그래프 업데이트
        self.update_graphs()

    def _get_threshold_info(self, key):
        """5단계 경보 시스템 임계값 정보 반환"""
        s = self.config.std

        if key == "o2":
            return {
                "min": s.get("o2_normal_min", 19.5),
                "max": s.get("o2_normal_max", 23.0),
                "label": f"정상: {s.get('o2_normal_min', 19.5):.1f}~{s.get('o2_normal_max', 23.0):.1f}%"
            }
        elif key == "h2s":
            return {
                "max": s.get("h2s_normal_max", 5),
                "label": f"정상 최대: {s.get('h2s_normal_max', 5):.1f} ppm"
            }
        elif key == "co":
            return {
                "max": s.get("co_normal_max", 9),
                "label": f"정상 최대: {s.get('co_normal_max', 9):.1f} ppm"
            }
        elif key == "co2":
            return {
                "max": s.get("co2_normal_max", 1000),
                "label": f"정상 최대: {s.get('co2_normal_max', 1000):.0f} ppm"
            }
        elif key == "temperature":
            return {
                "min": s.get("temp_normal_min", 18),
                "max": s.get("temp_normal_max", 28),
                "label": f"정상: {s.get('temp_normal_min', 18):.0f}~{s.get('temp_normal_max', 28):.0f}℃"
            }
        elif key == "humidity":
            return {
                "min": s.get("hum_normal_min", 40),
                "max": s.get("hum_normal_max", 60),
                "label": f"정상: {s.get('hum_normal_min', 40):.0f}~{s.get('hum_normal_max', 60):.0f}%"
            }
        elif key == "lel":
            return {
                "max": s.get("lel_normal_max", 10),
                "label": f"정상 최대: {s.get('lel_normal_max', 10):.1f}%"
            }
        elif key == "smoke":
            return {
                "max": s.get("smoke_normal_max", 0),
                "label": f"정상 최대: {s.get('smoke_normal_max', 0):.1f} ppm"
            }
        elif key == "water":
            return {
                "max": 1,
                "label": "정상: 0, 누수감지: 1"
            }
        return None

    def update_graphs(self, preset_data=None):
        """최근 1시간 데이터로 그래프 업데이트. preset_data가 주어지면 그것을 사용."""
        # 최근 1시간 데이터 가져오기 (사전 로드 데이터 우선)
        data = preset_data
        if data is None:
            try:
                data = self.logs.get_sensor_history_hours(self.sid, self.peer, hours=1)
            except Exception as e:
                print(f"[GraphView] Error getting data: {e}")
                data = None

        if not data:
            # 데이터가 없으면 빈 그래프 표시
            for key in SENSOR_KEYS:
                ax = self.axes[key]
                ax.clear()
                ax.set_facecolor("#FFFFFF")
                ax.tick_params(colors="#333333", labelsize=9, pad=1)
                ax.tick_params(axis='y', which='major', pad=1)
                ax.yaxis.labelpad = 1
                ax.grid(True, color="#BDBDBD", linestyle="-", linewidth=0.8, alpha=0.5)
                title = self.sensor_names.get(key, key)
                ax.set_title(title, color="#212121", fontsize=10, fontweight="bold", pad=6)
                ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                       transform=ax.transAxes, color="#757575", fontsize=12, fontweight="bold")
            self.canvas.draw_idle()
            return

        # 데이터를 시간순으로 정렬
        data.sort(key=lambda x: x["timestamp"])

        # 각 센서별로 그래프 그리기
        for key in SENSOR_KEYS:
            ax = self.axes[key]
            ax.clear()
            ax.set_facecolor("#FFFFFF")
            ax.tick_params(colors="#333333", labelsize=9, pad=1)
            ax.tick_params(axis='y', which='major', pad=1)
            ax.yaxis.labelpad = 1
            ax.grid(True, color="#BDBDBD", linestyle="-", linewidth=0.8, alpha=0.5)
            ax.spines["bottom"].set_color("#757575")
            ax.spines["top"].set_color("#757575")
            ax.spines["left"].set_color("#757575")
            ax.spines["right"].set_color("#757575")
            ax.spines["bottom"].set_linewidth(1.5)
            ax.spines["left"].set_linewidth(1.5)
            ax.spines["top"].set_linewidth(0.5)
            ax.spines["right"].set_linewidth(0.5)

            title = self.sensor_names.get(key, key)

            # 데이터 추출
            timestamps = []
            values = []
            all_values = []  # 디버깅용
            field_exists_count = 0
            field_none_count = 0
            
            for entry in data:
                if key in entry:
                    field_exists_count += 1
                    if entry[key] is not None:
                        try:
                            val = float(entry[key])
                            all_values.append(val)  # 디버깅용
                            # 유효한 값만 추가 (lel, smoke, water는 -1도 허용)
                            if val != -1 or key in ["lel", "smoke", "water"]:
                                timestamps.append(entry["timestamp"])
                                values.append(val)
                        except (ValueError, TypeError):
                            continue
                    else:
                        field_none_count += 1
            
            # 디버깅 정보 출력 (주석 처리)
            # if key in ["lel", "smoke", "water"] and len(values) == 0:
            #     if field_exists_count == 0:
            #         print(f"[GraphView] {key} - 필드가 데이터베이스에 없음 (기존 데이터)")
            #     else:
            #         print(f"[GraphView] {key} - 필드 존재: {field_exists_count}, None 값: {field_none_count}, 총 데이터: {len(data)}")
            #         if all_values:
            #             print(f"[GraphView] {key} raw values: {all_values[:10]}...")
            #         else:
            #             print(f"[GraphView] {key} - 변환 가능한 값이 없음")

            # 특수 센서 처리
            if key == "water":
                # 누수 센서는 0/1 값이므로 Y축을 0~1로 고정
                ax.set_ylim(-0.1, 1.1)
                ax.set_yticks([0, 1])
                ax.set_yticklabels(["정상", "누수감지"])
                
                if field_exists_count == 0:
                    # 필드가 없는 경우 (기존 데이터) - 더미 데이터 생성
                    ax.set_facecolor("#F5F5F5")  # 회색 배경
                    
                    # 기존 데이터의 타임스탬프 형식을 사용하여 더미 데이터 생성
                    if data:
                        timestamps = [entry["timestamp"] for entry in data]
                        values = [0] * len(timestamps)
                    else:
                        timestamps = []
                        values = []
                elif values:
                    # 누수 감지 시 배경색 변경
                    if values[-1] == 1:
                        ax.set_facecolor("#FFEBEE")  # 연한 빨간색
                    else:
                        ax.set_facecolor("#E8F5E8")  # 연한 녹색
            elif key in ["lel", "smoke"]:
                # 가연성가스와 연기는 더미 센서이므로 접속 대기 상태로 표시
                ax.set_ylim(-1.5, 0.5)
                ax.set_yticks([-1])
                ax.set_yticklabels(["센서 연결 대기중..."], fontsize=10)
                ax.set_facecolor("#E8E8E8")  # 회색 배경
                
                # 더미 데이터 생성 (접속 대기 상태)
                if data:
                    timestamps = [entry["timestamp"] for entry in data]
                    values = [-1] * len(timestamps)
                else:
                    timestamps = []
                    values = []
            
            # 최종 값 개수 출력 (주석 처리)
            # print(f"[GraphView] {key}: {len(values)} valid values")

            if not values:
                ax.set_title(title, color="#212121", fontsize=12, fontweight="bold", pad=8)
                ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                       transform=ax.transAxes, color="#757575", fontsize=14, fontweight="bold")
                continue

            # 통계 계산
            current_val = values[-1]
            
            # -1 값을 제외한 유효한 값들로 통계 계산
            valid_values = [v for v in values if v != -1]
            if valid_values:
                min_val = min(valid_values)
                max_val = max(valid_values)
                avg_val = sum(valid_values) / len(valid_values)
            else:
                # 모든 값이 -1인 경우
                min_val = max_val = avg_val = -1

            # 임계값 정보 가져오기
            threshold_info = self._get_threshold_info(key)

            # 임계값 초과 여부 확인
            is_threshold_exceeded = False
            if threshold_info:
                # 산소(O2)는 범위 체크 (min과 max 둘 다 있는 경우)
                if "min" in threshold_info and "max" in threshold_info and "danger" not in threshold_info:
                    if current_val < threshold_info["min"] or current_val > threshold_info["max"]:
                        is_threshold_exceeded = True
                # 온도는 위험값 또는 범위 체크
                elif "danger" in threshold_info:
                    if current_val >= threshold_info["danger"]:
                        is_threshold_exceeded = True
                    elif "min" in threshold_info and current_val < threshold_info["min"]:
                        is_threshold_exceeded = True
                    elif "max" in threshold_info and current_val > threshold_info["max"]:
                        is_threshold_exceeded = True
                # 기타 (최대값만 있는 경우: CO2, H2S, CO)
                elif "max" in threshold_info and current_val > threshold_info["max"]:
                    is_threshold_exceeded = True
                # 습도 (범위만 있는 경우)
                elif "min" in threshold_info and current_val < threshold_info["min"]:
                    is_threshold_exceeded = True
                elif "max" in threshold_info and current_val > threshold_info["max"]:
                    is_threshold_exceeded = True

            # 배경색 설정 (임계값 초과 시 경고색)
            if is_threshold_exceeded:
                bg_color = "#FFEBEE"  # 연한 빨간색 (경고)
                ax.set_facecolor(bg_color)
            else:
                bg_color = "#FFFFFF"
                ax.set_facecolor(bg_color)

            # Y축 범위 설정 (임계값 기반)
            if threshold_info and min_val != -1 and max_val != -1:
                y_min = min_val
                y_max = max_val

                # 임계값을 고려한 Y축 범위 설정
                if "min" in threshold_info:
                    y_min = min(y_min, threshold_info["min"])
                if "max" in threshold_info:
                    y_max = max(y_max, threshold_info["max"])
                if "danger" in threshold_info:
                    y_max = max(y_max, threshold_info["danger"])

                # 여유 공간 추가 (10%)
                y_range = y_max - y_min
                if y_range > 0:
                    margin = y_range * 0.1
                    y_min = y_min - margin
                    y_max = y_max + margin
                else:
                    # 범위가 0인 경우
                    y_min = y_min - 1
                    y_max = y_max + 1

                ax.set_ylim(y_min, y_max)

            # 제목에 현재값 표시
            if key == "water":
                # 누수 센서는 상태로 표시
                if len(values) == 0:
                    # 필드가 없는 경우
                    title_with_value = f"{title}\n현재: 센서 미연결"
                else:
                    current_status = "누수감지" if current_val == 1 else "정상"
                    title_with_value = f"{title}\n현재: {current_status}"
            elif key in ["lel", "smoke"]:
                if len(values) == 0 or current_val == -1:
                    # 필드가 없거나 -1인 경우
                    title_with_value = f"{title}\n현재: 센서 미연결"
                else:
                    title_with_value = f"{title}\n현재: {current_val:.1f}  |  최소: {min_val:.1f}  |  최대: {max_val:.1f}  |  평균: {avg_val:.1f}"
            else:
                title_with_value = f"{title}\n현재: {current_val:.1f}  |  최소: {min_val:.1f}  |  최대: {max_val:.1f}  |  평균: {avg_val:.1f}"
            ax.set_title(title_with_value, color="#212121", fontsize=10, fontweight="bold", pad=6)

            # 그래프 그리기 (선과 마커)
            color = self.sensor_colors.get(key, "#1976D2")
            edge_color = self.marker_edge_colors.get(key, "#212121")

            if timestamps and values:  # 타임스탬프와 값이 모두 있는 경우만 그래프 그리기
                if key == "water":
                    # 누수 센서는 막대 그래프로 표시
                    ax.bar(timestamps, values, color=color, alpha=0.7, width=0.01)
                else:
                    ax.plot(timestamps, values, color=color, linewidth=2.5, marker="o", markersize=5,
                           markerfacecolor=color, markeredgecolor=edge_color, markeredgewidth=1, alpha=0.9, zorder=3)

            # 영역 채우기 (그래프 아래) - 누수 센서 제외
            if key != "water" and timestamps and values:
                ax.fill_between(timestamps, values, alpha=0.15, color=color, zorder=2)

            # 임계값 선 그리기 (점선) - 누수 센서 제외
            if threshold_info and timestamps and values and key != "water":
                x_min, x_max = timestamps[0], timestamps[-1]

                # 최대값 선 (빨간색 점선)
                if "max" in threshold_info:
                    ax.axhline(y=threshold_info["max"], color="#D32F2F", linestyle="--",
                              linewidth=2, alpha=0.7, label=f'최대: {threshold_info["max"]:.1f}', zorder=4)

                # 최소값 선 (파란색 점선)
                if "min" in threshold_info:
                    ax.axhline(y=threshold_info["min"], color="#1976D2", linestyle="--",
                              linewidth=2, alpha=0.7, label=f'최소: {threshold_info["min"]:.1f}', zorder=4)

                # 위험 레벨 선 (진한 빨간색 점선)
                if "danger" in threshold_info:
                    ax.axhline(y=threshold_info["danger"], color="#B71C1C", linestyle="--",
                              linewidth=2.5, alpha=0.8, label=f'위험: {threshold_info["danger"]:.0f}', zorder=4)

                # 범례 표시 (왼쪽 위)
                ax.legend(loc="upper left", fontsize=10, framealpha=0.95, edgecolor="#757575")

            # 현재값 강조 표시
            if timestamps and values:
                ax.plot(timestamps[-1], values[-1], 'o', markersize=9,
                       color=color, markeredgecolor=edge_color, markeredgewidth=2, zorder=5)

            # x축 포맷 (시:분만 표시)
            from matplotlib.dates import DateFormatter, AutoDateLocator
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            ax.xaxis.set_major_locator(AutoDateLocator())

            # x축 범위를 데이터 시작/끝에 정확히 맞춤
            if timestamps and len(timestamps) >= 2:
                ax.set_xlim(timestamps[0], timestamps[-1])

            # x축 레이블 회전
            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha("right")
                label.set_fontsize(10)
                label.set_color("#424242")

        self.canvas.draw_idle()
