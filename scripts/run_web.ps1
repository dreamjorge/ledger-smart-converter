$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$VenvPath = "$RepoRoot\.venv"
$SrcDir = "$RepoRoot\src"

# Check for venv
if (-not (Test-Path $VenvPath)) {
    Write-Error "Virtual environment not found. Please run setup_env.ps1 first."
    exit 1
}

# Install streamlit if not present (simple check)
# Actually setup_env should have done it if requirements.txt was updated. 
# But let's assume dependencies are there.

Write-Host "Starting Web Interface..."
& "$VenvPath\Scripts\streamlit" run "$SrcDir\web_app.py"
