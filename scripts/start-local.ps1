$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonExe = Join-Path $backendRoot ".venv\Scripts\python.exe"
$pidFile = Join-Path $projectRoot "data\gm-ai.pid"

if (Test-Path -LiteralPath $pidFile) {
    $existingPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Start-Process "http://localhost:8000"
        Write-Host "GM AI ja estava actiu."
        exit 0
    }
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    python -m venv (Join-Path $backendRoot ".venv")
    & $pythonExe -m pip install -r (Join-Path $backendRoot "requirements.txt")
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "dist\index.html"))) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Cal Node.js 20 o superior per fer la primera compilació del frontend."
    }
    Push-Location $frontendRoot
    try {
        npm ci
        npm run build
    } finally {
        Pop-Location
    }
}

$process = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id

$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 1
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 250
}
if (-not $ready) { throw "El backend no ha arrencat correctament." }

Start-Process "http://localhost:8000"
Write-Host "GM AI actiu a http://localhost:8000"
Write-Host "Per aturar-lo: powershell -ExecutionPolicy Bypass -File scripts\stop-local.ps1"

