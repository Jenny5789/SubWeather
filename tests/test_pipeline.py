"""API 없이 가짜 데이터로 collector/merge 파이프라인을 눈으로 검증하는 스크립트.

pytest 형식이 아니라, 각 단계 결과를 print로 찍어 컬럼/값이 예상대로인지 육안 확인하는 용도.
실행: py tests/test_pipeline.py  (프로젝트 루트에서)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.merge import (
    add_time_bucket,
    compute_dispersion_metrics,
    match_nearest_station,
    merge_weather_ridership,
)
from src.collectors.station_collector import compute_transfer_yn
from src.collectors.ridership_collector import compute_ridership_total
from src.collectors.congestion_collector import merge_congestion_sources

from fixtures import (
    make_congestion_line_1_to_8,
    make_congestion_line_9,
    make_ridership_hourly,
    make_station_master,
    make_weather_hourly,
    make_weather_stations,
)


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 160)

    section("1. station_collector.compute_transfer_yn")
    station_df = make_station_master()
    station_df = compute_transfer_yn(station_df)
    print(station_df)

    section("2. merge.match_nearest_station")
    weather_station_df = make_weather_stations()
    station_weather_map = match_nearest_station(station_df, weather_station_df)
    print(station_weather_map)

    section("3. ridership_collector.compute_ridership_total")
    ridership_df = make_ridership_hourly()
    ridership_df = compute_ridership_total(ridership_df)
    print(ridership_df.head(10))

    section("4. merge.add_time_bucket")
    ridership_df = add_time_bucket(ridership_df)
    print(ridership_df.head(10))

    section("5. merge.merge_weather_ridership")
    weather_df = make_weather_hourly()
    merged = merge_weather_ridership(ridership_df, weather_df, station_weather_map)
    print(merged.head(10))
    print("\nNull 개수:")
    print(merged.isna().sum())

    section("6. merge.compute_dispersion_metrics")
    dispersion = compute_dispersion_metrics(merged)
    print(dispersion)

    section("7. congestion_collector.merge_congestion_sources")
    df_1_to_8 = make_congestion_line_1_to_8()
    df_9 = make_congestion_line_9()
    merged_congestion = merge_congestion_sources(df_1_to_8, df_9)
    print(merged_congestion)


if __name__ == "__main__":
    main()
