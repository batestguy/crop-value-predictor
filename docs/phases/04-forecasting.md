# Stage 4 — Forecasting and Validation

**Status:** Not started  
**Dependency:** Stage 3 approval

## Objective

Publish only forecasts supported by leakage-safe, rolling-origin evidence and
auditable uncertainty intervals.

## Work and evidence required

- Establish last-value and seasonal-naive baselines for one- and three-month
  horizons.
- Evaluate candidate models and weather, exchange-rate, and global-price
  features only through time-safe ablation.
- Report MAE, WAPE, MAPE, interval coverage, origins, provenance, and observed
  versus modeled source status.
- Make training inputs, seeds, parameters, and snapshot IDs reproducible.

## Acceptance gate

Every released series has at least six three-month origins, finite metrics, no
leakage, a baseline comparison, and an auditable 80% interval. A candidate is
`validated` only when it improves the seasonal baseline on median MAE and WAPE.

## Progress log

The seed forecast records are illustrative baseline data. No Stage 4 gate work
has been accepted.
