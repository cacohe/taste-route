"""Provider-neutral routing port and an optional OSRM driving adapter."""

from dataclasses import dataclass
from typing import Protocol

import httpx

from ..models.qloo import PlaceCandidate
from ..models.schemas import ItineraryDay, ItineraryRoute, TravelLeg


@dataclass(frozen=True)
class TravelEstimate:
    from_place_id: str
    to_place_id: str
    distance_meters: float | None
    duration_minutes: float | None


@dataclass(frozen=True)
class TravelMatrix:
    place_ids: list[str]
    durations_seconds: list[list[float | None]]
    distances_meters: list[list[float | None]]


class RoutingServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class RoutingPort(Protocol):
    async def build_matrix(self, candidates: list[PlaceCandidate]) -> TravelMatrix: ...
    async def route_day(
        self, day: ItineraryDay, candidate_by_id: dict[str, PlaceCandidate]
    ) -> ItineraryRoute: ...


class OSRMRoutingService:
    profile = "driving"

    def __init__(
        self, base_url: str, timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    @staticmethod
    def _coordinates(candidates: list[PlaceCandidate]) -> str:
        if not candidates or any(
            item.longitude is None or item.latitude is None for item in candidates
        ):
            raise RoutingServiceError(
                "ROUTING_INVALID_COORDINATES",
                "Routing requires mapped Qloo candidates.", retryable=False,
            )
        return ";".join(
            f"{item.longitude:g},{item.latitude:g}" for item in candidates
        )

    async def _get(self, path: str, params: dict[str, str]) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise RoutingServiceError(
                "ROUTING_TIMEOUT", "Routing timed out.", retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise RoutingServiceError(
                "ROUTING_NETWORK_ERROR", "Routing is unavailable.", retryable=True
            ) from exc
        if response.status_code == 429:
            raise RoutingServiceError(
                "ROUTING_RATE_LIMITED", "Routing is rate limited.", retryable=True
            )
        if response.status_code >= 500:
            raise RoutingServiceError(
                "ROUTING_UPSTREAM_ERROR", "Routing is unavailable.", retryable=True
            )
        if response.status_code >= 400:
            raise RoutingServiceError(
                "ROUTING_REJECTED", "Routing rejected the request.", retryable=False
            )
        try:
            return response.json()
        except ValueError as exc:
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            ) from exc

    async def build_matrix(self, candidates: list[PlaceCandidate]) -> TravelMatrix:
        coordinates = self._coordinates(candidates)
        payload = await self._get(
            f"/table/v1/{self.profile}/{coordinates}",
            {"annotations": "duration,distance"},
        )
        durations = payload.get("durations")
        distances = payload.get("distances")
        if not isinstance(durations, list) or not isinstance(distances, list):
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            )
        return TravelMatrix(
            place_ids=[candidate.id for candidate in candidates],
            durations_seconds=durations,
            distances_meters=distances,
        )

    async def route_day(
        self, day: ItineraryDay, candidate_by_id: dict[str, PlaceCandidate]
    ) -> ItineraryRoute:
        try:
            ordered = [candidate_by_id[item.place_id] for item in day.items]
        except KeyError as exc:
            raise RoutingServiceError(
                "ROUTING_UNKNOWN_PLACE", "Routing received an unknown place.", retryable=False
            ) from exc
        coordinates = self._coordinates(ordered)
        payload = await self._get(
            f"/route/v1/{self.profile}/{coordinates}",
            {"overview": "full", "geometries": "geojson", "steps": "false"},
        )
        routes = payload.get("routes")
        if not isinstance(routes, list) or not routes:
            raise RoutingServiceError(
                "ROUTING_NO_ROUTE", "No driving route was found.", retryable=True
            )
        route = routes[0]
        geometry = route.get("geometry", {}).get("coordinates")
        provider_legs = route.get("legs")
        if not isinstance(geometry, list) or not isinstance(provider_legs, list):
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            )
        legs = []
        for index, provider_leg in enumerate(provider_legs):
            if index + 1 >= len(day.items):
                break
            legs.append(TravelLeg(
                from_place_id=day.items[index].place_id,
                to_place_id=day.items[index + 1].place_id,
                distance_meters=round(float(provider_leg["distance"])),
                duration_minutes=round(float(provider_leg["duration"]) / 60),
            ))
        return ItineraryRoute(
            date=day.date,
            geometry=geometry,
            legs=legs,
            distance_meters=round(float(route.get("distance", 0))),
            duration_minutes=round(float(route.get("duration", 0)) / 60),
        )
