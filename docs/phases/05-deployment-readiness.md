# Stage 5 — Deployment and Farmer Readiness

**Status:** In progress — browser readiness evidence collected 2026-09-07

**Baseline:** Stage 2 approved for the farmer-entered calculator at commit
`2e8802f`. Stage 3 and Stage 4 remain blocked by the unchanged Stage 1 source
gate.

## Boundary and objective

Stage 5 covers a static, English, offline calculator pilot. It does not
authorize automated prices, source-driven defaults, forecasts, accounts, cloud
saves, scheduled refresh, deployment, or public launch. Calculator drafts stay
in versioned `localStorage`. Any future automated-data path is separate and
conditional: IndexedDB snapshot storage, source checksum/provenance, and
explicit forecast/default gates are required.

The objective is an installable, recoverable, accessible, responsive, private
calculator usable after one successful online load.

## Readiness work package

1. Review the existing dirty implementation against `2e8802f` before accepting
   results. Inventory the manifest, service worker, registration, persistence,
   UI, CSS, icons, scripts, and pilot protocol separately from recovery and
   source-remediation artifacts.
2. Validate install/update in an isolated environment as needed. Finish the
   precache script, manifest, icons, service worker, registration, and base-path
   handling. Review the fixed v3 cache name and introduce build-specific cache
   identities to isolate updates; require complete,
   successful precache before promotion. Test install, successful and failed
   updates, old-cache cleanup, navigation/asset fallbacks, and restart.
3. Finish blocked-storage, failed-clear, removed-active-crop, blank-selection,
   malformed/unknown-draft, and reset states. Reset must check the clear result.
   Preserve entered calculations and the shared screen/report result batch.
4. Review local assets, help/privacy copy, units, labels, focus and keyboard
   flow, responsive layout, English string externalization, and low-bandwidth
   behavior. Confirm no third-party requests or user data egress.
5. Extend browser evidence for install/update/offline restart, persistence and
   selection errors, report parity, accessibility, mobile keyboard use, privacy,
   and declared throttling. Record first result time (target ≤5 seconds) with
   device/profile assumptions. Label browser emulation separately from real
   Android hardware.

## Evidence matrix

| Area | Evidence |
|---|---|
| Regression | `npm test`; `npm run typecheck`; `npm run build`; `npm run test:e2e` (baseline: 4 Node tests, 6 Chromium scenarios) |
| Data/Python | `python pipeline/source_audit.py`; `python pipeline/validate.py`; `python -m unittest discover -s tests -v` (26 at baseline) |
| Hygiene | targeted links/paths/status plus `git diff --check` |
| Cache/update | Build-specific identity, generated asset-list completeness, complete precache promotion, update recovery, cleanup |
| Offline/report | controlled online load, SW control, restart, report, screen/report parity |
| UX/privacy | storage/selection errors, accessibility, mobile keyboard, no third-party/user-data requests, declared throttle and ≤5-second first result |

Evidence must identify browser, device/profile, network conditions, cache
identity, and whether it used real Android or emulation. Physical Android and
participant evidence are pending and do not block this plan.

## Acceptance gate

Install and offline flows must pass on agreed Android and desktop targets;
cached calculation and reporting must require no network access; the first
result must meet five seconds under a recorded throttling profile;
accessibility must have no critical violations; and no personal data may leave
the device. Device and throttling proposals remain provisional until agreed.
Record real-device evidence separately from browser emulation and preserve a
working prior cache when an update fails. Planning alone satisfies none of
these implementation checks.

## Pilot handoff

Use untracked [`docs/pilot-protocol.md`](../pilot-protocol.md) as input for the
future evidence package. Hosting/base URL, physical-device confirmation,
participant sessions, and deployment approval remain future decisions. Do not
mark Stage 5 `Gate review` or `Approved` from code presence or planning alone.

## Progress log

| Date | Entry | Outcome |
|---|---|---|
| 2026-09-05 | Planning prepared; implementation verification pending. | No Stage 5 gate claim. Dirty implementation remains unverified on the primary workstation. |
| 2026-09-07 | Implemented and reviewed calculator-only PWA readiness. The generated precache now uses an immutable, base-scoped hash; failed precache installation removes only its candidate cache, and activation removes only superseded Fieldmargin caches. Manifest, service-worker registration, and preview support both `/` and `/fieldmargin/`. Draft recovery now handles blocked storage, failed clears, empty selections, and retired crop IDs. | Automated browser evidence passed for desktop Chromium and iPhone 13 emulation. No physical-device, participant, deployment, or Stage 5 gate claim. |

## Verification evidence — 2026-09-07

- Passed: `npm test` (4 calculator tests), `npm run typecheck`, `npm run build`, `npm run test:e2e` (desktop plus iPhone 13-emulation coverage), `python pipeline/validate.py`, `python -m unittest discover -s tests -v` (26 tests), and `git diff --check`.
- Passed separately: `E2E_BASE_PATH=/fieldmargin/ E2E_PORT=4186 npm run test:e2e -- --grep "supports a /fieldmargin/"`. It confirms base-scoped manifest paths, active service-worker control, and an offline reload. Root-path coverage verifies cache cleanup only after the replacement worker activates and confirms unrelated caches are retained.
- A fresh Terra review found and the executor corrected two material E2E gaps: the prior activation race in cache-cleanup coverage and missing non-root base-path coverage. The reviewer found no remaining material cache, persistence, or no-egress issue in the changed surfaces.
- Browser evidence is Chromium desktop and iPhone 13 emulation only. The in-app-browser runtime was unavailable in this environment, so no separate interactive-browser screenshot was captured. Static review found no third-party runtime requests or user-data egress.

The following gate evidence remains outstanding: real Android install/update and offline recovery, a recorded throttling profile with a measured first-result time of at most five seconds, a formal accessibility audit, and participant pilot evidence. These limits keep Stage 5 `In progress`.

## Next action

Obtain the outstanding real-device, throttling/performance, and accessibility evidence before Stage 5 gate review. Hosting, deployment, and public launch remain separately unauthorized.
