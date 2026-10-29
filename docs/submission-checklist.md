# Qloo Agentic Hackathon submission checklist

## Repository owner actions

- [x] Add `QLOO_API_KEY` and LLM secrets to the deployment platform; never commit or paste them into an issue.
- [x] Run and record the live validation procedure.
- [x] Create the Render Blueprint, add server secrets, and save its deploy hook as the GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`.
- [ ] Optionally connect Railway to `main` as a supported fallback; Railway CD is intentionally deferred.
- [x] Use the OpenFreeMap Liberty production street style by default; retain `VITE_MAP_STYLE_URL` as an override.
- [ ] Deploy the backend and frontend and verify the public URL in a private/incognito window.
- [ ] Decide when to change the GitHub repository from private to public, if hackathon rules require it.
- [x] Add the hackathon-focused repository topics and About text.
- [ ] Add the public demo URL and remaining submission metadata.
- [ ] Record a short demo showing: seed search, a cross-domain taste selection, generated route, Qloo evidence, and MapLibre map.
- [ ] Prepare screenshots; the evaluator-facing provenance explanation is documented in `docs/project-introduction.md`.
- [ ] Review Qloo and map tile attribution requirements in the final public demo.
- [ ] Move the judging service off Render's sleeping free plan to avoid a 25–35 second cold start.
- [ ] Submit before the official deadline and retain the confirmation.

## Engineering checks

- [x] Backend tests pass.
- [x] Frontend tests and production build pass.
- [x] `/health`, `/`, and `/openapi.json` pass `scripts/smoke-test.ps1` against FastAPI serving the production Vue build.
- [x] Docker image builds successfully in CI.
- [x] The latest `main` CI run passes and triggers a Render deployment after the deploy-hook secret is configured.
- [x] Secret scan is clean.
- [x] Live responses contain no fabricated places or coordinates.
- [x] Error and partial states are visible and honest.
