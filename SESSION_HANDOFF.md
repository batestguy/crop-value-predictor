# Next-session handoff

Updated: 2026-09-10
Repository: `D:\Crop Value Predictor App`
Last implementation commit: `7683fb1 feat: add modeled price context lane`; the
FEWS static-export implementation is currently uncommitted in the working tree.
Branch at handoff: `stage1-adapter-fix`

## Start here

Read this file, then inspect `git status --short` and `git log -3`. The working
tree contains the documented implementation and validation changes from this
session, plus the pre-existing one-line `debug.log` change. The debug change
was deliberately left uncommitted; do not discard it without user approval.

The latest commit is the trusted implementation baseline for this session. Do
not redo the academic review or World Bank adapter work unless a validation
failure identifies a concrete defect.

## Current handoff — FEWS static export implementation

This session settled the FEWS retrieval design in code. The configured primary
path is now the official static CSV export discovered from the Nigeria FEWS
page. The documented v3 API adapter remains available only through the
explicit diagnostic canary and is not an automatic fallback or merge source.

Implementation is in `pipeline/source_audit.py`. It uses the standard-library
HTML parser, requires exactly one labeled official CSV link, permits only
configured FEWS-owned HTTPS hosts, rejects unknown-host redirects, empty/HTML/
JavaScript bot responses, and atomically replaces `raw/fews-net.csv` only after
explicit schema and Nigeria-row validation. Successful manifest records include
the discovery page, resolved export URL, filename, content type, cutoff month,
row count, byte count, and SHA-256.

The source contract is in `config/sources.json`; the API contract is under
`diagnostic_retrieval`. The manual workflow is
`.github/workflows/fews-canary.yml`. Artifact recovery now requires an explicit
run ID and verifies the current `raw/fews-net.csv` layout in
`pipeline/resume_stage1.ps1`. Operational details are in
`docs/agent-stage1-automation.md` and `docs/upstream-fallback-runbook.md`.

## Current project status

The project is a browser-first static React/Vite PWA. A simple equal-stage
estimate is 4 of 7 stages approved, or about 57% complete. The remaining 43%
is not routine polish: observed-price approval is the dependency for the
automated pipeline and forecasting stages.

| Stage | Status | Meaning |
| --- | --- | --- |
| 0. Baseline and tracking | Approved | Reproducible project baseline |
| 1. Source and feasibility audit | In progress; observed gate blocked | Static FEWS adapter is implemented; authorized cloud canary and unchanged source gates remain pending |
| 2. Offline decision calculator | Approved | Manual-input calculator works offline |
| 3. Automated data pipeline | Blocked | Cannot proceed as an observed-price pipeline until Stage 1 passes |
| 4. Forecasting and validation | Blocked | Depends on qualified Stage 1/Stage 3 data |
| 5. Web deployment and farmer readiness | Approved | Browser readiness approved; deployment is separately authorized |
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

### Path B: make actual observed Stage 1 progress

The API-based FEWS/WFP audit was run on 2026-09-10 and failed closed on FEWS
HTTP 403 after bounded retries. The static-export adapter is now implemented,
so the next observed Stage 1 action is an explicitly authorized cloud static
canary. If that export is unavailable, retain the calculator-only fallback.
The existing thresholds remain unchanged:

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
The modeled-context boundary is now covered by clean browser-suite evidence:
17 tests passed with one intentional base-path skip. Do not repeat local FEWS
retrieval; further observed-source work requires an explicitly authorized
cloud retrieval origin.

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

Expected current results are: 47 Python tests passing, 4 calculator tests
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
- `docs/stage1-source-alternatives.md` - observed versus modeled alternatives.
- `docs/academic-evidence-review.md` - literature review protocol and claims.
- `config/sources.json` - source contracts and retrieval metadata.
- `pipeline/source_audit.py` - source discovery, retrieval, and audit logic.
- `pipeline/world_bank_modeled.py` - separate modeled-estimate builder.
- `public/data/v1/manifest.json` - release flags and artifact contract.
- `public/data/v1/modeled_price_suggestions.json` - modeled context artifact.
- `src/priceSuggestions.ts` - same-origin artifact validation and loading.
- `src/main.tsx` - calculator UI and modeled-context warning.

## Final handoff rule

The next agent should report the evidence and gate state first, then make only
the smallest change needed for the selected path. The project is not
farmer-validated, not observed-price approved, not forecast-approved, and not
deployed.

## Session handoff — 2026-09-10 FEWS static export

Evidence from this session:

- Static discovery/download/schema/atomicity/host/bot/fallback tests pass; the
  full Python suite is 47 passing tests.
- `python pipeline/source_audit.py` validates the six-source register.
- `python pipeline/validate.py` passes the calculator-only snapshot.
- `npm.cmd test`, `npm.cmd run typecheck`, and `npm.cmd run build` pass.
- `npm.cmd run test:e2e` passes 17 tests with one intentional base-path skip.
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
