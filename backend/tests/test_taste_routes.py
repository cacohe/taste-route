from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_qloo_service, get_taste_route_orchestrator
from app.api.routes import taste, trip
from app.models.qloo import QlooEntity
from app.models.schemas import TasteProfile, TasteRoutePlan, TasteRouteResponse
from app.services.qloo_service import QlooServiceError


class FakeQloo:
    async def search_entities(self, query, entity_type=None, *, take=10):
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
            ),
        )


class RateLimitedOrchestrator:
    async def plan(self, request):
        raise QlooServiceError(
            "QLOO_RATE_LIMITED", "Qloo is temporarily rate limited.", retryable=True
        )


def _client(*, qloo=None, orchestrator=None) -> TestClient:
    app = FastAPI()
    app.include_router(taste.router, prefix="/api")
    app.include_router(trip.router, prefix="/api")
    if qloo is not None:
        app.dependency_overrides[get_qloo_service] = lambda: qloo
    if orchestrator is not None:
        app.dependency_overrides[get_taste_route_orchestrator] = lambda: orchestrator
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
