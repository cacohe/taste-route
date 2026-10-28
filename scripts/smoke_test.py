"""Verify that the tested commit is live and serving the complete application."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeCheckError(RuntimeError):
    """Raised when the deployed application does not satisfy its smoke contract."""


def _read_text(url: str, open_url: Callable = urlopen) -> str:
    request = Request(url, headers={"User-Agent": "TasteRoute-CD-Smoke/1.0"})
    with open_url(request, timeout=10) as response:
        if not 200 <= response.status < 400:
            raise SmokeCheckError(f"{url} returned HTTP {response.status}.")
        return response.read().decode("utf-8")


def run_smoke_checks(
    base_url: str,
    expected_commit: str = "",
    timeout_seconds: float = 900,
    poll_interval_seconds: float = 10,
    open_url: Callable = urlopen,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    root = base_url.strip().rstrip("/")
    if not root.startswith("https://"):
        raise SmokeCheckError("Base URL must be an HTTPS URL.")
    if expected_commit and len(expected_commit) != 40:
        raise SmokeCheckError("Expected commit must be a full 40-character SHA.")

    deadline = monotonic() + timeout_seconds
    observed_commit = "not reported"
    last_error = "service did not become ready"
    while True:
        try:
            health = json.loads(_read_text(f"{root}/health", open_url))
            if not isinstance(health, Mapping):
                raise SmokeCheckError("Health check JSON must be an object.")
            observed_commit = str(health.get("commit") or "not reported")
            if health.get("status") == "ok" and (
                not expected_commit or observed_commit == expected_commit
            ):
                break
            last_error = f"expected commit {expected_commit}, observed {observed_commit}"
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, SmokeCheckError) as exc:
            last_error = f"{type(exc).__name__}: service is not ready"

        if monotonic() >= deadline:
            raise SmokeCheckError(f"Timed out waiting for deployment: {last_error}.")
        sleep(poll_interval_seconds)

    homepage = _read_text(f"{root}/", open_url)
    if "TasteRoute" not in homepage:
        raise SmokeCheckError("Frontend smoke check did not find the TasteRoute marker.")

    try:
        openapi = json.loads(_read_text(f"{root}/openapi.json", open_url))
    except json.JSONDecodeError as exc:
        raise SmokeCheckError("OpenAPI smoke check returned invalid JSON.") from exc
    if not isinstance(openapi, Mapping) or not isinstance(openapi.get("paths"), Mapping):
        raise SmokeCheckError("OpenAPI smoke check returned an invalid document structure.")
    if not openapi.get("openapi") or "/api/trip/plan" not in openapi["paths"]:
        raise SmokeCheckError("OpenAPI smoke check did not expose the trip planning route.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--timeout-seconds", type=float, default=900)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        run_smoke_checks(
            base_url=args.base_url,
            expected_commit=args.expected_commit,
            timeout_seconds=args.timeout_seconds,
        )
    except SmokeCheckError as exc:
        print(f"::error::{exc}")
        return 1
    print(f"TasteRoute smoke checks passed for {args.base_url.rstrip('/')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
