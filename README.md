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
.npm-cache
```

This portable, project-scoped path avoids intermittent Windows `EPERM` errors
when npm writes temporary files in the user-profile cache and works in GitHub
Actions. Confirm the active cache with:

```powershell
npm config get cache
npm view react version
```

If the dependency install is interrupted, rerun `npm install` from the project
root. Do not delete the user-wide npm cache or change global npm settings.

The PWA caches its static shell and snapshot files through `public/sw.js`. The
observed-price snapshot remains calculator-only. The browser may load the
separately labelled World Bank modeled-estimate artifact as editable context;
it never calls an upstream market API, and the artifact is not an observed
retail, wholesale, or farmer selling price.

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

## Agent operating model

Repository-specific agent rules live in [`AGENTS.md`](./AGENTS.md). Start with
[`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md), then use the active phase
contract. The delegation roles, concurrency limit, handoff fields, and secret
boundary are recorded in [`.agents/agent-policy.toml`](./.agents/agent-policy.toml)
and [`docs/agent-handoff-template.md`](./docs/agent-handoff-template.md).

Run `pipeline\agent_preflight.ps1` before a handoff or credentialed artifact
operation. It checks the setup without contacting GitHub or printing secrets.

Stage 1 is **reopened for a web-first zero-secret FEWS NET/WFP qualification
attempt**. Until the five-crop technical gate, rights review, cross-check
review, two independent review passes, and explicit promotion approval all
pass, the shipped web calculator remains manual-price only. Suggestions are
editable local prefills, never forecasts or recommendations.
The operational response to failed, stale, malformed, or unqualified upstream
data is documented in the [upstream fallback runbook](./docs/upstream-fallback-runbook.md).
The ordered current action sequence is documented in
[`docs/next-actions.md`](./docs/next-actions.md).

## Active next move

Stage 6 is **Approved — literature-informed readiness**. The current release
target is a browser-first static PWA, not an Android-only application.
The protocol, search log, screening record, 20-source matrix, claim tiers, and
concern-to-requirement map are in
[`docs/academic-evidence-review.md`](./docs/academic-evidence-review.md) and
[`docs/academic-evidence-matrix.csv`](./docs/academic-evidence-matrix.csv).
The retained participant protocol and session kit are superseded for this
milestone and remain deferred future human-validation materials.

The copy-ready handoff is [`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md). The
Stage 6 gate is complete; the next active milestone is the Stage 1 web-first
remediation. Human validation, data promotion, deployment, or another scoped
milestone still requires separate authorization.
Literature-informed readiness must not be described as farmer-validated.

The latest fresh Stage 1 audit on 2026-09-10 failed closed because FEWS NET
returned HTTP 403 after bounded retries. World Bank, WFP/HDX, FAOSTAT, and NBS
artifacts were retained as immutable evidence, but qualification selected zero
crops. The calculator remains manual-input-only.

Production data integration, Stage 3, deployment, and public launch remain
blocked until their separate gates pass.

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
or commit the token; store it outside the workspace at the documented external
path. The legacy `githubtoken.txt` pattern remains ignored as defense in depth,
but an ignored in-repository token is not an accepted storage location.

Workflow dispatch, rerun, cancellation, approvals, pushes, and other write
actions have not been verified. They require appropriate write permissions and
must be tested explicitly through the same agent launcher:

```powershell
gh workflow run <workflow.yml> --repo batestguy/crop-value-predictor
```
# Current delivery boundary (2026-09-10)

The app is calculator-only: it compares complete farmer-entered crop scenarios
offline. The latest FEWS/WFP remediation audit failed closed on FEWS HTTP 403
and the unchanged technical gate, so observed automated prices and source-driven
rankings are not published. A separate modeled-estimate context lane is enabled
with explicit warnings and no Stage 1 approval effect. Stage 2 is **Approved** for calculator-only scenarios on validated
implementation commit `2e8802f`, with documentation/evidence in `8ef54f5`.
Clean-clone verification passed the npm, typecheck, build, six Chromium E2E,
and Python validation checks. This approval does not unlock automated prices,
defaults, forecasting, Stage 3/4, deployment, or public launch.
