from pathlib import Path

from services.db_service import DatabaseService


def test_initialize_creates_expected_tables(tmp_path):
    db_path = tmp_path / "ledger.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()

    rows = service.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {r["name"] for r in rows}
    assert "accounts" in tables
    assert "imports" in tables
    assert "rules" in tables
    assert "transactions" in tables


def test_insert_transaction_deduplicates_on_source_hash(tmp_path):
    db_path = tmp_path / "ledger.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account(
        account_id="cc:santander_likeu",
        display_name="Santander LikeU",
        account_type="credit_card",
        bank_id="santander_likeu",
        closing_day=15,
        currency="MXN",
    )

    txn = {
        "date": "2026-01-15",
        "amount": 123.45,
        "currency": "MXN",
        "merchant": "merchant:oxxo",
        "description": "OXXO QRO",
        "account_id": "Liabilities:CC:Santander LikeU",
        "canonical_account_id": "cc:santander_likeu",
        "bank_id": "santander_likeu",
        "statement_period": "2026-01",
        "category": "Food",
        "tags": "bucket:groceries,merchant:oxxo,period:2026-01",
        "source_file": "data/santander/firefly_likeu.csv",
    }

    inserted_first = service.insert_transaction(txn)
    inserted_second = service.insert_transaction(txn)
    count = service.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]

    assert inserted_first is True
    assert inserted_second is False
    assert count == 1


def test_build_source_hash_differs_for_different_canonical_accounts():
    first = DatabaseService.build_source_hash(
        bank_id="santander_likeu",
        source_file="manual",
        date="2026-03-15",
        amount=123.45,
        description="Supermercado",
        canonical_account_id="cc:santander_likeu",
    )
    second = DatabaseService.build_source_hash(
        bank_id="santander_likeu",
        source_file="manual",
        date="2026-03-15",
        amount=123.45,
        description="Supermercado",
        canonical_account_id="cash:shared",
    )

    assert first != second


def test_insert_transaction_allows_same_payload_for_different_accounts(tmp_path):
    db_path = tmp_path / "ledger.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account(
        account_id="cc:santander_likeu",
        display_name="Santander LikeU",
        bank_id="santander_likeu",
    )
    service.upsert_account(
        account_id="cash:shared",
        display_name="Shared Cash",
        bank_id="santander_likeu",
        account_type="asset",
    )

    common = {
        "date": "2026-03-15",
        "amount": 123.45,
        "currency": "MXN",
        "description": "Supermercado",
        "bank_id": "santander_likeu",
        "source_file": "manual",
    }

    first = service.insert_transaction(
        {
            **common,
            "account_id": "Liabilities:CC:Santander LikeU",
            "canonical_account_id": "cc:santander_likeu",
        }
    )
    second = service.insert_transaction(
        {
            **common,
            "account_id": "Assets:Cash:Shared",
            "canonical_account_id": "cash:shared",
        }
    )

    count = service.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]

    assert first is True
    assert second is True
    assert count == 2


def test_record_import_and_link_transactions(tmp_path):
    db_path = tmp_path / "ledger.db"
    service = DatabaseService(db_path=db_path)
    service.initialize()
    service.upsert_account(
        account_id="cc:hsbc",
        display_name="HSBC",
        account_type="credit_card",
        bank_id="hsbc",
        closing_day=20,
        currency="MXN",
    )

    import_id = service.record_import(
        bank_id="hsbc",
        source_file="data/hsbc/firefly_hsbc.csv",
        status="success",
        row_count=0,
    )

    inserted = service.insert_transaction(
        {
            "date": "2026-01-20",
            "amount": 200.0,
            "currency": "MXN",
            "merchant": "merchant:netflix",
            "description": "NETFLIX",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": "2026-01",
            "category": "Entertainment",
            "tags": "bucket:subs,merchant:netflix,period:2026-01",
            "source_file": "data/hsbc/firefly_hsbc.csv",
        },
        import_id=import_id,
    )

    row = service.fetch_one(
        "SELECT import_id FROM transactions WHERE description = ?",
        ("NETFLIX",),
    )
    assert inserted is True
    assert row["import_id"] == import_id


def test_record_audit_event(tmp_path):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    event_id = db.record_audit_event(
        event_type="test_event",
        entity_type="transaction",
        entity_id="abc123",
        payload={"key": "value"},
    )
    assert event_id > 0
    row = db.fetch_one("SELECT * FROM audit_events WHERE id = ?", (event_id,))
    assert row["event_type"] == "test_event"
    assert row["entity_id"] == "abc123"


def test_dashboard_metrics_view_exists(tmp_path):
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    rows = db.fetch_all("SELECT * FROM dashboard_metrics")
    assert isinstance(rows, list)  # view exists, returns empty list


