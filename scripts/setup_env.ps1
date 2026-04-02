$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$VenvPath = "$RepoRoot\.venv"
$VenvPython = "$VenvPath\Scripts\python.exe"

# Check for uv
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not installed or not in PATH."
    exit 1
}

# Create uv-managed venv if not exists
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating uv-managed virtual environment at $VenvPath..."
    & uv venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
else {
    Write-Host "uv-managed virtual environment already exists."
}

# Install requirements via uv
Write-Host "Installing requirements with uv..."
& uv pip install --python $VenvPython -r "$RepoRoot\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Setup complete. Use the uv-managed environment at $VenvPath."
