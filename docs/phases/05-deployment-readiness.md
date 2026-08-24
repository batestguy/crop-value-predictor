# Stage 5 — Deployment and Farmer Readiness

**Status:** Not started  
**Dependency:** Stages 2–4 approval

## Objective

Make the validated pilot installable, accessible, low-bandwidth, private, and
fully usable after its first successful online load.

## Work and evidence required

- Implement atomic manifest/checksum verification, IndexedDB promotion, cache
  migration, stale handling, install behavior, and offline report generation.
- Complete accessibility, responsive, low-bandwidth, localization-ready,
  privacy, and browser tests.
- Configure GitHub/Cloudflare deployment only after explicit authorization; the
  repository currently has no remote.

## Acceptance gate

Install and offline flows pass on the agreed Android and desktop targets; cached
calculation and reporting make no network request; the throttled first result
meets five seconds; accessibility has no critical violations; and no personal
data leaves the device.

## Progress log

The current service worker is a seed cache implementation. No Stage 5 gate work
has been accepted.
