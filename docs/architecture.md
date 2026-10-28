# Architecture

TasteRoute separates cultural discovery, deterministic safety checks, and generative composition.

1. The Vue client searches `/api/taste/entities`; the Qloo key never reaches the browser.
2. `QlooService` calls Search for seed entities and Insights for destination places and explainability.
3. `validate_candidates` rejects duplicates, explicit exclusions, and places without coordinates.
4. Process-local rate limits, TTL caches, and a planning semaphore bound public-demo load.
5. `TasteRouteOrchestrator` gives the LLM only validated Qloo candidates.
6. Date and provenance validation can request one corrective composition pass; a second invalid result is rejected.
7. The response keeps candidate IDs, coordinates, tags, affinity, named contributions, selected seeds, and a workflow trace for UI evidence.

## Failure contract

- Qloo authentication or malformed upstream responses: HTTP 502.
- Qloo rejected input: HTTP 422.
- Timeouts, server errors, and exhausted rate-limit retry: retryable HTTP 503.
- No resolved seeds or no usable candidates: successful partial response with warnings and no invented places.
- Composer unavailable: candidates remain available, while the itinerary is empty and explicitly warned.
- Repeated invalid date or unknown generated place ID: HTTP 502; the invalid plan is never returned.
- Per-client demo quota exceeded: HTTP 429.

The app has no durable user state. Its safeguards and caches are in-process, so the recommended hackathon deployment uses one replica. Dependency constructors are isolated in `backend/app/api/dependencies.py`, so service adapters can be replaced without changing route contracts.
