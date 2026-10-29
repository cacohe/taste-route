# TasteRoute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build TasteRoute as a provenance-safe Qloo travel agent.

**Architecture:** A typed Qloo HTTP client feeds normalized entities and recommendations into deterministic validation. A constrained orchestrator passes only validated candidates to the itinerary composer, while Vue exposes entity search and Qloo evidence.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, HTTPX, LangChain, Vue 3, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-10-27-taste-route-design.md`

## Global Constraints

- Keep Qloo credentials server-side and redact them from all errors and logs.
- Never use fixtures or fabricated coordinates in production fallback paths.
- Every itinerary place must reference a validated Qloo candidate ID.
- Retain the original Git history but develop on `feature/taste-route` until the new private remote exists.
- Use test-first RED-GREEN cycles for production behavior.

## Review Focus

- A malformed Qloo payload must become a controlled upstream error, not an unhandled exception.
- A Qloo 401 or 429 body must not leak into the public API response.
- Duplicate or coordinate-less candidates must not enter an itinerary.
- A composer output containing an unknown place ID must be rejected.
- Stale frontend search responses must not replace results for a newer query.

---

### Task 1: Repository identity and dependency baseline

**Files:**
- Modify: `README.md`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `frontend/package.json`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.get_qloo_config() -> dict[str, object]` for Task 2.

- [ ] Add failing tests for Qloo defaults, required production values, and redacted config output.
- [ ] Run the focused tests and confirm the missing settings fail.
- [ ] Add the minimal Qloo settings and resolve the inherited MCP dependency conflict according to the recorded product ruling.
- [ ] Re-run focused tests and the backend baseline suite.
- [ ] Rebrand package and README identity without claiming live integration.
- [ ] Commit as `chore: initialize TasteRoute application`.

### Task 2: Typed Qloo client

**Files:**
- Create: `backend/app/models/qloo.py`
- Create: `backend/app/services/qloo_service.py`
- Create: `backend/tests/fixtures/qloo/search.json`
- Create: `backend/tests/fixtures/qloo/insights.json`
- Create: `backend/tests/test_qloo_service.py`

**Interfaces:**
- Consumes: `Settings.get_qloo_config()` from Task 1.
- Produces: `QlooService.search_entities(query, entity_type, take)` and `QlooService.recommend_places(destination, entity_ids, take)`.

- [ ] Add failing behavior tests for request parameters, normalization, auth failure, rate limit, timeout, and malformed JSON.
- [ ] Confirm each new behavior fails for the expected missing implementation.
- [ ] Implement normalized Pydantic models, safe error types, bounded retries, and an injected HTTP transport.
- [ ] Run the focused suite and then all backend tests.
- [ ] Commit as `feat: add typed Qloo API client`.

### Task 3: Candidate validation and provenance

**Files:**
- Create: `backend/app/services/candidate_validator.py`
- Create: `backend/tests/test_candidate_validator.py`

**Interfaces:**
- Consumes: normalized Qloo recommendations from Task 2.
- Produces: `validate_candidates(candidates, destination, excluded_ids) -> list[PlaceCandidate]` and `enforce_plan_provenance(plan, candidates)`.

- [ ] Add failing tests for duplicates, missing coordinates, excluded IDs, and an itinerary containing an unknown ID.
- [ ] Confirm the tests fail for missing behavior.
- [ ] Implement the minimal deterministic validator and provenance guard.
- [ ] Run focused and full backend suites.
- [ ] Commit as `feat: enforce Qloo candidate provenance`.

### Task 4: TasteRoute orchestration and schemas

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/agents/taste_route_orchestrator.py`
- Create: `backend/tests/test_taste_route_orchestrator.py`

**Interfaces:**
- Consumes: `QlooService`, validator, and an injected itinerary composer.
- Produces: `TasteRouteOrchestrator.plan(request) -> TripPlanResponse`.

- [ ] Add failing tests for successful orchestration, partial unresolved seeds, no candidates, composer failure, and provenance rejection.
- [ ] Confirm RED results.
- [ ] Implement request/response schemas and orchestration without adding unrequested persistence.
- [ ] Run focused and full backend suites.
- [ ] Commit as `feat: orchestrate taste-grounded trips`.

### Task 5: Public API routes

**Files:**
- Create: `backend/app/api/routes/taste.py`
- Modify: `backend/app/api/routes/trip.py`
- Modify: `backend/app/api/main.py`
- Create: `backend/tests/test_taste_routes.py`

**Interfaces:**
- Consumes: Task 2 search and Task 4 planning interfaces.
- Produces: `GET /api/taste/entities` and updated `POST /api/trip/plan`.

- [ ] Add failing FastAPI tests for validation, normalized success, and safe error codes.
- [ ] Confirm route tests fail before registration.
- [ ] Register dependency-injected routes and public error mapping.
- [ ] Run focused and full backend suites.
- [ ] Commit as `feat: expose TasteRoute APIs`.

### Task 6: Taste entity selection frontend

**Files:**
- Create: `frontend/src/types/taste.ts`
- Create: `frontend/src/components/taste/TasteEntitySearch.vue`
- Create: `frontend/src/components/taste/TasteSeedChip.vue`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/views/Home.vue`
- Create: `frontend/src/components/taste/TasteEntitySearch.test.ts`

**Interfaces:**
- Consumes: `GET /api/taste/entities` from Task 5.
- Produces: selected `TasteSeed[]` in the trip request.

- [ ] Add failing Vitest tests for debounced search, stale response protection, deduplication, removal, and submission minimums.
- [ ] Confirm RED results.
- [ ] Implement the minimal selector and request mapping.
- [ ] Run frontend tests and build.
- [ ] Commit as `feat: collect cultural taste seeds`.

### Task 7: Taste evidence result experience

**Files:**
- Create: `frontend/src/components/taste/TasteProfileCard.vue`
- Create: `frontend/src/components/trip/TasteExplanation.vue`
- Modify: `frontend/src/views/Result.vue`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/trip/TasteExplanation.test.ts`

**Interfaces:**
- Consumes: the provenance-rich response from Task 5.

- [ ] Add failing tests that bind each explanation to its Qloo candidate and render partial/error states honestly.
- [ ] Confirm RED results.
- [ ] Implement Taste DNA and per-place evidence without inventing missing affinity data.
- [ ] Run frontend tests and production build.
- [ ] Commit as `feat: explain Qloo-grounded itineraries`.

### Task 8: Release documentation and verification

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/qloo-integration.md`
- Create: `docs/live-validation.md`
- Create: `docs/submission-checklist.md`

**Interfaces:**
- Consumes: all shipped behavior and verified commands.

- [ ] Document only implemented capabilities and clearly label live-key validation as pending until run.
- [ ] Run all backend tests, frontend tests, frontend build, and secret scans.
- [ ] Record exact commands and results in the verification ledger.
- [ ] Commit as `docs: prepare TasteRoute hackathon release`.
