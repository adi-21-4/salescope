import pandas as pd

from app.services.insights import build_summary


def _sample_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-05", "2026-01-05", "2026-01-06", "2026-01-12", "2026-02-02"])
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


def test_build_summary_matches_dashboard_aggregates():
    # The whole point of build_summary is that it's derived from the SAME
    # aggregate functions the dashboard charts use -- so the AI's narration
    # and the dashboard numbers can never disagree.
    df = _sample_df()
    summary = build_summary(df)
    assert summary["total_revenue"] == 120.0
    assert summary["total_sales"] == 5
    assert summary["date_range"] == {"start": "2026-01-05", "end": "2026-02-02"}
    assert len(summary["revenue_by_week"]) > 0
    assert {p["product"] for p in summary["top_products"]} <= {"Widget", "Gadget"}
    assert set(summary["day_of_week_avg_revenue"].keys()) == {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    }
    assert any(c["category"] == "Tools" for c in summary["category_breakdown"])
    assert any(loc["location"] == "Uptown" for loc in summary["location_breakdown"])
    assert any(pm["payment_method"] == "Cash" for pm in summary["payment_method_breakdown"])


def test_build_summary_caps_weekly_points():
    # 30 weeks of history -> only the most recent 26 should be sent to the LLM,
    # keeping the prompt small regardless of how much data the shop has.
    dates = pd.date_range("2025-01-05", periods=30, freq="W")
    df = pd.DataFrame(
        {
            "sale_date": dates,
            "product_name": ["Widget"] * 30,
            "category": ["Tools"] * 30,
            "location": [None] * 30,
            "payment_method": [None] * 30,
            "quantity": [1] * 30,
            "unit_price": [10.0] * 30,
            "revenue": [10.0] * 30,
        }
    )
    summary = build_summary(df)
    assert len(summary["revenue_by_week"]) <= 26


def test_build_summary_empty_dataframe_returns_safe_defaults():
    empty = pd.DataFrame(
        columns=[
            "sale_date", "product_name", "category", "location", "payment_method",
            "quantity", "unit_price", "revenue",
        ]
    )
    summary = build_summary(empty)
    assert summary["total_revenue"] == 0
    assert summary["total_sales"] == 0
    assert summary["revenue_by_week"] == []
    assert summary["top_products"] == []
