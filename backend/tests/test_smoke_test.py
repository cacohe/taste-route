from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import URLError

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"
SPEC = importlib.util.spec_from_file_location("smoke_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
smoke_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke_test)


class FakeResponse:
    def __init__(self, body: str, status: int = 200, content_type: str = "application/json"):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def test_smoke_waits_for_expected_commit_then_checks_application() -> None:
    expected_commit = "b" * 40
    responses = iter(
        [
            FakeResponse(json.dumps({"status": "ok", "commit": "a" * 40})),
            FakeResponse(json.dumps({"status": "ok", "commit": expected_commit})),
            FakeResponse("<html><title>TasteRoute</title></html>", content_type="text/html"),
            FakeResponse(json.dumps({"openapi": "3.1.0", "paths": {"/api/trip/plan": {}}})),
        ]
    )
    requested_urls = []

    def open_url(request, timeout):
        requested_urls.append((request.full_url, timeout))
        return next(responses)

    smoke_test.run_smoke_checks(
        base_url="https://taste-route.onrender.com/",
        expected_commit=expected_commit,
        timeout_seconds=30,
        poll_interval_seconds=0,
        open_url=open_url,
        monotonic=lambda: 0,
        sleep=lambda _seconds: None,
    )

    assert requested_urls == [
        ("https://taste-route.onrender.com/health", 10),
        ("https://taste-route.onrender.com/health", 10),
        ("https://taste-route.onrender.com/", 10),
        ("https://taste-route.onrender.com/openapi.json", 10),
    ]


def test_smoke_retries_transient_network_failure() -> None:
    expected_commit = "c" * 40
    responses = iter(
        [
            URLError("service is starting"),
            FakeResponse(json.dumps({"status": "ok", "commit": expected_commit})),
            FakeResponse("TasteRoute", content_type="text/html"),
            FakeResponse(json.dumps({"openapi": "3.1.0", "paths": {"/api/trip/plan": {}}})),
        ]
    )

    def open_url(_request, timeout):
        assert timeout == 10
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    smoke_test.run_smoke_checks(
        base_url="https://taste-route.onrender.com",
        expected_commit=expected_commit,
        timeout_seconds=30,
        poll_interval_seconds=0,
        open_url=open_url,
        monotonic=lambda: 0,
        sleep=lambda _seconds: None,
    )


def test_smoke_times_out_when_only_previous_commit_is_live() -> None:
    times = iter([0, 0, 31])

    with pytest.raises(smoke_test.SmokeCheckError, match="expected commit"):
        smoke_test.run_smoke_checks(
            base_url="https://taste-route.onrender.com",
            expected_commit="d" * 40,
            timeout_seconds=30,
            poll_interval_seconds=0,
            open_url=lambda _request, timeout: FakeResponse(
                json.dumps({"status": "ok", "commit": "e" * 40})
            ),
            monotonic=lambda: next(times),
            sleep=lambda _seconds: None,
        )


def test_smoke_rejects_unrelated_openapi_document() -> None:
    expected_commit = "f" * 40
    responses = iter(
        [
            FakeResponse(json.dumps({"status": "ok", "commit": expected_commit})),
            FakeResponse("TasteRoute", content_type="text/html"),
            FakeResponse(json.dumps({"openapi": "3.1.0", "paths": {}})),
        ]
    )

    with pytest.raises(smoke_test.SmokeCheckError, match="trip planning route"):
        smoke_test.run_smoke_checks(
            base_url="https://taste-route.onrender.com",
            expected_commit=expected_commit,
            timeout_seconds=30,
            poll_interval_seconds=0,
            open_url=lambda _request, timeout: next(responses),
            monotonic=lambda: 0,
            sleep=lambda _seconds: None,
        )
