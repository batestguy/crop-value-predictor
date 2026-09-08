---
name: codex-cli-update
description: Update an installed OpenAI Codex CLI, verify the resulting version, and recover safely from Windows PowerShell installer issues. Use when the user asks to update, upgrade, or check the Codex CLI itself; do not use for updating an unrelated app or an API model.
metadata:
  short-description: Update and verify Codex CLI
---

# Codex CLI update

Use this skill for an explicit Codex CLI update request. Updating the CLI is an external system mutation, so obtain the user's authorization immediately before running the updater when it has not already been given.

## Workflow

1. Identify the active executable and record the starting version:

   ```powershell
   Get-Command codex | Select-Object Source,Path
   codex --version
   ```

   Do not assume npm is the installer. On Windows, Codex may be bundled with the OpenAI desktop app.

2. Prefer the CLI's own updater. Confirm its availability with `codex update --help`, then run:

   ```powershell
   codex update
   ```

3. Verify the result with `codex --version`. Report both the previous and resulting versions. If the version is unchanged, report that the updater found no newer release rather than claiming an upgrade.

## Windows fallback

If `codex update` fails while resolving `Get-FileHash` or another PowerShell command, do not replace the executable manually. Confirm the native Windows PowerShell binary exists:

```powershell
Test-Path 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
```

Retry the official installer through that explicit binary:

```powershell
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -ExecutionPolicy Bypass -Command "$env:CODEX_NON_INTERACTIVE='1'; irm https://chatgpt.com/codex/install.ps1 | iex"
```

Then run `codex --version` again. Preserve the user's existing configuration and authentication; the updater should only replace the CLI installation.

## Safety and reporting

- Keep the update scoped to Codex CLI. Do not update the user's project dependencies, desktop app policies, or API model configuration unless separately requested.
- Never print or modify authentication tokens, config secrets, or unrelated files.
- If the official installer cannot download or verify a release, stop and report the exact failure and the last verified version.
- Mention that the official Codex CLI documentation describes the standalone installer/update flow: https://developers.openai.com/codex/cli/
