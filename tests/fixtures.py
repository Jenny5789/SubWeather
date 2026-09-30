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
    """station_id, station_name, line, latitude, longitude, region (20개 주요 역)."""
    # 원래 20개 고정 데이터 (Streamlit Cloud 서버 부하 줄이기)
    rows = [
        {"station_id": "STN001", "station_name": "서울역", "line": "1호선", "latitude": 37.5550, "longitude": 126.9733, "region": "서울"},
        {"station_id": "STN002", "station_name": "시청", "line": "1호선", "latitude": 37.5658, "longitude": 126.9784, "region": "서울"},
        {"station_id": "STN003", "station_name": "종로3가", "line": "1호선", "latitude": 37.5738, "longitude": 126.9920, "region": "서울"},
        {"station_id": "STN004", "station_name": "동대문역사문화공원", "line": "1호선", "latitude": 37.5706, "longitude": 127.0084, "region": "서울"},
        {"station_id": "STN005", "station_name": "강남", "line": "2호선", "latitude": 37.4979, "longitude": 127.0276, "region": "서울"},
        {"station_id": "STN006", "station_name": "교대", "line": "2호선", "latitude": 37.4943, "longitude": 127.0059, "region": "서울"},
        {"station_id": "STN007", "station_name": "홍대입구", "line": "2호선", "latitude": 37.5550, "longitude": 126.9240, "region": "서울"},
        {"station_id": "STN008", "station_name": "신사", "line": "2호선", "latitude": 37.5184, "longitude": 127.0269, "region": "서울"},
        {"station_id": "STN009", "station_name": "잠실", "line": "2호선", "latitude": 37.5115, "longitude": 127.0720, "region": "서울"},
        {"station_id": "STN010", "station_name": "고속터미널", "line": "3호선", "latitude": 37.5007, "longitude": 127.0096, "region": "서울"},
        {"station_id": "STN011", "station_name": "충무로", "line": "3호선", "latitude": 37.5599, "longitude": 126.9968, "region": "서울"},
        {"station_id": "STN012", "station_name": "교대", "line": "3호선", "latitude": 37.4943, "longitude": 127.0059, "region": "서울"},
        {"station_id": "STN013", "station_name": "광화문", "line": "5호선", "latitude": 37.5702, "longitude": 126.9768, "region": "서울"},
        {"station_id": "STN014", "station_name": "여의도", "line": "5호선", "latitude": 37.5214, "longitude": 126.9244, "region": "서울"},
        {"station_id": "STN015", "station_name": "한강진", "line": "6호선", "latitude": 37.5380, "longitude": 126.9789, "region": "서울"},
        {"station_id": "STN016", "station_name": "고속터미널", "line": "7호선", "latitude": 37.5007, "longitude": 127.0096, "region": "서울"},
        {"station_id": "STN017", "station_name": "명동", "line": "4호선", "latitude": 37.5604, "longitude": 126.9856, "region": "서울"},
        {"station_id": "STN018", "station_name": "고속터미널", "line": "9호선", "latitude": 37.5007, "longitude": 127.0096, "region": "서울"},
        {"station_id": "STN019", "station_name": "신논현", "line": "9호선", "latitude": 37.5663, "longitude": 126.9779, "region": "서울"},
        {"station_id": "STN020", "station_name": "삼성", "line": "2호선", "latitude": 37.5074, "longitude": 127.0580, "region": "서울"},
    ]
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
