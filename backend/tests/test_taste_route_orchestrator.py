from datetime import date

import pytest

from app.agents.taste_route_orchestrator import (
    ItineraryComposerError,
    TasteRouteOrchestrator,
)
from app.models.qloo import PlaceCandidate, QlooContribution, QlooEntity
from app.models.schemas import (
    ItineraryDay,
    ItineraryItem,
    TasteRouteRequest,
    TasteSeed,
    WorkflowStep,
)
from app.services.candidate_validator import CandidateValidationError


def _request(*seeds: TasteSeed) -> TasteRouteRequest:
    return TasteRouteRequest(
        destination="New York",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        pace="balanced",
        budget="medium",
        taste_seeds=list(seeds),
        constraints=["prefer walking"],
    )


def _candidate(entity_id: str, *, tags: list[str] | None = None) -> PlaceCandidate:
    return PlaceCandidate(
        id=entity_id,
        name=f"Place {entity_id}",
        latitude=40.75,
        longitude=-73.92,
        tags=tags or [],
    )


class FakeQlooService:
    def __init__(self, candidates: list[PlaceCandidate]) -> None:
        self.candidates = candidates
        self.search_results: dict[str, list[QlooEntity]] = {}
        self.recommended_with: list[str] = []

    async def search_entities(self, query, entity_type=None, *, take=10):
        return self.search_results.get(query, [])

    async def recommend_places(self, *, destination, entity_ids, take=20):
        self.recommended_with = list(entity_ids)
        return self.candidates


class FakeComposer:
    def __init__(self, days: list[ItineraryDay] | None = None) -> None:
        self.days = days or []
        self.called = False

    async def compose(self, request, candidates, correction=None):
        self.called = True
        return self.days


@pytest.mark.anyio
async def test_plan_emits_real_workflow_progress_in_order():
    events: list[WorkflowStep] = []
    async def collect(step: WorkflowStep) -> None:
        events.append(step)

    orchestrator = TasteRouteOrchestrator(
        qloo=FakeQlooService([_candidate("museum")]),
        composer=FakeComposer(),
    )

    await orchestrator.plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie")),
        on_progress=collect,
    )

    assert [(event.key, event.status) for event in events] == [
        ("taste_resolution", "active"),
        ("taste_resolution", "completed"),
        ("qloo_discovery", "active"),
        ("qloo_discovery", "completed"),
        ("itinerary_composition", "active"),
        ("itinerary_composition", "completed"),
    ]


@pytest.mark.anyio
async def test_plan_builds_taste_profile_and_provenance_safe_itinerary():
    qloo = FakeQlooService(
        [_candidate("museum", tags=["Film museum", "Design"]), _candidate("cafe", tags=["Design"])]
    )
    composer = FakeComposer(
        [
            ItineraryDay(
                date=date(2026, 11, 10),
                items=[
                    ItineraryItem(
                        place_id="museum",
                        start_time="10:00",
                        duration_minutes=120,
                        reason="Connected to the selected films.",
                    )
                ],
            )
        ]
    )
    orchestrator = TasteRouteOrchestrator(
        qloo=qloo, composer=composer, request_id_factory=lambda: "request-123"
    )

    result = await orchestrator.plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
    )

    assert result.success is True
    assert result.data is not None
    assert result.data.request_id == "request-123"
    assert result.data.taste_profile.tags == ["Film museum", "Design"]
    assert result.data.taste_profile.seeds[0].name == "Blade Runner"
    assert [step.status for step in result.data.trace] == ["completed", "completed", "completed"]
    assert [candidate.id for candidate in result.data.candidates] == ["museum", "cafe"]
    assert result.data.days[0].items[0].place_id == "museum"
    assert qloo.recommended_with == ["movie-1"]


@pytest.mark.anyio
async def test_plan_keeps_resolved_seeds_and_warns_about_unresolved_names():
    qloo = FakeQlooService([_candidate("museum")])
    composer = FakeComposer()
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    result = await orchestrator.plan(
        _request(
            TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"),
            TasteSeed(name="Unknown Film", entity_type="movie"),
        )
    )

    assert qloo.recommended_with == ["movie-1"]
    assert result.data is not None
    assert result.data.warnings == ["Could not resolve taste seed: Unknown Film"]


@pytest.mark.anyio
async def test_plan_returns_partial_result_when_no_seed_can_be_resolved():
    qloo = FakeQlooService([_candidate("unused")])
    composer = FakeComposer()
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    result = await orchestrator.plan(
        _request(TasteSeed(name="Unknown Film", entity_type="movie"))
    )

    assert result.data is not None
    assert result.data.candidates == []
    assert result.data.days == []
    assert result.data.warnings == [
        "Could not resolve taste seed: Unknown Film",
        "No taste seeds could be resolved by Qloo.",
    ]
    assert composer.called is False


