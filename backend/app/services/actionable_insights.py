"""Deterministic, explainable insight cards built only from dataset aggregates."""

import math

import pandas as pd


def _point(label: str, value: float, compare: float | None = None, marked: bool = False, note: str | None = None) -> dict:
    return {
        "label": str(label),
        "value": round(float(value), 2),
        "compare_value": round(float(compare), 2) if compare is not None else None,
        "marked": marked,
        "note": note,
    }


def _drivers(df: pd.DataFrame, current_start, previous_start, days: int) -> list[dict]:
    latest = df["sale_date"].max().normalize()
    current_end = latest + pd.Timedelta(days=1)
    current = df[(df.sale_date >= current_start) & (df.sale_date < current_end)]
    previous = df[(df.sale_date >= previous_start) & (df.sale_date < current_start)]
    best = []
    for column in ("product_name", "category", "agent", "location", "payment_method"):
        if column not in df or df[column].dropna().nunique() < 2:
            continue
        left = current.groupby(column).revenue.sum()
        right = previous.groupby(column).revenue.sum()
        for name in set(left.index) | set(right.index):
            now, before = float(left.get(name, 0)), float(right.get(name, 0))
            best.append({"label": str(name), "dimension": column, "current": round(now, 2), "previous": round(before, 2), "change": round(now - before, 2)})
    best.sort(key=lambda row: abs(row["change"]), reverse=True)
    return best[:4]


def _share_change(df: pd.DataFrame, column: str, days: int, id_: str, label: str, chart_ref: str) -> dict | None:
    if column not in df or df[column].dropna().nunique() < 2:
        return None
    latest = df.sale_date.max().normalize()
    first = df.sale_date.min().normalize()
    if (latest - first).days < days * 2 - 1:
        return None
    current_start = latest - pd.Timedelta(days=days - 1)
    previous_start = current_start - pd.Timedelta(days=days)
    current = df[(df.sale_date >= current_start) & (df.sale_date < latest + pd.Timedelta(days=1))]
    previous = df[(df.sale_date >= previous_start) & (df.sale_date < current_start)]
    if current.empty or previous.empty:
        return None
    cur_total, prev_total = float(current.revenue.sum()), float(previous.revenue.sum())
    if cur_total <= 0 or prev_total <= 0:
        return None
    cur_share = current.groupby(column).revenue.sum() / cur_total * 100
    prev_share = previous.groupby(column).revenue.sum() / prev_total * 100
    names = set(cur_share.index) | set(prev_share.index)
    shifts = [{"label": str(name), "now": float(cur_share.get(name, 0)), "before": float(prev_share.get(name, 0))} for name in names]
    shifts.sort(key=lambda row: abs(row["now"] - row["before"]), reverse=True)
    largest = shifts[0]
    delta = largest["now"] - largest["before"]
    if abs(delta) < 5:
        return None
    points = [_point(row["label"], row["now"], row["before"]) for row in shifts[:8]]
    return {
        "id": id_, "category": column, "title": f"{label} mix changed", "summary": f"{largest['label']} shifted {abs(delta):.1f} percentage points in revenue share.",
        "explanation": f"Compares each {label.lower()}’s share of revenue in the latest {days} days with the prior {days} days. This is a share change, not a revenue change.",
        "period": f"Latest {days} days vs previous {days} days", "metric_label": "Largest share shift", "metric_value": round(delta, 1), "value_format": "percentage_points",
                "point_format": "percent",
        "chart_ref": chart_ref, "points": points, "drivers": [],
        "suggested_question": f"What was revenue by {label.lower()}?",
    }


