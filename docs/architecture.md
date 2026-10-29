# Architecture

TasteRoute separates Qloo-grounded discovery, bounded agent decisions, deterministic safety checks, generative composition, and optional routing evidence.

## Request flow

1. The Vue client searches `GET /api/taste/entities`; Qloo and LLM credentials never reach the browser.
2. `QlooService` resolves the destination to a Qloo locality ID and resolves any taste seeds that do not already have IDs.
3. The bounded controller computes a closed set of allowed actions. The structured LLM policy chooses only when more than one safe action is available; invalid output or timeout uses the deterministic first action.
4. Strict discovery calls Qloo Insights with the resolved locality ID and radius `0`. If it returns no usable candidates, the controller may retry once with `QLOO_NEARBY_RADIUS_METERS`.
5. Candidate validation rejects duplicates, explicit exclusions, and places without coordinates while retaining rejection counts for safe logs.
6. The composer receives only validated Qloo candidates and, when available, a compact OSRM driving matrix. It cannot introduce new place IDs.
7. Deterministic validation enforces provenance, requested dates, unique days, ordered start times, and at least one stop. One repair pass is allowed.
8. OSRM route geometry and legs validate known travel-time feasibility. Routing failures preserve the itinerary and use geometric map lines.
9. The response exposes resolved locality, `completed`/`partial`/`failed` status, Qloo evidence, ordered agent decisions, and optional driving routes. NDJSON streaming uses the same `AgentDecision` records as the final response and cache replay.

The loop is capped by `AGENT_MAX_DECISIONS` (default `8`). A plan with zero stops cannot be serialized as `completed`.

## Failure contract

- Qloo authentication or malformed upstream responses: public-safe HTTP 502.
- Qloo rejected input: HTTP 422.
- Qloo timeout, server error, or exhausted rate-limit retry: retryable HTTP 503.
- Destination cannot resolve: failed plan with no global discovery.
- No usable candidates after strict and nearby discovery: failed plan with locality and decision evidence.
- Composition remains empty or invalid after one repair: partial plan preserving validated Qloo candidates.
- Routing matrix or route unavailable: completed itinerary with an explicit warning and geometric route fallback.
- Decision budget exhausted: partial when candidates exist, otherwise failed; never an empty success.
- Per-client public-demo quota exceeded: HTTP 429.

## Operational boundaries

The app has no durable user state. Rate limits, caches, and the planning semaphore are process-local, so the hackathon deployment uses one replica. Safe one-line JSON planning logs contain request IDs, actions, counts, durations, and safe error classes; they exclude credentials, raw prompts, upstream payloads, and user constraints.

Dependency constructors live in `backend/app/api/dependencies.py`, allowing Qloo, LLM, and routing adapters to be replaced without changing route contracts.
