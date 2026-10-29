"""Allowlisted one-line JSON logs for production planning diagnostics."""

import json
import logging

logger = logging.getLogger("taste_route.planning")

_ALLOWED_FIELDS = {
    "request_id", "locality_id", "locality_name", "seed_count", "attempt",
    "raw_count", "candidate_count", "rejected_count", "duplicate_count",
    "excluded_count", "missing_coordinates_count", "stop_count", "route_count",
    "distance_meters", "duration_minutes", "duration_ms", "action", "status",
    "reason_code", "iteration", "error_code",
}


def log_planning_event(event: str, **fields: object) -> None:
    payload: dict[str, object] = {"event": event}
    for key, value in fields.items():
        if key in _ALLOWED_FIELDS and isinstance(value, (str, int, float, bool, type(None))):
            payload[key] = value
    error = fields.get("error")
    if isinstance(error, BaseException):
        payload["error_class"] = type(error).__name__
    logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
