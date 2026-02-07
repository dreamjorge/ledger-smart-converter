# AI Agent Context - Ledger Smart Converter

## Quick Reference

**Project Type**: Financial data importer with ML categorization
**Language**: Python 3.8+
**Framework**: Streamlit (web UI)
**Primary Purpose**: Parse bank statements (PDF/XML/XLSX) → Firefly III CSV

## 🎯 Quick Context Files (QMD)

**Use these for focused context on specific areas:**

| Area | QMD File | When to Use |
|------|----------|-------------|
| **Domain Models** | `docs/context/domain.qmd` | Working with transaction models, validation |
| **Services** | `docs/context/services.qmd` | Import workflow, rules, analytics, data access |
| **Importers** | `docs/context/importers.qmd` | Bank parsers, PDF extraction, adding new banks |
| **UI** | `docs/context/ui.qmd` | Streamlit pages, dashboard, rule correction UI |
| **ML & Categories** | `docs/context/ml-categorization.qmd` | ML predictions, fuzzy matching, categorization rules |
| **Testing** | `docs/context/testing.qmd` | pytest suite, writing tests, CI/CD |

**Render QMD to HTML for viewing**:
```bash
cd docs/context
quarto render <file>.qmd
```

## 📊 Full Project Overview

**Comprehensive Reference**: `docs/project-index.qmd` (or `.html` for rendered version)

## Critical Files by Task

### Working on Domain/Validation
- Read: `docs/context/domain.qmd`
- Files: `src/domain/transaction.py`, `src/validation.py`, `src/errors.py`

### Working on Import Logic
- Read: `docs/context/importers.qmd`, `docs/context/services.qmd`
- Files: `src/generic_importer.py`, `src/import_*_firefly.py`, `src/pdf_utils.py`, `src/services/import_service.py`

### Working on Analytics Dashboard
- Read: `docs/context/ui.qmd`, `docs/context/services.qmd`
- Files: `src/ui/pages/analytics_page.py`, `src/services/analytics_service.py`, `src/services/data_service.py`

### Working on Categorization
- Read: `docs/context/ml-categorization.qmd`, `docs/context/services.qmd`
- Files: `src/ml_categorizer.py`, `src/smart_matching.py`, `src/services/rule_service.py`, `config/rules.yml`

### Writing Tests
- Read: `docs/context/testing.qmd`
- Files: `tests/test_*.py`, `.github/workflows/ci.yml`

### Working on PDF Extraction
- Read: `docs/context/importers.qmd` (PDF utilities section)
- Files: `src/pdf_utils.py`, `src/pdf_feedback.py`

## Architecture Pattern

**Layer Separation**:
- **Domain** (`src/domain/`) - Validated canonical models
- **Services** (`src/services/`) - Business logic (import, rules, analytics, data)
- **UI** (`src/ui/pages/`) - Streamlit presentation layer
- **Utilities** - Validation, logging, settings, OCR, translations

**Data Flow**: Input → Parse → Validate → Categorize (Rules + ML) → CSV → Firefly III

## Common Tasks Quick Reference

### Add New Bank Importer
1. Create `src/import_<bank>_firefly.py` (see `docs/context/importers.qmd`)
2. Add bank config to `config/rules.yml`
3. Register in `src/generic_importer.py`
4. Add tests in `tests/test_<bank>.py`
5. Document in importers QMD

### Modify Transaction Model
1. Edit `src/domain/transaction.py`
2. Update `src/validation.py` validators
3. Update importers to populate new fields
4. Update analytics if needed (see `docs/context/services.qmd`)
5. Run `pytest tests/test_validation.py`

### Add Categorization Rule
1. **Safe workflow**: Edit `config/rules.pending.yml` (NOT `rules.yml` directly)
2. Use UI "Apply Pending Rules" or `src/services/rule_service.py`
3. System creates backup in `config/backups/`
4. ML retrains automatically after merge

### Fix OCR/PDF Issues
1. Check `src/pdf_utils.py` regex patterns (see `docs/context/importers.qmd`)
2. Test with `src/pdf_feedback.py --pdf X.pdf --xml X.xml`
3. Review `data/<bank>/feedback/` outputs
4. Adjust preprocessing/date parsing logic

### Add UI Feature
1. Edit `src/ui/pages/*.py` (see `docs/context/ui.qmd`)
2. Use `t()` for translations (`src/translations.py`)
3. Call services from `src/services/` for business logic
4. Test in browser: `streamlit run src/web_app.py`

