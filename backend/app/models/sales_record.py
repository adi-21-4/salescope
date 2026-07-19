import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Computed, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class SalesRecord(Base):
    __tablename__ = "sales_records"
    __table_args__ = (
        # Scoped by shop only (not dataset) so re-uploading the same file — which
        # creates a new UploadedDataset row — still dedupes against rows already
        # persisted from a prior upload, rather than only catching dupes within a
        # single file.
        UniqueConstraint("shop_id", "row_hash", name="uq_sales_records_shop_hash"),
        Index("ix_sales_records_shop_date", "shop_id", "sale_date"),
        Index("ix_sales_records_shop_dataset", "shop_id", "dataset_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_datasets.id"), nullable=False
    )

    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Store location / branch / sales agent -- whichever the shop's data has.
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    revenue: Mapped[float | None] = mapped_column(
        Numeric, Computed("quantity * unit_price", persisted=True), nullable=True
    )
    is_incomplete: Mapped[bool] = mapped_column(Boolean, default=False)

    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
