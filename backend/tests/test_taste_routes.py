from datetime import date
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_demo_controls,
    get_qloo_service,
    get_taste_route_orchestrator,
)
from app.api.routes import taste, trip
from app.models.qloo import QlooEntity
from app.models.schemas import AgentDecision, TasteProfile, TasteRoutePlan, TasteRouteResponse
from app.services.qloo_service import QlooServiceError
from app.services.runtime_controls import DemoControls


class FakeQloo:
    def __init__(self):
        self.calls = 0

    async def search_entities(self, query, entity_type=None, *, take=10):
        self.calls += 1
        return [
            QlooEntity(
                id="movie-1",
                name="Blade Runner",
                entity_type="movie",
                description="1982 film",
            )
        ]


class FailingQloo:
    async def search_entities(self, query, entity_type=None, *, take=10):
        raise QlooServiceError(
            "QLOO_AUTH_FAILED", "Qloo authentication failed.", retryable=False
        )


class FakeOrchestrator:
    async def plan(self, request):
        return TasteRouteResponse(
            success=True,
            message="TasteRoute planning completed.",
            data=TasteRoutePlan(
                request_id="request-123",
                destination=request.destination,
                start_date=request.start_date,
                end_date=request.end_date,
                taste_profile=TasteProfile(tags=["Film culture"]),
                candidates=[],
                days=[],
                warnings=[],
                completion_status="partial",
            ),
        )


class RateLimitedOrchestrator:
    async def plan(self, request):
        raise QlooServiceError(
            "QLOO_RATE_LIMITED", "Qloo is temporarily rate limited.", retryable=True
        )


class StreamingOrchestrator(FakeOrchestrator):
    async def plan(self, request, on_progress=None):
        decision = AgentDecision(
            iteration=1,
            action="resolve_locality",
            status="completed",
            reason="Resolved destination with Qloo.",
            metrics={"result_count": 2},
        )
        if on_progress is not None:
            await on_progress(decision)
        response = await super().plan(request)
        response.data.decisions = [decision]
        return response


class FailingStreamingOrchestrator:
    async def plan(self, request, on_progress=None):
        raise QlooServiceError(
            "QLOO_RATE_LIMITED", "Qloo is temporarily rate limited.", retryable=True
        )


def _controls(*, search_limit=30, plan_limit=5) -> DemoControls:
    return DemoControls(
        search_limit=search_limit,
        plan_limit=plan_limit,
        plan_concurrency=1,
        search_ttl=60,
        plan_ttl=60,
    )


def _client(*, qloo=None, orchestrator=None, controls=None) -> TestClient:
    app = FastAPI()
    active_controls = controls or _controls()
    app.include_router(taste.router, prefix="/api")
    app.include_router(trip.router, prefix="/api")
    if qloo is not None:
        app.dependency_overrides[get_qloo_service] = lambda: qloo
    if orchestrator is not None:
        app.dependency_overrides[get_taste_route_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_demo_controls] = lambda: active_controls
    return TestClient(app)


def test_search_route_returns_normalized_qloo_entities():
    response = _client(qloo=FakeQloo()).get(
        "/api/taste/entities", params={"q": "Blade Runner", "type": "movie"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "movie-1",
                "name": "Blade Runner",
                "entity_type": "movie",
                "description": "1982 film",
                "image_url": None,
            }
        ]
    }


def test_search_route_caches_identical_queries_without_recalling_qloo():
    qloo = FakeQloo()
    client = _client(qloo=qloo)

    assert client.get("/api/taste/entities", params={"q": "Blade Runner"}).status_code == 200
    assert client.get("/api/taste/entities", params={"q": "Blade Runner"}).status_code == 200

    assert qloo.calls == 1


def test_search_route_returns_429_after_public_demo_quota():
    client = _client(qloo=FakeQloo(), controls=_controls(search_limit=1))

    assert client.get("/api/taste/entities", params={"q": "Blade Runner"}).status_code == 200
    response = client.get("/api/taste/entities", params={"q": "Alien"})

    assert response.status_code == 429


def test_search_route_returns_safe_auth_error():
    response = _client(qloo=FailingQloo()).get(
        "/api/taste/entities", params={"q": "Blade Runner"}
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "error_code": "QLOO_AUTH_FAILED",
            "message": "Qloo authentication failed.",
            "retryable": False,
        }
    }


def test_search_route_rejects_whitespace_only_query():
    response = _client(qloo=FakeQloo()).get(
        "/api/taste/entities", params={"q": "   "}
    )

    assert response.status_code == 422


def test_plan_route_returns_orchestrated_response():
    response = _client(orchestrator=FakeOrchestrator()).post(
        "/api/trip/plan",
        json={
            "destination": "New York",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "pace": "balanced",
            "budget": "medium",
            "taste_seeds": [
                {"id": "movie-1", "name": "Blade Runner", "entity_type": "movie"}
            ],
            "constraints": ["prefer walking"],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["request_id"] == "request-123"
    assert response.json()["data"]["taste_profile"]["tags"] == ["Film culture"]


def test_plan_route_maps_rate_limit_to_retryable_503():
    response = _client(orchestrator=RateLimitedOrchestrator()).post(
        "/api/trip/plan",
        json={
            "destination": "New York",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "taste_seeds": [
                {"id": "movie-1", "name": "Blade Runner", "entity_type": "movie"}
            ],
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error_code": "QLOO_RATE_LIMITED",
        "message": "Qloo is temporarily rate limited.",
        "retryable": True,
    }


def test_plan_stream_returns_progress_then_terminal_result():
    client = _client(orchestrator=StreamingOrchestrator())
    response = client.post(
        "/api/trip/plan/stream",
        json={
            "destination": "New York",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "taste_seeds": [
                {"id": "movie-1", "name": "Blade Runner", "entity_type": "movie"}
            ],
        },
    )

    records = [json.loads(line) for line in response.text.splitlines()]

    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [record["type"] for record in records] == ["progress", "result"]
    assert records[0]["decision"]["status"] == "completed"
    assert records[-1]["response"]["data"]["request_id"] == "request-123"

    cached = client.post(
        "/api/trip/plan/stream",
        json={
            "destination": "New York",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "taste_seeds": [
                {"id": "movie-1", "name": "Blade Runner", "entity_type": "movie"}
            ],
        },
    )
    cached_records = [json.loads(line) for line in cached.text.splitlines()]
    assert cached_records == records


def test_plan_stream_serializes_safe_retryable_error():
    response = _client(orchestrator=FailingStreamingOrchestrator()).post(
        "/api/trip/plan/stream",
        json={
            "destination": "New York",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "taste_seeds": [
                {"id": "movie-1", "name": "Blade Runner", "entity_type": "movie"}
            ],
        },
    )

    records = [json.loads(line) for line in response.text.splitlines()]

    assert records == [
        {
            "type": "error",
            "error": {
                "error_code": "QLOO_RATE_LIMITED",
                "message": "Qloo is temporarily rate limited.",
                "retryable": True,
            },
        }
    ]


def test_plan_route_rejects_whitespace_only_destination_and_seed_name():
    response = _client(orchestrator=FakeOrchestrator()).post(
        "/api/trip/plan",
        json={
            "destination": "   ",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "taste_seeds": [
                {"id": None, "name": "   ", "entity_type": "movie"}
            ],
        },
    )

    assert response.status_code == 422
