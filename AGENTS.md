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
| `/retrain` | Retrain ML categorization model with current rules |
| `/coverage` | Run tests with 85% minimum coverage enforcement |
| `/validate-config` | Validate config/rules.yml syntax and structure |
| `/add-field [field]` | Guide to add a new Transaction model field |
| `/generate-data` | Generate dummy test data for the dashboard |
| `/run-db-pipeline` | Migrate CSVs to SQLite DB and export Firefly CSVs |

---

## 🎯 QMD Context Configuration (Authoritative)

Use QMD files as the primary context source before reading broad code areas.

| Area | Canonical QMD Path | Use For |
|------|---------------------|---------|
| **Domain Models** | `docs/context/domain.qmd` | Transaction model contracts, validation boundaries |
| **Services** | `docs/context/services.qmd` | Import orchestration, rule service, analytics/data services |
| **Importers** | `docs/context/importers.qmd` | Bank parsers, OCR/PDF extraction, ingestion flows |
| **UI** | `docs/context/ui.qmd` | Streamlit pages, analytics dashboard, correction hub |
| **ML & Categories** | `docs/context/ml-categorization.qmd` | Rule-based + ML categorization pipeline |
| **Testing** | `docs/context/testing.qmd` | Pytest patterns, fixtures, mocking, coverage workflow |
| **Database** | `docs/context/db.qmd` | SQLite schema, DatabaseService API, deduplication, pipeline |
| **Project Overview** | `docs/project-index.qmd` | Architecture-wide orientation and cross-module navigation |

### QMD Usage Rules for Agents

1. Identify task area first, then load only matching QMD file(s).
2. Prefer QMD + CodeGraph before full-source scanning.
3. If task spans layers, load only the minimal set (for example: `importers.qmd` + `services.qmd`).
4. Treat QMD paths above as canonical; do not invent alternative locations.
5. **MANDATORY: After completing any code change, update the relevant QMD file(s) to reflect the new state.** If you added a function, changed a signature, introduced a pattern, or refactored a module — the matching QMD must be updated in the same commit. Stale context is worse than no context.

#### What "keeping context updated" means in practice

| Change Made | QMD to Update |
|-------------|---------------|
| New/renamed/removed function in `src/ui/` | `ui.qmd` |
| New service method or changed signature | `services.qmd` |
| New bank importer or PDF parsing change | `importers.qmd` |
| Domain model field added/removed | `domain.qmd` |
| ML pipeline change, new category, rule schema | `ml-categorization.qmd` |
| New test pattern, fixture, or coverage change | `testing.qmd` |
| Cross-cutting refactor (multiple layers) | All affected QMDs |

**Minimum update per change**: function name, signature, and a one-line description of the change. For larger changes, update the relevant section fully.

**Render QMD to HTML (optional):**
```bash
quarto render docs/context/<file>.qmd
quarto render docs/project-index.qmd
```

## 🔍 CodeGraph Context Configuration (Authoritative)

CodeGraph is the canonical symbol/dependency navigator for this repo. Use it before broad grep/glob scans.

### CodeGraph Availability + Index Health

```bash
# Verify index directory exists
ls -la .codegraph

# Rebuild index after large refactors or stale results
codegraph init -i
```

### Canonical CodeGraph Commands

| Command | Use For | Example |
|---------|---------|---------|
| `codegraph_search` | Find symbols by name (functions, classes, classes/types) | `codegraph_search "parse_date"` |
| `codegraph_context` | Retrieve focused context for a task | `codegraph_context "Add PDF parsing"` |
| `codegraph_callers` | Find callers of a symbol | `codegraph_callers "extract_transactions_from_pdf"` |
| `codegraph_callees` | Find dependencies called by a symbol | `codegraph_callees "process_hsbc_cfdi"` |
| `codegraph_impact` | Estimate blast radius before refactors | `codegraph_impact "parse_es_date"` |
| `codegraph_node` | Get symbol details + source snippet | `codegraph_node "TransactionCategorizer"` |

### Required Usage Order for Analysis Tasks

