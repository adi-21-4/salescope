"""Track sales agents separately from physical locations."""

import hashlib
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4ad741d2f90"
down_revision: Union[str, None] = "dd077d95ed3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AGENT_COLUMN_NAME = re.compile(
    r"(?:agent|sales[\s_-]*rep|sales[\s_-]*executive|salesperson|"
    r"sales[\s_-]*representative|representative|executive|assigned[\s_-]*to|"
    r"staff|(?<![a-z])rep(?![a-z]))",
    re.IGNORECASE,
)


def _clean_value(value: object) -> str:
    return str(value).strip().lower()


def _is_agent_column(column_name: str) -> bool:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", column_name)
    return bool(AGENT_COLUMN_NAME.search(separated))


def _hash_text(record: dict) -> str:
    quantity = "nan" if record["quantity"] is None else str(float(record["quantity"]))
    unit_price = "nan" if record["unit_price"] is None else str(float(record["unit_price"]))
    values = [
        record["sale_date"].isoformat(),
        str(record["product_name"]).strip().lower(),
        quantity,
        unit_price,
        _clean_value(record["location"]),
        _clean_value(record["agent"]),
        _clean_value(record["payment_method"]),
    ]
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _legacy_hash_text(record: dict) -> str:
    quantity = "nan" if record["quantity"] is None else str(float(record["quantity"]))
    unit_price = "nan" if record["unit_price"] is None else str(float(record["unit_price"]))
    values = [
        record["sale_date"].isoformat(),
        str(record["product_name"]).strip().lower(),
        quantity,
        unit_price,
        _clean_value(record["location"]),
        _clean_value(record["payment_method"]),
    ]
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column("sales_records", sa.Column("agent", sa.String(length=255), nullable=True))
    connection = op.get_bind()

    # Only reinterpret legacy location values when the saved mapping identifies
    # that exact source column as an agent/rep field. Ambiguous rows stay put.
    mappings = connection.execute(sa.text(
        "SELECT id, confirmed_column_mapping FROM uploaded_datasets "
        "WHERE confirmed_column_mapping IS NOT NULL"
    ))
    legacy_agent_datasets = []
    for dataset_id, mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        if any(
            role == "location" and _is_agent_column(column_name)
            for column_name, role in mapping.items()
        ):
            legacy_agent_datasets.append(dataset_id)

    for dataset_id in legacy_agent_datasets:
        connection.execute(sa.text(
            "UPDATE sales_records SET agent = location, location = NULL "
            "WHERE dataset_id = :dataset_id AND location IS NOT NULL"
        ), {"dataset_id": dataset_id})

    # Include the new canonical field in duplicate detection for future imports.
    result = connection.execute(sa.text(
        "SELECT id, sale_date, product_name, quantity, unit_price, location, agent, "
        "payment_method FROM sales_records ORDER BY id"
    ))
    batch = []
    for row in result.mappings():
        batch.append({"id": row["id"], "row_hash": _hash_text(dict(row))})
        if len(batch) == 1000:
            connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)
            batch.clear()
    if batch:
        connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text(
        "UPDATE sales_records SET location = COALESCE(location, agent)"
    ))
    result = connection.execute(sa.text(
        "SELECT id, sale_date, product_name, quantity, unit_price, location, agent, "
        "payment_method FROM sales_records ORDER BY id"
    ))
    batch = []
    for row in result.mappings():
        batch.append({"id": row["id"], "row_hash": _legacy_hash_text(dict(row))})
        if len(batch) == 1000:
            connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)
            batch.clear()
    if batch:
        connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)
    op.drop_column("sales_records", "agent")
