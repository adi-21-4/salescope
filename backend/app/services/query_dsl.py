import pandas as pd

from app.services.llm.schemas import QueryFilter, QuerySpec

# The LLM never sees or writes pandas/SQL -- it only ever produces a QuerySpec
# (a JSON object matching a fixed schema), and this module is the ONLY code
# that turns that spec into an actual computation. There is no exec() of
# model-authored text anywhere in this path, so there is nothing to sandbox
# escape: the DSL is data, not code.

_COLUMN_MAP = {
    "date": "sale_date",
    "product": "product_name",
    "category": "category",
    "location": "location",
    "payment_method": "payment_method",
}

_METRIC_COLUMN = {
    "revenue": "revenue",
    "quantity": "quantity",
    "avg_price": "unit_price",
}

_AGG_MAP = {"sum": "sum", "avg": "mean", "count": "count", "max": "max", "min": "min"}

MAX_GROUPS_RETURNED = 50


class QueryExecutionError(Exception):
    pass


def _apply_filter(df: pd.DataFrame, f: QueryFilter) -> pd.DataFrame:
    col = _COLUMN_MAP[f.column]
    if col not in df.columns:
        raise QueryExecutionError(f"Column '{f.column}' is not available in this dataset.")
    series = df[col]

    if f.column == "date":
        try:
            value: object = pd.to_datetime(f.value)
        except (ValueError, TypeError) as exc:
            raise QueryExecutionError(f"Could not parse date value '{f.value}'.") from exc
    else:
        value = f.value

    if f.op == "eq":
        mask = series == value
    elif f.op == "neq":
        mask = series != value
    elif f.op == "gt":
        mask = series > value
    elif f.op == "gte":
        mask = series >= value
    elif f.op == "lt":
        mask = series < value
    elif f.op == "lte":
        mask = series <= value
    elif f.op == "in":
        values = [v.strip() for v in f.value.split(",")]
        mask = series.isin(values)
    else:
        raise QueryExecutionError(f"Unsupported filter operator: {f.op}")

    return df[mask]


def _metric_series(df: pd.DataFrame, metric: str) -> pd.Series:
    if metric == "count":
        return pd.Series(1, index=df.index)
    col = _METRIC_COLUMN[metric]
    if col not in df.columns:
        raise QueryExecutionError(f"Metric '{metric}' is not available in this dataset.")
    return df[col]


def execute_query(df: pd.DataFrame, spec: QuerySpec) -> dict:
    working = df
    for f in spec.filters:
        working = _apply_filter(working, f)

    agg_name = _AGG_MAP[spec.agg]

    if spec.operation in ("groupby_aggregate", "top_n"):
        if not spec.group_by:
            raise QueryExecutionError("This question needs a column to group by (e.g. category, product).")
        group_col = _COLUMN_MAP[spec.group_by]
        if group_col not in working.columns:
            raise QueryExecutionError(f"Column '{spec.group_by}' is not available in this dataset.")

        working = working.assign(__metric__=_metric_series(working, spec.metric))
        grouped = working.groupby(group_col)["__metric__"].agg(agg_name)
        grouped = grouped.sort_values(ascending=(spec.order == "asc"))

        limit = spec.limit if spec.operation == "top_n" else None
        grouped = grouped.head(limit or MAX_GROUPS_RETURNED)

        data = [{"label": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]
        return {"data": data, "chart_type": spec.chart_type}

    if spec.operation == "trend":
        freq = "W" if (spec.granularity or "week") == "week" else "MS"
        working = working.assign(__metric__=_metric_series(working, spec.metric))
        series = working.set_index("sale_date")["__metric__"].resample(freq).agg(agg_name).fillna(0)
        data = [{"label": period.date().isoformat(), "value": round(float(v), 2)} for period, v in series.items()]
        return {"data": data, "chart_type": spec.chart_type}

    if spec.operation == "single_value":
        if spec.metric == "count":
            value = float(len(working))
        else:
            metric_series = _metric_series(working, spec.metric)
            value = float(getattr(metric_series, agg_name)()) if len(metric_series) else 0.0
        return {"data": [{"label": spec.metric, "value": round(value, 2)}], "chart_type": "number"}

    raise QueryExecutionError(f"Unsupported operation: {spec.operation}")
