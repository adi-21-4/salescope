import pandas as pd

from app.services.ingestion.column_detector import detect_columns


def _roles(df: pd.DataFrame) -> dict[str, str | None]:
    return {d.column: d.role for d in detect_columns(df)}


def test_standard_headers_detected():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "Product": ["Widget", "Gadget", "Widget"],
            "Quantity": ["3", "1", "2"],
            "Price": ["9.99", "19.99", "9.99"],
            "Category": ["Tools", "Electronics", "Tools"],
        }
    )
    roles = _roles(df)
    assert roles["Date"] == "date"
    assert roles["Product"] == "product"
    assert roles["Quantity"] == "quantity"
    assert roles["Price"] == "price"
    assert roles["Category"] == "category"


def test_nonstandard_headers_detected_via_dtype_sniffing():
    df = pd.DataFrame(
        {
            "Txn_DT": ["01/15/2026", "01/16/2026", "01/17/2026", "01/18/2026", "01/19/2026"],
            "Item": ["Blue Shirt", "Red Hat", "Green Scarf", "Blue Shirt", "Yellow Socks"],
            "Units": ["2", "1", "3", "1", "5"],
            "Cost": ["$24.50", "$12.00", "$8.75", "$24.50", "$3.25"],
        }
    )
    roles = _roles(df)
    assert roles["Txn_DT"] == "date"
    assert roles["Units"] == "quantity"
    assert roles["Cost"] == "price"
    # "Item" is high-cardinality text -> product
    assert roles["Item"] == "product"


def test_conflicting_date_columns_only_one_wins():
    df = pd.DataFrame(
        {
            "Order Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "Ship Date": ["2026-01-05", "2026-01-06", "2026-01-07"],
        }
    )
    detections = {d.column: d for d in detect_columns(df)}
    date_winners = [c for c, d in detections.items() if d.role == "date"]
    assert len(date_winners) == 1
    # the loser should still surface "date" as a candidate for the UI
    loser = [c for c in detections if c not in date_winners][0]
    assert any(c.role == "date" for c in detections[loser].candidates)
    # demoted columns must report 0 confidence for their (now-None) role, not
    # the stale pre-demotion score -- confidence and role must stay consistent
    assert detections[loser].confidence == 0.0


def test_low_confidence_column_left_unmapped():
    df = pd.DataFrame({"Notes": ["fragile", "handle with care", "n/a"]})
    roles = _roles(df)
    assert roles["Notes"] is None


def test_status_column_detected_by_name_and_vocabulary():
    df = pd.DataFrame(
        {
            "Status": ["Completed", "Cancelled", "Pending", "Completed", "Completed"],
        }
    )
    detections = {d.column: d for d in detect_columns(df)}
    assert detections["Status"].role == "status"
    assert set(detections["Status"].distinct_values) == {"Cancelled", "Completed", "Pending"}


def test_status_vocabulary_detected_even_without_status_in_name():
    # oddly-named column, but values are recognizable order-status vocabulary
    df = pd.DataFrame({"Booking_Result": ["Paid", "Refunded", "Paid", "Paid", "Void"]})
    roles = _roles(df)
    assert roles["Booking_Result"] == "status"


def test_low_cardinality_non_status_text_still_prefers_category():
    df = pd.DataFrame({"Dept": ["Tools", "Electronics", "Tools", "Tools", "Electronics"]})
    roles = _roles(df)
    assert roles["Dept"] == "category"


def test_location_column_detected_by_name():
    df = pd.DataFrame({"Store Location": ["Downtown", "Uptown", "Downtown", "Mall"]})
    roles = _roles(df)
    assert roles["Store Location"] == "location"


def test_sales_agent_column_detected_as_location():
    df = pd.DataFrame({"Sales_Executive": ["Amit", "Rachna", "Amit", "Neha", "Kiran"]})
    roles = _roles(df)
    assert roles["Sales_Executive"] == "location"


def test_payment_method_column_detected_by_name():
    df = pd.DataFrame({"Payment_Method": ["Cash", "Credit Card", "UPI", "Cash", "Bank Transfer"]})
    roles = _roles(df)
    assert roles["Payment_Method"] == "payment_method"


def test_payment_method_does_not_collide_with_payment_status():
    df = pd.DataFrame(
        {
            "Payment_Method": ["Cash", "Credit Card", "UPI"],
            "Payment_Status": ["Paid", "Pending", "Paid"],
        }
    )
    roles = _roles(df)
    assert roles["Payment_Method"] == "payment_method"
    assert roles["Payment_Status"] == "status"


def test_unit_price_and_line_total_columns_get_different_roles():
    # The exact real-world file that caused a 3.6x revenue overstatement: a
    # per-unit "Unit Price" alongside an already-multiplied "Net Amount". These
    # must land on different roles, not both compete for "price".
    df = pd.DataFrame(
        {
            "Unit Price": ["320", "300", "380", "420", "500"],
            "Net Amount": ["320.0", "270.0", "380.0", "1890.0", "1500.0"],
        }
    )
    roles = _roles(df)
    assert roles["Unit Price"] == "price"
    assert roles["Net Amount"] == "line_total"


def test_net_amount_preferred_over_gross_amount_for_line_total():
    df = pd.DataFrame(
        {
            "Gross Amount": ["320", "300", "2100"],
            "Net Amount": ["320", "270", "1890"],
        }
    )
    detections = {d.column: d for d in detect_columns(df)}
    winners = [c for c, d in detections.items() if d.role == "line_total"]
    assert winners == ["Net Amount"]
