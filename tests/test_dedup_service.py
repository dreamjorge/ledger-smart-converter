from services.db_service import DatabaseService
from services.dedup_service import check_and_insert_batch


def test_check_and_insert_batch_surfaces_duplicates_within_same_batch(tmp_path):
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account(
        "cc:santander_likeu", "Santander LikeU", bank_id="santander_likeu"
    )

    duplicate_rows = [
        {
            "date": "2026-03-15",
            "amount": 99.99,
            "currency": "MXN",
            "description": "Cafe",
            "account_id": "Liabilities:CC:Santander LikeU",
            "canonical_account_id": "cc:santander_likeu",
            "bank_id": "santander_likeu",
            "source_file": "manual",
        },
        {
            "date": "2026-03-15",
            "amount": 99.99,
            "currency": "MXN",
            "description": "Cafe",
            "account_id": "Liabilities:CC:Santander LikeU",
            "canonical_account_id": "cc:santander_likeu",
            "bank_id": "santander_likeu",
            "source_file": "manual",
        },
    ]

    result = check_and_insert_batch(db, duplicate_rows)
    persisted = db.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]

    assert result.inserted == 1
    assert len(result.duplicate_rows) == 1
    assert persisted == 1
