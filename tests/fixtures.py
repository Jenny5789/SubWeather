"""파이프라인 검증용 가짜(fixture) 데이터 생성 함수 모음.

공공데이터포털 API가 아직 열리지 않아, 실제 데이터 없이 collector/merge 함수들의
입출력 형태만 먼저 검증하기 위한 샘플 DataFrame들이다. 실제 API 필드명이 확정되면
이 파일의 컬럼명도 함께 맞춰야 한다.

역 구성(5개 물리적 역, 8개 station_id 행 — 환승역은 노선 수만큼 행이 생긴다):
- 강남(2호선), 잠실(2호선): 일반역 2개
- 교대(2호선+3호선): 2개 노선 환승역 1개
- 고속터미널(3호선+7호선+9호선): 3개 노선 환승역 1개
- 신논현(9호선): 9호선 단독역 1개

좌표는 지도 렌더링 테스트를 위해 강북/강서/도심/강남/강동 등 서울 전역에 흩어지도록
임의로 배치했다 (실제 역의 지리적 위치와는 무관 — 실 서비스에서 276개 역이 들어오면
자연스럽게 퍼지므로, 그 전까지 지도가 여러 지역에 마커를 제대로 그리는지 확인하는 용도).
"""

import pandas as pd


def make_station_master() -> pd.DataFrame:
    """station_id, station_name, line, latitude, longitude, region (서울 지하철 276개 역)."""

    # 호선별 끝점 좌표 및 역 수 (선형 보간용)
    line_configs = {
        "1호선": {"start": (37.5550, 126.9733), "end": (37.5825, 127.0521), "count": 44},
        "2호선": {"start": (37.4979, 127.0276), "end": (37.5550, 126.9240), "count": 48, "is_circular": True},
        "3호선": {"start": (37.6789, 127.0456), "end": (37.4650, 127.0200), "count": 34},
        "4호선": {"start": (37.6189, 127.0202), "end": (37.5280, 126.9713), "count": 28},
        "5호선": {"start": (37.5702, 126.9768), "end": (37.5214, 126.9244), "count": 52, "is_circular": True},
        "6호선": {"start": (37.5380, 126.9789), "end": (37.5093, 126.9844), "count": 33, "is_circular": True},
        "7호선": {"start": (37.6689, 127.0319), "end": (37.4860, 127.0114), "count": 52},
        "8호선": {"start": (37.5549, 127.1266), "end": (37.4979, 127.0276), "count": 28},
        "9호선": {"start": (37.5509, 126.8495), "end": (37.5663, 126.9779), "count": 38},
    }

    rows = []
    station_counter = 1

    for line, config in line_configs.items():
        start_lat, start_lon = config["start"]
        end_lat, end_lon = config["end"]
        count = config["count"]
        is_circular = config.get("is_circular", False)

        for i in range(count):
            # 선형 보간
            if count > 1:
                ratio = i / (count - 1)
            else:
                ratio = 0

            lat = start_lat + (end_lat - start_lat) * ratio
            lon = start_lon + (end_lon - start_lon) * ratio

            # 순환선의 경우 약간의 원형 왜곡 추가
            if is_circular:
                angle = (i / count) * 2 * 3.14159
                lat += 0.02 * pd.np.sin(angle) if hasattr(pd, 'np') else 0
                lon += 0.02 * pd.np.cos(angle) if hasattr(pd, 'np') else 0

            station_id = f"STN{station_counter:0>5d}"
            station_name = f"{line[0]}호선-{i+1}"

            rows.append({
                "station_id": station_id,
                "station_name": station_name,
                "line": line,
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "region": "서울",
            })
            station_counter += 1

    return pd.DataFrame(rows)


def make_weather_stations() -> pd.DataFrame:
    """weather_station_id, weather_station_name, latitude, longitude 샘플 (관측소 2개)."""
    rows = [
        {"weather_station_id": "WS001", "weather_station_name": "강남관측소", "latitude": 37.4980, "longitude": 127.0280},
        {"weather_station_id": "WS002", "weather_station_name": "송파관측소", "latitude": 37.5130, "longitude": 127.1000},
    ]
    return pd.DataFrame(rows)


def make_weather_hourly(dates=("2026-07-01", "2026-07-02")) -> pd.DataFrame:
    """weather_station_id, date, hour, temperature, rainfall, humidity, wind_speed 샘플."""
    rows = []
    for ws in ["WS001", "WS002"]:
        for d in dates:
            for h in range(24):
                rows.append(
                    {
                        "weather_station_id": ws,
                        "date": d,
                        "hour": h,
                        "temperature": 25 + (h % 5),
                        "rainfall": 2.5 if h % 6 == 0 else 0.0,
                        "humidity": 60 + (h % 10),
                        "wind_speed": 1.5,
                    }
                )
    return pd.DataFrame(rows)


