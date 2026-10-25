$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) {
    $PythonArgs = @("-3")
} else {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Python) {
        throw "Python 3.10 or newer was not found."
    }
    $PythonArgs = @()
}

$VersionOk = & $Python.Source @PythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 or newer is required."
}

Write-Host "Creating virtual environment in $RootDir\.venv"
& $Python.Source @PythonArgs -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
Write-Host "Installing the three projects and their dependencies..."
& .\.venv\Scripts\python.exe -m pip install ".[all]"

Write-Host ""
Write-Host "Installation complete."
Write-Host ""
Write-Host "Activate the environment:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Try the projects:"
Write-Host "  three-ai --help"
Write-Host "  three-ai researcher topics"
Write-Host "  three-ai scientist domains"
Write-Host "  three-ai game export --seed 42 --theme dungeon --output dungeon.html"
Write-Host "  three-ai game serve"
