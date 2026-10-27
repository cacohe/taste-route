# Live validation

Live validation is pending until the repository owner configures real Qloo and LLM credentials. Do not commit `.env`.

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
| Pending | Local | Real Qloo + LLM end-to-end | Not yet run |
