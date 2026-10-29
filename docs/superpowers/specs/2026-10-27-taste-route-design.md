# TasteRoute Design

## Intent

TasteRoute is a Qloo-powered travel agent. Users choose concrete cultural interests such as films, artists, books, brands, and places. Qloo resolves those interests and ranks destination-specific places; the application then validates the candidates and composes a practical itinerary whose recommendations remain traceable to Qloo evidence.

## Goals

- Make Qloo indispensable to the recommendation result rather than an optional enrichment.
- Let an unauthenticated judge complete a preset or custom trip end to end.
- Preserve Qloo entity IDs, affinity/explainability data, and source entities through the final response.
- Keep hard travel constraints deterministic and prevent the language model from inventing places.
- Ship TasteRoute as a self-contained project with reproducible setup and deployment instructions.

## Non-goals

- Accounts, persistence, bookings, payments, collaborative planning, and multi-city trips.
- Live navigation or production-grade route optimization.
- Supporting every Qloo entity type or every destination before submission.
- Returning synthetic plans when Qloo is unavailable.

## Constraints

- The public demo must not require a user-supplied API key or login.
- `QLOO_API_KEY` remains server-side and must never appear in logs or API responses.
- Production cannot use test fixtures as fallback data.
- Every planned place must originate from the validated Qloo candidate set.
- The initial implementation must work without a live Qloo key by using contract fixtures in tests.
- Existing Vue 3, FastAPI, Pydantic, LangChain, and pnpm/Python toolchains are retained.

## Approaches Considered

1. Add Qloo as another specialist in the existing four-agent chain. This is the smallest diff, but the model could still produce generic places and Qloo would be merely advisory.
2. Use a deterministic outer workflow with a typed Qloo client, candidate validator, and a constrained itinerary composer. This is selected because provenance is enforceable and external failures are explicit.
3. Replace the application with a new LangGraph system. This provides richer orchestration but adds migration risk without improving the judge-visible core.

## Selected Architecture

The backend owns a typed `QlooClient` and normalizes external responses into domain models. A `TasteRouteOrchestrator` resolves seeds when needed, requests taste analysis and place recommendations, validates candidates, and passes only validated candidates to an itinerary composer. The composer produces structured output; a final provenance guard rejects any place that was not in the candidate set.

The frontend adds Qloo-backed entity search, selected-interest chips, presets, Taste DNA, per-place evidence, and a map. Qloo errors are presented honestly. A missing LLM result may return ranked Qloo discoveries as a partial result, but never a fabricated successful itinerary.

## API Surface

- `GET /api/taste/entities?q=<query>&type=<optional type>` returns normalized Qloo entities.
- `POST /api/trip/plan` accepts destination, dates, pace, budget, selected Qloo entities, constraints, and excluded place IDs.
- The response includes taste profile tags, validated candidate provenance, itinerary days, warnings, and a request ID.

## Error Semantics

- Missing server configuration: `503 QLOO_NOT_CONFIGURED`.
- Invalid or expired key: `502 QLOO_AUTH_FAILED` without leaking the upstream response body.
- Rate limit: `503 QLOO_RATE_LIMITED` with a retryable flag.
- Timeout or upstream failure: `503 QLOO_UNAVAILABLE`.
- No usable candidates: a successful discovery response with no itinerary and a user-actionable warning, not dummy coordinates.

## Security and Observability

- Log request IDs, endpoint names, status codes, latency, and result counts only.
- Redact authorization headers and query text when it may contain personal free-form content.
- Bound query length, seed count, candidate count, request duration, and LLM output size.
- Store no user taste profile on the server.

## Acceptance

- Tests prove request construction, error mapping, response normalization, candidate filtering, and provenance enforcement.
- The frontend test suite proves entity selection and request construction.
- The production build succeeds without embedding Qloo secrets.
- A later opt-in live test can verify `/search` and `/v2/insights` with the event key.
