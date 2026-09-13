# Stage 1 — Source and Feasibility Audit

**Status:** In progress — web-first remediation run opened 2026-09-09
**Dependency:** Stage 0 approved on 2026-08-25; prior failed audits remain immutable evidence

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

## Current remediation contract — 2026-09-09

The active remediation is a fresh, date-specific audit. It does not modify or
stitch together the failed FEWS and WFP/HDX snapshots recorded below.

- Retrieve FEWS NET and WFP/HDX using the latest complete-month cutoff and
  record retrieval dates, source URLs, upstream identifiers, and SHA-256
  checksums in a new immutable audit directory.
- Bound the FEWS request to the latest 60 complete months through the cutoff;
  this exceeds the 36-month gate and preserves six rolling forecast origins
  without requesting an unnecessary full-history payload.
- Keep FEWS as the primary observed-price candidate. WFP/HDX remains an
  independent cross-check and cannot fill missing FEWS history or make an
  incomplete FEWS series eligible.
- Re-run the unchanged 36-month history, 80% recent-completeness, 75-day
  freshness, three-market national-median, six-forecast-origin, unit,
  transaction-type, mapping, and rights gates.
- Review source eligibility, extraction accuracy, rights interpretation, and
  claim wording in two independent passes before the result reaches Gate
  review.
- A passing technical report still requires explicit Stage 1 approval before
  any automated price artifact is promoted. A failed report preserves the
  calculator-only web fallback.

The active product target is the static React/TypeScript web PWA. Android
installation, update, and offline-recovery evidence are not Stage 1 or web
release requirements.

## Acceptance gate

At least five crops pass every qualification and rights check, one repeatable
no-secret price path works, units and price types resolve without guessing, and
national medians have at least three comparable markets. Otherwise document the
calculator-only fallback and stop automated-price claims.

## Sequential gate record

Technical qualification is only the first Phase 1 gate: each FEWS series must
pass the unchanged history, completeness, freshness, unit, transaction, and
forecast-origin rules; each selected crop and price type must have at least
three reviewed canonical markets; and at least five crops must pass. The local
`stage_1_gate_review.json` binds evidence, mappings, and two distinct,
timezone-aware post-retrieval review records to the immutable raw-manifest
checksum. It is evidence only, not a trust authority: anyone able to write the
audit directory can fabricate it. It cannot approve Stage 1 or permit
promotion. Final promotion requires a separately protected/external approval
artifact cryptographically bound to the immutable manifest, recomputed
qualification digest, and selected-series digest. No signing verifier is
configured in this repository, so promotion fails closed rather than treating
local reviewer IDs or hashes as trusted.

The current cloud audit remains `calculator_only_fallback` after FEWS HTTP 403,
with zero eligible series and zero selected crops. `stage_1_approved` remains
false; automated prices, forecasting, and Stages 3–4 remain blocked.

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

### 2026-09-09 — alternatives screened

- The alternative assessment in [`../stage1-source-alternatives.md`](../stage1-source-alternatives.md)
  compares FEWS NET, FAO FPMA, World Bank RTFP, NBS, NEPC, and WFP/HDX without
  changing the existing Stage 1 thresholds.
- No observed-price alternative passed the unchanged gate. FAO FPMA exposes
  explicit Nigeria retail/wholesale series, but the strongest current recent
  completeness screen is 69.4%; NBS-backed series are current only through May
  2026 in the live catalog and fail the 75-day freshness rule on 2026-09-09.
- The current World Bank Nigeria bulk file passed an exploratory numerical screen
  when its documented monthly close estimates were normalized to source-aligned
  forms. Because transaction type is unknown and the values are modeled, this is
  evidence for a possible separate modeled-estimate lane, not approval of the
  existing observed-price lane.
- Stage 1 therefore remains `calculator_only_fallback`; no automated price or
  forecast promotion is authorized by this screening note.

- Regenerated qualification report SHA-256: `f17e661076a9d8e642cc10ea732364d52fe60168d005eb195414f7de0e11e9d8`.
  The report and raw snapshot remain local/ignored audit evidence; automated
  prices remain blocked.

### 2026-09-09 — web-first remediation reopened

- Reopened Stage 1 for a fresh FEWS/WFP qualification attempt using the
  unchanged technical and rights gates.
- The existing React/Vite PWA is the primary web product. Android hardware is
  removed from the active release requirement; mobile-browser behavior remains
  in scope.
- The audit command is prepared to write the new immutable evidence package to
  `audit-output-remediation-2026-09-09`. Stage 1 remains unapproved until the
  qualification report, rights review, two review passes, and explicit user
  gate decision are complete.

### 2026-09-09 — remediation retrieval outcome

- The first fresh audit recorded FEWS HTTP 403, World Bank zero rows, a current
  WFP/HDX download of 10,801,660 bytes with SHA-256
  `10bfee3dbd4c1798ec4ea57b9611b025ddb3391147c238ab048185a24eb88d62`, a
  successful FAOSTAT archive, and an NBS connection timeout. Its report was
  `calculator_only_fallback` with zero eligible series.
