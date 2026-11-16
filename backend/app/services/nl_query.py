import re

import pandas as pd

from app.services.llm.schemas import QuerySpec

MAX_EXAMPLE_VALUES = 20


def _distinct_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns or not df[column].notna().any():
        return []
    return sorted(df[column].dropna().unique().tolist())[:MAX_EXAMPLE_VALUES]


def build_schema_description(df: pd.DataFrame) -> dict:
    """What the LLM is told about a shop's data shape -- canonical columns and
    example values for the low-cardinality ones. Never the raw rows."""
    if df.empty:
        return {
            "canonical_columns": ["date", "product", "category", "location", "agent", "payment_method"],
            "available_categories": [],
            "available_locations": [],
            "available_agents": [],
            "available_payment_methods": [],
            "date_range": None,
        }
    return {
        "canonical_columns": ["date", "product", "category", "location", "agent", "payment_method"],
        "available_categories": _distinct_values(df, "category"),
        "available_locations": _distinct_values(df, "location"),
        "available_agents": _distinct_values(df, "agent"),
        "available_payment_methods": _distinct_values(df, "payment_method"),
        "date_range": {
            "start": df["sale_date"].min().date().isoformat(),
            "end": df["sale_date"].max().date().isoformat(),
        },
    }


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


_METRIC_LABEL = {"revenue": "revenue", "quantity": "units sold", "avg_price": "average price", "count": "count"}


def format_answer(spec: QuerySpec, result: dict) -> str:
    """Deterministic templated summary of the query result -- not a second LLM
    call, to keep NL query latency/cost bounded to one model call per question."""
    data = result["data"]
    metric_label = _METRIC_LABEL.get(spec.metric, spec.metric)

    if not data:
        return "No matching data found."

    if spec.operation == "single_value":
        return f"Total {metric_label}: {data[0]['value']:,.2f}"

    if spec.operation == "top_n":
        top = data[0]
        rest = f" (showing top {len(data)})" if len(data) > 1 else ""
        return f"Top result by {metric_label}: {top['label']} at {top['value']:,.2f}{rest}"

    if spec.operation == "trend":
        total = sum(p["value"] for p in data)
        return f"{metric_label.capitalize()} across {len(data)} periods, totaling {total:,.2f}"

    # groupby_aggregate
    return f"Breakdown by {spec.group_by} ({len(data)} groups) -- top: {data[0]['label']} at {data[0]['value']:,.2f}"
