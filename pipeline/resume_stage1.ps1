[CmdletBinding()]
param(
    [string]$TokenFile = "D:\Crop Value Predictor App\githubtoken.txt",
    [string]$Repo = "batestguy/crop-value-predictor",
    [long]$RunId = 32812781709,
    [string]$Branch = "stage1-adapter-fix",
    [string]$ExpectedSha = "61c3192178225479b15137623940b291adaf79b3",
    [string]$ArtifactName = "source-audit-61c3192178225479b15137623940b291adaf79b3",
    [long]$ExpectedArtifactId = 9550678887,
    [string]$ExpectedDigest = "sha256:211cb7c8adf6b3cf25e48d0ad3c5c4e15d90f155bfbd4dac081ca8acd0745564",
    [string]$AuditDir = "D:\Crop Value Predictor App\audit-output-cloud-auth",
    [string]$CutoffMonth = "2026-07",
    [switch]$ForceDownload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$RequiredFiles = @(
    "raw_manifest.json",
    "source_profile.json",
    "qualification_report.json",
    "raw/world-bank-rtfp.json",
    "raw/fews-net.csv",
    "raw/faostat-qcl.zip",
    "raw/nbs-nass-2023.pdf"
)

function Invoke-GhJson([string[]]$Arguments) {
    $text = & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "gh failed: gh $($Arguments -join ' ')" }
    return ($text -join "`n" | ConvertFrom-Json)
}

if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) {
    throw "Token file not found: $TokenFile"
}

# Keep the token in this process only. Never write it to a config file or log it.
$env:GH_TOKEN = (Get-Content -Raw -LiteralPath $TokenFile).Trim()
if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN)) { throw "Token file is empty" }

$login = (& gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0 -or $login -ne "batestguy") { throw "GitHub authentication failed or returned an unexpected login" }

$repoInfo = Invoke-GhJson @("api", "repos/$Repo", "--jq", "{name,private,default_branch}")
$run = Invoke-GhJson @("run", "view", "$RunId", "--repo", $Repo, "--json", "status,conclusion,headSha,headBranch,jobs")
if ($run.headSha -ne $ExpectedSha) { throw "Run SHA mismatch: expected $ExpectedSha, got $($run.headSha)" }
if ($run.headBranch -ne $Branch) { throw "Run branch mismatch: expected $Branch, got $($run.headBranch)" }
if ($run.status -ne "completed" -or $run.conclusion -ne "success") { throw "Workflow is not successful: $($run.status)/$($run.conclusion)" }

$artifactResponse = Invoke-GhJson @("api", "repos/$Repo/actions/runs/$RunId/artifacts")
$artifact = @($artifactResponse.artifacts | Where-Object { $_.name -eq $ArtifactName }) | Select-Object -First 1
if ($null -eq $artifact) { throw "Artifact not found: $ArtifactName" }
if ([long]$artifact.id -ne $ExpectedArtifactId) { throw "Artifact ID mismatch" }
if ($artifact.expired) { throw "Artifact is expired" }
if ($artifact.digest -ne $ExpectedDigest) { throw "Artifact digest mismatch" }

New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
$existingManifest = Join-Path $AuditDir "raw_manifest.json"
if ($ForceDownload -or -not (Test-Path -LiteralPath $existingManifest)) {
    & gh run download $RunId --repo $Repo --name $ArtifactName --dir $AuditDir
    if ($LASTEXITCODE -ne 0) { throw "Artifact download failed" }
}

$missing = @($RequiredFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $AuditDir $_) -PathType Leaf) })
if ($missing.Count -gt 0) { throw "Required artifact files missing: $($missing -join ', ')" }

$manifest = Get-Content -Raw -LiteralPath (Join-Path $AuditDir "raw_manifest.json") | ConvertFrom-Json
$profile = Get-Content -Raw -LiteralPath (Join-Path $AuditDir "source_profile.json") | ConvertFrom-Json
$wb = @($profile.profiles | Where-Object { $_.source_id -eq "world-bank-rtfp" }) | Select-Object -First 1
if ($null -eq $wb) { throw "World Bank profile is missing" }

Push-Location $ProjectRoot
try {
    & python pipeline\qualification.py --audit-dir $AuditDir --cutoff-month $CutoffMonth
    if ($LASTEXITCODE -ne 0) { throw "Qualification script failed" }
}
finally { Pop-Location }

$report = Get-Content -Raw -LiteralPath (Join-Path $AuditDir "qualification_report.json") | ConvertFrom-Json
$summary = [ordered]@{
    login = $login
    repository = $repoInfo.name
    workflow = [ordered]@{ id = $RunId; status = $run.status; conclusion = $run.conclusion; sha = $run.headSha; branch = $run.headBranch }
    artifact = [ordered]@{ id = $artifact.id; name = $artifact.name; size = $artifact.size_in_bytes; expired = $artifact.expired; digest = $artifact.digest }
    audit_dir = $AuditDir
    required_files_verified = $RequiredFiles.Count
    world_bank_rows = $wb.rows
    world_bank_rows_through_cutoff = $wb.rows_through_cutoff
    world_bank_rows_after_cutoff = $wb.rows_after_cutoff
    locations = $wb.in_scope_location_count
    source_markets = $wb.in_scope_market_count
    national_aggregate_rows = $wb.national_aggregate_count
    qualification_status = $report.status
    selected_crops = @($report.selected_crops).Count
    technical_gate_passed = $report.technical_gate_passed
    stage_1_decision = if ($report.technical_gate_passed -and @($report.selected_crops).Count -ge 5) { "gate_review_rights_and_transaction_type_pending" } else { "calculator_only_fallback" }
}
Write-Output ($summary | ConvertTo-Json -Depth 6)
