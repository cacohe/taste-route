# Qloo integration

## Taste entity search

`GET /api/taste/entities?q=...&type=...` proxies a bounded request to Qloo `/search`. The backend normalizes only the ID, name, entity type, description, and image URL needed by the selector.

The frontend waits 300 ms after input and uses a monotonically increasing request version, so an older response cannot overwrite a newer query. The user-facing **Music** category maps to Qloo's `artist` entity type.

## Destination resolution

Before place discovery, `resolve_localities(destination)` searches Qloo with `types=urn:entity:locality`. An exact normalized name wins; otherwise Qloo's first-ranked result is used. If no locality resolves, TasteRoute stops instead of performing global discovery.

The selected locality ID and display name are returned as plan evidence and included in safe diagnostic logs.

## Local place discovery

Planning calls Qloo `/v2/insights` with:

- `filter.type=urn:entity:place`
- `filter.location=<resolved Qloo locality ID>`
- `filter.location.radius=0` for strict discovery
- `signal.interests.entities=<selected Qloo IDs>`
- `feature.explainability=true`
- a server-bounded `take`

If strict discovery yields no usable candidates, one bounded retry may use `QLOO_NEARBY_RADIUS_METERS` (default `10000`). TasteRoute never falls back to an unconstrained global place query.

The normalized place model retains coordinates, affinity, tags, image/address fields, and explainability contributions, including contribution scores when Qloo supplies them. Missing optional evidence remains `null` or empty and is never synthesized.

## Provenance and completion invariants

Every itinerary item contains a `place_id`. Before returning a plan, TasteRoute verifies that every ID exists in the validated Qloo candidate set. A completed plan must also contain at least one stop inside the requested dates with ordered start times.

These checks make Qloo the factual grounding layer rather than decorative enrichment. If composition fails after one repair, validated Qloo candidates remain available as an explicitly partial result.

## Security and diagnostics

- `QLOO_API_KEY` is read only by the backend.
- Upstream bodies, prompts, constraints, and credentials are never copied into public errors or planning logs.
- Structured logs record locality, attempt, raw/valid/rejected counts, and safe error classes by request ID.
- Automated tests use recorded-shaped local fixtures; live-provider evidence is recorded separately in `live-validation.md`.
