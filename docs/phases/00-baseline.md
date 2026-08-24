# Stage 0 — Baseline and Tracking Setup

**Status:** Gate review  
**Started:** 2026-08-24  
**Evidence owner:** implementation agent  
**Approval owner:** project user

## Objective

Create a reliable progress system and record the repository’s actual starting
point before changing the seed implementation.

## Completed work

- Added [`PROJECT_PROGRESS.md`](../../PROJECT_PROGRESS.md) as the master dashboard.
- Added one evidence record for each approved delivery stage.
- Linked the dashboard and phase records from `README.md`.
- Defined the cloud-compute boundary and repository data classification in
  [`cloud-compute.md`](../cloud-compute.md).
- Hardened CI and scheduled refresh workflows for clean cloud runners with
  read-only permissions and retained validation artifacts.
- Preserved the existing `/data/v1` runtime contract and application behavior.

## Baseline evidence

| Check | Result |
|---|---|
| `python pipeline/validate.py` | Passed: `pilot-seed-2026-08-24`, 5 crops, 5 forecast records |
| `python -m unittest discover -s tests` | Passed: 2 tests |
| `npm test` | Passed |
| `npm run build` | Passed |
| Git worktree before documentation | Clean; one baseline commit |
| Git remote | `https://github.com/batestguy/crop-value-predictor`, `main` tracking `origin/main` |
| CI workflow | Cloud validation/build workflow with read-only permissions |
| Refresh workflow | Scheduled/manual cloud validation with 30-day artifact retention; source adapters explicitly deferred until Stage 1 |
| Cloud CI run | [32685906128](https://github.com/batestguy/crop-value-predictor/actions/runs/32685906128) passed on `e201edf` |
| Cloud refresh run | [32685952971](https://github.com/batestguy/crop-value-predictor/actions/runs/32685952971) passed; artifact expires 2026-09-23 |

## Known limitations recorded

- `src/main.tsx` contains hardcoded crop, forecast, yield, and cost seed data.
- `public/data/v1` is explicitly labeled a pilot seed snapshot.
- The service worker caches the shell and JSON but does not yet implement
  manifest checksum verification or atomic IndexedDB promotion.
- Source auditing, repeatable ingestion, forecasting, and field validation are
  not complete.
- Existing prototype behavior must not be described as a passed Stage 2 or
  Stage 5 gate.
- GitHub Actions is the authoritative environment for ingestion, ML, validation,
  tests, and builds; local execution is not gate evidence.

## Gate checklist

- [x] Master tracker exists and describes the review-gated workflow.
- [x] All seven phase records exist and link to the approved plan.
- [x] Current test/build evidence is recorded.
- [x] Known seed limitations and external deployment dependency are recorded.
- [x] Cloud compute boundary and data storage rules are documented.
- [x] Public repository exists, `main` is pushed, and both cloud workflows pass.
- [ ] User approval recorded.

## Review result

Cloud bootstrap evidence is complete. Awaiting user approval; Stage 1 remains
locked until this baseline gate is approved.