1. `codegraph_search` to discover target symbols.
2. `codegraph_callers` to understand entry points and dependency direction.
3. `codegraph_callees` to identify collaborators/mock boundaries.
4. `codegraph_impact` before signature or behavior changes.
5. `codegraph_node` for precise implementation details.

**Example (test planning):**
```bash
codegraph_search "pdf_utils"
codegraph_callers "extract_transactions_from_pdf"
codegraph_callees "ocr_image"
codegraph_impact "parse_mx_date"
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

### Working on Database / Persistence
- Read: `docs/context/db.qmd`
- Files: `src/services/db_service.py`, `src/database/schema.sql`, `src/csv_to_db_migrator.py`, `src/db_pipeline.py`, `scripts/run_db_pipeline.py`, `config/accounts.yml`

## Architecture Pattern

**Layer Separation**:
- **Domain** (`src/domain/`) - Validated canonical models
- **Services** (`src/services/`) - Business logic (import, rules, analytics, data)
- **UI** (`src/ui/pages/`) - Streamlit presentation layer
- **Utilities** - Validation, logging, settings, OCR, translations

**Data Flow**: Input → Parse → Validate → Categorize (Rules + ML) → CSV → Firefly III

## 🤖 Subagent Role Assignments

For complex tasks, delegate to specialized subagents in parallel:

| Subagent | Assigned Tasks | Key Files | QMD Context | Skill Reference |
|---|---|---|---|---|
| **Import Agent** | New bank parsers, file ingestion debug | `src/import_*.py`, `src/generic_importer.py` | `importers.qmd` | [Bank Importer](file:///d:/Repositories/credit_cards/skills/bank-importer/SKILL.md) |
| **Validation Agent** | Domain model changes, contract validation | `src/domain/transaction.py`, `src/validation.py`, `src/errors.py` | `domain.qmd` | [Domain Model](file:///d:/Repositories/credit_cards/skills/domain-model/SKILL.md) |
| **ML/Rules Agent** | Categorization rules, model retraining | `src/ml_categorizer.py`, `src/smart_matching.py`, `config/rules.yml` | `ml-categorization.qmd` | [Categorization](file:///d:/Repositories/credit_cards/skills/categorization/SKILL.md) |
| **OCR Agent** | PDF extraction, Tesseract debugging | `src/pdf_utils.py`, `src/pdf_feedback.py` | `importers.qmd` | [OCR Debug](file:///d:/Repositories/credit_cards/skills/ocr-debug/SKILL.md) |
| **Analytics Agent** | Dashboard metrics, data queries | `src/services/analytics_service.py`, `src/ui/pages/analytics_page.py` | `ui.qmd`, `services.qmd` | [Analytics](file:///d:/Repositories/credit_cards/skills/analytics/SKILL.md) |
| **Testing Agent** | TDD workflow, coverage enforcement | `tests/`, `.github/workflows/ci.yml` | `testing.qmd` | [Testing](file:///d:/Repositories/credit_cards/skills/testing/SKILL.md) |
| **Database Agent** | DB pipeline runs, schema migrations, deduplication debugging | `src/services/db_service.py`, `src/csv_to_db_migrator.py`, `src/database/schema.sql` | `db.qmd` | [DB Operations](file:///root/ledger-smart-converter/skills/db-operations/SKILL.md) |
| **Architecture Agent** | Codebase analysis, refactoring, improvement planning | All modules | All QMDs | [Main Skill](file:///d:/Repositories/credit_cards/SKILL.md) |

### Parallel Delegation Pattern

When a task spans multiple layers, assign each layer to a separate agent:

```
Example: "Add new bank with ML rules"
  → Import Agent: create src/import_<bank>_firefly.py
  → ML/Rules Agent: add categorization rules to config/rules.yml
  → Testing Agent: write tests/test_<bank>.py (TDD first)

Example: "Run DB migration and verify"
  → Database Agent: run db pipeline, verify import counts
  → Testing Agent: run test_csv_to_db_migrator.py, test_db_service.py
