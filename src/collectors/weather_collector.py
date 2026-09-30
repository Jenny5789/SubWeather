"""기상 시간자료 수집기.

출처: 기상청 ASOS(우선) / AWS 시간자료 API (기상청 API 허브, kma_sfctm3.php - 기간 조회).
temperature, rainfall, wind_speed, humidity (+ 선택: pressure, snowfall, visibility)를 시간 단위로 수집한다.

인증키는 .env의 KMA_API_HUB_KEY를 사용한다 (레포에는 올리지 않음, .gitignore 처리됨).
"""

from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
# kma_sfctm2.php는 tm(단일 시각)만 받는 point-in-time 조회 API였다 (실제 요청으로 확인).
# kma_sfctm3.php는 tm1/tm2로 기간을 한 번에 조회할 수 있는 별도 엔드포인트다.
ASOS_ENDPOINT = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
SEOUL_STN = 108  # 기상청 지점번호: 108 = 서울
MAX_HOURS_PER_CALL = 720  # kma_sfctm3.php는 tm2 기준 최대 720시간(30일) 전까지만 한 번에 조회 가능

# kma_sfctm3.php 응답의 46개 컬럼 (순서 고정, 공백 구분) — kma_sfctm2.php와 동일한 포맷.
ASOS_COLUMNS = [
    "TM", "STN", "WD", "WS", "GST_WD", "GST_WS", "GST_TM", "PA", "PS", "PT",
    "PR", "TA", "TD", "HM", "PV", "RN", "RN_DAY", "RN_JUN", "RN_INT", "SD_HR3",
    "SD_DAY", "SD_TOT", "WC", "WP", "WW", "CA_TOT", "CA_MID", "CH_MIN", "CT", "CT_TOP",
    "CT_MID", "CT_LOW", "VS", "SS", "SI", "ST_GD", "TS", "TE_005", "TE_01", "TE_02",
    "TE_03", "ST_SEA", "WH", "BF", "IR", "IX",
]

# 우리 스키마로 쓸 컬럼만 골라서 rename
ASOS_RENAME_MAP = {
    "TM": "datetime_raw",
    "STN": "stn",
    "TA": "temperature",
    "RN": "rainfall",
    "WS": "wind_speed",
    "HM": "humidity",
    "PA": "pressure",
    "VS": "visibility",
}

# 결측을 나타내는 특수값 (빈 칸이 아니라 이 값들로 채워져 내려온다)
MISSING_VALUES = {"-9", "-9.0", "-9.00", "-"}


