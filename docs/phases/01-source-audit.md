# Stage 1 — Source and Feasibility Audit

**Status:** In progress
**Dependency:** Stage 0 approved on 2026-08-25

## Objective

Establish which free sources, crops, markets, units, price types, and defaults
are defensible for the public pilot.

## Work and evidence required

- Audit WFP/HDX, World Bank RTFP, FEWS NET, FAOSTAT, NBS, and supporting sources.
- Capture URLs, terms, cadence, authentication, coverage, units, attribution,
  and redistribution decisions.
- Build canonical crop/product-form, market, unit, and provenance mappings.
- Run the 36-month, freshness, completeness, market-count, forecast-origin,
  and rights qualification gates.
- Publish the source register, raw-data manifest, mappings, data profile, and
  selected 5–8 crop/market report.

The initial register is [`../source-register.md`](../source-register.md). The
remote execution path and one-time launch cutoff are documented in
[`../batch-training-architecture.md`](../batch-training-architecture.md).

## Acceptance gate

At least five crops pass every qualification and rights check, one repeatable
no-secret price path works, units and price types resolve without guessing, and
national medians have at least three comparable markets. Otherwise document the
calculator-only fallback and stop automated-price claims.

## Progress log

### 2026-08-25 — audit opened

- Added the initial candidate register with World Bank RTFP, FEWS NET, WFP/HDX,
  FAOSTAT, and NBS evidence links.
- Added machine-readable audit metadata, a manual cloud retrieval workflow,
  raw-file checksums, and an initial source profile artifact writer.
- Confirmed that the source audit must distinguish observed, aggregate, imputed,
  and forecast rows and must fail closed on unknown units.
- Remote retrieval and checksum generation are implemented but not yet run in
  the authoritative cloud environment. Coverage profiling, rights decisions,
  canonical mappings, and crop qualification remain outstanding.
