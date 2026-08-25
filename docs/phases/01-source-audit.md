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
- Remote retrieval and checksum generation have now run in the authoritative
  cloud environment. Coverage profiling, rights decisions, canonical mappings,
  and crop qualification remain outstanding.

### 2026-08-25 — first cloud retrieval

- [Workflow run 32808720258](https://github.com/batestguy/crop-value-predictor/actions/runs/32808720258)
  retrieved FEWS NET (84,427 rows through 2026-06), the FAOSTAT archive (33.9
  MB), and the NBS PDF into an artifact with checksums.
- The configured World Bank API returned a valid but empty JSON payload. The
  audit adapter now treats zero-row JSON responses as failures so a stale or
  incorrect endpoint cannot pass the gate. Resolving or explicitly deferring
  that endpoint is the next source-audit action.

### 2026-08-25 — fail-closed rerun

- [Workflow run 32811249560](https://github.com/batestguy/crop-value-predictor/actions/runs/32811249560)
  correctly failed the required-source step because `world-bank-rtfp` returned
  zero rows. FEWS NET, FAOSTAT, and NBS retrievals were still attempted and
  the evidence artifact was uploaded. This is an intentional gate failure,
  not a pipeline error: the World Bank endpoint must be repaired or formally
  deferred before qualification can proceed.

### 2026-08-25 — World Bank endpoint repaired

- The World Bank source now uses the documented global RTFP table
  `wld_2021_rtfp_v02_m`, filtered with the exact `ISO3=NGA` query. The adapter
  follows the NADA contract (`/{limit}/{offset}`), requests 100-row pages, and
  validates a stable `found` total, complete pagination, and country purity.
- The full retrieved snapshot is retained for reproducibility. The profile
  reports raw `DATES` minimum/maximum, rows through the requested cutoff, rows
  after the cutoff, and the number of in-scope markets. Only rows through the
  cutoff may enter later qualification inputs; post-cutoff rows are descriptive
  evidence only.
- Retrieval metadata records page count, row count, filter, `found` total, and
  SHA-256 checksum in `raw_manifest.json`. World Bank remains `candidate` and
  `qualification_report.status` remains `not_run` until rights, normalization,
  completeness, and crop qualification gates pass.
