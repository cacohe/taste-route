"""Taste-grounded trip planning endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...agents.taste_route_orchestrator import TasteRouteOrchestrator
from ...models.schemas import TasteRouteRequest, TasteRouteResponse
from ...services.candidate_validator import CandidateValidationError
from ...services.qloo_service import QlooServiceError
from ...services.runtime_controls import DemoControls
from ..dependencies import get_demo_controls, get_taste_route_orchestrator
from ..errors import qloo_http_error

router = APIRouter(prefix="/trip", tags=["trip planning"])


@router.post("/plan", response_model=TasteRouteResponse)
async def plan_trip(
    http_request: Request,
    request: TasteRouteRequest,
    orchestrator: TasteRouteOrchestrator = Depends(get_taste_route_orchestrator),
    controls: DemoControls = Depends(get_demo_controls),
) -> TasteRouteResponse:
    client = http_request.client.host if http_request.client else "unknown"
    if not await controls.plan_limiter.allow(client):
        raise HTTPException(status_code=429, detail="Planning rate limit exceeded. Please retry shortly.")
    cache_key = request.model_dump_json()
    cached = await controls.plan_cache.get(cache_key)
    if isinstance(cached, TasteRouteResponse):
        return cached
    try:
        async with controls.plan_gate.slot():
            response = await orchestrator.plan(request)
    except QlooServiceError as exc:
        raise qloo_http_error(exc) from exc
    except CandidateValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": "INVALID_PLAN_PROVENANCE",
                "message": "The generated itinerary referenced an unavailable place.",
                "retryable": True,
            },
        ) from exc
    await controls.plan_cache.set(cache_key, response)
    return response
