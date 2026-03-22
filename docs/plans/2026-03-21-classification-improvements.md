# Classification Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve ML categorization reliability — sync rules from `rules.yml` into the `rules` DB table, add an auto-categorization coverage metric, and trigger retraining after each import batch.

**Architecture:** `RuleService` gains a `sync_rules_to_db()` method; `DatabaseService` gains a `coverage()` query helper. The import pipeline calls `sync_rules_to_db()` after rule merge and triggers `train_global_model()` after a new import batch completes. No changes to the rule YAML workflow itself.

**Tech Stack:** Python 3.8+, sklearn, joblib, PyYAML, pytest

---

## Epic 1 — Rules DB Sync

### Task 1: Write failing test for `sync_rules_to_db`

**Files:**
- Test: `tests/test_rule_service.py`

**Acceptance Criteria:**
- After `sync_rules_to_db()`, the `rules` table contains one row **per regex pattern** from `rules.yml` (a single rule with two patterns creates two rows)
- Re-running sync is idempotent — `UNIQUE(pattern)` constraint + `INSERT OR IGNORE` prevents duplicates
- Returns count of newly inserted rows (0 on re-run)

> **YAML schema note:** `config/rules.yml` uses `rules[*].any_regex` (list of patterns),
> `rules[*].set.expense`, and `rules[*].set.tags` (list). The old `categorization_rules` /
> `regex` / `expense_account` / `bucket_tag` field names do **not** exist in this repo.

**Step 1: Write the failing test**

```python
def test_sync_rules_to_db_populates_table(tmp_path):
    from services.db_service import DatabaseService
    from services.rule_service import sync_rules_to_db

    rules_yml = tmp_path / "rules.yml"
    # Use the real rules.yml schema: rules[*].any_regex / set.expense / set.tags
    rules_yml.write_text("""
rules:
  - name: Groceries
    any_regex: [oxxo, walmart]
    set:
      expense: "Expenses:Food:Groceries"
      tags: [bucket:groceries]
  - name: Uber
    any_regex: [uber]
    set:
      expense: "Expenses:Transport:Uber"
      tags: [bucket:transport]
""")
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()

    inserted = sync_rules_to_db(db, rules_path=rules_yml)

    # 3 rows: oxxo + walmart + uber (one row per pattern)
    assert inserted == 3
    rows = db.fetch_all("SELECT * FROM rules WHERE enabled = 1")
    assert len(rows) == 3
    patterns = {r["pattern"] for r in rows}
    assert "oxxo" in patterns
    assert "walmart" in patterns
    assert "uber" in patterns

def test_sync_rules_to_db_is_idempotent(tmp_path):
    from services.db_service import DatabaseService
    from services.rule_service import sync_rules_to_db

    rules_yml = tmp_path / "rules.yml"
    rules_yml.write_text("""
rules:
  - name: Groceries
    any_regex: [oxxo, walmart]
    set:
      expense: "Expenses:Food:Groceries"
      tags: [bucket:groceries]
""")
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()

    sync_rules_to_db(db, rules_path=rules_yml)
    inserted2 = sync_rules_to_db(db, rules_path=rules_yml)  # second sync

    assert inserted2 == 0  # nothing new
    rows = db.fetch_all("SELECT COUNT(*) AS cnt FROM rules")
    assert rows[0]["cnt"] == 2  # oxxo + walmart, not 4
```

**Step 2: Run test to verify it fails**

```bash
cd /root/ledger-smart-converter
pytest tests/test_rule_service.py::test_sync_rules_to_db_populates_table -v
```

Expected: `ImportError` or `AttributeError` — `sync_rules_to_db` does not exist yet.

---

### Task 2: Implement `sync_rules_to_db` in `rule_service.py`

**Files:**
- Modify: `src/services/rule_service.py`
- Modify: `src/services/db_service.py` (add `insert_rule()` public method)
- Modify: `src/database/schema.sql` (add `UNIQUE` constraint on `pattern`)

**Prerequisite — add `UNIQUE(pattern)` to the `rules` table in `schema.sql`:**

