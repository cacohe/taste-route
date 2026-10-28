# TasteRoute UI, Generation Progress, and Map Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a polished homepage, truthful streamed generation progress, and a reliable itinerary-focused global street map for the public hackathon demo.

**Architecture:** Add an optional orchestration progress callback and a POST NDJSON streaming route, consumed by a small frontend stream parser. Move map data shaping and tag normalization into tested utilities, while `Result.vue` owns only MapLibre rendering and interactions. OpenFreeMap Liberty becomes the zero-configuration production default.

**Tech Stack:** FastAPI, Python 3.12, Vue 3, TypeScript, Vitest, pytest, MapLibre GL JS, OpenFreeMap Liberty.

**Spec:** `docs/superpowers/specs/2026-10-28-ui-generation-map-polish-design.md`

## Global Constraints

- Preserve the existing JSON planning endpoint and response schema.
- Do not show fabricated percentage completion.
- Default to `https://tiles.openfreemap.org/styles/liberty`; retain `VITE_MAP_STYLE_URL` override support.
- Prominent markers and route lines represent itinerary items, not every Qloo candidate.
- No new frontend runtime dependency unless the existing platform cannot express the behavior.
- All product behavior changes follow RED-GREEN-REFACTOR.

## Review Focus

- Stream chunks may split JSON records at arbitrary byte boundaries; the parser must preserve partial lines.
- A stream may end or fail before a result; the form must recover and show a retryable error.
- Partial plans may contain candidates but no itinerary days; the map must stay useful without inventing a route.
- Map style and tile failures arrive asynchronously; the user must see an error rather than a blank canvas.
- Candidate tags may be numeric-only, duplicated, blank, or malformed; none may leak into profile or evidence chips.

---

### Task 1: Normalize Qloo Tags

**Files:**
- Modify: `backend/app/services/candidate_validator.py`
- Test: `backend/tests/test_candidate_validator.py`

**Interfaces:**
- Produces: normalized `PlaceCandidate.tags` with trimmed, unique, non-numeric labels.

- [ ] Write failing tests for numeric-only, blank, duplicate, and valid tags.
- [ ] Run the focused pytest file and confirm the new assertions fail for leaked numeric tags.
- [ ] Implement minimal tag normalization at the Qloo candidate validation boundary.
- [ ] Run focused and full backend tests.
- [ ] Commit the task.

### Task 2: Stream Real Workflow Progress

**Files:**
- Modify: `backend/app/agents/taste_route_orchestrator.py`
- Modify: `backend/app/api/routes/trip.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_taste_route_orchestrator.py`
- Test: `backend/tests/test_taste_routes.py`

**Interfaces:**
- Produces: optional `on_progress(step: WorkflowStep) -> Awaitable[None]` orchestration callback.
- Produces: `POST /api/trip/plan/stream` with newline-delimited `progress`, `result`, or `error` JSON records.

- [ ] Write failing orchestrator tests proving real stage events occur in order.
- [ ] Write failing route tests for successful and failed NDJSON streams.
- [ ] Run focused tests and confirm failures are caused by the missing callback and route.
- [ ] Implement callback emission without changing existing plan results.
- [ ] Implement the streaming route using the existing limiter, gate, cache, and error contracts.
- [ ] Run focused and full backend tests.
- [ ] Commit the task.

### Task 3: Parse Streams and Render Generation Progress

**Files:**
- Create: `frontend/src/services/tripStream.ts`
- Create: `frontend/src/services/tripStream.test.ts`
- Create: `frontend/src/components/trip/GenerationProgress.vue`
- Create: `frontend/src/components/trip/GenerationProgress.test.ts`
- Create: `frontend/src/views/Home.test.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/views/Home.vue`

**Interfaces:**
- Produces: `generateTripPlanStream(request, onProgress, signal?) -> Promise<TasteRouteResponse>`.
- Produces: `GenerationProgress` props for current workflow step and elapsed state.

- [ ] Write failing parser tests for split chunks, error records, and missing terminal result.
- [ ] Write failing component/view tests for active, complete, error, and retry states.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement the parser and streaming API call.
- [ ] Implement the accessible workflow panel and wire it into form submission.
- [ ] Run focused and full frontend tests.
- [ ] Commit the task.

### Task 4: Fix and Refine the Homepage

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/Home.test.ts`

**Interfaces:**
- Consumes: `GenerationProgress` from Task 3.
- Produces: isolated `.planner > section` rules and responsive hero layout.

- [ ] Add a failing behavioral DOM/style contract test that distinguishes hero from planner steps.
- [ ] Run the focused test and confirm the current generic `section` structure fails it.
- [ ] Scope planner styles, cap the headline scale, add the route motif, and keep form content near the fold.
- [ ] Verify keyboard focus, reduced-motion CSS, desktop, and mobile layout contracts.
- [ ] Run the frontend suite and build.
- [ ] Commit the task.

### Task 5: Build the Itinerary Map Model

**Files:**
- Create: `frontend/src/utils/itineraryMap.ts`
- Create: `frontend/src/utils/itineraryMap.test.ts`
- Modify: `frontend/src/utils/mapConfig.ts`
- Modify: `frontend/src/utils/mapConfig.test.ts`
- Modify: `frontend/src/types/taste.ts`

**Interfaces:**
- Produces: ordered day routes and stop markers derived from itinerary days plus matching candidates.
- Produces: OpenFreeMap Liberty default style URL with environment override.

- [ ] Write failing tests for ordered stop markers, per-day route coordinates, missing candidates, partial plans, and the production default style.
- [ ] Run focused tests and verify failures.
- [ ] Implement the minimal pure map-model functions and new default style.
- [ ] Run focused and full frontend tests.
- [ ] Commit the task.

### Task 6: Render and Link the Polished Map

**Files:**
- Create: `frontend/src/components/trip/ItineraryMap.vue`
- Create: `frontend/src/components/trip/ItineraryMap.test.ts`
- Modify: `frontend/src/views/Result.vue`
- Create: `frontend/src/views/Result.test.ts`

**Interfaces:**
- Consumes: map model from Task 5.
- Produces: per-day lines, ordered markers, marker/card selection events, asynchronous load errors, and fallback state.

- [ ] Write failing tests for itinerary-only markers, selection linkage, async error state, and no-route fallback.
- [ ] Run focused tests and verify failures.
- [ ] Extract MapLibre rendering into `ItineraryMap.vue` and add load/error listeners plus timeout cleanup.
- [ ] Add per-day line layers, matching marker colors, and list/map selection linkage.
- [ ] Run focused and full frontend tests and build.
- [ ] Commit the task.

### Task 7: Deployment Contracts, Documentation, and End-to-End Verification

**Files:**
- Modify: `frontend/.env.example`
- Modify: `README.md`
- Modify: `docs/deployment.md`
- Modify: `docs/submission-checklist.md`
- Modify: `render.yaml`
- Modify: `.github/workflows/ci.yml` if the existing commands do not cover the new tests.
- Test: `backend/tests/test_deployment_config.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: documented provider override and CI/CD coverage for the shipped behavior.

- [ ] Update deployment tests first if configuration behavior changes.
- [ ] Document OpenFreeMap default, provider override, map attribution, progress protocol, and non-sleeping demo recommendation.
- [ ] Run backend tests, frontend tests/build, type checking, and production container build.
- [ ] Perform local browser checks at desktop and mobile widths, including generation and map failure states.
- [ ] Review the complete diff against the spec and resolve Important findings with RED-GREEN tests.
- [ ] Commit, push `main`, wait for CI/CD, confirm `/health` reports the deployed commit, and visually verify the public service.
