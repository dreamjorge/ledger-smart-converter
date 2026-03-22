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
- After `sync_rules_to_db()`, the `rules` table contains one row per rule from `rules.yml`
- Re-running sync is idempotent (no duplicates)
- Disabled rules have `enabled = 0`

**Step 1: Write the failing test**

```python
def test_sync_rules_to_db_populates_table(tmp_path):
    from pathlib import Path
    from services.db_service import DatabaseService
    from services.rule_service import sync_rules_to_db

    rules_yml = tmp_path / "rules.yml"
    rules_yml.write_text("""
categorization_rules:
  - merchant: OXXO
    regex: "OXXO.*"
    expense_account: "Expenses:Food:Groceries"
    bucket_tag: groceries
  - merchant: Uber
    regex: "UBER.*"
    expense_account: "Expenses:Transport:Uber"
    bucket_tag: transport
""")
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()

    sync_rules_to_db(db, rules_path=rules_yml)

    rows = db.fetch_all("SELECT * FROM rules WHERE enabled = 1")
    assert len(rows) == 2
    patterns = {r["pattern"] for r in rows}
    assert "OXXO.*" in patterns
    assert "UBER.*" in patterns

def test_sync_rules_to_db_is_idempotent(tmp_path):
    from pathlib import Path
    from services.db_service import DatabaseService
    from services.rule_service import sync_rules_to_db

    rules_yml = tmp_path / "rules.yml"
    rules_yml.write_text("""
categorization_rules:
  - merchant: OXXO
    regex: "OXXO.*"
    expense_account: "Expenses:Food:Groceries"
    bucket_tag: groceries
""")
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()

    sync_rules_to_db(db, rules_path=rules_yml)
    sync_rules_to_db(db, rules_path=rules_yml)  # second sync

    rows = db.fetch_all("SELECT COUNT(*) AS cnt FROM rules")
    assert rows[0]["cnt"] == 1  # not 2
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

**Step 1: Add the function**

```python
import yaml
from pathlib import Path
from services.db_service import DatabaseService

def sync_rules_to_db(db: DatabaseService, rules_path: Path) -> int:
    """Sync categorization_rules from rules.yml into the rules DB table.

    Uses INSERT OR IGNORE on pattern so re-runs are safe.
    Returns count of newly inserted rows.
    """
    with open(rules_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    rules = data.get("categorization_rules", [])
    inserted = 0
    for rule in rules:
        pattern = rule.get("regex", "")
        if not pattern:
            continue
        db._conn.execute(
            "INSERT OR IGNORE INTO rules (name, pattern, expense, tags, priority, enabled) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (
                rule.get("merchant", ""),
                pattern,
                rule.get("expense_account", ""),
                rule.get("bucket_tag", ""),
                rule.get("priority", 100),
            ),
        )
        if db._conn.execute("SELECT changes()").fetchone()[0]:
            inserted += 1
    db._conn.commit()
    return inserted
```

> **Note:** If `DatabaseService` doesn't expose `_conn` directly, check `db_service.py` — use the connection attribute it does expose, or add a `execute()` wrapper method to `DatabaseService` instead.

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