- FEWS’s official API documentation and Nigeria download page were checked.
  The adapter now uses the documented trailing-slash endpoint with
  `dataset=FEWS_NET_Staple_Food_Price_Data`, `country=NG`, `fields=website`,
  and `format=json`, while retaining strict pagination and country checks.
- Fresh retries using the repaired contract still failed closed because the
  public endpoint returned 403/timeouts during the full retrieval. The v3
  qualification report remains `calculator_only_fallback`, with
  `stage_1_approved: false` and promotion prohibited. No public data artifact
  changed and no automated price claim was unlocked.
- The adapter now bounds normal FEWS retrieval to 60 months and applies a
  configured inter-page delay plus bounded retries for transient 403, 429, and
  5xx responses. A fresh bounded FEWS-only run still received repeated 403
  responses, so this is an upstream access blocker rather than a qualification
  result.

### 2026-09-09 — modeled context artifact (separate lane)

The current World Bank bulk-discovery adapter now retrieves the official open
Nigeria RTFP ZIP and validates its single CSV member, `ISO3=NGA` purity, and
`price_date` field. A separate modeled-estimate builder produced
`public/data/v1/modeled_price_suggestions.json` from the 2026-08 file: 438
source-market suggestions across six source-aligned forms and 73 markets.
Every record is labelled `modeled_estimate`, retains the raw-artifact hash and
modeled-month-close provenance, and carries a warning that it is not an
observed retail, wholesale, or farmer selling price.

This artifact is enabled only as editable context. It has a separate snapshot
ID and manifest flag; `stage_1_approved` remains false, observed
`price_suggestions.json` remains unavailable, and no forecast or public
observed-price claim is unlocked.

### 2026-09-10 — fresh remediation audit failed closed

- A new immutable audit was written to
  `audit-output-remediation-2026-09-10` with the unchanged August 2026 cutoff.
- FEWS NET returned HTTP 403 after the configured bounded retries. World Bank,
  WFP/HDX, FAOSTAT, and NBS artifacts were retrieved and their manifest hashes
  verified.
- Qualification recorded `calculator_only_fallback`: zero FEWS eligible
  series, zero WFP eligible series, and zero selected crop forms. WFP produced
  12,742 normalized rows but no series passed the unchanged gates.
- `stage_1_approved` remains false, no public data changed, and Stages 3 and 4
  remain blocked. This is an upstream retrieval-availability blocker, not a
  relaxed threshold or an observed-price approval.

### 2026-09-10 — modeled context product and rights review

- The World Bank catalog identifies the RTFP dataset as open data and provides
  a required citation. Its dataset terms permit copying, adapting, displaying,
  and including the data in other products subject to attribution, no
  endorsement, and checking any restricted third-party material.
- The modeled artifact already carries the required source attribution, source
  hash, dataset reference, source-aligned crop forms, modeled provenance, and
  an explicit not-observed warning. Its values remain editable prefills and do
  not drive a separate data source, forecast, or Stage 1 decision.
- Product review is accepted for the narrow context-only lane. Redistribution
  remains provisional until any third-party restrictions are confirmed; this
  review does not approve observed prices, change `stage_1_approved`, or unlock
  Stages 3 or 4.

### 2026-09-10 — authorized cloud FEWS investigation

- The user authorized an external/cloud retrieval origin for further FEWS
  investigation. Two evidence-only canaries were run: August 2026 returned no
  positive result total, while June 2026 returned HTTP 403.
- Full read-only Stage 1 audit [run 34434760861](https://github.com/batestguy/crop-value-predictor/actions/runs/34434760861)
  completed with FEWS HTTP 403 after bounded retries. The uploaded artifact
  was downloaded to `audit-output-fews-cloud-full-20260910-34434760861`.
- The cloud qualification report is `calculator_only_fallback`, with zero
  FEWS eligible series and zero selected crop forms. WFP, FAOSTAT, and NBS
  manifest hashes passed; the remote branch's older World Bank endpoint
  returned zero rows.
- The downloaded WFP, FAOSTAT, and NBS files match their recorded byte sizes
  and SHA-256 values. The qualification-report SHA-256 is
  `db2eb66f0bf4c8d71238e1452ed13031af553910ef9c4c015cf29a1d7af35484`.
- The official API documentation confirms that market-price JSON uses
  `country_code`, `page_size`/`offset`, and a `count`/`results` envelope:
  [`FEWS NET API`](https://help.fews.net/fde/v3/fews-net-api). The adapter
  remains fail-closed when FEWS returns 403 or an empty/nonconforming payload.

Stage 1 remains unapproved, the public snapshot is unchanged, and no
promotion was attempted. The next FEWS action must be a justified
endpoint-contract or access-path change, not repeated requests against the
same failing path.
