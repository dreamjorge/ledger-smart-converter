from typing import Dict, List, get_type_hints

import pytest

from services.contracts import DedupDecision, TransactionInsertRow
from services.db_service import DatabaseService
from services.dedup_service import (
    DeduplicationResult,
    check_and_insert_batch,
    resolve_duplicates,
)


def _make_row(
    bank_id="santander_likeu",
    source_file="test.csv",
    date="2026-03-15",
    amount=99.99,
    description="Cafe",
    canonical_account_id="cc:santander_likeu",
):
    return {
        "date": date,
        "amount": amount,
        "currency": "MXN",
        "description": description,
        "account_id": "Liabilities:CC:Santander LikeU",
        "canonical_account_id": canonical_account_id,
        "bank_id": bank_id,
        "source_file": source_file,
    }


def test_check_and_insert_batch_empty_list(tmp_path):
    """Empty input returns zero inserted and no duplicates."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    result = check_and_insert_batch(db, [])
    assert result.inserted == 0
    assert result.duplicate_rows == []


def test_check_and_insert_batch_all_new_rows(tmp_path):
    """When no hashes exist in DB, all rows are inserted."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    rows = [_make_row(source_file="a.csv"), _make_row(source_file="b.csv")]
    result = check_and_insert_batch(db, rows)

    assert result.inserted == 2
    assert result.duplicate_rows == []
    persisted = db.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]
    assert persisted == 2


def test_check_and_insert_batch_all_duplicates(tmp_path):
    """When all hashes already exist, nothing is inserted."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    row = _make_row()
    db.upsert_transaction(row)
    result = check_and_insert_batch(db, [row])

    assert result.inserted == 0
    assert len(result.duplicate_rows) == 1


def test_check_and_insert_batch_mixed_duplicates_and_new(tmp_path):
    """Only new rows are inserted; duplicates are collected for review."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    existing = _make_row(source_file="existing.csv")
    db.upsert_transaction(existing)

    rows = [existing, _make_row(source_file="new.csv")]
    result = check_and_insert_batch(db, rows)

    assert result.inserted == 1
    assert len(result.duplicate_rows) == 1
    assert result.duplicate_rows[0]["source_file"] == "existing.csv"


def test_check_and_insert_batch_within_batch_duplicate(tmp_path):
    """A duplicate within the same batch is surfaced, not double-inserted."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    rows = [_make_row(source_file="dup.csv"), _make_row(source_file="dup.csv")]
    result = check_and_insert_batch(db, rows)

    assert result.inserted == 1
    assert len(result.duplicate_rows) == 1


def test_check_and_insert_batch_respects_import_id(tmp_path):
    """When import_id is provided, it is returned in the result."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    # First insert a row so check_and_insert_batch computes source_hash on the duplicate
    first_row = _make_row(source_file="first.csv")
    db.upsert_transaction(first_row)

    result = check_and_insert_batch(
        db, [_make_row(source_file="first.csv")], import_id=42
    )
    assert result.import_id == 42


def test_resolve_duplicates_skip(tmp_path):
    """skip decision does not insert and returns skipped count."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    # Pre-insert a row then surface it as duplicate via check_and_insert_batch
    db.upsert_transaction(_make_row(source_file="dup.csv"))

    dup_result = check_and_insert_batch(db, [_make_row(source_file="dup.csv")])
    assert len(dup_result.duplicate_rows) == 1

    counts = resolve_duplicates(db, dup_result.duplicate_rows, {"": "skip"})
    assert counts["skipped"] == 1


def test_resolve_duplicates_overwrite(tmp_path):
    """overwrite decision upserts and returns overwritten count."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    # Pre-compute source_hash so check_and_insert_batch recognizes the pre-existing row
    base_row = _make_row(source_file="orig.csv", description="Original")
    base_row["source_hash"] = db.build_source_hash(
        bank_id=base_row["bank_id"],
        source_file=base_row["source_file"],
        date=base_row["date"],
        amount=float(base_row["amount"]),
        description=base_row["description"],
        canonical_account_id=base_row["canonical_account_id"],
    )
    db.upsert_transaction(base_row)

    # Check with identical row (same source_file=orig.csv, same description="Original")
    dup_result = check_and_insert_batch(
        db, [_make_row(source_file="orig.csv", description="Original")]
    )
    dup_row = dup_result.duplicate_rows[0]

    dup_row["description"] = "Updated"
    counts = resolve_duplicates(db, [dup_row], {dup_row["source_hash"]: "overwrite"})

    assert counts["overwritten"] == 1
    assert (
        db.fetch_one("SELECT description FROM transactions")["description"] == "Updated"
    )


