# Stage 1 Source Register (Initial Audit)

**Started:** 2026-08-25  
**Status:** In progress; qualification is not yet accepted

This register records candidate sources before remote download and qualification.
The machine-readable versions are [`../config/sources.json`](../config/sources.json)
and the initial canonical mapping scaffold in
[`../config/mappings.json`](../config/mappings.json).
No source is promoted to a production claim from this table alone.

| Source | Intended role | Current evidence | Access path | Open qualification checks |
|---|---|---|---|---|
| [World Bank RTFP](https://microdata.worldbank.org/catalog/4503) | Optional modeled context only | Direct/ML-estimated values lack the transaction comparability required for a selling-price prefill | Global NADA table, queried with `ISO3=NGA` in pages | Never use for price suggestions or fill gaps in another source |
| [FEWS NET Nigeria prices](https://fews.net/nigeria-weekly-fews-net-staple-food-price-data-2) | Primary zero-secret price candidate | Public FEWS API candidate with Nigeria filtering, explicit units and retail/wholesale price types | Public paginated JSON API, `country_code=NG` | Confirm coverage, completeness, freshness, terms, and permission to cache a reviewed static snapshot |
| [WFP/HDX](https://data.humdata.org/dataset/wfp-food-prices-for-nigeria) | Independent cross-check only | Public CKAN resource with explicit market, commodity, unit, price flag, and price type | Public HDX CSV discovery/download; HAPI/app-ID access is out of scope | Compare only matching qualified FEWS series; never merge WFP rows to fill FEWS history |
| [FAOSTAT QCL](https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876) | National yield defaults | FAO documents annual crop production/yield data, yield in hg/ha, 1961–2024 coverage, and CC-BY-4.0 licensing | Public catalog/download | Confirm Nigeria crop rows, revision date, conversion to t/ha, citation, and non-local-advice warning |
| [NBS NASS 2022/23](https://microdata.nigerianstat.gov.ng/index.php/catalog/173/related-materials) | Dated cost and farm-gate defaults | NBS publishes NASS materials including crop prices, farm-gate prices, and fertilizer/pesticide input prices | Public catalog resources | Confirm usable tables, units, rights, extraction reproducibility, and stale-default labeling |
| [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Deferred weather feature candidate | Public daily weather API | Not part of the Stage 1 gate | Revisit only during leakage-safe forecast ablation |

## Qualification rules

The remote audit must establish at least 36 monthly observations, at least 80%
completeness over the latest 36-month window, no duplicate canonical keys,
freshness within 75 days for current claims, explicit units and price types,
five qualified crop forms, and redistribution rights. Each source qualifies on
its own: incomplete WFP/HDX data can never complete a FEWS NET series.

Rows retain provenance such as `observed`, `aggregate`, `imputed`, or `forecast`.
Unknown bag, basket, bunch, or count units fail closed; they are not silently
converted to kilograms.

## Evidence links

- World Bank’s catalog identifies the dataset as compiled from direct and
  machine-learning-estimated prices and publishes an explicit citation.
- FEWS NET’s market-data page confirms public downloadable price files.
- FAOSTAT’s catalog states the units, time coverage, and CC-BY-4.0 license;
  the FAO database terms require attribution.
- NBS’s catalog identifies NASS as a national agricultural survey and exposes
  crop-price and input-price resources.

These links support candidate selection, not final qualification. The next
evidence update must attach retrieval timestamps, checksums, row counts,
coverage profiles, and rights decisions from the remote run.

## Remote audit command

The manual GitHub Actions workflow [`source-audit.yml`](../.github/workflows/source-audit.yml)
executes:

```bash
python pipeline/source_audit.py --fetch --cutoff-month YYYY-MM --output-dir audit-output
```

It writes `raw_manifest.json`, `source_profile.json`, and raw files under
`audit-output/raw/`. Required-source failures fail the workflow; skipped
optional candidates remain visible in the artifact for review.

## Promotion boundary

Retrieval and technical qualification do not publish anything. A reviewer must
create an approval JSON that binds explicit Stage 1, rights, and
price-suggestion decisions to the SHA-256 of `qualification_report.json`; then
run:

```bash
python pipeline/promote_price_suggestions.py --audit-dir audit-output --approval stage1-approval.json
```

The promoter writes validated same-origin `approved_markets.json` and
`price_suggestions.json` before it writes the new manifest. Any failed, stale,
malformed, unmatched, or unapproved input leaves the current snapshot intact.

The World Bank adapter requests `/100/{offset}?ISO3=NGA` until the server's
stable `found` total is complete. It fails closed on zero rows, malformed JSON,
changed totals, empty intermediate pages, pagination gaps, retries exhausted,
or any row whose `ISO3` is not `NGA`. The raw snapshot may include records after
the cutoff for reproducibility; `source_profile.json` reports those separately,
and later qualification must use only `rows_through_cutoff`.