def make_ridership_hourly(dates=("2026-07-01", "2026-07-02")) -> pd.DataFrame:
    """station_id, date, hour, boarding, alighting 샘플 (20개 주요 역, 현실적 패턴).

    - 주말/평일 구분 (토/일은 출퇴근 피크 약함)
    - 역 규모에 따른 이용량 차등 (강남/서울역은 대역, 소형역은 낮음)
    - 시간대별 자연스러운 변동
    - 강수량과 상관없이 기본값 사용 (대시보드에서 강수 필터링 시 영향 표현)
    """
    # 역별 규모 인자 (강남=1.5, 소형역=0.6)
    station_profiles = {
        "STN001": ("서울역", "1호선", 1.4),      # 대역
        "STN002": ("시청", "1호선", 1.3),        # 대역
        "STN003": ("종로3가", "1호선", 0.9),     # 중형
        "STN004": ("동대문역사문화공원", "1호선", 1.0),
        "STN005": ("강남", "2호선", 1.5),        # 대역
        "STN006": ("교대", "2호선", 1.1),        # 중형
        "STN007": ("홍대입구", "2호선", 1.0),    # 중형
        "STN008": ("신사", "2호선", 0.9),        # 소형
        "STN009": ("잠실", "2호선", 1.2),        # 중형
        "STN010": ("고속터미널", "3호선", 1.3),  # 대역
        "STN011": ("충무로", "3호선", 0.8),      # 소형
        "STN012": ("교대", "3호선", 1.1),        # 중형
        "STN013": ("광화문", "5호선", 1.2),      # 중형
        "STN014": ("여의도", "5호선", 1.1),      # 중형
        "STN015": ("한강진", "6호선", 0.7),      # 소형
        "STN016": ("고속터미널", "7호선", 1.3),  # 대역
        "STN017": ("명동", "4호선", 1.3),        # 대역
        "STN018": ("고속터미널", "9호선", 1.3),  # 대역
        "STN019": ("신논현", "9호선", 0.9),      # 소형
        "STN020": ("삼성", "2호선", 1.2),        # 중형
    }

    def _get_hourly_base(hour: int, is_weekend: bool) -> int:
        """시간대별 기본 탑승객 수 (평일/주말 구분)."""
        if is_weekend:
            # 주말: 오전/오후 비슷, 새벽/밤 낮음
            if 0 <= hour < 6:
                return 30
            elif 10 <= hour < 20:
                return 400
            else:
                return 80
        else:
            # 평일: 출퇴근 피크
            if 0 <= hour < 6:
                return 30
            elif 7 <= hour <= 9:
                return 800  # 출근 피크
            elif 10 <= hour < 17:
                return 300  # 낮시간
            elif 18 <= hour <= 20:
                return 900  # 퇴근 피크
            else:
                return 80

    rows = []
    for sid, (station_name, line, scale) in station_profiles.items():
        for d in dates:
            date_obj = pd.to_datetime(d)
            is_weekend = date_obj.dayofweek >= 5  # 토/일

            for h in range(24):
                base = _get_hourly_base(h, is_weekend)
                # 역 규모 + 약간의 변동성
                boarding = int(base * scale * (0.85 + (hash(f"{sid}{d}{h}") % 100) / 500))
                alighting = int(base * scale * 0.75 * (0.85 + (hash(f"{sid}{d}{h}2") % 100) / 500))

                rows.append(
                    {
                        "station_id": sid,
                        "date": d,
                        "hour": h,
                        "boarding": max(0, boarding),
                        "alighting": max(0, alighting),
                    }
                )
    return pd.DataFrame(rows)


def make_congestion_line_1_to_8() -> pd.DataFrame:
    """서울교통공사(1~8호선) 원본 스타일 샘플 — 컬럼명이 아직 확정 전이라 실제와 다를 수 있다."""
    rows = [
        {"호선": "2호선", "역명": "강남", "요일구분": "평일", "시간대": "07-08", "혼잡도(%)": 120},
        {"호선": "2호선", "역명": "강남", "요일구분": "평일", "시간대": "18-19", "혼잡도(%)": 110},
        {"호선": "2호선", "역명": "잠실", "요일구분": "평일", "시간대": "07-08", "혼잡도(%)": 95},
        {"호선": "3호선", "역명": "교대", "요일구분": "평일", "시간대": "08-09", "혼잡도(%)": 88},
    ]
    return pd.DataFrame(rows)


def make_congestion_line_9() -> pd.DataFrame:
    """서울시메트로9호선 원본 스타일 샘플 — 1~8호선과 컬럼명 체계가 다르다고 가정."""
    rows = [
        {"line": "9호선", "station_name": "고속터미널", "day_type": "weekday", "time_range": "07-08", "congestion_rate": 130},
        {"line": "9호선", "station_name": "신논현", "day_type": "weekday", "time_range": "18-19", "congestion_rate": 105},
    ]
    return pd.DataFrame(rows)
