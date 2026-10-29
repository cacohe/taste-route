# TasteRoute Agentic Planning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a bounded hybrid planning agent that resolves destinations correctly, rejects empty itineraries, explains Qloo decisions, uses degradable road routing, and fixes the category selector.

**Architecture:** A deterministic controller owns planning state and the allowed action set; a structured LLM policy chooses only when multiple safe actions are available. Qloo locality IDs constrain discovery, OSRM supplies optional driving evidence, and deterministic validators enforce provenance, locality, schedule, non-empty output, and bounded termination.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, HTTPX, LangChain structured output, pytest, Vue 3, TypeScript, MapLibre GL JS, Vitest, OSRM HTTP API

**Spec:** `docs/superpowers/specs/2026-10-29-agentic-planning-loop-design.md`

## Global Constraints

- Work only on `main`; do not create or maintain another branch.
- Use red/green TDD for every behavior change and commit each independently testable task.
- Qloo remains the only source of place candidates; no LLM-created place IDs, coordinates, affinity, tags, or contribution scores.
- The LLM may choose only from controller-provided actions; invalid or failed decisions use a deterministic fallback.
- The planning loop is bounded by `AGENT_MAX_DECISIONS` with a default of `8`.
- Strict discovery uses the resolved Qloo locality ID and `filter.location.radius=0`; one nearby retry uses `QLOO_NEARBY_RADIUS_METERS`, default `10000`.
- A completed plan must contain at least one stop and pass provenance, date, ordering, and known travel-time validation.
- OSRM uses the explicitly labeled `driving` profile and is optional; failure preserves the itinerary with geometric route fallback.
- Never log API keys, authorization headers, raw prompts, complete Qloo/LLM payloads, or free-text constraints.
- The frontend maps Qloo `artist` to the user-facing label `Music`; do not add duplicate Artist and Music API values.

## File structure

- `backend/app/models/schemas.py`: public locality, completion, decision, route, and leg contracts.
- `backend/app/models/planning.py`: private action enum, observation, decision, and mutable planning state.
- `backend/app/agents/planning_policy.py`: structured LLM action selection with allowed-action validation.
- `backend/app/agents/taste_route_orchestrator.py`: bounded control loop and deterministic guards.
- `backend/app/agents/itinerary_composer.py`: Qloo candidates plus optional compact travel matrix composition.
- `backend/app/services/qloo_service.py`: locality resolution and locality-ID place discovery.
- `backend/app/services/candidate_validator.py`: candidate report and plan/schedule validation.
- `backend/app/services/routing_service.py`: provider-neutral routing types and OSRM adapter.
- `backend/app/services/planning_log.py`: safe one-line JSON event logging.
- `backend/app/config.py`, `backend/app/api/dependencies.py`: controller and routing configuration/wiring.
- `frontend/src/types/taste.ts`: mirror public response contracts.
- `frontend/src/components/taste/TasteEntitySearch.vue`: width fix and Music label.
- `frontend/src/components/trip/GenerationProgress.vue`: dynamic real decision progress.
- `frontend/src/components/trip/TasteExplanation.vue`: scored Qloo contribution evidence.
- `frontend/src/components/trip/ItineraryMap.vue`, `frontend/src/utils/itineraryMap.ts`: road geometry plus candidate fallback.
- `frontend/src/views/Result.vue`: locality, decision, partial status, and travel-leg presentation.

## Review Focus

- A non-Latin destination that Qloo resolves to several fuzzy localities must use the top deterministic locality result and never silently run global discovery; covered in Task 1.
- Qloo candidates whose coordinates are `0` must remain valid while `None` coordinates are rejected; covered in Task 1.
- A policy timeout or invalid action must not stall or escape the allowed action set; covered in Task 3.
- A plan with dates present but zero total stops must repair once, then become partial rather than completed; covered in Task 4.
- OSRM returning `null` matrix cells, no route, or a timeout must preserve Qloo evidence and never invent travel facts; covered in Task 5.

---

### Task 1: Resolve locality and report candidate validation

**Files:**
- Modify: `backend/app/services/qloo_service.py`
- Modify: `backend/app/services/candidate_validator.py`
- Modify: `backend/tests/test_qloo_service.py`
- Modify: `backend/tests/test_candidate_validator.py`
- Create: `backend/tests/fixtures/qloo/locality-search.json`

**Interfaces:**
- Produces: `QlooService.resolve_localities(query: str, *, take: int = 5) -> list[QlooEntity]`
- Changes: `QlooService.recommend_places(*, locality_id: str, entity_ids: list[str], radius_meters: int = 0, take: int = 20) -> list[PlaceCandidate]`
- Produces: `CandidateValidationReport(valid: list[PlaceCandidate], duplicate_count: int, excluded_count: int, missing_coordinates_count: int)`
- Produces: `validate_candidates(...) -> CandidateValidationReport`

