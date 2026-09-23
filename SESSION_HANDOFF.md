# Next-session handoff

Updated: 2026-09-23
Repository: `D:\Crop Value Predictor App`
This handoff records the completed local Phase 3A implementation slice, hosted
Pages Function adapter, and public deployment of the bounded research route. The pre-existing
`debug.log` change remains uncommitted. The external Tavily key remains outside
the repository and is never committed.
Branch at handoff: `main` (production deployment `2c672af6`, commit `37dfec2`)

## Live-link incident — resolved 2026-09-23

### Root cause

Cloudflare Pages answers `/index.html` with `308 → /`. The service worker
precached `/index.html`, stored the redirected response, and served it for
navigations. Chromium-based browsers reject a redirected response for a
navigation, so every visit after the first showed `ERR_FAILED`; private windows
worked only because they start without a service worker. The local e2e server
did not redirect, so tests never saw it.

### Fix (PR #12, merged as `37dfec2`)

- `scripts/write-precache.mjs` precaches the app shell at the base URL instead
  of `index.html`.
- `public/sw.js` uses the base URL as the navigation key, rebuilds any
  redirected response before caching or serving it, and calls `skipWaiting()`
  on install so clients stuck on the old worker recover on their next visit.
- `scripts/serve-preview.mjs` now mirrors the Pages `index.html` redirect. With
  the old worker six e2e tests fail with `ERR_FAILED`; with the fix all pass.
- README links point to production `https://crop-value-predictor.pages.dev/`.
  The pinned preview `a5b50794…pages.dev` is a fixed build that still ships the
  broken worker and must not be linked again.
- PR #11 (incognito warning) was closed as superseded.

### Deployment and verification

- Deployed with `wrangler pages deploy --branch main` → deployment `2c672af6`.
  Merging to `main` does not deploy; CI (`validate`) only checks.
- Checks: `npm test` 4 passed, typecheck clean, build ok, `test:e2e` 22 passed
  and 1 skipped, CI `validate` passed.
- Production Playwright check: three reloads under service-worker control
  succeeded on desktop and an emulated Pixel 7. The user confirmed the site
  opens in their normal Brave window.
- `fieldmargin.is-a.dev` is still unregistered (it redirects to
  `is-a.dev/available`). Do not link it until registration and HTTPS are
  verified.

### Next session

1. Preserve the pre-existing `debug.log` change and the untracked
   `.playwright-cli/` and `output/` artifacts unless the user asks for cleanup.
2. The local `main` branch still holds superseded commits (`8d02ea8`, `2d0f5e6`,
   `dca5ddd`). Their handoff content is carried forward here; resync local
   `main` with `origin/main` only with the user's approval.
3. Do not put Tavily or GitHub credentials in the repository, deployment files,
   command output, or handoff.

## Release slice update — 2026-09-13

The JJMB visual release slice is implemented locally. It adds a local
green-white-green Nigeria flag watermark, a compact accessible JJMB About card,
and responsive field-notebook styling. The watermark is decorative, offline,
non-interactive, hidden from assistive technology, and excluded from print.
The interactive Nigeria state-map proposal remains deferred.

The custom-crop Tavily path was verified with a real keyed smoke test for
`Soybean` / `dry grain` in Bauchi. It returned a web fallback estimate of
`NGN 150/kg`, `1.2 t/ha`, and eight sources. The key was read from its external
path only and was not printed, stored, or committed. The browser test also
confirms that Soybean and Carrot requests carry their crop names, forms, IDs,
state, and `researchAll: true`.

The initial static-only release was deployed successfully at 12:44 WAT using commit
`56e439d`. Cloudflare returned the deployment URL
`https://b5bbe675.crop-value-predictor.pages.dev`; the main URL
`https://crop-value-predictor.pages.dev/` also returned HTTP 200. Public
Playwright verified the JJMB card, custom-crop UI, and local flag asset. The
hosted research Function was excluded from that initial upload.

## Hosted Tavily deployment update — 2026-09-13

The hosted Pages Function is now deployed to the `main` production branch at
`https://crop-value-predictor.pages.dev/`. Cloudflare deployment ID:
`16323e9b` (source commit `5048a26`). `TAVILY_API_KEY` is configured only as an
encrypted production secret; the key was read from its external path and was
never printed, committed, or placed in browser code.

Public Playwright smoke verification confirmed:

