from dataclasses import dataclass, field

import pandas as pd

ROLE_KEYWORDS: dict[str, list[str]] = {
    "date": ["date", "dt", "order date", "sale date", "transaction date", "txn date", "day"],
    "product": ["product", "item", "sku", "description", "name", "product name", "service"],
    "quantity": ["qty", "quantity", "units", "count", "sold"],
    # "price" means PER-UNIT price -- revenue is computed as quantity * price.
    "price": ["price", "unit price", "unit cost", "cost", "rate"],
    # "line_total" means an already-computed total for that row (qty * price,
    # sometimes net of discount) -- must NOT be multiplied by quantity again.
    # Kept as a distinct role from "price" specifically because a file can
    # contain both (e.g. "Unit Price" AND "Net Amount"), and picking the wrong
    # one silently multiplies revenue by quantity twice.
    "line_total": [
        "amount", "total", "gross amount", "net amount", "gross total", "net total",
        "line total", "sale amount", "total amount", "revenue",
    ],
    "category": ["category", "type", "dept", "department", "class"],
    "status": ["status", "state", "booking status", "order status", "payment status"],
    "location": [
        "location", "branch", "store", "outlet", "shop", "site",
        "agent", "rep", "sales rep", "salesperson", "executive", "assigned to", "staff",
    ],
    "payment_method": [
        "payment method", "payment_method", "paymentmethod", "pay method",
        "paid via", "payment type", "payment mode", "tender type",
    ],
}
ROLES = list(ROLE_KEYWORDS.keys())

STATUS_VOCAB = {
    "completed", "complete", "cancelled", "canceled", "cancel", "pending",
    "refunded", "refund", "paid", "unpaid", "fulfilled", "shipped", "delivered",
    "returned", "void", "failed", "fail", "processing", "confirmed", "declined",
    "success", "successful", "open", "closed", "active", "inactive",
}

CONFIDENCE_THRESHOLD = 0.5
SAMPLE_SIZE = 200
CURRENCY_CHARS = r"[$,€£₹]"
DISTINCT_VALUES_CAP = 30


@dataclass
class RoleScore:
    role: str
    confidence: float


@dataclass
class ColumnDetection:
    column: str
    role: str | None
    confidence: float
    candidates: list[RoleScore] = field(default_factory=list)
    sample_values: list[str] = field(default_factory=list)
    distinct_values: list[str] = field(default_factory=list)


def _name_keyword_scores(column_name: str) -> dict[str, float]:
    name = column_name.strip().lower()
    scores: dict[str, float] = {}
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            scores[role] = 0.7
    # When both a "gross" and "net" total column exist, prefer net: it already
    # reflects discounts/returns, which is what a shop actually cares about as
    # revenue -- a small nudge so it wins the same-role conflict resolution.
    if "line_total" in scores:
        if "net" in name:
            scores["line_total"] += 0.05
        elif "gross" in name:
            scores["line_total"] -= 0.05
    return scores


def _status_vocab_overlap(sample: pd.Series) -> float:
    uniques = {v.strip().lower() for v in sample.unique()}
    if not uniques:
        return 0.0
    matches = sum(1 for v in uniques if v in STATUS_VOCAB)
    return matches / len(uniques)


def _dtype_sniff_scores(series: pd.Series) -> dict[str, float]:
    sample = series.dropna().astype(str).str.strip()
    sample = sample[sample != ""].head(SAMPLE_SIZE)
    if len(sample) == 0:
        return {}

    scores: dict[str, float] = {}

    best_date_hit_rate = 0.0
    for dayfirst in (False, True):
        parsed = pd.to_datetime(sample, errors="coerce", dayfirst=dayfirst)
        best_date_hit_rate = max(best_date_hit_rate, parsed.notna().mean())
    if best_date_hit_rate > 0.8:
        scores["date"] = 0.3 * best_date_hit_rate

    cleaned_numeric = sample.str.replace(CURRENCY_CHARS, "", regex=True).str.replace(",", "", regex=False)
    numeric = pd.to_numeric(cleaned_numeric, errors="coerce")
    numeric_hit_rate = numeric.notna().mean()

    if numeric_hit_rate > 0.8:
        values = numeric.dropna()
        is_integer_like = (values == values.round()).mean() > 0.9
        avg_abs_value = values.abs().mean()
        if is_integer_like and avg_abs_value < 1000:
            scores["quantity"] = 0.3 * numeric_hit_rate
        else:
            scores["price"] = 0.3 * numeric_hit_rate
    else:
        # A status-vocabulary match is checked independently of the cardinality
        # split below — a status column (Completed/Cancelled/Pending) is
        # low-cardinality like a category, but should win on vocabulary content
        # even when its header doesn't literally say "status".
        vocab_overlap = _status_vocab_overlap(sample)
        if vocab_overlap >= 0.4:
            scores["status"] = 0.3 + 0.5 * vocab_overlap

        unique_ratio = sample.nunique() / len(sample)
        if unique_ratio < 0.05:
            scores["category"] = 0.3
        elif unique_ratio > 0.3:
            scores["product"] = 0.3

    return scores


def _distinct_values(series: pd.Series, cap: int = DISTINCT_VALUES_CAP) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    uniques = list(pd.unique(values))
    if len(uniques) == 0 or len(uniques) > cap:
        return []
    return sorted(uniques)


def _detect_single_column(column_name: str, series: pd.Series) -> ColumnDetection:
    name_scores = _name_keyword_scores(column_name)
    dtype_scores = _dtype_sniff_scores(series)

    combined = {role: name_scores.get(role, 0.0) + dtype_scores.get(role, 0.0) for role in ROLES}
    candidates = sorted(
        (RoleScore(role, round(min(conf, 1.0), 2)) for role, conf in combined.items() if conf > 0),
        key=lambda c: c.confidence,
        reverse=True,
    )
    best = candidates[0] if candidates else None
    role = best.role if best and best.confidence >= CONFIDENCE_THRESHOLD else None

    sample_values = series.dropna().astype(str).head(5).tolist()
    return ColumnDetection(
        column=column_name,
        role=role,
        confidence=best.confidence if best else 0.0,
        candidates=candidates[:3],
        sample_values=sample_values,
        distinct_values=_distinct_values(series),
    )


def detect_columns(df: pd.DataFrame) -> list[ColumnDetection]:
    """Score every column against the canonical roles and assign the best guess.

    Two-pass: score each column independently, then resolve cross-column conflicts
    (e.g. two date-like columns) by keeping the higher-confidence column's
    assignment and demoting the loser to unmapped — its next-best candidate is
    still visible in `candidates` so the UI can offer it as an alternative.
    """
    results = [_detect_single_column(col, df[col]) for col in df.columns]

    assigned_columns_by_role: dict[str, list[ColumnDetection]] = {}
    for r in results:
        if r.role is not None:
            assigned_columns_by_role.setdefault(r.role, []).append(r)

    for role, columns in assigned_columns_by_role.items():
        if len(columns) <= 1:
            continue
        columns.sort(key=lambda c: c.confidence, reverse=True)
        for loser in columns[1:]:
            loser.role = None
            loser.confidence = 0.0  # demoted -- keep role/confidence consistent (see ColumnDetection invariant)

    return results
