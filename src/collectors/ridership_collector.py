"""지하철 승하차인원 수집기.

출처: 서울시 열린데이터광장(1~9호선 통합) - CardSubwayTime API.
station_id, boarding, alighting, ridership_total을 시간 단위로 수집한다
(포털 갱신주기는 일 단위라 최신 구간 결측 가능).
결측치는 보간하지 않고 삭제(Phase 2 결측치 처리 전략).

현재: API 인증 문제로 임시로 테스트 fixture 데이터 사용.
실제 API 열리면 collect_ridership_api()로 교체 예정.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import make_ridership_hourly


def collect_ridership(start_date: str, end_date: str) -> pd.DataFrame:
    """역별 시간대별 승하차인원을 수집한다.

    현재: 테스트 fixture 데이터 사용 (실제 API 인증 대기 중).

    start_date, end_date: "YYYYMMDD" 형식 (예: "20260701").
    반환: station_id, date, hour, boarding, alighting 컬럼을 포함하는 DataFrame.
    """
    start = pd.to_datetime(start_date, format="%Y%m%d")
    end = pd.to_datetime(end_date, format="%Y%m%d")

    # 요청 날짜 범위를 문자열 리스트로 변환
    dates = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d").tolist()

    # 테스트 fixture 데이터 생성 (실제 API 연동 전까지 임시)
    df = make_ridership_hourly(dates=tuple(dates))

    # data/raw에 저장 (실제 API 응답 형식과 동일하게)
    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"ridership_{start_date}_{end_date}.json"
    df.to_json(raw_path, orient="records", force_ascii=False)

    return df


def compute_ridership_total(ridership_df: pd.DataFrame) -> pd.DataFrame:
    """boarding + alighting으로 ridership_total 컬럼을 계산해 추가한다.

    ridership_df: boarding, alighting 컬럼을 포함해야 한다.
    """
    return ridership_df.assign(
        ridership_total=ridership_df["boarding"] + ridership_df["alighting"]
    )


def drop_missing_ridership() -> None:
    """승하차인원 결측 레코드를 삭제한다 (보간 시 분석 왜곡 위험이 크다고 판단)."""
    # TODO: dropna 적용
    raise NotImplementedError
