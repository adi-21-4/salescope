import pandas as pd
import pytest

from app.services.ingestion.cleaner import (
    DuplicateRoleMappingError,
    MissingRequiredRolesError,
    clean_dataframe,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "not-a-date", "2026-01-01", "2026-01-04"],
            "Product": ["Widget", "Gadget", "Widget", "Widget", "Gizmo"],
            "Qty": ["2", "1", "3", "2", ""],
            "Price": ["$9.99", "$19.99", "$5.00", "$9.99", "$3.00"],
        }
    )


def test_missing_required_roles_raises():
    df = _sample_df()
    with pytest.raises(MissingRequiredRolesError):
        clean_dataframe(df, {"Date": "date", "Product": "product"})


def test_duplicate_role_mapping_raises():
    df = _sample_df()
    # "Qty" and "Price" both mapped to "quantity" -- ambiguous, must reject rather
    # than silently keeping only one (this caused a real data-loss incident).
    mapping = {"Date": "date", "Product": "product", "Qty": "quantity", "Price": "quantity"}
    with pytest.raises(DuplicateRoleMappingError):
        clean_dataframe(df, mapping)


def test_invalid_dates_excluded_and_counted():
    df = _sample_df()
    mapping = {"Date": "date", "Product": "product", "Qty": "quantity", "Price": "price"}
    result = clean_dataframe(df, mapping)
    assert result.invalid_date_count == 1
    assert "not-a-date" not in result.clean_df["sale_date"].astype(str).tolist()


def test_incomplete_rows_flagged_not_dropped():
    df = _sample_df()
    mapping = {"Date": "date", "Product": "product", "Qty": "quantity", "Price": "price"}
    result = clean_dataframe(df, mapping)
    # the row with empty Qty has an incomplete quantity but a valid date -> kept, flagged
    assert result.incomplete_count == 1
    incomplete_rows = result.clean_df[result.clean_df["is_incomplete"]]
    assert len(incomplete_rows) == 1


def test_exact_duplicate_rows_deduped():
    df = _sample_df()
    mapping = {"Date": "date", "Product": "product", "Qty": "quantity", "Price": "price"}
    result = clean_dataframe(df, mapping)
    # rows 0 and 3 are identical (date/product/qty/price) -> deduped to 1
    assert result.duplicate_count == 1
    assert result.rows_clean == result.rows_total - result.invalid_date_count - result.duplicate_count


def _services_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
            "Service": ["Visa Assistance", "Bus Booking", "Hotel Booking", "Flight Booking", "Bus Booking"],
            "Qty": ["1", "1", "1", "1", "1"],
            "Amount": ["41048", "60302", "31062", "96506", "17156"],
            "Status": ["Completed", "Cancelled", "Pending", "Completed", "Completed"],
        }
    )


def test_status_filter_excludes_non_included_rows():
    df = _services_df()
    mapping = {"Date": "date", "Service": "product", "Qty": "quantity", "Amount": "price", "Status": "status"}
    result = clean_dataframe(df, mapping, included_status_values=["Completed"])
    assert result.excluded_by_status_count == 2  # Cancelled + Pending
    assert result.rows_clean == 3
    assert set(result.clean_df["status_value"]) == {"Completed"}


def test_status_filter_not_applied_when_no_included_values_given():
    df = _services_df()
    mapping = {"Date": "date", "Service": "product", "Qty": "quantity", "Amount": "price", "Status": "status"}
    result = clean_dataframe(df, mapping, included_status_values=None)
    assert result.excluded_by_status_count == 0
    assert result.rows_clean == 5


def test_quantity_defaults_to_one_when_unmapped():
    # Booking-style data with no quantity column at all -- each row is one sale.
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02"],
            "Service": ["Visa Assistance", "Bus Booking"],
            "Amount": ["41048", "60302"],
        }
    )
    mapping = {"Date": "date", "Service": "product", "Amount": "price"}
    result = clean_dataframe(df, mapping)
    assert result.rows_clean == 2
    assert (result.clean_df["quantity"] == 1.0).all()
    assert not result.clean_df["is_incomplete"].any()


def test_missing_price_or_line_total_raises():
    df = pd.DataFrame({"Date": ["2026-01-01"], "Product": ["Widget"]})
    with pytest.raises(MissingRequiredRolesError):
        clean_dataframe(df, {"Date": "date", "Product": "product"})


def _sweets_shop_df() -> pd.DataFrame:
    # Mirrors a real file: has BOTH a per-unit "Unit Price" and an already
    # line-total "Net Amount" (qty * unit price, net of a discount).
    return pd.DataFrame(
        {
            "Date": ["2026-06-07", "2026-06-08", "2026-06-15"],
            "Product": ["Motichoor Ladoo", "Rasgulla", "Rasmalai"],
            "Quantity": ["5", "1", "3"],
            "Unit Price": ["420", "300", "500"],
            "Net Amount": ["1890.0", "270.0", "1500.0"],  # discounted totals
        }
    )


def test_line_total_does_not_get_multiplied_by_quantity_again():
    # This is the exact bug: mapping an already-total "Net Amount" column as if
    # it were a per-unit "price" would compute revenue = quantity * net_amount,
    # inflating revenue several-fold. Mapping it as "line_total" must instead
    # back out a per-unit price so quantity * unit_price == the original total.
    df = _sweets_shop_df()
    mapping = {"Date": "date", "Product": "product", "Quantity": "quantity", "Net Amount": "line_total"}
    result = clean_dataframe(df, mapping)
    revenue = (result.clean_df["quantity"] * result.clean_df["unit_price"]).tolist()
    assert revenue == pytest.approx([1890.0, 270.0, 1500.0])


def test_price_role_still_multiplies_by_quantity_as_before():
    df = _sweets_shop_df()
    mapping = {"Date": "date", "Product": "product", "Quantity": "quantity", "Unit Price": "price"}
    result = clean_dataframe(df, mapping)
    revenue = (result.clean_df["quantity"] * result.clean_df["unit_price"]).tolist()
    # 5*420=2100, 1*300=300, 3*500=1500 -- the pre-discount gross amounts
    assert revenue == pytest.approx([2100.0, 300.0, 1500.0])


def test_line_total_with_zero_quantity_flagged_incomplete_not_inf():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01"],
            "Product": ["Widget"],
            "Quantity": ["0"],
            "Net Amount": ["50.0"],
        }
    )
    mapping = {"Date": "date", "Product": "product", "Quantity": "quantity", "Net Amount": "line_total"}
    result = clean_dataframe(df, mapping)
    assert result.incomplete_count == 1
    assert result.clean_df["unit_price"].isna().all()
