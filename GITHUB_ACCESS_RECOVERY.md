# GitHub access and artifact-download recovery

> This remains a security/recovery reference, not the active project handoff.
> Stage 1 artifact verification is complete and its calculator-only fallback
> was accepted on 2026-08-27. Use [`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md)
> for the current next move.

Use this guide when a workflow succeeds but the agent cannot inspect its
artifacts, logs, or repository metadata. It is intentionally repository- and
workflow-agnostic.

## Goal

Give the agent process the minimum read-only GitHub access needed to inspect
repositories, Actions runs, logs, and artifacts. Do not grant write, admin, or
organization-wide access unless a separate task explicitly requires it.

## Required access

For a private repository, use either:

- a fine-grained token restricted to the target repository with **Actions:
  Read-only** and **Contents: Read-only**, or
- an approved GitHub CLI/OAuth login with equivalent read access.

For public repositories, metadata may work without authentication, but Actions
artifact downloads can still require authentication.

## Authenticate in the same environment as the agent

The most common failure is authenticating in the user’s PowerShell while the
agent runs in a separate sandbox. Credentials must be visible to the process
that runs `gh`.

Preferred environment-variable method:

```powershell
$env:GH_TOKEN = (Get-Content -Raw "C:\secure\github-token.txt").Trim()
gh api user --jq .login
```

Expected output is the intended GitHub username. Never print the token, commit
the token file, or paste the token into chat.

If using GitHub CLI configuration instead:

```powershell
gh auth login --hostname github.com --with-token
gh auth status
```

If the agent sandbox cannot access the user’s CLI credential store, use
`GH_TOKEN` in the agent’s process environment or run the download in the
authenticated terminal and place the resulting files in the shared workspace.

## Verify repository and run access

```powershell
gh api repos/OWNER/REPOSITORY --jq '{name,private,default_branch}'
gh run view RUN_ID --repo OWNER/REPOSITORY --json status,conclusion,headSha,jobs
gh api repos/OWNER/REPOSITORY/actions/runs/RUN_ID/artifacts
```

Record the run conclusion, artifact name, artifact ID, size, expiry, and digest.

## Download an artifact

```powershell
New-Item -ItemType Directory -Force .\artifact-download | Out-Null
gh run download RUN_ID `
  --repo OWNER/REPOSITORY `
  --name ARTIFACT_NAME `
  --dir .\artifact-download
```

For large artifacts, use a persistent terminal/session and allow several
minutes. A short-lived sandbox command may time out without meaning the
artifact is unavailable.

## Diagnose common failures

- **401 Bad credentials:** token is invalid, expired, revoked, malformed, or
  not visible to the current process.
- **403:** token is valid but lacks repository or Actions artifact read access,
  or an organization policy requires approval.
- **404:** repository, run, or artifact identifier is wrong, or the token cannot
  see the private resource.
- **TLS/credential-store errors:** the shell environment cannot use its GitHub
  credential store; use `GH_TOKEN` in the same process or the user terminal.
- **Timeout on download:** keep the command running persistently and verify
  available disk space; do not repeatedly regenerate credentials.

## Security cleanup

Revoke any token exposed in chat, logs, screenshots, command history, or a
committed file. Store replacement tokens outside the repository. Remove local
token files after use and check `git status` before committing.

## Completion checklist

- `gh api user` succeeds in the agent environment.
- Repository metadata is readable.
- The target run is visible and its conclusion is recorded.
- Artifact metadata is visible and unexpired.
- Artifact download completes and files are inspectable.
- Credentials are not committed or exposed.
