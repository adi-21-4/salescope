import pandas as pd

from app.services.aggregates import (
    category_breakdown,
    day_of_week_trends,
    location_breakdown,
    payment_method_breakdown,
    revenue_over_time,
    seasonal_trends,
    summary_stats,
    top_bottom_products,
)


def _sample_df() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2026-01-05", "2026-01-05", "2026-01-06", "2026-01-12", "2026-02-02"]
    )  # Mondays: Jan 5 & 12, Tuesday: Jan 6, Monday: Feb 2
    return pd.DataFrame(
        {
            "sale_date": dates,
            "product_name": ["Widget", "Gadget", "Widget", "Widget", "Gadget"],
            "category": ["Tools", "Electronics", "Tools", "Tools", "Electronics"],
            "location": ["Downtown", "Downtown", "Uptown", "Uptown", "Uptown"],
            "payment_method": ["Cash", "Card", "Cash", "Card", "Card"],
            "quantity": [2, 1, 3, 1, 2],
            "unit_price": [10.0, 20.0, 10.0, 10.0, 20.0],
            "revenue": [20.0, 20.0, 30.0, 10.0, 40.0],
        }
    )


def test_revenue_over_time_monthly():
    df = _sample_df()
    result = revenue_over_time(df, granularity="month")
    assert result == [
        {"period": "2026-01-01", "revenue": 80.0},
        {"period": "2026-02-01", "revenue": 40.0},
    ]


def test_revenue_over_time_daily():
    df = _sample_df()
    result = revenue_over_time(df, granularity="day")
    # daily resampling fills every calendar day in range, including zero-revenue gaps
    by_period = {p["period"]: p["revenue"] for p in result}
    assert by_period["2026-01-05"] == 40.0
    assert by_period["2026-01-06"] == 30.0
    assert by_period["2026-01-12"] == 10.0
    assert by_period["2026-02-02"] == 40.0
    assert by_period["2026-01-07"] == 0.0
    assert result[0]["period"] == "2026-01-05"
    assert result[-1]["period"] == "2026-02-02"


def test_top_bottom_products():
    df = _sample_df()
    result = top_bottom_products(df, n=1)
    # Widget: 20+30+10=60, Gadget: 20+40=60 -- tied, so just check both totals surface
    assert result["top"][0]["revenue"] == 60.0
    assert result["bottom"][0]["revenue"] == 60.0
    assert {result["top"][0]["product"], result["bottom"][0]["product"]} == {"Widget", "Gadget"}


def test_top_bottom_products_never_overlap_with_few_products():
    # Only 2 distinct products but n=10 (the default) -- head(10) and tail(10) of
    # a 2-row series would naively both return both rows, making "bottom" a
    # duplicate of "top". Bottom should come back empty instead.
    df = _sample_df()
    result = top_bottom_products(df, n=10)
    top_names = {p["product"] for p in result["top"]}
    bottom_names = {p["product"] for p in result["bottom"]}
    assert top_names == {"Widget", "Gadget"}
    assert bottom_names == set()


def test_day_of_week_trends_averages_across_weeks():
    df = _sample_df()
    result = {r["day"]: r["avg_revenue"] for r in day_of_week_trends(df)}
    # Monday appears on Jan 5 (rev 40), Jan 12 (rev 10), Feb 2 (rev 40) -> avg 30
    assert result["Monday"] == 30.0
    assert result["Tuesday"] == 30.0
    assert result["Sunday"] == 0.0


def test_seasonal_trends_by_month_name():
    df = _sample_df()
    result = {r["month"]: r["avg_revenue"] for r in seasonal_trends(df)}
    assert result["January"] == 80.0
    assert result["February"] == 40.0
    assert result["March"] == 0.0


def test_category_breakdown_percentages_sum_to_100():
    df = _sample_df()
    result = category_breakdown(df)
    total_pct = sum(r["pct"] for r in result)
    assert abs(total_pct - 100.0) < 0.2
    tools = next(r for r in result if r["category"] == "Tools")
    assert tools["revenue"] == 60.0


def test_location_breakdown_percentages_sum_to_100():
    df = _sample_df()
    result = location_breakdown(df)
    total_pct = sum(r["pct"] for r in result)
    assert abs(total_pct - 100.0) < 0.2
    uptown = next(r for r in result if r["location"] == "Uptown")
    # Uptown: rows 2,3,4 -> revenue 30+10+40 = 80
    assert uptown["revenue"] == 80.0


def test_payment_method_breakdown_percentages_sum_to_100():
    df = _sample_df()
    result = payment_method_breakdown(df)
    total_pct = sum(r["pct"] for r in result)
    assert abs(total_pct - 100.0) < 0.2
    card = next(r for r in result if r["payment_method"] == "Card")
    # Card: rows 1,3,4 -> revenue 20+10+40 = 70
    assert card["revenue"] == 70.0


def test_summary_stats():
    df = _sample_df()
    stats = summary_stats(df)
    assert stats["total_revenue"] == 120.0  # 20+20+30+10+40
    assert stats["total_sales"] == 5
    assert stats["avg_sale_value"] == 24.0
    assert stats["date_range_start"] == "2026-01-05"
    assert stats["date_range_end"] == "2026-02-02"


def test_empty_dataframe_returns_safe_defaults():
    empty = pd.DataFrame(
        columns=[
            "sale_date", "product_name", "category", "location", "payment_method",
            "quantity", "unit_price", "revenue",
        ]
    )
    assert revenue_over_time(empty) == []
    assert top_bottom_products(empty) == {"top": [], "bottom": []}
    assert category_breakdown(empty) == []
    assert location_breakdown(empty) == []
    assert payment_method_breakdown(empty) == []
    assert len(day_of_week_trends(empty)) == 7
    assert len(seasonal_trends(empty)) == 12
    stats = summary_stats(empty)
    assert stats["total_revenue"] == 0.0
    assert stats["total_sales"] == 0
