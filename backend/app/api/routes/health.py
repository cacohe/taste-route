"""Operational health endpoint for deployment platforms."""

from fastapi import APIRouter

router = APIRouter(tags=["operations"])


@router.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

