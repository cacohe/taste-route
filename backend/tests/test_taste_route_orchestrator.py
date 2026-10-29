from datetime import date

import pytest

from app.agents.planning_policy import PlanningPolicyError
from app.agents.taste_route_orchestrator import (
    TasteRouteOrchestrator,
    allowed_actions,
    select_action,
    validate_itinerary,
)
from app.models.planning import PlanningAction, PlanningDecision, PlanningState
from app.models.qloo import PlaceCandidate, QlooContribution, QlooEntity
from app.models.schemas import ItineraryDay, ItineraryItem, TasteRouteRequest, TasteSeed
from app.services.candidate_validator import CandidateValidationError


def _request(destination="上海") -> TasteRouteRequest:
    return TasteRouteRequest(
        destination=destination,
        start_date=date(2026, 10, 29),
        end_date=date(2026, 10, 31),
        taste_seeds=[TasteSeed(id="movie-1", name="Jane Eyre", entity_type="movie")],
        constraints=["quiet places"],
    )


def _candidate(entity_id="museum") -> PlaceCandidate:
    return PlaceCandidate(
        id=entity_id, name=f"Place {entity_id}", latitude=31.23, longitude=121.47,
        tags=["Film culture"],
        contributions=[QlooContribution(entity_id="movie-1", score=0.8)],
    )


def _day(place_id="museum") -> ItineraryDay:
    return ItineraryDay(
        date=date(2026, 10, 29),
        items=[ItineraryItem(
            place_id=place_id, start_time="10:00", duration_minutes=90,
            reason="Grounded in Qloo film affinity.",
        )],
    )


class FakeQloo:
    def __init__(self, strict=None, nearby=None, localities=None):
        self.strict = [_candidate()] if strict is None else strict
        self.nearby = self.strict if nearby is None else nearby
        self.localities = localities or [QlooEntity(
            id="shanghai-id", name="上海市", entity_type="locality",
        )]
        self.discovery_calls = []

    async def search_entities(self, query, entity_type=None, *, take=10):
        return []

    async def resolve_localities(self, query, *, take=5):
        return self.localities

    async def recommend_places(self, *, locality_id, entity_ids, radius_meters=0, take=20):
        self.discovery_calls.append((locality_id, radius_meters, tuple(entity_ids)))
        return self.strict if radius_meters == 0 else self.nearby


class SequenceComposer:
    def __init__(self, *results):
        self.results = list(results or ([_day()],))
        self.corrections = []

    async def compose(self, request, candidates, correction=None):
        self.corrections.append(correction)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result


class SequencePolicy:
    def __init__(self, *results):
        self.results = list(results)

    async def choose(self, observation, allowed):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _state(**overrides):
    values = dict(request_id="r1", request=_request(), max_decisions=8)
    values.update(overrides)
    return PlanningState(**values)


def test_allowed_actions_are_derived_from_observed_state():
    assert allowed_actions(_state()) == (PlanningAction.RESOLVE_LOCALITY, PlanningAction.FAIL)


@pytest.mark.anyio
async def test_select_action_falls_back_when_policy_returns_disallowed_action():
    policy = SequencePolicy(PlanningDecision(action=PlanningAction.FINISH, reason="Too early"))
    decision = await select_action(_state(), policy)
    assert decision.action is PlanningAction.RESOLVE_LOCALITY
    assert "fallback" in decision.reason.lower()


@pytest.mark.anyio
async def test_select_action_falls_back_when_policy_times_out():
    policy = SequencePolicy(PlanningPolicyError("provider prompt secret"))
    decision = await select_action(_state(), policy)
    assert decision.action is PlanningAction.RESOLVE_LOCALITY
    assert "secret" not in decision.reason


@pytest.mark.anyio
async def test_shanghai_uses_resolved_locality_id_and_strict_radius():
    qloo = FakeQloo()
    result = await TasteRouteOrchestrator(qloo=qloo, composer=SequenceComposer()).plan(_request())
    assert result.data is not None
    assert result.data.locality is not None
    assert result.data.locality.id == "shanghai-id"
    assert qloo.discovery_calls[0] == ("shanghai-id", 0, ("movie-1",))
    assert result.data.completion_status == "completed"
    assert result.data.days[0].items


@pytest.mark.anyio
async def test_strict_empty_discovery_retries_nearby_once():
    qloo = FakeQloo(strict=[], nearby=[_candidate("nearby")])
    result = await TasteRouteOrchestrator(
        qloo=qloo, composer=SequenceComposer([_day("nearby")]),
        nearby_radius_meters=12_000,
    ).plan(_request())
    assert [call[1] for call in qloo.discovery_calls] == [0, 12_000]
    assert result.data is not None
    assert result.data.completion_status == "completed"


def test_validate_itinerary_removes_empty_days_and_rejects_zero_stops():
    request = _request()
    assert validate_itinerary(request, [_candidate()], [
        ItineraryDay(date=date(2026, 10, 29), items=[]), _day(),
    ]) == [_day()]
    with pytest.raises(CandidateValidationError, match="at least one stop"):
        validate_itinerary(request, [_candidate()], [
            ItineraryDay(date=date(2026, 10, 29), items=[]),
        ])


@pytest.mark.anyio
async def test_empty_composition_repairs_once_then_returns_partial_candidates():
    composer = SequenceComposer([], [])
    result = await TasteRouteOrchestrator(qloo=FakeQloo(), composer=composer).plan(_request())
    assert result.success is True
    assert result.data is not None
    assert result.data.completion_status == "partial"
    assert result.data.days == []
    assert [candidate.id for candidate in result.data.candidates] == ["museum"]
    assert len(composer.corrections) == 2
    assert composer.corrections[0] is None
    assert composer.corrections[1] is not None
    assert [decision.action for decision in result.data.decisions].count("repair_itinerary") == 1


@pytest.mark.anyio
async def test_loop_never_exceeds_decision_budget():
    result = await TasteRouteOrchestrator(
        qloo=FakeQloo(strict=[], nearby=[]), composer=SequenceComposer(), max_decisions=2,
    ).plan(_request())
    assert result.data is not None
    assert len(result.data.decisions) == 2
    assert result.data.completion_status == "failed"
    assert any("decision limit" in warning.lower() for warning in result.data.warnings)


@pytest.mark.anyio
async def test_progress_contains_one_completed_record_per_executed_action():
    events = []
    async def collect(decision):
        events.append(decision)
    result = await TasteRouteOrchestrator(
        qloo=FakeQloo(), composer=SequenceComposer(), request_id_factory=lambda: "request-123",
    ).plan(_request(), on_progress=collect)
    assert result.data is not None
    assert events == result.data.decisions
    assert [event.iteration for event in events] == list(range(1, len(events) + 1))
    assert all(event.status in {"completed", "repaired", "failed"} for event in events)


@pytest.mark.anyio
async def test_contribution_names_are_grounded_in_selected_seed():
    result = await TasteRouteOrchestrator(qloo=FakeQloo(), composer=SequenceComposer()).plan(_request())
    assert result.data is not None
    assert result.data.candidates[0].contributions[0].name == "Jane Eyre"


def test_validate_itinerary_rejects_unknown_places_and_bad_dates():
    with pytest.raises(CandidateValidationError, match="invented"):
        validate_itinerary(_request(), [_candidate()], [_day("invented")])
    with pytest.raises(CandidateValidationError, match="outside"):
        validate_itinerary(_request(), [_candidate()], [
            ItineraryDay(date=date(2026, 11, 1), items=_day().items),
        ])
