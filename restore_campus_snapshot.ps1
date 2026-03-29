$ErrorActionPreference = "Stop"

$snapshotBranch = "archive/campus-risk-20260329-133046"
$snapshotTag = "snapshot-campus-risk-20260329-133046"
$snapshotCommit = "187875f"

Set-Location -LiteralPath $PSScriptRoot

$dirty = git status --porcelain
if ($dirty) {
    Write-Host "Working tree is not clean. Commit or stash current changes before restoring the snapshot." -ForegroundColor Yellow
    exit 1
}

git fetch --all --tags | Out-Null
git switch $snapshotBranch

$currentCommit = (git rev-parse --short HEAD).Trim()
if ($currentCommit -ne $snapshotCommit) {
    Write-Host "Warning: snapshot branch is not at the recorded commit $snapshotCommit." -ForegroundColor Yellow
    Write-Host "Current branch commit: $currentCommit" -ForegroundColor Yellow
    Write-Host "Reference tag: $snapshotTag" -ForegroundColor Yellow
} else {
    Write-Host "Restored snapshot branch $snapshotBranch at commit $snapshotCommit." -ForegroundColor Green
}
