import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_shop_id
from app.models.dataset import DatasetStatus, UploadedDataset
from app.models.sales_record import SalesRecord
from app.schemas.dataset import (
    ColumnDetectionResponse,
    ConfirmMappingRequest,
    ConfirmMappingResponse,
    DatasetPreviewResponse,
    RoleCandidate,
    UploadedDatasetResponse,
)
from app.services.ingestion.cleaner import DuplicateRoleMappingError, MissingRequiredRolesError, clean_dataframe
from app.services.ingestion.column_detector import detect_columns
from app.services.ingestion.parser import UnsupportedFileTypeError, file_type_from_filename, parse_file
from app.services.storage import save_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB — generous for a small shop's sales export


def _get_owned_dataset(dataset_id: uuid.UUID, shop_id: uuid.UUID, db: Session) -> UploadedDataset:
    dataset = db.query(UploadedDataset).filter_by(id=dataset_id, shop_id=shop_id).first()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.post("/upload", response_model=UploadedDatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> UploadedDataset:
    try:
        file_type = file_type_from_filename(file.filename or "")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
        )

    dataset_id = uuid.uuid4()
    storage_path = save_upload(shop_id, dataset_id, file.filename or "upload", content)

    try:
        df = parse_file(Path(storage_path), file_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse file: {exc}",
        ) from exc

    dataset = UploadedDataset(
        id=dataset_id,
        shop_id=shop_id,
        original_filename=file.filename or "upload",
        file_type=file_type,
        storage_path=storage_path,
        status=DatasetStatus.UPLOADED,
        row_count_raw=len(df),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("", response_model=list[UploadedDatasetResponse])
def list_datasets(
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[UploadedDataset]:
    return (
        db.query(UploadedDataset)
        .filter_by(shop_id=shop_id)
        .order_by(UploadedDataset.uploaded_at.desc())
        .all()
    )


@router.get("/{dataset_id}", response_model=UploadedDatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> UploadedDataset:
    return _get_owned_dataset(dataset_id, shop_id, db)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: uuid.UUID,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> DatasetPreviewResponse:
    dataset = _get_owned_dataset(dataset_id, shop_id, db)

    try:
        df = parse_file(Path(dataset.storage_path), dataset.file_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not re-read stored file: {exc}",
        ) from exc

    detections = detect_columns(df)

    dataset.detected_column_mapping = {
        d.column: {
            "role": d.role,
            "confidence": d.confidence,
            "candidates": [{"role": c.role, "confidence": c.confidence} for c in d.candidates],
            "sample_values": d.sample_values,
            "distinct_values": d.distinct_values,
        }
        for d in detections
    }
    if dataset.status == DatasetStatus.UPLOADED:
        dataset.status = DatasetStatus.MAPPING_PENDING
    db.commit()

    return DatasetPreviewResponse(
        dataset_id=dataset.id,
        columns=[
            ColumnDetectionResponse(
                column=d.column,
                detected_role=d.role,
                confidence=d.confidence,
                candidates=[RoleCandidate(role=c.role, confidence=c.confidence) for c in d.candidates],
                sample_values=d.sample_values,
                distinct_values=d.distinct_values,
            )
            for d in detections
        ],
    )


@router.post("/{dataset_id}/confirm-mapping", response_model=ConfirmMappingResponse)
def confirm_mapping(
    dataset_id: uuid.UUID,
    body: ConfirmMappingRequest,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> ConfirmMappingResponse:
    dataset = _get_owned_dataset(dataset_id, shop_id, db)

    try:
        df = parse_file(Path(dataset.storage_path), dataset.file_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not re-read stored file: {exc}",
        ) from exc

    try:
        result = clean_dataframe(df, body.mapping, body.included_status_values)
    except (MissingRequiredRolesError, DuplicateRoleMappingError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    dataset.confirmed_column_mapping = dict(body.mapping)
    dataset.included_status_values = body.included_status_values
    dataset.status = DatasetStatus.MAPPING_CONFIRMED
    db.flush()

    extra_columns = [col for col, role in body.mapping.items() if role == "ignore"]

    rows = []
    for _, row in result.clean_df.iterrows():
        extra = (
            {col: (None if pd.isna(df.at[row.name, col]) else df.at[row.name, col]) for col in extra_columns}
            if extra_columns
            else None
        )
        rows.append(
            {
                "shop_id": shop_id,
                "dataset_id": dataset.id,
                "sale_date": row["sale_date"].date(),
                "product_name": None if pd.isna(row["product_name"]) else row["product_name"],
                "category": None if pd.isna(row["category"]) else row["category"],
                "location": None if pd.isna(row["location"]) else row["location"],
                "agent": None if pd.isna(row["agent"]) else row["agent"],
                "customer_id": None if pd.isna(row["customer_id"]) else row["customer_id"],
                "payment_method": None if pd.isna(row["payment_method"]) else row["payment_method"],
                "quantity": None if pd.isna(row["quantity"]) else float(row["quantity"]),
                "unit_price": None if pd.isna(row["unit_price"]) else float(row["unit_price"]),
                "unit_cost": None if pd.isna(row["unit_cost"]) else float(row["unit_cost"]),
                "is_incomplete": bool(row["is_incomplete"]),
                "extra": extra,
                "row_hash": row["row_hash"],
            }
        )

    if rows:
        stmt = pg_insert(SalesRecord).values(rows).on_conflict_do_nothing(
            index_elements=["shop_id", "row_hash"]
        )
        db.execute(stmt)

    # `rowcount` on a multi-VALUES INSERT ... ON CONFLICT is unreliable across
    # DB-API drivers (psycopg can report -1, meaning "undetermined") — count what
    # actually landed for this dataset instead of trusting the insert result.
    inserted_count = (
        db.query(SalesRecord).filter_by(shop_id=shop_id, dataset_id=dataset.id).count()
    )
    # rows that passed cleaning but didn't insert under THIS dataset_id either
    # duplicated within this same file (duplicate_count, already counted) or
    # matched a row already sitting in the shop's data from a previous upload.
    already_existed_count = len(rows) - inserted_count

    dataset.status = DatasetStatus.CLEANED
    dataset.row_count_clean = inserted_count
    db.commit()

    return ConfirmMappingResponse(
        dataset_id=dataset.id,
        status=dataset.status,
        rows_total=result.rows_total,
        rows_clean=inserted_count,
        invalid_date_count=result.invalid_date_count,
        excluded_by_status_count=result.excluded_by_status_count,
        incomplete_count=result.incomplete_count,
        duplicate_count=result.duplicate_count,
        already_existed_count=already_existed_count,
    )
