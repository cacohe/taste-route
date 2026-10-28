from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "render_deploy.py"
SPEC = importlib.util.spec_from_file_location("render_deploy", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
render_deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_deploy)


class FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b'{"deploy":{"id":"dep-123"}}'):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def test_missing_hook_skips_without_network_call() -> None:
    calls = []

    result = render_deploy.trigger_deploy(
        hook_url="",
        commit_sha="a" * 40,
        open_url=lambda request, timeout: calls.append((request, timeout)),
    )

    assert result.status == "skipped"
    assert "RENDER_DEPLOY_HOOK_URL" in result.message
    assert calls == []


def test_missing_required_hook_fails_without_network_call() -> None:
    calls = []

    result = render_deploy.trigger_deploy(
        hook_url="",
        commit_sha="a" * 40,
        require_hook=True,
        open_url=lambda request, timeout: calls.append((request, timeout)),
    )

    assert result.status == "failed"
    assert "RENDER_DEPLOY_HOOK_URL" in result.message
    assert calls == []


def test_trigger_pins_commit_and_preserves_existing_query() -> None:
    captured = {}

    def open_url(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["timeout"] = timeout
        return FakeResponse()

    commit_sha = "0123456789abcdef" * 2 + "01234567"
    result = render_deploy.trigger_deploy(
        hook_url="https://api.render.com/deploy/srv-123?key=secret%2Bvalue",
        commit_sha=commit_sha,
        open_url=open_url,
    )

    assert result.status == "triggered"
    assert result.deploy_id == "dep-123"
    assert captured == {
        "url": (
            "https://api.render.com/deploy/srv-123"
            f"?key=secret%2Bvalue&ref={commit_sha}"
        ),
        "method": "POST",
        "timeout": 30,
    }


def test_trigger_rejects_invalid_commit_before_network_call() -> None:
    calls = []

    result = render_deploy.trigger_deploy(
        hook_url="https://api.render.com/deploy/srv-123?key=secret",
        commit_sha="main",
        open_url=lambda request, timeout: calls.append((request, timeout)),
    )

    assert result.status == "failed"
    assert "40-character" in result.message
    assert calls == []


def test_trigger_rejects_malformed_hook_without_leaking_it() -> None:
    calls = []

    result = render_deploy.trigger_deploy(
        hook_url="not-a-secret-hook-url",
        commit_sha="a" * 40,
        open_url=lambda request, timeout: calls.append((request, timeout)),
    )

    assert result.status == "failed"
    assert "valid HTTPS" in result.message
    assert "not-a-secret-hook-url" not in result.message
    assert calls == []


def test_trigger_reports_render_http_failure_without_leaking_hook() -> None:
    hook_url = "https://api.render.com/deploy/srv-123?key=super-secret"

    def open_url(_request, timeout):
        assert timeout == 30
        raise HTTPError(
            hook_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"invalid key"}'),
        )

    result = render_deploy.trigger_deploy(
        hook_url=hook_url,
        commit_sha="f" * 40,
        open_url=open_url,
    )

    assert result.status == "failed"
    assert "401" in result.message
    assert "super-secret" not in result.message
