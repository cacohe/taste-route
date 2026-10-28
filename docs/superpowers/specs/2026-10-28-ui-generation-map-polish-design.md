# TasteRoute UI, Generation Progress, and Map Polish Design

## Intent

Make the public hackathon demo immediately understandable, visibly alive while the agent works, and trustworthy on the result page. A judge should reach the planner quickly, see real workflow progress rather than a frozen button, and understand each itinerary stop on a complete street map.

## Goals

- Fix the desktop hero layout regression caused by form-section CSS leaking into the hero.
- Reduce first-screen vertical waste while preserving TasteRoute's cream, aubergine, and violet identity.
- Stream the three real backend workflow stages to the browser and render an accessible progress panel without fake percentages.
- Replace MapLibre demo tiles with the production-quality OpenFreeMap Liberty style while retaining `VITE_MAP_STYLE_URL` as an override.
- Show itinerary stops in itinerary order, group them by day, draw per-day route lines, and link map markers with result cards.
- Surface asynchronous map failures instead of silently leaving a blue canvas.
- Remove numeric-only and malformed tags before they reach the UI.
- Add automated coverage for the new UI states, streaming protocol, map model, and tag normalization.

## Non-goals

- Turn-by-turn routing or travel-time calculation.
- Replacing MapLibre GL JS.
- Introducing a paid map account in this iteration.
- Displaying invented percentage completion.
- Redesigning the itinerary-generation prompt or Qloo ranking algorithm.

## Constraints

- Vue 3, TypeScript, FastAPI, and the existing same-origin Docker deployment remain in place.
- Only `main` is maintained.
- OpenFreeMap Liberty is the default production basemap; `VITE_MAP_STYLE_URL` may override it.
- The existing JSON planning endpoint remains available for tests and non-streaming clients; the browser uses a new POST streaming endpoint.
- Progress events must describe actual completed or active orchestration stages.
- Map-provider failure must not hide itinerary evidence.
- Respect reduced motion, keyboard focus, and screen-reader status announcements.

## Approaches

### Generation progress

1. **Timer-driven frontend stages:** smallest change, but the stages can disagree with real backend work.
2. **POST response streamed as NDJSON:** works with `fetch`, supports request bodies, and maps cleanly to the existing three-stage orchestrator. This is the selected approach.
3. **Persistent jobs plus SSE/WebSocket:** strongest for resumability, but adds storage and lifecycle complexity that the hackathon demo does not need.

### Basemap

1. **OpenFreeMap Liberty:** no account or key, full global street data, MapLibre-compatible, and deployable immediately. Selected for the current demo.
2. **MapTiler Streets:** polished and commercially supported, but requires a new account and browser-visible restricted key.
3. **Self-hosted vector tiles:** maximum control but disproportionate operational work for the event.

## Interaction Design

The hero becomes a disciplined single-column editorial block. A small route-line motif carries the travel concept; the headline remains the one bold visual moment, but its scale is capped so the planner begins near the fold. Form steps retain their numbered sequence because the content is genuinely procedural.

During generation, the submit area expands into a three-step workflow panel. One step is active, earlier steps are complete, and later steps remain pending. An indeterminate bar and elapsed-time copy communicate activity without pretending to know a percentage. Errors preserve the form and clearly invite retry.

The result map uses a complete street basemap. Only places used by the itinerary receive prominent numbered markers. Each day has a consistent color shared by its heading, route line, and markers. Selecting a card or marker highlights the counterpart. Candidate places that were not selected stay out of the primary map to reduce clutter.

## Reliability and Testing

- Orchestrator progress callbacks are optional and cannot change existing planning results.
- The streaming route emits typed `progress`, `result`, and `error` lines and never exposes credentials.
- The frontend parser tolerates chunk boundaries and rejects a stream that ends without a result.
- Map initialization listens for asynchronous MapLibre errors and has a load timeout.
- Unit/component tests cover tag cleanup, ordered map features, stream parsing, generation states, and failure messages.
- Final verification includes frontend tests/build, backend tests, container build, and browser checks at desktop and mobile widths.

## Deployment

After verification, commit and push `main` to use the existing CI-gated Render deployment. Confirm the deployed commit through `/health`, run the automated smoke path, and visually re-check the public service. Render's free-plan cold start remains an operational limitation; moving to a non-sleeping plan is recommended before judging but is not changed automatically.
