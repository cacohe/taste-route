"""Trigger a Render deploy for the exact commit that passed GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Callable, NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class DeployResult(NamedTuple):
    status: str
    message: str
    deploy_id: str | None = None


def _url_for_commit(hook_url: str, commit_sha: str) -> str:
    parts = urlsplit(hook_url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("ref", commit_sha))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def trigger_deploy(
    hook_url: str,
    commit_sha: str,
    require_hook: bool = False,
    open_url: Callable = urlopen,
) -> DeployResult:
    """Trigger Render without ever returning or logging the secret hook URL."""
    if not hook_url.strip():
        return DeployResult(
            "failed" if require_hook else "skipped",
            "RENDER_DEPLOY_HOOK_URL is not configured; Render deployment cannot proceed."
            if require_hook
            else "RENDER_DEPLOY_HOOK_URL is not configured; Render deployment was skipped.",
        )
    if not SHA_PATTERN.fullmatch(commit_sha):
        return DeployResult("failed", "GITHUB_SHA must be a 40-character hexadecimal commit SHA.")
    hook_parts = urlsplit(hook_url)
    if hook_parts.scheme != "https" or not hook_parts.hostname:
        return DeployResult("failed", "RENDER_DEPLOY_HOOK_URL must be a valid HTTPS URL.")

    request = Request(_url_for_commit(hook_url, commit_sha), method="POST")
    try:
        with open_url(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
            deploy_id = payload.get("deploy", {}).get("id")
            return DeployResult(
                "triggered",
                f"Render accepted the tested commit (HTTP {response.status}).",
                deploy_id,
            )
    except HTTPError as exc:
        return DeployResult("failed", f"Render rejected the deploy hook request (HTTP {exc.code}).")
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return DeployResult("failed", f"Render deploy hook request failed: {type(exc).__name__}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-hook", action="store_true")
    args = parser.parse_args()
    result = trigger_deploy(
        hook_url=os.getenv("RENDER_DEPLOY_HOOK_URL", ""),
        commit_sha=os.getenv("GITHUB_SHA", ""),
        require_hook=args.require_hook,
    )
    annotation = "error" if result.status == "failed" else "notice"
    print(f"::{annotation}::{result.message}")
    if result.deploy_id:
        print(f"Render deploy ID: {result.deploy_id}")
    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
