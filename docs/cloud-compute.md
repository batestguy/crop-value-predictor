# Cloud Compute and Data Storage Policy

## Authority boundary

GitHub Actions is the authoritative compute environment for this project. It
runs source downloads, normalization, data-quality checks, forecast training and
backtesting, contract validation, automated tests, and production builds on
clean Ubuntu runners.

The local workstation is used for editing, Git operations, and inspecting cloud
results. A local build or model run is not evidence that a stage gate passed.

The PWA intentionally retains only deterministic scenario arithmetic: applying
cached yield, cost, and forecast values to area, calculating revenue and profit,
ranking scenarios, and rendering the uncertainty range. This keeps the approved
offline behavior without moving forecasting or data processing onto the device.

## Repository

The public monorepo is:

`https://github.com/batestguy/crop-value-predictor`

It stores source code, configuration, schemas, mappings, documentation, gate
evidence, provenance manifests, checksums, and small redistribution-approved
`public/data/v1` snapshots.

## Data classification

| Material | Location | Rule |
|---|---|---|
| Code, config, docs, mappings, schemas | Git | Reviewable and versioned |
| Accepted publishable JSON | Git and tagged release assets | Must pass contract and rights checks |
| Raw downloads and normalized intermediates | GitHub Actions artifacts | 30-day retention; never required by the browser |
| Candidate forecasts and metrics | GitHub Actions artifacts | Reviewed before promotion |
| Secrets and tokens | GitHub encrypted secrets only | Never commit or print |
| Participant or farmer session data | Project-team controlled storage | Only anonymized aggregates enter the repository |
| Restricted or unlicensed source files | Not redistributed | Keep source URL, checksum, and processing metadata only |

The ignored `data/raw/` directory is for transient local inspection only. A
failed pipeline never replaces the last-known-good public snapshot.

## Workflow rules

- Pull requests and pushes run `ci.yml` with read-only repository permissions.
- Scheduled or manually dispatched refreshes run `refresh.yml` and upload a
  validation artifact with 30-day retention.
- Source adapters and forecast generation are added only after the Stage 1
  source gate passes.
- Candidate snapshots are reviewed and promoted through Git history; they are
  not silently written directly to the public artifact set.
- Main-branch protection must require the cloud validation check after the
  repository is created.
