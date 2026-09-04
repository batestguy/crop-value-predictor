# Crop Value Predictor Delivery Progress

**Plan:** [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)  
**Workflow:** sequential delivery with a user review at every acceptance gate  
**Last updated:** 2026-09-04

## Current status

| Stage | Status | Evidence record | Gate condition |
|---|---|---|---|
| 0. Baseline and tracking setup | Approved | [`00-baseline.md`](./docs/phases/00-baseline.md) | Progress records, public remote, and cloud validation are reproducible |
| 1. Source and feasibility audit | Closed — fallback accepted | [`01-source-audit.md`](./docs/phases/01-source-audit.md) | WFP/HDX technical gate failed; automated prices blocked |
| 2. Offline decision calculator | In progress | [`02-offline-calculator.md`](./docs/phases/02-offline-calculator.md) | Complete-input calculation, report parity, persistence, and offline restart |
| 3. Automated data pipeline | Not started | [`03-data-pipeline.md`](./docs/phases/03-data-pipeline.md) | Reproducible snapshots, schema/quality checks, and safe last-known-good fallback |
| 4. Forecasting and validation | Not started | [`04-forecasting.md`](./docs/phases/04-forecasting.md) | Leakage-safe rolling validation, baseline comparison, and auditable intervals |
| 5. Deployment and farmer readiness | Not started | [`05-deployment-readiness.md`](./docs/phases/05-deployment-readiness.md) | Tested install/offline flow, accessibility, low-bandwidth result, and privacy |
| 6. Pilot validation and expansion | Not started | [`06-pilot-validation.md`](./docs/phases/06-pilot-validation.md) | Moderated comprehension, helpfulness, forecast follow-up, and documented limits |

## Status rules

- `Not started`: no stage work has been accepted.
- `In progress`: implementation or evidence collection is underway.
- `Blocked`: a stated dependency prevents safe progress.
- `Gate review`: the stage work and evidence are complete and awaiting user review.
- `Closed — fallback accepted`: the success gate did not pass, the documented
  fallback was explicitly accepted, and downstream work may proceed only
  within that fallback's stop conditions.
- `Approved`: the acceptance gate passed and the next stage may begin.

Every phase record must include a dated progress log, changed files or
artifacts, commit references, commands and results, decisions, risks, and the
gate outcome. A stage is never approved from code presence alone.

## Review protocol

1. Mark one stage `In progress` and record its starting commit.
2. Record material work and verification as it happens.
3. Run the stage checks and the full regression suite.
4. Mark the record `Gate review` with evidence and known limitations.
5. Pause for an explicit outcome decision.
6. Mark a passing gate `Approved`; if the gate fails but its documented
   fallback is accepted, mark it `Closed — fallback accepted` and preserve the
   failed conditions in the evidence record.

## Baseline evidence

- Repository: public GitHub remote at `https://github.com/batestguy/crop-value-predictor`,
  `main` tracking `origin/main`.
- `python pipeline/validate.py`: passed; five crops and five forecast records.
- `python -m unittest discover -s tests`: passed; 19 tests.
- `npm test`: passed.

## Architecture decision — 2026-08-25

The project user authorized execution of the documented prototype architecture:
one remote, CPU-based Kaggle training release orchestrated and validated by
GitHub Actions; static versioned forecast outputs deployed to GitHub Pages; no
online learning, live prediction API, local training, or automatic post-launch
rebuild. See [`batch-training-architecture.md`](./docs/batch-training-architecture.md)
and [`source-register.md`](./docs/source-register.md).
- `npm run build`: passed.
- Current limitation: the React UI still uses hardcoded pilot-seed data and
  production source integration is not yet approved; calculator arithmetic now
  runs through the tested `src/calculations.ts` boundary.
- Cloud policy: GitHub Actions is authoritative for data/ML computation,
  validation, tests, and builds; browser arithmetic remains the offline client
  calculation.
