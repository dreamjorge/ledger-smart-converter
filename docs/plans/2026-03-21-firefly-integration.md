# Firefly Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the CSV export service column mapping, add per-account filtering, and lay the foundation for Firefly III API sync (POST transactions via HTTP).

**Architecture:** `firefly_export_service.py` gets hardened column handling and a `FireflyApiClient` class added alongside it. The API client is optional — CSV export remains the primary path. All network calls are isolated behind an interface so tests can run offline.

**Tech Stack:** Python 3.8+, requests, pytest, SQLite, pandas

---

## Epic 1 — Fix CSV Export Column Mapping

### Task 1: Write failing test that validates export column names

**Files:**
- Test: `tests/test_firefly_export_service.py`

**Acceptance Criteria:**
- Exported CSV has exactly these columns (matching Firefly III import format): `type`, `date`, `amount`, `currency_code`, `description`, `source_name`, `destination_name`, `category_name`, `tags`
- `amount` is a string formatted to 2 decimal places (e.g., `"100.50"`)
- `currency_code` is `MXN` (not empty)
- `category_name` is `""` when uncategorized (not `NULL`)
- File is created at the given path

**Step 1: Write the failing test**

```python
# tests/test_firefly_export_service.py

import csv
from pathlib import Path
import pytest

EXPECTED_COLUMNS = {
    "type", "date", "amount", "currency_code",
    "description", "source_name", "destination_name",
    "category_name", "tags",
}


def _seed_db(db, account_id="ACC1", bank_id="testbank"):
    db.upsert_account(account_id, "Test Account", bank_id=bank_id)
    db.insert_transaction({
        "source_hash": "h1",
        "date": "2024-01-15",
        "amount": 100.5,
        "currency": "MXN",
        "description": "OXXO STORE",
        "account_id": account_id,
        "canonical_account_id": account_id,
        "bank_id": bank_id,
        "statement_period": "2024-01",
        "category": "Groceries",
        "tags": "merchant:oxxo,period:2024-01",
        "transaction_type": "withdrawal",
        "source_name": account_id,
        "destination_name": "Expenses:Food:Groceries",
        "source_file": "test.csv",
    })


def test_export_column_names(tmp_path):
    from services.db_service import DatabaseService
    from services.firefly_export_service import export_firefly_csv_from_db

    db_path = tmp_path / "test.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    _seed_db(db)

    out_csv = tmp_path / "export.csv"
    count = export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv)

    assert count == 1
    with open(out_csv, newline="") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
    assert EXPECTED_COLUMNS.issubset(cols), f"Missing columns: {EXPECTED_COLUMNS - cols}"


def test_export_amount_formatted(tmp_path):
    from services.db_service import DatabaseService
    from services.firefly_export_service import export_firefly_csv_from_db

    db_path = tmp_path / "test.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    _seed_db(db)

    out_csv = tmp_path / "export.csv"
    export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv)

    with open(out_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["amount"] == "100.50"
    assert rows[0]["currency_code"] == "MXN"
    assert rows[0]["category_name"] == "Groceries"


def test_export_filter_by_bank_id(tmp_path):
    from services.db_service import DatabaseService
    from services.firefly_export_service import export_firefly_csv_from_db

    db_path = tmp_path / "test.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    _seed_db(db, account_id="ACC1", bank_id="bankA")
    _seed_db(db, account_id="ACC2", bank_id="bankB")

    out_csv = tmp_path / "export_a.csv"
    count = export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv, bank_id="bankA")

    assert count == 1
    with open(out_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["source_name"] == "ACC1" for r in rows)


def test_export_empty_db_creates_empty_csv(tmp_path):
    from services.db_service import DatabaseService
    from services.firefly_export_service import export_firefly_csv_from_db

    db_path = tmp_path / "test.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()

    out_csv = tmp_path / "empty.csv"
    count = export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv)
    assert count == 0
    assert out_csv.exists()
```

**Step 2: Run tests to verify they fail**

```bash
cd /root/ledger-smart-converter
pytest tests/test_firefly_export_service.py -v
```

Expected: failures around column names or empty CSV edge case.

---

### Task 2: Harden `export_firefly_csv_from_db`

**Files:**
- Modify: `src/services/firefly_export_service.py`

**Step 1: Read current implementation** — `src/services/firefly_export_service.py`

**Step 2: Replace with hardened version**

