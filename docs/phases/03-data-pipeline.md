# Stage 3 — Automated Data Pipeline

**Status:** Not started  
**Dependency:** A future source qualification report that passes the full Stage
1 technical and rights gate; the accepted calculator-only fallback does not
satisfy this dependency

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
# Stage 3 remains blocked while Stage 1 is closed at the calculator-only fallback.

The 2026-09-04 WFP/HDX remediation produced no technically qualified price
series. Automated prices, source-driven defaults, and pipeline promotion remain
blocked until a new immutable source audit passes all technical and rights
gates.