```sql
CREATE TABLE IF NOT EXISTS rules (
    rule_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT,
    pattern   TEXT NOT NULL UNIQUE,   -- UNIQUE enables INSERT OR IGNORE dedup
    expense   TEXT,
    tags      TEXT,
    priority  INTEGER NOT NULL DEFAULT 100,
    enabled   INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

> **Note on legacy DBs:** SQLite cannot add a UNIQUE constraint via `ALTER TABLE`.
> Existing databases must be re-initialized to gain the constraint. Without it,
> `INSERT OR IGNORE` has no dedup target and re-runs will insert duplicates.

**Add `insert_rule()` to `DatabaseService` (public API — do not use `_conn` directly from the service layer):**

```python
def insert_rule(self, name: str, pattern: str, expense: str = "",
                tags: str = "", priority: int = 100) -> bool:
    """Insert a rule row. INSERT OR IGNORE skips duplicate patterns.

    Returns True if inserted (new), False if skipped (duplicate pattern).
    Requires UNIQUE(pattern) constraint — see schema.sql.
    """
    with self._connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO rules (name, pattern, expense, tags, priority, enabled) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (name, pattern, expense, tags, priority),
        )
        conn.commit()
        return cursor.rowcount > 0
```

**Step 1: Add `sync_rules_to_db` to `rule_service.py`**

```python
from pathlib import Path
from services.db_service import DatabaseService

def sync_rules_to_db(db: DatabaseService, rules_path: Path) -> int:
    """Sync rules from rules.yml into the DB rules table.

    Maps the real YAML schema:
      rules[*].any_regex  → one DB row per pattern
      rules[*].set.expense → expense column
      rules[*].set.tags   → comma-joined string in tags column

    Uses INSERT OR IGNORE (backed by UNIQUE(pattern)) for idempotency.
    Returns count of newly inserted rows (0 on re-run).
    """
    data = _load_yaml(rules_path)  # existing helper in rule_service.py
    rules = (data or {}).get("rules", [])
    inserted = 0
    for rule in rules:
        set_block = rule.get("set", {}) or {}
        name     = rule.get("name", "") or ""
        expense  = set_block.get("expense", "") or ""
        raw_tags = set_block.get("tags", [])
        tags     = ",".join(raw_tags) if isinstance(raw_tags, list) else (raw_tags or "")
        priority = rule.get("priority", 100) or 100
        for pattern in _rule_regexes(rule):  # existing helper; yields each any_regex entry
            if db.insert_rule(name=name, pattern=pattern, expense=expense,
                              tags=tags, priority=priority):
                inserted += 1
    return inserted
```

**Step 2: Run tests**

```bash
pytest tests/test_rule_service.py::test_sync_rules_to_db_populates_table tests/test_rule_service.py::test_sync_rules_to_db_is_idempotent -v
```

Expected: `PASSED`

**Step 3: Commit**

```bash
git add src/services/rule_service.py tests/test_rule_service.py
git commit -m "feat(rules): sync rules.yml into DB rules table, idempotent"
```

---

## Epic 2 — Coverage Metric

### Task 3: Write failing test for `categorization_coverage()`

**Files:**
- Test: `tests/test_db_service.py`

**Acceptance Criteria:**
- Returns `{"categorized": N, "total": M, "pct": float}` dict
- `pct` is 0.0 when no transactions exist
- `pct` is 1.0 when all withdrawals have a non-empty category
- Deposits are excluded from the denominator

**Step 1: Write the failing test**

```python
def test_categorization_coverage_empty_db(tmp_path):
    from services.db_service import DatabaseService
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    result = db.categorization_coverage()
    assert result == {"categorized": 0, "total": 0, "pct": 0.0}

