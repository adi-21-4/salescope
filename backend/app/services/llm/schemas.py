from typing import Literal

from pydantic import BaseModel, Field

# --- Insights (M4) ---

InsightCategory = Literal[
    "trend", "anomaly", "seasonality", "product", "category", "location", "payment_method"
]
ChartRef = Literal[
    "revenue_over_time", "day_of_week", "seasonality", "top_products",
    "category_breakdown", "location_breakdown", "payment_method_breakdown",
]


class GeneratedInsight(BaseModel):
    finding: str = Field(description="Plain-language finding, e.g. 'Sales dip 30% on Mondays'")
    supporting_stat: str = Field(
        description="The specific number(s) from the input data that back up the finding, e.g. "
        "'Monday avg ₹812 vs weekday avg ₹1,160 (-30%)'. Must cite a number present in the input."
    )
    category: InsightCategory
    chart_ref: ChartRef | None = Field(
        default=None, description="Which existing dashboard chart this insight relates to, if any."
    )


class GeneratedInsightsResponse(BaseModel):
    insights: list[GeneratedInsight] = Field(min_length=1, max_length=6)


# --- Natural-language query (M5) ---

CanonicalColumn = Literal["date", "product", "category", "location", "payment_method"]
Metric = Literal["revenue", "quantity", "count", "avg_price"]


class QueryFilter(BaseModel):
    column: CanonicalColumn
    op: Literal["eq", "neq", "gt", "gte", "lt", "lte", "in"]
    value: str = Field(description="The comparison value as a string, e.g. '2026-01-01' or 'Electronics'")


class QuerySpec(BaseModel):
    """A constrained query the backend can safely execute against a shop's sales
    data -- the LLM only ever chooses from this fixed set of operations with typed
    parameters. It cannot express arbitrary pandas/SQL, which is the point: there
    is no code-generation step and nothing to sandbox-escape."""

    operation: Literal["groupby_aggregate", "top_n", "trend", "single_value"]
    filters: list[QueryFilter] = Field(default_factory=list)
    group_by: CanonicalColumn | None = None
    metric: Metric
    agg: Literal["sum", "avg", "count", "max", "min"]
    limit: int | None = Field(default=None, ge=1, le=50)
    order: Literal["asc", "desc"] | None = None
    granularity: Literal["week", "month"] | None = Field(
        default=None, description="Only used when operation is 'trend'."
    )
    chart_type: Literal["line", "bar", "number"]
