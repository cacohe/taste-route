from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import health
from app.api.static_site import mount_spa


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)
    return app


def test_health_endpoint_reports_ready():
    response = TestClient(_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mount_spa_is_a_noop_when_build_is_missing(tmp_path: Path):
    app = _app()

    assert mount_spa(app, tmp_path / "missing") is False
    assert TestClient(app).get("/").status_code == 404


def test_spa_serves_assets_and_falls_back_for_client_routes(tmp_path: Path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<h1>TasteRoute</h1>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('ready')", encoding="utf-8")
    app = _app()

    assert mount_spa(app, dist) is True

    client = TestClient(app)
    assert client.get("/").text == "<h1>TasteRoute</h1>"
    assert client.get("/result").text == "<h1>TasteRoute</h1>"
    assert client.get("/assets/app.js").text == "console.log('ready')"


def test_spa_does_not_turn_unknown_api_routes_into_html(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>TasteRoute</h1>", encoding="utf-8")
    app = _app()
    mount_spa(app, dist)

    response = TestClient(app).get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_spa_route_whose_name_starts_with_health_is_not_blocked(tmp_path: Path):
    (tmp_path / "index.html").write_text("<h1>TasteRoute</h1>", encoding="utf-8")
    app = _app()
    mount_spa(app, tmp_path)

    response = TestClient(app).get("/healthy-choices")

    assert response.status_code == 200
    assert "TasteRoute" in response.text
