---
name: db-operations
description: Use this skill for database operations, schema migrations, running the DB pipeline, and debugging duplicate imports or missing transactions.
---

# Database Operations Skill

## Mandate

Before any database work:
1. **Read `docs/context/db.qmd`** — the canonical reference for schema, API, and safe patterns.
2. **Use CodeGraph** (`codegraph_search "db_service"`, `codegraph_callers "insert_transaction"`) before touching DB code.
3. **Check `src/database/schema.sql`** before any migration — understand the current schema first.

## When to Use This Skill

Use this skill when:
1. Running or debugging the DB pipeline (`scripts/run_db_pipeline.py`)
2. Adding a new column to the `transactions` table
3. Investigating duplicate imports or missing transactions
4. Writing tests that use `DatabaseService`
5. Debugging deduplication issues (`source_hash` collisions or mismatches)

## Workflows

### Workflow A: Add a New Column to `transactions`

1. Add the column to `src/database/schema.sql` in the `CREATE TABLE transactions` block
2. Add an `ALTER TABLE` guard in `DatabaseService._ensure_transactions_columns()` in `src/services/db_service.py`:
   ```python
   alterations = [
       ...
       ("my_new_column", "TEXT"),  # add here
   ]
   ```
3. Update `insert_transaction()` to populate the new column from the input dict
4. Run `db.initialize()` in a test to verify the migration is idempotent
5. Update `docs/context/db.qmd` Schema Overview section

### Workflow B: Run and Verify the DB Pipeline

```bash
# 1. Run pipeline
python scripts/run_db_pipeline.py \
  --db data/ledger.db \
  --data-dir data \
  --accounts config/accounts.yml

# 2. Verify import log
sqlite3 data/ledger.db "SELECT bank_id, status, row_count, processed_at FROM imports ORDER BY processed_at DESC LIMIT 10"

# 3. Verify transaction counts by bank
sqlite3 data/ledger.db "SELECT bank_id, count(*) as tx_count FROM transactions GROUP BY bank_id"

# 4. Check for missing normalized descriptions
sqlite3 data/ledger.db "SELECT count(*) FROM transactions WHERE normalized_description IS NULL OR normalized_description = ''"
```

### Workflow C: Debug Duplicate Import Issue

```python
from pathlib import Path
from services.db_service import DatabaseService

db = DatabaseService(db_path=Path("data/ledger.db"))

# Check if a specific file was already imported
rows = db.fetch_all(
    "SELECT import_id, status, row_count, processed_at FROM imports WHERE source_file = ?",
    ("data/santander/firefly_likeu.csv",)
)
print(rows)

# Check for the specific transaction by source_hash
row = db.fetch_one(
    "SELECT id, date, amount, description FROM transactions WHERE source_hash = ?",
    ("abc123...",)
)
```

## Safety Rules

1. **NEVER UPDATE `raw_description`** after initial insert — it is immutable audit data recording the original source text. Treat it as append-only.

2. **ALWAYS call `db.initialize()` in tests** — it is idempotent and creates the full schema. Never skip this step:
   ```python
   @pytest.fixture
   def db(tmp_path):
       svc = DatabaseService(db_path=tmp_path / "test.db")
       svc.initialize()
       return svc
   ```

3. **NEVER bypass `INSERT OR IGNORE`** for transaction inserts — duplicate `source_hash` rows must be silently dropped, not overwritten. The deduplication contract depends on this.

4. **CHECK `_ensure_transactions_columns()`** when adding new columns — both `schema.sql` AND the `alterations` list in `_ensure_transactions_columns()` must be updated together so existing databases are forward-migrated.

## Required Context Files

- `docs/context/db.qmd` — schema, API reference, safe patterns (read first)
- `src/database/schema.sql` — authoritative schema definition
- `tests/test_db_service.py` — test patterns for DatabaseService
- `src/services/db_service.py` — DatabaseService implementation

## Related Agents
- **Database Agent**: Specialist in DB pipeline and schema management.
