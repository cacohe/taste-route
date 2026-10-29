# Live validation

Live validation records real-provider checks without storing credentials or raw provider payloads. Never commit `.env`.

## Procedure

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `QLOO_API_KEY` and the chosen LLM credentials.
3. Start backend and frontend using the README commands.
4. Search at least one entity in each relevant category (film, music, book, place).
5. Generate routes for at least two countries and verify returned coordinates visually in MapLibre.
6. Confirm every itinerary `place_id` exists in `data.candidates`.
7. Inspect the browser network log and confirm no Qloo credential appears.
8. Exercise an invalid Qloo key in a temporary local session and confirm the browser receives only `QLOO_AUTH_FAILED`.
9. Record tested date, destinations, selected seeds, and redacted response observations below.
10. Confirm `locality`, `decisions`, `completion_status`, and `routes` are present; a completed result must have at least one stop.
11. Confirm Render logs can correlate locality, candidate, composition, and routing counts by request ID without showing prompts or secrets.

The production regression scenario is destination `上海`, dates 2026-10-29 through 2026-10-31, search `简爱`, and the first two film results. Expected behavior: Qloo resolves a Shanghai locality ID, strict discovery stays local, the result is never an empty completed plan, and the map shows candidates or itinerary markers even if composition degrades.

## Validation record

| Date | Environment | Scenario | Result |
| --- | --- | --- | --- |
| 2026-10-28 | Local | Qloo search: movie, artist, book, place | Passed; three results returned for each tested category |
| 2026-10-28 | Local | Qloo Insights: Paris, France and Tokyo, Japan | Passed; 20/20 candidates had coordinates in each destination |
| 2026-10-28 | Local browser | Vite proxy + partial result + MapLibre | Passed; 20 Paris markers rendered without exposing the Qloo key |
| 2026-10-28 | Temporary invalid Qloo key | Public error contract | Passed; HTTP 502 contained only `QLOO_AUTH_FAILED`, a public message, and `retryable: false` |
| 2026-10-28 | Local | Provider-neutral LLM itinerary composition | Passed with `deepseek-flash`; Paris produced 2 days/10 items and Tokyo produced 2 days/9 items |
| 2026-10-28 | Local browser | Complete itinerary + evidence + MapLibre | Passed; Paris rendered two itinerary days, per-stop Qloo evidence, and 20 map markers |
| 2026-10-28 | Production-shaped local server | FastAPI-served Vue + live Paris regression | Passed; health, homepage, OpenAPI, Qloo search, and plan returned 20 candidates, 2 days, 13 items, and three completed workflow stages |
| 2026-10-29 | Render production (`f3b9f18`) | 上海, 2026-10-29–31, first two 简爱 film results | Passed; Qloo resolved 上海市 (`3FBE…3C35`), strict discovery returned 20/20 mappable local candidates, bounded actions were resolve → strict discover → compose → route → finish, and the completed plan contained 3 days, 13 stops, 3 driving routes, and no warnings |

## 2026-10-28 observations

- Live `/search` returns `results` as an array and exposes entity types through a `types` array. The adapter now supports this shape as well as the documented fixture shape.
- Live Insights places expose coordinates under top-level `location.lat` / `location.lon`; the adapter now preserves those coordinates.
- Both tested destinations returned only candidate IDs supplied by Qloo. Every generated date stayed inside the requested range and every itinerary item included a non-empty evidence-grounded reason.
- The configured endpoint does not support OpenAI's `json_schema` response format. The composer uses the more broadly compatible `json_mode` and supplies the authoritative Pydantic output schema in the prompt before validating the response.
- No credential value was printed, recorded, committed, or returned to the browser.
