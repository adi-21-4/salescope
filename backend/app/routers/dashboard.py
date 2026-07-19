import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_shop_id
from app.models.dataset import UploadedDataset
from app.schemas.dashboard import (
    CategoryShare,
    DayOfWeekPoint,
    ForecastResponse,
    LocationShare,
    PaymentMethodShare,
    RevenuePoint,
    SeasonalPoint,
    SummaryStats,
    TopBottomProductsResponse,
)
from app.services import aggregates, forecasting

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