def test_resolve_duplicates_keep_both(tmp_path):
    """keep_both creates a new row with modified source_file and returns kept_both count."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    db.upsert_transaction(_make_row(source_file="dup.csv"))

    dup_result = check_and_insert_batch(db, [_make_row(source_file="dup.csv")])
    dup_row = dup_result.duplicate_rows[0]

    counts = resolve_duplicates(db, [dup_row], {dup_row["source_hash"]: "keep_both"})

    assert counts["kept_both"] == 1
    all_rows = db.fetch_all("SELECT source_file FROM transactions")
    files = {r["source_file"] for r in all_rows}
    assert len(files) == 2


def test_resolve_duplicates_unknown_decision_defaults_to_skip(tmp_path):
    """Unknown decision string falls back to skip."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    db.upsert_transaction(_make_row(source_file="dup.csv"))

    dup_result = check_and_insert_batch(db, [_make_row(source_file="dup.csv")])
    dup_row = dup_result.duplicate_rows[0]

    counts = resolve_duplicates(db, [dup_row], {dup_row["source_hash"]: "garbage"})
    assert counts["skipped"] == 1


def test_resolve_duplicates_missing_decision_defaults_to_skip(tmp_path):
    """Missing source_hash in decisions dict falls back to skip."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    db.upsert_transaction(_make_row(source_file="dup.csv"))

    dup_result = check_and_insert_batch(db, [_make_row(source_file="dup.csv")])

    counts = resolve_duplicates(db, dup_result.duplicate_rows, {})  # empty decisions
    assert counts["skipped"] == 1


def test_resolve_duplicates_multiple_rows_mixed_decisions(tmp_path):
    """Multiple rows with different decisions are handled independently."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    # Pre-insert both rows
    db.upsert_transaction(_make_row(source_file="a.csv"))
    db.upsert_transaction(_make_row(source_file="b.csv"))

    dup_result = check_and_insert_batch(
        db,
        [_make_row(source_file="a.csv"), _make_row(source_file="b.csv")],
    )
    dup_rows = dup_result.duplicate_rows

    decisions = {
        dup_rows[0]["source_hash"]: "skip",
        dup_rows[1]["source_hash"]: "keep_both",
    }
    counts = resolve_duplicates(db, dup_rows, decisions)

    assert counts["skipped"] == 1
    assert counts["kept_both"] == 1


def test_resolve_duplicates_keeps_both_iterates_until_free_hash(tmp_path):
    """keep_both finds first available _copy_N suffix."""
    db = DatabaseService(db_path=tmp_path / "ledger.db")
    db.initialize()
    db.upsert_account("cc:santander_likeu", "Santander", bank_id="santander_likeu")

    # Pre-populate manual, manual_copy_1, manual_copy_2
    base = _make_row(source_file="manual")
    db.upsert_transaction(base)

    copy1 = dict(base)
    copy1["source_file"] = "manual_copy_1"
    db.upsert_transaction(copy1)

    copy2 = dict(base)
    copy2["source_file"] = "manual_copy_2"
    db.upsert_transaction(copy2)

    # next keep_both should land on copy_3
    dup_result = check_and_insert_batch(db, [base])
    dup_row = dup_result.duplicate_rows[0]

    counts = resolve_duplicates(db, [dup_row], {dup_row["source_hash"]: "keep_both"})
    assert counts["kept_both"] == 1

    all_files = {
        r["source_file"] for r in db.fetch_all("SELECT source_file FROM transactions")
    }
    assert "manual_copy_3" in all_files


def test_check_and_insert_batch_surfaces_duplicates_within_same_batch(tmp_path):
    """Original regression test: duplicate in same batch surfaces for review."""
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
    """DedupDecision and TransactionInsertRow contracts are used correctly."""
    check_hints = get_type_hints(check_and_insert_batch)
    resolve_hints = get_type_hints(resolve_duplicates)
    result_hints = get_type_hints(DeduplicationResult)

    assert check_hints["txn_rows"] == List[TransactionInsertRow]
    assert resolve_hints["duplicate_rows"] == List[TransactionInsertRow]
    assert resolve_hints["decisions"] == Dict[str, DedupDecision]
    assert result_hints["duplicate_rows"] == List[TransactionInsertRow]
