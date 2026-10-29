"""Private contracts for TasteRoute's bounded planning controller."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from .qloo import PlaceCandidate, QlooEntity
from .schemas import AgentDecision, ItineraryDay, ResolvedLocality, TasteRouteRequest


class PlanningAction(StrEnum):
    RESOLVE_LOCALITY = "resolve_locality"
    DISCOVER_STRICT = "discover_strict"
    DISCOVER_NEARBY = "discover_nearby"
    COMPOSE_ITINERARY = "compose_itinerary"
    REPAIR_ITINERARY = "repair_itinerary"
    BUILD_ROUTES = "build_routes"
    FINISH = "finish"
    FAIL = "fail"


class PlanningObservation(BaseModel):
    """Compact, sanitized state passed to the LLM policy."""

    iteration: int = Field(ge=1)
    stage: str = Field(min_length=1, max_length=40)
    remaining_decisions: int = Field(ge=0)
    has_locality: bool
    discovery_attempts: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    day_count: int = Field(ge=0)
    stop_count: int = Field(ge=0)
    routing_available: bool
    route_count: int = Field(ge=0)
    warnings_count: int = Field(ge=0)


class PlanningDecision(BaseModel):
    action: PlanningAction
    reason: str = Field(min_length=1, max_length=240)


class PlanningPolicy(Protocol):
    async def choose(
        self,
        observation: PlanningObservation,
        allowed_actions: tuple[PlanningAction, ...],
    ) -> PlanningDecision: ...


@dataclass
class PlanningState:
    """Mutable state owned exclusively by the deterministic controller."""

    request_id: str
    request: TasteRouteRequest
    max_decisions: int
    locality: ResolvedLocality | None = None
    locality_results: list[QlooEntity] = field(default_factory=list)
    seed_ids: list[str] = field(default_factory=list)
    seed_names: dict[str, str] = field(default_factory=dict)
    discovery_attempts: int = 0
    raw_candidate_count: int = 0
    rejected_count: int = 0
    candidates: list[PlaceCandidate] = field(default_factory=list)
    days: list[ItineraryDay] = field(default_factory=list)
    routes: list[object] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    decisions: list[AgentDecision] = field(default_factory=list)
    composition_attempts: int = 0
    routing_attempted: bool = False
    last_error_code: str | None = None

    @property
    def stop_count(self) -> int:
        return sum(len(day.items) for day in self.days)

    @property
    def remaining_decisions(self) -> int:
        return max(0, self.max_decisions - len(self.decisions))

