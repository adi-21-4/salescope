import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_shop_id
from app.models.dataset import UploadedDataset
from app.models.nl_query import NLQuery
from app.schemas.query import NLQueryRequest, NLQueryResponse
from app.services import aggregates, nl_query
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMError
from app.services.llm.schemas import QuerySpec
from app.services.query_dsl import QueryExecutionError, execute_query

router = APIRouter(prefix="/datasets", tags=["query"])


@router.post("/{dataset_id}/query", response_model=NLQueryResponse)
def query_dataset(
    dataset_id: uuid.UUID,
    body: NLQueryRequest,
    shop_id: uuid.UUID = Depends(get_current_shop_id),
    db: Session = Depends(get_db),
) -> NLQueryResponse:
    dataset = db.query(UploadedDataset).filter_by(id=dataset_id, shop_id=shop_id).first()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    df = aggregates.load_sales_dataframe(db, shop_id, dataset_id)
    if df.empty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No data to query")

    normalized = nl_query.normalize_question(body.question)
    cached = (
        db.query(NLQuery)
        .filter_by(shop_id=shop_id, dataset_id=dataset_id, question_normalized=normalized)
        .order_by(NLQuery.created_at.desc())
        .first()
    )

    if cached:
        # Re-validate against the current schema -- a stale cached spec (e.g.
        # from before a column was re-mapped) should still fail cleanly rather
        # than silently return wrong data.
        spec = QuerySpec.model_validate(cached.generated_spec)
    else:
        schema_description = nl_query.build_schema_description(df)
        provider = get_llm_provider()
        try:
            spec = provider.translate_query(body.question, schema_description)
        except LLMError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        db.add(
            NLQuery(
                shop_id=shop_id,
                dataset_id=dataset_id,
                question=body.question,
                question_normalized=normalized,
                generated_spec=spec.model_dump(mode="json"),
            )
        )
        db.commit()

    try:
        result = execute_query(df, spec)
    except QueryExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return NLQueryResponse(
        answer_text=nl_query.format_answer(spec, result),
        data=result["data"],
        chart_type=result["chart_type"],
    )
