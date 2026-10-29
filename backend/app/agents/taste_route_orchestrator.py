"""Bounded observe/decide/act loop with Qloo-grounded planning evidence."""

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import uuid4

from ..models.planning import (
    PlanningAction,
    PlanningDecision,
    PlanningObservation,
    PlanningPolicy,
    PlanningState,
)
from ..models.qloo import PlaceCandidate, QlooEntity
from ..models.schemas import (
    AgentDecision,
    ItineraryDay,
    ResolvedLocality,
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
from ..services.planning_log import log_planning_event
from ..services.routing_service import RoutingPort, RoutingServiceError
from .planning_policy import PlanningPolicyError


class QlooPort(Protocol):
    async def search_entities(
        self, query: str, entity_type: str | None = None, *, take: int = 10
    ) -> list[QlooEntity]: ...

    async def resolve_localities(
        self, query: str, *, take: int = 5
    ) -> list[QlooEntity]: ...

    async def recommend_places(
        self, *, locality_id: str, entity_ids: list[str],
        radius_meters: int = 0, take: int = 20,
    ) -> list[PlaceCandidate]: ...


class ItineraryComposer(Protocol):
    async def compose(
        self, request: TasteRouteRequest, candidates: list[PlaceCandidate],
        travel_matrix=None,
        correction: str | None = None,
    ) -> list[ItineraryDay]: ...


class ItineraryComposerError(RuntimeError):
    pass


ProgressCallback = Callable[[AgentDecision], Awaitable[None]]


def _actions(state: PlanningState) -> set[PlanningAction]:
    return {PlanningAction(decision.action) for decision in state.decisions}


def allowed_actions(state: PlanningState) -> tuple[PlanningAction, ...]:
    """Return the closed action set permitted by deterministic state guards."""
    previous = _actions(state)
    if state.locality is None:
        if PlanningAction.RESOLVE_LOCALITY in previous:
            return (PlanningAction.FAIL,)
        return (PlanningAction.RESOLVE_LOCALITY, PlanningAction.FAIL)
    if state.discovery_attempts == 0:
        return (PlanningAction.DISCOVER_STRICT,)
    if not state.candidates:
        if state.discovery_attempts == 1:
            return (PlanningAction.DISCOVER_NEARBY, PlanningAction.FAIL)
        return (PlanningAction.FAIL,)
    if state.composition_attempts == 0:
        return (PlanningAction.COMPOSE_ITINERARY,)
    if state.stop_count == 0:
        if state.composition_attempts == 1:
            return (PlanningAction.REPAIR_ITINERARY,)
        return (PlanningAction.FAIL,)
    if state.routing_available and not state.routing_attempted:
        return (PlanningAction.BUILD_ROUTES,)
    return (PlanningAction.FINISH,)


def _observation(state: PlanningState) -> PlanningObservation:
    actions = _actions(state)
    if state.locality is None:
        stage = "locality"
    elif not state.candidates:
        stage = "discovery"
    elif not state.days:
        stage = "composition"
    else:
        stage = "completion"
    return PlanningObservation(
        iteration=len(state.decisions) + 1,
        stage=stage,
        remaining_decisions=state.remaining_decisions,
        has_locality=state.locality is not None,
        discovery_attempts=state.discovery_attempts,
        candidate_count=len(state.candidates),
        rejected_count=state.rejected_count,
        day_count=len(state.days),
        stop_count=state.stop_count,
        routing_available=state.routing_available,
        route_count=len(state.routes),
        warnings_count=len(state.warnings),
    )


async def select_action(
    state: PlanningState, policy: PlanningPolicy | None,
) -> PlanningDecision:
    allowed = allowed_actions(state)
    fallback = allowed[0]
    if policy is None or len(allowed) == 1:
        return PlanningDecision(
            action=fallback, reason="Selected by deterministic planning guard."
        )
    try:
        decision = await policy.choose(_observation(state), allowed)
        if decision.action not in allowed:
            raise PlanningPolicyError("disallowed action")
        return decision
    except (PlanningPolicyError, ValueError, TypeError):
        return PlanningDecision(
            action=fallback,
            reason="Policy unavailable; used the deterministic fallback.",
        )


def validate_itinerary(
    request: TasteRouteRequest,
    candidates: list[PlaceCandidate],
    days: list[ItineraryDay],
    route_lookup=None,
) -> list[ItineraryDay]:
    """Validate provenance, dates, ordering, and the non-empty completion invariant."""
    non_empty = [day for day in days if day.items]
    if not non_empty:
        raise CandidateValidationError("Plan must contain at least one stop")
    enforce_plan_provenance(
        (item.place_id for day in non_empty for item in day.items), candidates
    )
    invalid_dates = sorted(
        str(day.date) for day in non_empty
        if day.date < request.start_date or day.date > request.end_date
    )
    if invalid_dates:
        raise CandidateValidationError(
            "Plan contains dates outside the requested trip: " + ", ".join(invalid_dates)
        )
    dates = [day.date for day in non_empty]
    if len(dates) != len(set(dates)):
        raise CandidateValidationError("Plan contains duplicate itinerary dates")
    for day in non_empty:
        times = [item.start_time for item in day.items]
        if times != sorted(times) or len(times) != len(set(times)):
            raise CandidateValidationError("Plan contains unordered itinerary times")
    return sorted(non_empty, key=lambda day: day.date)


def validate_schedule(days: list[ItineraryDay], route_by_date: dict) -> None:
    """Reject transitions that cannot fit between declared visit start times."""
    for day in days:
        route = route_by_date.get(day.date)
        if route is None:
            continue
        legs = {(leg.from_place_id, leg.to_place_id): leg for leg in route.legs}
        for previous, following in zip(day.items, day.items[1:]):
            leg = legs.get((previous.place_id, following.place_id))
            if leg is None:
                continue
            previous_hour, previous_minute = map(int, previous.start_time.split(":"))
            following_hour, following_minute = map(int, following.start_time.split(":"))
            available = (following_hour * 60 + following_minute) - (
                previous_hour * 60 + previous_minute
            )
            required = previous.duration_minutes + leg.duration_minutes
            if available < required:
                raise CandidateValidationError(
                    "Plan does not leave enough time between adjacent stops"
                )


class TasteRouteOrchestrator:
    def __init__(
        self, *, qloo: QlooPort, composer: ItineraryComposer,
        policy: PlanningPolicy | None = None, max_decisions: int = 8,
        nearby_radius_meters: int = 10_000,
        routing: RoutingPort | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._qloo = qloo
        self._composer = composer
        self._policy = policy
        self._max_decisions = max_decisions
        self._nearby_radius_meters = nearby_radius_meters
        self._routing = routing
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))

    async def plan(
        self, request: TasteRouteRequest,
        on_progress: ProgressCallback | None = None,
    ) -> TasteRouteResponse:
        state = PlanningState(
            request_id=self._request_id_factory(), request=request,
            max_decisions=self._max_decisions, routing_available=self._routing is not None,
        )
        log_planning_event(
            "plan.started", request_id=state.request_id,
            seed_count=len(request.taste_seeds),
        )
        state.seed_ids, state.seed_names, state.warnings = await self._resolve_seed_ids(request)
        if not state.seed_ids:
            state.warnings.append("No taste seeds could be resolved by Qloo.")
            return self._response(state, "failed")

        terminal_action: PlanningAction | None = None
        while len(state.decisions) < state.max_decisions:
            selected = await select_action(state, self._policy)
            status, metrics = await self._execute(state, selected.action)
            record = AgentDecision(
                iteration=len(state.decisions) + 1,
                action=selected.action.value,
                status=status,
                reason=selected.reason,
                metrics=metrics,
            )
            state.decisions.append(record)
            log_planning_event(
                "agent.decision", request_id=state.request_id,
                iteration=record.iteration, action=record.action,
                status=record.status, reason_code=record.action,
                candidate_count=len(state.candidates), stop_count=state.stop_count,
            )
            if on_progress is not None:
                await on_progress(record)
            if selected.action in {PlanningAction.FINISH, PlanningAction.FAIL}:
                terminal_action = selected.action
                break

        if terminal_action is None:
            state.warnings.append("The planning decision limit was reached before completion.")
        completion = (
            "completed" if terminal_action is PlanningAction.FINISH and state.stop_count > 0
            else "partial" if state.candidates
            else "failed"
        )
        return self._response(state, completion)

    async def _execute(
        self, state: PlanningState, action: PlanningAction,
    ) -> tuple[str, dict[str, int | float]]:
        if action is PlanningAction.RESOLVE_LOCALITY:
            state.locality_results = await self._qloo.resolve_localities(
                state.request.destination, take=5
            )
            if state.locality_results:
                selected = self._select_locality(
                    state.request.destination, state.locality_results
                )
                state.locality = ResolvedLocality(id=selected.id, name=selected.name)
                log_planning_event(
                    "locality.resolved", request_id=state.request_id,
                    locality_id=selected.id, locality_name=selected.name,
                    raw_count=len(state.locality_results),
                )
                return "completed", {"result_count": len(state.locality_results)}
            state.warnings.append("Qloo could not resolve this destination.")
            log_planning_event("locality.failed", request_id=state.request_id, raw_count=0)
            return "failed", {"result_count": 0}

        if action in {PlanningAction.DISCOVER_STRICT, PlanningAction.DISCOVER_NEARBY}:
            radius = 0 if action is PlanningAction.DISCOVER_STRICT else self._nearby_radius_meters
            discovered = await self._qloo.recommend_places(
                locality_id=state.locality.id,
                entity_ids=state.seed_ids,
                radius_meters=radius,
                take=20,
            )
            state.discovery_attempts += 1
            report = validate_candidates(
                discovered, excluded_ids=set(state.request.excluded_place_ids)
            )
            state.raw_candidate_count += len(discovered)
            state.rejected_count += (
                report.duplicate_count + report.excluded_count
                + report.missing_coordinates_count
            )
            state.candidates = self._name_contributions(report.valid, state.seed_names)
            log_planning_event(
                "candidates.validated", request_id=state.request_id,
                attempt=state.discovery_attempts, raw_count=len(discovered),
                candidate_count=len(state.candidates),
                duplicate_count=report.duplicate_count,
                excluded_count=report.excluded_count,
                missing_coordinates_count=report.missing_coordinates_count,
            )
            if not state.candidates and state.discovery_attempts >= 2:
                state.warnings.append(
                    "No usable Qloo places were found for the resolved locality."
                )
            return "completed", {"candidate_count": len(state.candidates), "radius_meters": radius}

        if action in {PlanningAction.COMPOSE_ITINERARY, PlanningAction.REPAIR_ITINERARY}:
            state.composition_attempts += 1
            if self._routing is not None and not state.matrix_attempted:
                state.matrix_attempted = True
                try:
                    state.travel_matrix = await self._routing.build_matrix(state.candidates)
                except RoutingServiceError as error:
                    state.warnings.append(
                        "Driving travel-time evidence was unavailable; planning used Qloo coordinates."
                    )
                    log_planning_event(
                        "routing.degraded", request_id=state.request_id,
                        error_code=error.code, error=error,
                    )
            correction = None
            if action is PlanningAction.REPAIR_ITINERARY:
                correction = (
                    "Return at least one valid stop, using only supplied Qloo place IDs, "
                    "inside the requested dates with ordered start times."
                )
            try:
                proposed = await self._composer.compose(
                    state.request, state.candidates,
                    travel_matrix=state.travel_matrix,
                    correction=correction,
                )
                state.days = validate_itinerary(state.request, state.candidates, proposed)
                if action is PlanningAction.REPAIR_ITINERARY:
                    state.routing_attempted = False
                    state.routes = []
                if action is PlanningAction.REPAIR_ITINERARY:
                    state.warnings.append("The itinerary required one automatic repair pass.")
                return (
                    "repaired" if action is PlanningAction.REPAIR_ITINERARY else "completed",
                    {"day_count": len(state.days), "stop_count": state.stop_count},
                )
            except (ItineraryComposerError, CandidateValidationError) as error:
                state.days = []
                state.last_error_code = type(error).__name__
                log_planning_event(
                    "composition.failed", request_id=state.request_id,
                    attempt=state.composition_attempts, error=error,
                )
                if state.composition_attempts >= 2:
                    state.warnings.append("Itinerary composition did not produce a usable plan.")
                return "failed", {"day_count": 0, "stop_count": 0}

        if action is PlanningAction.BUILD_ROUTES:
            state.routing_attempted = True
            state.routes = []
            candidate_by_id = {candidate.id: candidate for candidate in state.candidates}
            try:
                for day in state.days:
                    if len(day.items) > 1:
                        state.routes.append(
                            await self._routing.route_day(day, candidate_by_id)
                        )
                validate_schedule(
                    state.days, {route.date: route for route in state.routes}
                )
                return "completed", {"route_count": len(state.routes)}
            except CandidateValidationError as error:
                state.days = []
                state.routes = []
                state.last_error_code = type(error).__name__
                return "failed", {"route_count": 0}
            except RoutingServiceError as error:
                state.routes = []
                state.warnings.append(
                    "Driving routing was unavailable; the map uses geometric lines."
                )
                log_planning_event(
                    "routing.degraded", request_id=state.request_id,
                    error_code=error.code, error=error,
                )
                return "failed", {"route_count": 0}

        if action is PlanningAction.FINISH:
            return "completed", {"stop_count": state.stop_count}
        if action is PlanningAction.FAIL:
            return "failed", {"candidate_count": len(state.candidates), "stop_count": state.stop_count}
        return "skipped", {}

    @staticmethod
    def _select_locality(query: str, results: list[QlooEntity]) -> QlooEntity:
        normalized = query.strip().casefold()
        return next(
            (item for item in results if item.name.strip().casefold() == normalized),
            results[0],
        )

    async def _resolve_seed_ids(
        self, request: TasteRouteRequest,
    ) -> tuple[list[str], dict[str, str], list[str]]:
        ids: list[str] = []
        names: dict[str, str] = {}
        warnings: list[str] = []
        for seed in request.taste_seeds:
            if seed.id:
                ids.append(seed.id)
                names[seed.id] = seed.name
                continue
            results = await self._qloo.search_entities(seed.name, seed.entity_type, take=1)
            if results:
                ids.append(results[0].id)
                names[results[0].id] = seed.name
            else:
                warnings.append(f"Could not resolve taste seed: {seed.name}")
        return list(dict.fromkeys(ids)), names, warnings

    @staticmethod
    def _name_contributions(
        candidates: list[PlaceCandidate], seed_names: dict[str, str],
    ) -> list[PlaceCandidate]:
        return [candidate.model_copy(update={"contributions": [
            contribution.model_copy(update={
                "name": contribution.name or seed_names.get(contribution.entity_id)
            }) for contribution in candidate.contributions
        ]}) for candidate in candidates]

    def _response(self, state: PlanningState, completion: str) -> TasteRouteResponse:
        tags = list(dict.fromkeys(
            tag for candidate in state.candidates for tag in candidate.tags
        ))[:8]
        trace = [WorkflowStep(
            key=decision.action,
            label=decision.action.replace("_", " ").title(),
            status=decision.status,
        ) for decision in state.decisions]
        log_planning_event(
            f"plan.{completion}", request_id=state.request_id,
            candidate_count=len(state.candidates), stop_count=state.stop_count,
        )
        return TasteRouteResponse(
            success=completion != "failed",
            message=(
                "TasteRoute planning completed." if completion == "completed"
                else "TasteRoute produced a partial result." if completion == "partial"
                else "TasteRoute could not produce a usable plan."
            ),
            data=TasteRoutePlan(
                request_id=state.request_id,
                destination=state.request.destination,
                start_date=state.request.start_date,
                end_date=state.request.end_date,
                taste_profile=TasteProfile(tags=tags, seeds=state.request.taste_seeds),
                candidates=state.candidates,
                days=state.days,
                warnings=state.warnings,
                trace=trace,
                completion_status=completion,
                locality=state.locality,
                decisions=state.decisions,
                routes=state.routes,
            ),
            error_code="PLANNING_INCOMPLETE" if completion == "failed" else None,
            retryable=completion == "failed",
        )
