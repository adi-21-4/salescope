import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_shop_id
from app.models.dataset import UploadedDataset
from app.models.insight import InsightCard
from app.schemas.insights import InsightCardResponse
from app.services import aggregates
from app.services import insights as insights_service
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMError

router = APIRouter(prefix="/datasets", tags=["insights"])


@router.get("/{dataset_id}/insights", response_model=list[InsightCardResponse])
def get_insights(
    dataset_id: uuid.UUID,
    regenerate: bool = Query(False, description="Discard any cached insights and generate fresh ones"),
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> list[InsightCard]:
    dataset = db.query(UploadedDataset).filter_by(id=dataset_id, shop_id=shop_id).first()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    existing = (
        db.query(InsightCard)
        .filter_by(shop_id=shop_id, dataset_id=dataset_id)
        .order_by(InsightCard.generated_at.desc())
        .all()
    )
    # Cached by default -- narration for the same dataset doesn't change unless
    # its data does, and re-billing the LLM on every dashboard reload is wasteful.
    if existing and not regenerate:
        return existing

    if existing:
        for card in existing:
            db.delete(card)
        db.commit()

    df = aggregates.load_sales_dataframe(db, shop_id, dataset_id)
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data to generate insights from",
        )

    provider = get_llm_provider()
    try:
        return insights_service.generate_and_cache_insights(db, shop_id, dataset_id, df, provider)
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not generate insights."
        ) from exc
