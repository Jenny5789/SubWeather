"""공휴일 및 방학 플래그 수집기.

출처: 특일정보 API(한국천문연구원_특일 정보, data.go.kr) + 방학은 서울시교육청 공지 근사치를 수동 하드코딩.
holiday, is_long_holiday(연속 공휴일 탐지), is_summer_vacation, is_winter_vacation을 만든다.

인증키는 .env의 DATA_GO_KR_SERVICE_KEY를 사용한다 (레포에는 올리지 않음, .gitignore 처리됨).
"""

from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
HOLIDAY_ENDPOINT = "https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"


def _load_service_key() -> str:
    """.env에서 DATA_GO_KR_SERVICE_KEY를 읽는다.

    data.go.kr이 발급하는 키는 이미 URL-인코딩된 "인증키(Encoding)" 형태(끝이 %3D%3D 등)라서,
    requests의 params=에 그대로 넣으면 다시 인코딩되어 깨진다 (실제로 403
    SERVICE_KEY_IS_NOT_REGISTERED_ERROR로 확인함). 그래서 여기서 미리 디코딩해서 반환한다.
    """
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env 파일이 없습니다: {env_path} (DATA_GO_KR_SERVICE_KEY=... 형식으로 만들어주세요)")

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "DATA_GO_KR_SERVICE_KEY":
            return unquote(value.strip().strip('"').strip("'"))

    raise ValueError("DATA_GO_KR_SERVICE_KEY를 .env에서 찾지 못했습니다.")


def collect_holidays(year: int) -> pd.DataFrame:
    """특일정보 API(getRestDeInfo)로 해당 연도의 공휴일 목록을 수집해 data/raw에 저장하고 반환한다.

    solMonth를 생략하면 연도 전체 공휴일을 한 번의 호출로 받을 수 있다 (실제 요청으로 확인함).
    반환 컬럼: date(YYYY-MM-DD), holiday_name, is_holiday.
    """
    service_key = _load_service_key()
    response = requests.get(
        HOLIDAY_ENDPOINT,
        params={"serviceKey": service_key, "solYear": year, "numOfRows": 100, "_type": "json"},
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    payload = response.json()

    header = payload["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"특일정보 API 오류: {header['resultCode']} {header['resultMsg']}")

    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"holidays_{year}.json").write_text(response.text, encoding="utf-8")

    items = payload["response"]["body"]["items"]
    items = items["item"] if items else []
    if isinstance(items, dict):  # 공휴일이 1건뿐이면 API가 리스트가 아니라 dict 하나로 내려준다
        items = [items]

    rows = [
        {
            "date": pd.to_datetime(str(item["locdate"]), format="%Y%m%d").strftime("%Y-%m-%d"),
            "holiday_name": item["dateName"],
            "is_holiday": item["isHoliday"] == "Y",
        }
        for item in items
    ]
    return pd.DataFrame(rows)


def flag_long_holidays(holidays_df: pd.DataFrame) -> pd.DataFrame:
    """연속된 공휴일(명절 연휴 등)을 탐지해 is_long_holiday 플래그를 만든다.

    holidays_df: collect_holidays()의 반환값처럼 date 컬럼을 포함해야 한다.
    하루짜리 공휴일에 둘러싸인 날(예: 설날 연휴 3일)이 아니라, 날짜가 연속되는 공휴일이
    2일 이상 이어지는 구간을 전부 is_long_holiday=True로 표시한다.
    """
    df = holidays_df.sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(df["date"])

    # 하루 간격(1일)으로 이어지는 공휴일끼리 같은 그룹으로 묶는다
    is_new_group = dates.diff().dt.days != 1
    group_id = is_new_group.cumsum()
    group_size = df.groupby(group_id)["date"].transform("size")

    return df.assign(is_long_holiday=group_size >= 2)


# 방학 기간은 별도 공공 API가 없어 통상적인 서울 초중고 방학 시기를 참고해 근사한 값
VACATION_PERIODS: dict = {
    "2026_summer": ("2026-07-13", "2026-08-17"),
    "2026_winter": ("2026-12-21", "2027-02-01"),
}


def flag_vacation_period(df: pd.DataFrame) -> pd.DataFrame:
    """VACATION_PERIODS 테이블을 기준으로 is_summer_vacation/is_winter_vacation을 부여한다.

    df: date 컬럼(문자열 "YYYY-MM-DD" 또는 datetime)을 포함해야 한다.
    VACATION_PERIODS의 키에 "summer"가 들어있으면 여름방학, "winter"가 들어있으면 겨울방학 기간으로 취급한다.
    """
    date_series = pd.to_datetime(df["date"])

    is_summer = pd.Series(False, index=df.index)
    is_winter = pd.Series(False, index=df.index)

    for period_name, (start, end) in VACATION_PERIODS.items():
        in_range = date_series.between(pd.Timestamp(start), pd.Timestamp(end))
        if "summer" in period_name:
            is_summer |= in_range
        elif "winter" in period_name:
            is_winter |= in_range

    return df.assign(is_summer_vacation=is_summer, is_winter_vacation=is_winter)
