"""SubWeather Streamlit 대시보드 뼈대.

공공데이터포털 API가 아직 열리지 않아, tests/fixtures.py의 더미 데이터 생성 함수와
src/merge.py, src/collectors/*.py의 기존 파이프라인 함수를 그대로 재사용해 화면부터 채운다.
실제 API 연동 시에는 prepare_dummy_data()만 실제 수집 파이프라인 호출로 교체하면 된다.

실행: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from fixtures import (
    make_congestion_line_1_to_8,
    make_congestion_line_9,
    make_ridership_hourly,
    make_station_master,
    make_weather_hourly,
    make_weather_stations,
)
from src.collectors.congestion_collector import merge_congestion_sources
from src.collectors.holiday_collector import flag_vacation_period
from src.collectors.ridership_collector import compute_ridership_total
from src.collectors.station_collector import compute_transfer_yn
from src.merge import (
    TIME_BUCKET_RULES,
    add_time_bucket,
    compute_dispersion_metrics,
    match_nearest_station,
    merge_weather_ridership,
)

# 2025년 하반기 데이터 — 최근 6개월 (실제 기상청 API 데이터)
DEMO_START = "2025-07-01"
DEMO_END = "2025-12-31"
DEMO_DATES = tuple(pd.date_range(DEMO_START, DEMO_END, freq="D").strftime("%Y-%m-%d").tolist())

HEATWAVE_DATE = "2025-08-15"
COLDWAVE_DATE = "2025-12-15"

WEATHER_CONDITION_LABELS = {
    "맑음": "맑은 날 증감률",
    "비": "비 오는 날 증감률",
    "폭염": "폭염일 증감률",
    "한파": "한파일 증감률",
}

# src.merge.TIME_BUCKET_RULES를 그대로 써서 체크박스 라벨을 만든다.
# TIME_BUCKET_RULES가 바뀌면 이 라벨도 자동으로 같이 바뀐다.
TIME_BUCKETS = [label for _, label in TIME_BUCKET_RULES]
TIME_BUCKET_DISPLAY_LABELS = {
    label: f"{label} ({min(hour_range):02d}~{max(hour_range):02d}시)"
    for hour_range, label in TIME_BUCKET_RULES
}


# ---------------------------------------------------------------------------
# 더미 데이터 준비
# ---------------------------------------------------------------------------


def classify_weather_condition(weather_df: pd.DataFrame) -> pd.DataFrame:
    """temperature/rainfall 기준으로 맑음/비/폭염/한파를 분류한다 (데모용 간이 규칙)."""

    def _classify(row) -> str:
        if row["rainfall"] > 0:
            return "비"
        if row["temperature"] >= 33:
            return "폭염"
        if row["temperature"] <= -12:
            return "한파"
        return "맑음"

    return weather_df.assign(weather_condition=weather_df.apply(_classify, axis=1))


@st.cache_data
def prepare_dummy_data() -> dict:
    """더미 데이터를 생성하고 기존 파이프라인 함수(merge.py, collectors)로 가공한다."""
    station_df = compute_transfer_yn(make_station_master())
    weather_station_df = make_weather_stations()
    station_weather_map = match_nearest_station(station_df, weather_station_df)

    ridership_df = compute_ridership_total(make_ridership_hourly(dates=DEMO_DATES))
    ridership_df = add_time_bucket(ridership_df)

    weather_df = make_weather_hourly(dates=DEMO_DATES)
    # 데모용 극단 기온 주입 (폭염/한파 조건이 실제로 존재하도록)
    weather_df.loc[weather_df["date"] == HEATWAVE_DATE, "temperature"] = 34
    weather_df.loc[weather_df["date"] == HEATWAVE_DATE, "rainfall"] = 0.0
    weather_df.loc[weather_df["date"] == COLDWAVE_DATE, "temperature"] = -13
    weather_df.loc[weather_df["date"] == COLDWAVE_DATE, "rainfall"] = 0.0
    weather_df = classify_weather_condition(weather_df)

    merged_df = merge_weather_ridership(ridership_df, weather_df, station_weather_map)
    merged_df = merged_df.merge(
        station_df[["station_id", "station_name", "line", "latitude", "longitude", "region"]],
        on="station_id",
        how="left",
    )
    merged_df = flag_vacation_period(merged_df)

    dispersion_df = compute_dispersion_metrics(merged_df)

    congestion_1_to_8 = make_congestion_line_1_to_8()
    congestion_9 = make_congestion_line_9()
    # 실제 API 컬럼명 확보 전이라 merge_congestion_sources의 rename 매핑은 아직 TODO 상태.
    # (배관이 연결돼 있다는 것만 확인하는 용도로 호출 — 화면에는 아래 별도 정규화 테이블을 쓴다)
    _ = merge_congestion_sources(congestion_1_to_8, congestion_9)

    return {
        "station_df": station_df,
        "merged_df": merged_df,
        "dispersion_df": dispersion_df,
        "congestion_1_to_8": congestion_1_to_8,
        "congestion_9": congestion_9,
    }


# ---------------------------------------------------------------------------
# 화면 렌더링
# ---------------------------------------------------------------------------


def render_sidebar(station_df: pd.DataFrame, merged_df: pd.DataFrame) -> dict:
    st.sidebar.header("필터")

    lines = sorted(station_df["line"].unique())
    selected_lines = st.sidebar.multiselect("노선 선택", lines, default=lines)

    min_date = pd.to_datetime(merged_df["date"]).min().date()
    max_date = pd.to_datetime(merged_df["date"]).max().date()
    date_range = st.sidebar.date_input("기간", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    weather_condition = st.sidebar.selectbox("날씨 조건", list(WEATHER_CONDITION_LABELS.keys()))

    st.sidebar.caption("시간대 묶음")
    selected_buckets = [
        b
        for b in TIME_BUCKETS
        if st.sidebar.checkbox(TIME_BUCKET_DISPLAY_LABELS[b], value=True, key=f"bucket_{b}")
    ]

    st.sidebar.divider()
    if st.sidebar.button("🔄 캐시 비우기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    return {
        "lines": selected_lines,
        "date_range": date_range,
        "weather_condition": weather_condition,
        "time_buckets": selected_buckets,
    }


def apply_filters(merged_df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    df = merged_df[merged_df["line"].isin(filters["lines"])]
    df = df[df["time_bucket"].isin(filters["time_buckets"])]

    date_range = filters["date_range"]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        dates = pd.to_datetime(df["date"])
        df = df[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]

    return df


def render_metric_cards(filtered_df: pd.DataFrame, dispersion_df: pd.DataFrame, filters: dict) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        avg_ridership = filtered_df["ridership_total"].mean()
        st.metric("평균 이용량", f"{avg_ridership:,.0f}명" if pd.notna(avg_ridership) else "N/A")

    with col2:
        condition = filters["weather_condition"]
        cond_mask = filtered_df["weather_condition"] == condition
        cond_avg = filtered_df.loc[cond_mask, "ridership_total"].mean()
        base_avg = filtered_df.loc[~cond_mask, "ridership_total"].mean()
        title = WEATHER_CONDITION_LABELS[condition]
        if pd.notna(cond_avg) and pd.notna(base_avg) and base_avg:
            pct = (cond_avg - base_avg) / base_avg * 100
            st.metric(title, f"{pct:+.1f}%")
        else:
            st.metric(title, "N/A", help="선택한 필터 범위에 해당 날씨 조건 데이터가 없습니다.")

    with col3:
        station_ids = filtered_df["station_id"].unique()
        dates = filtered_df["date"].unique()
        peak_subset = dispersion_df[
            dispersion_df["station_id"].isin(station_ids) & dispersion_df["date"].isin(dates)
        ]
        avg_peak_ratio = peak_subset["peak_ratio"].mean()
        st.metric("출퇴근 쏠림도", f"{avg_peak_ratio:.1%}" if pd.notna(avg_peak_ratio) else "N/A")


def render_map_and_detail(filtered_df: pd.DataFrame, station_df: pd.DataFrame) -> None:
    st.subheader("역별 이용량 지도 (노선별 색상)")

    # 노선별 색상 (서울 지하철 공식 색상)
    LINE_COLORS = {
        "1호선": "#0052CC",
        "2호선": "#00A55D",
        "3호선": "#EF7C1C",
        "4호선": "#5A4F9F",
        "5호선": "#8235B4",
        "6호선": "#944D00",
        "7호선": "#5F9E42",
        "8호선": "#EC0047",
        "9호선": "#FFC400",
    }

    agg = (
        filtered_df.groupby(["station_id", "station_name", "latitude", "longitude", "line"])["ridership_total"]
        .sum()
        .reset_index()
    )

    if agg.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    min_val, max_val = agg["ridership_total"].min(), agg["ridership_total"].max()
    value_range = max_val - min_val or 1  # 전부 같은 값일 때 0으로 나누기 방지

    fmap = folium.Map(location=[station_df["latitude"].mean(), station_df["longitude"].mean()], zoom_start=11)
    fmap.fit_bounds(
        [[station_df["latitude"].min(), station_df["longitude"].min()], [station_df["latitude"].max(), station_df["longitude"].max()]],
        padding=(30, 30),
    )

    # 모든 역 정보 (전체 276개 역)
    all_stations = station_df[["station_id", "station_name", "latitude", "longitude", "line"]]

    # 노선별로 역을 연결하는 선 그리기 (모든 역 기준)
    import math
    for line in all_stations["line"].unique():
        line_stations = all_stations[all_stations["line"] == line].copy()
        if len(line_stations) > 1:
            # 중심점 계산
            center_lat = line_stations["latitude"].mean()
            center_lon = line_stations["longitude"].mean()

            # 중심점 기준 각도로 정렬 (순환선 포함)
            def calc_angle(lat, lon):
                return math.atan2(lon - center_lon, lat - center_lat)

            line_stations["angle"] = line_stations.apply(lambda r: calc_angle(r["latitude"], r["longitude"]), axis=1)
            line_stations = line_stations.sort_values("angle")

            # 좌표 리스트 생성 (순환선은 처음 점을 끝에 추가해서 폐곡선)
            coords = list(zip(line_stations["latitude"], line_stations["longitude"]))
            if line in ["2호선", "5호선", "6호선"]:  # 순환선
                coords.append(coords[0])

            line_color = LINE_COLORS.get(line, "#666666")
            folium.PolyLine(
                locations=coords,
                color=line_color,
                weight=3,
                opacity=0.6,
                dash_array="5, 5",
            ).add_to(fmap)

    # 먼저 데이터 없는 역을 작은 점으로 표시
    data_station_ids = set(agg["station_id"].unique())
    for _, row in all_stations.iterrows():
        if row["station_id"] not in data_station_ids:
            line_color = LINE_COLORS.get(row["line"], "#666666")
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=2,
                color=line_color,
                fill=True,
                fill_color=line_color,
                fill_opacity=0.3,
                weight=1,
                tooltip=f"{row['station_name']} ({row['line']})",
            ).add_to(fmap)

    # 데이터 있는 역을 큰 버블로 표시
    for _, row in agg.iterrows():
        ratio = (row["ridership_total"] - min_val) / value_range
        radius = 8 + ratio * 20  # 이용량이 많을수록 큰 마커
        line_color = LINE_COLORS.get(row["line"], "#666666")  # 노선별 색상
        # 이용량에 따라 투명도 조정 (많을수록 진함)
        opacity = 0.5 + ratio * 0.5
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius,
            color=line_color,
            fill=True,
            fill_color=line_color,
            fill_opacity=opacity,
            weight=2,
            tooltip=f"{row['station_name']} ({row['line']}) - {row['ridership_total']:,}명",
        ).add_to(fmap)

    map_state = st_folium(fmap, use_container_width=True, height=450, returned_objects=["last_object_clicked"])

    clicked = map_state.get("last_object_clicked") if map_state else None
    if clicked and clicked.get("lat") is not None:
        dist = (agg["latitude"] - clicked["lat"]).abs() + (agg["longitude"] - clicked["lng"]).abs()
        nearest_station = agg.loc[dist.idxmin()]
        st.session_state["selected_station_id"] = nearest_station["station_id"]

    st.markdown("---")
    selected_station_id = st.session_state.get("selected_station_id")

    if not selected_station_id:
        st.info("지도에서 역을 클릭하면 시간대별 이용량이 표시됩니다.")
        return

    station_detail = filtered_df[filtered_df["station_id"] == selected_station_id]
    if station_detail.empty:
        st.info("지도에서 역을 클릭하면 시간대별 이용량이 표시됩니다.")
        return

    station_name = station_detail["station_name"].iloc[0]
    st.markdown(f"**{station_name}** 시간대별 이용량")
    line_fig = px.line(
        station_detail.sort_values("hour"),
        x="hour",
        y="ridership_total",
        color="date",
        markers=True,
    )
    st.plotly_chart(line_fig, use_container_width=True)


def render_rainfall_vs_ridership_chart(filtered_df: pd.DataFrame) -> None:
    st.subheader("강수량 vs 이용량")

    # 날짜별로 강수량(최댓값)과 이용량(합계) 집계
    summary = (
        filtered_df.groupby("date")
        .agg({"rainfall": "max", "ridership_total": "sum"})
        .reset_index()
    )

    if summary.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    # 강수 여부로 구분
    summary["rain_category"] = summary["rainfall"].apply(lambda x: "강수 있음" if x > 0 else "강수 없음")

    # 산점도
    fig = px.scatter(
        summary,
        x="rainfall",
        y="ridership_total",
        color="rain_category",
        title="날짜별 강수량과 이용량",
        labels={"rainfall": "강수량 (mm)", "ridership_total": "총 이용량 (명)"},
        hover_data=["date"],
    )
    st.plotly_chart(fig, use_container_width=True)

    # 강수 여부별 평균 비교
    rain_comparison = summary.groupby("rain_category")["ridership_total"].agg(["mean", "count"]).reset_index()
    col1, col2 = st.columns(2)
    with col1:
        rain_avg = rain_comparison.loc[rain_comparison["rain_category"] == "강수 있음", "mean"].values
        st.metric(
            "강수 있는 날 평균 이용량",
            f"{rain_avg[0]:,.0f}명" if len(rain_avg) > 0 else "데이터 없음",
        )
    with col2:
        no_rain_avg = rain_comparison.loc[rain_comparison["rain_category"] == "강수 없음", "mean"].values
        st.metric(
            "강수 없는 날 평균 이용량",
            f"{no_rain_avg[0]:,.0f}명" if len(no_rain_avg) > 0 else "데이터 없음",
        )


def render_line_ridership_chart(filtered_df: pd.DataFrame) -> None:
    st.subheader("노선별 이용량 비교")

    summary = filtered_df.groupby("line")["ridership_total"].sum().reset_index().sort_values("ridership_total", ascending=False)

    if summary.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    fig = px.bar(
        summary,
        x="line",
        y="ridership_total",
        color="ridership_total",
        color_continuous_scale="Viridis",
        labels={"ridership_total": "총 이용량 (명)", "line": "노선"},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_top_bottom_stations(filtered_df: pd.DataFrame) -> None:
    st.subheader("역 이용량 순위 (Top 10 / Bottom 10)")

    agg = filtered_df.groupby(["station_id", "station_name", "line"])["ridership_total"].sum().reset_index()

    if agg.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.caption("🏆 가장 붐비는 역 Top 10")
        top10 = agg.nlargest(10, "ridership_total")[["station_name", "line", "ridership_total"]]
        st.dataframe(
            top10.rename(columns={"station_name": "역명", "line": "노선", "ridership_total": "총 이용량"}).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.caption("📉 가장 한산한 역 Bottom 10")
        bottom10 = agg.nsmallest(10, "ridership_total")[["station_name", "line", "ridership_total"]]
        st.dataframe(
            bottom10.rename(columns={"station_name": "역명", "line": "노선", "ridership_total": "총 이용량"}).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )


def render_weekday_vs_weekend(filtered_df: pd.DataFrame) -> None:
    st.subheader("주말 vs 평일 이용 패턴")

    df = filtered_df.copy()
    df["date_obj"] = pd.to_datetime(df["date"])
    df["day_type"] = df["date_obj"].dt.day_name()
    df["is_weekend"] = df["date_obj"].dt.dayofweek >= 5

    # 요일별 평균
    hourly_pattern = df.groupby(["hour", "is_weekend"])["ridership_total"].mean().reset_index()
    hourly_pattern["day_type"] = hourly_pattern["is_weekend"].apply(lambda x: "주말" if x else "평일")

    if hourly_pattern.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    fig = px.line(
        hourly_pattern,
        x="hour",
        y="ridership_total",
        color="day_type",
        markers=True,
        labels={"hour": "시간대", "ridership_total": "평균 이용량 (명)", "day_type": ""},
    )
    st.plotly_chart(fig, use_container_width=True)

    # 통계
    col1, col2 = st.columns(2)
    weekday_avg = df[~df["is_weekend"]]["ridership_total"].mean()
    weekend_avg = df[df["is_weekend"]]["ridership_total"].mean()

    with col1:
        st.metric("평일 평균 이용량", f"{weekday_avg:,.0f}명" if pd.notna(weekday_avg) else "N/A")
    with col2:
        diff_pct = (weekend_avg - weekday_avg) / weekday_avg * 100 if weekday_avg else 0
        st.metric("주말 vs 평일", f"{diff_pct:+.1f}%")


def render_vacation_chart(filtered_df: pd.DataFrame) -> None:
    st.subheader("휴가철 vs 평시 이용량 (노선별)")

    df = filtered_df.assign(
        period_label=filtered_df.apply(
            lambda r: "휴가철" if (r["is_summer_vacation"] or r["is_winter_vacation"]) else "평시",
            axis=1,
        )
    )
    summary = df.groupby(["line", "period_label"])["ridership_total"].mean().reset_index()

    if summary.empty:
        st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
        return

    fig = px.bar(
        summary,
        x="line",
        y="ridership_total",
        color="period_label",
        barmode="group",
        category_orders={"line": sorted(summary["line"].unique())},
        labels={"ridership_total": "평균 이용량", "line": "노선", "period_label": ""},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_congestion_expander(congestion_1_to_8: pd.DataFrame, congestion_9: pd.DataFrame) -> None:
    with st.expander("참고 지표 — 혼잡도", expanded=False):
        st.caption("혼잡도는 요일유형 평균값으로, 날짜와 정식 매칭되지 않는 참고용 부가 지표입니다.")

        # 실제 API 원본 컬럼명 확정 전까지는 congestion_collector.merge_congestion_sources의
        # rename 매핑이 비어 있어(TODO), 화면 표시용으로 여기서만 임시로 컬럼명을 통일한다.
        normalized_1_to_8 = congestion_1_to_8.rename(
            columns={"요일구분": "weekday_type", "시간대": "time_range", "혼잡도(%)": "congestion_pct"}
        )[["weekday_type", "time_range", "congestion_pct"]]
        normalized_9 = congestion_9.rename(
            columns={"day_type": "weekday_type", "time_range": "time_range", "congestion_rate": "congestion_pct"}
        )[["weekday_type", "time_range", "congestion_pct"]]
        normalized_9["weekday_type"] = normalized_9["weekday_type"].replace({"weekday": "평일"})

        combined = pd.concat([normalized_1_to_8, normalized_9], ignore_index=True)
        pivot = combined.pivot_table(index="weekday_type", columns="time_range", values="congestion_pct", aggfunc="mean")
        st.dataframe(pivot)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="SubWeather 대시보드", layout="wide")
    st.title("SubWeather — 날씨 기반 서울 지하철 이용 패턴")
    st.caption("2025년 7월~12월 데이터 기반 분석 (실제 기상청 데이터 추후 연동)")

    data = prepare_dummy_data()
    filters = render_sidebar(data["station_df"], data["merged_df"])
    filtered_df = apply_filters(data["merged_df"], filters)

    # 탭 기반 대시보드 레이아웃
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 개요",
        "🌧️ 강수량 분석",
        "🚆 노선/역 분석",
        "📅 시간/요일 분석",
        "🎊 특수 분석"
    ])

    with tab1:
        st.header("대시보드 개요")
        render_metric_cards(filtered_df, data["dispersion_df"], filters)
        st.divider()
        render_map_and_detail(filtered_df, data["station_df"])

    with tab2:
        st.header("강수량 vs 이용량")
        render_rainfall_vs_ridership_chart(filtered_df)

    with tab3:
        st.header("노선별 및 역별 분석")
        col1, col2 = st.columns([1, 1])
        with col1:
            render_line_ridership_chart(filtered_df)
        with col2:
            st.subheader("역 순위 통계")
            render_top_bottom_stations(filtered_df)

    with tab4:
        st.header("시간대 및 요일별 분석")
        render_weekday_vs_weekend(filtered_df)

    with tab5:
        st.header("특수 분석")
        col1, col2 = st.columns([1, 1])
        with col1:
            render_vacation_chart(filtered_df)
        with col2:
            render_congestion_expander(data["congestion_1_to_8"], data["congestion_9"])


if __name__ == "__main__":
    main()
