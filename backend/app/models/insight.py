import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class InsightCard(Base):
    __tablename__ = "insight_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_datasets.id"), nullable=False, index=True
    )

    finding: Mapped[str] = mapped_column(String(500))
    supporting_stat: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50))
    chart_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)

    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    model_used: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