- `GET /api/price-research` returns the Function's expected `405`;
- a custom `Soybean` / `dry grain` request for Bauchi returns HTTP `200`;
- the parsed estimate is `NGN 110/kg`, with `NGN 100-120/kg` bounds;
- natural-language yield parsing returns `2.5 t/ha`; and
- eight HTTPS source links are returned.

The result remains low-confidence research context. It does not change the
scenario until the farmer clicks **Use this estimate**. The hosted route does
not publish a snapshot, reopen Stage 1, or enable automatic rankings/defaults.

## Latest handoff update — 2026-09-13

### Completed in this session

Custom crop support is implemented and committed. A farmer can enter any crop
name and product form, add it to the shortlist, and compare it using the same
calculator fields as the built-in crops. Custom crop names, forms, inputs, and
confirmed research provenance persist in the local browser draft.

For a custom crop, the local research adapter sends the crop name, product form,
state, and retail basis to Tavily only after the farmer clicks the research
button. The bounded request asks Tavily for a practical multi-source average
and clearly labelled values for:

- average selling price in NGN/kg, plus optional low/high bounds;
- yield in tonnes/hectare; and
- any available cost categories in NGN/hectare: land preparation, seed,
  fertilizer, pesticide, labour, irrigation, transport, and storage.

Returned values are shown as low-confidence, editable starting values. They do
not change the scenario until the farmer explicitly confirms them. Missing
categories stay blank for manual entry. A custom crop cannot rank until all
required calculator fields are complete.

### Key implementation commits

- `ba500e8` — custom crop persistence, UI, local Vite route, Tavily request
  fields, returned yield/cost values, and browser coverage.
- `285201d` — explicit Tavily low/high price marker parsing.
- `a25d8fd` — natural-language Tavily cost extraction for answers such as
  “NGN 50,000 for land preparation”.

### Real local Tavily smoke test

The keyed local Vite endpoint was tested without exposing or moving the key.
For `custom:soybean-dry-grain` in Bauchi, Tavily returned eight source links
and the adapter produced:

- price: `NGN 100/kg`;
- yield: `1.5 t/ha`;
- land preparation: `NGN 50,000/ha`; and
- seed: `NGN 30,000/ha`.

The response was successfully parsed after the natural-language cost fix.
The result is still low-confidence research context and requires farmer
confirmation before use.

### Current deployment boundary

The public site at `https://crop-value-predictor.pages.dev/` includes the
calculator and the optional hosted Pages Function. The Function uses the
encrypted production `TAVILY_API_KEY` secret and supports custom crop/form
requests. It is bounded, low-confidence research context only; results require
explicit farmer confirmation and never become the observed-price snapshot.

Never place the Tavily key in the repository, browser bundle, command output,
or deployment files. The existing
`debug.log` modification is pre-existing and remains intentionally
uncommitted.

### Validation evidence

- `npm.cmd test` — 4 passed.
- `npm.cmd run typecheck` — passed.
- `npm.cmd run build` — passed.
- `python -m unittest discover -s tests -v` — 61 passed.
- `npm.cmd run test:e2e` — 19 passed, 1 intentional base-path skip.
- `npx.cmd tsc --noEmit functions/api/price-research.ts --target es2020 --module esnext --lib es2020,dom --skipLibCheck` — passed.
- Public Playwright smoke — Function `GET` 405, custom-crop `POST` 200,
  `NGN 110/kg` estimate, `NGN 100-120/kg` range, `2.5 t/ha`, and 8 sources.
- `pipeline\agent_preflight.ps1` — passed with an external temporary token
  path because the configured GitHub token path was access-denied to the
  sandbox; no token was read or printed.

### Next session: most logical next action

1. Read this handoff and run `git status --short`.
2. Run `npm.cmd run dev` from `D:\Crop Value Predictor App`.
3. Add a test custom crop, enter a Nigerian state, and click **Find all starting
   values**. The local keyed smoke test has already passed; use the existing
   mocked Playwright test for repeatable regression coverage.
4. Do not deploy the hosted research Function or upload a key until the 522
   runtime issue, privacy/rate-limit controls, and hosted smoke test are
   explicitly reviewed.
5. The interactive Nigeria map remains a separate proposal; the current
   release uses only the local Nigeria flag watermark.

## Current disposition — 2026-09-13

