"""Validated public request and response contracts for TasteRoute."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from .qloo import PlaceCandidate

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
EntityType = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]
EntityId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
ConstraintText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]


class TasteSeed(BaseModel):
    id: EntityId | None = None
    name: ShortText
    entity_type: EntityType


class TasteRouteRequest(BaseModel):
    destination: ShortText
    start_date: date
    end_date: date
    pace: str = Field(default="balanced", pattern="^(relaxed|balanced|packed)$")
    budget: str = Field(default="medium", pattern="^(budget|medium|comfort)$")
    taste_seeds: list[TasteSeed] = Field(min_length=1, max_length=8)
    constraints: list[ConstraintText] = Field(default_factory=list, max_length=10)
    excluded_place_ids: list[EntityId] = Field(default_factory=list, max_length=50)

    @field_validator("end_date")
    @classmethod
    def end_date_not_before_start(cls, value: date, info):
        start_date = info.data.get("start_date")
        if start_date is not None and value < start_date:
            raise ValueError("end_date cannot be before start_date")
        if start_date is not None and (value - start_date).days >= 30:
            raise ValueError("trip cannot exceed 30 days")
        return value


class TasteProfile(BaseModel):
    tags: list[str] = Field(default_factory=list)
    seeds: list[TasteSeed] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    key: str
    label: str
    status: str = Field(pattern="^(completed|repaired|skipped|failed)$")


class ItineraryItem(BaseModel):
    place_id: str
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_minutes: int = Field(ge=15, le=720)
    reason: str = Field(min_length=1, max_length=500)


class ItineraryDay(BaseModel):
    date: date
    items: list[ItineraryItem] = Field(default_factory=list)


class TasteRoutePlan(BaseModel):
    request_id: str
    destination: str
    start_date: date
    end_date: date
    taste_profile: TasteProfile
    candidates: list[PlaceCandidate] = Field(default_factory=list)
    days: list[ItineraryDay] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[WorkflowStep] = Field(default_factory=list)


class TasteRouteResponse(BaseModel):
    success: bool
    message: str
    data: TasteRoutePlan | None = None
    error_code: str | None = None
    retryable: bool = False
