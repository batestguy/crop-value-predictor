# Stage 2 — Offline Decision Calculator

**Status:** In progress — calculator-only delivery authorized
**Decision date:** 2026-08-27
**Dependency:** Stage 1 is Closed — fallback accepted. Production static data,
automated price claims, and Stage 3 still require a future qualification report
that passes the full technical and rights gate.

## Purpose

Turn the current React pilot seed into a deterministic, offline-first decision
calculator. The calculator must remain useful when audited market prices are
not qualified: farmer-entered prices, yields, and costs remain valid scenario
inputs, while every result clearly labels its source and fallback status.

This phase does not approve automated price claims, replace the Stage 1 gate, or
introduce a live upstream API. Only complete farmer-entered scenarios may drive
a ranking or recommendation label.

## Current starting point

- The UI and arithmetic are currently colocated in `src/main.tsx`.
- Pilot data is hardcoded in the browser and is intentionally illustrative.
- `public/data/v1/` already defines the static snapshot contract used by the
  existing validation tests.
- Stage 1 has zero technically qualified crop forms, so production market-price
  recommendations remain blocked. The reviewed outcome authorizes a strict
  calculator-only Stage 2 while preserving every source-gate threshold.

## Reviewed delivery decision

The next milestone is a useful offline calculator, not a forecast product. The
existing five crop labels and cost categories may remain as interface metadata,
but no seed price, yield, or cost number may enter the decision calculation.
The farmer supplies every decision-driving value.

### Included

- A shared farm area in hectares.
- At least two selected crops.
- Per-crop yield in tonnes per hectare, expected sale price in NGN/kg, and all
  eight cost inputs in NGN/ha.
- Optional per-crop low and high sale prices for a scenario range.
- Pure deterministic calculations, complete-input validation, local draft
  persistence, screen/print parity, and installed offline restart.
- Explicit calculator-only language and removal of forecast/model claims from
  the active decision view.

### Excluded

- FEWS NET, World Bank, WFP, NBS, or seed values driving a ranking.
- Automatic price refresh, production forecasts, live APIs, model training,
  source-threshold relaxation, Stage 3, deployment, or public launch.
- Accounts, analytics, cookies, server persistence, or remote storage of farmer
  inputs.

## Execution order

### 1. Verify and checkpoint the foundation

1. Review the current dirty working tree without resetting or overwriting user
   changes.
2. Restore the declared npm toolchain, generate and retain the npm lockfile,
   and verify Python, Node, TypeScript, snapshot, and production-build checks.
3. Confirm `githubtoken.txt`, raw audit directories, generated build output,
   and local `.agents` tooling are not staged.
4. Commit the current Stage 1 qualification and calculator-boundary foundation
   as a local checkpoint before implementing the remaining Stage 2 behavior.
5. Do not push, deploy, dispatch workflows, or alter credentials as part of the
   checkpoint.

### 2. Replace forecast-driven inputs

The current calculation boundary accepts a `ForecastInput`. Replace it with a
user scenario contract:

```ts
type UserScenarioInput = {
  crop: CropInput
  areaHa: number
  yieldTPerHa: number
  sellingPriceNgnPerKg: number
  priceRangeNgnPerKg?: { low: number; high: number }
  costsPerHa: Record<CostCategory, number>
}
```

`CostCategory` contains `land_preparation`, `seed`, `fertilizer`, `pesticide`,
`labour`, `irrigation`, `transport`, and `storage`. The UI keeps drafts as
strings so blank input is distinguishable from an explicit zero; parsing and
validation happen before `UserScenarioInput` is constructed.

The result contract contains production kilograms, total cost per hectare,
total cost, point revenue, point profit, and optional low/high profits. It must
include `inputSource: "user"` and must not contain model, WAPE, forecast status,
freshness, or inferred market-fallback fields.

### 3. Enforce complete-scenario behavior

