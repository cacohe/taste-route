"""Taste-grounded trip planning endpoints."""

import asyncio
import json
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...agents.taste_route_orchestrator import TasteRouteOrchestrator
from ...models.schemas import TasteRouteRequest, TasteRouteResponse
from ...services.candidate_validator import CandidateValidationError
from ...services.qloo_service import QlooServiceError
from ...services.runtime_controls import DemoControls
from ..dependencies import get_demo_controls, get_taste_route_orchestrator
from ..errors import qloo_http_error

router = APIRouter(prefix="/trip", tags=["trip planning"])


def _stream_line(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"


def _stream_error(error: Exception) -> dict[str, Any]:
    if isinstance(error, QlooServiceError):
        return {
            "type": "error",
            "error": {
                "error_code": error.code,
                "message": str(error),
                "retryable": error.retryable,
            },
        }
    if isinstance(error, CandidateValidationError):
        return {
            "type": "error",
            "error": {
                "error_code": "INVALID_PLAN_PROVENANCE",
                "message": "The generated itinerary referenced an unavailable place.",
                "retryable": True,
            },
        }
    return {
        "type": "error",
        "error": {
            "error_code": "PLANNING_FAILED",
            "message": "TasteRoute could not finish this itinerary.",
            "retryable": True,
        },
    }


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


@router.post("/plan/stream")
async def plan_trip_stream(
    http_request: Request,
    request: TasteRouteRequest,
    orchestrator: TasteRouteOrchestrator = Depends(get_taste_route_orchestrator),
    controls: DemoControls = Depends(get_demo_controls),
) -> StreamingResponse:
    client = http_request.client.host if http_request.client else "unknown"
    if not await controls.plan_limiter.allow(client):
        raise HTTPException(status_code=429, detail="Planning rate limit exceeded. Please retry shortly.")

    cache_key = request.model_dump_json()
    cached = await controls.plan_cache.get(cache_key)

    async def records():
        if isinstance(cached, TasteRouteResponse):
            if cached.data is not None:
                for step in cached.data.trace:
                    yield _stream_line({"type": "progress", "step": step.model_dump(mode="json")})
            yield _stream_line({"type": "result", "response": cached.model_dump(mode="json")})
            return

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def publish_progress(step) -> None:
            await queue.put({"type": "progress", "step": step.model_dump(mode="json")})

        async def run_plan() -> None:
            try:
                async with controls.plan_gate.slot():
                    response = await orchestrator.plan(request, on_progress=publish_progress)
                await controls.plan_cache.set(cache_key, response)
                await queue.put({"type": "result", "response": response.model_dump(mode="json")})
            except Exception as error:
                await queue.put(_stream_error(error))
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_plan())
        try:
            while True:
                record = await queue.get()
                if record is None:
                    break
                yield _stream_line(record)
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(records(), media_type="application/x-ndjson")
