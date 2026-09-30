# WeatherSubwayTraffic

날씨 기반 서울 지하철(1~9호선) 이용 패턴 분석 — 실제 기상 조건이 역별·시간대별 이용률에 미치는 영향을 분석하는 데이터 분석 포트폴리오 프로젝트입니다.

## 핵심 질문
- 강수량이 많을수록 지하철 이용률이 줄어드는가?
- 폭염/한파 등 극단적 기온일 때 시간대별 이용 패턴이 달라지는가?
- 휴가철·명절 연휴엔 평소 대비 이용률이 얼마나 빠지는가?
- 날씨가 안 좋은 날, 출퇴근 시간대 쏠림이 완화(분산)되는가?
- (부가) 요일·시간대별 지하철 혼잡도 패턴은 어떤가?

## 기술 스택
Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit

## 프로젝트 구조
```
WeatherSubwayTraffic/
├── data/          # 원본(raw)/가공(processed) 데이터 — 레포에는 미포함
├── notebooks/     # EDA 및 실험용 노트북
├── src/           # 전처리, 분석 함수 모듈화
├── dashboard/     # Streamlit 앱
├── reports/       # 자동 생성 리포트
├── images/        # 저장된 시각화 결과
├── requirements.txt
├── README.md
└── LICENSE
```

## 데이터 출처
- 기상청 API허브 (ASOS/AWS 시간자료)
- 서울시 열린데이터광장 (지하철 역별 시간대별 승하차인원, 1~9호선)
- 서울교통공사 / 서울시메트로9호선(주) (지하철 혼잡도, 부가 지표)
- 한국천문연구원 특일정보 (공휴일)
- 방학/휴가철: 수동 정의 (서울시교육청 공지 기준 근사)

## 진행 상태
Phase 0(데이터 실사)~Phase 2(수집·병합 설계) 완료.

**검증 완료** (더미 데이터로 실제 실행 확인):
- `match_nearest_station`, `add_time_bucket`, `merge_weather_ridership`, `compute_dispersion_metrics` (merge.py)
- `compute_transfer_yn` (station_collector.py) — 2노선/3노선 환승역 모두 정확히 판정
- `compute_ridership_total` (ridership_collector.py)
- `flag_vacation_period` (holiday_collector.py) — 경계값·연도 넘김 케이스 검증 완료

**결정 완료** (API 없이 사람이 정한 항목):
- 방학 기간(VACATION_PERIODS): 통상적인 서울 초중고 방학 시기를 참고해 근사 설정
- station_id 통일 방식: station_name + line 조합으로 두 출처(서울교통공사/국토부) 매칭 (서울 스코프 한정으로 오매칭 위험 낮음)

**대기 중**: 공공데이터포털 점검 해제 후 API 키 발급 → 각 collector의 실제 호출 로직(TODO) 구현, `merge_congestion_sources`의 컬럼명 매핑 확정.

## 실행 방법
```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## 분석 결과 요약 / 느낀 점 / 향후 개선 사항
> 추후 EDA·대시보드 완료 후 작성 예정