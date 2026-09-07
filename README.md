# Fieldmargin Crop Value Planner

An offline-first, anonymous crop comparison tool for Nigerian farmers. The
current UI is the strict calculator-only fallback defined by the delivery plan in
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

### npm on the managed Windows workspace

The repository uses the project-scoped cache configured in `.npmrc`:

```text
D:\Crop Value Predictor App\.npm-cache-repair
```

This avoids intermittent Windows `EPERM` errors when npm writes temporary
files in the user-profile cache. Confirm the active cache with:

```powershell
npm config get cache
npm view react version
```

If the dependency install is interrupted, rerun `npm install` from the project
root. Do not delete the user-wide npm cache or change global npm settings.

The PWA caches its static shell and snapshot files through `public/sw.js`. The
current snapshot is calculator-only. The browser loads a selling-price prefill
only from a versioned, same-origin `price_suggestions.json` advertised by a
Stage 1-approved manifest; it never calls an upstream market API.

## Project layout

- `src/` — responsive React/TypeScript decision interface and pure calculations
- `public/data/v1/` — versioned static JSON interfaces
- `pipeline/` — no-network snapshot validation and future source adapters
- `IMPLEMENTATION_PLAN.md` — staged roadmap, source policy, and acceptance gates

The browser never calls upstream agricultural APIs. User-entered costs and
yield overrides remain local to the device, and recommendations include source,
freshness, price type, uncertainty, and fallback context.

## Development checks

The calculator arithmetic is isolated in `src/calculations.ts` and covered by
the TypeScript tests in `src/calculations.test.ts`:

```bash
npm test
python pipeline/validate.py
python -m unittest discover -s tests -v
```

Stage 1 is **reopened for a zero-secret FEWS NET qualification attempt**. Until
the five-crop technical gate, rights review, cross-check review, and explicit
promotion approval all pass, the shipped calculator remains manual-price only.
Suggestions are editable local prefills, never forecasts or recommendations.

## Active next move

The decision-complete execution plan is
[`docs/phases/02-offline-calculator.md`](./docs/phases/02-offline-calculator.md),
and the copy-ready session brief is [`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md).
Stage 2 is approved for calculator-only pilot and deployment-readiness
planning. The next step is to define that calculator-only readiness work.

Production data integration, source remediation, Stage 3, deployment, and
public launch are outside this milestone.

Stage 2 is **Approved** on commit `2e8802f`: clean-clone
verification passed npm tests, typecheck, build, six Chromium E2E scenarios,
and the Python validation suite. The primary
workstation's partial `node_modules` is an operational limitation and is
excluded from the product checkout.

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

## GitHub Actions access for agents

The verified agent recovery procedure is documented in
[`docs/agent-stage1-automation.md`](./docs/agent-stage1-automation.md) and
[`GITHUB_ACCESS_RECOVERY.md`](./GITHUB_ACCESS_RECOVERY.md).

When `GH_TOKEN` is loaded in its own process, the agent has verified that it
can authenticate as `batestguy`, list repository workflows and recent Actions
runs, inspect the pinned Stage 1 run and artifact, and download and qualify the
artifact.

Every agent must be started through a process that loads the token; logging in
from an unrelated terminal does not make the credential visible to isolated
agents:

```powershell
$env:GH_TOKEN = (Get-Content -Raw "C:\secure\github-token.txt").Trim()
gh api user --jq .login
gh workflow list --repo batestguy/crop-value-predictor
gh run list --repo batestguy/crop-value-predictor
```

Use a repository-scoped fine-grained token. Actions and Contents read-only
permissions are sufficient for inspection and artifact downloads. Never print
or commit the token; an external secure location is preferred. The local
`githubtoken.txt` filename is ignored by `.gitignore`.

Workflow dispatch, rerun, cancellation, approvals, pushes, and other write
actions have not been verified. They require appropriate write permissions and
must be tested explicitly through the same agent launcher:

```powershell
gh workflow run <workflow.yml> --repo batestguy/crop-value-predictor
```
# Current delivery boundary (2026-09-04)

The app is calculator-only: it compares complete farmer-entered crop scenarios
offline. WFP/HDX remediation is closed after failing the unchanged technical
qualification gate, so automated prices and source-driven rankings are not
published. Stage 2 is **Approved** for calculator-only scenarios on validated
implementation commit `2e8802f`, with documentation/evidence in `8ef54f5`.
Clean-clone verification passed the npm, typecheck, build, six Chromium E2E,
and Python validation checks. This approval does not unlock automated prices,
defaults, forecasting, Stage 3/4, deployment, or public launch.
