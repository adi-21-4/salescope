import uuid

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_SHARE_SLOTS = 8  # matches the fixed 8-slot categorical palette; the rest fold into "Other"


def load_sales_dataframe(db: Session, shop_id: uuid.UUID, dataset_id: uuid.UUID) -> pd.DataFrame:
    """Load complete (non-incomplete) sales rows for a shop-owned dataset.

    Reads via a plain SQL query rather than ORM hydration — this is a read path
    that can scan the whole dataset, and we only need a handful of columns as a
    DataFrame, not fully-hydrated model instances.
    """
    query = text(
        """
        SELECT sale_date, product_name, category, location, agent, customer_id, payment_method,
               quantity, unit_price, unit_cost, gross_profit, revenue
        FROM sales_records
        WHERE shop_id = :shop_id AND dataset_id = :dataset_id AND NOT is_incomplete
        """
    )
    df = pd.read_sql(query, db.connection(), params={"shop_id": str(shop_id), "dataset_id": str(dataset_id)})
    if not df.empty:
        df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


def summary_stats(df: pd.DataFrame) -> dict:
    """Headline sales, volume, and cost-coverage metrics for the dashboard."""
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_sales": 0,
            "avg_sale_value": 0.0,
            "total_units": 0.0,
            "gross_profit": None,
            "gross_margin_pct": None,
            "cost_coverage_pct": 0.0,
            "date_range_start": None,
            "date_range_end": None,
        }
    total_revenue = float(df["revenue"].sum())
    total_sales = int(len(df))
    total_units = float(df["quantity"].fillna(0).sum()) if "quantity" in df.columns else float(total_sales)
    cost_rows = df.dropna(subset=["unit_cost", "gross_profit"]) if {"unit_cost", "gross_profit"}.issubset(df.columns) else df.iloc[0:0]
    cost_revenue = float(cost_rows["revenue"].sum()) if not cost_rows.empty else 0.0
    gross_profit = float(cost_rows["gross_profit"].sum()) if not cost_rows.empty else None
    return {
        "total_revenue": round(total_revenue, 2),
        "total_sales": total_sales,
        "avg_sale_value": round(total_revenue / total_sales, 2) if total_sales else 0.0,
        "total_units": round(total_units, 2),
        "gross_profit": round(gross_profit, 2) if gross_profit is not None else None,
        "gross_margin_pct": round(gross_profit / cost_revenue * 100, 1) if gross_profit is not None and cost_revenue > 0 else None,
        "cost_coverage_pct": round(cost_revenue / total_revenue * 100, 1) if total_revenue > 0 else 0.0,
        "date_range_start": df["sale_date"].min().date().isoformat(),
        "date_range_end": df["sale_date"].max().date().isoformat(),
    }


def performance_highlights(df: pd.DataFrame) -> list[dict]:
    """Return concise, deterministic takeaways derived only from this dataset."""
    if df.empty:
        return []

    highlights: list[dict] = []
    total = float(df["revenue"].sum())

    products = top_bottom_products(df, n=1)["top"]
    if products:
        product = products[0]
        share = float(product["revenue"]) / total * 100 if total else 0
        highlights.append({
            "kind": "product",
            "label": "Top product",
            "value": product["product"],
            "detail": f"{share:.1f}% of recorded revenue",
        })

    for kind, label, rows, key in (
        ("category", "Leading category", category_breakdown(df), "category"),
        ("location", "Leading location", location_breakdown(df), "location"),
    ):
        if rows:
            leader = rows[0]
            highlights.append({
                "kind": kind,
                "label": label,
                "value": leader[key],
                "detail": f"{leader['pct']:.1f}% of recorded revenue",
            })

    weekdays = day_of_week_trends(df)
    if weekdays:
        strongest = max(weekdays, key=lambda row: row["avg_revenue"])
        if strongest["avg_revenue"] > 0:
            highlights.append({
                "kind": "weekday",
                "label": "Strongest day",
                "value": strongest["day"],
                "detail": f"{strongest['avg_revenue']:,.0f} average daily revenue",
            })

    return highlights


_REVENUE_OVER_TIME_FREQ = {"day": "D", "week": "W", "month": "MS"}


def revenue_over_time(df: pd.DataFrame, granularity: str = "week") -> list[dict]:
    if df.empty:
        return []
    freq = _REVENUE_OVER_TIME_FREQ.get(granularity, "W")
    series = df.set_index("sale_date")["revenue"].resample(freq).sum().fillna(0)
    return [{"period": period.date().isoformat(), "revenue": round(float(value), 2)} for period, value in series.items()]


