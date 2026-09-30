"""역-관측소 등 서로 다른 출처 데이터를 병합하는 로직.

Phase 2 병합 전략: 역 좌표 기준 최근접 기상 관측소(Haversine 거리) 매칭,
시간대 묶음(time_bucket) 파생, 날씨-승하차인원 병합, 분산 지표 계산 등
여러 collector가 공통으로 쓰는 병합/파생 함수를 모아둔다.
"""

import math

import pandas as pd


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 거리(km)를 Haversine 공식으로 계산한다."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def match_nearest_station(
    station_df: pd.DataFrame, weather_station_df: pd.DataFrame
) -> pd.DataFrame:
    """역 좌표 기준 최근접 기상 관측소를 Haversine 거리로 매칭한다.

    station_df: station_id, latitude, longitude 컬럼 포함
    weather_station_df: weather_station_id, latitude, longitude 컬럼 포함
    반환: station_id, weather_station_id, distance_km
    """
    matches = []
    for _, station in station_df.iterrows():
        best_id = None
        best_dist = float("inf")
        for _, ws in weather_station_df.iterrows():
            dist = _haversine_km(
                station["latitude"], station["longitude"], ws["latitude"], ws["longitude"]
            )
            if dist < best_dist:
                best_dist = dist
                best_id = ws["weather_station_id"]
        matches.append(
            {"station_id": station["station_id"], "weather_station_id": best_id, "distance_km": best_dist}
        )
    return pd.DataFrame(matches)


# hour(0~23) -> time_bucket 매핑 규칙 (Phase 1 스키마 정의 기준)
TIME_BUCKET_RULES = [
    (range(0, 6), "새벽"),
    (range(6, 10), "출근"),
    (range(10, 17), "낮"),
    (range(17, 21), "퇴근"),
    (range(21, 24), "저녁"),
]


def add_time_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """hour 컬럼을 기준으로 time_bucket(새벽/출근/낮/퇴근/저녁)을 부여한다."""

    def _bucket(hour: int) -> str:
        for hour_range, label in TIME_BUCKET_RULES:
            if hour in hour_range:
                return label
        raise ValueError(f"unexpected hour value: {hour}")

    return df.assign(time_bucket=df["hour"].map(_bucket))


def merge_weather_ridership(
    ridership_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    station_weather_map_df: pd.DataFrame,
) -> pd.DataFrame:
    """station_id + datetime(date+hour) 기준으로 승하차인원과 날씨를 병합한다.

    station_weather_map_df: match_nearest_station()의 반환값(station_id, weather_station_id).
    """
    merged = ridership_df.merge(
        station_weather_map_df[["station_id", "weather_station_id"]], on="station_id", how="left"
    )
    merged = merged.merge(weather_df, on=["weather_station_id", "date", "hour"], how="left")
    return merged


def compute_dispersion_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """station_id+date 단위로 hourly_std(시간대 표준편차)와 peak_ratio(출퇴근 비중)를 계산한다.

    df: station_id, date, ridership_total, time_bucket 컬럼 포함 필요.
    """

    def _agg(group: pd.DataFrame) -> pd.Series:
        total = group["ridership_total"].sum()
        peak = group.loc[group["time_bucket"].isin(["출근", "퇴근"]), "ridership_total"].sum()
        return pd.Series(
            {
                "hourly_std": group["ridership_total"].std(ddof=0),
                "peak_ratio": (peak / total) if total else float("nan"),
            }
        )

    return df.groupby(["station_id", "date"]).apply(_agg, include_groups=False).reset_index()
