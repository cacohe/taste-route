# TasteRoute Hackathon Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship TasteRoute as a single-origin, public-demo-safe, English-first Railway application with clearer Qloo evidence and reproducible submission documentation.

**Architecture:** A multi-stage Docker image builds Vue and runs FastAPI, which serves both API and SPA assets. The existing deterministic Qloo workflow gains bounded evidence, a truthful trace, one repair attempt, and process-local public-demo controls.

**Tech Stack:** FastAPI, Pydantic, HTTPX, LangChain, Vue 3, TypeScript, MapLibre, pytest, Vitest, Docker, Railway, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-28-hackathon-readiness-design.md`

## Global Constraints

- Qloo and LLM credentials remain backend-only and `.env` stays untracked.
- Every itinerary `place_id` must belong to the validated Qloo candidate set.
- The public demo uses one origin and no database.
- English is the submission UI language.
- Public controls are bounded, configurable, and process-local.
- Existing partial/error behavior remains honest.

## Review Focus

- Missing frontend build artifacts must not shadow API/docs routes or crash API-only startup.
- Concurrent plan requests above the configured limit must fail quickly and release permits after errors.
- Cache keys must include all inputs that affect Qloo or itinerary results and must expire.
- A repair attempt must never bypass provenance/date validation or loop more than once.
- SPA fallback must not convert unknown `/api/*` paths into HTML 200 responses.

---

### Task 1: Single-service deployment

**Files:** Create `Dockerfile`, `.dockerignore`, `railway.json`, `backend/app/api/static_site.py`, `backend/tests/test_static_site.py`; modify `backend/app/api/main.py`, `backend/app/config.py`, `.github/workflows/ci.yml`.

**Interfaces:** Produces `/health`, `mount_spa(app, directory)`, and a Docker/CI contract consumed by deployment docs.

- [ ] Write failing health, SPA fallback, missing-build, and unknown-API tests.
- [ ] Run focused tests and verify RED.
- [ ] Implement health/static routing and deployment files.
- [ ] Run focused tests, backend suite, and Docker build where available.
- [ ] Commit deployment foundation.

### Task 2: Public-demo controls

**Files:** Create `backend/app/services/runtime_controls.py`, `backend/tests/test_runtime_controls.py`; modify `backend/app/config.py`, `backend/app/api/dependencies.py`, `backend/app/api/routes/taste.py`, `backend/app/api/routes/trip.py`, `backend/app/services/llm_service.py`, `backend/.env.example`.

**Interfaces:** Produces TTL cache, per-client rate limiter, plan semaphore, and configurable LLM timeout/retries.

- [ ] Write failing expiry, rate-limit, concurrency-release, and configuration tests.
- [ ] Run focused tests and verify RED.
- [ ] Implement controls and route integration without caching failures.
- [ ] Run focused and full backend suites.
- [ ] Commit public-demo controls.

### Task 3: Evidence and Taste DNA

**Files:** Modify `backend/app/models/qloo.py`, `backend/app/models/schemas.py`, `backend/app/services/qloo_service.py`, `backend/app/agents/taste_route_orchestrator.py`, backend tests, `frontend/src/types/taste.ts`, `TasteProfileCard.vue`, `TasteExplanation.vue`, and component tests.

**Interfaces:** Produces bounded `PlaceCandidate.tags`, human-readable contributions, selected seeds, and weighted/aggregated Taste DNA.

- [ ] Write failing backend tests for tag bounding, contribution enrichment, and profile aggregation.
- [ ] Write failing frontend tests for bounded evidence and no raw UUID display.
- [ ] Run focused tests and verify RED.
- [ ] Implement evidence normalization and presentation.
- [ ] Run backend/frontend suites.
- [ ] Commit evidence improvements.

### Task 4: Trace and one repair attempt

**Files:** Modify schemas, composer protocol/implementation, orchestrator, result UI, and tests.

**Interfaces:** Produces `trace: list[WorkflowStep]` and `compose(..., correction: str | None)`; retries composition at most once after a deterministic validation failure.

- [ ] Write failing tests for successful trace, one repair, failed repair, and preserved provenance.
- [ ] Run focused tests and verify RED.
- [ ] Implement correction prompt and bounded repair loop.
- [ ] Render truthful trace in the result page.
- [ ] Run full suites.
- [ ] Commit agent workflow clarity.

### Task 5: English-first UI and production map

**Files:** Modify Vue views/components/utilities/tests, `frontend/src/vite-env.d.ts`, and `frontend/.env.example`.

**Interfaces:** Consumes existing API contracts; produces English UI and configurable map style.

- [ ] Update tests to expect English labels and map configuration behavior; verify RED.
- [ ] Translate all visible product/error/loading copy.
- [ ] Add `VITE_MAP_STYLE_URL` with local demo fallback and production documentation.
- [ ] Run frontend tests and build.
- [ ] Commit judge-facing UI.

### Task 6: Submission documentation and smoke checks

**Files:** Create `docs/deployment.md`, `scripts/smoke-test.ps1`; modify README, submission checklist, architecture/Qloo docs, CI.

**Interfaces:** Produces clean-environment deployment and a `BASE_URL` smoke-test contract.

- [ ] Add smoke checks for `/health`, `/`, and an invalid API request.
- [ ] Update README with Why Qloo, hackathon-period changes, architecture, validation, demo placeholders, and known limitations.
- [ ] Correct official submission requirements and owner actions.
- [ ] Run secret/reference scans, full tests, build, and diff checks.
- [ ] Commit submission readiness documentation.

### Task 7: Final integration review

**Files:** Review all changes from this plan.

- [ ] Build the production Docker image if Docker is available.
- [ ] Run backend compile/tests/pip check and frontend tests/build.
- [ ] Verify no `.env`, credential, raw UUID UI, Chinese visible copy, stale MiniMax config, or demo-only deployment claim remains.
- [ ] Record rulings/minors in the ledger and commit final fixes if required.