- Area, yield, and point sale price must be finite and greater than zero.
- Every cost field is required, finite, and non-negative; explicit zero is
  allowed.
- Low/high prices are optional as a pair. If present, both must be finite and
  satisfy `0 <= low <= point <= high`.
- At least two crops must be selected and every selected crop must be valid
  before the batch becomes `ready`.
- While the batch is incomplete, show field/crop errors and suppress ranking,
  the winner card, recommendation wording, and print action. Do not silently
  drop an invalid crop and rank the remainder.
- Stable ties sort by canonical crop ID after point profit.

Calculations remain:

```text
production_kg = yield_t_per_ha * 1000 * area_ha
cost_per_ha = sum(eight user cost inputs)
total_cost = cost_per_ha * area_ha
revenue = selling_price_ngn_per_kg * production_kg
profit = revenue - total_cost
```

When a price range is supplied, apply its low and high prices to the same
production quantity and total cost. The range is a farmer scenario range, not a
confidence interval or forecast uncertainty interval.

### 4. Add versioned local persistence

Persist only a `SavedScenarioV1` draft:

```ts
type SavedScenarioV1 = {
  schemaVersion: 1
  savedAt: string
  areaHa: string
  selectedCropIds: string[]
  inputsByCropId: Record<string, {
    yieldTPerHa: string
    sellingPriceNgnPerKg: string
    lowPriceNgnPerKg?: string
    highPriceNgnPerKg?: string
    costsPerHa: Record<CostCategory, string>
  }>
}
```

- Save drafts locally after edits; never persist derived rankings or reports.
- Restore valid version-1 drafts after browser restart.
- On invalid JSON, invalid shape, or unknown schema version, ignore the stored
  value, start a blank scenario, and show a dismissible recovery notice.
- Provide a deliberate clear/reset action that removes the saved draft and
  returns the UI to its blank calculator-only state.

### 5. Quarantine inactive seed data

- Retain the existing `/data/v1` filenames so the public file contract and
  service worker do not break abruptly.
- Publish an explicit calculator-only snapshot with
  `stage_1_approved: false`, empty forecast/default arrays, warnings, and all
  catalog crops ineligible for automated recommendation.
- Bump the snapshot schema version and update Python validation so empty arrays
  are accepted only in calculator-only mode. Automated recommendation data in
  that mode must fail closed.
- Do not copy the qualification report or raw audit evidence into `public/data`.

### 6. Screen, print, and offline parity

- Render screen results and the printable report from the same immutable
  `ScenarioBatch` result object.
- Enable printing only for a `ready` batch. Include entered assumptions, units,
  generated time, all crop results, the ranking basis, and the statement that
  the figures are user scenarios rather than forecasts or guarantees.
- Add print CSS instead of a separate report calculation or PDF library; the
  browser print dialog provides paper/PDF output.
- Version the service-worker cache and verify an installed production build can
  reopen with networking disabled. The calculation path must not require the
  inactive seed JSON or any upstream request.

## Implementation waves

### Wave 1 — Foundation checkpoint and contract replacement

- Verify and checkpoint the current audit and calculation extraction.
- Replace forecast inputs with the user-scenario and batch-readiness contracts.
- Keep all arithmetic in NGN, hectares, tonnes/ha, and NGN/kg with conversions
  visible at the calculation boundary.

### Wave 2 — Deterministic calculation engine

Implement and test:

- total production cost per hectare and for the selected area;
- yield conversion from tonnes/ha to kilograms for revenue calculation;
- point revenue and net profit;
- lower/upper interval profit using the price interval only;
- deterministic ranking with stable tie-breaking;
- complete-batch readiness and deterministic error ordering;
- optional user scenario ranges with no forecast semantics.

### Wave 3 — UI integration

- Replace inline arithmetic with the pure calculation module.
- Keep the current visual layout unless a usability defect is found.
- Prevent incomplete selections from producing a recommendation.
- Require and label the user price, yield, and cost basis beside every result.
- Surface incomplete fields without ranking a partial shortlist.

