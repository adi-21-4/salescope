import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_shop_id
from app.models.dataset import UploadedDataset
from app.schemas.dashboard import (
    CategoryShare,
    AgentPerformance,
    ActionableInsight,
    AgentDetail,
    DayOfWeekPoint,
    ForecastResponse,
    LocationShare,
    PaymentMethodShare,
    PerformanceHighlight,
    RevenuePoint,
    SeasonalPoint,
    SummaryStats,
    TopBottomProductsResponse,
)
from app.services import aggregates, forecasting
from app.services.actionable_insights import build_actionable_insights

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _load_owned_dataframe(dataset_id: uuid.UUID, shop_id: uuid.UUID, db: Session):
    dataset = db.query(UploadedDataset).filter_by(id=dataset_id, shop_id=shop_id).first()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return aggregates.load_sales_dataframe(db, shop_id, dataset_id)


@router.get("/{dataset_id}/summary", response_model=SummaryStats)
def get_summary_stats(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> dict:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.summary_stats(df)


@router.get("/{dataset_id}/highlights", response_model=list[PerformanceHighlight])
def get_performance_highlights(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Fast, deterministic takeaways for the selected sales dataset."""
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.performance_highlights(df)


@router.get("/{dataset_id}/actionable-insights", response_model=list[ActionableInsight])
def get_actionable_insights(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Explainable trend, outlier, concentration, and mix-shift findings."""
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return build_actionable_insights(df)


@router.get("/{dataset_id}/revenue", response_model=list[RevenuePoint])
def get_revenue_over_time(
    dataset_id: uuid.UUID,
    granularity: Literal["day", "week", "month"] = Query("week"),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.revenue_over_time(df, granularity)


@router.get("/{dataset_id}/top-products", response_model=TopBottomProductsResponse)
def get_top_bottom_products(
    dataset_id: uuid.UUID,
    n: int = Query(10, ge=1, le=50),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> dict:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.top_bottom_products(df, n)


@router.get("/{dataset_id}/day-of-week", response_model=list[DayOfWeekPoint])
def get_day_of_week_trends(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.day_of_week_trends(df)


@router.get("/{dataset_id}/seasonality", response_model=list[SeasonalPoint])
def get_seasonal_trends(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.seasonal_trends(df)


@router.get("/{dataset_id}/category-breakdown", response_model=list[CategoryShare])
def get_category_breakdown(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.category_breakdown(df)


@router.get("/{dataset_id}/location-breakdown", response_model=list[LocationShare])
def get_location_breakdown(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.location_breakdown(df)


@router.get("/{dataset_id}/agent-performance", response_model=list[AgentPerformance])
def get_agent_performance(
    dataset_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.agent_performance(df, limit)


@router.get("/{dataset_id}/agent-detail", response_model=AgentDetail)
def get_agent_detail(
    dataset_id: uuid.UUID,
    agent: str = Query(..., min_length=1, max_length=255),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> dict:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    if "agent" not in df.columns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent data is not available")
    selected = df[df["agent"] == agent]
    if selected.empty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    summary = aggregates.summary_stats(selected)
    total_agent_revenue = float(df.loc[df["agent"].notna(), "revenue"].sum())
    return {
        "agent": agent,
        "revenue": summary["total_revenue"],
        "transactions": summary["total_sales"],
        "average_sale": summary["avg_sale_value"],
        "share_pct": round(summary["total_revenue"] / total_agent_revenue * 100, 1) if total_agent_revenue else 0,
        "weekly_revenue": aggregates.revenue_over_time(selected, "week"),
        "top_products": aggregates.top_bottom_products(selected, 5)["top"],
        "categories": aggregates.category_breakdown(selected),
    }


@router.get("/{dataset_id}/payment-method-breakdown", response_model=list[PaymentMethodShare])
def get_payment_method_breakdown(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return aggregates.payment_method_breakdown(df)


@router.get("/{dataset_id}/forecast", response_model=ForecastResponse)
def get_forecast(
    dataset_id: uuid.UUID,
    horizon_weeks: int = Query(4, ge=1, le=12),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> dict:
    df = _load_owned_dataframe(dataset_id, shop_id, db)
    return forecasting.forecast_revenue(df, horizon_weeks)
