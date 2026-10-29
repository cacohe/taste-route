"""FastAPI dependency constructors for TasteRoute services."""

from fastapi import Depends

from ..agents.itinerary_composer import LangChainItineraryComposer
from ..agents.planning_policy import LangChainPlanningPolicy
from ..agents.taste_route_orchestrator import TasteRouteOrchestrator
from ..config import get_settings
from ..services.llm_service import get_llm
from ..services.qloo_service import QlooService
from ..services.routing_service import OSRMRoutingService
from ..services.runtime_controls import DemoControls

_demo_controls: DemoControls | None = None


def get_qloo_service() -> QlooService:
    return QlooService(**get_settings().get_qloo_config())


def get_itinerary_composer() -> LangChainItineraryComposer:
    return LangChainItineraryComposer(get_llm())


def get_planning_policy() -> LangChainPlanningPolicy:
    return LangChainPlanningPolicy(get_llm())


def get_routing_service() -> OSRMRoutingService:
    settings = get_settings()
    return OSRMRoutingService(
        settings.routing_base_url,
        timeout_seconds=settings.routing_timeout_seconds,
    )


def get_taste_route_orchestrator(
    qloo: QlooService = Depends(get_qloo_service),
    composer: LangChainItineraryComposer = Depends(get_itinerary_composer),
    policy: LangChainPlanningPolicy = Depends(get_planning_policy),
) -> TasteRouteOrchestrator:
    settings = get_settings()
    return TasteRouteOrchestrator(
        qloo=qloo,
        composer=composer,
        policy=policy,
        max_decisions=settings.agent_max_decisions,
        nearby_radius_meters=settings.qloo_nearby_radius_meters,
    )


def get_demo_controls() -> DemoControls:
    global _demo_controls
    if _demo_controls is None:
        settings = get_settings()
        _demo_controls = DemoControls(
            search_limit=settings.search_rate_limit_per_minute,
            plan_limit=settings.plan_rate_limit_per_minute,
            plan_concurrency=settings.plan_max_concurrency,
            search_ttl=settings.search_cache_ttl_seconds,
            plan_ttl=settings.plan_cache_ttl_seconds,
        )
    return _demo_controls
