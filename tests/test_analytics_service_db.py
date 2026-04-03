import pandas as pd

from services.analytics_service import (
    calculate_categorization_stats,
    calculate_categorization_stats_from_db,
)
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


def test_calculate_categorization_stats_from_db_returns_empty_stats_for_bank_with_no_rows(
    tmp_path,
):
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

    stats = calculate_categorization_stats_from_db(
        db_path=db_path, bank_id="santander_likeu"
    )
    assert stats["total"] == 0
    assert stats["categorized"] == 0
    assert stats["uncategorized"] == 0
    assert stats["total_spent"] == 0.0
    assert stats["categories"] == {}


def test_calculate_categorization_stats_from_db_matches_csv_like_frame_for_same_transactions(
    tmp_path,
):
    db_path = tmp_path / "ledger.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    db.upsert_account(
        account_id="cc:hsbc",
        display_name="Liabilities:CC:HSBC",
        bank_id="hsbc",
        currency="MXN",
    )

    csv_like_df = pd.DataFrame(
        [
            {
                "type": "withdrawal",
                "amount": "100.0",
                "destination_name": "Expenses:Food",
                "date": "2024-01-15",
            },
            {
                "type": "withdrawal",
                "amount": "200.0",
                "destination_name": "Expenses:Transport",
                "date": "2024-01-20",
            },
        ]
    )

    db.insert_transaction(
        {
            "date": "2024-01-15",
            "amount": 100.0,
            "currency": "MXN",
            "merchant": "merchant:food",
            "description": "FOOD",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": "2024-01",
            "category": None,
            "tags": "period:2024-01",
            "source_file": "data/hsbc/firefly_hsbc.csv",
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:HSBC",
            "destination_name": "Expenses:Food",
        }
    )
    db.insert_transaction(
        {
            "date": "2024-01-20",
            "amount": 200.0,
            "currency": "MXN",
            "merchant": "merchant:transport",
            "description": "TRANSPORT",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": "2024-01",
            "category": None,
            "tags": "period:2024-01",
            "source_file": "data/hsbc/firefly_hsbc.csv",
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:HSBC",
            "destination_name": "Expenses:Transport",
        }
    )

    csv_stats = calculate_categorization_stats(csv_like_df)
    db_stats = calculate_categorization_stats_from_db(db_path=db_path, bank_id="hsbc")

    assert db_stats == csv_stats


def test_calculate_categorization_stats_from_db_matches_csv_filters_when_db_has_invalid_dates(
    tmp_path,
):
    db_path = tmp_path / "ledger.db"
    db = DatabaseService(db_path=db_path)
    db.initialize()
    db.upsert_account(
        account_id="cc:hsbc",
        display_name="Liabilities:CC:HSBC",
        bank_id="hsbc",
        currency="MXN",
    )

    csv_like_df = pd.DataFrame(
        [
            {
                "type": "withdrawal",
                "amount": 100.0,
                "destination_name": "Expenses:Food",
                "date": "2024-01-15",
            },
            {
                "type": "withdrawal",
                "amount": 999.0,
                "destination_name": "Expenses:Ghost",
                "date": "not-a-date",
            },
        ]
    )

    db.insert_transaction(
        {
            "date": "2024-01-15",
            "amount": 100.0,
            "currency": "MXN",
            "merchant": "merchant:food",
            "description": "FOOD",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": "2024-01",
            "category": None,
            "tags": "period:2024-01",
            "source_file": "data/hsbc/firefly_hsbc.csv",
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:HSBC",
            "destination_name": "Expenses:Food",
        }
    )
    db.insert_transaction(
        {
            "date": "not-a-date",
            "amount": 999.0,
            "currency": "MXN",
            "merchant": "merchant:ghost",
            "description": "GHOST",
            "account_id": "Liabilities:CC:HSBC",
            "canonical_account_id": "cc:hsbc",
            "bank_id": "hsbc",
            "statement_period": None,
            "category": None,
            "tags": None,
            "source_file": "data/hsbc/firefly_hsbc.csv",
            "transaction_type": "withdrawal",
            "source_name": "Liabilities:CC:HSBC",
            "destination_name": "Expenses:Ghost",
        }
    )

    start_date = pd.Timestamp("2024-01-01")

    csv_stats = calculate_categorization_stats(
        csv_like_df,
        start_date=start_date,
    )
    db_stats = calculate_categorization_stats_from_db(
        db_path=db_path,
        bank_id="hsbc",
        start_date=start_date,
    )

    assert csv_stats["total"] == 1
    assert db_stats == csv_stats
