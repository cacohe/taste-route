"""FastAPI dependency constructors for TasteRoute services."""

from fastapi import Depends

from ..agents.itinerary_composer import LangChainItineraryComposer
from ..agents.taste_route_orchestrator import TasteRouteOrchestrator
from ..config import get_settings
from ..services.llm_service import get_llm
from ..services.qloo_service import QlooService


def get_qloo_service() -> QlooService:
    return QlooService(**get_settings().get_qloo_config())


def get_itinerary_composer() -> LangChainItineraryComposer:
    return LangChainItineraryComposer(get_llm())


def get_taste_route_orchestrator(
    qloo: QlooService = Depends(get_qloo_service),
    composer: LangChainItineraryComposer = Depends(get_itinerary_composer),
) -> TasteRouteOrchestrator:
    return TasteRouteOrchestrator(qloo=qloo, composer=composer)
