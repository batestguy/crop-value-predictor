# Current session handoff

Updated 2026-09-07. Resume calculator-only readiness from
[Stage 5](./docs/phases/05-deployment-readiness.md).

## Approved baseline

Stage 2 was approved on 2026-09-04 in `7e626c0`, based on implementation
`2e8802f` and evidence `8ef54f5`. The clean-clone evidence records 4 Node tests,
6 Chromium scenarios, 26 Python tests, typecheck, build, source audit, snapshot
validation, and diff checks passing. See
[Stage 2](./docs/phases/02-offline-calculator.md).
These results do not validate subsequent uncommitted changes.

## Current work and next action

Stage 5 browser readiness is implemented and locally verified against the approved baseline. The candidate implementation includes:
`index.html`, `package.json`, `public/manifest.webmanifest`, `public/sw.js`,
`src/main.tsx`, `src/persistence.ts`, and `src/styles.css`, plus untracked
icons, `scripts/write-precache.mjs`, `src/vite-env.d.ts`, and `docs/pilot-protocol.md`. Preserve these changes and unrelated workstation artifacts.

Passed 2026-09-07: `npm test` (4), `npm run typecheck`, `npm run build`, `npm run test:e2e`, `python pipeline/validate.py`, 26 Python tests, `git diff --check`, and a separate `/fieldmargin/` scoped-base Chromium E2E. Fresh review corrected the service-worker activation race and added scoped-base coverage. Historical npm recovery details remain in
[the progress log](./PROJECT_PROGRESS.md); they are not the current next task.

## Validation and boundaries

The next evidence is real Android install/update/offline recovery, a documented network-throttling profile and first-result timing, formal accessibility checks, and participant pilot sessions. Distinguish browser emulation from physical Android results. Hosting/base URL and deployment remain open and unauthorized.

Keep versioned localStorage calculator drafts separate from future automated
snapshot architecture. Stage 1's source gate still blocks Stages 3 and 4.
Do not infer deployment, push, remote configuration, workflow dispatch, or
participant-contact authorization from this handoff. Leave credentials,
workstation caches, agent configuration, and unrelated artifacts untouched.
Stage 5 remains `In progress`, not at gate review or approved.
