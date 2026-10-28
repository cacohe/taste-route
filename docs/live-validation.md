# Live validation

Live validation records real-provider checks without storing credentials or raw provider payloads. Never commit `.env`.

## Procedure

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `QLOO_API_KEY` and the chosen LLM credentials.
3. Start backend and frontend using the README commands.
4. Search at least one entity in each relevant category (movie, artist, book, place).
5. Generate routes for at least two countries and verify returned coordinates visually in MapLibre.
6. Confirm every itinerary `place_id` exists in `data.candidates`.
7. Inspect the browser network log and confirm no Qloo credential appears.
8. Exercise an invalid Qloo key in a temporary local session and confirm the browser receives only `QLOO_AUTH_FAILED`.
9. Record tested date, destinations, selected seeds, and redacted response observations below.

## Validation record

| Date | Environment | Scenario | Result |
| --- | --- | --- | --- |
| 2026-10-28 | Local | Qloo search: movie, artist, book, place | Passed; three results returned for each tested category |
| 2026-10-28 | Local | Qloo Insights: Paris, France and Tokyo, Japan | Passed; 20/20 candidates had coordinates in each destination |
| 2026-10-28 | Local browser | Vite proxy + partial result + MapLibre | Passed; 20 Paris markers rendered without exposing the Qloo key |
| 2026-10-28 | Temporary invalid Qloo key | Public error contract | Passed; HTTP 502 contained only `QLOO_AUTH_FAILED`, a public message, and `retryable: false` |
| 2026-10-28 | Local | MiniMax itinerary composition | Blocked; provider returned HTTP 401 / error 2049 for the configured key |

## 2026-10-28 observations

- Live `/search` returns `results` as an array and exposes entity types through a `types` array. The adapter now supports this shape as well as the documented fixture shape.
- Live Insights places expose coordinates under top-level `location.lat` / `location.lon`; the adapter now preserves those coordinates.
- Both tested destinations returned only candidate IDs supplied by Qloo. The composer could not produce itinerary days because the configured MiniMax credential was rejected before generation.
- No credential value was printed, recorded, committed, or returned to the browser.