The reviewed static-export implementation was committed as `cbb9e3c` and
pushed to `stage1-adapter-fix`. The single authorized evidence-only canary was
run as [34731386407](https://github.com/batestguy/crop-value-predictor/actions/runs/34731386407)
with cutoff `2026-08` and a 30-second bound. It failed closed because the
official Nigeria FEWS page exposed zero matching CSV links:
`expected exactly one official Nigeria FEWS CSV link, found 0`.

Phase 1 is now **Closed — fallback accepted**, not approved. The artifact is
`audit-output-fews-canary-20260913-34731386407`; no raw FEWS file was accepted,
no public snapshot changed, and no promotion occurred. Stages 3 and 4 remain
blocked. Do not repeat the old API path or the same static canary. Reopen Stage
1 only after a materially changed official access path or provider-supplied
export URL, followed by the complete unchanged gates and two independent
reviews.

## Start here

Read this file, then inspect `git status --short` and `git log -3`. The working
tree contains the documented implementation and validation changes from this
session, plus the pre-existing one-line `debug.log` change. The debug change
was deliberately left uncommitted; do not discard it without user approval.

The latest commit is the trusted implementation baseline for this session. Do
not redo the academic review or World Bank adapter work unless a validation
failure identifies a concrete defect.

The latest user request is documented in
[`docs/proposals/crop-expansion-and-nigeria-map.md`](./docs/proposals/crop-expansion-and-nigeria-map.md):
custom **Other crop** scenarios with manual inputs, plus a local accessible
Nigeria map for state selection/orientation and a more distinctive field-
notebook visual direction. The custom-crop slice is now implemented locally;
the Nigeria map remains a separate proposal.

## Current handoff — settled Stage 1 and completed local Phase 3A slice

Stage 1 is settled as **Closed — fallback accepted**, not approved. The latest
authorized static canary failed closed because the official Nigeria FEWS page
exposed zero matching CSV links. Do not repeat the old API path or the same
static canary. Reopen Stage 1 only after a materially changed official access
path or provider-supplied export URL, followed by the unchanged qualification,
rights, review, and approval gates.

Stage 2 is approved for complete farmer-entered offline scenarios. The user
authorized the local Phase 3A implementation slice and the bounded public
deployment. The Vite development server now has a guarded same-origin research
route, the Python helper reads the retained raw CSV first and uses Tavily only
for a missing-location fallback, and custom crops can request starting price,
yield, and available cost categories. The UI requires review and explicit
confirmation before changing a scenario. The hosted Pages Function is live at
`https://crop-value-predictor.pages.dev/` with its secret held server-side.
Formal source allowlisting, privacy, and rate-limit hardening remain open for
any expansion; Phase 3A does not reopen Stage 1 or the automated pipeline.

## Current project status

The project is a browser-first static React/Vite PWA. A simple equal-stage
estimate is 4 of 7 stages approved, or about 57% complete. The remaining 43%
is not routine polish: observed-price approval is the dependency for the
automated pipeline and forecasting stages.

| Stage | Status | Meaning |
| --- | --- | --- |
| 0. Baseline and tracking | Approved | Reproducible project baseline |
| 1. Source and feasibility audit | Closed — fallback accepted; observed gate unapproved | Failed API/static-export procedures are not active; reopen only with a materially changed official access path and unchanged gates |
| 2. Offline decision calculator | Approved | Manual-input calculator works offline |
| 3A. Optional online research assist | Bounded hosted lane deployed; broader hardening open | Multi-source internet aggregate context with explicit confirmation; see `docs/phases/03-online-research-assist.md` |
| 3. Automated data pipeline | Blocked | Cannot proceed as an observed-price pipeline until Stage 1 passes |
| 4. Forecasting and validation | Blocked | Depends on qualified Stage 1/Stage 3 data |
| 5. Web deployment and farmer readiness | Approved — calculator and optional research route live | Public site is live; online values remain editable context only |
| 6. Literature-informed calculator readiness | Approved | Academic evidence review approved; participant validation remains absent |

## Critical truth

`public/data/v1/manifest.json` intentionally has:

- `stage_1_approved: false`
- `modeled_estimates_enabled: true`
- `modeled_estimate_snapshot_id: world-bank-modeled-2026-09-09`

The World Bank artifact is an optional, editable modeled-estimate context lane.
It is not an observed retail price, wholesale price, farmer selling price,
forecast, or farmer validation result. Never relabel it or use it to claim that
Stage 1 passed.

## What the latest commit delivered

- Repaired World Bank bulk discovery and ZIP validation for the current official
  Nigeria RTFP file.
- Added `pipeline/world_bank_modeled.py` with source-aligned product forms,
  explicit component-mass conversion, modeled provenance, and fail-closed
  normalization.
- Published `public/data/v1/modeled_price_suggestions.json` containing 438
  suggestions across 6 crop forms and 73 markets.
- Added separate manifest, quality, loader, persistence, UI-warning, and
  snapshot-contract support for the modeled lane.
- Added World Bank source-adapter and modeled-lane tests.
- Updated the Stage 1 alternatives assessment, implementation plan, README,
  progress record, and this handoff.
- Preserved the participant protocol and session kit as deferred future work.

## Next action: choose the next separately authorized path

### Path A: keep the modeled context lane

Complete a focused product/rights review of the World Bank modeled artifact.
Confirm that the warning, attribution, source hash, crop-form mappings, and
editable-context wording are acceptable. If approved, record that decision in
the Stage 1 evidence log without changing `stage_1_approved`.

### Path B: maintain the bounded Phase 3A hosted lane

The optional hybrid lane is defined in
[`docs/phases/03-online-research-assist.md`](./docs/phases/03-online-research-assist.md).
Gate A is authorized and the bounded hosted route is deployed. The lane uses
retained raw data first, falls back to Tavily only when local evidence is absent,
keeps the key server-side, shows evidence and warnings, and requires explicit
confirmation before changing a scenario. The remaining work is a focused
review of source rights/allowlisting, Tavily quotas and terms, privacy/rate
limits, deterministic candidate validation, and any future expansion. The lane
returns a transparent aggregate for user confirmation and does not change Stage
1 or automatic ranking.

### What is next, in order

1. Keep using the local app for manual and confirmed research-assisted
   scenarios. Start it with the external key loaded only into the server
   process; do not put the key in the repository or browser.
2. Continue the hosted Gate A/D hardening review: source/terms, free quota,
   privacy, rate-limit, timeout, malformed/no-evidence behavior, and browser
   smoke test.
3. Do not promote online results into `public/data`, enable automatic price
   defaults, or start Stage 3/4 as part of this path.

### Stage 1 reopening boundary

Do not repeat the failed FEWS API/static-export procedure. Reopen Stage 1 only
after a materially changed official access path or provider-supplied export URL.
The unchanged thresholds would then apply:

- at least five crop forms;
- at least 36 months and at least 80% completeness in the latest 36 months;
- latest observation within 75 days;
- at least three comparable markets for national medians;
- at least six forecast-origin windows;
- explicit units, transaction types, mappings, rights, and source checksums;
- two independent review passes and explicit user approval.

Do not stitch FEWS, WFP, FAO, NBS, or modeled World Bank rows together to create
an artificial pass. A successful technical report still stops at Gate review
until the user explicitly approves it.

The 2026-09-10 evidence is in
`audit-output-remediation-2026-09-10`. It contains verified World Bank,
WFP/HDX, FAOSTAT, and NBS artifacts, but qualification returned
`calculator_only_fallback` with zero eligible series and zero selected crops.
No public artifact changed.

The prior authorized cloud FEWS API investigation is complete. Canaries
`34434267144` and `34434497826` produced no usable FEWS evidence (empty August
window and June HTTP 403), and full audit
`34434760861` failed closed on FEWS HTTP 403. Its downloaded immutable artifact
is `audit-output-fews-cloud-full-20260910-34434760861`; qualification remains
`calculator_only_fallback` with `stage_1_approved: false`. It predates the
static-export implementation and must not be treated as the new static result.

Follow the ordered sequence in [`docs/next-actions.md`](./docs/next-actions.md).
The modeled-context boundary and explicit online confirmation flow are covered
by clean browser-suite evidence: 19 tests passed with one intentional base-path
skip. Playwright also completed a live local Bauchi lookup and confirmation.
Do not repeat local FEWS retrieval; further observed-source work requires an
explicitly authorized cloud retrieval origin.

## Recommended validation commands

Use the real Windows npm executable, `npm.cmd`, because the `npm` shim has
previously returned success without running the requested script:

```powershell
python pipeline/source_audit.py --cutoff-month 2026-08
python pipeline/validate.py
python -m unittest discover -s tests -v
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
git diff --check
```

Expected baseline results are: 60 Python tests passing, 4 calculator tests
passing, typecheck passing, production build passing, and the Chromium suite
passing with one intentional base-path skip in the existing environment.

## Important boundaries

- Do not deploy, publish, push, dispatch workflows, or change hosting without
  explicit authorization.
- Do not start participant recruitment or contact farmers. Academic evidence
  does not substitute for direct participant validation.
- Do not enable observed automated prices, forecasting, Stage 3, or Stage 4
  based on the modeled lane.
- Keep Android hardware validation optional and non-blocking; the active product
  target is the web PWA.
- Preserve `audit-output-*` evidence directories and their checksums.
- Leave credentials, npm caches, workstation configuration, and unrelated
  artifacts untouched.

## Key files

- `PROJECT_PROGRESS.md` - stage dashboard and dated evidence log.
- `IMPLEMENTATION_PLAN.md` - roadmap, gates, and product boundaries.
- `docs/phases/01-source-audit.md` - source-gate evidence and remediation log.
- `docs/phases/03-online-research-assist.md` - online research contract,
  local implementation evidence, and hosted-gate boundary.
- `docs/stage1-source-alternatives.md` - observed versus modeled alternatives.
- `docs/academic-evidence-review.md` - literature review protocol and claims.
- `config/sources.json` - source contracts and retrieval metadata.
- `pipeline/source_audit.py` - source discovery, retrieval, and audit logic.
- `pipeline/world_bank_modeled.py` - separate modeled-estimate builder.
- `public/data/v1/manifest.json` - release flags and artifact contract.
- `public/data/v1/modeled_price_suggestions.json` - modeled context artifact.
- `src/priceSuggestions.ts` - same-origin artifact validation and loading.
- `src/main.tsx` - calculator UI, modeled-context warning, and confirmed
  research-assist flow.
- `src/onlineEstimate.ts` - same-origin research client and response checks.
- `vite.config.ts` - local-only guarded research endpoint.
- `pipeline/online_estimate.py` - raw-data estimator and bounded Tavily fallback.

## Final handoff rule

The next agent should report the evidence and gate state first, then make only
the smallest change needed for the selected path. The project is not
farmer-validated, not observed-price approved, and not forecast-approved. The
calculator-only static site is deployed; online retrieval remains disabled.

## Historical FEWS static-export handoff — superseded

The following is retained as dated evidence only. It must not be used as an
active instruction to dispatch or repeat the failed canary; the current
disposition and next-path rules above control.

Evidence from this session:

- Static discovery/download/schema/atomicity/host/bot/fallback tests pass; the
  full Python suite is 47 passing tests.
- `python pipeline/source_audit.py` validates the six-source register.
- `python pipeline/validate.py` passes the calculator-only snapshot.
- `npm.cmd test`, `npm.cmd run typecheck`, and `npm.cmd run build` pass.
- `npm.cmd run test:e2e` passes 19 tests with one intentional base-path skip.
- Workflow YAML parses and `git diff --check` passes.
- A local static canary with a one-second bound failed closed with
  `The read operation timed out`; its temporary manifest recorded the exact
  reason and no raw FEWS file was accepted.
- No `public/data/v1` artifact changed. `stage_1_approved` remains false.

Next session sequence:

1. Inspect `git status --short` and preserve the existing unrelated dirty files,
   especially `debug.log` and prior documentation changes.
2. Review the FEWS static diff and rerun focused Python tests if needed.
3. With explicit workflow-dispatch authorization, run the manual **FEWS static
   export canary (evidence only)** workflow using cutoff `2026-08` and a bounded
   timeout. Evidence must upload even when discovery or download fails.
4. Download the resulting artifact only with the external GitHub token and use
   `pipeline/resume_stage1.ps1 -RunId <run-id>` to verify the artifact, static
   manifest, hash/size, and qualification output.
5. Run two independent reviews of the immutable result. Stop at Gate review;
   do not promote data, change `public/data/v1`, enable automated defaults, or
   start Stage 3/forecasting.

If the cloud static export is unavailable, retain the precise fail-closed
reason and the calculator-only product. Do not bypass anti-bot controls, use a
mirror, relax schema checks, retry the blocked API indefinitely, or stitch API,
WFP, FAO, NBS, and modeled World Bank rows together.