@pytest.mark.anyio
async def test_plan_returns_discovery_result_without_calling_composer_when_no_candidates():
    qloo = FakeQlooService([])
    composer = FakeComposer()
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    result = await orchestrator.plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
    )

    assert result.success is True
    assert result.data is not None
    assert result.data.candidates == []
    assert result.data.days == []
    assert "No usable Qloo places" in result.data.warnings[0]
    assert composer.called is False


class FailingComposer(FakeComposer):
    async def compose(self, request, candidates, correction=None):
        raise ItineraryComposerError("model unavailable")


@pytest.mark.anyio
async def test_plan_preserves_qloo_discoveries_when_composer_fails():
    qloo = FakeQlooService([_candidate("museum")])
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=FailingComposer())

    result = await orchestrator.plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
    )

    assert result.success is True
    assert result.data is not None
    assert [candidate.id for candidate in result.data.candidates] == ["museum"]
    assert result.data.days == []
    assert result.data.warnings == ["Itinerary composition is temporarily unavailable."]


@pytest.mark.anyio
async def test_plan_rejects_composer_output_with_unknown_place_id():
    qloo = FakeQlooService([_candidate("known")])
    composer = FakeComposer(
        [
            ItineraryDay(
                date=date(2026, 11, 10),
                items=[
                    ItineraryItem(
                        place_id="invented",
                        start_time="10:00",
                        duration_minutes=60,
                        reason="Invented by the model.",
                    )
                ],
            )
        ]
    )
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    with pytest.raises(CandidateValidationError, match="invented"):
        await orchestrator.plan(
            _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
        )


@pytest.mark.anyio
async def test_plan_repairs_invalid_first_composition_once():
    qloo = FakeQlooService([_candidate("known")])

    class RepairingComposer:
        def __init__(self):
            self.corrections = []

        async def compose(self, request, candidates, correction=None):
            self.corrections.append(correction)
            place_id = "invented" if correction is None else "known"
            return [
                ItineraryDay(
                    date=date(2026, 11, 10),
                    items=[ItineraryItem(place_id=place_id, start_time="10:00", duration_minutes=60, reason="Grounded choice.")],
                )
            ]

    composer = RepairingComposer()
    result = await TasteRouteOrchestrator(qloo=qloo, composer=composer).plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
    )

    assert result.data is not None
    assert result.data.days[0].items[0].place_id == "known"
    assert composer.corrections[0] is None
    assert "invented" in composer.corrections[1]
    assert result.data.trace[-1].status == "repaired"


@pytest.mark.anyio
async def test_plan_replaces_contribution_ids_with_selected_seed_names():
    candidate = _candidate("museum")
    candidate.contributions = [QlooContribution(entity_id="movie-1", score=0.8)]
    result = await TasteRouteOrchestrator(
        qloo=FakeQlooService([candidate]), composer=FakeComposer()
    ).plan(_request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie")))

    assert result.data is not None
    assert result.data.candidates[0].contributions[0].name == "Blade Runner"


@pytest.mark.anyio
async def test_plan_rejects_itinerary_day_outside_requested_dates():
    qloo = FakeQlooService([_candidate("museum")])
    composer = FakeComposer(
        [
            ItineraryDay(
                date=date(2026, 11, 12),
                items=[
                    ItineraryItem(
                        place_id="museum",
                        start_time="10:00",
                        duration_minutes=60,
                        reason="Valid place on an invalid date.",
                    )
                ],
            )
        ]
    )
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    with pytest.raises(CandidateValidationError, match="outside the requested trip"):
        await orchestrator.plan(
            _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
        )


@pytest.mark.anyio
async def test_plan_orders_composer_days_chronologically():
    qloo = FakeQlooService([_candidate("museum")])
    composer = FakeComposer(
        [
            ItineraryDay(date=date(2026, 11, 11), items=[]),
            ItineraryDay(date=date(2026, 11, 10), items=[]),
        ]
    )
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    result = await orchestrator.plan(
        _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
    )

    assert result.data is not None
    assert [day.date for day in result.data.days] == [
        date(2026, 11, 10),
        date(2026, 11, 11),
    ]


@pytest.mark.anyio
async def test_plan_rejects_duplicate_itinerary_dates():
    qloo = FakeQlooService([_candidate("museum")])
    composer = FakeComposer(
        [
            ItineraryDay(date=date(2026, 11, 10), items=[]),
            ItineraryDay(date=date(2026, 11, 10), items=[]),
        ]
    )
    orchestrator = TasteRouteOrchestrator(qloo=qloo, composer=composer)

    with pytest.raises(CandidateValidationError, match="duplicate itinerary dates"):
        await orchestrator.plan(
            _request(TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie"))
        )
