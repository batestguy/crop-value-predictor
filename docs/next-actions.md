# Next actions and decision gates

**Updated:** 2026-09-13
**Current release posture:** calculator-only, browser-first PWA
**Active gate:** Phase 3A Gate A is authorized and in review. Stage 1 remains
closed as calculator-only fallback; observed prices remain unapproved.

This is the operational sequence after the 2026-09-10 fresh audit. It keeps
the existing technical thresholds and the manual-input fallback intact.

## Progress snapshot

| Area | Current state | Evidence |
| --- | --- | --- |
| Agent workflow | Implemented locally and globally | `AGENTS.md`, `.agents/agent-policy.toml`, global `.codex/AGENTS.md` |
| Offline calculator | Approved and validated | `docs/phases/02-offline-calculator.md` |
| Observed-price Stage 1 | Closed — fallback accepted; retrieval unavailable | `audit-output-fews-canary-20260913-34731386407` |
| Modeled context lane | Provisionally retained as editable context | `public/data/v1/modeled_price_suggestions.json` |
| Optional online research assist | Static calculator deployed; online Function disabled after 522 and key intentionally not uploaded | `docs/phases/03-online-research-assist.md`, `docs/deployment-runbook.md` |
| Custom crop starting values | Implemented locally: farmer can add any crop/form and request Tavily starting price, yield, and available cost categories for review | `src/main.tsx`, `pipeline/online_estimate.py`, `tests/e2e/calculator.spec.ts` |
| Automated pipeline / forecasting | Blocked | Stage 1 dependency |
| Browser verification | Complete: 22 passed, 1 intentional skip; Playwright confirms custom-crop research and JJMB UI flows | `tests/e2e/calculator.spec.ts`, `scripts/run-e2e.mjs` |

## Newly documented UI/product proposal

The proposal [`crop-expansion-and-nigeria-map.md`](./proposals/crop-expansion-and-nigeria-map.md)
records the implemented **Other crop** option, Nigeria flag watermark, and the
deferred interactive-map idea. Custom crops can request Tavily starting values,
but they remain editable context and require confirmation.

## Ordered action sequence

### 1. Close the browser verification gap — complete 2026-09-10

The Windows Playwright preview-server lifecycle was corrected with a direct
Vite preview server and a project-owned runner that builds, starts the server,
waits for readiness, runs Playwright, and cleans up child processes.

Acceptance evidence:

- modeled-context test passes;
- `npm.cmd run test:e2e` exits successfully with 19 passing tests and 1
  intentional skip;
- the suite confirms warning visibility, editable prefill behavior, no
  “qualified price” wording for modeled values, offline restart, print parity,
  and critical accessibility checks.

The runner and process-cleanup fix is recorded separately from product
behavior in `scripts/run-e2e.mjs` and `scripts/serve-preview.mjs`.

### 2. Keep the modeled lane under a narrow governance boundary — review complete 2026-09-10

Retain the current artifact only as an editable context prefill. Keep its
`modeled_estimate` type, source hash, source-aligned crop forms, attribution,
and “not observed” warning. Do not map milled rice to paddy or gari to fresh
cassava, and do not use the values as an observed-price or forecast claim.

The current product/rights review is provisional: attribution and
non-endorsement wording are covered, but any third-party restrictions must be
confirmed before broader redistribution. This lane does not alter
`stage_1_approved`.

### 3. Authorized observed-price retrieval investigation — closed 2026-09-13

The authorized cloud origin was used for two bounded canaries and one full
read-only Stage 1 audit. The cloud origin is reachable, but the FEWS data path
still fails closed. The corrected static-export canary then found zero official
CSV links on the Nigeria page.

Evidence:

- Canaries: `34434267144` and `34434497826`.
- Full audit: `34434760861`.
- Static canary: [34731386407](https://github.com/batestguy/crop-value-predictor/actions/runs/34731386407).
- Downloaded immutable artifact:
  `audit-output-fews-cloud-full-20260910-34434760861`.
- Static canary artifact:
  `audit-output-fews-canary-20260913-34731386407`.
- Qualification: `calculator_only_fallback`; zero FEWS eligible series and
  zero selected crops; `stage_1_approved: false`.

Do not promote or alter the public snapshot. Phase 1 is closed as fallback;
reopening requires a materially changed official access path or provider-supplied
export URL, followed by a new immutable audit and two independent reviews.

### 4. Phase 3A implementation — local adapter complete; hosted deployment remains separate

The optional hybrid research lane is documented in
[`03-online-research-assist.md`](./phases/03-online-research-assist.md). It may
The user authorized the local implementation slice. Custom crop support now
uses the same explicit-review boundary: Tavily may suggest a price, yield, and
available cost categories, but the farmer must confirm them and missing values
remain blank. Gate A is still reviewing
a multi-source internet aggregate,
including a candidate Hugging Face WFP/HDX snapshot, Cloudflare Workers/Workers
AI free-tier viability, Tavily Search free-tier viability, aggregation rules,
privacy/security controls, and the
candidate contract. The local Vite endpoint, Python estimator, review UI, and
draft provenance are now implemented and tested. No production refresh, live
snapshot, automatic default, or unconfirmed ranking input is authorized. The
static calculator is live at `https://crop-value-predictor.pages.dev/`.
The hosted Pages Function adapter and `wrangler.toml` exist, but the Function
deployment returned 522 and was replaced by a static-only production upload.
The Tavily key was intentionally not uploaded, so online lookup remains
disabled and falls back to manual entry. Resolving the Function runtime issue,
then configuring a server-side secret and running the hosted smoke test, is a
separate future action. See `docs/deployment-runbook.md` for the sequence.

### 5. Continue calculator-only readiness

While Stage 1 is blocked, permitted work is limited to browser-PWA quality:

- accessibility and responsive behavior;
- local draft recovery and print parity;
- performance and offline behavior;
- clear source, modeled-context, and uncertainty wording;
- reproducible CI and clean-clone verification.

Do not add automated price defaults, browser calls to upstream sources,
forecasting, source stitching, participant claims, or production-data
promotion.

### 6. Re-open Stage 1 only after a materially changed source path

Stage 3 can begin only after Stage 1 technical and rights approval. Stage 4
also requires an approved Stage 3 data pipeline and validation design. Deployment
or public launch requires separate authorization even though browser readiness
is approved.

## Exit criteria for the next project update

The next progress update should contain either:

- an explicit decision to remain calculator-only for the next release slice; or
- an explicitly authorized immutable observed-price audit with a qualification
  result and review status; or
- an explicitly authorized Phase 3A implementation gate with its source,
  rights, privacy, free-tier, service, and test evidence.

Until then, the truthful status is: useful offline calculator, modeled context
available with warnings, observed prices unapproved, forecasting blocked, and
not farmer-validated.

If Phase 3A proceeds beyond local development, it must record explicit
entry-gate evidence and deployment authorization. The local slice does not
authorize public online retrieval or deployment.