def top_bottom_products(df: pd.DataFrame, n: int = 10) -> dict:
    """Top and bottom N products by revenue. "Bottom" only ever shows products
    NOT already shown in "top" -- with few distinct products (common for small
    shops), naively taking head(n) and tail(n) of the same short list returns
    the same items twice, making the two charts look identical."""
    if df.empty or df["product_name"].isna().all():
        return {"top": [], "bottom": []}
    by_product = df.groupby("product_name")["revenue"].sum().sort_values(ascending=False)
    top_series = by_product.head(n)
    remaining = by_product.iloc[len(top_series):]
    bottom_series = remaining.tail(n)
    top = [{"product": name, "revenue": round(float(v), 2)} for name, v in top_series.items()]
    bottom = [{"product": name, "revenue": round(float(v), 2)} for name, v in bottom_series.items()]
    return {"top": top, "bottom": bottom}


_WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def day_of_week_trends(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return [{"day": d, "avg_revenue": 0.0} for d in _WEEKDAY_ORDER]
    working = df.copy()
    working["weekday"] = working["sale_date"].dt.day_name()
    daily_totals = working.groupby([working["sale_date"].dt.date, "weekday"])["revenue"].sum().reset_index()
    avg_by_weekday = daily_totals.groupby("weekday")["revenue"].mean()
    return [
        {"day": d, "avg_revenue": round(float(avg_by_weekday.get(d, 0.0)), 2)}
        for d in _WEEKDAY_ORDER
    ]


_MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def seasonal_trends(df: pd.DataFrame) -> list[dict]:
    """Average revenue per calendar month across all years present — surfaces
    recurring intra-year seasonality (e.g. "December is our best month") rather
    than a single-pass timeline (that's revenue_over_time's job)."""
    if df.empty:
        return [{"month": m, "avg_revenue": 0.0} for m in _MONTH_ORDER]
    working = df.copy()
    working["month"] = working["sale_date"].dt.month_name()
    working["year"] = working["sale_date"].dt.year
    monthly_totals = working.groupby(["year", "month"])["revenue"].sum().reset_index()
    avg_by_month = monthly_totals.groupby("month")["revenue"].mean()
    return [
        {"month": m, "avg_revenue": round(float(avg_by_month.get(m, 0.0)), 2)}
        for m in _MONTH_ORDER
    ]


def _share_breakdown(df: pd.DataFrame, dim_col: str, label_key: str) -> list[dict]:
    """Shared logic behind category_breakdown and location_breakdown: group by a
    dimension column, sum revenue, fold anything past the 8-slot categorical
    palette into "Other" so the chart never needs more colors than the palette has."""
    if df.empty or dim_col not in df.columns or df[dim_col].isna().all():
        return []
    by_dim = df.groupby(dim_col)["revenue"].sum().sort_values(ascending=False)
    total = by_dim.sum()
    if total == 0:
        return []

    top = by_dim.head(MAX_SHARE_SLOTS - 1) if len(by_dim) > MAX_SHARE_SLOTS else by_dim
    rest_total = total - top.sum()

    result = [
        {label_key: name, "revenue": round(float(v), 2), "pct": round(float(v) / float(total) * 100, 1)}
        for name, v in top.items()
    ]
    if rest_total > 0:
        result.append(
            {label_key: "Other", "revenue": round(float(rest_total), 2), "pct": round(float(rest_total) / float(total) * 100, 1)}
        )
    return result


def category_breakdown(df: pd.DataFrame) -> list[dict]:
    return _share_breakdown(df, "category", "category")


def location_breakdown(df: pd.DataFrame) -> list[dict]:
    return _share_breakdown(df, "location", "location")


def agent_performance(df: pd.DataFrame, limit: int = 20) -> list[dict]:
    """Rank agents and assign Pareto ABC tiers by cumulative revenue share."""
    if df.empty or "agent" not in df.columns or df["agent"].isna().all():
        return []
    work = df[df["agent"].notna() & (df["agent"].astype(str).str.strip() != "")]
    if work.empty:
        return []
    grouped = (
        work.groupby("agent")["revenue"]
        .agg(revenue="sum", transactions="count")
        .sort_values("revenue", ascending=False)
        .head(limit)
    )
    total_revenue = float(work["revenue"].sum())
    if total_revenue <= 0:
        return []
    results = []
    cumulative = 0.0
    for agent, values in grouped.iterrows():
        revenue = float(values["revenue"])
        share = revenue / total_revenue * 100
        prior_cumulative = cumulative
        cumulative += share
        tier = "A" if prior_cumulative < 80 else "B" if prior_cumulative < 95 else "C"
        count = int(values["transactions"])
        results.append({
            "agent": str(agent),
            "revenue": round(revenue, 2),
            "transactions": count,
            "average_sale": round(revenue / count, 2) if count else 0.0,
            "share_pct": round(share, 1),
            "cumulative_pct": round(cumulative, 1),
            "tier": tier,
        })
    return results


def payment_method_breakdown(df: pd.DataFrame) -> list[dict]:
    return _share_breakdown(df, "payment_method", "payment_method")
