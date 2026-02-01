$RepoRoot = Resolve-Path "$PSScriptRoot\.."

# Check for python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# Create venv if not exists
$VenvPath = "$RepoRoot\.venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment at $VenvPath..."
    python -m venv $VenvPath
}
else {
    Write-Host "Virtual environment already exists."
}

# Activate and install requirements
Write-Host "Installing/Upgrading requirements..."
& "$VenvPath\Scripts\python" -m pip install --upgrade pip
& "$VenvPath\Scripts\pip" install -r "$RepoRoot\requirements.txt"

Write-Host "Setup complete."
