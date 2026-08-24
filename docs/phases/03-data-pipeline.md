# Stage 3 — Automated Data Pipeline

**Status:** Not started  
**Dependency:** Stage 1 approval

## Objective

Produce reproducible, versioned static snapshots while failing closed and
serving the last known-good snapshot when source data are invalid.

## Work and evidence required

- Implement modular adapters, immutable raw capture, normalization, medians,
  schema validation, duplicate/range/freshness checks, and source-drift checks.
- Complete the scheduled workflow only with approved sources.
- Test deterministic output, source failure, snapshot checksums, and absence of
  secrets or paid runtime dependencies.

## Acceptance gate

Two consecutive dry runs pass; identical raw inputs reproduce identical output;
a simulated source failure preserves the prior snapshot and surfaces a stale
warning; and no secret or paid service is required.

## Progress log

The current refresh workflow is a validation scaffold. No pipeline gate work has
been accepted.