```python
from pathlib import Path
from typing import Optional

import pandas as pd

from services.db_service import DatabaseService

# Exact column order expected by Firefly III CSV import
FIREFLY_COLUMNS = [
    "type", "date", "amount", "currency_code",
    "description", "source_name", "destination_name",
    "category_name", "tags",
]


def export_firefly_csv_from_db(
    db_path: Path,
    out_csv: Path,
    bank_id: Optional[str] = None,
    use_normalized_description: bool = False,
) -> int:
    """Export transactions from DB to a Firefly III-compatible CSV.

    Args:
        db_path: Path to the SQLite database.
        out_csv: Destination CSV path (created with parent dirs).
        bank_id: If set, export only transactions for this bank.
        use_normalized_description: Use normalized_description when available.

    Returns:
        Number of rows exported.
    """
    db = DatabaseService(db_path=db_path)
    desc_col = (
        "COALESCE(normalized_description, description)"
        if use_normalized_description
        else "description"
    )
    query = (
        f"SELECT type, date, amount, currency_code, {desc_col} AS description, "
        "source_name, destination_name, category_name, tags, bank_id "
        "FROM firefly_export"
    )
    params: list = []
    if bank_id:
        query += " WHERE bank_id = ?"
        params.append(bank_id)
    query += " ORDER BY date, description"

    rows = db.fetch_all(query, tuple(params))
    df = pd.DataFrame(rows, columns=[
        "type", "date", "amount", "currency_code", "description",
        "source_name", "destination_name", "category_name", "tags", "bank_id",
    ]) if rows else pd.DataFrame(columns=FIREFLY_COLUMNS + ["bank_id"])

    # Drop the internal bank_id column before export
    export_df = df[FIREFLY_COLUMNS]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(out_csv, index=False)
    return len(export_df)
```

**Step 3: Run tests**

```bash
pytest tests/test_firefly_export_service.py -v
```

Expected: `PASSED` (fix any remaining edge cases)

**Step 4: Commit**

```bash
git add src/services/firefly_export_service.py tests/test_firefly_export_service.py
git commit -m "fix(firefly): harden CSV export — correct columns, empty-DB safety, bank_id filter"
```

---

## Epic 2 — Firefly III API Client Foundation

### Task 3: Write failing test for `FireflyApiClient`

**Files:**
- Test: `tests/test_firefly_api_client.py`
- Create: `src/services/firefly_api_client.py`

**Acceptance Criteria:**
- `FireflyApiClient(base_url, token)` can be instantiated
- `post_transaction(txn_dict)` sends a POST to `{base_url}/api/v1/transactions`
- Authorization header is `Bearer {token}`
- On HTTP 422 (validation error) raises `FireflyValidationError` with details
- On HTTP 401 raises `FireflyAuthError`
- All tests run offline (no real HTTP calls — use `responses` or `unittest.mock`)

**Step 1: Write the failing tests**

```python
# tests/test_firefly_api_client.py

import pytest
from unittest.mock import patch, MagicMock


def test_client_instantiation():
    from services.firefly_api_client import FireflyApiClient
    client = FireflyApiClient(base_url="http://firefly.local", token="mytoken")
    assert client.base_url == "http://firefly.local"


def test_post_transaction_sends_correct_headers(tmp_path):
    from services.firefly_api_client import FireflyApiClient

    client = FireflyApiClient(base_url="http://firefly.local", token="secret")
    txn = {
        "type": "withdrawal",
        "date": "2024-01-15",
        "amount": "100.50",
        "currency_code": "MXN",
        "description": "OXXO",
        "source_name": "ACC1",
        "destination_name": "Expenses:Food:Groceries",
        "category_name": "Groceries",
        "tags": "merchant:oxxo",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"id": "42"}}

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = client.post_transaction(txn)

    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer secret"
    assert result["data"]["id"] == "42"


def test_post_transaction_raises_on_401():
    from services.firefly_api_client import FireflyApiClient, FireflyAuthError

    client = FireflyApiClient(base_url="http://firefly.local", token="bad")
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(FireflyAuthError):
            client.post_transaction({"type": "withdrawal"})


def test_post_transaction_raises_on_422():
    from services.firefly_api_client import FireflyApiClient, FireflyValidationError

    client = FireflyApiClient(base_url="http://firefly.local", token="tok")
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "The given data was invalid."}

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(FireflyValidationError) as exc_info:
            client.post_transaction({"type": "withdrawal"})
    assert "invalid" in str(exc_info.value).lower()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_firefly_api_client.py -v
```

Expected: `ModuleNotFoundError` — `firefly_api_client` does not exist.

---

### Task 4: Implement `FireflyApiClient`

**Files:**
- Create: `src/services/firefly_api_client.py`

