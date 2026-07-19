from typing import Literal

from pydantic import BaseModel


class RevenuePoint(BaseModel):
    period: str
    revenue: float


class ForecastResponse(BaseModel):
    method: Literal["insufficient_data", "linear_trend", "holt_winters_trend", "holt_winters_seasonal"]
    points: list[RevenuePoint]
    caveat: str


class ProductRevenue(BaseModel):
    product: str
    revenue: float


class TopBottomProductsResponse(BaseModel):
    top: list[ProductRevenue]
    bottom: list[ProductRevenue]


class DayOfWeekPoint(BaseModel):
    day: str
    avg_revenue: float


class SeasonalPoint(BaseModel):
    month: str
    avg_revenue: float


class CategoryShare(BaseModel):
    category: str
    revenue: float
    pct: float


class LocationShare(BaseModel):
    location: str
    revenue: float
    pct: float


class PaymentMethodShare(BaseModel):
    payment_method: str
    revenue: float
    pct: float


class SummaryStats(BaseModel):
    total_revenue: float
    total_sales: int
    avg_sale_value: float
    date_range_start: str | None
    date_range_end: str | None
