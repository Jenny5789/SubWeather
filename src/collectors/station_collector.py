"""역 좌표 마스터 데이터 수집기.

출처: 서울교통공사 역사좌표 + 국토교통부 전국도시철도역사정보표준데이터(9호선 1단계 보완).
station_name, line, transfer_yn, latitude, longitude, region(자치구)을 만든다.
가장 먼저 수집해야 하는 정적 마스터 데이터 — 날씨 관측소 매칭 및 지도 시각화의 기준이 된다.
"""

import pandas as pd


def collect_station_master() -> None:
    """역 좌표 마스터 원본 파일/API 응답을 data/raw에 저장한다."""
    # TODO: 서울교통공사 역사좌표 파일 다운로드 or API 호출
    # TODO: 국토교통부 전국도시철도역사정보표준데이터로 9호선 보완
    raise NotImplementedError


def build_station_master() -> None:
    """두 출처를 병합해 station_id, line, transfer_yn, lat/lon, region 스키마로 정리한다."""
    # 결정: station_id는 station_name + line 조합으로 두 출처를 매칭해 생성한다.
    #   (서울로 스코프를 한정했으므로 역명 중복으로 인한 오매칭 위험이 낮다고 판단)
    # TODO: 위 매칭 규칙으로 실제 station_id 생성 구현 (API 데이터 확보 후)
    # TODO: reverse geocoding으로 region(자치구) 산출
    raise NotImplementedError


def compute_transfer_yn(station_df: pd.DataFrame) -> pd.DataFrame:
    """같은 station_name이 여러 line에 나오면 환승역(transfer_yn=Y)으로 판단한다.

    station_df: station_name, line 컬럼을 포함해야 한다.
    반환: station_df에 transfer_yn(Y/N) 컬럼을 추가한 DataFrame.
    """
    line_count = station_df.groupby("station_name")["line"].transform("nunique")
    return station_df.assign(transfer_yn=(line_count > 1).map({True: "Y", False: "N"}))