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
