param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPy = Join-Path $AppDir "venv\Scripts\python.exe"
$SetupScript = Join-Path $AppDir "setup_riskguard.ps1"
$UiScript = Join-Path $AppDir "riskguard_ui.py"

function Ensure-Venv {
    if (Test-Path $VenvPy) {
        & $VenvPy -V *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Venv python is broken. Recreating..."
            & powershell -NoProfile -ExecutionPolicy Bypass -File $SetupScript
        }
    }

    if (-not (Test-Path $VenvPy)) {
        Write-Host "Venv python not found. Running setup..."
        if (-not (Test-Path $SetupScript)) {
            throw "setup_riskguard.ps1 not found. Aborting."
        }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $SetupScript
    }

    if (-not (Test-Path $VenvPy)) {
        throw "Venv python still not found. Aborting."
    }
}

Ensure-Venv

Push-Location $AppDir
& $VenvPy $UiScript @Args
$exitCode = $LASTEXITCODE
Pop-Location
exit $exitCode