### Improve ML Predictions
1. Review categorization rules quality (see `docs/context/ml-categorization.qmd`)
2. Add more rules to `config/rules.yml`
3. Retrain model: `ml.train_global_model()`
4. Test predictions in UI Rule Hub

## Testing & CI

**Run Tests**: `python -m pytest tests/ -v` (see `docs/context/testing.qmd`)
**Quick Run**: `python -m pytest tests/ -q`
**CI**: `.github/workflows/ci.yml` runs on push/PR
**Current**: 55 tests passing ✅

## Code Style

- Type hints for service layer functions
- Docstrings for public functions (see QMD examples)
- Validation at domain boundary
- Structured logging (`from logging_config import get_logger`)
- Error types in `src/errors.py`

## Environment

**Config**: `.env` file (see `.env.example`)
**Key Settings**: OCR paths, data directories, test mode flag
**Healthcheck**: `python src/healthcheck.py` validates dependencies

## Deployment Modes

**CLI**:
```bash
python src/generic_importer.py --bank <name> --data <file> --out <csv>
```

**Web**:
```bash
./scripts/run_web.sh  # → http://localhost:8501
```

**Flags**: `--strict` (fail fast), `--dry-run` (no writes), `--log-json` (audit manifest)

## Known Patterns (See QMD Files for Details)

- **Atomic writes**: Write to temp file, rename on success
- **Safe rules**: Stage in `.pending.yml`, detect conflicts, backup on merge
- **Fuzzy search**: `smart_matching.py` for merchant lookup (see ML context QMD)
- **ML predictions**: sklearn model retrains on rule changes (see ML context QMD)
- **Statement periods**: Auto-tag `period:YYYY-MM` based on `closing_day` config
- **Date parsing**: Enhanced support for multiple formats (see importers QMD)
- **Error handling**: Structured logging, typed errors, graceful degradation

## Anti-Patterns to Avoid

- ❌ Don't mutate `config/rules.yml` directly → use pending workflow
- ❌ Don't skip validation layer → domain models enforce contracts
- ❌ Don't use `cat`/`sed` for CSV writes → use atomic write utilities
- ❌ Don't hardcode paths → use `settings.py` config
- ❌ Don't use `print()` → use structured logging
- ❌ Don't mutate dataframes in place → create filtered copies

## Recent Enhancements (2026-02-06)

**PDF Utils** (see `docs/context/importers.qmd`):
- Structured logging (replaced print statements)
- Enhanced date parsing (more formats supported)
- Robust amount parsing (returns None vs crashing)
- Better OCR configuration and fallback
- Comprehensive docstrings

**Testing Infrastructure** (see `docs/context/testing.qmd`):
- Dummy data generator: `scripts/generate_dummy_data.py`
- 690 realistic test transactions
- 70+ Mexican merchants across 9 categories
- Run: `python scripts/generate_dummy_data.py`

**Documentation**:
- QMD context files for token-efficient agent context
- Rendered HTML documentation with Quarto
- Module-specific reference files

## Quick Diagnostics

```bash
# Validate environment
python src/healthcheck.py

# Run all tests
python -m pytest tests/ -v

# Dry run import
python src/generic_importer.py --bank santander_likeu --data test.xlsx --dry-run

# Generate test data for dashboard
python scripts/generate_dummy_data.py

# Start web UI
streamlit run src/web_app.py
```

## Token-Saving Workflow for Agents

**Step 1**: Identify your task area (domain, services, importers, UI, ML, testing)

**Step 2**: Read the relevant QMD file:
```bash
# For Python agents
from pathlib import Path
context = Path("docs/context/<area>.qmd").read_text()

# For CLI
cat docs/context/<area>.qmd
```

**Step 3**: Reference specific sections as needed (QMD files are organized with clear headers)

**Step 4**: For full context, read `docs/project-index.qmd`

**Benefits**:
- 📉 Reduced token usage (read only relevant context)
- 🎯 Focused context (no irrelevant information)
- 📚 Comprehensive examples (code patterns and best practices)
- 🔄 Always up-to-date (maintained alongside code)

## Future Direction (Roadmap)

**Next Phase**: SQLite persistence, account unification, hash-based deduplication
**See**: `docs/plan_mejoras.md` for detailed roadmap

## Getting Help

- **Architecture questions**: Read `docs/project-index.qmd`
- **Module-specific questions**: Read relevant `docs/context/*.qmd`
- **Code examples**: Search QMD files for usage patterns
- **Testing**: Refer to `docs/context/testing.qmd`
- **API reference**: Check docstrings in source files