def _load_api_key() -> str:
    """.env에서 KMA_API_HUB_KEY를 읽는다 (python-dotenv 없이 직접 파싱)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env 파일이 없습니다: {env_path} (KMA_API_HUB_KEY=... 형식으로 만들어주세요)")

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "KMA_API_HUB_KEY":
            return value.strip().strip('"').strip("'")

    raise ValueError("KMA_API_HUB_KEY를 .env에서 찾지 못했습니다.")


def _parse_asos_text(raw_text: str) -> pd.DataFrame:

    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != len(ASOS_COLUMNS):
            continue  
        rows.append(fields)

    return pd.DataFrame(rows, columns=ASOS_COLUMNS)


def _resolve_rainfall(raw_df: pd.DataFrame) -> pd.Series:
    """RN(강수량)의 -9는 다른 컬럼과 달리 "무강수"와 "진짜 결측"이 섞여 있다.

    응답 도움말(help=1)의 45번 컬럼 IR 설명(Code 1819)에 그 구분 기준이 명시되어 있다:
      1(Sec1에 포함), 2(Sec3에 포함) → 실제 관측값이 있어야 하는 경우
      3(무강수) → 문자 그대로 비가 안 온 것 → RN의 -9는 0.0으로 채운다
      4(결측)   → 진짜 관측 결측 → RN의 -9는 NaN으로 남긴다
    """
    rn_raw = raw_df["RN"]
    missing_mask = rn_raw.isin(MISSING_VALUES)

    rn_values = pd.to_numeric(rn_raw.mask(missing_mask), errors="coerce")

    no_rain_mask = missing_mask & (raw_df["IR"] == "3")
    rn_values = rn_values.where(~no_rain_mask, 0.0)
    return rn_values


def _clean_and_reshape(raw_df: pd.DataFrame) -> pd.DataFrame:
    """결측 특수값을 NaN으로 바꾸고, 우리 스키마 컬럼으로 rename + datetime 파생.

    rainfall(RN)만 IR 플래그를 참고해 별도 처리하고(_resolve_rainfall), 나머지 컬럼의
    -9/-9.0/-9.00/- 는 전부 진짜 결측으로 보고 그대로 NaN 처리한다.
    """
    rainfall = _resolve_rainfall(raw_df)

    df = raw_df.drop(columns=["RN"]).replace(list(MISSING_VALUES), pd.NA)
    df["RN"] = rainfall

    df = df.rename(columns=ASOS_RENAME_MAP)
    keep_cols = list(ASOS_RENAME_MAP.values())
    df = df[keep_cols]

    numeric_cols = ["temperature", "wind_speed", "humidity", "pressure", "visibility"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["datetime_raw"] = df["datetime_raw"].astype(str)
    dt = pd.to_datetime(df["datetime_raw"], format="%Y%m%d%H%M")
    df["date"] = dt.dt.strftime("%Y-%m-%d")
    df["hour"] = dt.dt.hour

    # TODO(preprocess.py의 fill_weather_gaps에서 감안): rainfall(RN)은 계절별로 결측 특성이 다르다.
    #   11~3월(동절기)에는 3시간 단위로만 값이 채워지고 나머지 시간은 결측으로 내려오는 경우가 있어서,
    #   단순 선형보간을 그대로 적용하면 왜곡될 수 있다. 겨울철 rainfall은 3시간 단위 관측 주기를
    #   고려한 보간/대체 로직이 필요할 수 있다.
    return df


def _fetch_range(tm1: str, tm2: str, stn: int, auth_key: str) -> str:
    """kma_sfctm3.php에 tm1~tm2 기간을 한 번에 요청한다 (최대 720시간 분량)."""
    params = {"tm1": tm1, "tm2": tm2, "stn": stn, "help": 1, "authKey": auth_key}
    response = requests.get(ASOS_ENDPOINT, params=params, timeout=60)
    response.raise_for_status()
    return response.text


def _split_into_chunks(start: pd.Timestamp, end: pd.Timestamp, max_hours: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """start~end 구간을 max_hours 시간 이하 단위로 쪼갠다 (끝 경계가 겹치지 않게)."""
    chunks = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + pd.Timedelta(hours=max_hours - 1), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + pd.Timedelta(hours=1)
    return chunks


def collect_asos_hourly(start_date: str, end_date: str, stn: int = SEOUL_STN) -> pd.DataFrame:
    """기상청 ASOS 시간자료를 기간 단위로 호출해 data/raw에 저장하고 DataFrame으로 반환한다.

    kma_sfctm3.php는 tm1(시작)~tm2(종료) 기간을 한 번에 조회할 수 있지만, tm2 기준
    최대 720시간(30일) 전까지만 한 번의 호출로 받을 수 있다 (기상청 API 허브 사용 안내 확인,
    https://apihub.kma.go.kr 참고). 720시간을 넘는 기간(예: 3개월치)을 요청하면
    자동으로 720시간 이하 구간으로 나눠서 여러 번 호출한 뒤 하나로 합친다.

    start_date, end_date: "YYYYMMDDHHMI" 형식 (예: "202607010000").
    """
    auth_key = _load_api_key()
    start = pd.to_datetime(start_date, format="%Y%m%d%H%M")
    end = pd.to_datetime(end_date, format="%Y%m%d%H%M")
    chunks = _split_into_chunks(start, end, MAX_HOURS_PER_CALL)

    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_texts = []
    for chunk_start, chunk_end in chunks:
        tm1 = chunk_start.strftime("%Y%m%d%H%M")
        tm2 = chunk_end.strftime("%Y%m%d%H%M")
        raw_text = _fetch_range(tm1, tm2, stn, auth_key)
        raw_texts.append(raw_text)

    combined_raw_text = "\n".join(raw_texts)
    raw_path = raw_dir / f"asos_{stn}_{start_date}_{end_date}.txt"
    raw_path.write_text(combined_raw_text, encoding="utf-8")

    raw_df = _parse_asos_text(combined_raw_text)
    return _clean_and_reshape(raw_df)


def collect_aws_hourly(start_date: str, end_date: str) -> None:
    """ASOS 결측 구간을 보완하기 위한 AWS 시간자료 수집."""
    # TODO: ASOS와 동일 스키마로 정리
    raise NotImplementedError