### Wave 4 — Persistence and report parity

- Persist only draft user assumptions and selected crops locally.
- Restore a valid scenario after browser restart and offline reload.
- Generate the printable report from the same result object used on screen.
- Add schema-version and corrupt-data recovery behavior.

### Wave 5 — Review and verification

- Run unit tests, TypeScript checks, production build, and snapshot contract
  validation.
- Test with network access disabled and with the calculator-only static
  snapshot.
- Compare screen results and printable report values from golden fixtures.
- Record the evidence and stop for the Stage 2 gate review.

## Planned files

| File | Planned change |
|---|---|
| `src/main.tsx` | UI composition only; remove business arithmetic and hardcoded result logic |
| `src/calculations.ts` | New pure calculator functions and typed result contracts |
| `src/persistence.ts` | Version-1 draft parsing, storage, recovery, and reset behavior |
| `src/types.ts` | Shared user-scenario, result, error, and saved-draft contracts |
| `src/calculations.test.ts` | Golden arithmetic, validation, ranking, and fallback tests |
| `tests/e2e/*.spec.ts` | Browser input, persistence, print-parity, and offline-restart tests |
| `public/data/v1/*.json` | Explicit inactive calculator-only snapshot; no decision-driving values |
| `.github/workflows/ci.yml` | Typecheck, unit, build, and Chromium end-to-end gate |
| `docs/phases/02-offline-calculator.md` | Progress log and gate evidence |

## Acceptance gate

Stage 2 can move to Gate review only when all of the following are evidenced:

1. Pure calculation tests cover arithmetic, area scaling, ties, invalid or
   missing inputs, eight cost fields, and optional user price ranges.
2. Incomplete inputs cannot rank or produce a misleading recommendation.
3. The browser and printable report use the same calculated result object and
   agree on every displayed value.
4. Local persistence restores a valid scenario after a browser restart and
   safely handles an incompatible saved schema.
5. The app produces the same result with network access disabled.
6. `npm test`, `npm run typecheck`, `npm run build`, `npm run test:e2e`,
   `python pipeline/validate.py`, and the full Python regression suite pass.
7. No automated price, forecast, source-driven default, or partial-shortlist
   ranking is introduced.

## Explicit stop conditions

- Do not replace the calculator-only fallback with automated FEWS, World Bank,
  WFP, NBS, or seed values without a new qualification report that passes the
  complete Stage 1 technical and rights gate.
- Do not treat World Bank modeled OHLC values as recommendation-driving prices.
- Do not use NBS cost defaults as reproducible production evidence until their
  units and redistribution rights are resolved.
- Do not begin Stage 3, production static-data integration, deployment, or
  public launch under this plan.

## Progress log

### 2026-08-26 — planning prepared

- Stage 1 evidence was regenerated and documented.
- Stage 2 was initially `Not started`; this document now records the approved
  fallback-safe boundary work while production data integration remains
  blocked.
- A decision was requested between source remediation and the calculator-only
  fallback; it was resolved in favor of the fallback on 2026-08-27.

### 2026-08-26 — fallback-safe calculation boundary implemented

- Added `src/calculations.ts` with validated, deterministic scenario arithmetic,
  stable tie-breaking, interval profit, override handling, and explicit market
  fallback metadata.
- Replaced the inline `useMemo` arithmetic in `src/main.tsx` with the pure
  calculation boundary.
- Added four Node TypeScript regression tests in
  `src/calculations.test.ts`. Automated price data remains out of scope.

### 2026-08-27 — calculator-only outcome accepted and plan locked

- Stage 1 was closed with its fallback accepted; its technical gate remains
  failed and no source was approved for automated recommendations.
- The user selected strict user-entered values, versioned `localStorage`, and a
  verify-then-checkpoint workflow.
- This document is now the authoritative implementation and acceptance plan for
  the next session.

### 2026-08-27 — calculator-only implementation wave completed

