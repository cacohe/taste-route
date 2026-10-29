# TasteRoute Agentic Planning Loop Design

**Date:** 2026-10-29  
**Status:** Proposed for implementation  
**Selected approach:** Bounded hybrid decision loop

## Intent

Make TasteRoute reliably produce a useful, geographically valid itinerary while making the agent's decisions visible and keeping Qloo as the source of truth. This design also fixes the production incident in which the input `上海`, 2026-10-29 through 2026-10-31, and the first two `Jane Eyre` movie results produced an empty itinerary and a blank map.

The production replay established the full failure chain:

1. `filter.location.query=上海` returned one place in Serbia rather than a place in Shanghai.
2. The composer returned three requested dates with empty `items` arrays.
3. Empty itinerary days passed validation and were reported as a successful plan.
4. The map fallback only ran when `days` itself was empty, so non-empty days with zero stops hid the remaining candidate and produced `Qloo returned no mappable coordinates.`

A second live Qloo check confirmed that searching `上海` as `urn:entity:locality` resolves `上海市` (`3FBE70C0-D22F-4E01-8A5C-98DFADF53C35`). Passing that locality ID through `filter.location` with `filter.location.radius=0` returns places in Shanghai.

## Goals

- Resolve a destination into a Qloo locality before place discovery.
- Enforce the resolved locality strictly for the first discovery attempt.
- Replace the fixed happy-path pipeline with a bounded observe/decide/act/validate/critique loop.
- Let an LLM decision policy select only from actions explicitly allowed by deterministic guards.
- Never report an itinerary with zero total stops as a successful completed plan.
- Add safe structured logs that make production failures diagnosable without logging credentials, prompts, or user constraints.
- Use routing information to improve ordering and schedule feasibility without making the public routing service a hard dependency.
- Expose Qloo contribution scores and actual agent decisions in the result experience.
- Fix the category selector width and expose the existing Qloo `artist` type to users as `Music`.
- Preserve Qloo provenance: every itinerary stop must reference a validated Qloo candidate.

## Non-goals

- Turn-by-turn navigation instructions.
- Booking, reservations, live inventory, or opening-hours guarantees.
- Unbounded autonomous tool use.
- Allowing the LLM to invent Qloo parameters, place IDs, coordinates, or routing facts.
- Persisting personal profiles or complete planning requests in logs.
- Treating the public OSRM endpoint as a production SLA. The adapter remains configurable and degradable.

## Approaches considered

### Rules-only controller

A deterministic state machine could resolve the locality, retry discovery, validate the plan, and route it. This is the most predictable option, but the decision trace would still represent a sophisticated pipeline rather than an agent choosing among meaningful actions.

### Unrestricted LLM tool-calling agent

An LLM could call Qloo, locality search, routing, and composition tools freely. This presents the strongest agent aesthetic but increases latency, cost, nondeterminism, and the risk of unsupported Qloo parameters or repeated calls on a shared hackathon key.

### Bounded hybrid loop — selected

Deterministic evaluators own safety and produce the valid next-action set. A structured LLM policy chooses among those actions and supplies a short user-safe rationale. The controller executes the chosen action, records the observation, and repeats until it can finish or reaches a strict decision budget.

This option provides real decision-making while retaining reproducibility, testability, bounded cost, provenance, and graceful degradation.

## Agent state and actions

The controller owns a `PlanningState` with:

- request ID and sanitized request summary;
- resolved locality ID and display name;
- seed IDs and names;
- discovery attempt and locality policy;
- raw, rejected, and validated candidate counts;
- composed days and total stop count;
- routing matrix availability and route result;
- warnings, decisions, and remaining decision budget.

The action enum is intentionally closed:

1. `resolve_locality`
2. `discover_strict`
3. `discover_nearby`
4. `compose_itinerary`
5. `repair_itinerary`
6. `build_routes`
7. `finish`
8. `fail`

The deterministic evaluator computes allowed actions after every observation. Examples:

- No locality allows only `resolve_locality` or `fail`.
- A resolved locality with no discovery allows `discover_strict`.
- Too few valid strict candidates allows `discover_nearby` or `fail`.
- Valid candidates with no plan allows `compose_itinerary`.
- An empty, invalid, geographically infeasible, or provenance-invalid plan allows one bounded `repair_itinerary` attempt.
- A valid plan allows `build_routes` or `finish` when routing is unavailable.
- `finish` is forbidden unless at least one itinerary stop exists and every stop passes provenance and date validation.

The decision policy receives only a compact observation, the allowed action enum values, and sanitized metrics. Its structured response contains `action` and a short `reason`. The controller rejects any action not in the allowed set and applies a deterministic default. The complete loop has a small fixed maximum decision count; exceeding it fails safely with a public error rather than returning empty success.

## Destination and Qloo discovery

The Qloo adapter gains explicit operations rather than overloading a destination string:

- `resolve_localities(query, take)` searches `urn:entity:locality`.
- `recommend_places(locality_id, entity_ids, radius_meters, take)` passes the locality ID through `filter.location`.

The first attempt uses `filter.location.radius=0`. A bounded nearby retry may use a documented, configured radius only when strict discovery returns too few usable candidates. Returned candidates retain Qloo coordinates, affinity, tags, and explainability.

Locality resolution selects the best Qloo result deterministically. Exact normalized names win; otherwise Qloo rank is retained. The selected locality name and ID become part of the plan evidence and diagnostic trace.

Candidate validation will report counts by rejection reason rather than returning only a list. Coordinates remain required. Duplicates, explicit exclusions, and missing coordinates are counted separately for logs and decisions.

