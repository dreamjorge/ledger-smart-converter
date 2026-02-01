# Example script to run with specific arguments
$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$DataDir = "$RepoRoot\data\santander"
$ConfigDir = "$RepoRoot\config"

if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }

$Xlsx = "$DataDir\3045-31_01_26.xlsx"
$Rules = "$ConfigDir\rules.yml"
$Pdf = "$DataDir\ESTADO DE CUENTA-SANTANDER LIKEU-ENERO2026-310126.pdf"
$OutCsv = "$DataDir\firefly_likeu.csv"
$UnknownOut = "$DataDir\unknown_merchants.csv"
$SuggestionsOut = "$DataDir\rules_suggestions.yml"

Write-Host "Running import with:"
Write-Host "  XLSX: $Xlsx"
Write-Host "  Rules: $Rules"
Write-Host "  PDF: $Pdf"

# Call the helper run script (located in same dir)
& "$PSScriptRoot\run.ps1" `
    --xlsx "$Xlsx" `
    --rules "$Rules" `
    --pdf "$Pdf" `
    --out "$OutCsv" `
    --unknown-out "$UnknownOut" `
    --suggestions-out "$SuggestionsOut"
