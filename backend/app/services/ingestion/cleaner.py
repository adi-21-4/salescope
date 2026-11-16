import hashlib
from dataclasses import dataclass

import pandas as pd

from app.services.ingestion.column_detector import CURRENCY_CHARS

REQUIRED_ROLES = ("date",)
# Exactly one of these must be mapped -- "price" is per-unit (revenue = qty *
# price); "line_total" is an already-computed total for that row (revenue =
# line_total directly, never multiplied by quantity again).
PRICE_ROLES = ("price", "line_total")


class MissingRequiredRolesError(Exception):
    pass


class DuplicateRoleMappingError(Exception):
    pass


@dataclass
class CleaningResult:
    clean_df: pd.DataFrame
    rows_total: int
    invalid_date_count: int
    excluded_by_status_count: int
    incomplete_count: int
    duplicate_count: int
    rows_clean: int


def _to_numeric(series: pd.Series) -> pd.Series:
    stripped = series.astype(str).str.replace(CURRENCY_CHARS, "", regex=True).str.replace(",", "", regex=False)
    return pd.to_numeric(stripped, errors="coerce")


def _to_clean_text(series: pd.Series) -> pd.Series:
    return series.map(lambda value: None if pd.isna(value) or not str(value).strip() else str(value).strip())


def _row_hash(row: pd.Series) -> str:
    unit_cost = None if pd.isna(row["unit_cost"]) else row["unit_cost"]
    key = "|".join(
        [
            row["sale_date"].date().isoformat(),
            str(row["product_name"]).strip().lower(),
            str(row["quantity"]),
            str(row["unit_price"]),
            str(row["location"]).strip().lower(),
            str(row["agent"]).strip().lower(),
            str(row["customer_id"]).strip().lower(),
            str(unit_cost),
            str(row["payment_method"]).strip().lower(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def clean_dataframe(
    df: pd.DataFrame,
    mapping: dict[str, str],
    included_status_values: list[str] | None = None,
) -> CleaningResult:
    """mapping: {raw_column_name: canonical_role}, role in
    {date, product, quantity, price, unit_cost, line_total, category, status, location, agent, customer_id,
    payment_method, ignore}. Exactly one of price/line_total is required (not
    both). quantity is optional -- defaults every row to 1 unit when unmapped
    (service/booking data often has no separate quantity column).

    included_status_values: when a column is mapped to "status", only rows whose
    status value is in this list count as a real sale (e.g. exclude "Cancelled" /
    "Pending" bookings from revenue). Ignored if no column is mapped to "status".
    """
    role_counts: dict[str, list[str]] = {}
    for col, role in mapping.items():
        if role != "ignore":
            role_counts.setdefault(role, []).append(col)
    duplicated = {role: cols for role, cols in role_counts.items() if len(cols) > 1}
    if duplicated:
        detail = "; ".join(f"{role}: {', '.join(cols)}" for role, cols in duplicated.items())
        raise DuplicateRoleMappingError(
            f"Each role can only be mapped to one column. Conflicting: {detail}"
        )

    role_to_col = {role: col for col, role in mapping.items() if role != "ignore"}

    missing = [role for role in REQUIRED_ROLES if role not in role_to_col]
    if not any(role in role_to_col for role in PRICE_ROLES):
        missing.append("price (or a line-total column)")
    if missing:
        raise MissingRequiredRolesError(
            f"Mapping must include columns for: {', '.join(missing)}"
        )

    working = pd.DataFrame(index=df.index)
    working["sale_date"] = pd.to_datetime(df[role_to_col["date"]], errors="coerce")
    working["product_name"] = (
        df[role_to_col["product"]].astype(str).str.strip() if "product" in role_to_col else None
    )
    working["category"] = (
        df[role_to_col["category"]].astype(str).str.strip() if "category" in role_to_col else None
    )
    working["location"] = (
        _to_clean_text(df[role_to_col["location"]]) if "location" in role_to_col else None
    )
    working["agent"] = (
        _to_clean_text(df[role_to_col["agent"]]) if "agent" in role_to_col else None
    )
    working["customer_id"] = (
        _to_clean_text(df[role_to_col["customer_id"]]) if "customer_id" in role_to_col else None
    )
    working["payment_method"] = (
        df[role_to_col["payment_method"]].astype(str).str.strip() if "payment_method" in role_to_col else None
    )
    # Service businesses often have no quantity column at all -- each row IS one
    # unit of service (one appointment, one booking). Default to 1 rather than
    # blocking the upload; a shop that genuinely tracks quantity just maps it.
    working["quantity"] = _to_numeric(df[role_to_col["quantity"]]) if "quantity" in role_to_col else 1.0
    if "line_total" in role_to_col:
        # Back out a per-unit price from the total so the DB's generated
        # `revenue = quantity * unit_price` column still lands on the right
        # number: quantity * (line_total / quantity) == line_total. Dividing by
        # a zero/invalid quantity produces inf, which is flagged incomplete
        # rather than silently treated as a real price.
        line_total = _to_numeric(df[role_to_col["line_total"]])
        derived_unit_price = line_total / working["quantity"]
        working["unit_price"] = derived_unit_price.replace([float("inf"), float("-inf")], None)
    else:
        working["unit_price"] = _to_numeric(df[role_to_col["price"]])
    working["unit_cost"] = _to_numeric(df[role_to_col["unit_cost"]]) if "unit_cost" in role_to_col else None
    if "status" in role_to_col:
        working["status_value"] = df[role_to_col["status"]].astype(str).str.strip()

    rows_total = len(working)

    invalid_date_mask = working["sale_date"].isna()
    invalid_date_count = int(invalid_date_mask.sum())
    working = working[~invalid_date_mask].copy()

    excluded_by_status_count = 0
    if "status" in role_to_col and included_status_values is not None:
        included_lower = {v.strip().lower() for v in included_status_values}
        status_mask = working["status_value"].str.lower().isin(included_lower)
        excluded_by_status_count = int((~status_mask).sum())
        working = working[status_mask].copy()

    incomplete_mask = working["quantity"].isna() | working["unit_price"].isna()
    working["is_incomplete"] = incomplete_mask
    incomplete_count = int(incomplete_mask.sum())

    working["row_hash"] = working.apply(_row_hash, axis=1)
    before_dedup = len(working)
    working = working.drop_duplicates(subset="row_hash", keep="first")
    duplicate_count = before_dedup - len(working)

    return CleaningResult(
        clean_df=working,
        rows_total=rows_total,
        invalid_date_count=invalid_date_count,
        excluded_by_status_count=excluded_by_status_count,
        incomplete_count=incomplete_count,
        duplicate_count=duplicate_count,
        rows_clean=len(working),
    )
