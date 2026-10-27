"""Taste entity discovery endpoints backed by Qloo."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...models.qloo import QlooEntity
from ...services.qloo_service import QlooService, QlooServiceError
from ..dependencies import get_qloo_service
from ..errors import qloo_http_error


class TasteEntitySearchResponse(BaseModel):
    items: list[QlooEntity]


router = APIRouter(prefix="/taste", tags=["taste"])


@router.get("/entities", response_model=TasteEntitySearchResponse)
async def search_taste_entities(
    q: str = Query(min_length=2, max_length=120),
    entity_type: str | None = Query(default=None, alias="type"),
    take: int = Query(default=10, ge=1, le=20),
    qloo: QlooService = Depends(get_qloo_service),
) -> TasteEntitySearchResponse:
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Search query must contain at least 2 characters.")
    try:
        items = await qloo.search_entities(q, entity_type, take=take)
    except QlooServiceError as exc:
        raise qloo_http_error(exc) from exc
    return TasteEntitySearchResponse(items=items)
