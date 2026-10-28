"""Structured LangChain adapter for composing Qloo-grounded itineraries."""

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..models.qloo import PlaceCandidate
from ..models.schemas import ItineraryDay, TasteRouteRequest
from .taste_route_orchestrator import ItineraryComposerError


class ItineraryComposition(BaseModel):
    days: list[ItineraryDay]


class LangChainItineraryComposer:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model.with_structured_output(
            ItineraryComposition, method="json_mode"
        )

    async def compose(
        self, request: TasteRouteRequest, candidates: list[PlaceCandidate]
    ) -> list[ItineraryDay]:
        payload = {
            "request": request.model_dump(mode="json"),
            "qloo_candidates": [
                candidate.model_dump(mode="json") for candidate in candidates
            ],
            "output_schema": ItineraryComposition.model_json_schema(),
        }
        messages = [
            SystemMessage(
                content=(
                    "Create a practical day-by-day itinerary from the supplied Qloo "
                    "candidates. Do not invent places or place IDs. Respect dates, pace, "
                    "budget, and constraints. Ground every reason only in the candidate's "
                    "Qloo tags, affinity, contributions, description, and the user's stated "
                    "constraints; say evidence is limited when those fields are absent. "
                    "Return only a JSON object matching output_schema exactly."
                )
            ),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        try:
            result = await self._model.ainvoke(messages)
            if isinstance(result, dict):
                result = ItineraryComposition.model_validate(result)
            if not isinstance(result, ItineraryComposition):
                raise TypeError("structured output has an unexpected type")
            return result.days
        except Exception as exc:
            raise ItineraryComposerError(
                "Itinerary composition is temporarily unavailable."
            ) from exc
