# Qloo Agentic Hackathon submission checklist

Official references:

- [Hackathon overview and submission requirements](https://qloo.devpost.com/)
- [Official rules](https://qloo.devpost.com/rules)
- [Official schedule](https://qloo.devpost.com/details/dates)

Submission closes **October 30, 2026 at 11:45 PM EDT**, which is **October 31, 2026 at 11:45 AM China Standard Time**. Entries cannot be substantively changed after the deadline.

## Eligibility requirements

- [x] TasteRoute is a working agentic application with Qloo as a material grounding layer.
- [x] The externally hosted application is available at `https://taste-route-ch14.onrender.com`.
- [x] The repository contains source code, assets, setup instructions, deployment configuration, and an MIT license recognized by GitHub.
- [x] The English project description explains the workflow, core features, and why the result is Qloo-powered.
- [ ] Change the GitHub repository from private to public before submitting.
- [ ] Confirm the live application remains free and accessible without login through the judging period, ending November 5, 2026 at 9:00 AM EST.
- [ ] Confirm all third-party services, assets, fonts, map tiles, and APIs are used under applicable terms and attribution requirements.

## Devpost submission steps

- [ ] Join the Qloo Agentic Hackathon with the submitting Devpost account.
- [ ] Create a draft from the hackathon's **Enter a Submission** page.
- [ ] Enter the project name, a concise tagline, and an English project story based on `docs/project-introduction.md`.
- [ ] Upload a 3:2 project thumbnail and add representative screenshots to the image gallery.
- [ ] Add relevant **Built with** tags, including Qloo, LangChain, FastAPI, Vue, MapLibre, and Render.
- [ ] Add the functional demo URL: `https://taste-route-ch14.onrender.com`.
- [ ] Add the public repository URL: `https://github.com/cacohe/taste-route`.
- [ ] Ensure the gallery covers taste selection, generation progress, Qloo evidence, the itinerary, and the MapLibre route.
- [ ] Add concise testing instructions and state that no account is required.
- [ ] Complete any entrant type, country of residence, license, public-repository, and project-history questions shown by Devpost.
- [ ] Review the submission preview, test every submitted link in a private browser window, and submit before the deadline.
- [ ] Save the final Devpost URL and submission confirmation.

A demo video is **not required** by the official overview. Screenshots are still strongly recommended because the rules allow judges to evaluate the text, images, and video without necessarily exercising the application.

## Final presentation readiness

- [ ] Move the judging service off Render's sleeping free plan so the first evaluator does not encounter a cold start.
- [ ] Prepare a 90-second live walkthrough using the script in `docs/project-introduction.md`.
- [ ] Keep a tested fallback example ready in case an external API is temporarily unavailable during judging.
- [ ] If selected as a top-three finalist, be available for preparation and the live presentation on November 5, 2026.

## Engineering evidence

- [x] Backend tests, frontend tests, type checking, and the production build pass.
- [x] The production Docker image builds in CI.
- [x] A push to `main` deploys to Render only after backend, frontend, and container jobs pass.
- [x] CD automatically verifies `/health`, `/`, `/openapi.json`, and the deployed commit.
- [x] Secret scanning is clean and provider credentials remain server-side.
- [x] Live responses contain no fabricated places or coordinates.
- [x] Empty and partial states are explicit rather than presented as successful itineraries.
- [x] The Shanghai/Jane Eyre regression resolves the locality, returns mappable candidates, produces non-empty days, and renders driving routes.
