# Project Enhancement & Execution Plan

**Status**: Draft
**Context**: Deep analysis of Ledger Smart Converter codebase.
**Goal**: Stabilize current base, correct documentation drift, and execute the roadmap towards a database-backed architecture.

## 1. Executive Summary

The project is functional but has significant "documentation drift" and some fragility in environment setup. The `docs/context/*.qmd` files—intended as the source of truth for agents—are outdated (e.g., claiming 55 tests when 200+ exist, wrong ML algorithm details).

Immediate priority is **stabilization** (fixing bugs/docs), followed by **standardization** (canonical accounts), and finally **persistence** (SQLite migration).

## 2. Critical Technical Debt (Immediate Actions)

These issues break functionality or development workflows and must be fixed first.

- [ ] **Fix `requirements.txt`**: Add `python-dotenv` (required for local dev env vars).
- [ ] **Fix `src/web_app.py`**: Missing `from pathlib import Path` import causing crash on CSS load.
- [ ] **Update `src/settings.py`**: Explicitly load `.env` file using `load_dotenv()` to ensure environment variables are picked up locally.
- [ ] **Fix ML Documentation**: `ml-categorization.qmd` claims Naive Bayes, code uses `LogisticRegression`. Update code or docs to match.
- [ ] **Standardize Class Names**: Model class is `TransactionCategorizer` in code, often referred to as `MLCategorizer` in docs.

## 3. Documentation Synchronization

The QMD context files are the "brain" for agents. They must be accurate.

- [ ] **`docs/context/testing.qmd`**: Update test counts (currently says 55 tests/8 files; reality ~22 files).
- [ ] **`docs/context/ml-categorization.qmd`**: Correct algorithm description and class names.
- [ ] **`docs/context/importers.qmd`**: Verify listed functions match `src/` signature.

## 4. Strategic Roadmap

Derived from `docs/plan_mejoras.md`, structured for execution.

### Phase 1: Foundation & Standardization (Weeks 1-2)
*Goal: Solidify data consistency before DB migration.*

- [ ] **Canonical Account Model**:
    - Create `config/accounts.yml` to map bank-specific IDs (e.g., "santander_likeu") to canonical IDs (e.g., `cc:santander_likeu`).
    - Update `Transaction` domain model to include `canonical_account_id`.
- [ ] **Unify Output Paths**: Ensure all importers output to a consistently structured `data/` hierarchy (already mostly done, needs verification).

### Phase 2: Persistence Layer (Weeks 3-4)
*Goal: Move from fragile CSVs to robust SQLite.*

- [ ] **Design Schema**: Create `src/database/schema.sql` (Transactions, Accounts, Rules, Imports).
- [ ] **Database Service**: Implement `src/services/db_service.py` with SQLite integration.
- [ ] **Migration Script**: Create `scripts/migrate_csv_to_db.py` to load existing CSV data.

### Phase 3: Advanced Features (Weeks 5+)
*Goal: Leverage DB for features.*

- [ ] **Firefly III Exporter**: Generate Firefly-compatible CSVs (or API calls) strictly from the DB views.
- [ ] **Advanced Analytics**: Rewrite `AnalyticsService` to use SQL queries instead of Pandas for performance and complexity handling.
- [ ] **Audit Trail**: Record rule changes and re-categorization events in a DB table.

## 5. Execution Context for Agents

When working on these tasks, Agents should:

1.  **Check this plan** for priority.
2.  **Read specific QMDs** ONLY after they are marked as "Synchronized".
3.  **Use `codegraph`** to verify current code structure, as docs might still be lagging during the transition.
