$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$frontendNodeModules = Join-Path $frontendDir "node_modules"
$backendEnvFile = Join-Path $backendDir ".env"
$llmEnabled = $false

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path $Path)) {
        Write-Host $Message -ForegroundColor Red
        exit 1
    }
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $line = Get-Content $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return ($line -split "=", 2)[1].Trim()
}

Assert-PathExists -Path $backendDir -Message "Missing backend directory."
Assert-PathExists -Path $frontendDir -Message "Missing frontend directory."
Assert-PathExists -Path $backendPython -Message "Missing backend virtual environment. Install backend dependencies first."
Assert-PathExists -Path $frontendNodeModules -Message "Missing frontend node_modules. Run npm install in frontend first."

$llmFlag = Get-EnvValue -Path $backendEnvFile -Key "LLM_ENABLED"
if ($llmFlag -and $llmFlag.ToLower() -eq "true") {
    $llmEnabled = $true
}

$llmCommand = @"
Set-Location -LiteralPath '$backendDir'
Write-Host 'Starting local LLM service on http://127.0.0.1:8011' -ForegroundColor Magenta
& '$backendPython' -m uvicorn local_llm_service:app --host 127.0.0.1 --port 8011
"@

$backendCommand = @"
Set-Location -LiteralPath '$backendDir'
Write-Host 'Starting backend on http://127.0.0.1:8000' -ForegroundColor Cyan
& '$backendPython' -m uvicorn app.main:app --reload
"@

$frontendCommand = @"
Set-Location -LiteralPath '$frontendDir'
Write-Host 'Starting frontend on http://127.0.0.1:5173' -ForegroundColor Green
npm run dev
"@

if ($llmEnabled) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $llmCommand
    )

    Start-Sleep -Seconds 2
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCommand
)

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCommand
)

if ($llmEnabled) {
    Write-Host "Started LLM, backend and frontend windows." -ForegroundColor Yellow
    Write-Host "LLM:      http://127.0.0.1:8011" -ForegroundColor Yellow
} else {
    Write-Host "Started backend and frontend windows." -ForegroundColor Yellow
}
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Yellow
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Yellow
