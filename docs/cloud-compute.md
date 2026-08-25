# Cloud Compute and Data Storage Policy

## Authority boundary

GitHub Actions is the workflow and validation authority for this project. It
runs source downloads, normalization, data-quality checks, contract validation,
automated tests, production builds, and release review on clean Ubuntu runners.

The prototype's one-time training run executes remotely on Kaggle through the
Kaggle CLI. GitHub Actions submits the job, polls it, retrieves its artifacts,
and validates them. There is no scheduled retraining in the prototype.

The local workstation is limited to editing, Git operations, and inspecting
cloud results. A local build, data pull, or model run is not evidence that a
stage gate passed.

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
- The launch training workflow is manually dispatched and accepts an explicit
  release ID and complete-month cutoff; it does not run on a schedule.
- Candidate model outputs are uploaded as artifacts with provenance and are
  promoted only through reviewed Git history.
- Source adapters and forecast generation are added only after the Stage 1
  source gate passes.
- Candidate snapshots are reviewed and promoted through Git history; they are
  not silently written directly to the public artifact set.
- Main-branch protection must require the cloud validation check after the
  repository is created.
