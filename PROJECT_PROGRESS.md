# Crop Value Predictor Delivery Progress

**Plan:** [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)  
**Workflow:** sequential delivery with a user review at every acceptance gate  
**Last updated:** 2026-09-10

## Current status

| Stage | Status | Evidence record | Gate condition |
|---|---|---|---|
| 0. Baseline and tracking setup | Approved | [`00-baseline.md`](./docs/phases/00-baseline.md) | Progress records, public remote, and cloud validation are reproducible |
| 1. Source and feasibility audit | In progress — observed retrieval blocked | [`01-source-audit.md`](./docs/phases/01-source-audit.md) | Fresh FEWS/WFP audit must pass unchanged technical and rights gates |
| 2. Offline decision calculator | Approved | [`02-offline-calculator.md`](./docs/phases/02-offline-calculator.md) | Complete-input calculation, report parity, persistence, and offline restart |
| 3. Automated data pipeline | Blocked | [`03-data-pipeline.md`](./docs/phases/03-data-pipeline.md) | Unchanged Stage 1 source gate blocks automated data |
| 4. Forecasting and validation | Blocked | [`04-forecasting.md`](./docs/phases/04-forecasting.md) | Unchanged Stage 1/Stage 3 dependency blocks forecasting |
| 5. Web deployment and farmer readiness | Approved | [`05-deployment-readiness.md`](./docs/phases/05-deployment-readiness.md) | Browser-first calculator readiness; Cloudflare Pages deployment remains separately gated |
| 6. Literature-informed calculator readiness | Approved — literature-informed readiness | [`06-pilot-validation.md`](./docs/phases/06-pilot-validation.md) | User approved the 20-source review and requirement map; participant validation remains absent |

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
GitHub Actions; static versioned forecast outputs deployed to Cloudflare Pages; no
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

## Stage 2 approval — 2026-09-04

The user explicitly approved Stage 2 after the complete clean-clone gate passed.
Approval covers complete farmer-entered calculator scenarios only. It does not
unlock automated prices, source-driven defaults, forecasting, Stage 3, Stage 4,
deployment, public launch, push, or workflow dispatch. The unchanged Stage 1
source gate continues to block automated work.

The next action is calculator-only pilot and deployment-readiness planning.

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

