"""Serve a built Vue SPA without masking backend routes."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_BACKEND_ROOTS = {"api", "docs", "redoc", "openapi.json", "health"}


def mount_spa(app: FastAPI, directory: str | Path) -> bool:
    root = Path(directory).resolve()
    index = root / "index.html"
    if not index.is_file():
        return False

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        normalized = full_path.lstrip("/")
        first_segment = normalized.split("/", 1)[0]
        if first_segment in _BACKEND_ROOTS:
            raise HTTPException(status_code=404, detail="Not found")

        candidate = (root / normalized).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    return True

