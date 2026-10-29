import pytest

from app.models.qloo import PlaceCandidate
from app.services.candidate_validator import (
    CandidateValidationError,
    enforce_plan_provenance,
    validate_candidates,
)


def _candidate(
    entity_id: str,
    *,
    latitude: float | None = 40.0,
    longitude: float | None = -73.0,
    tags: list[str] | None = None,
) -> PlaceCandidate:
    return PlaceCandidate(
        id=entity_id,
        name=f"Place {entity_id}",
        address="New York, NY",
        latitude=latitude,
        longitude=longitude,
        tags=tags or [],
    )


def test_validate_candidates_removes_duplicate_ids_in_rank_order():
    candidates = [_candidate("a"), _candidate("a"), _candidate("b")]

    validated = validate_candidates(candidates, excluded_ids=set())

    assert [candidate.id for candidate in validated.valid] == ["a", "b"]
    assert validated.duplicate_count == 1


def test_validate_candidates_keeps_later_usable_copy_after_invalid_duplicate():
    candidates = [
        _candidate("a", latitude=None),
        _candidate("a", latitude=40.0, longitude=-73.0),
    ]

    validated = validate_candidates(candidates, excluded_ids=set())

    assert [candidate.id for candidate in validated.valid] == ["a"]
    assert validated.missing_coordinates_count == 1


@pytest.mark.parametrize(
    ("latitude", "longitude"), [(None, -73.0), (40.0, None), (None, None)]
)
def test_validate_candidates_rejects_missing_coordinates(latitude, longitude):
    candidates = [_candidate("invalid", latitude=latitude, longitude=longitude)]

    validated = validate_candidates(candidates, excluded_ids=set())

    assert validated.valid == []
    assert validated.missing_coordinates_count == 1


def test_validate_candidates_removes_explicitly_excluded_ids():
    candidates = [_candidate("keep"), _candidate("exclude")]

    validated = validate_candidates(candidates, excluded_ids={"exclude"})

    assert [candidate.id for candidate in validated.valid] == ["keep"]
    assert validated.excluded_count == 1


def test_validate_candidates_normalizes_display_tags():
    candidates = [
        _candidate(
            "tagged",
            tags=[" Themed ", "45 54", "", "THEMED", "Family travel", "0 12"],
        )
    ]

    validated = validate_candidates(candidates, excluded_ids=set())

    assert validated.valid[0].tags == ["Themed", "Family travel"]


def test_validate_candidates_accepts_zero_coordinates():
    report = validate_candidates(
        [_candidate("origin", latitude=0.0, longitude=0.0)], excluded_ids=set()
    )

    assert [candidate.id for candidate in report.valid] == ["origin"]
    assert report.missing_coordinates_count == 0


def test_validate_candidates_reports_each_rejection_reason():
    report = validate_candidates(
        [
            _candidate("keep"),
            _candidate("keep"),
            _candidate("excluded"),
            _candidate("missing", longitude=None),
        ],
        excluded_ids={"excluded"},
    )

    assert [candidate.id for candidate in report.valid] == ["keep"]
    assert report.duplicate_count == 1
    assert report.excluded_count == 1
    assert report.missing_coordinates_count == 1


def test_enforce_plan_provenance_rejects_unknown_place_id():
    candidates = [_candidate("known")]

    with pytest.raises(CandidateValidationError, match="unknown"):
        enforce_plan_provenance(["known", "unknown"], candidates)


def test_enforce_plan_provenance_accepts_only_known_place_ids():
    candidates = [_candidate("first"), _candidate("second")]

    enforce_plan_provenance(["second", "first"], candidates)
