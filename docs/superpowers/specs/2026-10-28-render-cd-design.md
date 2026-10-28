# Render CD Design

## Goal

Keep TasteRoute deployable as one Docker service on both Railway and Render, while making `main` the only maintained branch and the only source of production deployments. A push to `main` must run backend, frontend, and container validation before Render is triggered.

## Deployment model

- Keep `railway.json` as the Railway deployment contract.
- Add a root `render.yaml` Blueprint for the same Dockerfile, `/health` health check, and runtime secrets.
- Disable Render's commit-based auto-deploy. GitHub Actions owns the gate and calls a secret Render deploy hook only after all CI jobs pass.
- Do not fail pull requests or local forks merely because the Render hook secret is unavailable. The deployment job is limited to pushes on `main`, reports a clear skip when the secret is missing, and becomes automatic as soon as `RENDER_DEPLOY_HOOK_URL` is configured.
- Keep one replica because rate limits, concurrency guards, and caches are process-local.

## CI/CD contract

- CI runs for manual dispatch, pull requests targeting `main`, and pushes to `main` only.
- Backend, frontend, and production container jobs remain independent quality gates.
- The Render deployment job depends on all three gates and never runs for pull requests or non-`main` refs.
- The hook receives the tested commit SHA through Render's `ref` query parameter so a newer untested commit cannot be deployed accidentally.
- Railway remains deployable from its checked-in configuration; Railway CD is intentionally deferred.

## Documentation and branch policy

Deployment documentation covers both platforms, identifies Render as the current CD target, and lists the one-time user actions needed in Render and GitHub. After the new `main` workflow passes, delete the obsolete local and remote `feature/taste-route` branch.

## Verification

Repository tests assert the deployment contracts, branch filters, CI dependencies, secret handling, and tested-commit pinning. The full backend, frontend, and container checks must pass before pushing, and the resulting GitHub Actions run must be green before obsolete branch deletion.
