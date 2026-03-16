# Task: Update AGENTS.md

**Priority**: High
**Effort**: Medium (1–2 hours)
**Files**: `AGENTS.md`

---

## Why

AGENTS.md is the authoritative routing document for all agents. It has several stale
sections and is missing key context for the DB layer, the Flet prototype, and the
`@pytest.mark.slow` test pattern introduced in the current branch.

---

## Specific Changes

### 1. Add `/run-db-pipeline` slash command to the table

```markdown
| `/run-db-pipeline` | Run the full CSV→SQLite ETL pipeline and inspect results |
```

Also create the corresponding file `.claude/commands/run-db-pipeline.md` with steps:
1. Run `python scripts/run_db_pipeline.py`
2. Check `data/ledger.db` for row counts
3. On error, consult `src/db_pipeline.py` and `src/csv_to_db_migrator.py`

### 2. Add `db.qmd` to the QMD Context Configuration table

```markdown
| **Database** | `docs/context/db.qmd` | SQLite schema, DatabaseService methods, migration, audit events |
```

Also add the corresponding row to the "What 'keeping context updated' means" table:

```markdown
| New DB method, schema change, or migration logic | `db.qmd` |
```

### 3. Add a **Database Agent** to the Subagent Role Assignments table

```markdown
| **Database Agent** | SQLite persistence, migrations, audit trail, DB pipeline | `src/services/db_service.py`, `src/db_pipeline.py`, `src/csv_to_db_migrator.py`, `src/database/schema.sql` | `db.qmd` | (create db-operations skill; see task 05) |
```

### 4. Update the Parallel Delegation Pattern example to include the Database Agent

```markdown
Example: "Add new bank with ML rules and DB storage"
  → Import Agent: create src/import_<bank>_firefly.py
  → ML/Rules Agent: add categorization rules to config/rules.yml
  → Testing Agent: write tests/test_<bank>.py (TDD first)
  → Database Agent: ensure insert_transaction() handles new bank_id
```

### 5. Add "Working on Database / Persistence" to Critical Files by Task

```markdown
### Working on Database / Persistence
- Read: `docs/context/db.qmd`
- Files: `src/services/db_service.py`, `src/database/schema.sql`, `src/db_pipeline.py`, `src/csv_to_db_migrator.py`
```

### 6. Add "Run DB Pipeline" to Common Tasks Quick Reference

```markdown
### Run or Debug DB Pipeline
1. `python scripts/run_db_pipeline.py` — full ETL
2. On failure: check `src/db_pipeline.py` → `src/csv_to_db_migrator.py`
3. Inspect DB: `sqlite3 data/ledger.db ".tables"` then `SELECT COUNT(*) FROM transactions`
4. Audit trail: `SELECT * FROM audit_events ORDER BY id DESC LIMIT 20`
```

### 7. Update Testing & CI section — add `@pytest.mark.slow` info

```diff
-**Run Tests**: `python -m pytest tests/ -v`
-**Quick Run**: `python -m pytest tests/ -q`
-**Current**: 521 tests passing ✅
+**Fast Run** (skips ML training): `pytest -m "not slow" -q`   (~34s)
+**Full Run** (all tests):         `pytest -q`                  (~55+ min on slow machines)
+**Slow tests**: ML training tests tagged `@pytest.mark.slow` in `test_ml_categorizer*.py`
+**Current**: 554 tests (546 non-slow + 8 slow)
```

### 8. Update Recent Enhancements section (stale — dated 2026-02-06)

Replace with:
```markdown
## Recent Enhancements (2026-03-16)

**Persistence Layer**:
- SQLite database via `src/services/db_service.py` + `src/database/schema.sql`
- Full ETL pipeline: `src/db_pipeline.py`, `scripts/run_db_pipeline.py`
- CSV → DB migration: `src/csv_to_db_migrator.py`
- Audit events table for operation tracking

**Description Normalization**:
- `src/description_normalizer.py`: deterministic merchant name cleaning
- Integrated into ML training (prefers `normalized_description` over raw text)

**Account Mapping**:
- `src/account_mapping.py` + `config/accounts.yml`: canonical account IDs across banks

**Fixes (update-md-files branch)**:
- `CanonicalTransaction.amount` is now `Optional[float]` (was crashing on None)
- `analytics_service.py`: date column now coerced to datetime before `.dt.to_period()`
- `db_service.py`: backfill no longer overwrites `raw_description`

**Test Infrastructure**:
- `@pytest.mark.slow` on ML training tests — fast suite now skippable
```

### 9. Update Future Direction (Roadmap) section

```diff
-**Next Phase**: SQLite persistence, account unification, hash-based deduplication
+**Next Phase**: Firefly API sync, automated monthly reports, Flet UI to replace Streamlit
 **See**: `docs/plan_mejoras.md` for detailed roadmap
```

---

## Acceptance Criteria

- [ ] `/run-db-pipeline` command documented
- [ ] `db.qmd` in QMD routing table
- [ ] Database Agent in Subagent Role table
- [ ] "Working on Database" section in Critical Files by Task
- [ ] Testing section mentions `@pytest.mark.slow` and correct test counts
- [ ] Recent Enhancements reflects 2026-03-16 changes
