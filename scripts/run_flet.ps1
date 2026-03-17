# PowerShell script to run the Flet Prototype

$VENV_PATH = ".\.venv"
$PYTHON_EXE = "$VENV_PATH\Scripts\python.exe"

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "Virtual environment not found at $VENV_PATH. Please run setup_env.ps1 first." -ForegroundColor Red
    exit
}

Write-Host "Checking for Flet dependency..." -ForegroundColor Cyan
& $PYTHON_EXE -m pip install flet

Write-Host "Starting Flet Prototype..." -ForegroundColor Green
& $PYTHON_EXE src\flet_prototype.py
