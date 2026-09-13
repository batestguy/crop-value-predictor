# Next actions and decision gates

**Updated:** 2026-09-13
**Current release posture:** calculator-only, browser-first PWA
**Active gate:** Stage 1 is closed as calculator-only fallback; observed prices
remain unapproved.

This is the operational sequence after the 2026-09-10 fresh audit. It keeps
the existing technical thresholds and the manual-input fallback intact.

## Progress snapshot

| Area | Current state | Evidence |
| --- | --- | --- |
| Agent workflow | Implemented locally and globally | `AGENTS.md`, `.agents/agent-policy.toml`, global `.codex/AGENTS.md` |
| Offline calculator | Approved and validated | `docs/phases/02-offline-calculator.md` |
| Observed-price Stage 1 | Closed — fallback accepted; retrieval unavailable | `audit-output-fews-canary-20260913-34731386407` |
| Modeled context lane | Provisionally retained as editable context | `public/data/v1/modeled_price_suggestions.json` |
| Automated pipeline / forecasting | Blocked | Stage 1 dependency |
| Browser verification | Complete: 17 passed, 1 intentional skip, clean process exit | `tests/e2e/calculator.spec.ts`, `scripts/run-e2e.mjs` |

## Ordered action sequence

### 1. Close the browser verification gap — complete 2026-09-10

The Windows Playwright preview-server lifecycle was corrected with a direct
Vite preview server and a project-owned runner that builds, starts the server,
waits for readiness, runs Playwright, and cleans up child processes.

Acceptance evidence:

- modeled-context test passes;
- `npm.cmd run test:e2e` exits successfully with 17 passing tests and 1
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

### 4. Continue calculator-only readiness

While Stage 1 is blocked, permitted work is limited to browser-PWA quality:

- accessibility and responsive behavior;
- local draft recovery and print parity;
- performance and offline behavior;
- clear source, modeled-context, and uncertainty wording;
- reproducible CI and clean-clone verification.

Do not add automated price defaults, browser API calls, forecasting, source
stitching, participant claims, or production-data promotion.

### 5. Re-open Stage 1 only after a materially changed source path

Stage 3 can begin only after Stage 1 technical and rights approval. Stage 4
also requires an approved Stage 3 data pipeline and validation design. Deployment
or public launch requires separate authorization even though browser readiness
is approved.

## Exit criteria for the next project update

The next progress update should contain either:

- an explicit decision to remain calculator-only for the next release slice; or
- an explicitly authorized immutable observed-price audit with a qualification
  result and review status.

Until then, the truthful status is: useful offline calculator, modeled context
available with warnings, observed prices unapproved, forecasting blocked, and
not farmer-validated.