**Step 1: Write the implementation**

```python
"""Firefly III API client — wraps the v1 REST API for transaction sync."""

from __future__ import annotations

from typing import Any, Dict

import requests


class FireflyAuthError(Exception):
    """Raised when the API returns HTTP 401."""


class FireflyValidationError(Exception):
    """Raised when the API returns HTTP 422 (invalid payload)."""


class FireflyApiClient:
    """Thin client for Firefly III REST API v1.

    Args:
        base_url: Base URL of the Firefly instance, e.g. ``http://firefly.local``
        token: Personal Access Token from Firefly III → Profile → OAuth
    """

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def post_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """POST a single transaction to Firefly III.

        Args:
            txn: Dict with Firefly transaction fields
                 (type, date, amount, currency_code, description, …)

        Returns:
            Parsed JSON response from the API.

        Raises:
            FireflyAuthError: On HTTP 401.
            FireflyValidationError: On HTTP 422.
            requests.HTTPError: On any other non-2xx response.
        """
        url = f"{self.base_url}/api/v1/transactions"
        payload = {"transactions": [txn]}
        response = requests.post(url, json=payload, headers=self._headers())

        if response.status_code == 401:
            raise FireflyAuthError("Invalid Firefly token — check your Personal Access Token.")
        if response.status_code == 422:
            detail = response.json().get("message", "Validation error")
            raise FireflyValidationError(f"Firefly rejected transaction: {detail}")
        response.raise_for_status()
        return response.json()
```

**Step 2: Run tests**

```bash
pytest tests/test_firefly_api_client.py -v
```

Expected: `PASSED`

**Step 3: Commit**

```bash
git add src/services/firefly_api_client.py tests/test_firefly_api_client.py
git commit -m "feat(firefly): add FireflyApiClient with auth/validation error handling"
```

---

### Task 5: Wire API client to settings (opt-in)

**Files:**
- Read: `src/settings.py`

**Acceptance Criteria:**
- `settings.firefly_url` and `settings.firefly_token` read from env vars `FIREFLY_URL` / `FIREFLY_TOKEN`
- Both default to `None` — absence means API sync is skipped
- No breaking change to existing settings

> **Settings API note:** `src/settings.py` exposes a `Settings` dataclass and a
> `load_settings()` factory function — **not** a module-level singleton. Existing
> tests (e.g. `tests/test_settings.py`) all call `load_settings()` directly.
> Do **not** use `importlib.reload` — it will fight with the frozen dataclass and
> is incompatible with the existing test patterns.

**Step 1: Read `src/settings.py` first** to confirm the dataclass + `load_settings()` pattern, then write the failing tests:

```python
def test_firefly_settings_default_to_none(monkeypatch):
    monkeypatch.delenv("FIREFLY_URL", raising=False)
    monkeypatch.delenv("FIREFLY_TOKEN", raising=False)
    from settings import load_settings
    s = load_settings()
    assert s.firefly_url is None
    assert s.firefly_token is None

def test_firefly_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("FIREFLY_URL", "http://my-firefly.local")
    monkeypatch.setenv("FIREFLY_TOKEN", "mytoken123")
    from settings import load_settings
    s = load_settings()
    assert s.firefly_url == "http://my-firefly.local"
    assert s.firefly_token == "mytoken123"
```

**Step 2: Add to `src/settings.py`**

Add to the `Settings` dataclass and the `load_settings()` factory (match the exact pattern used for other optional env vars in that file):

```python
firefly_url: Optional[str] = None
firefly_token: Optional[str] = None
```

In `load_settings()`:

```python
firefly_url=os.getenv("FIREFLY_URL"),
firefly_token=os.getenv("FIREFLY_TOKEN"),
```

**Step 3: Run tests**

```bash
pytest tests/ -k "firefly_settings" -v
```

**Step 4: Update `.env.example`**

Add:

```
# Firefly III API sync (optional — leave blank to use CSV export only)
FIREFLY_URL=
FIREFLY_TOKEN=
```

**Step 5: Commit**

```bash
git add src/settings.py .env.example tests/
git commit -m "feat(firefly): add optional FIREFLY_URL/TOKEN settings for API sync"
```

---

## Definition of Done

- [ ] `export_firefly_csv_from_db` produces correct column names and handles empty DB
- [ ] `FireflyApiClient` implemented, tested offline, raises typed errors
- [ ] `settings.firefly_url` / `settings.firefly_token` wired to env vars
- [ ] `pytest tests/ -m "not slow" -q` exits green
- [ ] `requests` added to `requirements.txt` if not already present
