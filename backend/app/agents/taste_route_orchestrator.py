"""TasteRoute workflow that keeps Qloo provenance across itinerary composition."""

from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

from ..models.qloo import PlaceCandidate, QlooEntity
from ..models.schemas import (
    ItineraryDay,
    TasteProfile,
    TasteRoutePlan,
    TasteRouteRequest,
    TasteRouteResponse,
)
from ..services.candidate_validator import (
    enforce_plan_provenance,
    validate_candidates,
)


class QlooPort(Protocol):
    async def search_entities(
        self, query: str, entity_type: str | None = None, *, take: int = 10
    ) -> list[QlooEntity]: ...

    async def recommend_places(
        self, *, destination: str, entity_ids: list[str], take: int = 20
    ) -> list[PlaceCandidate]: ...


class ItineraryComposer(Protocol):
    async def compose(
        self, request: TasteRouteRequest, candidates: list[PlaceCandidate]
    ) -> list[ItineraryDay]: ...


class ItineraryComposerError(RuntimeError):
    pass


class TasteRouteOrchestrator:
    def __init__(
        self,
        *,
        qloo: QlooPort,
        composer: ItineraryComposer,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._qloo = qloo
        self._composer = composer
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))

    async def plan(self, request: TasteRouteRequest) -> TasteRouteResponse:
        seed_ids, warnings = await self._resolve_seed_ids(request)
        if not seed_ids:
            warnings.append("No taste seeds could be resolved by Qloo.")
            return self._response(request, [], [], warnings)

        discovered = await self._qloo.recommend_places(
            destination=request.destination,
            entity_ids=seed_ids,
            take=20,
        )
        candidates = validate_candidates(
            discovered, excluded_ids=set(request.excluded_place_ids)
        )
        if not candidates:
            warnings.append(
                "No usable Qloo places were found for this destination and taste profile."
            )
            return self._response(request, [], [], warnings)

        try:
            days = await self._composer.compose(request, candidates)
        except ItineraryComposerError:
            warnings.append("Itinerary composition is temporarily unavailable.")
            return self._response(request, candidates, [], warnings)

        planned_ids = [item.place_id for day in days for item in day.items]
        enforce_plan_provenance(planned_ids, candidates)
        return self._response(request, candidates, days, warnings)

    async def _resolve_seed_ids(
        self, request: TasteRouteRequest
    ) -> tuple[list[str], list[str]]:
        ids: list[str] = []
        warnings: list[str] = []
        for seed in request.taste_seeds:
            if seed.id:
                ids.append(seed.id)
                continue
            results = await self._qloo.search_entities(
                seed.name, seed.entity_type, take=1
            )
            if results:
                ids.append(results[0].id)
            else:
                warnings.append(f"Could not resolve taste seed: {seed.name}")
        return list(dict.fromkeys(ids)), warnings

    def _response(
        self,
        request: TasteRouteRequest,
        candidates: list[PlaceCandidate],
        days: list[ItineraryDay],
        warnings: list[str],
    ) -> TasteRouteResponse:
        tags = list(
            dict.fromkeys(tag for candidate in candidates for tag in candidate.tags)
        )[:8]
        return TasteRouteResponse(
            success=True,
            message="TasteRoute planning completed.",
            data=TasteRoutePlan(
                request_id=self._request_id_factory(),
                destination=request.destination,
                start_date=request.start_date,
                end_date=request.end_date,
                taste_profile=TasteProfile(tags=tags),
                candidates=candidates,
                days=days,
                warnings=warnings,
            ),
        )
