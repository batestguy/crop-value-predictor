# Stage 1 — Source and Feasibility Audit

**Status:** Closed — fallback accepted; WFP/HDX remediation failed technical gate on 2026-09-04
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

### 2026-08-25 — qualification preparation

- Successful audit workflow [32812781709](https://github.com/batestguy/crop-value-predictor/actions/runs/32812781709)
  collected 17,464 Nigerian World Bank rows across 175 pages (17,390 through
  July 2026 and 74 August rows). Market profiling now recognizes `mkt_name`,
  reports 74 locations (73 source markets plus `Market Average`), and excludes
  only `geo_id=gid_nga_national_average` from market counts and national medians.
- `pipeline/qualification.py` normalizes FEWS NET public, explicit retail or
  wholesale kilogram rows; rejects unknown/count units and duplicate keys;
  applies the 36-month, 80%-recent-completeness, freshness, and forecast-origin
  gates; and writes an evidence-rich `qualification_report.json` only under the
  audit directory. World Bank OHLC fields remain modeled evidence with unknown
  transaction type, and NBS cost data remains deferred pending reproducible
  units and rights.
- The authenticated artifact was regenerated with the repaired pipeline. It
  records 74 World Bank locations, 73 source markets, and one separate
  `gid_nga_national_average` aggregate location. Manifest bytes and SHA-256
  checksums pass. FAOSTAT matching yields are retained for 13 distinct crop
  forms, while NBS costs remain deferred.
- FEWS observations are normalized from explicit NGN package masses to
  `NGN/kg`; retail and wholesale remain separate, and count/tuber units are
  rejected. All usable FEWS series end in June 2026, which is 56 days before
  the 2026-08-25 retrieval date and therefore passes the approved 75-day
  freshness rule. However, the best recent completeness is 69.4%, below the
  80% gate, so zero series and zero crop forms qualify technically.
- The derived report is `calculator_only_fallback`; Stage 1 is not Approved.
  On 2026-08-27 the evidence was explicitly reviewed and the documented
  fallback was accepted. Stage 2 may proceed only as a farmer-input calculator;
  automated prices, production source integration, and Stage 3 remain blocked.

### 2026-08-27 — gate outcome reviewed

### 2026-09-04 — data-source remediation reopened

- Prior FEWS qualification remains immutable evidence and is not stitched to a
  replacement source. A new WFP/HDX path uses public CKAN `package_show` with
  stable slug `wfp-food-prices-for-nigeria`, without an app identifier or secret.
- Retrieval requires one unique CSV, expected WFP publisher, configured live
  license, HTTPS URL sanitization, bounded atomic download, and SHA-256 evidence.
- WFP normalization requires explicit dates, stable market/commodity IDs, NGN,
  retail/wholesale type, provenance flag, and exact mass units; unknown/count
  units and duplicate canonical keys remain rejected.
- This is evidence collection only: `stage_1_approved` remains false and the
  deployed calculator remains calculator-only. A passing report stops at Gate
  review pending explicit user approval.

### 2026-09-04 — WFP/HDX v2 live outcome

- The pinned HDX package UUID is `42db041f-7aaf-4ab4-961f-2a12096861e7`, WFP
  organization UUID is `3ecac442-7fed-448d-8f78-b385ef6f84e7`, and the only
  accepted observation resource is `12b51155-0cd3-4806-9924-61ede4077591`
  (`Nigeria - Food Prices`, `wfp_food_prices_nga.csv`, `cc-by-igo`). The
  separate `Nigeria - Markets` resource is explicitly excluded.
- Fresh audit directory `audit-output-remediation-2026-09-04-v2` contains the
  81,534-row WFP snapshot (2002-01 through 2026-07), with 11,716 rows surviving
  explicit form/unit/flag mapping. Its immutable SHA-256 is recorded in the
  manifest; World Bank failed with zero rows and remained optional.
- No WFP series qualified: the best recent completeness was 83.3% but ended
  2026-06-15 (81 days old), while fresh series reached only 52.8%. The report
  is `calculator_only_fallback`, with zero eligible series and zero selected
  crop forms. Technical and rights gates are separate; `stage_1_approved` is
  false and no public calculator data changed.

- The five-crop technical acceptance gate remains failed: zero crop forms and
  zero price series qualified.
- The stage status is `Closed — fallback accepted`, which records a reviewed
  stop/fallback outcome rather than a successful source approval.
- No gate threshold was relaxed and no source was promoted. A future source
  remediation effort must produce a new immutable audit and independently pass
  every technical and rights gate before automated-price work can resume.

- Regenerated qualification report SHA-256: `f17e661076a9d8e642cc10ea732364d52fe60168d005eb195414f7de0e11e9d8`.
  The report and raw snapshot remain local/ignored audit evidence; automated
  prices remain blocked.
