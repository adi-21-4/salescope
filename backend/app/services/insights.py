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
            "payment_method_breakdown": [],
        }

    revenue_weekly = aggregates.revenue_over_time(df, granularity="week")
    top_bottom = aggregates.top_bottom_products(df, n=5)
    day_of_week = aggregates.day_of_week_trends(df)
    seasonal = aggregates.seasonal_trends(df)

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
        "payment_method_breakdown": aggregates.payment_method_breakdown(df),
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
