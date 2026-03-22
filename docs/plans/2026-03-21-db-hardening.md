# DB Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the SQLite persistence layer — add `dashboard_metrics` view, enforce DB-first contract in the import pipeline, and ensure `_ensure_transactions_columns()` is forward-compatible.

**Architecture:** All changes go through `DatabaseService`; no raw SQL outside `db_service.py`. The new `dashboard_metrics` view aggregates by period + category inside `schema.sql`. `generic_importer.py` delegates persistence to `DatabaseService` instead of writing CSV directly when a DB path is available.

**Tech Stack:** Python 3.8+, SQLite, pytest, pandas

---

## Epic 1 — `dashboard_metrics` Aggregation View

### Task 1: Write failing test for `dashboard_metrics` view

**Files:**
- Test: `tests/test_db_service.py`

**Acceptance Criteria:**
- Query `SELECT * FROM dashboard_metrics` returns rows with columns: `statement_period`, `category`, `bank_id`, `tx_count`, `total_amount`
- Filters work: `WHERE bank_id = ?` returns only that bank's rows
- Empty DB returns zero rows (not an error)

**Step 1: Write the failing test**

```python
# In tests/test_db_service.py — add after existing DB tests

def test_dashboard_metrics_view_exists(tmp_path):
    from services.db_service import DatabaseService
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    rows = db.fetch_all("SELECT * FROM dashboard_metrics")
    assert isinstance(rows, list)  # view exists, returns empty list

def test_dashboard_metrics_aggregates_by_period_and_category(tmp_path):
    from services.db_service import DatabaseService
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    db.upsert_account("ACC1", "Test Account", bank_id="testbank")
    # Insert two transactions — same period, same category
    db.insert_transaction({
        "source_hash": "hash1", "date": "2024-01-15", "amount": 100.0,
        "currency": "MXN", "description": "OXXO", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "testbank",
        "statement_period": "2024-01", "category": "Groceries",
        "transaction_type": "withdrawal", "source_file": "test.csv",
    })
    db.insert_transaction({
        "source_hash": "hash2", "date": "2024-01-20", "amount": 50.0,
        "currency": "MXN", "description": "WALMART", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "testbank",
        "statement_period": "2024-01", "category": "Groceries",
        "transaction_type": "withdrawal", "source_file": "test.csv",
    })
    rows = db.fetch_all("SELECT * FROM dashboard_metrics WHERE bank_id = ?", ("testbank",))
    assert len(rows) == 1
    assert rows[0]["statement_period"] == "2024-01"
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["tx_count"] == 2
    assert abs(rows[0]["total_amount"] - 150.0) < 0.01
```

**Step 2: Run test to verify it fails**

```bash
cd /root/ledger-smart-converter
pytest tests/test_db_service.py::test_dashboard_metrics_view_exists tests/test_db_service.py::test_dashboard_metrics_aggregates_by_period_and_category -v
```

Expected: `FAILED` — `OperationalError: no such table: dashboard_metrics`

---

### Task 2: Add `dashboard_metrics` view to schema

**Files:**
- Modify: `src/database/schema.sql`

**Step 1: Append view definition**

Add after the `firefly_export` view in `src/database/schema.sql`:

```sql
CREATE VIEW IF NOT EXISTS dashboard_metrics AS
SELECT
    COALESCE(statement_period, 'unknown') AS statement_period,
    COALESCE(category, 'Uncategorized')   AS category,
    bank_id,
    COUNT(*)                              AS tx_count,
    ROUND(SUM(amount), 2)                 AS total_amount
FROM transactions
WHERE transaction_type = 'withdrawal'
GROUP BY statement_period, category, bank_id;
```

**Step 2: Run tests**

```bash
pytest tests/test_db_service.py::test_dashboard_metrics_view_exists tests/test_db_service.py::test_dashboard_metrics_aggregates_by_period_and_category -v
```

Expected: `PASSED`

**Step 3: Commit**

```bash
git add src/database/schema.sql tests/test_db_service.py
git commit -m "feat(db): add dashboard_metrics aggregation view"
```

---

## Epic 2 — Forward-Compatible Column Migration

### Task 3: Verify `_ensure_transactions_columns()` covers all current schema columns

**Files:**
- Read: `src/services/db_service.py`

**Step 1: Audit existing guard**

Scan `_ensure_transactions_columns()` in `db_service.py`. Confirm every column in `schema.sql`'s `transactions` table has a corresponding `ALTER TABLE` guard.

Columns that must be present in the guard:
- `raw_description TEXT`
- `normalized_description TEXT`
- `canonical_account_id TEXT`
- `merchant TEXT`
- `source_name TEXT`
- `destination_name TEXT`
- `statement_period TEXT`
- `tags TEXT`
- `transaction_type TEXT`
- `import_id INTEGER`
- `updated_at TEXT`

