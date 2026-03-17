from pathlib import Path

from services.db_service import DatabaseService
from services.firefly_export_service import export_firefly_csv_from_db


def test_export_firefly_csv_from_db(tmp_path):
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
