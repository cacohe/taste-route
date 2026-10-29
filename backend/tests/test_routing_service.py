from datetime import date

import httpx
import pytest

from app.models.qloo import PlaceCandidate
from app.models.schemas import ItineraryDay, ItineraryItem
from app.services.routing_service import OSRMRoutingService, RoutingServiceError


def candidates():
    return [
        PlaceCandidate(id="a", name="A", longitude=121.47, latitude=31.23),
        PlaceCandidate(id="b", name="B", longitude=121.50, latitude=31.25),
    ]


def day():
    return ItineraryDay(date=date(2026, 10, 29), items=[
        ItineraryItem(place_id="a", start_time="10:00", duration_minutes=60, reason="A"),
        ItineraryItem(place_id="b", start_time="12:00", duration_minutes=60, reason="B"),
    ])


@pytest.mark.anyio
async def test_build_matrix_uses_driving_and_longitude_before_latitude():
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={
            "code": "Ok",
            "durations": [[0, 600.0], [None, 0]],
            "distances": [[0, 5200.0], [None, 0]],
        })
    service = OSRMRoutingService(
        "https://router.example", timeout_seconds=3,
        transport=httpx.MockTransport(handler),
    )

    matrix = await service.build_matrix(candidates())

    assert seen[0].url.path == "/table/v1/driving/121.47,31.23;121.5,31.25"
    assert seen[0].url.params["annotations"] == "duration,distance"
    assert matrix.place_ids == ["a", "b"]
    assert matrix.durations_seconds[1][0] is None
    assert matrix.distances_meters[0][1] == 5200.0


@pytest.mark.anyio
async def test_route_day_normalizes_geojson_geometry_and_legs():
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"code": "Ok", "routes": [{
            "distance": 5200.4, "duration": 600.0,
            "geometry": {"type": "LineString", "coordinates": [[121.47, 31.23], [121.5, 31.25]]},
            "legs": [{"distance": 5200.4, "duration": 600.0}],
        }]})
    service = OSRMRoutingService(
        "https://router.example", timeout_seconds=3,
        transport=httpx.MockTransport(handler),
    )

    route = await service.route_day(day(), {item.id: item for item in candidates()})

    assert seen[0].url.path == "/route/v1/driving/121.47,31.23;121.5,31.25"
    assert seen[0].url.params["geometries"] == "geojson"
    assert seen[0].url.params["overview"] == "full"
    assert route.profile == "driving"
    assert route.geometry == [[121.47, 31.23], [121.5, 31.25]]
    assert route.legs[0].from_place_id == "a"
    assert route.legs[0].to_place_id == "b"
    assert route.duration_minutes == 10


@pytest.mark.anyio
async def test_empty_route_is_a_safe_retryable_error():
    service = OSRMRoutingService(
        "https://router.example", timeout_seconds=3,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"code": "Ok", "routes": []})),
    )
    with pytest.raises(RoutingServiceError) as captured:
        await service.route_day(day(), {item.id: item for item in candidates()})
    assert captured.value.retryable is True
    assert captured.value.code == "ROUTING_NO_ROUTE"


@pytest.mark.anyio
@pytest.mark.parametrize("status,code", [(429, "ROUTING_RATE_LIMITED"), (503, "ROUTING_UPSTREAM_ERROR")])
async def test_http_failures_are_safely_classified(status, code):
    service = OSRMRoutingService(
        "https://router.example", timeout_seconds=3,
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="provider secret")),
    )
    with pytest.raises(RoutingServiceError) as captured:
        await service.build_matrix(candidates())
    assert captured.value.code == code
    assert captured.value.retryable is True
    assert "provider secret" not in str(captured.value)


@pytest.mark.anyio
async def test_timeout_is_safely_classified():
    def handler(request):
        raise httpx.ReadTimeout("secret URL", request=request)
    service = OSRMRoutingService(
        "https://router.example", timeout_seconds=0.01,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RoutingServiceError) as captured:
        await service.build_matrix(candidates())
    assert captured.value.code == "ROUTING_TIMEOUT"
    assert captured.value.retryable is True
    assert "secret URL" not in str(captured.value)
