# Qloo integration

## Search

`GET /api/taste/entities?q=...&type=...` proxies a bounded request to Qloo `/search`. The backend normalizes only the ID, name, entity type, description, and image URL needed by the selector.

The frontend waits 300 ms after input and uses a monotonically increasing request version. A response for an older query cannot replace a newer result set.

## Insights

Planning calls Qloo `/v2/insights` with:

- `filter.type=urn:entity:place`
- `filter.location.query=<destination>`
- `signal.interests.entities=<selected Qloo IDs>`
- `feature.explainability=true`
- a server-bounded `take`

The normalized place model retains coordinates, affinity, tags, image/address fields, and explainability contributions. Missing optional evidence stays `null` or empty; it is never synthesized.

## Provenance invariant

Every itinerary item contains a `place_id`. Before returning a plan, TasteRoute verifies that every ID exists in the validated Qloo candidate set. This turns Qloo from decorative enrichment into the factual grounding layer for the agent.

## Security

- `QLOO_API_KEY` is read only by the backend.
- Upstream bodies and credentials are never copied into public errors.
- Tests use recorded-shaped local fixtures, not a production fallback.
