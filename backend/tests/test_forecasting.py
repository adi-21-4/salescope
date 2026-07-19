import numpy as np
import pandas as pd
import pytest

from app.services.forecasting import forecast_revenue


def _weekly_df(n_weeks: int, weekly_revenue) -> pd.DataFrame:
    """Build a sales dataframe with one row per week landing on distinct weeks,
    with revenue equal to weekly_revenue(i) for week i."""
    dates = pd.date_range("2026-01-04", periods=n_weeks, freq="W")  # Sundays
    revenue = [weekly_revenue(i) for i in range(n_weeks)]
    return pd.DataFrame({"sale_date": dates, "revenue": revenue})


def test_empty_dataframe_returns_insufficient_data():
    empty = pd.DataFrame(columns=["sale_date", "revenue"])
    result = forecast_revenue(empty)
    assert result["method"] == "insufficient_data"
    assert result["points"] == []


def test_single_week_returns_insufficient_data():
    df = _weekly_df(1, lambda i: 100.0)
    result = forecast_revenue(df, horizon_weeks=4)
    assert result["method"] == "insufficient_data"


def test_short_history_uses_linear_trend():
    # 5 weeks, clean upward trend: 100, 200, 300, 400, 500
    df = _weekly_df(5, lambda i: 100.0 * (i + 1))
    result = forecast_revenue(df, horizon_weeks=3)
    assert result["method"] == "linear_trend"
    assert len(result["points"]) == 3
    # trend continues upward: next points should be ~600, 700, 800
    values = [p["revenue"] for p in result["points"]]
    assert values[0] == pytest.approx(600.0, abs=1.0)
    assert values[1] > values[0]
    assert values[2] > values[1]


def test_longer_history_uses_holt_winters_trend():
    # 20 weeks of roughly-flat-with-slight-upward-trend revenue
    rng = np.random.default_rng(42)
    df = _weekly_df(20, lambda i: 1000.0 + 10 * i + float(rng.normal(0, 5)))
    result = forecast_revenue(df, horizon_weeks=4)
    assert result["method"] == "holt_winters_trend"
    assert len(result["points"]) == 4
    assert all(p["revenue"] >= 0 for p in result["points"])


def test_forecast_never_negative():
    # sharply declining trend that would go negative if extrapolated naively
    df = _weekly_df(6, lambda i: max(0.0, 500.0 - 150.0 * i))
    result = forecast_revenue(df, horizon_weeks=5)
    assert all(p["revenue"] >= 0 for p in result["points"])


def test_forecast_periods_are_sequential_weeks_after_history():
    df = _weekly_df(5, lambda i: 100.0)
    result = forecast_revenue(df, horizon_weeks=3)
    periods = [p["period"] for p in result["points"]]
    assert periods == sorted(periods)
    assert len(set(periods)) == 3
