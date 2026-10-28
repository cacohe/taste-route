import json
from pathlib import Path

import httpx
import pytest

from app.services.qloo_service import QlooService, QlooServiceError


FIXTURES = Path(__file__).parent / "fixtures" / "qloo"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.anyio
async def test_search_entities_sends_server_key_and_normalizes_results():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=_fixture("search.json"))

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        timeout_seconds=5,
        max_results=20,
        transport=httpx.MockTransport(handler),
    )

    results = await service.search_entities("Blade Runner", "movie", take=8)

    assert captured == {
        "url": "https://hackathon.api.qloo.com/search?query=Blade+Runner&take=8&types=urn%3Aentity%3Amovie",
        "api_key": "secret-key",
    }
    assert [entity.model_dump() for entity in results] == [
        {
            "id": "movie-blade-runner",
            "name": "Blade Runner",
            "entity_type": "movie",
            "description": "1982 science fiction film",
            "image_url": "https://images.example/blade-runner.jpg",
        }
    ]


@pytest.mark.anyio
async def test_search_entities_normalizes_live_search_result_shape():
    payload = {
        "results": [
            {
                "entity_id": "movie-blade-runner",
                "name": "Blade Runner",
                "types": ["urn:entity:movie"],
                "properties": {
                    "description": "1982 science fiction film",
                    "image": {"url": "https://images.example/blade-runner.jpg"},
                },
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    results = await service.search_entities("Blade Runner", "movie")

    assert [entity.model_dump() for entity in results] == [
        {
            "id": "movie-blade-runner",
            "name": "Blade Runner",
            "entity_type": "movie",
            "description": "1982 science fiction film",
            "image_url": "https://images.example/blade-runner.jpg",
        }
    ]


@pytest.mark.anyio
async def test_recommend_places_preserves_coordinates_affinity_and_explainability():
    captured_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json=_fixture("insights.json"))

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com/",
        timeout_seconds=5,
        max_results=20,
        transport=httpx.MockTransport(handler),
    )

    results = await service.recommend_places(
        destination="New York",
        entity_ids=["movie-blade-runner", "artist-vangelis"],
        take=10,
    )

    request = httpx.URL(captured_url)
    assert request.path == "/v2/insights"
    assert dict(request.params) == {
        "filter.type": "urn:entity:place",
        "filter.location.query": "New York",
        "signal.interests.entities": "movie-blade-runner,artist-vangelis",
        "feature.explainability": "true",
        "take": "10",
    }
    assert results[0].id == "place-moving-image"
    assert results[0].latitude == 40.7563
    assert results[0].longitude == -73.9239
    assert results[0].affinity == 0.91
    assert results[0].tags == ["Film museum"]
    assert results[0].contributions[0].entity_id == "movie-blade-runner"
    assert results[0].contributions[0].score == 0.72


@pytest.mark.anyio
async def test_recommend_places_normalizes_live_location_coordinates():
    payload = _fixture("insights.json")
    entity = payload["results"]["entities"][0]
    entity["properties"]["geocode"] = {"city": "Paris"}
    entity["location"] = {"lat": 48.8566, "lon": 2.3522}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )
    results = await service.recommend_places(
        destination="Paris, France", entity_ids=["movie-blade-runner"]
    )

    assert results[0].latitude == 48.8566
    assert results[0].longitude == 2.3522


@pytest.mark.anyio
async def test_recommend_places_sorts_and_bounds_weighted_tags():
    payload = _fixture("insights.json")
    entity = payload["results"]["entities"][0]
    entity["tags"] = [
        {"name": f"Tag {index}", "weight": index} for index in range(10)
    ]

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
    )
    results = await service.recommend_places(
        destination="Paris", entity_ids=["movie-blade-runner"]
    )

    assert results[0].tags == [f"Tag {index}" for index in range(9, 1, -1)]


@pytest.mark.anyio
async def test_recommend_places_normalizes_documented_entity_explainability_map():
    payload = _fixture("insights.json")
    entity = payload["results"]["entities"][0]
    entity["query"]["explainability"] = {
        "signal.interests.entities": {
            "movie-blade-runner": {"name": "Blade Runner", "score": 0.72},
            "artist-vangelis": 0.41,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    results = await service.recommend_places(
        destination="New York",
        entity_ids=["movie-blade-runner", "artist-vangelis"],
    )

    assert [item.model_dump() for item in results[0].contributions] == [
        {
            "entity_id": "movie-blade-runner",
            "name": "Blade Runner",
            "score": 0.72,
        },
        {"entity_id": "artist-vangelis", "name": None, "score": 0.41},
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "expected_code", "retryable"),
    [(401, "QLOO_AUTH_FAILED", False), (429, "QLOO_RATE_LIMITED", True)],
)
async def test_upstream_statuses_map_to_safe_errors(status, expected_code, retryable):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"message": "upstream secret detail"})

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert captured.value.code == expected_code
    assert captured.value.retryable is retryable
    assert "upstream secret detail" not in str(captured.value)
    assert "secret-key" not in str(captured.value)


@pytest.mark.anyio
async def test_timeout_maps_to_retryable_unavailable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert captured.value.code == "QLOO_UNAVAILABLE"
    assert captured.value.retryable is True


@pytest.mark.anyio
async def test_malformed_success_payload_maps_to_controlled_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "results": "invalid"})

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert captured.value.code == "QLOO_INVALID_RESPONSE"
    assert captured.value.retryable is False


@pytest.mark.anyio
async def test_missing_api_key_fails_before_network_access():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_fixture("search.json"))

    service = QlooService(
        api_key="",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert captured.value.code == "QLOO_NOT_CONFIGURED"
    assert calls == 0


@pytest.mark.anyio
async def test_server_error_retries_once_then_returns_safe_unavailable():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"message": "internal upstream detail"})

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert calls == 2
    assert captured.value.code == "QLOO_UNAVAILABLE"
    assert "internal upstream detail" not in str(captured.value)


@pytest.mark.anyio
async def test_bad_request_is_not_retried():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"message": "private upstream detail"})

    service = QlooService(
        api_key="secret-key",
        base_url="https://hackathon.api.qloo.com",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QlooServiceError) as captured:
        await service.search_entities("Blade Runner")

    assert calls == 1
    assert captured.value.code == "QLOO_REQUEST_REJECTED"
