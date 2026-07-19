import uuid
from datetime import datetime

from pydantic import BaseModel


class InsightCardResponse(BaseModel):
    id: uuid.UUID
    finding: str
    supporting_stat: str
    category: str
    chart_ref: str | None
    generated_at: datetime

    class Config:
        from_attributes = True
