# Project Enhancement & Execution Plan

**Status**: Completed (roadmap phases + DB-first runtime integration updated 2026-02-13)
**Context**: Deep analysis of Ledger Smart Converter codebase.
**Goal**: Stabilize current base, correct documentation drift, and execute the roadmap towards a database-backed architecture.

## 1. Executive Summary

The project is functional but has significant "documentation drift" and some fragility in environment setup. The `docs/context/*.qmd` files—intended as the source of truth for agents—are outdated (e.g., claiming 55 tests when 200+ exist, wrong ML algorithm details).

Immediate priority is **stabilization** (fixing bugs/docs), followed by **standardization** (canonical accounts), and finally **persistence** (SQLite migration).

## 2. Critical Technical Debt (Immediate Actions)

These issues break functionality or development workflows and must be fixed first.

- [x] **Fix `requirements.txt`**: Added `python-dotenv`.
- [x] **Fix `src/web_app.py`**: `from pathlib import Path` is present (verified).
- [x] **Update `src/settings.py`**: Added explicit `.env` loading through `load_dotenv()`.
- [x] **Fix ML Documentation**: `ml-categorization.qmd` now reflects `LogisticRegression` implementation.
- [x] **Standardize Class Names**: QMD context now consistently references `TransactionCategorizer`.

## 3. Documentation Synchronization

The QMD context files are the "brain" for agents. They must be accurate.

- [x] **`docs/context/testing.qmd`**: Updated counts and coverage notes to current repo state.
- [x] **`docs/context/ml-categorization.qmd`**: Corrected algorithm, training data source, and class names.
- [x] **`docs/context/importers.qmd`**: Updated key function signatures to match current code.

## 4. Strategic Roadmap

Derived from `docs/plan_mejoras.md`, structured for execution.

### Phase 1: Foundation & Standardization (Weeks 1-2)
*Goal: Solidify data consistency before DB migration.*

- [x] **Canonical Account Model**:
    - Created `config/accounts.yml` with canonical mappings for current banks.
    - Updated `CanonicalTransaction` model to include `canonical_account_id`.
    - Added resolver module `src/account_mapping.py` and wired it into `src/generic_importer.py`.
    - Added/updated tests: `tests/test_account_mapping.py`, `tests/test_validation.py`, `tests/test_generic_importer_branches.py`.
- [x] **Unify Output Paths**: Standardized fallback output hierarchy in `src/services/import_service.py` to `data/<bank_id>/...` and updated tests.

### Phase 2: Persistence Layer (Weeks 3-4)
*Goal: Move from fragile CSVs to robust SQLite.*

- [x] **Design Schema**: Created `src/database/schema.sql` with `transactions`, `accounts`, `rules`, `imports` tables.
- [x] **Database Service**: Implemented `src/services/db_service.py` (schema init, account upsert, import audit, transaction insert/dedup).
- [x] **Migration Script**: Created `scripts/migrate_csv_to_db.py` (wrapper) + `src/csv_to_db_migrator.py` (core migration logic).

### Phase 3: Advanced Features (Weeks 5+)
*Goal: Leverage DB for features.*

- [x] **Firefly III Exporter**: Implemented `src/services/firefly_export_service.py` using SQL view `firefly_export`.
- [x] **Advanced Analytics**: Added SQL-backed `calculate_categorization_stats_from_db(...)` in `src/services/analytics_service.py`.
- [x] **Audit Trail**: Added `audit_events` table and wired rule stage/merge + recategorization event recording.
- [x] **DB-first Runtime Wiring**: Analytics UI now loads transactions via SQLite first (`data/ledger.db`) with CSV fallback, and rule actions write audit events with DB path wiring.

## 5. Execution Context for Agents

When working on these tasks, Agents should:

1.  **Check this plan** for priority.
2.  **Read specific QMDs** ONLY after they are marked as "Synchronized".
3.  **Use `codegraph`** to verify current code structure, as docs might still be lagging during the transition.
