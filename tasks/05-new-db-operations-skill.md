# Task: Create skills/db-operations/SKILL.md

**Priority**: Medium
**Effort**: Small (30 min)
**Files**: `skills/db-operations/SKILL.md` (new)

---

## Why

Every other major subsystem has a skill (`bank-importer`, `analytics`, `testing`, etc.)
but there is no skill for the database/persistence layer. Agents working on DB tasks
have no structured workflow — they must infer it from source code.

---

## Skill Structure

Use `skills/analytics/SKILL.md` as a template. The skill should cover:

### Mandate

```markdown
## Core Mandate

Token-efficient DB work:
1. Read `docs/context/db.qmd` FIRST (not the source files).
2. Use `codegraph_search "DatabaseService"` to find the entry point.
3. Check `src/database/schema.sql` for column definitions before writing migrations.
4. Never read `db_service.py` in full — use CodeGraph for targeted lookups.
```

### When To Use This Skill

```markdown
- Adding new columns to any table
- Writing queries against `transactions`, `accounts`, `imports`, or `audit_events`
- Debugging the CSV → SQLite migration
- Adding new audit event types
- Changing `backfill_normalized_descriptions()` or similar maintenance methods
```

### Step-by-Step Workflows

#### Add a new column to transactions

```
1. Add column to `src/database/schema.sql` in the CREATE TABLE block
2. Add ALTER TABLE entry in `db_service._ensure_transactions_columns()`
3. Update `insert_transaction()` to populate the new column
4. Update `docs/context/db.qmd` schema table
5. Write a test in `tests/test_db_service.py`
```

#### Run and verify the DB pipeline

```
1. python scripts/run_db_pipeline.py
2. sqlite3 data/ledger.db "SELECT COUNT(*) FROM transactions"
3. sqlite3 data/ledger.db "SELECT bank_id, COUNT(*) FROM transactions GROUP BY bank_id"
4. Check audit_events: sqlite3 data/ledger.db "SELECT * FROM audit_events ORDER BY id DESC LIMIT 10"
```

#### Debug a duplicate import

```
1. Check source_hash: query transactions WHERE source_hash = build_source_hash(...)
2. Check imports table: SELECT * FROM imports WHERE source_file = ?
3. If csv_to_db_migrator wrongly skipped: verify the "firefly" filename filter
```

### Safety Rules

```markdown
- **NEVER** issue `UPDATE transactions SET raw_description = ...` in maintenance scripts
  (only backfill can update normalized_description — raw is immutable after insert)
- **ALWAYS** run `initialize()` before the first query in tests (uses `tmp_path`)
- **NEVER** bypass `INSERT OR IGNORE` with `INSERT OR REPLACE` — it would lose the id
- **CHECK** `_ensure_transactions_columns()` when adding new columns to avoid breaking
  existing databases that don't have the column yet
```

### Required Context Files

```markdown
- `docs/context/db.qmd` — canonical DB context
- `src/database/schema.sql` — ground truth for column definitions
- `tests/test_db_service.py` — usage examples and expected behavior
```

---

## Acceptance Criteria

- [ ] `skills/db-operations/SKILL.md` exists
- [ ] Covers: when to use, 3 step-by-step workflows, safety rules
- [ ] References `docs/context/db.qmd` as primary context
- [ ] Referenced from `AGENTS.md` Database Agent row (see task 02)
