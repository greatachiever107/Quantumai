# publish.ps1 - one-command update: pull, unpack a downloaded frontend.zip, commit, push.
# Usage (from this folder):   .\publish.ps1 "what you changed"
param([string]$Message = "Update")

Set-Location $PSScriptRoot

Write-Host "1/3 Pulling the latest from GitHub (includes the weekly bot's commits)..."
git pull
if ($LASTEXITCODE -ne 0) {
    Write-Host "git pull failed. Stop here and check the message above."
    exit 1
}

$zip = Join-Path $HOME "Downloads\frontend.zip"
if (Test-Path $zip) {
    Write-Host "2/3 Unpacking frontend.zip over the frontend folder..."
    tar -xf $zip -C $PSScriptRoot
    Remove-Item $zip
} else {
    Write-Host "2/3 No frontend.zip in Downloads - skipping that step."
}

Write-Host "3/3 Publishing..."
git add .
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Nothing new to publish."
    exit 0
}
git commit -m $Message
git push
if ($LASTEXITCODE -eq 0) {
    Write-Host "Done. Vercel and Render will redeploy in a minute or two."
}
