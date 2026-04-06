# Claude Code Context

## 🎯 Quick Context Files (NEW!)

**For token efficiency, use modular QMD context files:**

| Working On | Read This | Files |
|-----------|-----------|-------|
| Domain/Validation | `docs/context/domain.qmd` | `src/domain/`, `src/validation.py` |
| Services Layer | `docs/context/services.qmd` | `src/services/` |
| Database/Persistence | `docs/context/db.qmd` | `src/services/db_service.py`, `src/database/schema.sql` |
| Bank Importers | `docs/context/importers.qmd` | `src/import_*.py`, `src/pdf_utils.py` |
| UI/Dashboard | `docs/context/ui.qmd` | `src/ui/pages/` |
| ML/Categories | `docs/context/ml-categorization.qmd` | `src/ml_categorizer.py`, `config/rules.yml` |
| Testing | `docs/context/testing.qmd` | `tests/` |

**See also:** `AGENTS.md` for complete agent guide, `docs/context/README.md` for QMD usage guide, and the `skills/` directory for specialized assistant workflows.

---

## Project Identity

**Name**: Ledger Smart Converter
**Type**: Bank statement importer with ML categorization
**Stack**: Python 3.8+, Streamlit, sklearn, pytest, SQLite
**Domain**: Financial data ETL (PDF/XML/XLSX → Firefly III CSV)

## When Working Here

### Architecture is Layered
- **Domain** models enforce validation (`src/domain/`)
- **Services** contain business logic (`src/services/`)
- **Database** persistence layer — SQLite via `DatabaseService` (`src/services/db_service.py`)
- **UI** is presentation only (`src/ui/pages/`)
- **Importers** are bank-specific parsers (`src/import_*.py`)

### Critical Workflows
1. **Imports**: Input → Parse → Validate → Categorize → Atomic CSV write
2. **Rules**: Stage in `rules.pending.yml` → Conflict check → Backup → Merge → Retrain ML
3. **Analytics**: Load CSVs → Aggregate → Display metrics + drill-down

### Safety First
- **Never** edit `config/rules.yml` directly (use pending workflow)
- **Always** validate domain models (Transaction class)
- **Always** use atomic writes for CSV outputs
- **Check** tests pass before structural changes: `pytest tests/`
- **Before creating a PR to `main`**: confirm tests pass against `main`'s codebase — if a test depends on code from another unmerged branch, mark it `@pytest.mark.skip(reason="depends on feat/X")` to keep CI green

### Files I'll Need Most

**To understand data model**: `src/domain/transaction.py`
**To modify import logic**: `src/services/import_service.py`
**To fix categorization**: `src/ml_categorizer.py`, `config/rules.yml`
**To update UI**: `src/ui/pages/*.py`
**To debug OCR**: `src/pdf_utils.py`
**To add tests**: `tests/`
**To work with DB**: `src/services/db_service.py`, `src/database/schema.sql`
**To run DB pipeline**: `scripts/run_db_pipeline.py`, `src/db_pipeline.py`, `src/csv_to_db_migrator.py`
**To configure accounts**: `config/accounts.yml`, `src/account_mapping.py`
**To debug normalization**: `src/description_normalizer.py`

## Common Request Patterns

### "Add support for X bank"
1. Create `src/import_<bank>_firefly.py` parser
2. Add config section in `config/rules.yml`
3. Register in `src/generic_importer.py`
4. Write tests in `tests/test_<bank>.py`

### "Fix OCR parsing"
1. Check `src/pdf_utils.py` regex patterns
2. Run `src/pdf_feedback.py` to compare OCR vs reference data
3. Review feedback files in `data/<bank>/feedback/`
4. Adjust date parsing or preprocessing

### "Modify transaction fields"
1. Update `src/domain/transaction.py` model
2. Update validators in `src/validation.py`
3. Update importers to populate new fields
4. Update analytics queries in `src/services/analytics_service.py`
5. Run `pytest tests/test_validation.py`

### "Add new categorization rule"
- **User-facing**: They use UI rule correction feature
- **Code-level**: Edit `config/rules.pending.yml`, then use rule service to merge

