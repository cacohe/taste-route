# TasteRoute — Project Introduction

## One-line pitch

TasteRoute is a taste-grounded travel agent that turns the films, artists, books, brands, and places a traveler already loves into a practical itinerary of real destinations discovered through Qloo.

## The problem

Most trip planners begin with broad filters such as “food,” “museums,” or “nightlife.” Those categories are useful, but they flatten the cultural signals that make a trip feel personal. Two travelers who both select “art and cafés” may have completely different tastes, yet receive nearly identical suggestions.

TasteRoute starts from specific cultural references. A traveler can combine signals such as a favorite film, musician, book, brand, or place. Qloo connects those signals to relevant real-world places at the destination, and a bounded planning agent organizes only those validated candidates into a usable day-by-day plan.

## What makes TasteRoute different

### Taste is the input, not a decorative filter

The selected Qloo entities are the foundation of discovery. They are not appended to a generic itinerary after generation.

### Qloo discovers; a bounded agent decides

The system deliberately separates responsibilities:

- Qloo Search resolves the traveler’s cultural references into canonical entities.
- Qloo Search first resolves the destination to a locality ID; Qloo Insights then discovers strictly local places and returns coordinates, affinity, tags, and explainability signals.
- Deterministic validation removes duplicates, exclusions, and places without usable coordinates.
- Deterministic guards expose a closed action set; a structured LLM policy chooses only among those safe actions.
- The composer receives only validated Qloo candidates plus optional OSRM driving evidence and arranges them into an itinerary.
- A provenance guard rejects every generated place ID that was not returned by Qloo.
- Empty plans, invalid dates, impossible known travel timing, and exhausted decision budgets cannot be reported as successful completion.

This boundary keeps the generative model useful without allowing it to invent attractions.

### Recommendations remain explainable

The result page preserves the evidence behind each stop:

- the selected taste seeds;
- Qloo affinity and tags;
- named contribution signals when Qloo provides them;
- the LLM’s grounded reason for including the place;
- Qloo coordinates rendered with MapLibre;
- resolved Qloo locality evidence and the actual bounded agent decisions;
- OSRM driving geometry, distance, and duration when routing succeeds.

When upstream evidence is missing, the interface says so instead of fabricating an explanation.

## Agentic workflow

```text
Traveler selects cultural references
                │
                ▼
 Qloo seed + locality resolution
                │
                ▼
 Strict local Qloo discovery
                │
                ▼
 Deterministic candidate validation
                │
                ▼
 Bounded policy chooses allowed action
                │
                ▼
 Structured itinerary composition
                │
                ▼
 Provenance + non-empty + date guards
        │                    │
        │ valid              │ invalid
        ▼                    ▼
 OSRM driving critique   One repair pass
        │                    │
        └──────────┬─────────┘
                   ▼
     completed / partial / failed
```

If the first composition is empty, references an unknown place, leaves the requested date range, duplicates a day, or conflicts with known driving time, TasteRoute supplies a safe correction for one bounded repair pass. A second invalid result becomes an explicit partial result with Qloo candidates preserved. The invalid itinerary is never returned to the traveler.

## Example user journey

1. Enter a destination and travel dates.
2. Search Qloo for specific films, music, books, brands, or places.
3. Combine one or more taste signals and choose pace, budget, and practical constraints.
4. Generate a route.
5. Explore the Taste DNA summary, day-by-day itinerary, Qloo evidence, agent workflow, and MapLibre map.

The application also supports honest partial results. If Qloo discovers places but itinerary composition is unavailable, those Qloo candidates remain visible instead of being replaced by an ungrounded fallback.

## How Qloo is used

Qloo is central to the product rather than an auxiliary enrichment API.

| Stage | Qloo capability | Product purpose |
| --- | --- | --- |
| Taste selection | Search API | Resolve human-readable cultural references into Qloo entity IDs |
| Destination resolution | Search API | Resolve user input to a canonical Qloo locality ID |
| Destination discovery | Insights API | Find strictly local real places connected to the selected taste signals |
| Evidence | Explainability, affinity, and tags | Show why a candidate is relevant |
| Mapping | Place coordinates | Render validated candidates globally with MapLibre |

The Qloo credential remains server-side. Raw upstream errors and credentials are never returned to the browser.

## Reliability and public-demo safeguards

- Typed Qloo normalization supports the observed hackathon response shapes.
- Qloo calls use bounded timeouts and retries with public-safe error classifications.
- LLM timeout and retry behavior are configurable and provider-neutral.
- Structured output is validated with Pydantic.
- Candidate provenance, non-empty completion, dates, ordering, and known driving feasibility are enforced deterministically.
- Search and planning endpoints have process-local rate limits and short-lived caches.
- Planning concurrency is bounded to protect Qloo and LLM quotas.
- The production container exposes a health endpoint and serves the frontend and API from one origin.

## Technology

- **Taste intelligence:** Qloo Search and Insights APIs
- **Agent orchestration:** Python, LangChain, provider-neutral OpenAI-compatible chat model
- **Backend:** FastAPI, Pydantic, HTTPX
- **Frontend:** Vue 3, TypeScript, Vite
- **Map and routing:** MapLibre GL JS using Qloo coordinates plus degradable OSRM driving evidence
- **Deployment:** Multi-stage Docker image, Render Blueprint/CD, retained Railway configuration, GitHub Actions
- **Testing:** pytest, Vitest, Vue Test Utils, production smoke tests

## Validation evidence

The repository includes fixture-based automated tests and a redacted live-validation record. The latest production regression used the first two **Jane Eyre** film results and **上海** as the destination:

- Qloo resolved `上海市` and strict local discovery returned 20 mappable candidates;
- all accepted candidates retained Qloo provenance and coordinates;
- 3 itinerary days, 13 itinerary items, and 3 driving routes were generated;
- the bounded decision chain completed locality resolution, strict discovery, composition, routing, and finish;
- no itinerary item referenced a place outside the Qloo candidate set;
- the production Vue build, `/health`, and `/openapi.json` passed the smoke test.

See [live-validation.md](live-validation.md) for the broader validation record.

## Suggested 90-second demo

1. **Problem, 10 seconds:** explain that category-based planners do not understand the traveler’s specific cultural taste.
2. **Taste selection, 20 seconds:** search Qloo and combine two cross-domain signals, including the Music category when useful.
3. **Generation, 10 seconds:** choose a destination, dates, pace, and one practical constraint.
4. **Evidence, 30 seconds:** show the resolved locality, scored Qloo contribution signals, real decision trace, and driving legs.
5. **Trust, 10 seconds:** explain that the policy can choose only controller-approved actions and the composer receives one repair attempt before a partial result.
6. **Global experience, 10 seconds:** show Qloo coordinates and OSRM road geometry in MapLibre, then mention geometric fallback and the single-service deployment.

## Current scope and next steps

TasteRoute intentionally focuses on trusted cultural discovery and itinerary composition. OSRM driving evidence improves ordering and schedule feasibility but is degradable and is not turn-by-turn navigation or live traffic. The product does not yet provide reservations, authentication, or persistent trip storage. Natural next steps are collaborative saved trips, feedback-driven taste refinement, opening-hours evidence, and booking integrations while retaining the same Qloo provenance boundary.

## Why it matters

TasteRoute demonstrates an agent pattern in which generative intelligence is constrained by a specialized source of truth. Qloo supplies the cultural graph and real places; deterministic code protects provenance; the LLM converts that evidence into a useful experience. The result is more personal than a category search and more trustworthy than an unconstrained itinerary generator.
