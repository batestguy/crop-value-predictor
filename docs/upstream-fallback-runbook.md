# Upstream price-run fallback runbook

## Purpose and safety rule

Use this runbook when a source retrieval fails, is stale, malformed, or does
not pass qualification. The public calculator must continue to use its
last-known-good snapshot. Do not manually copy raw source data into
`public/data/v1`, and do not run promotion to "try" an unreviewed result.

The promotion command validates its inputs before writing, stages all release
files atomically, and writes `manifest.json` last. A failed retrieval or a
failed promotion therefore does not replace the published snapshot.

## Triage (offline and read-only)

From the repository root, inspect the most recent audit directory and validate
the currently published calculator snapshot:

```powershell
python pipeline/validate.py
Get-Content audit-output\raw_manifest.json
Get-Content audit-output\qualification_report.json
```

Use the actual audit directory if it differs from `audit-output`. Check these
fields before any release decision:

| Condition | Evidence | Required decision |
|---|---|---|
| Retrieval failure | a required `raw_manifest.json` record is not `downloaded` | Stop. Keep the calculator-only/last-known-good snapshot. |
| Malformed or altered artifact | qualification fails manifest size or SHA-256 verification | Stop. Quarantine the audit directory; acquire a new immutable artifact in a later reviewed run. |
| Stale data | `rejected_series` includes `latest_value_over_75_days_old` | Stop. Do not waive freshness or alter observation dates. |
| Unqualified data | `technical_gate_passed` is false, fewer than five selected crops, or no publishable series | Stop. Keep manual user-entered prices. |
| Mapping/crosswalk gap | `cross_source_check.status` is `not_comparable` or `unavailable` | Stop. A reviewer must add a source-scoped canonical-market crosswalk and approve it. |
| Cross-source disagreement | `disagreement_count` is non-zero | Stop. Investigate the source rows; WFP must not fill or merge FEWS history. |

## Recovery path

1. Record the failure class, audit directory, source ID, retrieval timestamp,
   checksum, and report checksum in the release ticket.
2. Leave `public/data/v1/manifest.json` and all existing public artifacts
   unchanged. The browser keeps serving the manifest it already discovers.
3. Correct the upstream issue outside the release directory: obtain a new raw
   artifact through the approved source-audit process, then generate a new
   audit directory. Never edit a recorded raw artifact or its manifest.
4. Re-run qualification against that new immutable directory:

   ```powershell
   python pipeline/qualification.py --audit-dir <new-audit-dir> --cutoff-month YYYY-MM
   Get-Content <new-audit-dir>\qualification_report.json
   ```

5. If the result is still failed, stale, malformed, or unqualified, close the
   release attempt as **calculator-only fallback**. No promotion is needed.

## Release checkpoint (only after a qualified rerun)

A human reviewer must verify all of the following before creating approval
JSON:

- `technical_gate_passed` is true and at least five selected crop forms are
  present.
- FEWS is the primary source and its source artifact, total, pagination, and
  Nigeria geography passed validation.
- Cross-source evidence is `comparable` with zero disagreements.
- Every promoted crop form maps exactly to an app crop. Do not map milled rice
  to paddy or gari to fresh cassava.
- Every source market has a reviewed source-scoped canonical market identity.
- Rights, attribution, and redistribution review are explicit.
- The approval JSON is bound to both the qualification-report SHA-256 and the
  current `config/mappings.json` SHA-256, and includes the mapping version and
  `mapping_reviewed: true`.

Only then run the manual, local promotion command:

```powershell
python pipeline/promote_price_suggestions.py --audit-dir <new-audit-dir> --approval <approval.json>
python pipeline/validate.py
python -m unittest discover -s tests -p "test_*.py"
```

If either command fails, treat it as a failed promotion: do not retry with
edited public files. Preserve the error output with the ticket, fix the audit
or approval input, and restart from the qualification step.

## Verification and evidence

Before closing either a fallback or a release, run:

```powershell
python -m py_compile pipeline/source_audit.py pipeline/qualification.py pipeline/promote_price_suggestions.py pipeline/validate.py
python -m unittest discover -s tests -p "test_*.py"
python pipeline/validate.py
```

The test `test_malformed_or_unapproved_promotion_preserves_last_known_good_snapshot`
in `tests/test_sources.py` specifically proves that a rejected promotion leaves
the prior manifest unchanged. This runbook intentionally contains no network
command: retrieval should occur only in its separately authorized audit run.
