[CmdletBinding()]
param(
    [string]$TokenFile = (Join-Path ([Environment]::GetFolderPath("UserProfile")) ".config\crop-value-predictor\github-token.txt"),
    [string]$Repo = "batestguy/crop-value-predictor",
    [Parameter(Mandatory = $true)][long]$RunId,
    [string]$Branch = "",
    [string]$ExpectedSha = "",
    [string]$ArtifactName = "",
    [long]$ExpectedArtifactId = 0,
    [string]$ExpectedDigest = "",
    [string]$AuditDir = "D:\Crop Value Predictor App\audit-output-cloud-static",
    [string]$CutoffMonth = "2026-08",
    [switch]$ForceDownload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ProjectRootFull = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
$RequiredFiles = @(
    "raw_manifest.json",
    "source_profile.json",
    "qualification_report.json",
    "raw/fews-net.csv"
)

function Invoke-GhJson([string[]]$Arguments) {
    $text = & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "gh failed: gh $($Arguments -join ' ')" }
    return ($text -join "`n" | ConvertFrom-Json)
}

if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) {
    throw "Token file not found: $TokenFile"
}
$TokenPathFull = (Resolve-Path -LiteralPath $TokenFile).Path
if ($TokenPathFull.StartsWith($ProjectRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    throw "TokenFile must be outside the project workspace: $TokenPathFull"
}

# Keep the token in this process only. Never write it to a config file or log it.
$env:GH_TOKEN = (Get-Content -Raw -LiteralPath $TokenPathFull).Trim()
if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN)) { throw "Token file is empty" }

$login = (& gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0 -or $login -ne "batestguy") { throw "GitHub authentication failed or returned an unexpected login" }

$repoInfo = Invoke-GhJson @("api", "repos/$Repo", "--jq", "{name,private,default_branch}")
$run = Invoke-GhJson @("run", "view", "$RunId", "--repo", $Repo, "--json", "status,conclusion,headSha,headBranch,jobs")
if ($ExpectedSha -and $run.headSha -ne $ExpectedSha) { throw "Run SHA mismatch: expected $ExpectedSha, got $($run.headSha)" }
if ($Branch -and $run.headBranch -ne $Branch) { throw "Run branch mismatch: expected $Branch, got $($run.headBranch)" }
if ($run.status -ne "completed" -or $run.conclusion -ne "success") { throw "Workflow is not successful: $($run.status)/$($run.conclusion)" }

$artifactResponse = Invoke-GhJson @("api", "repos/$Repo/actions/runs/$RunId/artifacts")
if ($ArtifactName) {
    $artifact = @($artifactResponse.artifacts | Where-Object { $_.name -eq $ArtifactName }) | Select-Object -First 1
} else {
    $artifact = @($artifactResponse.artifacts | Where-Object { $_.name -match "source-audit|fews-canary" }) | Select-Object -First 1
}
if ($null -eq $artifact) { throw "Artifact not found: $ArtifactName" }
if ($ExpectedArtifactId -and [long]$artifact.id -ne $ExpectedArtifactId) { throw "Artifact ID mismatch" }
if ($artifact.expired) { throw "Artifact is expired" }
if ($ExpectedDigest -and $artifact.digest -ne $ExpectedDigest) { throw "Artifact digest mismatch" }

New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
$existingManifest = Join-Path $AuditDir "raw_manifest.json"
if ($ForceDownload -or -not (Test-Path -LiteralPath $existingManifest)) {
    & gh run download $RunId --repo $Repo --name $artifact.name --dir $AuditDir
    if ($LASTEXITCODE -ne 0) { throw "Artifact download failed" }
}

$missing = @($RequiredFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $AuditDir $_) -PathType Leaf) })
if ($missing.Count -gt 0) { throw "Required artifact files missing: $($missing -join ', ')" }

$manifest = Get-Content -Raw -LiteralPath (Join-Path $AuditDir "raw_manifest.json") | ConvertFrom-Json
$profile = Get-Content -Raw -LiteralPath (Join-Path $AuditDir "source_profile.json") | ConvertFrom-Json
$fews = @($manifest.records | Where-Object { $_.source_id -eq "fews-net" }) | Select-Object -First 1
if ($null -eq $fews) { throw "FEWS manifest record is missing" }
if ($fews.status -ne "downloaded") { throw "FEWS static export was not downloaded: $($fews.error)" }
if ($fews.path -ne "fews-net.csv") { throw "FEWS artifact is not the canonical raw/fews-net.csv layout" }
if (-not $fews.discovery_page -or -not $fews.resolved_export_url) { throw "FEWS static manifest lacks discovery and resolved export provenance" }
$fewsPath = Join-Path $AuditDir (Join-Path "raw" $fews.path)
$fewsBytes = (Get-Item -LiteralPath $fewsPath).Length
$fewsHash = (Get-FileHash -LiteralPath $fewsPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ([long]$fews.bytes -ne $fewsBytes) { throw "FEWS byte count mismatch: manifest $($fews.bytes), file $fewsBytes" }
if ($fews.sha256.ToLowerInvariant() -ne $fewsHash) { throw "FEWS SHA-256 mismatch" }

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
    fews_static_export = [ordered]@{
        path = $fews.path
        bytes = $fews.bytes
        sha256 = $fews.sha256
        discovery_page = $fews.discovery_page
        resolved_export_url = $fews.resolved_export_url
        filename = $fews.filename
        content_type = $fews.content_type
        rows = $fews.rows
    }
    qualification_status = $report.status
    selected_crops = @($report.selected_crops).Count
    technical_gate_passed = $report.technical_gate_passed
    stage_1_decision = if ($report.technical_gate_passed -and @($report.selected_crops).Count -ge 5) { "gate_review_rights_and_transaction_type_pending" } else { "calculator_only_fallback" }
}
Write-Output ($summary | ConvertTo-Json -Depth 6)
