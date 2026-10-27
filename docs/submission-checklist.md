# Qloo Agentic Hackathon submission checklist

## Repository owner actions

- [ ] Add `QLOO_API_KEY` and LLM secrets to the deployment platform; never commit or paste them into an issue.
- [ ] Run and record the live validation procedure.
- [ ] Choose the final deployment platform and configure `CORS_ORIGINS` plus `VITE_API_BASE_URL`.
- [ ] Deploy the backend and frontend and verify the public URL in a private/incognito window.
- [ ] Decide when to change the GitHub repository from private to public, if hackathon rules require it.
- [ ] Add the hackathon-required repository topics, About text, demo URL, and submission metadata.
- [ ] Record a short demo showing: seed search, a cross-domain taste selection, generated route, Qloo evidence, and MapLibre map.
- [ ] Prepare screenshots and a concise explanation of why the provenance guard matters.
- [ ] Review Qloo and map tile attribution requirements in the final public demo.
- [ ] Submit before the official deadline and retain the confirmation.

## Engineering checks

- [ ] Backend tests pass.
- [ ] Frontend tests and production build pass.
- [ ] Secret scan is clean.
- [ ] Live responses contain no fabricated places or coordinates.
- [ ] Error and partial states are visible and honest.