- [ ] **Step 1: Write failing Qloo locality tests**

Add tests asserting that `resolve_localities("上海", take=5)` requests `/search` with `types=urn:entity:locality`, and that strict discovery sends `filter.location=<locality UUID>` plus `filter.location.radius=0` rather than `filter.location.query`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_qloo_service.py -q` from repository root.  
Expected: FAIL because `resolve_localities` and the locality-ID discovery signature do not exist.

- [ ] **Step 3: Implement the Qloo interfaces**

Use the existing bounded HTTP adapter and normalization. Keep `search_entities` unchanged for taste search; make `resolve_localities` an explicit locality wrapper.

- [ ] **Step 4: Write failing candidate-report tests**

Assert separate counts for duplicate, excluded, and missing-coordinate candidates; include longitude and latitude `0.0` as valid coordinates.

- [ ] **Step 5: Run candidate tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_candidate_validator.py -q`  
Expected: FAIL because validation returns a list without rejection metrics.

- [ ] **Step 6: Implement `CandidateValidationReport` and update existing assertions**

Keep first-usable occurrence semantics and display-tag normalization; expose rejection counts without logging here.

- [ ] **Step 7: Verify Task 1**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_qloo_service.py backend/tests/test_candidate_validator.py -q`  
Expected: PASS.

- [ ] **Step 8: Commit**

Commit: `fix: constrain Qloo discovery to resolved localities`

### Task 2: Fix category selector and map fallback

**Files:**
- Modify: `frontend/src/components/taste/TasteEntitySearch.vue`
- Modify: `frontend/src/components/taste/TasteEntitySearch.test.ts`
- Modify: `frontend/src/utils/itineraryMap.ts`
- Modify: `frontend/src/utils/itineraryMap.test.ts`

**Interfaces:**
- Produces: dropdown option label `Music` with value `artist`.
- Changes: `buildItineraryMapModel(plan)` falls back to mappable candidates when itinerary marker construction yields zero markers.

- [ ] **Step 1: Write failing selector tests**

Assert that the category select has a stable `category-select` class, contains `Music` with value `artist`, does not contain the old `Artist` label, and the search call receives `artist` after Music is selected. Assert the component style contract includes an intrinsic category minimum of at least `11.5rem`.

- [ ] **Step 2: Run selector test and verify RED**

Run from `frontend`: `.\node_modules\.bin\vitest.cmd run src/components/taste/TasteEntitySearch.test.ts`.  
Expected: FAIL for missing Music label/class/width behavior.

- [ ] **Step 3: Implement the selector fix**

Use `minmax(0, 1fr)` for search and `minmax(11.5rem, max-content)` for category, reserve native arrow padding, retain the existing single-column mobile breakpoint, and map Music to `artist`.

- [ ] **Step 4: Write the failing empty-day map fallback test**

Given non-empty `days` whose `items` are empty or unmappable and candidates with coordinates, assert candidate markers and no routes.

- [ ] **Step 5: Run map test and verify RED**

Run from `frontend`: `.\node_modules\.bin\vitest.cmd run src/utils/itineraryMap.test.ts`.  
Expected: FAIL with zero markers.

- [ ] **Step 6: Implement marker-first fallback**

Build itinerary markers first; when the result is empty, call one candidate-marker helper used by both empty-day and unmappable-day cases.

- [ ] **Step 7: Verify Task 2**

Run from `frontend`: `.\node_modules\.bin\vitest.cmd run src/components/taste/TasteEntitySearch.test.ts src/utils/itineraryMap.test.ts`.  
Expected: PASS.

- [ ] **Step 8: Commit**

Commit: `fix: keep category labels and fallback map visible`

### Task 3: Add agent decision contracts and bounded policy

**Files:**
- Create: `backend/app/models/planning.py`
- Create: `backend/app/agents/planning_policy.py`
- Create: `backend/tests/test_planning_policy.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/tests/test_itinerary_composer.py`

**Interfaces:**
- Produces: `PlanningAction` enum with the eight actions defined in the spec.
- Produces: `PlanningObservation`, `PlanningDecision`, and `PlanningState`.
- Produces: `PlanningPolicy.choose(observation: PlanningObservation, allowed_actions: tuple[PlanningAction, ...]) -> PlanningDecision`.
- Produces: public `AgentDecision(iteration, action, status, reason, metrics)` and `ResolvedLocality(id, name)`.
- Changes: `TasteRoutePlan` gains `completion_status`, `locality`, `decisions`, and `routes`; `AgentDecision` is both stored evidence and the unit streamed to the browser while an action runs/completes.

- [ ] **Step 1: Write failing policy tests**

Assert successful structured selection, rejection of an action outside `allowed_actions`, safe reason truncation, and propagation of model timeout as `PlanningPolicyError` without prompt contents.

- [ ] **Step 2: Run policy tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_planning_policy.py -q`  
Expected: FAIL because policy contracts do not exist.

