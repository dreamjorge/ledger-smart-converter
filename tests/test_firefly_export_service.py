import csv
from pathlib import Path
import pytest

from services.db_service import DatabaseService
from services.firefly_export_service import export_firefly_csv_from_db

EXPECTED_COLUMNS = {
    "type", "date", "amount", "currency_code",
    "description", "source_name", "destination_name",
    "category_name", "tags",
}


def _seed_db(db, account_id="ACC1", bank_id="testbank"):
    db.upsert_account(account_id, "Test Account", bank_id=bank_id)
    db.insert_transaction({
        "source_hash": f"h_{account_id}",
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


def test_export_firefly_csv_from_db(tmp_path):
    """Original test — kept for regression."""
    db_path = tmp_path / "ledger.db"
    out_csv = tmp_path / "export.csv"
    db = DatabaseService(db_path=db_path)
    db.initialize()

    db.upsert_account(
        account_id="cc:santander_likeu",
        display_name="Liabilities:CC:Santander LikeU",
        bank_id="santander_likeu",
        currency="MXN",
    )
    db.insert_transaction(
        {
            "date": "2026-01-15",
            "amount": 120.0,
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
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:Santander LikeU",
            "destination_name": "Expenses:Food:Groceries",
        }
    )

    rows = export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv, bank_id="santander_likeu")
    content = out_csv.read_text(encoding="utf-8")

    assert rows == 1
    assert "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags" in content
    assert "OXXO QRO" in content


def test_export_column_names(tmp_path):
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
    # bank_id must NOT appear in the exported CSV
    assert "bank_id" not in cols, "bank_id should not be exported to Firefly CSV"


def test_export_amount_and_currency(tmp_path):
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
    db_path = tmp_path / "test.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()

    out_csv = tmp_path / "empty.csv"
    count = export_firefly_csv_from_db(db_path=db_path, out_csv=out_csv)
    assert count == 0
    assert out_csv.exists()
    # Even empty export should have a header row
    with open(out_csv, newline="") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
    assert EXPECTED_COLUMNS.issubset(cols), f"Missing columns in empty export: {EXPECTED_COLUMNS - cols}"
