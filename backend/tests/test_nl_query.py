import pandas as pd

from app.services.llm.schemas import QuerySpec
from app.services.nl_query import build_schema_description, format_answer, normalize_question


def _sample_df() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-05", "2026-01-06"])
    return pd.DataFrame(
        {
            "sale_date": dates,
            "product_name": ["Widget", "Gadget"],
            "category": ["Tools", "Electronics"],
            "location": ["Downtown", "Uptown"],
            "payment_method": ["Cash", "Card"],
            "quantity": [2, 1],
            "unit_price": [10.0, 20.0],
            "revenue": [20.0, 20.0],
        }
    )


def test_build_schema_description_includes_example_values():
    desc = build_schema_description(_sample_df())
    assert "Tools" in desc["available_categories"]
    assert "Electronics" in desc["available_categories"]
    assert desc["date_range"] == {"start": "2026-01-05", "end": "2026-01-06"}


def test_build_schema_description_empty_dataframe():
    empty = pd.DataFrame(columns=["sale_date", "category", "location", "payment_method"])
    desc = build_schema_description(empty)
    assert desc["available_categories"] == []
    assert desc["date_range"] is None


def test_normalize_question_collapses_whitespace_and_case():
    assert normalize_question("  What Was   my Revenue?  ") == "what was my revenue?"
    assert normalize_question("what was my revenue?") == "what was my revenue?"


def test_format_answer_single_value():
    spec = QuerySpec(operation="single_value", metric="revenue", agg="sum", chart_type="number")
    result = {"data": [{"label": "revenue", "value": 1234.5}], "chart_type": "number"}
    assert "1,234.50" in format_answer(spec, result)


def test_format_answer_no_data():
    spec = QuerySpec(operation="single_value", metric="revenue", agg="sum", chart_type="number")
    assert format_answer(spec, {"data": [], "chart_type": "number"}) == "No matching data found."


def test_format_answer_top_n():
    spec = QuerySpec(
        operation="top_n", group_by="category", metric="revenue", agg="sum",
        limit=3, chart_type="bar",
    )
    result = {
        "data": [
            {"label": "Tools", "value": 100.0},
            {"label": "Electronics", "value": 50.0},
        ],
        "chart_type": "bar",
    }
    answer = format_answer(spec, result)
    assert "Tools" in answer
    assert "100.00" in answer