- [ ] **Step 3: Implement planning models and `LangChainPlanningPolicy`**

Use one structured-output model with an enum action and a 240-character reason. Pass only observation metrics and allowed action values.

- [ ] **Step 4: Add public contract serialization tests**

Extend schema/composer tests to assert `completion_status`, locality, decisions, and empty routes serialize consistently and do not alter candidate provenance.

- [ ] **Step 5: Run focused backend tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_planning_policy.py backend/tests/test_itinerary_composer.py -q`  
Expected: PASS.

- [ ] **Step 6: Commit**

Commit: `feat: define bounded planning decisions`

### Task 4: Implement the bounded controller, non-empty validity, and safe logs

**Files:**
- Create: `backend/app/services/planning_log.py`
- Create: `backend/tests/test_planning_log.py`
- Modify: `backend/app/agents/taste_route_orchestrator.py`
- Modify: `backend/app/services/candidate_validator.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/routes/trip.py`
- Modify: `backend/tests/test_taste_route_orchestrator.py`
- Modify: `backend/tests/test_taste_routes.py`
- Modify: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `allowed_actions(state: PlanningState) -> tuple[PlanningAction, ...]`.
- Produces: `select_action(state, policy) -> PlanningDecision` with deterministic fallback.
- Produces: `validate_itinerary(request, candidates, days, route_lookup=None) -> list[ItineraryDay]` that removes empty days and rejects zero total stops.
- Produces: `log_planning_event(event: str, **safe_fields: object) -> None`.
- Changes: `TasteRouteOrchestrator(..., policy, max_decisions=8, nearby_radius_meters=10000)`.
- Changes: the progress callback receives `AgentDecision` records; `/plan/stream` emits them as `type=progress` records and replays stored decisions for cache hits.

- [ ] **Step 1: Rewrite orchestrator fakes around locality and policy, then add failing loop tests**

Cover the Shanghai locality ID path, strict discovery before nearby retry, policy choice from multiple actions, invalid-action fallback, policy timeout fallback, bounded termination, and one decision record per executed action.

- [ ] **Step 2: Add failing validity tests**

Assert empty days are removed; zero total stops raises validation; first empty composition triggers one repair; a second empty composition returns `completion_status=partial`, preserves Qloo candidates, and never emits completed composition.

- [ ] **Step 3: Run orchestrator tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_taste_route_orchestrator.py -q`  
Expected: FAIL because the controller and zero-stop guard do not exist.

- [ ] **Step 4: Implement the controller and validator**

Assign request ID at plan start. Invoke the policy only when more than one valid next action exists; otherwise select deterministically. Stop at the configured decision limit and return an explicit partial/failed status.

- [ ] **Step 5: Write failing safe-log tests**

Using `caplog`, parse each message as JSON and assert request ID, stage counts, action, reason code, status, and duration fields. Assert sentinel API keys, raw prompts, and free-text constraints never appear.

- [ ] **Step 6: Implement `planning_log.py` and controller events**

Serialize only an allowlisted field dictionary as one-line JSON at INFO; log safe exception class/code instead of exception text.

- [ ] **Step 7: Wire configuration and dependencies**

Add `agent_max_decisions` and `qloo_nearby_radius_meters`; construct policy and orchestrator from the existing provider-neutral LLM.

- [ ] **Step 8: Update and verify streaming contract tests**

Assert live and cached NDJSON responses emit the same ordered decision records before the result and never expose an internal policy exception.

- [ ] **Step 9: Verify Task 4**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_taste_route_orchestrator.py backend/tests/test_taste_routes.py backend/tests/test_planning_log.py backend/tests/test_config.py -q`  
Expected: PASS.

- [ ] **Step 10: Commit**

Commit: `feat: run a bounded planning decision loop`

### Task 5: Add degradable OSRM routing

**Files:**
- Create: `backend/app/services/routing_service.py`
- Create: `backend/tests/test_routing_service.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `TravelEstimate(from_place_id, to_place_id, distance_meters, duration_minutes)`.
- Produces: `TravelMatrix(place_ids, durations_seconds, distances_meters)`.
- Produces: `TravelLeg(from_place_id, to_place_id, distance_meters, duration_minutes)`.
- Produces: `ItineraryRoute(date, profile='driving', geometry, legs, distance_meters, duration_minutes)`.
- Produces: `RoutingPort.build_matrix(candidates) -> TravelMatrix` and `RoutingPort.route_day(day, candidate_by_id) -> ItineraryRoute`.
- Produces: `OSRMRoutingService(base_url, timeout_seconds, transport=None)`.

