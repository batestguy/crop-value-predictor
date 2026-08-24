# Crop Value Predictor Delivery Progress

**Plan:** [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)  
**Workflow:** sequential delivery with a user review at every acceptance gate  
**Last updated:** 2026-08-24

## Current status

| Stage | Status | Evidence record | Gate condition |
|---|---|---|---|
| 0. Baseline and tracking setup | Gate review | [`00-baseline.md`](./docs/phases/00-baseline.md) | Progress records, public remote, and cloud validation are reproducible |
| 1. Source and feasibility audit | Not started | [`01-source-audit.md`](./docs/phases/01-source-audit.md) | 5–8 crops, qualified markets, rights, units, and repeatable ingestion path |
| 2. Offline decision calculator | Not started | [`02-offline-calculator.md`](./docs/phases/02-offline-calculator.md) | Complete-input calculation, report parity, persistence, and offline restart |
| 3. Automated data pipeline | Not started | [`03-data-pipeline.md`](./docs/phases/03-data-pipeline.md) | Reproducible snapshots, schema/quality checks, and safe last-known-good fallback |
| 4. Forecasting and validation | Not started | [`04-forecasting.md`](./docs/phases/04-forecasting.md) | Leakage-safe rolling validation, baseline comparison, and auditable intervals |
| 5. Deployment and farmer readiness | Not started | [`05-deployment-readiness.md`](./docs/phases/05-deployment-readiness.md) | Tested install/offline flow, accessibility, low-bandwidth result, and privacy |
| 6. Pilot validation and expansion | Not started | [`06-pilot-validation.md`](./docs/phases/06-pilot-validation.md) | Moderated comprehension, helpfulness, forecast follow-up, and documented limits |

## Status rules

- `Not started`: no stage work has been accepted.
- `In progress`: implementation or evidence collection is underway.
- `Blocked`: a stated dependency prevents safe progress.
- `Gate review`: the stage work and evidence are complete and awaiting user review.
- `Approved`: the acceptance gate passed and the next stage may begin.

Every phase record must include a dated progress log, changed files or
artifacts, commit references, commands and results, decisions, risks, and the
gate outcome. A stage is never approved from code presence alone.

## Review protocol

1. Mark one stage `In progress` and record its starting commit.
2. Record material work and verification as it happens.
3. Run the stage checks and the full regression suite.
4. Mark the record `Gate review` with evidence and known limitations.
5. Pause for explicit user approval before marking it `Approved`.

## Baseline evidence

- Repository: public GitHub remote at `https://github.com/batestguy/crop-value-predictor`,
  `main` tracking `origin/main`.
- `python pipeline/validate.py`: passed; five crops and five forecast records.
- `python -m unittest discover -s tests`: passed; two tests.
- `npm test`: passed.
- `npm run build`: passed.
- Current limitation: the React UI uses hardcoded pilot-seed data; the source
  audit and production pipeline are not yet implemented.
- Cloud policy: GitHub Actions is authoritative for data/ML computation,
  validation, tests, and builds; browser arithmetic remains the offline client
  calculation.
- Cloud CI run: [32685906128](https://github.com/batestguy/crop-value-predictor/actions/runs/32685906128)
  passed on commit `e201edf`.
- Cloud refresh run: [32685952971](https://github.com/batestguy/crop-value-predictor/actions/runs/32685952971)
  passed and uploaded the validation artifact with 30-day retention.