- Replaced forecast/default-driven arithmetic with complete user-entered
  scenarios, eight required cost categories, optional price ranges, and stable
  profit ranking.
- Added version-1 local draft persistence, corrupt-state recovery, clear/reset,
  shared screen/print result rendering, and calculator-only copy.
- Quarantined inactive snapshot forecasts and defaults; all catalog crops are
  ineligible for automated recommendation and the service-worker cache was
  versioned.
- Unit and Python snapshot checks pass. Typecheck/build remain pending because
  the local npm installation is incomplete and npm cache restoration hit a
  Windows EPERM error.

## Current handoff — 2026-08-27

### Completed

- Implemented the user-scenario contract in `src/calculations.ts`.
- Required all eight cost categories while preserving blank-versus-zero input
  semantics in the UI draft state.
- Implemented complete-batch readiness, deterministic validation, optional
  price ranges, and stable ranking.
- Added version-1 local draft persistence, corrupt-state recovery, and reset in
  `src/persistence.ts`.
- Rendered screen and print views from the same ready `ScenarioBatch` object.
- Published an explicitly calculator-only snapshot and versioned the service
  worker cache.
- Added `playwright.config.ts` and `tests/e2e/calculator.spec.ts` covering
  incomplete-input suppression, complete ranking, reload restoration, and
  deliberate reset.

### Evidence

| Check | Result |
|---|---|
| `npm test` | Passed — 3 tests at this checkpoint; current suite has 4 |
| `python pipeline\\validate.py` | Passed — calculator-only snapshot |
| `python -m unittest discover -s tests -v` | Passed — 19 tests |
| `git diff --check` | Passed |
| `npm run typecheck` | Pending — incomplete local TypeScript installation |
| `npm run build` | Pending — incomplete local Vite installation |
| `npm run test:e2e` | Implemented but pending toolchain/browser installation |

### Next phase

Finish verification and prepare the Stage 2 gate review. Restore npm tooling and
retain `package-lock.json`, install the Chromium runtime, run the new browser
coverage plus all acceptance commands, and document the evidence and commit
reference. Stage 2
must remain `In progress` until typecheck, production build, browser offline
restart, and print-parity evidence are available. Automated data work remains
prohibited until a future qualification report passes the full Stage 1
technical and rights gate.

### 2026-08-27 — verification execution update

- Re-ran the direct Node calculator suite: 3 tests passed at this checkpoint;
  a fourth regression test was added later.
- Re-ran `python pipeline\\validate.py`: calculator-only snapshot passed.
- Attempted npm restoration with workspace-local cache and escalated
  permissions. npm still failed to materialize `vite`, `tsc`, or a lockfile;
  the environment rewrote the cache path and returned a Windows path/permission
  error. `npm run typecheck` and `npm run build` therefore remain blocked before
  application compilation.
- The new Playwright suite is present but cannot execute until the npm toolchain
  and Chromium browser runtime are available.

Stage 2 remains `In progress`; this evidence is not a gate approval.

### 2026-09-04 — calculator-only checkpoint

- Commit `2a40c62` records the calculator foundation: blank reset clears saved
  state, calculation results retain all scenario assumptions, and print output
  includes the shared area, yield, point/range prices, all eight costs, ranking
  basis, generated time, and disclaimer.
- `npm test` passed all 4 tests; Python validation passed; all 26 Python tests
  passed; `git diff --check` passed.
- `npm run typecheck` remains blocked because `tsc` is not installed. npm
  install attempts (including project-cache and offline attempts) did not
  produce a lockfile or local Vite/TypeScript/Playwright binaries. Stage 2 is
  still `In progress`, pending clean dependency materialization and browser
  evidence.

### 2026-08-28 — npm permissions isolated and restart handoff consolidated

- Confirmed Node `24.15.0`, npm `11.16.0`, and the project-scoped cache at
  `D:\Crop Value Predictor App\.npm-cache-repair`.
