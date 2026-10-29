"""Provider-neutral routing port and an optional OSRM driving adapter."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

import httpx

from ..models.qloo import PlaceCandidate
from ..models.schemas import ItineraryDay, ItineraryRoute, TravelLeg


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
        size = len(candidates)
        if not self._valid_matrix(durations, size) or not self._valid_matrix(distances, size):
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            )
        return TravelMatrix(
            place_ids=[candidate.id for candidate in candidates],
            durations_seconds=durations,
            distances_meters=distances,
        )

    @staticmethod
    def _valid_matrix(value: object, size: int) -> bool:
        return (
            isinstance(value, list)
            and len(value) == size
            and all(
                isinstance(row, list)
                and len(row) == size
                and all(
                    cell is None
                    or OSRMRoutingService._valid_number(cell)
                    for cell in row
                )
                for row in value
            )
        )

    @staticmethod
    def _valid_number(value: object) -> bool:
        return (
            OSRMRoutingService._finite_number(value)
            and value >= 0
        )

    @staticmethod
    def _finite_number(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
        )

    @classmethod
    def _valid_coordinate(cls, point: object) -> bool:
        return (
            isinstance(point, list)
            and len(point) == 2
            and cls._finite_number(point[0])
            and cls._finite_number(point[1])
            and -180 <= point[0] <= 180
            and -90 <= point[1] <= 90
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
        if not isinstance(route, dict):
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            )
        try:
            geometry = route["geometry"]["coordinates"]
            provider_legs = route["legs"]
            if (
                not isinstance(geometry, list)
                or len(geometry) < 2
                or not all(self._valid_coordinate(point) for point in geometry)
                or not isinstance(provider_legs, list)
                or len(provider_legs) != max(0, len(day.items) - 1)
                or not self._valid_number(route.get("distance"))
                or not self._valid_number(route.get("duration"))
                or not all(
                    isinstance(provider_leg, dict)
                    and self._valid_number(provider_leg.get("distance"))
                    and self._valid_number(provider_leg.get("duration"))
                    for provider_leg in provider_legs
                )
            ):
                raise ValueError("invalid route shape")
            legs = [TravelLeg(
                from_place_id=day.items[index].place_id,
                to_place_id=day.items[index + 1].place_id,
                distance_meters=round(float(provider_leg["distance"])),
                duration_minutes=round(float(provider_leg["duration"]) / 60),
            ) for index, provider_leg in enumerate(provider_legs)]
            return ItineraryRoute(
                date=day.date,
                geometry=geometry,
                legs=legs,
                distance_meters=round(float(route["distance"])),
                duration_minutes=round(float(route["duration"]) / 60),
            )
        except (KeyError, OverflowError, TypeError, ValueError) as exc:
            raise RoutingServiceError(
                "ROUTING_INVALID_RESPONSE", "Routing returned invalid data.", retryable=True
            ) from exc