Stage 2 was approved on 2026-09-04, recorded in `7e626c0`, based on
implementation `2e8802f` and evidence `8ef54f5`. Continue calculator-only
readiness using [Stage 5's work packages](./docs/phases/05-deployment-readiness.md)
and the [current handoff](./SESSION_HANDOFF.md). Review the existing uncommitted
implementation against the approved baseline, then validate it in an isolated
reproducible environment if the primary toolchain remains unusable.

Planning is prepared; implementation verification is pending. Earlier recovery
entries below are historical and do not reopen the approved Stage 2 gate.
Stage 1 remediation is now active under the unchanged source gates; Stages 3
and 4 remain blocked until a new report passes. Deployment and public launch
require separate authorization.

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

## Checkpoint boundary completion — 2026-09-04

Follow-up commits `adbca90` and `516e3d1` make the source-audit retrieval and
calculator checkpoint artifacts self-contained. Lock recovery was attempted in
`%TEMP%\\crop-value-lock-20260904-1` using only a copied `package.json` and the
project cache. The cache-path command failed with npm `ENOENT` because the
space-containing path was parsed incorrectly; the `npm_config_cache` retry was
stopped after 60 seconds without creating a lockfile. Typecheck/build/E2E stay
blocked and Stage 2 remains `In progress`.

## Final clean-clone recovery — 2026-09-04

Commit `f3e0551` adds the validated `package-lock.json` (SHA-256
`0c1fc59fe68d10a896933129ffada842baa4437e769b501661f6009f97eeb749`). In a
clean detached clone, `npm ci` succeeded after one sandbox `ECONNRESET` retry
with network access; `npm ls --depth=0`, `npm test` (4), `npm run typecheck`,
and Python tests (26) passed. The clone build failed because esbuild could not
read the temporary clone path (`Access is denied` resolving `vite.config.ts`),
so E2E and Chromium were not run. The primary workstation still has an
uncleanable partial `node_modules`; Stage 2 remains `In progress`.

## Stage 2 gate evidence — 2026-09-04

Commit `2e8802f` completed the focused recovery/test fixes. A fresh detached
clone at that commit passed `npm ci`, `npm test` (4), `npm run typecheck`,
`npm run build`, `npm run test:e2e` (6), `python pipeline\\source_audit.py`,
`python pipeline\\validate.py`, Python tests (26), and `git diff --check`.
Node versions were 24.15.0/npm 11.16.0; installed packages resolve to React
18.3.1, Vite 6.4.3, TypeScript 5.9.3, and Playwright 1.62.1. Chromium was
installed under the validation root. The lockfile SHA-256 is
`0c1fc59fe68d10a896933129ffada842baa4437e769b501661f6009f97eeb749`.
At the time of this evidence capture, Stage 2 was `Gate review`, pending user
approval. The primary workstation's partial
`node_modules` remains an operational cleanup limitation only.

## Calculator readiness planning - 2026-09-05

Prepared sequential install/cache, draft-error, usability/privacy, browser,
and pilot-evidence work packages in
[`docs/phases/05-deployment-readiness.md`](./docs/phases/05-deployment-readiness.md).
Updated the current handoff and retained historical toolchain recovery evidence.
Stage 5 is `In progress`: planning prepared; implementation verification pending.
Existing application changes are unverified and preserved. Documentation checks
cover relative links, status consistency, and targeted `git diff --check`;
application tests were not rerun for this documentation-only continuation.
No Stage 5 gate approval, deployment, or participant evidence is claimed.

## Calculator readiness implementation — 2026-09-07

Stage 5 calculator-only browser readiness is now at `Gate review`. The service worker uses generated immutable cache identities and scoped cleanup; PWA assets and registration support both root and `/fieldmargin/` bases; persistence recovers safely from blocked or malformed storage; and browser coverage includes update cleanup, offline restart, print parity, selection recovery, axe critical-violation assertions, keyboard completion, desktop-Chromium Slow-4G final-input-to-result timing, and no-third-party post-load print/report flow. The full local suite passed: 4 calculator tests, typecheck, build, Chromium E2E, snapshot validation, and 26 Python tests. A separate scoped-base Chromium test passed. Fresh review identified and corrected the worker-activation test race and missing non-root base-path coverage.

Physical Android install/update/offline recovery and participant evidence remain
uncollected; they are no longer active web-release requirements. No deployment,
public launch, push, workflow dispatch, automated prices, forecasting, or Stage
6 work was performed.

## Stage 5 approval and Stage 6 start — 2026-09-07

The user approved Stage 5's calculator-only browser-evidence package and directed the project to proceed. This approval covers browser-first web readiness only; it is not deployment approval, public-launch approval, or participant validation.

Stage 6 entered `Gate review` for literature-informed calculator readiness.
The approval is recorded below.
The review protocol and matrix are in
[`docs/academic-evidence-review.md`](./docs/academic-evidence-review.md) and
[`docs/academic-evidence-matrix.csv`](./docs/academic-evidence-matrix.csv).
The consent-safe moderator script and session kit remain superseded, deferred
human-validation materials. Participant recruitment, contact, session records,
and storage remain project-team-controlled external work. Stages 3 and 4 remain
blocked, so no automated-price or forecast evidence is created or implied.

## Stage 6 literature-informed readiness — 2026-09-09

Reframed Stage 6 from participant pilot validation to a rapid scoping review
reported with PRISMA 2020 and JBI guidance. The evidence package contains four
search areas, exact search strings, frozen screening counts, 20 source rows
(five per area), stable DOI/URL references, MMAT/context judgments, an internal
second review pass, claim tiers, and a concern-to-requirement/test map.

The stage was at `Gate review` pending the user's decision. The user approved
the package on 2026-09-09 as `Approved — literature-informed readiness`. The
review does not prove Nigerian farmer comprehension, usefulness, completion,
offline recovery, or physical-device performance. The former 80% completion and
70% helpfulness thresholds are removed because there is no participant
denominator. The retained pilot protocol and session kit are future
human-validation materials only.

## Stage 6 approval — 2026-09-09

The user approved the completed academic evidence review, extraction matrix,
screening record, two audit passes, evidence tiers, and
concern-to-requirement map. Stage 6 is now `Approved — literature-informed
readiness`. This approval does not claim farmer validation and does not unlock
automated prices, forecasting, deployment, or public launch. Android hardware
evidence is optional and non-blocking for the web product.

## Stage 1 web-first remediation — 2026-09-09

The active remediation preserved the existing technical and rights gates and
created immutable audit directories for the fresh attempts. The first run
downloaded the current WFP/HDX resource and FAOSTAT archive but failed closed
on FEWS HTTP 403, World Bank zero rows, and an NBS timeout. Qualification
returned `calculator_only_fallback` with zero eligible series.

The FEWS adapter was repaired to use the official dataset-filtered public API
contract (`dataset=FEWS_NET_Staple_Food_Price_Data`, `country=NG`,
`format=json`) and the source regression suite passed 34 tests. Fresh retries
still encountered FEWS 403/timeouts during full retrieval. Stage 1 remains
unapproved, `stage_1_approved` remains false, no public snapshot changed, and
Stages 3 and 4 remain blocked. The browser-first PWA remains the active
calculator product; Android hardware evidence is optional and non-blocking.

The follow-up FEWS-only attempt now requests the latest 60 complete months and
uses bounded backoff for transient upstream responses. It still received
repeated HTTP 403 responses, so the source gate remains blocked by retrieval
availability rather than by a relaxed threshold.

### 2026-09-09 — modeled context lane implemented

The current official World Bank Nigeria bulk file was retrieved through the
catalog bulk-discovery API and passed a separate numerical screen: 17,464 rows,
73 source markets, six source-aligned forms, 100% latest-36-month completeness,
and a latest observation of 2026-08-01. The generated artifact contains 438
editable modeled estimates across those forms and markets. It is exposed only
through `modeled_price_suggestions.json`, with a separate snapshot ID,
`modeled_estimate` price type, source hash, and explicit “not observed” warning.
The observed Stage 1 gate remains false; no forecast, observed-price approval,
or farmer-validation claim was made.

## Stage 1 fresh audit — 2026-09-10

The next-stage observed-price audit was executed into the new immutable
directory `audit-output-remediation-2026-09-10` using the unchanged August
2026 cutoff. FEWS NET returned HTTP 403 after its bounded retries, so the
required-source retrieval gate failed closed. World Bank, WFP/HDX, FAOSTAT,
and NBS artifacts were retrieved and their manifest checksums passed.

Qualification recorded `calculator_only_fallback`, with zero FEWS eligible
series, zero WFP eligible series, and zero selected crop forms. No public data
artifact changed; `stage_1_approved` remains false, and Stages 3 and 4 remain
blocked. The next actionable step is an authorized retrieval origin that can
reach the FEWS endpoint, or a separate focused review of the already isolated
modeled-estimate context lane.

The ordered follow-up sequence is maintained in
[`docs/next-actions.md`](./docs/next-actions.md). The modeled-context browser
verification is now complete: the full suite passed 17 tests with one
intentional base-path skip and exited cleanly. The next decision is whether to
remain calculator-only or authorize a retrieval origin that can reach FEWS;
observed-price retrieval remains an externally authorized decision, not a
local retry loop.

## Authorized cloud FEWS investigation — 2026-09-10

The user authorized an external/cloud retrieval origin. Two bounded canaries
and the full read-only Stage 1 workflow were dispatched on
`stage1-adapter-fix`:

- Canaries `34434267144` and `34434497826` tested August and June windows.
  August returned no positive total; June returned HTTP 403.
- Full audit `34434760861` completed with the required-source retrieval step
  failed closed on FEWS HTTP 403. Its artifact was downloaded into the new
  immutable directory `audit-output-fews-cloud-full-20260910-34434760861`.
- The cloud qualification report is `calculator_only_fallback`, with zero
  FEWS eligible series, zero selected crops, and `stage_1_approved: false`.
  WFP, FAOSTAT, and NBS manifest hashes passed; World Bank used the older
  remote-branch endpoint and returned zero rows.

The cloud origin is reachable, but no observed-price evidence passed the
unchanged gates. No public artifact changed, no promotion was attempted, and
Stages 3 and 4 remain blocked. Further FEWS work requires a justified adapter
or endpoint-contract change, not repeated retrieval of the same failing path.