### "Run DB Pipeline"
1. Run: `python scripts/run_db_pipeline.py --db data/ledger.db --data-dir data --accounts config/accounts.yml`
2. Verify: `sqlite3 data/ledger.db "SELECT bank_id, count(*) FROM transactions GROUP BY bank_id"`
3. Debug: check `imports` table for status/errors
4. Re-run safely — idempotent via `source_hash` deduplication

### "Improve ML predictions"
1. Review `src/ml_categorizer.py` model
2. Check training data quality (requires existing categorized transactions)
3. Consider feature engineering (merchant name cleaning, amount ranges)
4. Model retrains automatically when rules are updated

## Code Conventions

- **Type hints**: Use for service layer functions
- **Validation**: At domain boundary (Transaction creation)
- **Errors**: Use typed errors from `src/errors.py`
- **Logging**: Use `logging_config.py` structured logger
- **Atomicity**: Write temp file → rename (see utilities)

## Testing Strategy

**Unit tests**: Domain models, validation logic
**Integration tests**: Import service workflows
**Coverage areas**: Import services, validation, settings, healthcheck
**Fast run**: `python -m pytest -m "not slow" -q` (~34s, 546 tests — default for CI)
**Full suite**: `python -m pytest -q` (~55+ min, includes 8 slow ML/OCR tests)
**Slow tests**: Tagged `@pytest.mark.slow` — ML training, large PDFs, real datasets
**CI**: GitHub Actions on push/PR (`.github/workflows/ci.yml`) — fast suite + separate slow step

## Configuration Files

**`config/rules.yml`**: Account definitions, closing days, categorization rules
**`config/rules.pending.yml`**: Staged rule changes (safe workflow)
**`.env`**: Environment settings (see `.env.example`)
**`requirements.txt`**: Python dependencies

## Known Gotchas

- **OCR dependency**: Tesseract required for scanned PDFs (optional otherwise)
- **Rule conflicts**: System detects before merge and prompts resolution
- **CSV encoding**: Handle UTF-8 with BOM for Excel compatibility
- **Date parsing**: Different banks use different formats, check `pdf_utils.py`
- **Statement periods**: Calculated from `closing_day` config, tagged as `period:YYYY-MM`

## Roadmap Context

**Recently completed**: Validation layer, service architecture, safe rules workflow, CI, SQLite persistence, description normalization, account mapping, Flet UI prototype
**Next up**: Firefly API sync, automated monthly reports, Flet UI migration
**Future**: Automated monthly reports, mobile-friendly UI
**See**: `docs/plan_mejoras.md` for details

## When You're Stuck

1. **Run healthcheck**: `python src/healthcheck.py`
2. **Check logs**: Import service creates structured logs
3. **Dry run**: Use `--dry-run` flag to test without writing
4. **Feedback tool**: Use `src/pdf_feedback.py` for OCR debugging
5. **Ask about**: Architecture decisions (check service layer), roadmap priorities (check plan_mejoras.md)

## Token-Efficient References

- **Full overview**: `docs/project-index.qmd`
- **Agent quick ref**: `AGENTS.md`
- **Data model**: `src/domain/transaction.py` (single source of truth)
- **Config schema**: `config/rules.yml` (commented with examples)
- **Roadmap**: `docs/plan_mejoras.md`

## What Users Care About

1. **Accuracy**: Correct categorization (Rules + ML working together)
2. **Safety**: No duplicate imports, no data loss (validation + atomic writes)
3. **Ease**: Simple UI for upload and rule correction
4. **Privacy**: 100% local processing (no cloud calls)
5. **Reliability**: Consistent results, good error messages

## My Goal When Helping

- **Preserve safety**: Don't bypass validation or atomic writes
- **Maintain architecture**: Keep layers separate (domain/service/UI)
- **Test changes**: Run pytest before declaring done
- **Document decisions**: Update comments/docstrings for non-obvious logic
- **Stay focused**: Don't over-engineer, solve the specific problem
