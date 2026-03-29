# PowerShell script to run the Flet Prototype

$VENV_PATH = ".\.venv"
if (Test-Path ".\.venv_uv") {
    $VENV_PATH = ".\.venv_uv"
}
$PYTHON_EXE = "$VENV_PATH\Scripts\python.exe"

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "Virtual environment not found at $VENV_PATH. Please run setup_env.ps1 first." -ForegroundColor Red
    exit
}

$env:PYTHONPATH = "src"

# Clear stale Flet desktop client caches before startup. Failed first-run
# extraction on Windows can leave behind versioned directories that cause
# flet_desktop's atomic rename step to fail on the next launch.
$FLET_CLIENT_ROOT = Join-Path $HOME ".flet\client"
if (Test-Path $FLET_CLIENT_ROOT) {
    Get-ChildItem $FLET_CLIENT_ROOT -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "flet-desktop-*" } |
        ForEach-Object {
            try {
                Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
            }
            catch {
                Write-Host "Could not clear stale Flet cache: $($_.FullName)" -ForegroundColor Yellow
            }
        }
}

Write-Host "Starting Flet Desktop App..." -ForegroundColor Green
& $PYTHON_EXE src\flet_app.py
