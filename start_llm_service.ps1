$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    Write-Host "Missing backend virtual environment." -ForegroundColor Red
    exit 1
}

$command = @"
Set-Location -LiteralPath '$backendDir'
Write-Host 'Starting local LLM service on http://127.0.0.1:8011' -ForegroundColor Magenta
& '$backendPython' -m uvicorn local_llm_service:app --host 127.0.0.1 --port 8011
"@

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $command
)

Write-Host "Started local LLM service window." -ForegroundColor Yellow
Write-Host "LLM endpoint: http://127.0.0.1:8011/v1/chat/completions" -ForegroundColor Yellow

