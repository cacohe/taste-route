import json
import logging

from app.services.planning_log import log_planning_event


def test_planning_log_emits_allowlisted_one_line_json(caplog):
    with caplog.at_level(logging.INFO, logger="taste_route.planning"):
        log_planning_event(
            "agent.decision", request_id="request-1", action="discover_strict",
            status="completed", reason_code="strict_locality", candidate_count=4,
            duration_ms=18, api_key="do-not-log", prompt="raw prompt",
            constraints="quiet places",
        )
    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "agent.decision", "request_id": "request-1",
        "action": "discover_strict", "status": "completed",
        "reason_code": "strict_locality", "candidate_count": 4, "duration_ms": 18,
    }
    assert "do-not-log" not in caplog.text
    assert "raw prompt" not in caplog.text
    assert "quiet places" not in caplog.text


def test_planning_log_uses_safe_exception_class_not_message(caplog):
    with caplog.at_level(logging.INFO, logger="taste_route.planning"):
        log_planning_event("composition.failed", request_id="request-1", error=RuntimeError("provider secret"))
    payload = json.loads(caplog.records[-1].message)
    assert payload["error_class"] == "RuntimeError"
    assert "provider secret" not in caplog.text
