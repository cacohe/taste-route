"""Normalized Qloo domain models used outside the HTTP adapter."""

from pydantic import BaseModel, Field


class QlooEntity(BaseModel):
    id: str
    name: str
    entity_type: str
    description: str | None = None
    image_url: str | None = None


class QlooContribution(BaseModel):
    entity_id: str
    name: str | None = None
    score: float | None = Field(default=None, ge=0)


class PlaceCandidate(BaseModel):
    id: str
    name: str
    address: str | None = None
    description: str | None = None
    image_url: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    affinity: float | None = None
    tags: list[str] = Field(default_factory=list)
    contributions: list[QlooContribution] = Field(default_factory=list)

