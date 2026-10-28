# Season Margin

> Know your margin before you plant.

Season Margin is an offline-first crop comparison tool for Nigerian farmers. It
helps you test a season using your own land, yield, selling price, and cost
assumptions before you plant.

> **Renamed on 2026-10-27.** This project was previously called *Fieldmargin*.
> That name belongs to [fieldmargin.com](https://www.fieldmargin.com/), an established UK
> farm-management product selling farm mapping and field-job planning — the same category
> as this app. The name was changed to avoid trading on it. Saved drafts and cached
> app shells written under the old name are migrated automatically
> (`LEGACY_STORAGE_KEY` in `src/persistence.ts`, `LEGACY_CACHE_PREFIX` in `public/sw.js`).
>
> The deployment URL is unchanged: the Cloudflare Pages project is still
> `crop-value-predictor`, so the live link above keeps working.

<p align="center">
  <a href="https://crop-value-predictor.pages.dev/"><strong>Open the live app</strong></a>
  &nbsp; | &nbsp;
  <a href="./SESSION_HANDOFF.md">Read the project handoff</a>
  &nbsp; | &nbsp;
  <a href="./docs/deployment-runbook.md">Deployment runbook</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/works-offline-17483f?style=flat-square" alt="Works offline">
  <img src="https://img.shields.io/badge/React-18-17483f?style=flat-square" alt="React 18">
  <img src="https://img.shields.io/badge/TypeScript-checked-17483f?style=flat-square" alt="TypeScript checked">
  <img src="https://img.shields.io/badge/status-live-f26b4f?style=flat-square" alt="Live status">
</p>

<p align="center">
  <img src="./docs/screenshots/seasonmargin-overview.png" alt="Season Margin home screen: Know your margin before you plant, the field-note card, and the first calculator step" width="960">
</p>

## Watch the walkthrough

[![Play the Season Margin walkthrough: four crops ranked, with the decision view and price basis visible](./docs/screenshots/decision-view.png)](./docs/media/demo-walkthrough.mp4)

**[Download the walkthrough — MP4, 3.1 MB, 1:04](./docs/media/demo-walkthrough.mp4)**

One continuous take of the whole workflow, captioned step by step: set an area,
add a crop that is not on the list, ask the research assistant for starting
values, replace the returned price with a local one, complete the other crops by
hand, read the ranking, print the report, and reload with the network turned off.

> The recording is a production build served locally with the research endpoint
> stubbed, so the take is deterministic and spends no Tavily credits. The app is
> unmodified — only the numbers returned by that single request are fixed.

Stage-by-stage table, reproduction commands, and capture settings:
[Demo walkthrough](./docs/demo-walkthrough.md).

## Live demo

**[Launch the Season Margin demo](https://crop-value-predictor.pages.dev/)**

The production demo includes the offline calculator, custom crops, bag
equivalents, and optional Quick Research through the server-side Tavily route.

`https://crop-value-predictor.pages.dev/`

It works in desktop and phone browsers (Chrome, Brave, Safari, Firefox). On a
phone you can also use **Add to Home screen** to install it; after the first
visit the calculator keeps working offline.

> **Access note:** Releases before 2026-09-23 could show `ERR_FAILED` on a
> second visit in Chromium-based browsers (Brave, Chrome, Android) because of a
> service-worker bug. The fix is live and was verified on desktop and a phone
> profile. If a browser that visited earlier still shows the error, reload once;
> if it persists, clear the site data for `crop-value-predictor.pages.dev`.

## Why it exists

Farm decisions often begin with incomplete information. Season Margin makes the
assumptions visible, lets you change them, and shows the effect on your margin.
The calculator stays useful without an internet connection, while an optional
research button can find a starting point when you want outside context.

## What you can do

| | Capability | What it means in practice |
| --- | --- | --- |
| **01** | Compare crops | Enter one field and compare a shortlist using the same calculation rules. |
| **02** | Add any crop | Add a crop name and product form, such as `Soybean` + `dry grain` or `Carrot` + `fresh`. |
| **03** | Research assumptions | Ask for a price, range, yield, and available cost categories for a Nigerian state. |
| **04** | Think in local units | See price in NGN/kg and the equivalent value for your bag size. |
| **05** | Keep control | Review every returned value and choose **Use this estimate** before it changes your scenario. |
| **06** | Work privately | Drafts stay in the browser on the device; the calculator itself works offline. |

## See it in action

### The decision view

Three crops ranked by net profit from the figures the farmer typed. Every row
carries its own price basis, and the basis strip names the units.

<p align="center">
  <img src="./docs/screenshots/decision-view.png" alt="Decision view ranking Rice, Soybean and White maize by net profit, with the price basis and units shown" width="960">
</p>

### A research result, before you accept it

The estimate, range, bag equivalents, warning, and evidence links appear below
the button that requested them. Nothing changes in the scenario until
**Use this estimate** is pressed.

<p align="center">
  <img src="./docs/screenshots/research-output.png" alt="Quick Research panel showing 1,250 naira per kilogram, a 1,100 to 1,400 range, starting yield and costs, evidence links, and the Use this estimate button" width="520">
</p>

### The printable report

The same figures, the same basis, and the same wording as the screen.

<p align="center">
  <img src="./docs/screenshots/print-report.png" alt="Printable scenario report listing each crop's area, yield, selling price, price basis, profit, and cost breakdown" width="720">
</p>

### On a phone

The same calculator at 390 px wide, with the field-note layout intact.

<p align="center">
  <img src="./docs/screenshots/mobile.png" alt="Season Margin on a 390 pixel wide phone screen" width="300">
</p>

## How Quick Research works

Quick Research is an optional assistant, not an automatic price feed.

```mermaid
flowchart LR
    A[Farmer enters crop, form, and state] --> B{Usable retained local data?}
    B -- Yes --> C[Prepare local starting values]
    B -- No --> D[One bounded Tavily search]
    D --> E[Parse price, range, yield, costs, and sources]
    C --> F[Show editable research output]
    E --> F
    F --> G{Farmer clicks Use this estimate?}
    G -- No --> H[Keep manual values]
    G -- Yes --> I[Apply selected starting values]
```

The public route is a Cloudflare Pages Function at
`/api/price-research`. The Tavily credential is stored as an encrypted
server-side secret and never shipped to the browser. The request is bounded and
the response is labelled low-confidence. A missing, malformed, or unsupported
answer fails safely back to manual entry.

## Try a custom crop

1. Open the [live app](https://crop-value-predictor.pages.dev/).
2. Enter your land area and a Nigerian state, for example `Bauchi`.
3. Under **Another crop**, enter a crop name and its product form.
4. Add it to the shortlist and complete the crop assumptions.
5. Click **Find all starting values** to see the research package below the
   button.
6. Check the source, unit, date, and warning. Click **Use this estimate** only
   when the values are suitable as your starting assumptions.

For example, the deployed flow was tested with `Soybean` / `dry grain` in
`Bauchi` and returned a low-confidence `NGN 110/kg` midpoint from an
`NGN 100-120/kg` range, `2.5 t/ha`, and eight source links.

## Run locally

### Requirements

- Node.js with npm
- Python 3 for the local research helper and validation suite

Install dependencies and start the development server:

```powershell
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite. The offline calculator works without a
Tavily key. For local Quick Research, provide `TAVILY_API_KEY` only to the
server process or use the documented external credential path; never commit a
key, put it in browser code, or paste it into a repository file.

## Validate a change

Run the smallest relevant checks while developing, then the full suite before
release:

```powershell
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
python -m unittest discover -s tests -v
```

The current release has passed the calculation tests, TypeScript check, Vite
build, browser tests, Python validation suite, and a public Playwright smoke
test against the production research route.

## Project map

The main code is organized into `src/` for the React calculator,
`functions/` for the hosted research endpoint, `pipeline/` for local data
helpers, `public/data/` for versioned context artifacts, `docs/` for phase
contracts, deployment notes, screenshots, and the demo video, and `scripts/` for
build and documentation tooling such as `demo-capture.mjs`.

## Product boundaries

- The calculator is offline-first and manual-input-first.
- Research suggestions are editable context, not observed prices or forecasts.
- Online values never automatically rank crops or become default assumptions.
- The hosted route does not publish a price snapshot or reopen Stage 1.
- Stage 1 remains **Closed - fallback accepted**, with observed-price approval
  unresolved.
- Automated data integration and forecasting remain separately gated.

These boundaries are intentional: a quick web answer can be stale, use the
wrong unit, or describe a different market. The farmer remains the final
decision-maker.

## Documentation

- [Next-session handoff](./SESSION_HANDOFF.md)
- [Demo walkthrough](./docs/demo-walkthrough.md)
- [Project progress](./PROJECT_PROGRESS.md)
- [Next actions and gates](./docs/next-actions.md)
- [Offline calculator phase](./docs/phases/02-offline-calculator.md)
- [Online research-assist phase](./docs/phases/03-online-research-assist.md)
- [Deployment runbook](./docs/deployment-runbook.md)
- [Custom crop and Nigeria visual proposal](./docs/proposals/crop-expansion-and-nigeria-map.md)

## About

Season Margin is the JJMB crop-planning project: practical planning support for
Nigerian farms, with clear assumptions and a gentler path from uncertainty to a
decision.
