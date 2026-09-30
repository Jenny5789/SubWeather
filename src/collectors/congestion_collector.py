"""혼잡도(부가 지표) 수집기.

출처: 서울교통공사(1~8호선) + 서울시메트로9호선(주)(9호선), 두 출처를 별도 파일로 수집한다.
메인 분석 테이블과는 station_id + weekday_type + time_bucket 기준으로 느슨하게 연결하는
참고용 lookup 테이블이며, 정식 조인 대상이 아니다. 9호선은 컬럼명·형식 통일 전처리가 필수.
"""

import pandas as pd


def collect_congestion_line_1_to_8() -> None:
    """서울교통공사 1~8호선 혼잡도 데이터를 수집한다(분기 단위 갱신)."""
    # TODO: 서울교통공사 공개 파일/API 확인
    raise NotImplementedError


def collect_congestion_line_9() -> None:
    """서울시메트로9호선(주) 9호선 혼잡도 데이터를 수집한다."""
    # TODO: 서울시메트로9호선 공개 파일/API 확인, 1~8호선과 컬럼명 통일 필요
    raise NotImplementedError


def merge_congestion_sources(
    df_line_1_to_8: pd.DataFrame, df_line_9: pd.DataFrame
) -> pd.DataFrame:
    """1~8호선/9호선 혼잡도 DataFrame의 컬럼명을 통일한 뒤 하나로 합친다.

    두 출처의 원본 컬럼명이 서로 다르므로, 실제 데이터 확보 후 아래 매핑을 채워야 한다.
    """
    # TODO: 서울교통공사(1~8호선) 원본 컬럼명 -> 공통 스키마 매핑 확정
    #   예: {"호선": "line", "역명": "station_name", "요일구분": "weekday_type", ...}
    rename_1_to_8 = {}

    # TODO: 서울시메트로9호선 원본 컬럼명 -> 공통 스키마 매핑 확정 (1~8호선과 동일 스키마로)
    rename_9 = {}

    df_line_1_to_8 = df_line_1_to_8.rename(columns=rename_1_to_8)
    df_line_9 = df_line_9.rename(columns=rename_9)

    # TODO: rename 확정 후 두 DataFrame의 최종 컬럼 구성이 일치하는지 검증
    return pd.concat([df_line_1_to_8, df_line_9], ignore_index=True)
