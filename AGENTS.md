# Repository Agent Instructions

These instructions apply to every agent working in this repository. The
user-level Codex policy remains the general authority; this file adds the
project-specific boundary and operating contract.

## Start here

1. Read `SESSION_HANDOFF.md`.
2. Read the phase document for the requested work. For the active product,
   `docs/phases/02-offline-calculator.md` is the acceptance contract.
3. Inspect `git status --short` before editing. Preserve existing user changes.
4. Use `.agents/agent-policy.toml` and
   `docs/agent-handoff-template.md` for delegation and handoffs.

## Product boundary

The approved product is an offline, calculator-only experience. Only complete
farmer-entered scenarios may drive rankings or recommendations. Automated
prices, forecast values, upstream APIs, production defaults, model training,
Stage 3/4, deployment, and public launch remain blocked unless a later gate
explicitly authorizes them.

Do not publish or promote audit artifacts into `public/data`. Treat modeled
estimates as context only and label them clearly; they must not affect the
calculator decision.

## Agent operating rules

- Keep small or tightly coupled work with the main agent.
- Delegate only independent, substantial, broad, or high-risk work.
- Use at most two concurrent subagents and do not recursively delegate.
- Use `terra_executor` for normal implementation, `luna_worker` for narrow
  mechanical work, and `terra_reviewer` for an independent review when risk
  warrants it. Reserve Sol and Astra for the cases defined in the global policy.
- Standard handoffs use `fork_turns = "none"` and must include objective,
  acceptance criteria, scope, constraints, risks, and validation commands.
- The receiving agent reports evidence and gate state before making changes.

## Secrets and external access

Never print, commit, copy into logs, or place credentials in this repository.
GitHub tokens belong outside the workspace, preferably at
`%USERPROFILE%\.config\crop-value-predictor\github-token.txt`, and must be
loaded only into the process that needs them. `pipeline/resume_stage1.ps1`
rejects token files inside the project directory.

Use repository-scoped read-only GitHub access for artifact inspection. Do not
dispatch, rerun, cancel, approve, push, deploy, or change credentials without
explicit authorization.

## Validation

Run the smallest relevant checks first. For a normal application change, use:

```powershell
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

Run `npm.cmd run test:e2e` and `python -m unittest discover -s tests -v`
when the changed surface or the handoff requires them. Run
`pipeline\agent_preflight.ps1` before a session handoff or credentialed
artifact operation.

Do not claim completion without reporting the commands run, their result, and
any remaining boundary or gate.
