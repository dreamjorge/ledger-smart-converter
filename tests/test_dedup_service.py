from typing import List, get_type_hints

from services.contracts import DedupDecision, TransactionInsertRow
from services.db_service import DatabaseService
from services.dedup_service import (
    DeduplicationResult,
    check_and_insert_batch,
    resolve_duplicates,
)


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


def test_dedup_service_uses_shared_contract_annotations():
    check_hints = get_type_hints(check_and_insert_batch)
    resolve_hints = get_type_hints(resolve_duplicates)
    result_hints = get_type_hints(DeduplicationResult)

    assert check_hints["txn_rows"] == List[TransactionInsertRow]
    assert resolve_hints["duplicate_rows"] == List[TransactionInsertRow]
    assert resolve_hints["decisions"] == dict[str, DedupDecision]
    assert result_hints["duplicate_rows"] == List[TransactionInsertRow]
