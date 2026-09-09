# Stage 1 Source Alternatives

**Review date:** 2026-09-09
**Decision status:** exploratory alternatives reviewed; Stage 1 remains not approved.

This note compares source paths against the existing Stage 1 contract. It does not
relax the 36-month history, 80% latest-36-month completeness, 75-day freshness,
six forecast-origin, market-coverage, units, mapping, or rights requirements.

## Short answer

No currently checked observed-price source passes the unchanged Stage 1 release
gate. The strongest immediate alternative is a separate **modeled-estimate
release lane** based on the World Bank Real-Time Food Prices dataset. It passes
the numerical history/freshness screen, but it must not be presented as observed
retail, wholesale, or farmer selling prices because the dataset is modeled and
the transaction type is not supplied.

The observed-price calculator should therefore remain manual-price-only. A
separate modeled-context artifact has now been implemented behind its own
manifest flag, with explicit UI warnings and no Stage 1 approval effect.
Further promotion still requires an explicit decision about the modeled lane:

1. keep the existing observed-price contract and wait for an observed source to
   meet the completeness gate; or
2. keep the clearly labelled modeled-estimate mode as editable context with a
   separate acceptance gate.

## Comparison

| Alternative | What the live source provides | Stage 1 result under the current contract | Main work or risk |
|---|---|---|---|
| FEWS NET direct, filtered API | Observed retail/wholesale market observations, explicit package units, Nigeria market IDs | **Fails current snapshot:** best recent completeness recorded in the audit is 69.4%; repeated local retrieval also encountered 403/timeouts | Keep as observed-price primary candidate; use filtered product/CPC queries and a cloud retrieval origin, then re-run the immutable audit. A successful HTTP request alone is not a gate pass. |
| FAO FPMA API | Nigeria series with explicit retail/wholesale labels, NGN, units, stable market IDs, and monthly values | **Fails current snapshot:** the strongest FEWS-backed series screened at 69.4% latest-36-month completeness; NBS-backed FPMA series currently end in May 2026 and fail freshness at the 2026-09-09 snapshot | Good independent cross-check or future observed primary candidate after coverage/freshness improves. Do not fill FEWS gaps with FPMA rows. |
| World Bank RTFP bulk/API | 73 Nigerian source markets plus a national aggregate, 2007-01 through 2026-08, and modeled monthly product estimates | **Passes numerical screen only in a new modeled lane:** six source-aligned forms, 236 months, 100% latest-36-month completeness, 39-day freshness, and 234 forecast-origin windows in an exploratory close-estimate screen | Adapter and component-mass mapping are implemented; retain `modeled_estimate` and modeled/imputed provenance, and keep open-data/redistribution review separate from the observed-price gate. |
| NBS Selected Food Price Watch | Official Nigeria monthly state/national food prices and documented field coverage | **Fails current release gate:** current catalog materials are through May 2026, which is 131 days old on 2026-09-09; historical materials do not solve freshness | Strong contextual/validation source and possible future primary source when current releases are available. |
| NEPC indicative prices | Official indicative commodity prices, including a July 2026 publication | **Fails current release gate:** publication is not a complete 36-month, multi-market series for the five app forms | Use only as contextual evidence unless a reproducible historical series and rights decision are established. |
| WFP/HDX current snapshot | Public CSV with explicit market, commodity, unit, and price-type fields | **Fails current snapshot:** the retrieved file is stale and produced zero eligible series under the existing gates | Retain as an independent cross-check; never stitch it into another source to manufacture completeness. |

## World Bank modeled-lane screen

The exploratory screen used the current official Nigeria bulk file and selected
only the monthly close (`c_`) estimate. It converted the documented component
package sizes to NGN/kg and kept source markets distinct. This is a numerical
screen, not a release approval.

| Screen | Result |
|---|---:|
| Source rows | 17,464 |
| Source markets | 73, excluding the separate national aggregate |
| Source-aligned forms | 6: maize, rice-milled, gari-white, yam, sorghum-white, millet |
| Monthly history | 236 months through 2026-08 |
| Latest-36-month completeness | 100% in the screened series |
| Latest observation | 2026-08-01; 39 days before the 2026-09-09 screen |
| Forecast-origin windows | 234 per screened series |
| Transaction type | Unknown; do not relabel as retail or wholesale |
| Provenance | Modeled monthly estimate; some values are imputed |

The current app catalog calls rice “paddy” and cassava “fresh roots”. The source
records screened here are milled rice and white gari. The modeled lane adds
source-aligned `rice-milled`, `gari-white`, and `millet` forms; it does not map
milled rice to paddy or gari to fresh cassava. Those mappings remain prohibited.

## Recommended next move

Use a two-lane decision:

- **Observed-price lane:** keep Stage 1 blocked and continue FEWS remediation,
  with FAO FPMA as a cross-check. No source stitching and no threshold changes.
- **Modeled-estimate lane:** the separate artifact is implemented as
  `public/data/v1/modeled_price_suggestions.json` and enabled only as editable
  context. It has a distinct snapshot ID, source hash, source-aligned crop
  forms, modeled provenance, warning, loader validation, and automated tests.
  It does not unlock a claim of current farmer selling price, observed market
  price, or farmer validation.

The modeled lane is the only checked alternative that is close to a technical
Stage 1 pass today. It is not a pass of the existing observed-price gate.

## Evidence links

- [World Bank Nigeria RTFP catalog](https://microdata.worldbank.org/catalog/4503)
- [World Bank data API page](https://microdata.worldbank.org/catalog/4503/data-api)
- [World Bank current data dictionary and file metadata](https://microdata.worldbank.org/catalog/4503/data-dictionary/NGA_2021_RTFP_MKT?file_name=NGA_RTFP_mkt_2007_2026-08-24.csv)
- [FAO GIEWS data tools and FPMA description](https://www.fao.org/giews/data-tools/en/)
- [FAO FPMA API](https://fpma.fao.org/giews/v4/global/price_module/api/v1/FpmaSerie/?iso3_country_code=NGA)
- [FEWS NET API filters and pagination](https://help.fews.net/fde/v3/fews-net-api)
- [NBS Selected Food Price Watch catalog](https://microdata.nigerianstat.gov.ng/index.php/catalog/162/study-description)
- [NEPC indicative market prices](https://nepc.gov.ng/indicative-market-prices/)