- Cloud CI run: [32685906128](https://github.com/batestguy/crop-value-predictor/actions/runs/32685906128)
  passed on commit `e201edf`.
- Cloud refresh run: [32685952971](https://github.com/batestguy/crop-value-predictor/actions/runs/32685952971)
  passed and uploaded the validation artifact with 30-day retention.

## Reviewed fallback decision — 2026-08-27

The authenticated Stage 1 evidence is complete and has been reviewed. FEWS NET
data is fresh under the 75-day rule, but its best recent completeness is 69.4%,
below the required 80%; zero crop forms qualify. The accepted outcome is the
documented calculator-only fallback. This closes the review without declaring
the five-crop technical gate Approved.

Stage 2 may now proceed as a strict farmer-input calculator. Production data
integration, automated price claims, source-driven rankings, and Stage 3 remain
blocked until a future qualification report independently passes the source
gate. The current execution handoff is [`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md).

## Remediation reopening — 2026-09-04

Source remediation is reopened for a fresh WFP/HDX observed-price audit. This
does not approve Stage 1 or alter the calculator-only deployment boundary:
`stage_1_approved` remains false and no public snapshot/default/forecast files
are changed. A successful technical and rights gate will be recorded as
`Gate review` and await explicit user approval.

The v2 live audit completed in `audit-output-remediation-2026-09-04-v2`.
WFP/HDX identity, `cc-by-igo` license, resource separation, and SHA-256
manifest checks passed. The 81,534-row snapshot normalized 11,716 rows, but
zero series passed the unchanged 36-month, 80%-completeness, 75-day freshness,
six-origin, and three-market gates. Best completeness was 83.3% but stale at
81 days; fresh series reached only 52.8%. World Bank remained an optional
zero-row failure. Automated prices remain blocked and the app remains
calculator-only.

## Next-phase plan — Stage 2

The decision-complete Stage 2 scope is documented in
[`02-offline-calculator.md`](./docs/phases/02-offline-calculator.md). The next
move is to verify and checkpoint the existing uncommitted Stage 1/calculation
foundation, then finish strict input validation, versioned local persistence,
print parity, seed-data quarantine, offline browser tests, and CI evidence.

## Implementation update — 2026-08-27

Stage 2 implementation is substantially complete at the source and contract
level. The calculator now accepts only complete farmer-entered scenarios:
shared area, yield, selling price, optional low/high price range, and eight
per-hectare cost categories. Invalid or incomplete selections remain visible as
errors but cannot produce a ranking, winner, recommendation, or print action.

Delivered artifacts include `src/calculations.ts`, `src/persistence.ts`, the
calculator-only `src/main.tsx`, an inactive `public/data/v1/` snapshot, a
versioned service-worker cache in `public/sw.js`, and Playwright coverage in
`tests/e2e/calculator.spec.ts`.

Verification completed:

- `npm test`: passed, 3 calculator tests at this checkpoint; the current suite
  contains 4 passing tests.
- `python pipeline\\validate.py`: passed.
- `python -m unittest discover -s tests -v`: passed, 19 tests.
- `git diff --check`: passed.

The production toolchain remains unverified. npm installation encountered a
Windows npm-cache `EPERM` error, so `npm run typecheck` and `npm run build`
could not find complete local `tsc` and `vite` installations. No Stage 2 gate
approval is claimed.

## Next action and handoff

The next phase is Stage 2 verification and gate preparation, not automated data
integration or Stage 3. Restore npm tooling and a lockfile, add/run Chromium
coverage for ranking suppression, ranges, reload persistence, corrupt-state
recovery, reset, screen/print parity, and offline restart. Record the evidence
and commit reference in [`docs/phases/02-offline-calculator.md`](./docs/phases/02-offline-calculator.md),
then move Stage 2 to `Gate review` only when every acceptance condition passes.

Keep Stage 1 marked `Closed — fallback accepted`; do not introduce automated
prices, source-driven defaults, forecasting, deployment, or public launch claims.

## Verification checkpoint — 2026-09-04

Source remediation is recorded in commit `14d50f0`; the calculator foundation is
recorded in `2a40c62`. Passed checks are `npm test` (4),
`python pipeline\\validate.py`, Python regression tests (26), and
`git diff --check`. Stage 2 remains `In progress`: typecheck/build/E2E are
blocked because npm could not materialize the local toolchain or lockfile after
registry and offline-cache attempts. No approval is claimed.

## Plan execution update — 2026-08-28

- Node `24.15.0`, npm `11.16.0`, and the project cache were confirmed.
- Passed: `npm test` (4), `python pipeline\\validate.py`, Python regressions (19),
  and `git diff --check`.
- Updated `playwright.config.ts` to build and serve the production preview on
  port 4173; updated CI for Node 24, `npm ci`, typecheck/build, Chromium, and
  Playwright.
- npm dependency resolution remains blocked: generated lockfile installation
  fails with `Invalid Version`, and Vite/TypeScript/Playwright binaries plus
  Chromium are unavailable. Stage 2 remains **In progress**.
- No checkpoint commit, push, CI dispatch, deployment, source remediation, or
  Stage 3 work occurred.

Follow-up recovery on 2026-08-28 retried npm 10/11 with a clean temporary
cache. Lockfile generation completed, but `npm ci` reported the lockfile was
out of sync, so the unvalidated lockfile was removed. A regular install timed
out before creating Vite, TypeScript, Playwright, or Chromium. Stage 2 remains
**In progress** pending an alternative dependency-resolution strategy.

## Toolchain and handoff update — 2026-08-28

The original Windows npm cache permission problem has been isolated. The
project now uses `D:\Crop Value Predictor App\.npm-cache-repair`, and registry
queries succeed from that location. Verbose dependency installation makes
network progress but has not yet completed, so there is still no lockfile or
local `vite`, `tsc`, and Playwright executables.

The calculator suite now records 4 passing Node tests. The Python snapshot and
19-test regression suite remain passing. Production typecheck/build and
Chromium evidence remain pending.

The existing browser suite contains 3 initial scenarios but is not yet gate
complete. It still needs optional price-range, corrupt/unknown persistence,
screen/print parity, and production offline-restart coverage. The Playwright
server configuration must also be changed from the mismatched development
server to a production preview on port 4173.

[`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md) is now the authoritative restart
entry point. Stage 2 remains **In progress**.
