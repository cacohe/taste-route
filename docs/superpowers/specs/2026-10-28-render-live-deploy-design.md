# Render Live Deployment and Automated Smoke Design

## Intent

Finish the existing Render deployment instead of leaving CD in a configured-but-skipped state. A successful GitHub workflow must mean that the exact tested commit is live on Render and the deployed application passes production smoke checks.

## Chosen approach

Use the existing Render Deploy Hook and GitHub Actions gate. After triggering the tested SHA, a Python smoke runner polls the public service until `/health` reports the same `RENDER_GIT_COMMIT`, then validates the SPA and OpenAPI document. This is preferred over a fixed sleep, which is flaky, and over checking only HTTP 200, which could accidentally verify the previous deployment.

The existing PowerShell smoke command remains a local wrapper, but CI/CD owns the required production check. The Render service URL is stored as the non-secret GitHub Actions variable `RENDER_SERVICE_URL`; the deploy hook remains the secret `RENDER_DEPLOY_HOOK_URL`.

## Deployment setup

- Create the `taste-route` Docker web service from the committed `render.yaml` on `main`.
- Populate required runtime credentials from the ignored local `backend/.env` without printing or committing values.
- Store the Render hook and public URL in GitHub Actions.
- Keep Render commit auto-deploy disabled so GitHub CI remains the release gate.

## Reliability contract

- Missing hook or service URL fails CD instead of producing a false green result.
- `/health` remains fast and dependency-free, and includes the deployed commit only when Render provides it.
- Smoke polling is bounded and reports the last safe error without exposing credentials.
- A deployment is complete only after the expected SHA, homepage marker, and OpenAPI document are verified.
