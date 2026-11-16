import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.models.insight import InsightCard
from app.services import aggregates
from app.services.llm.base import LLMProvider

# How many recent weekly points to send the LLM -- enough to spot a trend
# without sending full multi-year history for every request.
MAX_WEEKLY_POINTS = 26


def build_summary(df: pd.DataFrame) -> dict:
    """Compact structured summary of a dataset's aggregates -- NEVER raw rows.
    Reuses the exact same aggregate functions the dashboard charts call, so the
    AI narration and the dashboard numbers can never disagree with each other."""
    stats = aggregates.summary_stats(df)
    if df.empty:
        return {
            "date_range": None,
            "total_revenue": 0,
            "total_sales": 0,
            "avg_sale_value": 0,
            "revenue_by_week": [],
            "top_products": [],
            "bottom_products": [],
            "day_of_week_avg_revenue": {},
            "seasonal_avg_revenue": {},
            "category_breakdown": [],
            "location_breakdown": [],
            "agent_performance": [],
            "payment_method_breakdown": [],
            "profit_summary": None,
            "customer_retention_summary": None,
        }

    revenue_weekly = aggregates.revenue_over_time(df, granularity="week")
    top_bottom = aggregates.top_bottom_products(df, n=5)
    day_of_week = aggregates.day_of_week_trends(df)
    seasonal = aggregates.seasonal_trends(df)

    profit_summary = None
    if "unit_cost" in df.columns and "gross_profit" in df.columns:
        cost_rows = df.dropna(subset=["unit_cost", "gross_profit"])
        revenue = float(cost_rows["revenue"].sum()) if not cost_rows.empty else 0.0
        if revenue > 0:
            profit_summary = {
                "gross_profit": round(float(cost_rows["gross_profit"].sum()), 2),
                "gross_margin_pct": round(float(cost_rows["gross_profit"].sum()) / revenue * 100, 1),
                "cost_coverage_pct": round(len(cost_rows) / len(df) * 100, 1),
            }

    retention_summary = None
    if "customer_id" in df.columns:
        customer_rows = df.dropna(subset=["customer_id"]).copy()
        customer_rows = customer_rows[customer_rows["customer_id"].astype(str).str.strip() != ""]
        if not customer_rows.empty:
            customer_rows["month"] = customer_rows["sale_date"].dt.to_period("M")
            customer_rows["first_month"] = customer_rows.groupby("customer_id")["month"].transform("min")
            latest_complete_month = customer_rows["month"].max() - 1
            complete = customer_rows[customer_rows["first_month"] < latest_complete_month]
            if not complete.empty:
                cohort_sizes = complete.groupby("first_month")["customer_id"].nunique()
                first_repeat = complete[complete["month"] == complete["first_month"] + 1]
                rates = [
                    round(float(first_repeat[first_repeat["first_month"] == cohort]["customer_id"].nunique()) / size * 100, 1)
                    for cohort, size in cohort_sizes.items() if size > 0
                ]
                if rates:
                    retention_summary = {"completed_cohorts": len(rates), "average_month_one_retention_pct": round(sum(rates) / len(rates), 1)}

    return {
        "date_range": {"start": stats["date_range_start"], "end": stats["date_range_end"]},
        "total_revenue": stats["total_revenue"],
        "total_sales": stats["total_sales"],
        "avg_sale_value": stats["avg_sale_value"],
        "revenue_by_week": revenue_weekly[-MAX_WEEKLY_POINTS:],
        "top_products": top_bottom["top"],
        "bottom_products": top_bottom["bottom"],
        "day_of_week_avg_revenue": {d["day"]: d["avg_revenue"] for d in day_of_week},
        "seasonal_avg_revenue": {m["month"]: m["avg_revenue"] for m in seasonal},
        "category_breakdown": aggregates.category_breakdown(df),
        "location_breakdown": aggregates.location_breakdown(df),
        "agent_performance": aggregates.agent_performance(df),
        "payment_method_breakdown": aggregates.payment_method_breakdown(df),
        "profit_summary": profit_summary,
        "customer_retention_summary": retention_summary,
    }


def generate_and_cache_insights(
    db: Session,
    shop_id: uuid.UUID,
    dataset_id: uuid.UUID,
    df: pd.DataFrame,
    provider: LLMProvider,
) -> list[InsightCard]:
    summary = build_summary(df)
    result = provider.generate_insights(summary)

    cards = [
        InsightCard(
            shop_id=shop_id,
            dataset_id=dataset_id,
            finding=insight.finding,
            supporting_stat=insight.supporting_stat,
            category=insight.category,
            chart_ref=insight.chart_ref,
            model_used=provider.model_name,
        )
        for insight in result.insights
    ]
    db.add_all(cards)
    db.commit()
    for card in cards:
        db.refresh(card)
    return cards
