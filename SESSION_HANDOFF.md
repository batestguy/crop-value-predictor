# Next-session handoff

Updated: 2026-09-09
Repository: `D:\Crop Value Predictor App`
Last implementation commit: `7683fb1 feat: add modeled price context lane`
Branch at handoff: `stage1-adapter-fix`

## Start here

Read this file, then inspect `git status --short` and `git log -3`. The working
tree should contain only the pre-existing one-line `debug.log` change; it was
deliberately left uncommitted. Do not discard it without user approval.

The latest commit is the trusted implementation baseline for this session. Do
not redo the academic review or World Bank adapter work unless a validation
failure identifies a concrete defect.

## Current project status

The project is a browser-first static React/Vite PWA. A simple equal-stage
estimate is 4 of 7 stages approved, or about 57% complete. The remaining 43%
is not routine polish: observed-price approval is the dependency for the
automated pipeline and forecasting stages.

| Stage | Status | Meaning |
| --- | --- | --- |
| 0. Baseline and tracking | Approved | Reproducible project baseline |
| 1. Source and feasibility audit | In progress; observed gate blocked | FEWS/WFP remediation and unchanged source gates remain unresolved |
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

## Next action: choose one of two explicitly separate paths

### Path A: keep the modeled context lane

Complete a focused product/rights review of the World Bank modeled artifact.
Confirm that the warning, attribution, source hash, crop-form mappings, and
editable-context wording are acceptable. If approved, record that decision in
the Stage 1 evidence log without changing `stage_1_approved`.

### Path B: make actual observed Stage 1 progress

Run a fresh immutable FEWS/WFP or other observed-price audit. The existing
thresholds remain unchanged:

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

Expected current results are: 40 Python tests passing, 4 calculator tests
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
