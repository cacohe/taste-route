# Render Live Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GitHub CD deploy the tested `main` commit to Render and automatically smoke-test the live service.

**Architecture:** Render exposes its current Git commit through `/health`. A tested Python smoke runner waits for that exact SHA and then validates the frontend and OpenAPI endpoints; GitHub Actions invokes it after the deploy hook.

**Tech Stack:** FastAPI, Python stdlib HTTP client, pytest, GitHub Actions, Render Docker Web Service.

**Spec:** `docs/superpowers/specs/2026-10-28-render-live-deploy-design.md`

## Global Constraints

- Secrets come only from ignored local configuration and must not enter source, logs, or responses.
- Only `main` deploys.
- CI must prove the exact commit is live, not merely that an older service responds.
- Railway support remains unchanged.

## Review Focus

- Old live commit responds successfully while a new deploy is still building.
- Render cold start temporarily returns network or 5xx errors.
- Hook or service URL configuration is missing.
- Homepage responds but is not the TasteRoute SPA.
- OpenAPI endpoint responds with malformed or unrelated JSON.

---

### Task 1: Commit-aware health and smoke runner

**Files:**
- Modify: `backend/app/api/routes/health.py`
- Modify: `backend/tests/test_static_site.py`
- Create: `scripts/smoke_test.py`
- Create: `backend/tests/test_smoke_test.py`
- Modify: `scripts/smoke-test.ps1`

**Interfaces:** Produces `/health.commit` and CLI arguments `--base-url`, `--expected-commit`, and `--timeout-seconds`.

- [x] Write failing health and smoke behavior tests.
- [x] Implement bounded commit-aware polling and endpoint validation.
- [x] Run focused and full backend suites.

### Task 2: CD integration and live Render service

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/render_deploy.py`
- Modify: `backend/tests/test_render_deploy.py`
- Modify: `backend/tests/test_deployment_config.py`
- Modify: `docs/deployment.md`
- Modify: `docs/submission-checklist.md`

**Interfaces:** Consumes `RENDER_DEPLOY_HOOK_URL`, `RENDER_SERVICE_URL`, and `github.sha`; produces a green workflow only after live smoke verification.

- [x] Add failing tests for mandatory CD configuration and post-deploy smoke wiring.
- [x] Implement the workflow and documentation changes.
- [x] Create/configure the Render service and GitHub Action values.
- [x] Push `main`, monitor Render to `live`, and verify the automated smoke job succeeds.
