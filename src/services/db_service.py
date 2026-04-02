import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logging_config import get_logger
from settings import load_settings

logger = get_logger("db_service")


class DatabaseService:
    def __init__(
        self, db_path: Optional[Path] = None, schema_path: Optional[Path] = None
    ):
        settings = load_settings()
        self.db_path = Path(db_path) if db_path else (settings.data_dir / "ledger.db")
        self.schema_path = (
            Path(schema_path)
            if schema_path
            else (settings.root_dir / "src" / "database" / "schema.sql")
        )

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        sql = self.schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            self._ensure_transactions_columns(conn)
            conn.executescript(sql)
            self._ensure_transactions_columns(conn)
            conn.commit()
        logger.info("initialized sqlite database at %s", self.db_path)

    @staticmethod
    def _ensure_transactions_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(transactions)").fetchall()
        existing = {r["name"] for r in rows}
        if not existing:
            return

        alterations = [
            ("raw_description", "TEXT"),
            ("normalized_description", "TEXT"),
            ("canonical_account_id", "TEXT"),
            ("merchant", "TEXT"),
            ("statement_period", "TEXT"),
            ("category", "TEXT"),
            ("tags", "TEXT"),
            ("transaction_type", "TEXT NOT NULL DEFAULT 'withdrawal'"),
            ("source_name", "TEXT"),
            ("destination_name", "TEXT"),
            ("import_id", "INTEGER"),
            ("updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
            ("user_id", "TEXT"),
        ]
        for col, typ in alterations:
            if col not in existing:
                conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typ}")

    def fetch_one(
        self, query: str, params: Iterable[Any] = ()
    ) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def upsert_account(
        self,
        account_id: str,
        display_name: str,
        account_type: str = "credit_card",
        bank_id: Optional[str] = None,
        closing_day: Optional[int] = None,
        currency: str = "MXN",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO accounts (account_id, display_name, type, bank_id, closing_day, currency)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    type = excluded.type,
                    bank_id = excluded.bank_id,
                    closing_day = excluded.closing_day,
                    currency = excluded.currency
                """,
                (
                    account_id,
                    display_name,
                    account_type,
                    bank_id,
                    closing_day,
                    currency,
                ),
            )
            conn.commit()

    def record_import(
        self,
        bank_id: str,
        source_file: str,
        status: str,
        row_count: int = 0,
        error: Optional[str] = None,
    ) -> int:
        processed_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO imports (bank_id, source_file, processed_at, status, row_count, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bank_id, source_file, processed_at, status, int(row_count), error),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_import_status(
        self,
        import_id: int,
        status: str,
        row_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE imports
                SET status = ?,
                    row_count = COALESCE(?, row_count),
                    error = COALESCE(?, error)
                WHERE import_id = ?
                """,
                (status, row_count, error, import_id),
            )
            conn.commit()

    @staticmethod
    def build_source_hash(
        bank_id: str,
        source_file: str,
        date: str,
        amount: float,
        description: str,
        canonical_account_id: Optional[str] = None,
    ) -> str:
        raw = (
            f"{bank_id}|{canonical_account_id or ''}|{source_file}|{date}|"
            f"{float(amount):.2f}|{(description or '').strip().lower()}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def insert_transaction(
        self,
        txn: Dict[str, Any],
        import_id: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        source_hash = txn.get("source_hash") or self.build_source_hash(
            bank_id=txn["bank_id"],
            source_file=txn["source_file"],
            date=txn["date"],
            amount=float(txn["amount"]),
            description=txn.get("description", ""),
            canonical_account_id=txn.get("canonical_account_id"),
        )
        effective_user_id = user_id or txn.get("user_id")

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    source_hash, date, amount, currency, merchant, description, raw_description, normalized_description,
                    account_id, canonical_account_id, bank_id, statement_period,
                    category, tags, transaction_type, source_name, destination_name, source_file, import_id, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_hash,
                    txn["date"],
                    float(txn["amount"]),
                    txn.get("currency", "MXN"),
                    txn.get("merchant"),
                    txn.get("description", ""),
                    txn.get("raw_description"),
                    txn.get("normalized_description"),
                    txn["account_id"],
                    txn["canonical_account_id"],
                    txn["bank_id"],
                    txn.get("statement_period"),
                    txn.get("category"),
                    txn.get("tags"),
                    txn.get("transaction_type", "withdrawal"),
                    txn.get("source_name", txn.get("account_id")),
                    txn.get("destination_name"),
                    txn["source_file"],
                    import_id,
                    effective_user_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def insert_transactions_batch(
        self,
        txn_rows: List[Dict[str, Any]],
        import_id: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Insert multiple transactions efficiently in a single DB transaction.

        Returns:
            Dict with "inserted" and "skipped" counts.
        """
        inserted = 0
        skipped = 0

        # Prepare parameters for all rows
        params = []
        for txn in txn_rows:
            source_hash = txn.get("source_hash") or self.build_source_hash(
                bank_id=txn["bank_id"],
                source_file=txn["source_file"],
                date=txn["date"],
                amount=float(txn["amount"]),
                description=txn.get("description", ""),
                canonical_account_id=txn.get("canonical_account_id"),
            )
            effective_user_id = user_id or txn.get("user_id")
            params.append(
                (
                    source_hash,
                    txn["date"],
                    float(txn["amount"]),
                    txn.get("currency", "MXN"),
                    txn.get("merchant"),
                    txn.get("description", ""),
                    txn.get("raw_description"),
                    txn.get("normalized_description"),
                    txn["account_id"],
                    txn["canonical_account_id"],
                    txn["bank_id"],
                    txn.get("statement_period"),
                    txn.get("category"),
                    txn.get("tags"),
                    txn.get("transaction_type", "withdrawal"),
                    txn.get("source_name", txn.get("account_id")),
                    txn.get("destination_name"),
                    txn["source_file"],
                    import_id,
                    effective_user_id,
                )
            )

        with self._connect() as conn:
            # We use individual execution inside one transaction to get accurate rowcounts per row
            # Or we could use executemany but we lose individual rowcount feedback.
            # For exact counts of inserted vs skipped with INSERT OR IGNORE, we iterate.
            for p in params:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions (
                        source_hash, date, amount, currency, merchant, description, 
                        raw_description, normalized_description, account_id, 
                        canonical_account_id, bank_id, statement_period,
                        category, tags, transaction_type, source_name, 
                        destination_name, source_file, import_id, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    p,
                )
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            conn.commit()

        return {"inserted": inserted, "skipped": skipped}

    def transaction_exists(self, source_hash: str) -> bool:
        """Return True if a transaction with this source_hash already exists."""
        row = self.fetch_one(
            "SELECT 1 FROM transactions WHERE source_hash = ?", (source_hash,)
        )
        return row is not None

    def upsert_transaction(
        self,
        txn: Dict[str, Any],
        import_id: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Insert or replace a transaction (overwrite mode).
        Preserves the original created_at timestamp if the row already exists.
        Returns True always (the row is guaranteed to exist after this call)."""
        source_hash = txn.get("source_hash") or self.build_source_hash(
            bank_id=txn["bank_id"],
            source_file=txn["source_file"],
            date=txn["date"],
            amount=float(txn["amount"]),
            description=txn.get("description", ""),
            canonical_account_id=txn.get("canonical_account_id"),
        )
        effective_user_id = user_id or txn.get("user_id")
        # Preserve created_at from existing row if present
        existing = self.fetch_one(
            "SELECT created_at FROM transactions WHERE source_hash = ?", (source_hash,)
        )
        created_at = (
            existing["created_at"]
            if existing
            else datetime.now(timezone.utc).isoformat()
        )
        updated_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO transactions (
                    source_hash, date, amount, currency, merchant, description,
                    raw_description, normalized_description, account_id,
                    canonical_account_id, bank_id, statement_period,
                    category, tags, transaction_type, source_name,
                    destination_name, source_file, import_id,
                    user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_hash,
                    txn["date"],
                    float(txn["amount"]),
                    txn.get("currency", "MXN"),
                    txn.get("merchant"),
                    txn.get("description", ""),
                    txn.get("raw_description"),
                    txn.get("normalized_description"),
                    txn["account_id"],
                    txn["canonical_account_id"],
                    txn["bank_id"],
                    txn.get("statement_period"),
                    txn.get("category"),
                    txn.get("tags"),
                    txn.get("transaction_type", "withdrawal"),
                    txn.get("source_name", txn.get("account_id")),
                    txn.get("destination_name"),
                    txn["source_file"],
                    import_id,
                    effective_user_id,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
        return True

    def insert_rule(
        self,
        name: str,
        pattern: str,
        expense: str = "",
        tags: str = "",
        priority: int = 100,
    ) -> bool:
        """Insert a rule row. Uses INSERT OR IGNORE so duplicate patterns are skipped.

        Requires a UNIQUE constraint on ``pattern`` (present in schema.sql for new
        databases).  On legacy databases without the constraint, ``INSERT OR IGNORE``
        has no uniqueness target and may insert duplicates; re-initialize the DB to
        apply the current schema in that case.

        Returns:
            True if inserted (new row), False if skipped (duplicate pattern).
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO rules (name, pattern, expense, tags, priority, enabled) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (name, pattern, expense, tags, priority),
            )
            conn.commit()
            return cursor.rowcount > 0

    def categorization_coverage(self) -> dict:
        """Return categorization coverage stats for withdrawal transactions.

        Returns:
            {"categorized": int, "total": int, "pct": float}
            where pct is 0.0 when total == 0.
        """
        row = self.fetch_one(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN category IS NOT NULL AND category != '' THEN 1 ELSE 0 END) AS categorized
            FROM transactions
            WHERE transaction_type = 'withdrawal'
            """
        )
        total = row["total"] if row and row["total"] else 0
        categorized = row["categorized"] if row and row["categorized"] else 0
        pct = round(categorized / total, 4) if total > 0 else 0.0
        return {"categorized": categorized, "total": total, "pct": pct}

    def backfill_normalized_descriptions(self, normalizer) -> int:
        """Backfill missing normalized_description values for existing rows."""
        updated = 0
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, COALESCE(raw_description, description, '') AS raw_desc
                FROM transactions
                WHERE normalized_description IS NULL OR normalized_description = ''
                """
            ).fetchall()
            for row in rows:
                norm = normalizer(row["raw_desc"])
                conn.execute(
                    "UPDATE transactions SET normalized_description = ? WHERE id = ?",
                    (norm, row["id"]),
                )
                updated += 1
            conn.commit()
        return updated

    def record_audit_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_events (event_type, entity_type, entity_id, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, entity_type, entity_id, payload_json),
            )
            conn.commit()
            return int(cur.lastrowid)
