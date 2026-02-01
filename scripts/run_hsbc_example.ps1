# Example script to run HSBC import with specific arguments
$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$DataDir = "$RepoRoot\data\hsbc"
$ConfigDir = "$RepoRoot\config"
$VenvPath = "$RepoRoot\.venv"
$SrcDir = "$RepoRoot\src"

# Ensure directories exist
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }

$Xml = "$DataDir\statements.xml"
# Using global rules.yml, or could use specific one if it existed
$Rules = "$ConfigDir\rules.yml" 
$OutCsv = "$DataDir\firefly_hsbc.csv"
$UnknownOut = "$DataDir\unknown_merchants.csv"
$SuggestionsOut = "$DataDir\rules_suggestions.yml"

Write-Host "Running HSBC import with:"
Write-Host "  XML: $Xml"
Write-Host "  Rules: $Rules"

# Check for venv
if (-not (Test-Path $VenvPath)) {
    Write-Error "Virtual environment not found. Please run setup_env.ps1 first."
    exit 1
}

# Run script
Write-Host "Running import_hsbc_cfdi_firefly.py..."
& "$VenvPath\Scripts\python" "$SrcDir\import_hsbc_cfdi_firefly.py" `
    --xml "$Xml" `
    --rules "$Rules" `
    --out "$OutCsv" `
    --unknown-out "$UnknownOut" `
    --suggestions-out "$SuggestionsOut"
