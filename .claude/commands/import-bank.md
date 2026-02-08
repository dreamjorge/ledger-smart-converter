# Bank Import

Run a bank statement import. $ARGUMENTS

## CLI Usage

```bash
python src/generic_importer.py \
    --bank <bank_id> \
    --data <input_file> \
    --out <output.csv> \
    [--strict] \
    [--dry-run] \
    [--log-json]
```

**Supported banks**: `santander_likeu`, `hsbc`

**Flags**:
- `--strict` — Fail fast on validation errors
- `--dry-run` — Parse and validate but don't write CSV
- `--log-json` — Output run manifest as JSON for auditing

## Examples

```bash
# Dry run first (always recommended)
python src/generic_importer.py --bank santander_likeu --data statement.xlsx --dry-run

# Full import
python src/generic_importer.py --bank santander_likeu --data statement.xlsx --out data/santander/firefly_likeu.csv

# Strict mode (fail on first error)
python src/generic_importer.py --bank hsbc --data invoice.xml --strict
```

## Pipeline Steps

1. Load bank config from `config/rules.yml`
2. Call bank-specific parser (`src/import_<bank>_firefly.py`)
3. Validate transactions (domain model)
4. Apply rules + ML categorization
5. Write CSV atomically (temp file → rename)
6. Log run manifest

Read `docs/context/importers.qmd` for parser details and troubleshooting.
