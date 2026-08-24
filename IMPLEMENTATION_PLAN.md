# Zero-Cost Crop Value Predictor Delivery Plan

**Status:** Approved delivery baseline  
**Plan date:** 2026-08-24  
**Original specification:** `Crop Value Predictor App.txt`, version 1.0

## 1. Delivery decision

The product is viable as a zero-cost, public pilot if it is delivered as a
static, offline-capable decision aid rather than as a real-time, 30-crop cloud
ML platform.

The pilot will compare **5–8 data-qualified crops**, only at markets covered by
the selected price data and at a derived **Nigeria national median**. Farmers
will enter costs manually, starting from dated and sourced defaults where those
defaults are defensible. A scheduled batch pipeline will publish static JSON
snapshots and forecasts. The progressive web app (PWA) will cache those files
and perform the complete cost, revenue, profit, ranking, chart, and report
calculation in the browser, including while offline.

This is decision support, not a promise of price, yield, or profit. Every result
must show its source, price basis, data date, forecast horizon, uncertainty, and
fallback status.

## 2. Agreed pilot defaults

| Decision | Pilot default |
|---|---|
| Access and cost | Public, anonymous, free pilot; no paid API, server, database, account, or custom domain required |
| Crop scope | 5–8 crops selected by the data qualification gate; no crop is included merely because it appears in a top-30 list |
| Geography | Markets present in the qualified source data plus a Nigeria national median; no inferred LGA or agro-ecological-zone price |
| Price basis | Keep farm-gate, wholesale, and retail series separate; prefer farm-gate, then wholesale, for farmer revenue |
| Costs | Manual farmer inputs in NGN per hectare, prefilled only with dated, sourced defaults; every default remains editable |
| Yield | Dated sourced default in tonnes per hectare, with manual override; national values are never presented as local agronomic advice |
| Architecture | Static React/TypeScript PWA, static versioned JSON, scheduled Python pipeline, and free static hosting |
| Offline behaviour | Full calculation and recommendations from cached forecasts/defaults; no network call is required after a successful first load |
| Language | English-first UI with all visible strings externalized into locale JSON; Pidgin, Hausa, Yoruba, and Igbo follow validation |
| Forecasts | One- and three-month monthly forecasts; cached forecast records, not browser-cached Python models |
| Recommendation | Highest estimated net profit by default, accompanied by uncertainty, data quality, volatility, and a no-guarantee warning |

## 3. Source viability and pilot policy

### 3.1 Viability table

