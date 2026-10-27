from datetime import date

import pytest

from app.agents.itinerary_composer import LangChainItineraryComposer
from app.agents.taste_route_orchestrator import ItineraryComposerError
from app.models.qloo import PlaceCandidate
from app.models.schemas import TasteRouteRequest, TasteSeed


def _request() -> TasteRouteRequest:
    return TasteRouteRequest(
        destination="New York",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        pace="balanced",
        budget="medium",
        taste_seeds=[TasteSeed(id="movie-1", name="Blade Runner", entity_type="movie")],
        constraints=["prefer walking"],
    )


def _candidate() -> PlaceCandidate:
    return PlaceCandidate(
        id="museum",
        name="Museum of the Moving Image",
        latitude=40.7563,
        longitude=-73.9239,
        tags=["Film museum"],
    )


class FakeStructuredModel:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.result


class FakeModel:
    def __init__(self, structured: FakeStructuredModel) -> None:
        self.structured = structured
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self.structured


@pytest.mark.anyio
async def test_composer_requests_structured_days_with_candidate_ids_in_prompt():
    structured = FakeStructuredModel(
        result={
            "days": [
                {
                    "date": "2026-11-10",
                    "items": [
                        {
                            "place_id": "museum",
                            "start_time": "10:00",
                            "duration_minutes": 120,
                            "reason": "Matches the selected film culture.",
                        }
                    ],
                }
            ]
        }
    )
    model = FakeModel(structured)
    composer = LangChainItineraryComposer(model)

    days = await composer.compose(_request(), [_candidate()])

    assert days[0].items[0].place_id == "museum"
    prompt = "\n".join(message.content for message in structured.messages)
    assert "museum" in prompt
    assert "prefer walking" in prompt
    assert "Do not invent" in prompt
    assert "Ground every reason" in prompt


@pytest.mark.anyio
async def test_composer_maps_model_failure_to_public_safe_error():
    model = FakeModel(FakeStructuredModel(error=RuntimeError("provider secret")))
    composer = LangChainItineraryComposer(model)

    with pytest.raises(ItineraryComposerError) as captured:
        await composer.compose(_request(), [_candidate()])

    assert "provider secret" not in str(captured.value)


@pytest.mark.anyio
async def test_composer_maps_invalid_structured_output_to_public_safe_error():
    model = FakeModel(FakeStructuredModel(result={"unexpected": []}))
    composer = LangChainItineraryComposer(model)

    with pytest.raises(ItineraryComposerError) as captured:
        await composer.compose(_request(), [_candidate()])

    assert str(captured.value) == "Itinerary composition is temporarily unavailable."

