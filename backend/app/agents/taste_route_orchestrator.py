"""TasteRoute workflow that keeps Qloo provenance across itinerary composition."""

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import uuid4

from ..models.qloo import PlaceCandidate, QlooEntity
from ..models.schemas import (
    ItineraryDay,
    TasteProfile,
    TasteRoutePlan,
    TasteRouteRequest,
    TasteRouteResponse,
    WorkflowStep,
)
from ..services.candidate_validator import (
    CandidateValidationError,
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
        self,
        request: TasteRouteRequest,
        candidates: list[PlaceCandidate],
        correction: str | None = None,
    ) -> list[ItineraryDay]: ...


class ItineraryComposerError(RuntimeError):
    pass


ProgressCallback = Callable[[WorkflowStep], Awaitable[None]]


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

    async def plan(
        self,
        request: TasteRouteRequest,
        on_progress: ProgressCallback | None = None,
    ) -> TasteRouteResponse:
        trace: list[WorkflowStep] = []
        await self._emit_progress(on_progress, "taste_resolution", "Resolve taste signals", "active")
        seed_ids, seed_names, warnings = await self._resolve_seed_ids(request)
        taste_step = WorkflowStep(key="taste_resolution", label="Resolve taste signals", status="completed")
        trace.append(taste_step)
        await self._emit_step(on_progress, taste_step)
        if not seed_ids:
            warnings.append("No taste seeds could be resolved by Qloo.")
            skipped = [
                WorkflowStep(key="qloo_discovery", label="Discover Qloo places", status="skipped"),
                WorkflowStep(key="itinerary_composition", label="Compose itinerary", status="skipped"),
            ]
            trace.extend(skipped)
            for step in skipped:
                await self._emit_step(on_progress, step)
            return self._response(request, [], [], warnings, trace)

        await self._emit_progress(on_progress, "qloo_discovery", "Discover Qloo places", "active")
        discovered = await self._qloo.recommend_places(
            destination=request.destination,
            entity_ids=seed_ids,
            take=20,
        )
        candidates = validate_candidates(
            discovered, excluded_ids=set(request.excluded_place_ids)
        )
        candidates = self._name_contributions(candidates, seed_names)
        discovery_step = WorkflowStep(key="qloo_discovery", label="Discover Qloo places", status="completed")
        trace.append(discovery_step)
        await self._emit_step(on_progress, discovery_step)
        if not candidates:
            warnings.append(
                "No usable Qloo places were found for this destination and taste profile."
            )
            skipped_step = WorkflowStep(key="itinerary_composition", label="Compose itinerary", status="skipped")
            trace.append(skipped_step)
            await self._emit_step(on_progress, skipped_step)
            return self._response(request, [], [], warnings, trace)

        await self._emit_progress(on_progress, "itinerary_composition", "Compose itinerary", "active")
        try:
            days = await self._composer.compose(request, candidates)
            days = self._validate_days(request, candidates, days)
            composition_step = WorkflowStep(key="itinerary_composition", label="Compose itinerary", status="completed")
            trace.append(composition_step)
            await self._emit_step(on_progress, composition_step)
        except (ItineraryComposerError, CandidateValidationError) as first_error:
            try:
                days = await self._composer.compose(
                    request,
                    candidates,
                    correction=f"Previous output was invalid: {first_error}",
                )
                days = self._validate_days(request, candidates, days)
                warnings.append("The itinerary required one automatic repair pass.")
                repaired_step = WorkflowStep(key="itinerary_composition", label="Compose itinerary", status="repaired")
                trace.append(repaired_step)
                await self._emit_step(on_progress, repaired_step)
            except ItineraryComposerError:
                warnings.append("Itinerary composition is temporarily unavailable.")
                failed_step = WorkflowStep(key="itinerary_composition", label="Compose itinerary", status="failed")
                trace.append(failed_step)
                await self._emit_step(on_progress, failed_step)
                return self._response(request, candidates, [], warnings, trace)

        return self._response(request, candidates, days, warnings, trace)

    @staticmethod
    async def _emit_progress(
        callback: ProgressCallback | None,
        key: str,
        label: str,
        status: str,
    ) -> None:
        await TasteRouteOrchestrator._emit_step(
            callback,
            WorkflowStep(key=key, label=label, status=status),
        )

    @staticmethod
    async def _emit_step(
        callback: ProgressCallback | None,
        step: WorkflowStep,
    ) -> None:
        if callback is not None:
            await callback(step)

    @staticmethod
    def _validate_days(
        request: TasteRouteRequest,
        candidates: list[PlaceCandidate],
        days: list[ItineraryDay],
    ) -> list[ItineraryDay]:
        planned_ids = [item.place_id for day in days for item in day.items]
        enforce_plan_provenance(planned_ids, candidates)
        invalid_dates = sorted(
            str(day.date)
            for day in days
            if day.date < request.start_date or day.date > request.end_date
        )
        if invalid_dates:
            raise CandidateValidationError(
                "Plan contains dates outside the requested trip: "
                + ", ".join(invalid_dates)
            )
        dates = [day.date for day in days]
        if len(dates) != len(set(dates)):
            raise CandidateValidationError("Plan contains duplicate itinerary dates")
        return sorted(days, key=lambda day: day.date)

    async def _resolve_seed_ids(
        self, request: TasteRouteRequest
    ) -> tuple[list[str], dict[str, str], list[str]]:
        ids: list[str] = []
        names: dict[str, str] = {}
        warnings: list[str] = []
        for seed in request.taste_seeds:
            if seed.id:
                ids.append(seed.id)
                names[seed.id] = seed.name
                continue
            results = await self._qloo.search_entities(
                seed.name, seed.entity_type, take=1
            )
            if results:
                ids.append(results[0].id)
                names[results[0].id] = seed.name
            else:
                warnings.append(f"Could not resolve taste seed: {seed.name}")
        return list(dict.fromkeys(ids)), names, warnings

    @staticmethod
    def _name_contributions(
        candidates: list[PlaceCandidate], seed_names: dict[str, str]
    ) -> list[PlaceCandidate]:
        return [
            candidate.model_copy(
                update={
                    "contributions": [
                        contribution.model_copy(
                            update={"name": contribution.name or seed_names.get(contribution.entity_id)}
                        )
                        for contribution in candidate.contributions
                    ]
                }
            )
            for candidate in candidates
        ]

    def _response(
        self,
        request: TasteRouteRequest,
        candidates: list[PlaceCandidate],
        days: list[ItineraryDay],
        warnings: list[str],
        trace: list[WorkflowStep],
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
                taste_profile=TasteProfile(tags=tags, seeds=request.taste_seeds),
                candidates=candidates,
                days=days,
                warnings=warnings,
                trace=trace,
            ),
        )
