from __future__ import annotations

import json
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_render_blueprint_uses_main_and_waits_for_ci_deploy_hook() -> None:
    blueprint = yaml.safe_load((REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8"))
    service = blueprint["services"][0]
    secret_vars = {item["key"]: item["sync"] for item in service["envVars"]}

    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["branch"] == "main"
    assert service["autoDeployTrigger"] == "off"
    assert secret_vars == {
        "QLOO_API_KEY": False,
        "LLM_API_KEY": False,
        "LLM_BASE_URL": False,
        "LLM_MODEL": False,
    }


def test_railway_and_render_share_the_health_contract() -> None:
    railway = json.loads((REPOSITORY_ROOT / "railway.json").read_text(encoding="utf-8"))
    render = yaml.safe_load((REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8"))

    assert railway["build"]["dockerfilePath"] == "Dockerfile"
    assert railway["deploy"]["healthcheckPath"] == "/health"
    assert render["services"][0]["dockerfilePath"] == "./Dockerfile"
    assert render["services"][0]["healthCheckPath"] == "/health"


def test_ci_deploys_only_tested_main_pushes_to_render() -> None:
    workflow = yaml.load(
        (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert workflow["concurrency"]["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' }}"
    )

    deploy = workflow["jobs"]["deploy-render"]
    assert deploy["needs"] == ["backend", "frontend", "container"]
    assert deploy["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert deploy["steps"][-1]["env"] == {
        "RENDER_SERVICE_URL": "${{ vars.RENDER_SERVICE_URL }}",
        "GITHUB_SHA": "${{ github.sha }}",
    }
    assert deploy["steps"][-1]["run"] == (
        "python scripts/smoke_test.py --base-url \"$RENDER_SERVICE_URL\" "
        "--expected-commit \"$GITHUB_SHA\" --timeout-seconds 900"
    )
    assert deploy["steps"][-2]["run"] == "python scripts/render_deploy.py --require-hook"
