import pytest
from pydantic import ValidationError

from app.services.llm.schemas import GeneratedInsight, GeneratedInsightsResponse, QuerySpec


def test_generated_insight_valid():
    insight = GeneratedInsight(
        finding="Sales dip 30% on Mondays",
        supporting_stat="Monday avg $812 vs weekday avg $1,160 (-30%)",
        category="trend",
        chart_ref="day_of_week",
    )
    assert insight.category == "trend"


def test_generated_insight_rejects_invalid_category():
    with pytest.raises(ValidationError):
        GeneratedInsight(
            finding="x", supporting_stat="y", category="not_a_real_category", chart_ref=None
        )


def test_insights_response_requires_at_least_one_card():
    with pytest.raises(ValidationError):
        GeneratedInsightsResponse(insights=[])


def test_query_spec_valid_top_n():
    spec = QuerySpec(
        operation="top_n",
        group_by="category",
        metric="revenue",
        agg="sum",
        limit=5,
        order="desc",
        chart_type="bar",
    )
    assert spec.limit == 5


def test_query_spec_rejects_out_of_range_limit():
    with pytest.raises(ValidationError):
        QuerySpec(operation="top_n", metric="revenue", agg="sum", limit=999, chart_type="bar")
