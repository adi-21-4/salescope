import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.dataset import DatasetStatus

ColumnRole = Literal[
    "date", "product", "quantity", "price", "unit_cost", "line_total",
    "category", "status", "location", "agent", "customer_id", "payment_method",
]
MappingRole = ColumnRole | Literal["ignore"]


class UploadedDatasetResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_type: str
    status: DatasetStatus
    row_count_raw: int | None
    row_count_clean: int | None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RoleCandidate(BaseModel):
    role: ColumnRole
    confidence: float


class ColumnDetectionResponse(BaseModel):
    column: str
    detected_role: ColumnRole | None
    confidence: float
    candidates: list[RoleCandidate]
    sample_values: list[str]
    distinct_values: list[str] = Field(
        default_factory=list,
        description="Populated only for low-cardinality columns (<=30 distinct values); "
        "used by the UI to build the status-filter checkbox list.",
    )


class DatasetPreviewResponse(BaseModel):
    dataset_id: uuid.UUID
    columns: list[ColumnDetectionResponse]


class ConfirmMappingRequest(BaseModel):
    mapping: dict[str, MappingRole] = Field(description="raw column name -> role")
    included_status_values: list[str] | None = Field(
        default=None,
        description="Only relevant if a column is mapped to 'status'. Values in this "
        "list count as a completed sale; everything else is excluded from revenue.",
    )


class ConfirmMappingResponse(BaseModel):
    dataset_id: uuid.UUID
    status: DatasetStatus
    rows_total: int
    rows_clean: int
    invalid_date_count: int
    excluded_by_status_count: int
    incomplete_count: int
    duplicate_count: int
    already_existed_count: int