def test_categorization_coverage_partial(tmp_path):
    from services.db_service import DatabaseService
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    db.upsert_account("ACC1", "Test", bank_id="b1")
    base = {
        "currency": "MXN", "account_id": "ACC1",
        "canonical_account_id": "ACC1", "bank_id": "b1",
        "description": "X", "transaction_type": "withdrawal", "source_file": "f.csv",
    }
    db.insert_transaction({**base, "source_hash": "h1", "date": "2024-01-01", "amount": 10.0, "category": "Groceries"})
    db.insert_transaction({**base, "source_hash": "h2", "date": "2024-01-02", "amount": 20.0, "category": None})
    db.insert_transaction({**base, "source_hash": "h3", "date": "2024-01-03", "amount": 5.0,  "category": ""})
    result = db.categorization_coverage()
    assert result["total"] == 3
    assert result["categorized"] == 1
    assert abs(result["pct"] - 1/3) < 0.01
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_db_service.py::test_categorization_coverage_empty_db -v
```

Expected: `AttributeError: 'DatabaseService' object has no attribute 'categorization_coverage'`

---

### Task 4: Implement `categorization_coverage()` in `DatabaseService`

**Files:**
- Modify: `src/services/db_service.py`

**Step 1: Add method**

```python
def categorization_coverage(self) -> dict:
    """Return categorization coverage stats for withdrawal transactions.

    Returns:
        {"categorized": int, "total": int, "pct": float}
    """
    row = self.fetch_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN category IS NOT NULL AND category != '' THEN 1 ELSE 0 END) AS categorized
        FROM transactions
        WHERE transaction_type = 'withdrawal'
        """
    )
    total = row["total"] if row and row["total"] else 0
    categorized = row["categorized"] if row and row["categorized"] else 0
    pct = round(categorized / total, 4) if total > 0 else 0.0
    return {"categorized": categorized, "total": total, "pct": pct}
```

**Step 2: Run tests**

```bash
pytest tests/test_db_service.py::test_categorization_coverage_empty_db tests/test_db_service.py::test_categorization_coverage_partial -v
```

Expected: `PASSED`

**Step 3: Commit**

```bash
git add src/services/db_service.py tests/test_db_service.py
git commit -m "feat(db): add categorization_coverage() metric helper"
```

---

## Epic 3 — Retrain Trigger After Import

### Task 5: Write failing test asserting retrain is called after import

**Files:**
- Test: `tests/test_import_service.py`

**Acceptance Criteria:**
- When `ImportService.run_import()` completes successfully, `train_global_model` is invoked once
- Retrain is NOT called when import fails (status = "error")

**Step 1: Write the failing test**

```python
def test_retrain_triggered_after_successful_import(tmp_path, monkeypatch):
    from unittest.mock import MagicMock, patch
    # This test verifies the integration point — adjust module path as needed
    calls = []
    monkeypatch.setattr("ml_categorizer.train_global_model", lambda: calls.append(1))

    from services.import_service import ImportService
    svc = ImportService(db_path=tmp_path / "test.db", data_dir=tmp_path)
    # Run a minimal successful import ... (adapt to actual ImportService interface)
    # Assert retrain was called
    assert len(calls) == 1
```

> **Note:** Adjust the `ImportService` constructor and method call to match `src/services/import_service.py`. The goal is to assert the retrain hook exists in the success path.

**Step 2: Verify current behavior** — run test, observe failure.

**Step 3: Add retrain call in import service success path**

In `src/services/import_service.py`, find the success path after `update_import_status(import_id, "success")` and add:

```python
try:
    from ml_categorizer import train_global_model
    train_global_model()
except Exception as exc:  # never block an import for ML failure
    logger.warning("ML retrain after import failed: %s", exc)
```

**Step 4: Run tests**

```bash
pytest tests/test_import_service.py -v -k "retrain"
```

**Step 5: Commit**

```bash
git add src/services/import_service.py tests/test_import_service.py
git commit -m "feat(ml): trigger model retrain after successful import batch"
```

---

## Definition of Done

- [ ] `sync_rules_to_db()` exists, is idempotent, all tests pass
- [ ] `categorization_coverage()` returns correct stats, all tests pass
- [ ] Retrain is triggered in import success path
- [ ] `pytest tests/ -m "not slow" -q` exits green
