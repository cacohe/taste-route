# TasteRoute Hackathon Readiness Design

## Intent

Turn the working local Qloo travel agent into a publicly deployable, judge-friendly hackathon product. The shipped experience must be English-first, evidence-led, reproducible, safe to expose publicly, and deployable as one Railway service.

## Goals

- Build the Vue frontend and FastAPI backend into one container and one public origin.
- Add health checks, SPA fallback, production configuration, CI coverage, and deployment documentation.
- Make the visible product English-first and keep Qloo provenance understandable rather than overwhelming.
- Replace internal contribution IDs with selected seed names and derive Taste DNA from aggregated evidence.
- Expose a truthful workflow trace and retry one invalid LLM composition with validation feedback.
- Bound public usage with in-memory rate limits, concurrency control, TTL caches, and configurable LLM timeouts.
- Make the map style configurable and add smoke/E2E coverage appropriate for the deadline.

## Non-goals

- Accounts, a database, bookings, payments, turn-by-turn navigation, or persistent user history.
- A multi-service frontend/backend deployment for the initial submission.
- Eliminating the lazy MapLibre bundle warning.
- Replacing the deterministic orchestration with an unconstrained autonomous agent.

## Architecture

Railway builds a multi-stage Docker image: Node builds `frontend/dist`, Python installs the backend, and FastAPI serves both `/api/*` and the SPA. A `/health` route is always available. API protection is process-local because the app has one replica and no database.

Qloo remains the factual source. The orchestrator resolves seeds, retrieves candidates, validates them, asks the composer for a structured plan, retries once only when composition or deterministic plan validation fails, and returns a truthful trace. Evidence displayed to users is summarized, while the validated response retains bounded candidate data.

## Product decisions

- English is the default and only submission UI language; adding i18n is deferred.
- Up to eight high-signal tags are shown per place; the full unbounded live tag list is not sent to the browser or LLM.
- Taste DNA ranks recurring candidate tags and excludes a small explicit set of facility/generic tags.
- Contribution names are enriched from request seed IDs; unknown IDs are hidden rather than displayed.
- `VITE_MAP_STYLE_URL` is required for the production deployment and has the MapLibre demo style only as a local-development fallback.
- Public controls are configurable and return honest `429`/partial responses; no distributed guarantees are claimed.

## Approaches considered

- Separate static frontend plus API service: better CDN separation, but doubles deployment and CORS risk before the deadline.
- Vercel functions: workable but adds serverless duration and Python packaging risk for 60–90 second generation.
- One Railway container: selected for one domain, persistent FastAPI, bounded long requests, and the smallest deployment surface.

## Success criteria

- Docker image builds and serves `/`, `/result`, `/health`, and `/api/*` correctly.
- Current backend/frontend suites remain green; deployment, controls, evidence, trace, and retry behavior have regression tests.
- Live validation still produces only Qloo candidate IDs.
- README contains a demo-ready English story, deployment instructions, validation evidence, and hackathon-period changes.

