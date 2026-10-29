# Render and Railway deployment

TasteRoute ships as one Docker image: Vite builds the Vue app, then FastAPI serves both the API and generated frontend. This keeps the demo same-origin and avoids a second service, duplicated CORS configuration, and cross-service cold starts. Render is the current CD target; `railway.json` is retained as a supported alternative and Railway CD can be added later.

## Render: initial setup

1. In Render, create a Blueprint from the public GitHub repository. Render reads the root `render.yaml`, links `main`, builds the root `Dockerfile`, and checks `GET /health`.
2. During Blueprint creation, provide `QLOO_API_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. They are declared with `sync: false` and must never be committed. Optional planning controls are `AGENT_MAX_DECISIONS`, `QLOO_NEARBY_RADIUS_METERS`, `ROUTING_BASE_URL`, and `ROUTING_TIMEOUT_SECONDS`.
3. No map credential is required: the production build defaults to the OpenFreeMap Liberty global street style. Optionally add `VITE_MAP_STYLE_URL` to select another MapLibre-compatible style; Render supplies that non-secret value to the Vite build through the matching Docker build argument.
4. Keep one instance. Rate limits, concurrency guards, and caches are process-local.
5. In the Render service's **Settings**, copy its secret Deploy Hook URL into the GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`.
6. Store the public `https://…onrender.com` service URL in the GitHub Actions repository variable `RENDER_SERVICE_URL`.

`render.yaml` sets `autoDeployTrigger: off`, so Render does not race ahead of CI. On every push to `main`, GitHub Actions runs backend tests, frontend tests/build, and a production Docker build. Only after all three succeed does `Deploy Render` call the hook with `ref=<tested commit SHA>`. The job then polls `/health` until Render reports that exact commit, and automatically verifies the homepage and OpenAPI document. Pull requests never deploy, and missing deployment configuration fails CD instead of producing a false green result.

The Blueprint currently uses Render's free plan. That is suitable for development but can show a 25–35 second cold-start interstitial after inactivity. Move the judging service to a non-sleeping Render plan before submitting the public demo; do not rely on synthetic keep-alive traffic.

## Railway: supported manual deployment

1. Create a Railway service from this GitHub repository and select `main`.
2. Railway detects `railway.json` and builds the root `Dockerfile`.
3. Add `QLOO_API_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` from `backend/.env.example` as service variables.
4. Optionally add `VITE_MAP_STYLE_URL` to override the default OpenFreeMap Liberty style; Railway exposes declared service variables to the Docker build through the matching Dockerfile `ARG`.
5. Generate a Railway domain. No `VITE_API_BASE_URL` is needed because production is same-origin.

Railway is deployable now, but `.github/workflows/ci.yml` intentionally contains no Railway deployment job. Add one only after choosing Railway as an active release target and storing its credentials in GitHub.

## Verify and operate

Render verification is automatic in CI/CD. A green `Deploy Render` job proves `/health` reports the tested commit and that `/` plus `/openapi.json` satisfy the production smoke contract. `scripts/smoke-test.ps1` remains available only for optional local diagnosis or Railway verification.

After deployment, complete one real itinerary in a private/incognito browser. The platform-provided `PORT` is consumed automatically by the container command.

The browser submits generation requests to `POST /api/trip/plan/stream`. The endpoint returns newline-delimited `progress`, `result`, or safe `error` records. Reverse proxies must not buffer the response if the deployment architecture changes away from the current Render Docker service.

## Rollback and diagnosis

- A failed `/health` means the container did not start or the service is not reachable.
- Startup rejects missing Qloo or LLM configuration before serving traffic.
- Qloo errors are classified without leaking upstream credentials or response bodies.
- Planning logs are one-line JSON records correlated by request ID; they include stage counts and safe error classes, never credentials, prompts, raw payloads, or user constraints.
- An unavailable composer or a second empty composition returns Qloo discoveries as an explicit `partial` result; zero stops can never be marked `completed`.
- OSRM failure retains the itinerary and switches the map to geometric lines with a visible warning.
- The Render deploy job prints the deploy ID when the hook returns one; use it to find the deployment in Render.
- Roll back to the previous successful deployment in the active platform if live generation regresses.
