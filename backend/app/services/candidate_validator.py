"""Deterministic filtering and provenance enforcement for Qloo candidates."""

from collections.abc import Iterable

from ..models.qloo import PlaceCandidate


class CandidateValidationError(ValueError):
    pass


def _normalize_display_tags(tags: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = raw_tag.strip()
        if not tag or all(character.isdigit() or character.isspace() for character in tag):
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized


def validate_candidates(
    candidates: Iterable[PlaceCandidate], *, excluded_ids: set[str]
) -> list[PlaceCandidate]:
    """Keep the first usable occurrence of each non-excluded Qloo entity."""
    validated: list[PlaceCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.id in seen or candidate.id in excluded_ids:
            continue
        if candidate.latitude is None or candidate.longitude is None:
            continue
        seen.add(candidate.id)
        validated.append(candidate.model_copy(update={"tags": _normalize_display_tags(candidate.tags)}))
    return validated


def enforce_plan_provenance(
    planned_place_ids: Iterable[str], candidates: Iterable[PlaceCandidate]
) -> None:
    """Reject composer output that references entities Qloo did not return."""
    candidate_ids = {candidate.id for candidate in candidates}
    unknown_ids = sorted(set(planned_place_ids) - candidate_ids)
    if unknown_ids:
        raise CandidateValidationError(
            f"Plan contains unknown Qloo place IDs: {', '.join(unknown_ids)}"
        )
