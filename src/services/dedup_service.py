# -*- coding: utf-8 -*-
"""Deduplication service for batch transaction imports.

Provides two public functions:
- check_and_insert_batch: Insert new rows immediately; return duplicate rows for UI review.
- resolve_duplicates: Apply per-row user decisions (skip / overwrite / keep_both).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from services.contracts import DedupDecision, TransactionInsertRow
from services.db_service import DatabaseService


@dataclass
class DeduplicationResult:
    inserted: int
    duplicate_rows: List[TransactionInsertRow] = field(default_factory=list)
    import_id: Optional[int] = None


def check_and_insert_batch(
    db: DatabaseService,
    txn_rows: List[TransactionInsertRow],
    import_id: Optional[int] = None,
) -> DeduplicationResult:
    """Insert new rows immediately; collect duplicates for user review.

    For each row:
    - Compute source_hash using DatabaseService.build_source_hash.
    - If hash already exists in DB → add to duplicate_rows (do not insert).
    - Otherwise → insert via db.insert_transaction.

    Args:
        db: Initialized DatabaseService instance.
        txn_rows: List of transaction dicts (same schema as insert_transaction expects).
        import_id: Optional import audit trail ID.

    Returns:
        DeduplicationResult with inserted count and list of duplicate row dicts.
        Each duplicate row dict includes a "source_hash" key for UI keying.
    """
    result = DeduplicationResult(inserted=0, import_id=import_id)

    # 1. Pre-calculate hashes
    for row in txn_rows:
        if not row.get("source_hash"):
            row["source_hash"] = db.build_source_hash(
                bank_id=row["bank_id"],
                source_file=row["source_file"],
                date=row["date"],
                amount=float(row["amount"]),
                description=row.get("description", ""),
                canonical_account_id=row.get("canonical_account_id"),
            )

    # 2. Find existing hashes in bulk
    all_hashes = [r["source_hash"] for r in txn_rows]
    existing_hashes = set()

    if all_hashes:
        # SQLite limit for variables in IN clause is 999, so chunk it
        for i in range(0, len(all_hashes), 900):
            chunk = all_hashes[i : i + 900]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"SELECT source_hash FROM transactions WHERE source_hash IN ({placeholders})"
            rows = db.fetch_all(query, tuple(chunk))
            existing_hashes.update(r["source_hash"] for r in rows)

    # 3. Separate duplicates and new rows
    new_rows = []
    seen_new_hashes = set()
    for row in txn_rows:
        h = row["source_hash"]
        if h in existing_hashes:
            result.duplicate_rows.append(row)
        elif h in seen_new_hashes:
            result.duplicate_rows.append(row)
        else:
            seen_new_hashes.add(h)
            new_rows.append(row)

    # 4. Insert new rows in bulk using insert_transactions_batch
    if new_rows:
        batch_res = db.insert_transactions_batch(new_rows, import_id=import_id)
        result.inserted = batch_res.get("inserted", 0)

    return result


def resolve_duplicates(
    db: DatabaseService,
    duplicate_rows: List[TransactionInsertRow],
    decisions: Dict[str, DedupDecision],
    import_id: Optional[int] = None,
) -> Dict[str, int]:
    """Apply per-row user decisions to duplicate transactions.

    Args:
        db: Initialized DatabaseService instance.
        duplicate_rows: List of duplicate row dicts (each must have "source_hash").
        decisions: Mapping of source_hash → decision string.
                   Valid decisions: "skip", "overwrite", "keep_both".
        import_id: Optional import audit trail ID.

    Returns:
        Dict with keys "overwritten", "kept_both", "skipped" and their counts.
    """
    counts = {"overwritten": 0, "kept_both": 0, "skipped": 0}

    for row in duplicate_rows:
        source_hash = row["source_hash"]
        decision = decisions.get(source_hash, "skip")

        if decision == "overwrite":
            db.upsert_transaction(row, import_id=import_id)
            counts["overwritten"] += 1

        elif decision == "keep_both":
            # Find an unused hash by appending _copy_N to source_file
            original_source_file = row.get("source_file", "unknown")
            copy_row = dict(row)
            n = 1
            while True:
                candidate_file = f"{original_source_file}_copy_{n}"
                candidate_hash = db.build_source_hash(
                    bank_id=row["bank_id"],
                    source_file=candidate_file,
                    date=row["date"],
                    amount=float(row["amount"]),
                    description=row.get("description", ""),
                    canonical_account_id=row.get("canonical_account_id"),
                )
                if not db.transaction_exists(candidate_hash):
                    copy_row["source_file"] = candidate_file
                    copy_row["source_hash"] = candidate_hash
                    break
                n += 1
            db.insert_transaction(copy_row, import_id=import_id)
            counts["kept_both"] += 1

        else:  # "skip" or unknown
            counts["skipped"] += 1

    return counts
