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
