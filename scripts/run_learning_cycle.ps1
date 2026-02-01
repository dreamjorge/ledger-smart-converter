param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("hsbc", "santander")]
    $Bank
)

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$VenvPath = "$RepoRoot\.venv"
$SrcDir = "$RepoRoot\src"
$ConfigDir = "$RepoRoot\config"
$DataDir = "$RepoRoot\data\$Bank"

# Check directories
if (-not (Test-Path $DataDir)) {
    Write-Error "Data directory not found for bank: $Bank ($DataDir)"
    exit 1
}

$RulesBase = "$ConfigDir\rules.yml"
$RulesSuggestions = "$DataDir\rules_suggestions.yml"
$RulesMerged = "$DataDir\rules_merged.yml"

# Define bank-specific settings
if ($Bank -eq "hsbc") {
    $Script = "$SrcDir\import_hsbc_cfdi_firefly.py"
    $InputFile = "$DataDir\statements.xml"
    $InputArg = "--xml"
}
elseif ($Bank -eq "santander") {
    $Script = "$SrcDir\import_likeu_firefly.py"
    # Find first xlsx or specific one? Hardcoding for verified example.
    $InputFile = "$DataDir\3045-31_01_26.xlsx" 
    $InputArg = "--xlsx"
}

# 1. First Run (Generate Suggestions)
Write-Host "--- [1/3] Cycle 1: Generating Suggestions ---" -ForegroundColor Cyan
& "$VenvPath\Scripts\python" $Script `
    $InputArg "$InputFile" `
    --rules "$RulesBase" `
    --out "$DataDir\firefly_${Bank}_v1.csv" `
    --unknown-out "$DataDir\unknown_merchants_v1.csv" `
    --suggestions-out "$RulesSuggestions"

# 2. Merge
Write-Host "`n--- [2/3] Merging Rules ---" -ForegroundColor Cyan
if (-not (Test-Path $RulesSuggestions)) {
    Write-Warning "No rules suggestions generated. Skipping merge."
    exit
}

& "$VenvPath\Scripts\python" "$SrcDir\merge_suggestions.py" `
    --base "$RulesBase" `
    --suggestions "$RulesSuggestions" `
    --out "$RulesMerged"

# 3. Second Run (Verify with New Rules)
Write-Host "`n--- [3/3] Cycle 2: Verifying with Merged Rules ---" -ForegroundColor Cyan
& "$VenvPath\Scripts\python" $Script `
    $InputArg "$InputFile" `
    --rules "$RulesMerged" `
    --out "$DataDir\firefly_${Bank}_final.csv" `
    --unknown-out "$DataDir\unknown_merchants_final.csv" `
    --suggestions-out "$DataDir\rules_suggestions_final.yml"

Write-Host "`nDone." -ForegroundColor Green
Write-Host "Compare 'unknown_merchants_v1.csv' vs 'unknown_merchants_final.csv'."
Write-Host "If satisfied, replace '$RulesBase' with '$RulesMerged'."
