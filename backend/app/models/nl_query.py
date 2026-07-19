import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class NLQuery(Base):
    """Audit log + cache of natural-language question -> QuerySpec translations.
    Only the LLM *translation* step is cached (by normalized question text) --
    the numeric result is always recomputed fresh against current data, so a
    cached translation never shows stale numbers."""

    __tablename__ = "nl_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_datasets.id"), nullable=False, index=True
    )

    question: Mapped[str] = mapped_column(String(1000))
    question_normalized: Mapped[str] = mapped_column(String(1000), index=True)
    generated_spec: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
