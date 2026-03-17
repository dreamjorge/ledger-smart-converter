from pathlib import Path

from services.analytics_service import calculate_categorization_stats_from_db
from services.db_service import DatabaseService


def test_calculate_categorization_stats_from_db(tmp_path):
    db_path = tmp_path / "ledger.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    db.upsert_account(
        account_id="cc:hsbc",
        display_name="Liabilities:CC:HSBC",
        bank_id="hsbc",
        currency="MXN",
    )

    db.insert_transaction(
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
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:HSBC",
            "destination_name": "Expenses:Entertainment:DigitalServices",
        }
    )
    db.insert_transaction(
        {
            "date": "2026-01-21",
            "amount": 500.0,
            "currency": "MXN",
            "merchant": "merchant:pago",
            "description": "PAGO TARJETA",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": "2026-01",
            "category": None,
            "tags": "period:2026-01,pago",
            "source_file": "data/hsbc/firefly_hsbc.csv",
            "transaction_type": "transfer",
            "source_name": "Assets:HSBC Debito",
            "destination_name": "Liabilities:CC:HSBC",
        }
    )

    stats = calculate_categorization_stats_from_db(db_path=db_path, bank_id="hsbc")
    assert stats["total"] == 2
    assert stats["categorized"] == 2
    assert stats["uncategorized"] == 0
    assert stats["total_spent"] == 200.0
    assert stats["categories"]["Entertainment"] == 1