## Itinerary validity

A completed itinerary must satisfy all of these conditions:

- at least one day contains at least one stop;
- every stop references a validated Qloo candidate;
- every day lies inside the requested range;
- dates are unique and sorted;
- stops within a day have strictly increasing start times;
- the scheduled gap between adjacent stops is sufficient for the previous visit and known travel time;
- the plan does not exceed the bounded repair count.

Empty days may be removed before final validation. If every day becomes empty, composition is invalid and triggers repair. A second empty result fails explicitly; it is not returned as successful completion.

Partial discovery evidence may still be returned when composition or routing is unavailable, but the response and workflow trace must label the result as partial rather than completed.

## Routing feasibility

Introduce a provider-neutral routing port with an OSRM adapter. The adapter uses a configurable base URL and bounded timeout.

The first implementation uses OSRM's driving profile and labels it explicitly; it must not present driving time as walking or public-transit time. Other modes remain future adapter work.

Before composition, a table request supplies approximate driving durations between validated candidates. The composer receives those durations as evidence and is instructed to prefer geographically coherent days. After composition, a route request per day returns:

- ordered road geometry;
- total distance;
- total duration;
- individual leg distance and duration.

The schedule validator uses leg durations when available. The map renders road geometry instead of straight point-to-point lines. Each transition in the itinerary displays travel time and distance.

Routing is degradable. If OSRM is unavailable, composition continues with Qloo coordinates, the map uses geometric lines, and a warning states that travel-time validation was unavailable. Routing failure never permits invented distances.

## Explainability and visible decisions

The public plan adds:

- resolved locality evidence;
- an explicit `completion_status` of `completed`, `partial`, or `failed`;
- structured decision trace entries with iteration, action, status, reason, and small numeric metrics;
- route summaries and legs;
- the existing Qloo contributions with names and scores.

The result page shows:

- the locality Qloo resolved;
- each agent action and its observed outcome;
- the strongest one or two Qloo contribution signals per stop, including scores when provided;
- real route distance and travel time when available;
- a clear partial-result state when composition or routing degrades.

No internal prompt, raw upstream payload, credential, or stack trace appears in the UI.

## Structured logging

All planning logs are one-line JSON records associated with a request ID. Events include:

- `plan.started`
- `locality.resolved` or `locality.failed`
- `qloo.discovery.completed`
- `candidates.validated`
- `agent.decision`
- `composition.completed` or `composition.failed`
- `routing.completed` or `routing.degraded`
- `plan.completed`, `plan.partial`, or `plan.failed`

Allowed fields include request ID, locality name/ID, seed count and types, attempt number, raw/valid/rejected counts, total stop count, route distance/duration, stage duration, action, reason code, and safe error class.

Logs must not include API keys, authorization headers, raw prompts, complete upstream payloads, full free-text constraints, or exception representations that may embed request data.

## Frontend category fixes

The search row will use a flexible search column and a category column with enough intrinsic minimum width for `All categories`, including native arrow and padding. The existing single-column mobile breakpoint remains.

Qloo's `urn:entity:artist` is a music-artist type. The dropdown label changes from `Artist` to `Music`; the API value remains `artist`. A duplicate `Music` and `Artist` option will not be created.

## Map fallback correction

The map model first attempts to build itinerary markers. If that produces zero markers—whether `days` is empty, all days are empty, IDs are missing, or coordinates are absent—it falls back to every mappable validated candidate. The map message distinguishes candidate evidence from a completed route.

## Failure behavior

- Locality cannot resolve: fail with an actionable destination message; do not run global discovery.
- Qloo returns no usable local candidates after bounded attempts: return a partial/failure response with the resolved locality and decision trace.
- LLM returns an empty or invalid plan twice: preserve Qloo candidates as partial evidence and label composition failed.
- Routing fails: keep the itinerary, geometric map lines, and a routing warning.
- Decision budget exhausted: fail safely with a stable public error code.

## Testing strategy

Every behavior change follows red/green TDD.

Backend coverage includes:

- Chinese `上海` locality resolution and use of locality ID with radius zero;
- candidate rejection counts;
- decision actions restricted to the allowed set;
- deterministic fallback when the policy returns an invalid action;
- bounded loop termination;
- empty-day and zero-stop rejection;
- repair success and second-failure partial response;
- routing matrix/route success and routing degradation;
- schedule feasibility validation;
- structured logs contain required fields and exclude secrets/free text;
- contribution score and locality serialization.

Frontend coverage includes:

- `All categories` minimum width behavior through a stable class/style contract;
- `Music` maps to `artist`;
- decision trace detail rendering;
- contribution scores;
- real route geometry and route-leg labels;
- candidate map fallback when days exist but contain no mappable stops.

The final quality gate runs backend tests, frontend tests, type checking, production build, Docker build in CI, production smoke checks, and a live replay of the original Shanghai/Jane Eyre incident.

## Acceptance criteria

1. Replaying Shanghai, 2026-10-29 through 2026-10-31, with the first two Jane Eyre movies never returns Serbia or another locality.
2. A response cannot be marked completed with zero total itinerary stops.
3. If composition fails, validated Qloo candidates remain visible on the map with an explicit partial-result message.
4. Agent decisions are observable, bounded, and backed by actual tool results.
5. Every final stop retains Qloo provenance and shows its strongest available Qloo contribution.
6. Routes use real road geometry and travel times when OSRM succeeds; failure degrades without losing the itinerary.
7. Render logs can identify the failure stage and counts for one request ID without exposing secrets.
8. `All categories` is fully visible at desktop/tablet widths, and `Music` searches Qloo `artist` entities.

