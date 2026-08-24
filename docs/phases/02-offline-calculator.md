# Stage 2 — Offline Decision Calculator

**Status:** Not started  
**Dependency:** Stage 1 approval and qualified static contracts

## Objective

Deliver a data-driven, deterministic calculator that remains useful offline and
shows assumptions, uncertainty, sources, and fallback status.

## Work and evidence required

- Replace hardcoded UI data with validated `/data/v1` JSON.
- Implement pure calculation functions, complete-input confirmation, ranking,
  uncertainty range, charts, local persistence, and printable report parity.
- Test arithmetic, area scaling, ties, invalid/missing inputs, overrides,
  fallback warnings, offline restart, and report equality.

## Acceptance gate

Golden fixtures reproduce the same values on screen and in the report; incomplete
inputs cannot rank; area and per-hectare costs scale correctly; and the flow
works after network removal and browser restart.

## Progress log

The existing React seed is prototype evidence only; no Stage 2 gate work has
been accepted.
