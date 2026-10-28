"""Taste entity discovery endpoints backed by Qloo."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...models.qloo import QlooEntity
from ...services.qloo_service import QlooService, QlooServiceError
from ...services.runtime_controls import DemoControls
from ..dependencies import get_demo_controls, get_qloo_service
from ..errors import qloo_http_error


class TasteEntitySearchResponse(BaseModel):
    items: list[QlooEntity]


router = APIRouter(prefix="/taste", tags=["taste"])


@router.get("/entities", response_model=TasteEntitySearchResponse)
async def search_taste_entities(
    request: Request,
    q: str = Query(min_length=2, max_length=120),
    entity_type: str | None = Query(default=None, alias="type"),
    take: int = Query(default=10, ge=1, le=20),
    qloo: QlooService = Depends(get_qloo_service),
    controls: DemoControls = Depends(get_demo_controls),
) -> TasteEntitySearchResponse:
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Search query must contain at least 2 characters.")
    client = request.client.host if request.client else "unknown"
    if not await controls.search_limiter.allow(client):
        raise HTTPException(status_code=429, detail="Search rate limit exceeded. Please retry shortly.")
    cache_key = f"{q.casefold()}|{entity_type or ''}|{take}"
    cached = await controls.search_cache.get(cache_key)
    if isinstance(cached, TasteEntitySearchResponse):
        return cached
    try:
        items = await qloo.search_entities(q, entity_type, take=take)
    except QlooServiceError as exc:
        raise qloo_http_error(exc) from exc
    response = TasteEntitySearchResponse(items=items)
    await controls.search_cache.set(cache_key, response)
    return response
