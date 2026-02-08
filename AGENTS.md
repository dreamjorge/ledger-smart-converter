# AI Agent Context - Ledger Smart Converter

## Quick Reference

**Project Type**: Financial data importer with ML categorization
**Language**: Python 3.8+
**Framework**: Streamlit (web UI)
**Primary Purpose**: Parse bank statements (PDF/XML/XLSX) → Firefly III CSV

## ⚡ Claude Code Slash Commands

Project-specific commands available in `.claude/commands/`:

| Command | Description |
|---|---|
| `/add-bank [name]` | Step-by-step guide to add a new bank importer |
| `/run-tests` | Run the pytest suite with test file references |
| `/add-rule [merchant]` | Safe categorization rule staging workflow |
| `/health` | System health check and diagnostics |
| `/import-bank [bank] [file]` | Run a bank statement import |
| `/fix-ocr [file]` | Debug PDF/OCR parsing issues |
| `/new-test [module]` | TDD workflow for creating new test files |

---

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

## 🔍 CodeGraph (Semantic Code Navigation)

**`.codegraph/` exists** — use these tools instead of grep/glob for symbol lookups:

| Tool | Use For |
|------|---------|
| `codegraph_search` | Find symbols by name (functions, classes, types) |
| `codegraph_context` | Get relevant code context for a task |
| `codegraph_callers` | Find what calls a function |
| `codegraph_callees` | Find what a function calls |
| `codegraph_impact` | See what's affected before changing a symbol |
| `codegraph_node` | Get details + source code for a symbol |

**Reinitialize if stale** (after large refactors):
```bash
codegraph init -i
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
**Current**: 227 tests passing ✅

### ⚠️ CRITICAL: Test-Driven Development Policy

**FOR EVERY NEW FEATURE OR BUG FIX, CREATE UNIT TESTS FIRST**

This is **MANDATORY** to maintain project sanity and prevent regressions:

1. **Before writing feature code**:
   - Create test file: `tests/test_<module>.py`
   - Write tests for expected behavior (TDD approach)
   - Tests should fail initially (red phase)

2. **While implementing**:
   - Write minimal code to make tests pass (green phase)
   - Refactor while keeping tests green

3. **Coverage requirements**:
   - **New modules**: Aim for 80%+ coverage
   - **Critical paths** (imports, validation, classification): 90%+ coverage
   - **Utilities**: 100% coverage (they're small and reusable)

4. **Test types required**:
   - **Unit tests**: Test functions/methods in isolation
   - **Edge cases**: None, empty, invalid inputs
   - **Integration tests**: Test workflows end-to-end
   - **Error handling**: Test that errors are raised correctly

5. **When NOT to test**:
   - UI rendering code (Streamlit pages) - smoke tests only
   - CLI entry points (`if __name__ == "__main__"`) - covered by integration
   - Translation dictionaries - static data

**Example workflow**:
```bash
# 1. Create test file first
touch tests/test_my_feature.py

# 2. Write failing tests
pytest tests/test_my_feature.py  # Should fail

# 3. Implement feature
vim src/my_feature.py

# 4. Run tests until green
pytest tests/test_my_feature.py -v

# 5. Commit together
git add tests/test_my_feature.py src/my_feature.py
git commit -m "feat: add my_feature with 15 tests"
```

**Benefits**:
- ✅ Prevents regressions when refactoring
- ✅ Documents expected behavior
- ✅ Enables confident code changes
- ✅ Catches bugs before production
- ✅ Makes code review easier
- ✅ CI validates every commit

**Current test coverage** (as of 2026-02-07):
- Core utilities: ~90% ✅
- Services layer: ~75% ✅
- Import pipeline: ~70% ✅
- Domain models: 100% ✅

**See `docs/context/testing.qmd` for**:
- Writing effective tests
- Mocking strategies
- Fixture patterns
- pytest best practices

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
