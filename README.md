# TasteRoute

TasteRoute is a taste-grounded travel agent built for the Qloo Agentic Hackathon. Instead of asking users to pick generic categories, it starts from cultural references they genuinely like—films, artists, books, brands, and places—and uses Qloo to discover relevant experiences in a destination.

> Private development repository derived from [`cacohe/trip-planner`](https://github.com/cacohe/trip-planner), with its Git history retained. The product path no longer uses the inherited Amap MCP integration.

## What works

- Debounced Qloo entity search with stale-response protection and duplicate prevention.
- Server-side Qloo Search and Insights clients with typed normalization, bounded retry, and public-safe failures.
- Deterministic filtering of duplicate, excluded, or coordinate-less places.
- Provenance enforcement: an itinerary cannot reference a place Qloo did not return.
- One bounded repair pass when the model returns invalid dates or unknown place IDs.
- Structured LangChain itinerary composition constrained to validated candidate IDs.
- Taste DNA, named Qloo contribution signals, and a visible agent workflow trace.
- Global MapLibre map using coordinates supplied by Qloo.
- Public-demo rate limits, bounded concurrency, short-lived response caches, and a same-origin Docker deployment.

## Architecture

```text
Vue taste selector
      │
      ├── GET /api/taste/entities ── Qloo Search
      │
      └── POST /api/trip/plan
              │
              ├── Qloo Insights (places + explainability)
              ├── deterministic validation
              ├── structured LangChain composer (one repair pass)
              └── provenance + date guards
                        │
                        └── Vue result + MapLibre
```

Qloo credentials are server-only. There is no fabricated production fallback: if Qloo or the composer is unavailable, the API returns a controlled error or a clearly labelled partial result.

## Stack

- Backend: Python, FastAPI, Pydantic, HTTPX, LangChain
- Frontend: Vue 3, TypeScript, Vite, MapLibre GL JS
- Tests: pytest, Vitest, Vue Test Utils

## Local setup

Requirements: Python 3.12+, Node.js 22+, pnpm, a Qloo Hackathon API key, and credentials for an OpenAI-compatible LLM endpoint.

```powershell
git clone https://github.com/cacohe/taste-route.git
cd taste-route

Copy-Item backend/.env.example backend/.env
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

In another terminal:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:5173`; backend API docs are at `http://localhost:8000/docs`.

### Required backend environment

| Variable | Purpose |
| --- | --- |
| `QLOO_API_KEY` | Qloo Hackathon API credential; never expose it as `VITE_*` |
| `QLOO_API_BASE_URL` | Defaults to `https://hackathon.api.qloo.com` |
| `LLM_API_KEY` | Key for the structured itinerary composer |
| `LLM_BASE_URL` / `LLM_MODEL` | OpenAI-compatible endpoint and model; no provider is selected by default |
| `CORS_ORIGINS` | Comma-separated frontend origins |

The frontend only needs `VITE_API_BASE_URL` when it is not served through the local Vite proxy.
`VITE_MAP_STYLE_URL` selects a production MapLibre-compatible style; local development falls back to MapLibre's public demo style.

## Production deployment

The root `Dockerfile` builds Vue and serves its static output from FastAPI. This is the recommended Railway topology because the browser and API remain same-origin. See [`docs/deployment.md`](docs/deployment.md) for exact environment variables, health checks, smoke tests, and rollback notes.

```powershell
docker build -t taste-route .
docker run --env-file backend/.env -p 8000:8000 taste-route
```

Open `http://localhost:8000`. The container health endpoint is `GET /health`.

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
pnpm test
pnpm build
```

Fixture-based integration tests do not contact Qloo or the LLM. Live-key validation is deliberately tracked separately in [`docs/live-validation.md`](docs/live-validation.md).

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — boundaries and failure behavior
- [`docs/qloo-integration.md`](docs/qloo-integration.md) — exact Qloo usage and provenance
- [`docs/live-validation.md`](docs/live-validation.md) — live API validation procedure
- [`docs/deployment.md`](docs/deployment.md) — Railway single-service deployment and rollback
- [`docs/submission-checklist.md`](docs/submission-checklist.md) — owner actions before submission

## Known limitations

- No account system or database; the generated plan is kept in browser session storage.
- Route lines and turn-by-turn navigation are not implemented; MapLibre displays Qloo coordinates.
- Demo rate limits and caches are process-local; use one application replica or introduce Redis before scaling horizontally.
- MapLibre is intentionally isolated behind the lazy result route. Its audited library chunk is about 1.1 MB minified / 300 KB gzip and is not downloaded on the planner page.

## License

[MIT](LICENSE.md)
