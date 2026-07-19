import pandas as pd
import pytest

from app.services.llm.schemas import QueryFilter, QuerySpec
from app.services.query_dsl import QueryExecutionError, execute_query


def _sample_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-12", "2026-02-02", "2026-02-03"])
    return pd.DataFrame(
        {
            "sale_date": dates,
            "product_name": ["Widget", "Gadget", "Widget", "Widget", "Gadget"],
            "category": ["Tools", "Electronics", "Tools", "Tools", "Electronics"],
            "location": ["Downtown", "Downtown", "Uptown", "Uptown", "Uptown"],
            "payment_method": ["Cash", "Card", "Cash", "Card", "Card"],
            "quantity": [2, 1, 3, 1, 2],
            "unit_price": [10.0, 20.0, 10.0, 10.0, 20.0],
            "revenue": [20.0, 20.0, 30.0, 10.0, 40.0],
        }
    )


def test_top_n_by_category():
    spec = QuerySpec(
        operation="top_n", group_by="category", metric="revenue", agg="sum",
        limit=1, order="desc", chart_type="bar",
    )
    result = execute_query(_sample_df(), spec)
    # Tools (20+30+10=60) and Electronics (20+40=60) are tied -- just check the
    # top_n cap and the correct tied value surface, not which one wins the tie.
    assert len(result["data"]) == 1
    assert result["data"][0]["value"] == 60.0
    assert result["data"][0]["label"] in {"Tools", "Electronics"}


def test_groupby_aggregate_avg_price_by_product():
    spec = QuerySpec(
        operation="groupby_aggregate", group_by="product", metric="avg_price",
        agg="avg", chart_type="bar",
    )
    result = execute_query(_sample_df(), spec)
    values = {r["label"]: r["value"] for r in result["data"]}
    assert values["Gadget"] == 20.0
    assert values["Widget"] == pytest.approx(10.0)


def test_trend_monthly_revenue():
    spec = QuerySpec(operation="trend", metric="revenue", agg="sum", granularity="month", chart_type="line")
    result = execute_query(_sample_df(), spec)
    values = {r["label"]: r["value"] for r in result["data"]}
    assert values["2026-01-01"] == 70.0  # 20+20+30
    assert values["2026-02-01"] == 50.0  # 10+40


def test_single_value_total_revenue():
    spec = QuerySpec(operation="single_value", metric="revenue", agg="sum", chart_type="number")
    result = execute_query(_sample_df(), spec)
    assert result["data"] == [{"label": "revenue", "value": 120.0}]
    assert result["chart_type"] == "number"


def test_filter_by_payment_method():
    spec = QuerySpec(
        operation="single_value",
        filters=[QueryFilter(column="payment_method", op="eq", value="Card")],
        metric="revenue", agg="sum", chart_type="number",
    )
    result = execute_query(_sample_df(), spec)
    assert result["data"][0]["value"] == 70.0  # 20 (Gadget) + 10 (Widget card) + 40 (Gadget)


def test_filter_by_date_range():
    spec = QuerySpec(
        operation="single_value",
        filters=[QueryFilter(column="date", op="gte", value="2026-02-01")],
        metric="revenue", agg="sum", chart_type="number",
    )
    result = execute_query(_sample_df(), spec)
    assert result["data"][0]["value"] == 50.0  # Feb rows only


def test_count_metric():
    spec = QuerySpec(operation="single_value", metric="count", agg="count", chart_type="number")
    result = execute_query(_sample_df(), spec)
    assert result["data"][0]["value"] == 5.0


def test_groupby_requires_group_by_column():
    spec = QuerySpec(operation="groupby_aggregate", metric="revenue", agg="sum", chart_type="bar")
    with pytest.raises(QueryExecutionError):
        execute_query(_sample_df(), spec)


def test_top_n_respects_limit_cap():
    spec = QuerySpec(
        operation="top_n", group_by="product", metric="revenue", agg="sum",
        limit=1, order="desc", chart_type="bar",
    )
    result = execute_query(_sample_df(), spec)
    assert len(result["data"]) == 1
