# Railway deployment

TasteRoute ships as one Docker image: Vite builds the Vue app, then FastAPI serves both the API and the generated frontend. This keeps the demo same-origin and avoids a second service, duplicated CORS configuration, and cross-service cold starts.

## Deploy

1. Create a Railway service from this GitHub repository.
2. Railway detects `railway.json` and builds the root `Dockerfile`.
3. Add the required secrets from `backend/.env.example`: `QLOO_API_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
4. Set `CORS_ORIGINS` to the final `https://…up.railway.app` domain. Do not set `VITE_API_BASE_URL` for the same-origin production image.
5. For a polished public demo, set `VITE_MAP_STYLE_URL` before the Docker build to a production MapLibre-compatible style. The default public demo style is suitable only for evaluation and local development.
6. Generate a Railway domain and wait for `/health` to report `{"status":"ok"}`.
7. Run `scripts/smoke-test.ps1 -BaseUrl https://your-domain` and complete one real itinerary in an incognito browser.

The rate limiter and caches are process-local. Keep the demo at one replica unless these controls are moved to Redis. Railway's `PORT` is consumed automatically by the container command.

## Rollback and diagnosis

- A failed `/health` means the container did not start or the service is not reachable.
- Startup rejects missing Qloo or LLM configuration before serving traffic.
- Qloo errors are classified without leaking upstream credentials or response bodies.
- An unavailable composer returns Qloo discoveries as an explicit partial result.
- Roll back to the previous successful Railway deployment if live generation regresses.
