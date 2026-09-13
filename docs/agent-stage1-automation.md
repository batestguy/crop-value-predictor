# Agent automation: Stage 1 cloud artifact verification

> **Supporting procedure.** The prior Stage 1 fallback remains immutable and
> source remediation was reopened on 2026-09-09. Use the current session
> handoff for the active milestone; this document describes artifact recovery
> and fail-closed qualification only.

This is the repeatable procedure for resuming Stage 1. It verifies an
explicitly supplied GitHub Actions run and its evidence artifact, downloads the
artifact into the audit directory, checks the current static-export layout and
manifest hash/size, and runs the project qualification script. The FEWS API is
diagnostic only; it is never merged with the static export.

## Required tools

- Windows PowerShell 5+.
- GitHub CLI (`gh`) on `PATH`.
- Python on `PATH` from the project environment.
- A persistent terminal for the approximately 59 MB artifact download.
- A fine-grained GitHub token limited to this repository with Actions and
  Contents read-only access.

The token must be stored outside the repository. The automation loads it into
`GH_TOKEN` for one PowerShell process and never prints or persists it. The
default location is `%USERPROFILE%\.config\crop-value-predictor\github-token.txt`.

## Run

From any directory:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1" -RunId 123456789
```

To force a fresh download:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1" -RunId 123456789 -ForceDownload
```

Override the default token path when needed:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1" -RunId 123456789 -TokenFile "C:\secure\github-token.txt"
```

The script rejects any token file located inside the project workspace, even
when supplied through `-TokenFile`. Run the non-network preflight before an
artifact operation:

```powershell
& "D:\Crop Value Predictor App\pipeline\agent_preflight.ps1"
```

## Automated checks

The script stops on failure if authentication, repository metadata, run status,
optional caller-supplied commit/branch/artifact metadata, expiry, required
files, FEWS provenance, or the static file's byte count/SHA-256 is incorrect.
The current required layout is:

- `raw_manifest.json`
- `source_profile.json`
- `qualification_report.json`
- `raw/fews-net.csv`

The FEWS manifest record must contain the discovery page, resolved export URL,
filename/content type, cutoff month, byte count, and SHA-256. It then runs:

```powershell
python pipeline\qualification.py --audit-dir audit-output-cloud-static --cutoff-month 2026-08
```

The final JSON summary records the workflow conclusion, artifact metadata,
static-export provenance, qualification status, selected crop count, and the
Stage 1 decision. `gate_review_rights_and_transaction_type_pending` is not
approval: the rights and transaction-type gates still require review. If fewer
than five crops qualify technically, the result is `calculator_only_fallback`
and no automated price claims are permitted.

## Agent stop rules

- Do not use this audit to introduce automated prices or production data.
- Calculator-only web work may proceed under its reviewed plan.
- Do not write qualification artifacts to `public/data`.
- Do not commit the token, credentials, or raw audit files.
- If access fails, record the exact error and request the downloaded artifact
  directory instead of broader repository credentials.
- Rotate any token exposed in chat, logs, screenshots, or command history.

## Historical verification result

The prior authenticated artifact regeneration verified:

- GitHub login: `batestguy`.
- Workflow `32812781709`: completed successfully on branch
  `stage1-adapter-fix` at the expected commit.
- Artifact `9550678887`: present, unexpired, expected size and digest.
- All seven required artifact files: present.
- World Bank profile: 17,464 total rows, 17,390 through the cutoff, 74 rows
  after the cutoff, 74 locations, 73 source markets, and one aggregate.
- FAOSTAT: 616 matching Nigerian yield records covering 13 distinct crop
  forms, normalized to `t/ha`.
- Qualification: `calculator_only_fallback`, zero selected crops, zero
  eligible series; best FEWS recent completeness is 69.4%.

That historical decision was `calculator_only_fallback`: artifact access and
manifest verification succeeded, but the technical crop gate did not reach
five selected crops. It is not a substitute for the current static-export
artifact. If the static export is unavailable or fails schema checks, retain
the calculator-only product and record the exact fail-closed reason.
