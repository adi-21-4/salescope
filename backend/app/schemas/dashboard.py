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
    total_units: float
    gross_profit: float | None
    gross_margin_pct: float | None
    cost_coverage_pct: float
    date_range_start: str | None
    date_range_end: str | None


class PerformanceHighlight(BaseModel):
    kind: Literal["product", "category", "location", "weekday"]
    label: str
    value: str
    detail: str


class AgentPerformance(BaseModel):
    agent: str
    revenue: float
    transactions: int
    average_sale: float
    share_pct: float
    cumulative_pct: float
    tier: Literal["A", "B", "C"]


class ActionableInsightPoint(BaseModel):
    label: str
    value: float
    compare_value: float | None = None
    marked: bool = False
    note: str | None = None


class InsightDriver(BaseModel):
    label: str
    dimension: str
    current: float
    previous: float
    change: float


class ActionableInsight(BaseModel):
    id: Literal["revenue_change", "sales_anomaly", "product_concentration", "payment_shift", "location_shift", "profit_margin", "customer_retention"]
    category: str
    title: str
    summary: str
    explanation: str
    period: str
    metric_label: str
    metric_value: float
    value_format: Literal["currency", "percent", "percentage_points"]
    point_format: Literal["currency", "percent"]
    chart_ref: str | None
    points: list[ActionableInsightPoint]
    drivers: list[InsightDriver]
    suggested_question: str | None


class AgentDetail(BaseModel):
    agent: str
    revenue: float
    transactions: int
    average_sale: float
    share_pct: float
    weekly_revenue: list[RevenuePoint]
    top_products: list[ProductRevenue]
    categories: list[CategoryShare]
