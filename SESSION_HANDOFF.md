# Current session handoff

Updated 2026-09-07. Stage 5 is approved for calculator-only pilot preparation;
resume [Stage 6](./docs/phases/06-pilot-validation.md).

## Approved baseline

Stage 2 was approved on 2026-09-04 in `7e626c0`, based on implementation
`2e8802f` and evidence `8ef54f5`. The clean-clone evidence records 4 Node tests,
6 Chromium scenarios, 26 Python tests, typecheck, build, source audit, snapshot
validation, and diff checks passing. See
[Stage 2](./docs/phases/02-offline-calculator.md).
These results do not validate subsequent uncommitted changes.

## Current work and next action

Stage 5 browser readiness was approved by the user with its physical-Android
limitation retained. The candidate implementation includes:
`index.html`, `package.json`, `public/manifest.webmanifest`, `public/sw.js`,
`src/main.tsx`, `src/persistence.ts`, and `src/styles.css`, plus untracked
icons, `scripts/write-precache.mjs`, `src/vite-env.d.ts`, and `docs/pilot-protocol.md`. Preserve these changes and unrelated workstation artifacts.

Passed 2026-09-07: `npm test` (4), `npm run typecheck`, `npm run build`, root Chromium E2E with axe, keyboard, Slow-4G, and no-egress evidence, `python pipeline/validate.py`, 26 Python tests, `git diff --check`, and a separate `/fieldmargin/` scoped-base Chromium E2E. The desktop-Chromium Slow-4G test records final-required-input-to-ranked-result time with a 5-second maximum; the recorded run was 194 ms. Fresh review corrected the service-worker activation race and added scoped-base coverage. Historical npm recovery details remain in
[the progress log](./PROJECT_PROGRESS.md); they are not the current next task.

## Validation and boundaries

Stage 6 materials are prepared in [`docs/pilot-session-kit.md`](./docs/pilot-session-kit.md): a verbal-consent script, privacy rules, moderator tasks, observer rubric, critical-blocker handling, aggregate gate worksheet, and calculator release card. The explicit limitation remains no real Android install/update/offline-recovery evidence. Participant access, recruitment, contact, session records, hosting/base URL, and deployment require project-team authority.

Keep versioned localStorage calculator drafts separate from future automated
snapshot architecture. Stage 1's source gate still blocks Stages 3 and 4.
Do not infer deployment, push, remote configuration, workflow dispatch, or
participant-contact authorization from this handoff. Leave credentials,
workstation caches, agent configuration, and unrelated artifacts untouched.
Stage 5 is `Approved` for this calculator-only transition. Stage 6 is `In progress`; do not claim participant outcomes, start Stages 3/4, deploy, or start a public launch without separate authorization.
