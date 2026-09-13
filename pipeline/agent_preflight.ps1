[CmdletBinding()]
param(
    [string]$TokenFile = (Join-Path ([Environment]::GetFolderPath("UserProfile")) ".config\crop-value-predictor\github-token.txt"),
    [switch]$RequireToken
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$requiredFiles = @(
    "AGENTS.md",
    "SESSION_HANDOFF.md",
    ".agents\agent-policy.toml",
    "docs\agent-handoff-template.md",
    "docs\phases\02-offline-calculator.md",
    "package.json",
    "package-lock.json"
)

$missing = @($requiredFiles | Where-Object {
    -not (Test-Path -LiteralPath (Join-Path $ProjectRoot $_) -PathType Leaf)
})
if ($missing.Count -gt 0) {
    throw "Agent setup files missing: $($missing -join ', ')"
}

$projectRootFull = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
$tokenExists = Test-Path -LiteralPath $TokenFile -PathType Leaf
$tokenOutsideWorkspace = $true
if ($tokenExists) {
    $tokenPathFull = (Resolve-Path -LiteralPath $TokenFile).Path
    $tokenOutsideWorkspace = -not $tokenPathFull.StartsWith($projectRootFull, [StringComparison]::OrdinalIgnoreCase)
    if (-not $tokenOutsideWorkspace) {
        throw "Token file must be outside the project workspace: $tokenPathFull"
    }
}
if ($RequireToken -and -not $tokenExists) {
    throw "Token file not found: $TokenFile"
}

$trackedToken = @(& git -C $ProjectRoot ls-files -- githubtoken.txt)
if (-not [string]::IsNullOrWhiteSpace(($trackedToken -join ""))) {
    throw "githubtoken.txt is tracked; remove it from version control without exposing its contents"
}

$status = @(& git -C $ProjectRoot status --short)
[ordered]@{
    project_root = $ProjectRoot
    required_files_verified = $requiredFiles.Count
    token_path = $TokenFile
    token_present = $tokenExists
    token_outside_workspace = $tokenOutsideWorkspace
    githubtoken_tracked = $false
    working_tree_entries = $status.Count
} | ConvertTo-Json -Depth 4
