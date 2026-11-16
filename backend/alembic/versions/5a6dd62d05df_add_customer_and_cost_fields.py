"""Add optional customer and cost data for retention and margin analytics."""

import hashlib
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5a6dd62d05df"
down_revision: Union[str, None] = "e4ad741d2f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _value(value: object) -> str:
    return str(value).strip().lower()


def _hash(row: dict, include_optional: bool) -> str:
    quantity = "nan" if row["quantity"] is None else str(float(row["quantity"]))
    unit_price = "nan" if row["unit_price"] is None else str(float(row["unit_price"]))
    parts = [row["sale_date"].isoformat(), _value(row["product_name"]), quantity, unit_price,
             _value(row["location"]), _value(row["agent"])]
    if include_optional:
        parts.extend([_value(row["customer_id"]), str(float(row["unit_cost"])) if row["unit_cost"] is not None else "None"])
    parts.append(_value(row["payment_method"]))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _rehash(include_optional: bool) -> None:
    connection = op.get_bind()
    columns = "id, sale_date, product_name, quantity, unit_price, location, agent, payment_method"
    if include_optional:
        columns += ", customer_id, unit_cost"
    result = connection.execute(sa.text(f"SELECT {columns} FROM sales_records ORDER BY id"))
    batch = []
    for row in result.mappings():
        batch.append({"id": row["id"], "row_hash": _hash(dict(row), include_optional)})
        if len(batch) == 1000:
            connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)
            batch.clear()
    if batch:
        connection.execute(sa.text("UPDATE sales_records SET row_hash = :row_hash WHERE id = :id"), batch)


def upgrade() -> None:
    op.add_column("sales_records", sa.Column("customer_id", sa.String(length=255), nullable=True))
    op.add_column("sales_records", sa.Column("unit_cost", sa.Numeric(), nullable=True))
    op.add_column(
        "sales_records",
        sa.Column("gross_profit", sa.Numeric(), sa.Computed("quantity * (unit_price - unit_cost)", persisted=True), nullable=True),
    )
    _rehash(include_optional=True)


def downgrade() -> None:
    op.drop_column("sales_records", "gross_profit")
    op.drop_column("sales_records", "unit_cost")
    op.drop_column("sales_records", "customer_id")
    _rehash(include_optional=False)