**Step 2: Write failing test for a missing column**

```python
def test_ensure_columns_adds_missing_column(tmp_path):
    """Simulates an old DB missing normalized_description."""
    import sqlite3
    from services.db_service import DatabaseService

    db_path = tmp_path / "old.db"
    # Create minimal old schema without normalized_description
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE transactions (
        id INTEGER PRIMARY KEY, source_hash TEXT UNIQUE,
        date TEXT, amount REAL, currency TEXT DEFAULT 'MXN',
        description TEXT, account_id TEXT, canonical_account_id TEXT,
        bank_id TEXT, transaction_type TEXT DEFAULT 'withdrawal',
        source_file TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("CREATE TABLE IF NOT EXISTS accounts (account_id TEXT PRIMARY KEY, display_name TEXT, type TEXT DEFAULT 'credit_card', bank_id TEXT, closing_day INTEGER, currency TEXT DEFAULT 'MXN', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    con.execute("CREATE TABLE IF NOT EXISTS imports (import_id INTEGER PRIMARY KEY, bank_id TEXT, source_file TEXT, processed_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT, row_count INTEGER DEFAULT 0, error TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY, event_type TEXT, entity_type TEXT, entity_id TEXT, payload_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    con.execute("CREATE TABLE IF NOT EXISTS rules (rule_id INTEGER PRIMARY KEY, name TEXT, pattern TEXT, expense TEXT, tags TEXT, priority INTEGER DEFAULT 100, enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    con.commit()
    con.close()

    # initialize() must add missing columns without error
    db = DatabaseService(db_path=db_path)
    db.initialize()

    # Verify column now exists
    con2 = sqlite3.connect(db_path)
    cols = [row[1] for row in con2.execute("PRAGMA table_info(transactions)")]
    con2.close()
    assert "normalized_description" in cols
    assert "raw_description" in cols
```

**Step 3: Run test**

```bash
pytest tests/test_db_service.py::test_ensure_columns_adds_missing_column -v
```

Note result — fix any missing guards in `_ensure_transactions_columns()` until test passes.

**Step 4: Commit**

```bash
git add src/services/db_service.py tests/test_db_service.py
git commit -m "fix(db): ensure all schema columns have ALTER TABLE migration guards"
```

---

## Epic 3 — DB-First Contract in Pipeline

### Task 4: Write test asserting pipeline does NOT write duplicate rows on re-run

**Files:**
- Test: `tests/test_db_pipeline.py`

**Acceptance Criteria:**
- Running `db_pipeline.run()` twice against the same CSV produces the same row count, not double
- `imports` table records both runs with `status = "success"`

**Step 1: Write the failing test**

```python
def test_pipeline_is_idempotent(tmp_path):
    """Re-running pipeline against same CSV must not duplicate transactions."""
    import csv
    from pathlib import Path
    from db_pipeline import run_pipeline  # adjust import to actual entry point

    # Create a minimal CSV
    csv_path = tmp_path / "data" / "testbank_transactions.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date","amount","description","account_id","bank_id"])
        w.writeheader()
        w.writerow({"date":"2024-01-01","amount":"100.00","description":"OXXO","account_id":"ACC1","bank_id":"testbank"})

    db_path = tmp_path / "ledger.db"
    accounts_path = tmp_path / "accounts.yml"
    accounts_path.write_text("accounts:\n  - account_id: ACC1\n    display_name: Test\n    bank_id: testbank\n")

    run_pipeline(db_path=db_path, data_dir=tmp_path / "data", accounts_path=accounts_path)
    run_pipeline(db_path=db_path, data_dir=tmp_path / "data", accounts_path=accounts_path)

    from services.db_service import DatabaseService
    db = DatabaseService(db_path=db_path)
    rows = db.fetch_all("SELECT COUNT(*) AS cnt FROM transactions")
    assert rows[0]["cnt"] == 1  # NOT 2
```

**Step 2: Run test**

```bash
pytest tests/test_db_pipeline.py::test_pipeline_is_idempotent -v
```

Fix any idempotency issues until passing.

**Step 3: Commit**

```bash
git add tests/test_db_pipeline.py
git commit -m "test(db): assert pipeline idempotency on re-run"
```

---

## Definition of Done

- [ ] `dashboard_metrics` view exists and all tests pass
- [ ] `_ensure_transactions_columns()` covers all current schema columns
- [ ] Pipeline idempotency test passes
- [ ] `pytest tests/ -m "not slow" -q` exits green
