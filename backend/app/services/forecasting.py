import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

MIN_WEEKS_FOR_ANY_FORECAST = 2
MIN_WEEKS_FOR_HOLT_WINTERS = 8
MIN_WEEKS_FOR_SEASONALITY = 104  # ~2 full yearly cycles
SEASONAL_PERIOD_WEEKS = 52


def _linear_trend_forecast(weekly: pd.Series, horizon: int) -> np.ndarray:
    x = np.arange(len(weekly))
    slope, intercept = np.polyfit(x, weekly.to_numpy(dtype=float), 1)
    future_x = np.arange(len(weekly), len(weekly) + horizon)
    return slope * future_x + intercept


def forecast_revenue(df: pd.DataFrame, horizon_weeks: int = 4) -> dict:
    """Project revenue for the next `horizon_weeks` weeks.

    Method scales with how much history is available: too little data -> no
    forecast; a handful of weeks -> linear trend; 8+ weeks -> Holt-Winters
    (trend only, statsmodels needs far more than a year to safely fit yearly
    seasonality); 2+ years -> Holt-Winters with additive yearly seasonality.
    Always reports which method was used and a plain-language caveat so the
    frontend can show appropriate uncertainty framing rather than a number
    with false precision.
    """
    if df.empty:
        return {"method": "insufficient_data", "points": [], "caveat": "No sales data yet."}

    weekly = df.set_index("sale_date")["revenue"].resample("W").sum()

    if len(weekly) < MIN_WEEKS_FOR_ANY_FORECAST:
        return {
            "method": "insufficient_data",
            "points": [],
            "caveat": "Need at least 2 weeks of sales history to forecast.",
        }

    if len(weekly) < MIN_WEEKS_FOR_HOLT_WINTERS:
        forecast_values = _linear_trend_forecast(weekly, horizon_weeks)
        method = "linear_trend"
        caveat = "Based on limited history (fewer than 8 weeks) — treat as a rough estimate."
    else:
        seasonal_periods = SEASONAL_PERIOD_WEEKS if len(weekly) >= MIN_WEEKS_FOR_SEASONALITY else None
        try:
            model = ExponentialSmoothing(
                weekly,
                trend="add",
                seasonal="add" if seasonal_periods else None,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit()
            forecast_values = model.forecast(horizon_weeks).to_numpy()
            if seasonal_periods:
                method = "holt_winters_seasonal"
                caveat = "Forecast accounts for both trend and yearly seasonality in your sales history."
            else:
                method = "holt_winters_trend"
                caveat = "Forecast based on your recent trend. Add more history (2+ years) to also capture seasonality."
        except Exception:
            # Degenerate series (e.g. all-zero, constant, or too short after
            # resampling gaps) can fail to converge -- fall back rather than 500.
            forecast_values = _linear_trend_forecast(weekly, horizon_weeks)
            method = "linear_trend"
            caveat = "Based on irregular sales history — treat as a rough estimate."

    last_period = weekly.index[-1]
    future_periods = pd.date_range(start=last_period + pd.Timedelta(weeks=1), periods=horizon_weeks, freq="W")
    points = [
        {"period": period.date().isoformat(), "revenue": max(0.0, round(float(value), 2))}
        for period, value in zip(future_periods, forecast_values)
    ]

    return {"method": method, "points": points, "caveat": caveat}