- [ ] **Step 1: Write failing matrix and route adapter tests**

Assert exact OSRM table/route URLs, longitude-before-latitude order, GeoJSON geometry normalization, leg totals, `driving` profile, and bounded timeout.

- [ ] **Step 2: Write failing degradation tests**

Assert `null` matrix cells stay unknown, an empty route raises `RoutingServiceError`, 429/5xx and network timeouts return safe retryable classifications, and no fabricated distance appears.

- [ ] **Step 3: Run routing tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_routing_service.py -q`  
Expected: FAIL because the routing adapter does not exist.

- [ ] **Step 4: Implement routing models and adapter**

Use existing HTTPX, URL-encode coordinate lists, request `annotations=duration,distance` for tables and `overview=full&geometries=geojson&steps=false` for routes.

- [ ] **Step 5: Wire routing config**

Add `routing_base_url` defaulting to `https://router.project-osrm.org`, `routing_timeout_seconds=10`, and a `get_routing_service()` dependency.

- [ ] **Step 6: Verify Task 5**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_routing_service.py backend/tests/test_config.py -q`  
Expected: PASS.

- [ ] **Step 7: Commit**

Commit: `feat: add optional OSRM route evidence`

### Task 6: Integrate routing into composition and schedule critique

**Files:**
- Modify: `backend/app/agents/itinerary_composer.py`
- Modify: `backend/app/agents/taste_route_orchestrator.py`
- Modify: `backend/app/services/candidate_validator.py`
- Modify: `backend/tests/test_itinerary_composer.py`
- Modify: `backend/tests/test_taste_route_orchestrator.py`

**Interfaces:**
- Changes: `ItineraryComposer.compose(request, candidates, travel_matrix=None, correction=None)`.
- Produces: `validate_schedule(days, route_by_date) -> None`.
- Consumes: Task 5 `RoutingPort`, `TravelMatrix`, and `ItineraryRoute`.

- [ ] **Step 1: Write failing composer evidence tests**

Assert the compact matrix is included as factual travel evidence, profile is labeled driving, unknown cells are omitted, and prompts forbid presenting driving time as walking/transit time.

- [ ] **Step 2: Run composer tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_itinerary_composer.py -q`  
Expected: FAIL because the composer does not accept travel evidence.

- [ ] **Step 3: Implement matrix-aware composition**

Serialize matrix rows compactly by candidate ID and integer minutes; preserve the existing correction and structured-output boundaries.

- [ ] **Step 4: Write failing controller routing tests**

Cover matrix success before composition, per-day routing after composition, route geometry in the plan, insufficient time between adjacent stops triggering one repair, route recomputation after repair, and routing failure producing a warning plus geometric fallback without losing the itinerary.

- [ ] **Step 5: Run controller routing tests and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_taste_route_orchestrator.py -q`  
Expected: FAIL because routing and schedule critique are not integrated.

- [ ] **Step 6: Implement routing actions and schedule validation**

Route only days with at least two stops. Compare each next `start_time` with previous start plus visit duration plus known leg duration. Unknown travel times do not create violations.

- [ ] **Step 7: Verify Task 6**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_itinerary_composer.py backend/tests/test_taste_route_orchestrator.py -q`  
Expected: PASS.

- [ ] **Step 8: Commit**

Commit: `feat: critique itineraries with route evidence`

### Task 7: Present agent decisions, Qloo scores, and real routes

