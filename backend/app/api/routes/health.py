"""Operational health endpoint for deployment platforms."""

import os

from fastapi import APIRouter

router = APIRouter(tags=["operations"])


@router.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    payload = {"status": "ok"}
    render_commit = os.getenv("RENDER_GIT_COMMIT", "").strip()
    if render_commit:
        payload["commit"] = render_commit
    return payload

