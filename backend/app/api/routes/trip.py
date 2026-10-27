"""Taste-grounded trip planning endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from ...agents.taste_route_orchestrator import TasteRouteOrchestrator
from ...models.schemas import TasteRouteRequest, TasteRouteResponse
from ...services.candidate_validator import CandidateValidationError
from ...services.qloo_service import QlooServiceError
from ..dependencies import get_taste_route_orchestrator
from ..errors import qloo_http_error

router = APIRouter(prefix="/trip", tags=["trip planning"])


@router.post("/plan", response_model=TasteRouteResponse)
async def plan_trip(
    request: TasteRouteRequest,
    orchestrator: TasteRouteOrchestrator = Depends(get_taste_route_orchestrator),
) -> TasteRouteResponse:
    try:
        return await orchestrator.plan(request)
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
