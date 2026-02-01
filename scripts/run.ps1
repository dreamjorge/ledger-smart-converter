param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $ScriptArgs
)

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$VenvPath = "$RepoRoot\.venv"
$SrcDir = "$RepoRoot\src"

# Check for venv
if (-not (Test-Path $VenvPath)) {
    Write-Error "Virtual environment not found at $VenvPath. Please run setup_env.ps1 first."
    exit 1
}

# Run script
Write-Host "Running import_likeu_firefly.py..."
& "$VenvPath\Scripts\python" "$SrcDir\import_likeu_firefly.py" @ScriptArgs