```

### Architecture Analysis Pattern

When conducting codebase analysis or creating improvement plans:

```
Example: "Analyze project status and create improvement plan"
  → Architecture Agent workflow:
     1. Read docs/plan_mejoras.md for roadmap context
     2. Use codegraph_search to find untested modules
     3. Use codegraph_impact to identify critical paths
     4. Read relevant docs/context/*.qmd files for domain knowledge
     5. Use codegraph_callers/callees to map dependencies
     6. Create prioritized improvement plan with CodeGraph references
```

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

### Run or Debug DB Pipeline
1. Run: `python scripts/run_db_pipeline.py --db data/ledger.db --data-dir data --accounts config/accounts.yml`
2. Check import log: `sqlite3 data/ledger.db "SELECT * FROM imports ORDER BY processed_at DESC LIMIT 10"`
3. Verify transaction count: `sqlite3 data/ledger.db "SELECT bank_id, count(*) FROM transactions GROUP BY bank_id"`
4. Rerun safely (idempotent): duplicates are skipped via source_hash

## Testing & CI

**Run Tests**: `python -m pytest tests/ -v` (see `docs/context/testing.qmd`)
**Fast Run (default)**: `python -m pytest -m "not slow" -q` — excludes slow ML/OCR tests (~34s)
**Full Suite**: `python -m pytest -q` — includes all tests (~55+ min)
**Slow Only**: `python -m pytest -m "slow" -q --tb=short`
**CI**: `.github/workflows/ci.yml` runs on push/PR (fast tests with 80% coverage + separate slow step)
 **Current**: 566 tests total (558 fast + 8 slow `@pytest.mark.slow`)

### ⚠️ CRITICAL: Test-Driven Development Policy

**FOR EVERY NEW FEATURE OR BUG FIX, CREATE UNIT TESTS FIRST**

This is **MANDATORY** to maintain project sanity and prevent regressions:

#### Branch/CI Compatibility Rule (prevents CI failures)

Before committing tests to a PR targeting `main`, verify the tests pass **against main's codebase**, not just the current branch:

```bash
# Check that no test depends on code not yet in main
git stash          # temporarily remove feature code
pytest tests/      # should pass or only fail for your new tests
git stash pop
```

If a test depends on a feature that lives in another branch (not yet merged to main):
- **Option A (preferred)**: decorate with `@pytest.mark.skip(reason="depends on feat/branch-name")` until that branch merges
- **Option B**: note the dependency explicitly in the PR description so CI failure is expected and documented

❌ **Never**: commit tests that fail in CI with `TypeError` or `ImportError` due to missing code from an unmerged branch.

```python
# Example: test depends on ImportPipelineService.ml_categorizer (not in main yet)
@pytest.mark.skip(reason="depends on feat/streamlit-global-controls-pr — remove skip after merge")
def test_ml_fallback_high_confidence(...):
    ...
```

1. **Before writing feature code**:
   - Create test file: `tests/test_<module>.py`
   - Write tests for expected behavior (TDD approach)
   - Tests should fail initially (red phase)

2. **While implementing**:
   - Write minimal code to make tests pass (green phase)
   - Refactor while keeping tests green

3. **Coverage requirements** (minimum enforced):
   - **All new code**: 85%+ coverage (hard minimum)
   - **Critical paths** (imports, validation, classification): 90%+ coverage
   - **Utilities**: 100% coverage (they're small and reusable)
   - Run: `python -m pytest tests/ --cov=src --cov-fail-under=85`

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
- ❌ **Don't leave QMD context files stale** → update the matching QMD in the same commit as the code change; outdated context misleads future agents

## Recent Enhancements (2026-03-29)
 
 **Flet Desktop UI**:
 - Modular desktop interface in `src/ui/flet_ui/`
 - NavigationRail sidebar, AppLayout, and custom Chart containers
 - Family profile switching with PIN protection
 
 **Family Profiles & Security**:
 - `UserService` with bcrypt PIN hashing
 - Profile migration and PIN-protected switching in both UIs
 
 **Manual Entry & Resolution**:
 - `ManualEntryService` for single-transaction injection
 - `DedupService` for interactive batch resolution (Skip/Overwrite/Keep Both)
 
**SQLite Persistence (Previous)**:
 - `DatabaseService` (`src/services/db_service.py`) with hash-based deduplication (`source_hash`)
 - CSV→DB migration: `src/csv_to_db_migrator.py` + `scripts/migrate_csv_to_db.py`
- One-command DB pipeline: `scripts/run_db_pipeline.py`
- DB-backed analytics: `calculate_categorization_stats_from_db()` in analytics service
- See: `docs/context/db.qmd`

**Description Normalization**:
- `src/description_normalizer.py` — deterministic text normalization for ML
- All transactions get `normalized_description` (ML prefers this over raw `description`)
- Backfill support via `DatabaseService.backfill_normalized_descriptions()`

**Account Mapping**:
- `src/account_mapping.py` — bank/account to canonical account resolver
- `config/accounts.yml` — canonical account definitions with bank_id mappings
- Resolves `canonical_account_id` (e.g. `cc:santander_likeu`) for every transaction

**Audit Events**:
- `audit_events` table in SQLite stores all rule changes and import events
- `record_recategorization_event()` in rule service logs category corrections

**Bug Fixes**:
- Import service CSV fallback when DB is empty
- Analytics date parsing: `pd.to_datetime(errors="coerce")` prevents crashes on bad dates

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

**Step 1**: Identify your task area (domain, services, importers, UI, ML, testing, architecture)

**Step 2**: Read the relevant QMD file:
```bash
# For Python agents
from pathlib import Path
context = Path("docs/context/<area>.qmd").read_text()

# For CLI
cat docs/context/<area>.qmd
```

**Step 3**: Use CodeGraph for navigation instead of reading all files:
```bash
# Find symbols without reading files
codegraph_search "function_name"

# Understand dependencies without grep
codegraph_callers "critical_function"

# Check impact before changes without manual search
codegraph_impact "refactor_target"
```

**Step 4**: Reference specific sections as needed (QMD files are organized with clear headers)

**Step 5**: For full context, read `docs/project-index.qmd`

**Benefits**:
- 📉 Reduced token usage (read only relevant context)
- 🎯 Focused context (no irrelevant information)
- 📚 Comprehensive examples (code patterns and best practices)
- 🔄 Always up-to-date (maintained alongside code)
- ⚡ Faster navigation (CodeGraph vs grep/glob)
- 🎯 Precise impact analysis (CodeGraph dependency tracking)

### Example: Adding Tests with QMD + CodeGraph

**Scenario**: Add unit tests for `pdf_utils.py`

1. **Read context**: `cat docs/context/importers.qmd` (PDF utilities section)
2. **Find functions**: `codegraph_search "pdf_utils"` (list all functions)
3. **Check callers**: `codegraph_callers "extract_transactions_from_pdf"` (understand usage)
4. **Check dependencies**: `codegraph_callees "ocr_image"` (identify mocking targets)
5. **Write tests**: Use context + CodeGraph insights to write comprehensive tests
6. **Verify coverage**: `pytest tests/test_pdf_utils.py --cov=src/pdf_utils`

### Example: Refactoring with Impact Analysis

**Scenario**: Consolidate duplicate date parsing functions

1. **Read context**: `cat docs/context/importers.qmd` (Date parsing section)
2. **Find duplicates**: `codegraph_search "parse.*date"` (find all variants)
3. **Check impact**: `codegraph_impact "parse_es_date"` (find all callers)
4. **Analyze dependencies**: `codegraph_callees "parse_es_date"` (check dependencies)
5. **Plan refactor**: Create `src/date_utils.py` based on impact analysis
6. **Migrate safely**: Update all callers identified by CodeGraph

### Example: Architecture Analysis with Full Context

**Scenario**: Create comprehensive improvement plan

1. **Read roadmap**: `cat docs/plan_mejoras.md` (understand planned work)
2. **Read project index**: `cat docs/project-index.qmd` (full architecture overview)
3. **Find untested code**: `codegraph_search "def " | xargs -I{} grep -L "test_{}"` (combine with grep)
4. **Identify critical paths**: `codegraph_callers <critical_function>` for each importer entry point
5. **Read domain contexts**: All `docs/context/*.qmd` files for comprehensive understanding
6. **Create plan**: Prioritized by impact (CodeGraph) and roadmap alignment (plan_mejoras.md)
7. **Document with references**: Include CodeGraph commands for each improvement item

## Future Direction (Roadmap)

**Completed**: SQLite persistence, description normalization, account mapping, Flet UI prototype
**Next up**: Firefly API sync, automated monthly reports, Flet UI migration
**See**: `docs/plan_mejoras.md` for detailed roadmap

## 🎫 Token Management & Agent Handoff

### When Approaching Token Limit (98% usage ~196K/200K tokens)

**STOP and follow this protocol:**

1. **Save Progress**:
   ```bash
   # Create checkpoint file
   cat > docs/checkpoint-$(date +%Y%m%d-%H%M).md <<EOF
   # Checkpoint - $(date +%Y-%m-%d %H:%M)

   ## Completed This Session
   - [List completed tasks with file references]

   ## Currently Working On
   - [Current task status and next steps]

   ## Test Count
   - Before: XXX tests
   - After: YYY tests (+ZZ)

   ## Files Modified
   - Created: [list]
   - Modified: [list]

   ## Next Agent Should
   - [Specific next action]
   - [Files to read first]
   - [Commands to run]
   EOF
   ```

2. **Commit Work**:
   ```bash
   git add -A
   git commit -m "feat: [summary] - [test count change]

   [Bullet list of changes]

   Related: [task/issue references]

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

3. **Update Continuation Plan**:
   - If Phase 1 in progress: Update `docs/phase1-continuation-plan.md`
   - If custom task: Create `docs/[task-name]-continuation.md`
   - Include:
     - What's done
     - What's next
     - CodeGraph commands for next agent
     - QMD files to read
     - Expected outcomes

4. **Update AGENTS.md** (if needed):
   - Add any new patterns discovered
   - Document any tricky areas
   - Update task assignments

### Handoff File Template

When creating continuation plan for next agent:

```markdown
# [Task Name] Continuation Plan

**Last Updated**: [timestamp]
**Session**: [N]
**Token Usage**: [current/max]

## Progress Summary
- [Completed work]
- [Test count change]
- [Files modified]

## Next Steps
1. [Specific action]
2. [Expected outcome]

## For Next Agent

### Quick Start
1. Run: `pytest tests/ -q` (should see XXX tests passing)
2. Read: `docs/context/[area].qmd`
3. Analyze: `codegraph_search "[symbol]"`
4. Continue: [specific instruction]

### Context
- **Working on**: [module/feature]
- **Files**: [list]
- **Related QMD**: `docs/context/[area].qmd`
- **CodeGraph**: `codegraph_callees "[function]"`

### Success Criteria
- [ ] [Specific goal 1]
- [ ] [Specific goal 2]
- [ ] Tests: XXX → YYY (+ZZ)
```

### Token-Efficient Strategies

**Before starting work**:
- ✅ Use CodeGraph instead of reading full files
- ✅ Read only relevant QMD sections
- ✅ Use `--help` flags instead of reading docs
- ✅ Check existing tests for patterns

**During work**:
- ✅ Write code in small chunks, commit frequently
- ✅ Use grep/CodeGraph for lookups
- ✅ Avoid reading large log files
- ✅ Use `head`/`tail` for partial file views

**When context is full**:
- ✅ Commit work immediately
- ✅ Create handoff file
- ✅ Exit gracefully (don't start new complex tasks)

## Getting Help

- **Architecture questions**: Read `docs/project-index.qmd`
- **Module-specific questions**: Read relevant `docs/context/*.qmd`
- **Code examples**: Search QMD files for usage patterns
- **Testing**: Refer to `docs/context/testing.qmd`
- **API reference**: Check docstrings in source files
- **Continuation plans**: Check `docs/*-continuation-plan.md` or `docs/checkpoint-*.md`