- Reproduced the old user-profile cache failure as `EPERM` under
  `_cacache\tmp`, then granted the sandbox modify access to the dedicated
  project cache. `npm view react version` now succeeds from that cache.
- Verbose install attempts continued receiving successful registry responses
  for React, Playwright, Babel, esbuild, Rollup, and platform packages. They
  were stopped before completion, so `package-lock.json`, `vite`, `tsc`, and
  Playwright remain absent. The current blocker is incomplete dependency
  materialization, not a reproduced cache-permission error.
- Re-ran `npm test`: all 4 calculator tests passed. Typecheck, build, Chromium,
  and browser evidence remain pending.
- Audited the existing Playwright suite. It has 3 scenarios but still lacks
  optional ranges, corrupt/unknown saved-state recovery, screen/print parity,
  and production offline restart. Its web-server command also starts Vite dev
  mode on the wrong port for the configured base URL.
- Consolidated the operational restart procedure in `SESSION_HANDOFF.md` and
  retained `NPM_FIX_HANDOFF.md` as the detailed toolchain appendix.

Stage 2 remains `In progress`. No push, workflow dispatch, deployment, source
remediation, or Stage 3 work was performed.

### 2026-08-28 — documented plan execution attempt

- Confirmed Node `v24.15.0`, npm `11.16.0`, project cache configuration, and
  the dirty-worktree safety boundary.
- `npm test` passed (4 tests); `python pipeline\\validate.py` passed; the full
  Python regression suite passed (19 tests); `git diff --check` passed.
- Added a production-build/preview Playwright web server on `127.0.0.1:4173`
  and updated CI to Node 24, `npm ci`, typecheck, build, Chromium installation,
  and Playwright execution.
- npm registry access is intermittent. A lockfile was generated, but `npm ci`
  currently fails with `Invalid Version` from npm's dependency tree, and the
  local `vite`, `tsc`, and Playwright binaries were not materialized. Typecheck,
  production build, Chromium, and browser evidence therefore remain pending.
- Stage 2 remains `In progress`; no checkpoint commit, push, dispatch,
  deployment, or Stage 3 work was performed.

### 2026-08-28 — follow-up recovery attempt

- Retried lockfile generation with npm 10/11 and a clean temporary cache.
- `npm ci` rejected the generated lockfile as out of sync; the unvalidated
  lockfile was removed rather than retained as release evidence.
- A regular install did not materialize Vite, TypeScript, Playwright, or
  Chromium before timing out. The project `.npmrc` was restored.
- Reconfirmed 4 Node tests, 19 Python tests, snapshot validation, and
  `git diff --check` passing. Stage 2 remains `In progress`.

### 2026-09-04 — checkpoint artifacts and lock recovery

Follow-up commit `516e3d1` records the remaining CI, snapshot, service-worker,
Playwright, persistence, and calculator-test artifacts required by the
checkpoint. Lock recovery used unique workspace `%TEMP%\\crop-value-lock-20260904-1`
with only `package.json`. The cache-path invocation failed with npm `ENOENT`
while resolving the space-containing path; the `npm_config_cache` retry was
stopped after 60 seconds without producing a lockfile. No unvalidated lockfile
was copied into the repository. Typecheck, build, Chromium installation, and
E2E remain pending; Stage 2 is `In progress`.

### 2026-09-04 — validated lockfile checkpoint

Commit `f3e0551` adds the lockfile with SHA-256
`0c1fc59fe68d10a896933129ffada842baa4437e769b501661f6009f97eeb749`.
`npm ci` succeeded in a clean detached clone after an escalated retry for
`ECONNRESET`; `npm ls --depth=0`, `npm test` (4), `npm run typecheck`, and
Python tests (26) passed. `npm run build` failed in the temporary clone because
esbuild was denied access while resolving `vite.config.ts`; E2E and Chromium
were not run. Stage 2 remains `In progress`, pending build/browser evidence.