def test_ensure_columns_adds_missing_column(tmp_path):
    """Simulates an old DB missing normalized_description and raw_description."""
    import sqlite3
    from services.db_service import DatabaseService

    db_path = tmp_path / "old.db"
    # Create minimal old schema without several newer columns
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE transactions (
        id INTEGER PRIMARY KEY, source_hash TEXT UNIQUE,
        date TEXT, amount REAL, currency TEXT DEFAULT 'MXN',
        description TEXT, account_id TEXT, canonical_account_id TEXT,
        bank_id TEXT, transaction_type TEXT DEFAULT 'withdrawal',
        source_file TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute(
        "CREATE TABLE IF NOT EXISTS accounts (account_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'credit_card', bank_id TEXT, closing_day INTEGER, currency TEXT NOT NULL DEFAULT 'MXN', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS imports (import_id INTEGER PRIMARY KEY AUTOINCREMENT, bank_id TEXT NOT NULL, source_file TEXT NOT NULL, processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL, row_count INTEGER NOT NULL DEFAULT 0, error TEXT)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT, payload_json TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS rules (rule_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, pattern TEXT NOT NULL, expense TEXT, tags TEXT, priority INTEGER NOT NULL DEFAULT 100, enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    con.commit()
    con.close()

    # initialize() must add missing columns without error
    db = DatabaseService(db_path=db_path)
    db.initialize()

    # Verify columns now exist
    con2 = sqlite3.connect(db_path)
    cols = [row[1] for row in con2.execute("PRAGMA table_info(transactions)")]
    con2.close()
    assert "normalized_description" in cols
    assert "raw_description" in cols
    assert "merchant" in cols
    assert "source_name" in cols
    assert "destination_name" in cols
    assert "statement_period" in cols
    assert "tags" in cols
    assert "category" in cols


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
        "currency": "MXN",
        "account_id": "ACC1",
        "canonical_account_id": "ACC1",
        "bank_id": "b1",
        "description": "X",
        "transaction_type": "withdrawal",
        "source_file": "f.csv",
    }
    db.insert_transaction(
        {
            **base,
            "source_hash": "h1",
            "date": "2024-01-01",
            "amount": 10.0,
            "category": "Groceries",
        }
    )
    db.insert_transaction(
        {
            **base,
            "source_hash": "h2",
            "date": "2024-01-02",
            "amount": 20.0,
            "category": None,
        }
    )
    db.insert_transaction(
        {
            **base,
            "source_hash": "h3",
            "date": "2024-01-03",
            "amount": 5.0,
            "category": "",
        }
    )
    result = db.categorization_coverage()
    assert result["total"] == 3
    assert result["categorized"] == 1
    assert abs(result["pct"] - 1 / 3) < 0.01


def test_categorization_coverage_excludes_deposits(tmp_path):
    from services.db_service import DatabaseService

    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    db.upsert_account("ACC1", "Test", bank_id="b1")
    base = {
        "currency": "MXN",
        "account_id": "ACC1",
        "canonical_account_id": "ACC1",
        "bank_id": "b1",
        "description": "X",
        "source_file": "f.csv",
    }
    db.insert_transaction(
        {
            **base,
            "source_hash": "h1",
            "date": "2024-01-01",
            "amount": 10.0,
            "transaction_type": "withdrawal",
            "category": "Groceries",
        }
    )
    db.insert_transaction(
        {
            **base,
            "source_hash": "h2",
            "date": "2024-01-02",
            "amount": 500.0,
            "transaction_type": "deposit",
            "category": None,
        }
    )
    result = db.categorization_coverage()
    assert result["total"] == 1  # deposit excluded
    assert result["categorized"] == 1
    assert result["pct"] == 1.0


def test_dashboard_metrics_aggregates_by_period_and_category(tmp_path):
    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    db.upsert_account("ACC1", "Test Account", bank_id="testbank")
    db.insert_transaction(
        {
            "source_hash": "hash1",
            "date": "2024-01-15",
            "amount": 100.0,
            "currency": "MXN",
            "description": "OXXO",
            "account_id": "ACC1",
            "canonical_account_id": "ACC1",
            "bank_id": "testbank",
            "statement_period": "2024-01",
            "category": "Groceries",
            "transaction_type": "withdrawal",
            "source_file": "test.csv",
        }
    )
    db.insert_transaction(
        {
            "source_hash": "hash2",
            "date": "2024-01-20",
            "amount": 50.0,
            "currency": "MXN",
            "description": "WALMART",
            "account_id": "ACC1",
            "canonical_account_id": "ACC1",
            "bank_id": "testbank",
            "statement_period": "2024-01",
            "category": "Groceries",
            "transaction_type": "withdrawal",
            "source_file": "test.csv",
        }
    )
    rows = db.fetch_all(
        "SELECT * FROM dashboard_metrics WHERE bank_id = ?", ("testbank",)
    )
    assert len(rows) == 1
    assert rows[0]["statement_period"] == "2024-01"
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["tx_count"] == 2
    assert abs(rows[0]["total_amount"] - 150.0) < 0.01


def test_insert_transactions_batch(tmp_path):
    from services.db_service import DatabaseService

    db = DatabaseService(db_path=tmp_path / "test.db")
    db.initialize()
    db.upsert_account("ACC1", "Test", bank_id="testbank")

    txn1 = {
        "date": "2024-01-15",
        "amount": 100.0,
        "currency": "MXN",
        "description": "Txn 1",
        "account_id": "ACC1",
        "canonical_account_id": "ACC1",
        "bank_id": "testbank",
        "source_file": "test.csv",
    }
    txn2 = {
        "date": "2024-01-16",
        "amount": 50.0,
        "currency": "MXN",
        "description": "Txn 2",
        "account_id": "ACC1",
        "canonical_account_id": "ACC1",
        "bank_id": "testbank",
        "source_file": "test.csv",
    }

    # Insert batch of two unique transactions
    res1 = db.insert_transactions_batch([txn1, txn2])
    assert res1["inserted"] == 2
    assert res1["skipped"] == 0

    # Insert batch with one new, one duplicate
    txn3 = {
        "date": "2024-01-17",
        "amount": 25.0,
        "currency": "MXN",
        "description": "Txn 3",
        "account_id": "ACC1",
        "canonical_account_id": "ACC1",
        "bank_id": "testbank",
        "source_file": "test.csv",
    }
    res2 = db.insert_transactions_batch([txn1, txn3])
    # txn1 should be skipped, txn3 should be inserted
    assert res2["inserted"] == 1
    assert res2["skipped"] == 1

    # Total rows in db should be 3
    count = db.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]
    assert count == 3
