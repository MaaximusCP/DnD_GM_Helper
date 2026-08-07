$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pidFile = Join-Path $projectRoot "data\gm-ai.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "No hi ha cap instància registrada de GM AI."
    exit 0
}

$savedPid = Get-Content -LiteralPath $pidFile
$process = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
if ($process) { Stop-Process -Id $process.Id }
Remove-Item -LiteralPath $pidFile -Force
Write-Host "GM AI aturat."