def build_actionable_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    work = df.dropna(subset=["sale_date", "revenue"]).copy()
    if work.empty:
        return []
    work["sale_date"] = pd.to_datetime(work["sale_date"])
    latest = work.sale_date.max().normalize()
    first = work.sale_date.min().normalize()
    cards: list[dict] = []

    # Adjacent rolling seven-day windows; each plotted weekday compares like-for-like.
    if (latest - first).days >= 13:
        current_start = latest - pd.Timedelta(days=6)
        previous_start = current_start - pd.Timedelta(days=7)
        current = work[(work.sale_date >= current_start) & (work.sale_date < latest + pd.Timedelta(days=1))]
        previous = work[(work.sale_date >= previous_start) & (work.sale_date < current_start)]
        current_total, previous_total = float(current.revenue.sum()), float(previous.revenue.sum())
        if previous_total > 0 and not current.empty:
            pct = (current_total - previous_total) / previous_total * 100
            points = []
            for offset in range(7):
                current_day = current_start + pd.Timedelta(days=offset)
                prior_day = current_day - pd.Timedelta(days=7)
                now = float(current.loc[current.sale_date.dt.normalize() == current_day, "revenue"].sum())
                before = float(previous.loc[previous.sale_date.dt.normalize() == prior_day, "revenue"].sum())
                points.append(_point(current_day.strftime("%a"), now, before))
            change_word = "up" if pct >= 0 else "down"
            cards.append({
                "id": "revenue_change", "category": "trend", "title": f"Revenue {change_word} {abs(pct):.1f}% week over week",
                "summary": f"The latest 7 days brought in ₹{current_total:,.0f}, compared with ₹{previous_total:,.0f} in the prior 7 days.",
                "explanation": "Revenue totals for two adjacent 7-day windows ending on the latest sale date. Daily bars pair the same weekday; drivers rank the largest absolute revenue changes across mapped dimensions.",
                "period": "Latest 7 days vs previous 7 days", "metric_label": "Revenue change", "metric_value": round(pct, 1), "value_format": "percent",
                "point_format": "currency",
                "chart_ref": "revenue-chart", "points": points,
                "drivers": _drivers(work, current_start, previous_start, 7),
                "suggested_question": "Which products earned the most in the latest week?",
            })

    # Robust median/MAD outlier scan over selling days, avoiding closed-day zeros.
    daily = work.groupby(work.sale_date.dt.normalize()).revenue.sum().sort_index()
    if len(daily) >= 14:
        median = float(daily.median())
        mad = float((daily - median).abs().median())
        limit = max(3.5 * 1.4826 * mad, 0.6 * median, 1.0)
        deviations = (daily - median).abs()
        unusual = deviations[deviations > limit]
        if not unusual.empty:
            day = unusual.idxmax()
            actual = float(daily.loc[day])
            direction = "above" if actual > median else "below"
            recent = daily.tail(18)
            cards.append({
                "id": "sales_anomaly", "category": "anomaly", "title": f"Unusual sales day: {day.strftime('%b %d').replace(' 0', ' ')}",
                "summary": f"Revenue was ₹{actual:,.0f}, {direction} the typical selling day of ₹{median:,.0f}.",
                "explanation": "Compares daily revenue on selling days with the dataset median. A day is flagged only when it exceeds the larger of 3.5 scaled median absolute deviations, 60% of the median, or ₹1. This robust baseline is less affected by one large sale than an average.",
                "period": f"{len(daily)} selling days observed", "metric_label": "Revenue vs median", "metric_value": round(actual - median, 2), "value_format": "currency",
                "point_format": "currency",
                "chart_ref": "revenue-chart", "points": [_point(index.strftime("%b %d"), value, median, index == day) for index, value in recent.items()],
                "drivers": [
                    {"label": str(name), "dimension": "product_name", "current": round(float(value), 2), "previous": 0.0, "change": round(float(value), 2)}
                    for name, value in work[work.sale_date.dt.normalize() == day].groupby("product_name").revenue.sum().sort_values(ascending=False).head(4).items()
                ],
                "suggested_question": "Which products earned the most on the unusual sales day?",
            })

    # Pareto concentration: contribution from the leading 20% of distinct products.
    if work.product_name.notna().sum() > 0:
        products = work.dropna(subset=["product_name"]).groupby("product_name").revenue.sum().sort_values(ascending=False)
        if len(products) >= 3:
            leading_count = max(1, math.ceil(len(products) * 0.2))
            total = float(products.sum())
            cumulative = products.cumsum() / total * 100 if total else products * 0
            share = float(products.head(leading_count).sum()) / total * 100 if total else 0
            cards.append({
                "id": "product_concentration", "category": "product", "title": f"{leading_count} products drive {share:.1f}% of revenue",
                "summary": f"The top 20% of products account for ₹{float(products.head(leading_count).sum()):,.0f} of recorded revenue.",
                "explanation": "Products are ranked by revenue, then the smallest leading group representing at least 20% of distinct products is compared with total revenue. Cumulative share reveals concentration and dependence on a few products.",
                "period": f"{len(products)} distinct products", "metric_label": "Top-product revenue share", "metric_value": round(share, 1), "value_format": "percent",
                "point_format": "currency",
                "chart_ref": "product-charts", "points": [_point(name, float(value), note=f"{float(cumulative.loc[name]):.1f}% cumulative") for name, value in products.head(8).items()],
                "drivers": [], "suggested_question": "What are my top 5 products by revenue?",
            })

    payment = _share_change(work, "payment_method", 30, "payment_shift", "Payment method", "sales-breakdowns")
    location = _share_change(work, "location", 30, "location_shift", "Location", "sales-breakdowns")
    cards.extend(card for card in (payment, location) if card)

    # Gross margin is shown only for rows with a mapped unit cost.
    if "unit_cost" in work and "gross_profit" in work:
        known_cost = work.dropna(subset=["unit_cost", "gross_profit"])
        if not known_cost.empty:
            known_revenue = float(known_cost.revenue.sum())
            gross_profit = float(known_cost.gross_profit.sum())
            if known_revenue > 0:
                margin = gross_profit / known_revenue * 100
                by_product = known_cost.groupby("product_name").gross_profit.sum().sort_values(ascending=False) if "product_name" in known_cost else pd.Series(dtype=float)
                coverage = len(known_cost) / len(work) * 100
                cards.append({
                    "id": "profit_margin", "category": "profit", "title": f"Gross margin is {margin:.1f}% on cost-mapped sales",
                    "summary": f"Estimated gross profit is ₹{gross_profit:,.0f} across {coverage:.0f}% of included sales with cost data.",
                    "explanation": "Gross margin = (revenue − quantity × unit cost) ÷ revenue. This uses only rows with a mapped unit cost; the coverage percentage makes missing cost data visible. It excludes overhead, tax, and other operating expenses.",
                    "period": f"{first.strftime('%b %d, %Y')} – {latest.strftime('%b %d, %Y')}",
                    "metric_label": "Gross margin · cost-mapped rows", "metric_value": round(margin, 1), "value_format": "percent", "point_format": "currency",
                    "chart_ref": None, "points": [_point(str(name), float(value)) for name, value in by_product.head(8).items()], "drivers": [], "suggested_question": None,
                })

    # Customer cohorts need a stable customer identifier and at least one full
    # follow-up month. Do not send identifiers to an LLM or expose them in cards.
    if "customer_id" in work:
        customers = work.dropna(subset=["customer_id"]).copy()
        customers = customers[customers.customer_id.astype(str).str.strip() != ""]
        customers["month"] = customers.sale_date.dt.to_period("M")
        if customers.customer_id.nunique() >= 3 and customers.month.nunique() >= 2:
            first_month = customers.groupby("customer_id").month.min()
            customers["cohort"] = customers.customer_id.map(first_month)
            latest_observed_month = customers.month.max()
            latest_complete_month = latest_observed_month - 1
            cohorts = []
            month_one_rates = []
            complete_cohorts = [cohort for cohort in sorted(customers.cohort.unique()) if cohort < latest_complete_month]
            for cohort in complete_cohorts[-8:]:
                cohort_rows = customers[customers.cohort == cohort]
                cohort_ids = set(cohort_rows.customer_id)
                cohort_size = len(cohort_ids)
                points = []
                max_offset = min(6, (latest_complete_month.year - cohort.year) * 12 + latest_complete_month.month - cohort.month)
                for offset in range(max_offset + 1):
                    period = cohort + offset
                    active = int(cohort_rows.loc[cohort_rows.month == period, "customer_id"].nunique())
                    pct = active / cohort_size * 100 if cohort_size else 0
                    points.append(_point(f"{cohort.strftime('%b %Y')} · M{offset}", pct, note=f"{active} of {cohort_size} customers"))
                    if offset == 1 and cohort_size:
                        month_one_rates.append(pct)
                cohorts.extend(points)
            if month_one_rates:
                avg_return = sum(month_one_rates) / len(month_one_rates)
                cards.append({
                    "id": "customer_retention", "category": "retention", "title": f"{avg_return:.1f}% average month-one repeat rate",
                    "summary": f"Across {len(month_one_rates)} completed monthly cohorts, this share of customers purchased again in their next calendar month.",
                    "explanation": "Customers are grouped by the calendar month of their first recorded purchase. Month-one retention is the number of that cohort with another purchase in the next calendar month divided by the original cohort size. Only cohorts with a full follow-up month are included in the average.",
                    "period": f"{len(month_one_rates)} completed cohorts", "metric_label": "Average month-one retention", "metric_value": round(avg_return, 1), "value_format": "percent", "point_format": "percent",
                    "chart_ref": None, "points": cohorts, "drivers": [], "suggested_question": None,
                })
    return cards
