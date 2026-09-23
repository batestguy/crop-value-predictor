# Deployment runbook

Updated: 2026-09-13

This project targets Cloudflare Pages. The static Vite build is published from
`dist/`, and the optional online lookup is a Pages Function at
`/api/price-research`. The function calls Tavily server-side; the Tavily key
must never be placed in the browser bundle, repository, or command arguments.

## Current state

- The static app builds locally with `npm.cmd run build`.
- The Pages Function source is `functions/api/price-research.ts`.
- `wrangler.toml` declares the Pages build output and project name
  `crop-value-predictor`.
- The local Vite route remains available for development and uses the retained
  raw snapshot before its Tavily fallback.
- The hosted Function uses the bounded Tavily fallback contract. It does not
  publish a price snapshot and it does not change `stage_1_approved`.
- The calculator-only static production deployment and hosted Function are live
  at `https://crop-value-predictor.pages.dev/`.
- The production deployment `16323e9b` was verified with Playwright on
  2026-09-13. A custom Soybean / dry grain request for Bauchi returned
  `NGN 110/kg`, a `NGN 100-120/kg` range, `2.5 t/ha`, and eight source links.
- `TAVILY_API_KEY` is configured only as an encrypted production Pages secret.
  It is not present in the repository, browser bundle, command output, or
  deployment files.
- The current production deployment is `2c672af6` (source commit `37dfec2`,
  2026-09-23). It carries the service-worker fix for the `ERR_FAILED`
  repeat-visit bug (PR #12). Pushing or merging to `main` does not deploy;
  CI only validates. Publish with the `wrangler pages deploy` command below.
- If `npx wrangler` fails with `EBUSY ... node_modules\workerd`, the install
  was interrupted by a file lock (usually antivirus). Retry with a fresh cache
  outside the repository, for example `npx.cmd -y --cache <dir> wrangler@4`.

## One-time account setup

Run these commands from the repository root in an authenticated terminal:

```powershell
npx.cmd wrangler login
npx.cmd wrangler pages project create crop-value-predictor
```

If the Pages project already exists, do not create a second one. Confirm the
actual project name in the Cloudflare dashboard or with `npx.cmd wrangler pages
project list`.

Set the secret through the Cloudflare secret store. Use the external key file
only as process input; do not copy its contents into this repository:

```powershell
Get-Content -Raw 'C:\Users\TOSHIBA\.config\crop-value-predictor\tavily-key.txt' |
  npx.cmd wrangler pages secret put TAVILY_API_KEY --project-name crop-value-predictor
```

The production secret was configured only after explicit owner authorization.
Do not repeat the command unless rotating the secret; use the external file
only as process input.

## Build and deploy

Run the checks before publishing:

```powershell
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
```

Then publish the committed build:

```powershell
npx.cmd wrangler pages deploy dist --project-name crop-value-predictor --branch main
```

The first deployment may require the Pages project to be created. Do not pass
the Tavily key to `wrangler`, and do not use `--env` values containing secrets.

## Hosted smoke test

After deployment, verify the public URL in a browser or with Playwright:

1. The calculator loads and can be used with networking unavailable.
2. The state field and **Find internet estimate** button are present.
3. A lookup requires an explicit click and does not silently change price.
4. **Use this estimate** is required before the returned value changes the
   scenario.
5. The result shows a low-confidence warning and source links.
6. A missing or invalid request fails closed and leaves manual entry available.
7. No Tavily key appears in page source, JavaScript assets, network responses,
   or browser storage.

Record the deployed URL, commit, timestamp, response status, and any provider
error without recording request bodies, keys, cookies, or farmer costs.

## Stop conditions

Stop before production publishing if any of these is true:

- Wrangler is not authenticated to the intended Cloudflare account.
- The Pages project or production domain is not identified.
- `TAVILY_API_KEY` is not configured as a server-side secret.
- The free provider quota or terms cannot be confirmed.
- The hosted route cannot be tested with the online provider unavailable.
- A lookup can populate or rank a crop without explicit farmer confirmation.

The current production deployment includes the optional hosted research route.
Its outputs are low-confidence editable context and require explicit farmer
confirmation. This does not promote online values into `public/data`, reopen
Stage 1, or enable automatic defaults/rankings. Continue the service/privacy/
rate-limit review before expanding the source set or request volume.
