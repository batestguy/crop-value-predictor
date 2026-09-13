# Agent automation: Stage 1 cloud artifact verification

> **Historical/supporting procedure.** Stage 1 was closed on 2026-08-27 with
> the calculator-only fallback accepted. Do not use this document as the active
> session resume path unless source remediation is explicitly reopened. The
> active handoff is [`../AGENT_RESUME_INSTRUCTIONS.md`](../AGENT_RESUME_INSTRUCTIONS.md).

This is the repeatable procedure for resuming Stage 1. It verifies the exact
GitHub Actions run and artifact recorded in `AGENT_RESUME_INSTRUCTIONS.md`,
downloads the artifact into the audit directory, checks the required files, and
runs the project qualification script.

## Required tools

- Windows PowerShell 5+.
- GitHub CLI (`gh`) on `PATH`.
- Python on `PATH` from the project environment.
- A persistent terminal for the approximately 59 MB artifact download.
- A fine-grained GitHub token limited to this repository with Actions and
  Contents read-only access.

The token must be stored outside the repository. The automation loads it into
`GH_TOKEN` for one PowerShell process and never prints or persists it.

## Run

From any directory:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1"
```

To force a fresh download:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1" -ForceDownload
```

The default token path is `D:\Crop Value Predictor App\githubtoken.txt`.
Override it when needed:

```powershell
& "D:\Crop Value Predictor App\pipeline\resume_stage1.ps1" -TokenFile "C:\secure\github-token.txt"
```

## Automated checks

The script stops on failure if authentication, repository metadata, run status,
branch, commit SHA, artifact ID, digest, expiry, required files, or World Bank
profile is incorrect. It then runs:

```powershell
python pipeline\qualification.py --audit-dir audit-output-cloud-auth --cutoff-month 2026-07
```

The final JSON summary records the workflow conclusion, artifact metadata,
profile counts, qualification status, selected crop count, and the Stage 1
decision. `gate_review_rights_and_transaction_type_pending` is not approval:
the rights and transaction-type gates still require review. If fewer than five
crops qualify technically, the result is `calculator_only_fallback` and no
automated price claims are permitted.

## Agent stop rules

- Do not use this audit to introduce automated prices or production data.
- Calculator-only Stage 2 work may proceed under its reviewed 2026-08-27 plan.
- Do not write qualification artifacts to `public/data`.
- Do not commit the token, credentials, or raw audit files.
- If access fails, record the exact error and request the downloaded artifact
  directory instead of broader repository credentials.
- Rotate any token exposed in chat, logs, screenshots, or command history.

## Latest verification result

On 2026-08-26, the authenticated artifact regeneration verified:

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

The resulting decision is `calculator_only_fallback`: artifact access and
manifest verification succeeded, but the technical crop gate did not reach
five selected crops. Rights and transaction-type review also remain pending.
The fallback outcome was reviewed and accepted on 2026-08-27. Agents may work
on the strict farmer-input calculator, but must not publish automated price
claims or begin Stage 3 from this result.
