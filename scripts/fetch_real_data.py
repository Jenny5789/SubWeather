"""실제 2023년 기상청 데이터 수집"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from collectors.weather_collector import collect_asos_hourly

# 2025년 최근 6개월 데이터 수집
print("📥 기상청 2025년 하반기 데이터 수집 중...")
print("(기간: 2025-07-01 ~ 2025-12-31, 약 6개월)")

try:
    weather_df = collect_asos_hourly("202507010000", "202512312359", stn=108)
    print(f"\n✅ 수집 완료: {len(weather_df)}개 행")
    print(f"   기간: {weather_df['date'].min()} ~ {weather_df['date'].max()}")
    print(f"   강수량 > 0인 날: {(weather_df['rainfall'] > 0).sum()}개")
    print(f"\n샘플:")
    print(weather_df[["date", "hour", "temperature", "rainfall", "humidity"]].head(10))

except Exception as e:
    print(f"❌ 오류: {e}")
