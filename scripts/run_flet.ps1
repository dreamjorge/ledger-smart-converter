# PowerShell script to run the Flet Prototype

$VENV_PATH = ".\.venv"
$PYTHON_EXE = "$VENV_PATH\Scripts\python.exe"

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "uv-managed virtual environment not found at $VENV_PATH. Please run setup_env.ps1 first." -ForegroundColor Red
    exit
}

$env:PYTHONPATH = "src"
Write-Host "Starting Flet Desktop App..." -ForegroundColor Green
& $PYTHON_EXE src\flet_app.py