**Files:**
- Modify: `frontend/src/types/taste.ts`
- Modify: `frontend/src/utils/tasteRoute.ts`
- Modify: `frontend/src/utils/tasteRoute.test.ts`
- Modify: `frontend/src/utils/itineraryMap.ts`
- Modify: `frontend/src/utils/itineraryMap.test.ts`
- Modify: `frontend/src/services/tripStream.ts`
- Modify: `frontend/src/services/tripStream.test.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/components/trip/GenerationProgress.vue`
- Modify: `frontend/src/components/trip/GenerationProgress.test.ts`
- Modify: `frontend/src/components/trip/TasteExplanation.vue`
- Modify: `frontend/src/components/trip/TasteExplanation.test.ts`
- Modify: `frontend/src/components/trip/ItineraryMap.vue`
- Modify: `frontend/src/components/trip/ItineraryMap.test.ts`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/Result.vue`
- Modify: `frontend/src/views/Result.test.ts`

**Interfaces:**
- Consumes: public contracts from Tasks 3 and 5.
- Changes: `ItineraryMapRoute` accepts backend route geometry and `profile`.
- Produces: `legFor(date: string, toPlaceId: string) -> TravelLeg | null` in the result view.

- [ ] **Step 1: Write failing response-parser tests**

Assert valid completed/partial plans with locality, decisions, routes, and legs parse; invalid action/status/geometry/leg data is rejected.

- [ ] **Step 2: Update TypeScript contracts and parser**

Mirror backend enum literals exactly and retain strict nested validation.

- [ ] **Step 3: Write failing progress and decision-trace tests**

Assert the NDJSON parser forwards `AgentDecision` progress records; dynamic action labels are shown in arrival order with reasons, retries are not collapsed, and statuses remain accessible through `aria-live`.

- [ ] **Step 4: Implement dynamic progress and result trace**

Replace the fixed three-row generation list with event-driven decision rows while retaining elapsed time and reduced-motion behavior. Show resolved locality and completion status in the result overview.

- [ ] **Step 5: Write failing contribution-score tests**

Assert contributions sort by descending available score, show at most two named signals, format scores as percentages, and retain the no-signal message.

- [ ] **Step 6: Implement scored Qloo evidence**

Never infer a score or name; render only values present in the candidate.

- [ ] **Step 7: Write failing route/map/leg tests**

Assert backend GeoJSON route geometry replaces straight coordinates when present, driving attribution is visible, each transition displays distance/time, and routing absence retains geometric lines with a warning.

- [ ] **Step 8: Implement real route and travel-leg presentation**

Use existing per-day colors and marker/card linkage. Format distance in km above 1000m, otherwise meters; round duration to whole minutes.

- [ ] **Step 9: Verify Task 7**

Run from `frontend`: `.\node_modules\.bin\vitest.cmd run`, then `.\node_modules\.bin\vue-tsc.cmd`.  
Expected: all tests and type checking PASS.

- [ ] **Step 10: Commit**

Commit: `feat: explain agent choices and travel routes`

### Task 8: Documentation, complete verification, and production replay

**Files:**
- Modify: `README.md`
- Modify: `docs/project-introduction.md`
- Modify: `docs/deployment.md`
- Modify: `docs/live-validation.md`
- Modify: `frontend/.env.example` only if a frontend variable is introduced (none expected).

**Interfaces:**
- Documents all public environment variables and degradation semantics.

- [ ] **Step 1: Update documentation**

Document the bounded action loop, locality resolution, decision trace, safe logs, OSRM driving evidence, routing fallback, Music category, and the difference between completed and partial plans.

- [ ] **Step 2: Run complete backend quality gate**

Run from `backend`: `.\.venv\Scripts\python.exe -m compileall app`, `.\.venv\Scripts\python.exe -m pytest tests -q`, and `.\.venv\Scripts\python.exe -m pip check`.  
Expected: syntax succeeds, all tests pass, no broken requirements.

- [ ] **Step 3: Run complete frontend quality gate**

Run from `frontend`: `.\node_modules\.bin\vitest.cmd run`, `.\node_modules\.bin\vue-tsc.cmd`, and `.\node_modules\.bin\vite.cmd build`.  
Expected: all tests, type checking, and production build pass.

- [ ] **Step 4: Run repository checks**

Run: `git diff --check` and inspect `git status --short`.  
Expected: no whitespace errors and only intended files changed.

- [ ] **Step 5: Commit documentation**

Commit: `docs: document bounded agent planning`

- [ ] **Step 6: Push `main` and wait for CI/CD**

Push only after all local checks pass. Confirm Backend, Frontend, Container, and Deploy Render jobs succeed for the tested commit.

- [ ] **Step 7: Replay the production incident**

On the deployed service, search `简爱`, select the first two movie results, use destination `上海` and dates 2026-10-29 through 2026-10-31. Assert the resolved locality is Shanghai, every candidate is geographically local, the completed result has at least one stop, the map has a basemap and markers, and Render logs show correlated safe stage/decision counts.

- [ ] **Step 8: Record validation evidence**

Add the redacted replay outcome and deployed commit to `docs/live-validation.md`; if this changes the file after Step 5, make a final `docs: record agent loop production validation` commit and repeat the documentation-only CI check.