| Source | Candidate role | Viability assessment | Pilot decision |
|---|---|---|---|
| [WFP food prices through HDX HAPI](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/food_security_nutrition_and_poverty/#food-prices-market-monitor) | Market price history and market metadata | Strong candidate. The documented series is primarily monthly, updated weekly, and retains commodity, market, unit, price flag, and price type. Coverage still has to pass crop-by-market tests. | **Primary observed-data candidate.** Ingest for Nigeria, retain flags and price types, and never combine retail with wholesale/farm-gate. |
| [World Bank Nigeria Real-Time Food Prices](https://microdata.worldbank.org/catalog/4503) | Current market-level price estimates and coverage cross-check | Strong, open, broad baseline: the catalog reports 73 markets from 2007 onward. Some values are smoothed or ML-imputed, so the data are not all independent observations. | **Primary continuity/fallback candidate.** Preserve modeled/observed provenance and report validation separately on observed rows. |
| [FEWS NET Nigeria weekly staple prices](https://fews.net/nigeria-weekly-fews-net-staple-food-price-data-2) | Independent staple-price source and validation | Strong for covered staples; public CSV/JSON/XLSX downloads are documented from 2003. The broader Data Explorer API requires a free account. | **Secondary and validation source.** Use file downloads in the zero-secret path; do not make the PWA depend on an account-gated API. |
| [FAO GIEWS FPMA](https://www.fao.org/giews/data-tools/en/) | Monthly domestic-price cross-check | Credible and downloadable, with domestic retail/wholesale series, but the public tool is better documented than a stable unauthenticated extraction API. | **Secondary source.** Automate only after a repeatable, permitted download path passes the audit; otherwise use for release checks. |
| [FAOSTAT crop production and yield](https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876) | Yield defaults and crop-name mapping | Strong national annual source with units, quality flags, CSV resources, and CC BY 4.0 terms. It does not provide Nigeria market/LGA/agro-zone yields. | **Use for national defaults.** Convert `hg/ha` to `t/ha`, keep the source year/flag, and require user override. |
| [Nigeria NBS National Agricultural Sample Survey 2023](https://microdata.nigerianstat.gov.ng/index.php/catalog/173/related-materials) | Cost defaults and farm-gate reasonableness checks | Useful official survey/report with farm-gate prices and fertilizer/pesticide input-price tables. It is periodic, not a current-cost API. | **Use as a dated seed source.** Mark old defaults as stale and never silently refresh them by inflation assumptions. |
| [NASA POWER daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Rainfall and temperature forecast features | Strong free batch API with JSON/CSV and long daily history. Spatial resolution and rate guidance prevent market-level precision claims. | **Candidate model feature.** Aggregate by market coordinate and retain it only when time-safe ablation improves validation. |
| [Central Bank of Nigeria data page](https://www.cbn.gov.ng/data-page.html) | Official NGN/USD feature | Official exchange-rate and monthly-average publications exist, but a stable public API is not established by the current page. | **Batch/manual adapter.** Cache a normalized monthly series; never call or scrape it from the browser. |
| [World Bank Pink Sheet](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/world-bank-commodities-price-data-the-pink-sheet) | International commodity feature | Free monthly history, but global benchmark prices are not Nigerian market prices. | **Optional exogenous feature only.** Do not use it as the target or as a local price fallback. |
| [Iya Oloja market API](https://nigerian-markets-api-docs.vercel.app/docs/openapi/listMarkets) | State/LGA/market directory and coordinates | Viable directory endpoint with market names and coordinates. It does not document crop-price observations. | **Optional lookup enrichment.** Do not treat directory coverage as price coverage; cache accepted records with attribution. |
| ADIP | Rice/cassava/palm-oil benchmarking | Public descriptions exist, but the audit has not established a canonical, stable endpoint, license, update policy, or service-level expectation. | **Deferred.** Admit only after endpoint, terms, schema, freshness, and reproducibility checks pass. |
| Coldtivate ML4Market Nigeria | External forecast comparison | Open project documentation confirms a Nigeria forecasting service, but not a stable anonymous public forecast contract suitable for this pilot. | **Deferred/benchmark only.** Never make core results depend on it. |
| Farm Price API | Community farm-price endpoint | Available evidence describes a sample/self-hosted code project rather than an authoritative maintained production feed. | **Reject for pilot data.** It may be studied as an adapter example only. |
| Kaggle WFP mirrors | Historical bootstrap | Convenient copies can be stale, transformed, or ambiguously licensed relative to the upstream dataset. | **Fallback for development only.** Production artifacts must trace to WFP/HDX or another authoritative upstream source. |
| AfroTools | Yield lookup proposed in the original specification | No sufficiently documented, authoritative pilot contract has been established. | **Deferred.** FAOSTAT is the pilot yield source. |

### 3.2 Data qualification gate

A crop can enter the pilot only when all of the following are true:

- Its canonical name, form, price type, currency, and unit can be mapped without
  guessing. Varieties or processed forms such as paddy rice, milled rice, white
  maize, and maize flour remain separate unless a documented mapping permits an
  aggregation.
- It has at least 36 distinct monthly observations for a market series, with 60
  months preferred, at least 80% completeness over the most recent 36 expected
  months, and no unresolved duplicate `(crop, market, price_type, month)` keys.
- The latest observation is no more than 75 days old at snapshot time. A series
  may remain visible when stale, but it cannot generate the default planting
  recommendation.
- At least three qualified markets contribute to a national figure for a given
  crop/month. The national value is the median of those comparable market
  prices, not an interpolation for uncovered places.
- Its usable history supports at least six rolling three-month forecast origins
  after feature creation.
- Source terms permit the intended processing, redistribution, attribution, and
  public caching. A technically accessible source fails if its rights are not
  clear.

The audit ranks all eligible crops by qualified-market count, recent
completeness, history length, and cross-source agreement, then selects the best
5–8. This deterministic rule intentionally replaces an unsupported preselected
crop list.

### 3.3 Source and fallback rules

1. Store raw downloads immutably with retrieval time, source URL, checksum, and
   upstream version where available.
2. Preserve whether a row is observed, aggregate, imputed, or forecast. Never
   relabel modeled World Bank values as observations.
3. Convert all prices to `NGN/kg` only through explicit unit conversions. Reject
   unknown bags, baskets, bunches, or counts until a sourced conversion exists.
4. Keep farm-gate, wholesale, and retail series separate. The default revenue
   basis is farm-gate, otherwise wholesale with a visible proxy warning. Retail
   prices are reference/sensitivity values unless field validation supports
   their use.
5. Use a qualified market forecast first, then a national-median forecast. If
   neither is available, use the last cached qualified price only as a labeled
   historical scenario and do not call it a forecast.
6. Show source, `as_of`, `generated_at`, freshness, price type, number of
   observations, model status, and fallback reason next to each recommendation.
7. A source failure must not erase the last known-good public snapshot. The
   pipeline fails closed and deployment continues serving that snapshot with a
   stale-data warning.

## 4. Target architecture

```mermaid
flowchart LR
    S[Free public data sources] --> P[Scheduled Python pipeline]
    P --> Q[Schema, unit, freshness, and leakage checks]
    Q --> M[Baseline and candidate forecasts]
    M --> J[Versioned static JSON snapshot]
    J --> H[Free static hosting]
    H --> W[React/TypeScript PWA]
    W --> C[Cache Storage + IndexedDB]
    C --> D[Offline decision calculator, charts, and PDF]
```

### 4.1 Components

| Component | Responsibility | Zero-cost implementation |
|---|---|---|
| Data adapters | Download and archive upstream data without exposing secrets | Python scripts; unauthenticated downloads preferred |
| Normalizer | Canonical crop/market IDs, dates, price types, units, currency, and provenance | Pandas plus checked mapping files |
| Forecast job | Train, backtest, select, and emit small forecast records | Scikit-learn; XGBoost only if installation and validation justify it |
| Scheduler | Refresh data and rebuild only after a valid new snapshot | GitHub Actions on a weekly schedule and manual dispatch; public-repository Actions are free under current limits |
| Hosting | Serve immutable app assets and JSON | Cloudflare Pages free static hosting at a `pages.dev` address; no Pages Functions |
| PWA | Inputs, calculations, warnings, ranking, charts, localization, and report export | React + TypeScript + Vite; service worker and IndexedDB |
| Persistence | Cache public snapshots and private user-entered scenarios locally | Cache Storage for URL assets; IndexedDB for structured snapshot/input data |

The browser does not contact upstream agricultural APIs. It downloads only the
published JSON snapshot, validates it, and atomically replaces its cached
last-known-good version. This keeps the user path fast, anonymous, and fully
offline after initial synchronization.

All authoritative computation runs in cloud-hosted GitHub Actions runners:
source downloads, normalization, qualification, forecast training and
backtesting, contract validation, automated tests, and production builds. The
browser's profit, revenue, ranking, and interval arithmetic is intentionally a
small deterministic presentation calculation over cached inputs; it is not the
forecasting or data-processing workload and remains available offline. Local
machines are editing and inspection environments, not the source of truth for
an accepted snapshot or release.

### 4.2 Repository shape to implement

```text
app/                    # PWA source
pipeline/               # adapters, normalization, features, forecasts
config/                 # crop mappings, units, sources, thresholds
data/raw/               # gitignored local downloads or CI artifacts
public/data/v1/         # deployable JSON contract
tests/                  # unit, contract, pipeline, forecast, and browser tests
.github/workflows/      # test, scheduled refresh, and deployment workflows
```

## 5. Static JSON interfaces

All published files are UTF-8 JSON with no comments, `NaN`, or `Infinity`.
Dates use ISO 8601; timestamps use UTC. IDs are stable lowercase slugs. Currency
and units are explicit. Each contract has a version and is validated before
deployment.

| Path | Purpose | Required top-level fields |
|---|---|---|
| `/data/v1/manifest.json` | Atomic entry point and snapshot discovery | `schema_version`, `snapshot_id`, `generated_at`, `valid_until`, `artifacts`, `warnings` |
| `/data/v1/catalog.json` | Qualified crops, covered markets, and national-median location | `schema_version`, `snapshot_id`, `crops`, `locations` |
| `/data/v1/defaults.json` | Dated yield and cost defaults | `schema_version`, `snapshot_id`, `yield_defaults`, `cost_defaults` |
| `/data/v1/forecasts.json` | One- and three-month price forecasts | `schema_version`, `snapshot_id`, `forecasts` |
| `/data/v1/quality.json` | User-facing and audit-facing data/model status | `schema_version`, `snapshot_id`, `series`, `pipeline` |

### 5.1 Manifest contract

```json
{
  "schema_version": "1.0.0",
  "snapshot_id": "2026-08-24T060000Z-a1b2c3d4",
  "generated_at": "2026-08-24T06:00:00Z",
  "valid_until": "2026-10-08T06:00:00Z",
  "artifacts": [
    {
      "path": "catalog.json",
      "sha256": "64-lowercase-hex-characters",
      "bytes": 12345
    }
  ],
  "warnings": []
}
```

The PWA downloads the manifest network-first with a timeout, downloads all
referenced artifacts, verifies the snapshot IDs and checksums, and only then
promotes the set in IndexedDB. A partial snapshot is never displayed.

### 5.2 Catalog record shapes

```json
{
  "crop_id": "maize-white",
  "name": "White maize",
  "form": "dry grain",
  "sale_unit": "kg",
  "eligible_for_recommendation": true,
  "horizons_months": [1, 3]
}
```

```json
{
  "location_id": "market-wfp-1234",
  "name": "Example Market",
  "kind": "market",
  "state": "Example State",
  "latitude": 9.0,
  "longitude": 7.0,
  "covered_crop_ids": ["maize-white"]
}
```

The synthetic location `nigeria-national-median` has `kind` set to
`national_median`; it is never described as a national government statistic.

### 5.3 Default record shapes

```json
{
  "crop_id": "maize-white",
  "location_id": "nigeria-national-median",
  "yield_t_per_ha": 2.1,
  "source_id": "faostat-qcl",
  "source_url": "https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876",
  "as_of": "2024-12-31",
  "quality_flag": "official_or_reported",
  "override_required_confirmation": true
}
```

```json
{
  "crop_id": "maize-white",
  "location_id": "nigeria-national-median",
  "basis": "NGN_per_ha",
  "items": {
    "land_preparation": 0,
    "seed": 0,
    "fertilizer": 0,
    "pesticide": 0,
    "labour": 0,
    "irrigation": 0,
    "transport": 0,
    "storage": 0
  },
  "source_id": "nbs-nass-2023",
  "as_of": "2023-12-31",
  "stale": true
}
```

Zero is not silently interpreted as a real sourced cost. The UI treats missing
or zero seed values as incomplete and asks the farmer to confirm or replace
them before ranking that crop.

### 5.4 Forecast record shape

```json
{
  "crop_id": "maize-white",
  "location_id": "market-wfp-1234",
  "price_type": "wholesale",
  "currency": "NGN",
  "unit": "kg",
  "horizon_months": 3,
  "target_month": "2026-11",
  "point": 825.4,
  "lower_80": 690.2,
  "upper_80": 970.1,
  "model_id": "seasonal-naive-v1",
  "validation": {
    "origins": 12,
    "mae": 78.3,
    "wape": 0.146,
    "beats_seasonal_naive": false
  },
  "source_ids": ["wfp-hdx"],
  "last_observation_at": "2026-08-01",
  "generated_at": "2026-08-24T06:00:00Z",
  "status": "baseline"
}
```

The sample deliberately shows that the seasonal-naive model cannot claim to
beat itself. Candidate models receive `status: "validated"` only when they pass
the gates in Stage 4.

## 6. Decision calculation contract

All editable costs use `NGN/ha`; yield uses `t/ha`; forecast price uses
`NGN/kg`; area uses hectares.

```text
saleable_kg = yield_t_per_ha × 1,000 × hectares
total_cost = sum(cost_item_NGN_per_ha) × hectares
revenue_point = forecast_price_NGN_per_kg × saleable_kg
net_profit_point = revenue_point - total_cost
profit_per_ha = net_profit_point / hectares
```

The same calculation uses `lower_80` and `upper_80` to show a price-uncertainty
profit range. It does not invent a yield confidence interval. Crops are ranked
by point net profit only after area, every cost item, yield, and price basis are
confirmed. Ties are displayed as ties; risk does not silently change the rank.

The risk badge combines separately displayed evidence:

- historical month-to-month price-return volatility;
- forecast interval width relative to the point estimate;
- freshness and completeness warnings; and
- whether the price is farm-gate, wholesale proxy, or historical fallback.

Spoilage and storage-life risk remain absent until a crop-specific, citable
dataset and definitions are approved.

## 7. Staged roadmap and acceptance gates

### Stage 1 — Source and feasibility audit

**Work**

- Build a source register with URL, terms, authentication, cadence, format,
  price type, units, coverage, attribution, and redistribution decision.
- Download sample histories from WFP/HDX, World Bank RTFP, and FEWS NET; inspect
  FAO FPMA as an independent check.
- Define canonical crop, product-form, market, unit, and source mappings.
- Run the qualification gate and publish an audit report listing eligible and
  rejected crop/market series with reasons.
- Test FAOSTAT yield extraction and NBS cost-default extraction separately from
  price ingestion.

**Deliverables:** source register, raw-data manifest, mapping files, data profile,
and the selected 5–8 pilot crops and covered markets.

**Acceptance gate:** at least five crops pass every qualification and rights
check; at least one repeatable no-secret price ingestion path works; all units
and price types are resolvable; national medians can be computed with at least
three markets; otherwise the project stops at a calculator with farmer-entered
sale prices and makes no automated price claim.

### Stage 2 — Offline decision calculator

**Work**

- Build the mobile-first crop/location selection and per-hectare cost editor.
- Load sourced yield/cost defaults with source, date, and stale labels; allow
  manual override and remember inputs locally.
- Implement pure, deterministic calculation functions, ranked results, a profit
  comparison chart, and cost breakdown.
- Add plain-English recommendation text that states assumptions and does not
  imply a guarantee.
- Add a client-side printable/downloadable report using the same calculation
  object rendered on screen.

**Acceptance gate:** golden test fixtures reproduce revenue, costs, point profit,
profit interval, and ranking to the naira rounding rule; incomplete inputs
cannot be ranked; changing hectares scales revenue and per-hectare costs
correctly; the calculator works after network removal and a browser restart.

### Stage 3 — Automated data pipeline

**Work**

- Implement modular adapters and raw snapshot/checksum capture.
- Normalize dates, product forms, market IDs, price types, currencies, and units.
- Generate national medians only from comparable qualified market rows.
- Add schema, duplicate, range, freshness, coverage, and source-drift tests.
- Publish static JSON through a scheduled workflow while retaining the last
  known-good snapshot when any gate fails.

**Acceptance gate:** two consecutive scheduled dry runs produce schema-valid,
reproducible artifacts; rerunning against the same raw inputs produces identical
normalized content; a simulated source failure leaves the prior snapshot live
and adds a visible stale warning; no secret or paid service is required.

### Stage 4 — Forecasting and validation

**Work**

- Start with last-value and seasonal-naive baselines for one- and three-month
  direct horizons.
- Evaluate Random Forest and XGBoost only as candidates. Prophet is optional and
  is not a required dependency.
- Create lag and calendar features using only information available at each
  forecast origin. Evaluate NASA weather, CBN exchange-rate, and Pink Sheet
  features through ablation rather than assuming they help.
- Use rolling-origin backtests, never random train/test splits. Report MAE,
  WAPE, MAPE, interval coverage, validation origins, and the naive comparison by
  crop/location/horizon.
- Generate 80% empirical prediction intervals from out-of-fold residuals or an
  equally auditable method.

**Acceptance gate:** every published series has at least six three-month
backtest origins, no leakage, finite metrics, and a baseline result. A candidate
is labeled `validated` only if it improves median MAE and WAPE over the seasonal
naive baseline and has acceptable interval coverage. The original MAPE below
20% remains a target, not a blanket release promise; failures stay labeled
`baseline` or `experimental` and are disclosed in the UI.

### Stage 5 — Deployment and farmer readiness

**Work**

- Add the web app manifest, service worker, offline fallback, atomic snapshot
  update, install prompt, and cache-version cleanup.
- Deploy the static build to Cloudflare Pages and schedule the data job in the
  public repository. Monitor free-tier limits; do not enable billable Functions.
- Complete English microcopy, accessibility labels, keyboard navigation,
  responsive layout, low-bandwidth assets, source panels, and error messages.
- Externalize all text in `locales/en.json`; test pseudo-localization before
  commissioning Pidgin, Hausa, Yoruba, or Igbo translation.
- Verify that the downloadable report works online and offline and carries the
  same snapshot ID, inputs, sources, dates, intervals, and disclaimers as the UI.

**Acceptance gate:** install and offline flows pass on a low-end Android target
and a desktop browser; cached calculation and PDF/report generation make no
network request; a throttled first result is available within five seconds on
the agreed 3G test profile; automated accessibility checks have no critical
violations; no personal data leaves the device.

### Stage 6 — Pilot validation and expansion

**Work**

- Run moderated sessions with at least 10 farmers and 3 extension agents across
  more than one covered market.
- Test comprehension of `NGN/kg`, `NGN/ha`, yield, price type, national median,
  forecast range, stale data, and the non-guarantee message.
- Compare forecast snapshots with later observed prices and maintain a public
  model/data card per release.
- Prioritize expansion by observed demand and the same data qualification gate,
  not by an arbitrary top-30 label.
- Translate with native-speaker review only after the English decision flow is
  stable.

**Acceptance gate:** at least 80% of moderated participants complete a valid
comparison without facilitator correction, no critical unit or certainty
misunderstanding remains, at least 70% rate the result helpful, and forecast
performance/failure cases are documented. Expansion is approved one crop,
market, or language at a time only when its evidence gate passes.

## 8. Required changes to specification version 1.0

| Original area | Required pilot change | Reason |
|---|---|---|
| D-01/D-02: many live adapters, daily/hourly | Begin with one primary repeatable source plus independent checks; refresh weekly or at source cadence | Source data are mostly monthly and the browser must not depend on upstream uptime |
| C-01/C-02: top 30 crops | Ship only 5–8 crops selected by the documented qualification rule | Thirty comparable, fresh, market-level histories and defaults are not established |
| C-03: national, agro-zone, and local | Offer covered markets and a calculated national median only | Do not imply geographic precision unsupported by the source |
| CP-02: current API cost defaults | Manual `NGN/ha` inputs with dated, sourced, editable defaults | No credible comprehensive live Nigerian input-cost API is established |
| Y-01: agro-zone default from AfroTools/FAOSTAT | Use dated FAOSTAT national yield as a starting scenario and require confirmation | FAOSTAT is national annual data, not an agro-zone prescription |
| ML-02: one week, one month, three months | Publish one- and three-month horizons; defer weekly forecasts | Qualified target series are mainly monthly |
| ML-03: mandate Random Forest/XGBoost/Prophet | Use naive baselines first; promote a candidate only after time-series backtesting | Algorithm names do not guarantee forecast value |
| ML-04: mandatory weather and FX | Treat exogenous variables as time-safe candidates retained only after ablation | More features can add leakage or noise |
| ML-05: retrain after every ingestion | Retrain in batch only after a new snapshot passes QA | Prevent broken data from triggering deployment |
| ML-06/N-04: interval and universal MAPE below 20% | Always publish an auditable interval and metrics; retain 20% as a goal, not a promise | Performance varies by crop, market, horizon, and price regime |
| DA-03: maximum net profit recommendation | Keep point-profit ranking, but display uncertainty, source quality, and risk beside it | Highest point estimate is not the same as a guaranteed best choice |
| R-02: spoilage/storage life when available | Defer until a governed crop-specific source exists | Avoid unsupported lookup values |
| P-02: cache data and models | Cache versioned forecast/default JSON and calculate fully offline | A browser does not need the Python training model to reproduce the decision |
| P-03: five launch languages | Launch English first with locale-ready code; add reviewed translations later | Farmer-safe translation requires field and native-speaker validation |
| P-05: server-side PDF | Generate the report entirely in the browser | Preserves offline use, anonymity, and zero server cost |
| E-02: API error logging | Keep CI/job logs and publish sanitized health metadata | There is no always-on backend in the pilot |
| N-02: thousands of server connections | Validate static-host limits, asset size, and cache behaviour | Static delivery removes application-server concurrency |
| Section 4: FastAPI, PostgreSQL, Celery, cloud ML | Replace with scheduled Python jobs, versioned JSON, static PWA, and local storage | Meets the zero-cost and offline goals with fewer failure modes |

## 9. Verification strategy

### 9.1 Data and contracts

- Validate every published file against JSON Schema and reject unknown required
  enum values, nonfinite numbers, invalid dates, or snapshot mismatches.
- Assert uniqueness at the raw source key and canonical monthly series key.
- Test every accepted unit conversion with fixtures; unknown units fail rather
  than defaulting to kilograms.
- Check currency, price type, product form, missingness, freshness, market count,
  national-median contributors, source license metadata, and checksums.
- Detect upstream schema drift and retain the last known-good snapshot.
- Verify all source URLs and attributions in the release manifest.

### 9.2 Calculator

- Unit-test zero, decimal, large, and invalid values; reject negative area,
  yield, price, or cost inputs.
- Property-test area scaling, cost summation, interval ordering, stable sorting,
  ties, rounding, and equality between on-screen and report values.
- Ensure missing/zero defaults require confirmation and user overrides are not
  replaced during background snapshot refresh.
- Test farm-gate/wholesale/retail separation and every fallback warning.

### 9.3 Forecasts

- Verify feature timestamps are not later than each forecast origin.
- Use expanding or sliding rolling-origin evaluation with the same horizons used
  in production.
- Compare every candidate with last-value and seasonal-naive baselines.
- Report MAE, WAPE, MAPE, empirical interval coverage, and results split by
  observed versus modeled source rows.
- Test deterministic seeds, pinned dependencies, saved parameters, training data
  snapshot IDs, and reproducible predictions.

### 9.4 PWA, accessibility, and operations

- Run unit/component tests and browser end-to-end tests for first visit, update,
  offline restart, stale snapshot, corrupt download, and cache migration.
- Confirm service-worker caching of the app shell and IndexedDB persistence of
  structured data and user inputs.
- Test keyboard-only use, focus order, form labels, error association, color
  contrast, 200% zoom, screen-reader names, and chart text alternatives.
- Test a low-end mobile viewport and a throttled 3G profile; keep the initial
  shell and JSON small enough to meet the five-second result goal.
- Scan the built bundle and logs for secrets and verify that analytics, accounts,
  cookies, and remote translation services are absent.
- Exercise rollback by deliberately failing pipeline QA and by restoring a
  prior static snapshot.

## 10. Assumptions and operating constraints

- The pilot app and its automated pipeline can live in a public repository so
  current free CI allowances apply. Hosting uses a free platform subdomain; a
  branded domain is optional and outside the zero-cost promise.
- Free-tier terms and source endpoints can change. Limits and terms are checked
  before launch and at least quarterly; a future paid requirement triggers a
  design review, not an automatic charge.
- The app targets current evergreen mobile and desktop browsers. Users must
  complete one successful online load before offline use; browser storage can be
  cleared by the user or operating system.
- Farmer-entered inputs stay on the device. There are no accounts, cloud saves,
  or cross-device synchronization.
- Prices are scenarios for a documented market and supply-chain stage. They do
  not include an assumed transport path, trader margin, loss, credit cost, tax,
  or guaranteed buyer.
- Yield defaults are national historical reference values. Farmers must confirm
  yield and costs for their own conditions before a crop is ranked.
- The static snapshot cadence follows the slowest critical source and will
  normally be weekly even though most underlying prices are monthly. Hourly
  refresh has no evidence-based value for the pilot.
- A data or model failure reduces scope or falls back transparently; it never
  invents a crop, market, conversion, price, yield, cost, or confidence claim.

## 11. Deferred features

The following are explicitly outside the pilot and require a later evidence,
cost, privacy, or usability decision:

- expansion to 30 crops or uncovered markets;
- agro-ecological-zone, state-wide, LGA-wide, or market-town estimates without
  qualified observations;
- one-week forecasts from monthly data;
- live browser calls to agricultural, weather, or foreign-exchange APIs;
- an always-on FastAPI service, PostgreSQL, Celery, paid hosting, or server-side
  model inference;
- accounts, cloud scenario history, admin dashboards, and personal-data sync;
- Pidgin, Hausa, Yoruba, and Igbo releases before reviewed translation and field
  validation;
- server-side PDF generation, e-mailing reports, notifications, and reminders;
- spoilage/storage-life scores, risk-preference optimization, satellite/NDVI
  yield models, cooperative analysis, native apps, and USSD;
- automatic adoption of ADIP, Coldtivate, Farm Price API, Kaggle mirrors,
  AfroTools, or any new source before it passes the same source gate.

## 12. Delivery completion definition

The public pilot is complete only when all six stage gates pass; the current
static JSON contract is published; the PWA performs the full decision flow
offline; every recommendation is reproducible from its snapshot and inputs; all
source, freshness, price-basis, uncertainty, and fallback labels are visible;
and the pilot findings and limitations are documented.

If fewer than five crops pass the source audit, a useful offline calculator may
still be released, but it is not branded as a crop value predictor and it uses
farmer-entered expected sale prices instead of automated forecasts.

## 13. Research references

- [World Bank: Nigeria monthly food price estimates by product and market](https://microdata.worldbank.org/catalog/4503)
- [HDX HAPI: WFP food prices and market monitor data guide](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/food_security_nutrition_and_poverty/#food-prices-market-monitor)
- [FEWS NET: markets and trade data](https://fews.net/data/markets-and-trade)
- [FEWS NET: Nigeria weekly staple food price downloads](https://fews.net/nigeria-weekly-fews-net-staple-food-price-data-2)
- [FAO GIEWS: Food Price Monitoring and Analysis data and tools](https://www.fao.org/giews/data-tools/en/)
- [FAOSTAT: crop production, yield, and harvested-area dataset](https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876)
- [Nigeria NBS: National Agricultural Sample Survey 2023 materials](https://microdata.nigerianstat.gov.ng/index.php/catalog/173/related-materials)
- [NASA POWER: daily meteorological API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [Central Bank of Nigeria: exchange-rate and statistics data](https://www.cbn.gov.ng/data-page.html)
- [World Bank: Commodity Price Data, the Pink Sheet](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/world-bank-commodities-price-data-the-pink-sheet)
- [Iya Oloja: market directory API](https://nigerian-markets-api-docs.vercel.app/docs/openapi/listMarkets)
- [Cloudflare Pages free-plan limits](https://developers.cloudflare.com/pages/platform/limits/)
- [GitHub Actions billing and free public-repository usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [web.dev: offline PWA data with Cache Storage and IndexedDB](https://web.dev/learn/pwa/offline-data)
