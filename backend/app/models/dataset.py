import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    MAPPING_PENDING = "mapping_pending"
    MAPPING_CONFIRMED = "mapping_confirmed"
    CLEANED = "cleaned"
    FAILED = "failed"


class UploadedDataset(Base):
    __tablename__ = "uploaded_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)

    original_filename: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))
    storage_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status"), default=DatasetStatus.UPLOADED
    )

    row_count_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count_clean: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # {raw_col: {role, confidence, sample_values}} — populated in M2.
    detected_column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # User-corrected mapping; NULL until the user confirms it (M2).
    confirmed_column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Values of the "status" column (if mapped) that count as a completed sale.
    included_status_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())
    cleaned_at: Mapped[datetime | None] = mapped_column(nullable=True)
