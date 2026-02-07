# AI Agent Context - Ledger Smart Converter

## Quick Reference

**Project Type**: Financial data importer with ML categorization
**Language**: Python 3.8+
**Framework**: Streamlit (web UI)
**Primary Purpose**: Parse bank statements (PDF/XML/XLSX) → Firefly III CSV

## Critical Files

| File | Purpose |
|------|---------|
| `src/generic_importer.py` | CLI entry point, validation flags |
| `src/domain/transaction.py` | Canonical model |
| `src/services/import_service.py` | Import orchestration |
| `src/services/rule_service.py` | Safe rule staging/merge |
| `src/ml_categorizer.py` | sklearn category predictions |
| `src/pdf_utils.py` | PDF text + OCR extraction |
| `src/ui/pages/import_page.py` | Upload interface |
| `src/ui/pages/analytics_page.py` | Dashboard + rule correction |
| `config/rules.yml` | Account config + categorization rules |
| `tests/` | pytest suite (14 tests) |

## Architecture Pattern

**Layer Separation**:
- **Domain** (`src/domain/`): Validated canonical models
- **Services** (`src/services/`): Business logic (import, rules, analytics)
- **UI** (`src/ui/pages/`): Streamlit presentation layer
- **Utilities**: Validation, logging, settings, OCR

**Data Flow**: Input → Parse → Validate → Categorize (Rules + ML) → CSV → Firefly III

## Common Tasks

### Add New Bank Importer
1. Create `src/import_<bank>_firefly.py`
2. Implement parser returning `List[Transaction]`
3. Add bank config to `config/rules.yml`
4. Register in `src/generic_importer.py`
5. Add tests in `tests/test_<bank>.py`

### Modify Transaction Model
1. Edit `src/domain/transaction.py`
2. Update `src/validation.py` validators
3. Update importers to populate new fields
4. Run `pytest tests/test_validation.py`

### Add Categorization Rule
1. **Safe workflow**: Edit `config/rules.pending.yml` (not `rules.yml` directly)
2. Use UI "Apply Pending Rules" or `src/services/rule_service.py`
3. System creates backup in `config/backups/` before merge
4. ML retrains after merge

### Fix OCR Issues
1. Check `src/pdf_utils.py` regex patterns
2. Test with `src/pdf_feedback.py --pdf X.pdf --xml X.xml`
3. Review `data/<bank>/feedback/` outputs
4. Adjust preprocessing/date parsing logic

## Testing & CI

**Run Tests**: `python -m pytest -q`
**CI**: `.github/workflows/ci.yml` (compile + pytest on push/PR)
**Coverage**: Import services, validation, settings, healthcheck

## Code Style

- Type hints for service layer functions
- Docstrings for public functions
- Validation at domain boundary
- Structured logging (`logging_config.py`)
- Error types in `src/errors.py`

## Environment

**Config**: `.env` file (see `.env.example`)
**Key Settings**: OCR paths, data directories, test mode flag
**Healthcheck**: `python src/healthcheck.py` validates dependencies

## Deployment Modes

**CLI**: `python src/generic_importer.py --bank <name> --data <file> --out <csv>`
**Web**: `./scripts/run_web.sh` → `http://localhost:8501`
**Flags**: `--strict` (fail fast), `--dry-run` (no writes), `--log-json` (audit manifest)

## Known Patterns

- **Atomic writes**: Write to temp file, rename on success
- **Safe rules**: Stage in `.pending.yml`, detect conflicts, backup on merge
- **Fuzzy search**: Use `smart_matching.py` for merchant lookup
- **ML predictions**: sklearn model retrains on rule changes
- **Statement periods**: Auto-tag `period:YYYY-MM` based on `closing_day` config

## Anti-Patterns to Avoid

- Don't mutate `config/rules.yml` directly (use pending workflow)
- Don't skip validation layer (domain models enforce contracts)
- Don't use `cat`/`sed` for CSV writes (use atomic write utilities)
- Don't hardcode paths (use `settings.py` config)

## Future Direction (Roadmap)

**Next Phase**: SQLite persistence, account unification, hash-based deduplication
**See**: `docs/plan_mejoras.md` for detailed roadmap

## Quick Diagnostics

```bash
# Validate environment
python src/healthcheck.py

# Test imports work
python -m pytest tests/ -v

# Dry run import
python src/generic_importer.py --bank santander_likeu --data test.xlsx --dry-run

# Check rule conflicts
# (Use UI "Apply Pending Rules" button)
```

## Token-Saving Tips

- Read `docs/project-index.qmd` for comprehensive overview
- Check `src/domain/transaction.py` for data model
- Review `config/rules.yml` for configuration schema
- Use `src/services/` for business logic reference
- Consult `docs/plan_mejoras.md` for roadmap context
