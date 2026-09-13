# npm Toolchain Fix Handoff

**Updated:** 2026-08-28  
**Project:** Fieldmargin Crop Value Planner  
**Purpose:** Resume the unfinished npm/toolchain repair in a new session.

## Current state

The calculator-only Stage 2 implementation is present in the working tree.
The code-level and Python checks pass, but the JavaScript development toolchain
has not been restored. There is currently no `package-lock.json`, and these
executables are missing from `node_modules/.bin/`:

- `tsc`
- `vite`
- `playwright`

The working tree contains substantial intentional uncommitted work from the
Stage 1 and Stage 2 implementation. Preserve it. Do not reset, clean, or
overwrite unrelated changes.

## Observed npm failure

The normal install command was attempted:

```powershell
npm install --no-audit --no-fund
```

It failed with `EPERM` while npm tried to open a temporary file in the default
cache:

```text
C:\Users\TOSHIBA\AppData\Local\npm-cache\_cacache\tmp\***
```

The reported fetch target was the Playwright package registry endpoint:
`https://registry.npmjs.org/@playwright%2ftest`.

A repository-local cache was also attempted:

```powershell
npm install --cache .npm-cache --no-audit --no-fund
```

That process produced no output for several minutes and was stopped. The
escalated retry of the normal install also ended without producing a lockfile
or installing the missing tools. A legacy `.npm-cache` directory may remain,
but it is ignored and inactive; `.npm-cache-repair` is the configured cache.

## npm cache location update — 2026-08-28

This project now uses a project-scoped npm cache on the D: drive:

```text
D:\Crop Value Predictor App\.npm-cache-repair
```

The earlier user-owned C: cache paths were not reliable. npm could not open
temporary files under `_cacache\tmp` even though the account ACLs showed full
control. The project cache now grants modify access to the Codex sandbox
service account, and npm can successfully query the registry from it.

```text
D:\Crop Value Predictor App\.npm-cache-repair
```

The project-local `.npmrc` contains:

```ini
cache=D:\Crop Value Predictor App\.npm-cache-repair
```

This setting is project-scoped and does not change npm’s cache for other
repositories. `npm view react version` succeeds with this configuration.
The original failure was an `EPERM` opening a cache temporary file, not a
missing Node or npm installation.

The full dependency install is still pending. It is slow because npm resolves
many platform-specific optional packages for Vite/Rollup. Use the repaired
cache and avoid the old C: cache paths. Do not delete the user-wide npm cache.

### What the latest attempts proved

The cache and registry path now work:

```text
npm config get cache
# D:\Crop Value Predictor App\.npm-cache-repair

npm view react version
# 19.2.8 at the time of verification
```

Verbose install attempts received successful package metadata responses for
React, React DOM, Playwright, Babel, esbuild, Rollup, and their optional
platform packages. Those attempts were manually stopped before npm completed.
They did not reproduce the earlier `EPERM` error.

This distinction matters for the next session:

- `EPERM` or `ENOENT` under `_cacache\tmp` is a cache/endpoint-protection
  failure;
- continuing HTTP `200` responses are slow dependency resolution, not a
  permission failure;
- no new `package-lock.json` or local tool executables exist yet, so the
  JavaScript toolchain is still incomplete.

The operational recovery sequence now lives in
[`SESSION_HANDOFF.md`](./SESSION_HANDOFF.md). This file is the detailed npm
history and troubleshooting appendix.

## Checks already passing

Run from `D:\Crop Value Predictor App`:

```text
npm test
```

Passed: 4 TypeScript calculator tests using Node's built-in
`--experimental-strip-types` support.

```text
python pipeline\validate.py
```

Passed: calculator-only snapshot validation.

```text
python -m unittest discover -s tests -v
```

Passed: 19 Python regression tests.

```text
git diff --check
```

Passed. Git reports only line-ending warnings and an inaccessible global
ignore file; there are no whitespace errors.

## Next-session recovery sequence

1. Read `SESSION_HANDOFF.md` completely, then read
   `docs/phases/02-offline-calculator.md`. Use this file only as the detailed
   npm troubleshooting appendix.
2. Inspect npm and Node versions without exposing credentials:

   ```powershell
   node --version
   npm --version
   npm config get cache
   npm config get registry
   Test-Path node_modules
   Test-Path package-lock.json
   ```

   Confirm the project-local cache is active:

   ```powershell
   npm config get cache
   # Expected: D:\Crop Value Predictor App\.npm-cache-repair
   ```

3. Resume the install using the repaired project-local cache:

   ```powershell
   npm install --no-audit --no-fund --fetch-timeout=60000 --fetch-retries=1 --loglevel=verbose
   ```

4. Confirm the configured cache path before retrying. If npm reports an
   `EPERM` under `.npm-cache-repair\_cacache\tmp`, inspect endpoint-protection
   quarantine/locks rather than deleting project data.

5. Confirm that `package-lock.json`, `tsc`, `vite`, and Playwright are present.
6. Run the complete Stage 2 verification:

   ```powershell
   npm test
   npm run typecheck
   npm run build
   npm run test:e2e
   python pipeline\validate.py
   python -m unittest discover -s tests -v
   ```

7. If Playwright is installed but Chromium is missing, install only the
   required browser runtime and rerun `npm run test:e2e`.
8. Update `docs/phases/02-offline-calculator.md` and
   `PROJECT_PROGRESS.md` with exact command results. Keep Stage 2 as
   **In progress** until typecheck, build, browser offline restart, and
   print-parity evidence pass.

## Important boundaries

- Do not print, commit, or request the contents of any GitHub token file.
- Do not stage `githubtoken.txt`, `audit-output-*`, `dist`, `.agents`, or npm
  cache directories.
- Do not push, deploy, dispatch workflows, reopen source remediation, integrate
  production data, or start Stage 3.
- Automated prices and forecast-driven recommendations remain prohibited.

## Current code fix from the previous session

`src/persistence.ts` now validates the complete nested saved-draft shape,
including all eight cost categories, before restoring it. Invalid JSON,
unknown versions, and malformed nested fields are removed and reported as a
recoverable blank draft. `src/calculations.test.ts` includes coverage for an
invalid price range and negative costs.
