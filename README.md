# Fieldmargin Crop Value Planner

An offline-first, anonymous crop comparison tool for Nigerian farmers. The
current UI is a runnable pilot-seed implementation of the delivery plan in
[`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md).

## Run locally

```bash
npm install
npm run dev
```

For a production build:

```bash
npm run build
python pipeline/validate.py
```

The PWA caches its static shell and snapshot files through `public/sw.js`. The
current snapshot is intentionally labeled as seed data; replace it with the
audited pipeline output before presenting automated forecasts as production
evidence.

## Project layout

- `src/` — responsive React/TypeScript decision interface and pure calculations
- `public/data/v1/` — versioned static JSON interfaces
- `pipeline/` — no-network snapshot validation and future source adapters
- `IMPLEMENTATION_PLAN.md` — staged roadmap, source policy, and acceptance gates

The browser never calls upstream agricultural APIs. User-entered costs and
yield overrides remain local to the device, and recommendations include source,
freshness, price type, uncertainty, and fallback context.

## Delivery progress

Implementation follows the review-gated stages in
[`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md). The live status dashboard
is [`PROJECT_PROGRESS.md`](./PROJECT_PROGRESS.md), with an evidence record for
each baseline and delivery stage under [`docs/phases/`](./docs/phases/).

The prototype release architecture is documented in
[`docs/batch-training-architecture.md`](./docs/batch-training-architecture.md),
and the active Stage 1 source register is
[`docs/source-register.md`](./docs/source-register.md).

Cloud execution rules are documented in
[`docs/cloud-compute.md`](./docs/cloud-compute.md). GitHub Actions is the
authoritative environment for data processing, forecasting, validation, tests,
and production builds; the browser performs only the small deterministic
scenario calculation required for offline use.
