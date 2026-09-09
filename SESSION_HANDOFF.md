# Current session handoff

Updated 2026-09-09. Stage 5 is approved for calculator-only readiness and Stage
6 is approved as literature-informed readiness.

## Approved baseline

Stage 2 was approved on 2026-09-04 in `7e626c0`, based on implementation
`2e8802f` and evidence `8ef54f5`. The clean-clone evidence records 4 Node tests,
6 Chromium scenarios, 26 Python tests, typecheck, build, source audit, snapshot
validation, and diff checks passing. See
[Stage 2](./docs/phases/02-offline-calculator.md).
These results do not validate subsequent uncommitted changes.

## Current work and next action

Stage 5 browser readiness was approved by the user as the web-first calculator
baseline. The candidate implementation includes:
`index.html`, `package.json`, `public/manifest.webmanifest`, `public/sw.js`,
`src/main.tsx`, `src/persistence.ts`, and `src/styles.css`, plus untracked
icons, `scripts/write-precache.mjs`, `src/vite-env.d.ts`, and the deferred
`docs/pilot-protocol.md`. Preserve these changes and unrelated workstation
artifacts.

Passed 2026-09-07: `npm test` (4), `npm run typecheck`, `npm run build`, root Chromium E2E with axe, keyboard, Slow-4G, and no-egress evidence, `python pipeline/validate.py`, 26 Python tests, `git diff --check`, and a separate `/fieldmargin/` scoped-base Chromium E2E. The desktop-Chromium Slow-4G test records final-required-input-to-ranked-result time with a 5-second maximum; the recorded run was 194 ms. Fresh review corrected the service-worker activation race and added scoped-base coverage. Historical npm recovery details remain in
[the progress log](./PROJECT_PROGRESS.md); they are not the current next task.

## Validation and boundaries

Stage 6 is approved as a literature-informed calculator-readiness review. The protocol,
search log, screening record, 20-source extraction matrix, two internal audit
passes, claim tiers, and concern-to-requirement map are in
[`docs/academic-evidence-review.md`](./docs/academic-evidence-review.md) and
[`docs/academic-evidence-matrix.csv`](./docs/academic-evidence-matrix.csv).
The participant protocol and session kit are retained as superseded, deferred
human-validation materials. The current next action is review of the separate
modeled-estimate context lane while the observed-price Stage 1 remediation remains
blocked. Participant access, recruitment, contact, session
records, hosting/base URL, data promotion, and deployment require project-team
authority. Android installation and hardware recovery are optional and do not
block the web release.

Keep versioned localStorage calculator drafts separate from future automated
snapshot architecture. Stage 1's source gate still blocks Stages 3 and 4.
Do not infer deployment, push, remote configuration, workflow dispatch, or
participant-contact authorization from this handoff. Leave credentials,
workstation caches, agent configuration, and unrelated artifacts untouched.
Stage 5 is `Approved` for this calculator-only web transition. Stage 6 is
`Approved — literature-informed readiness`. Do not claim participant outcomes,
farmer validation, or start Stages 3/4, deploy, or start a public launch without
separate authorization. Do not promote observed automated prices until the new
Stage 1 report passes and receives explicit approval. The World Bank modeled
artifact is editable context only and must never be described as an observed
farmer price.
