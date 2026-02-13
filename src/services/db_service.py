import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logging_config import get_logger
from settings import load_settings

logger = get_logger("db_service")


class DatabaseService:
    def __init__(self, db_path: Optional[Path] = None, schema_path: Optional[Path] = None):
        settings = load_settings()
        self.db_path = Path(db_path) if db_path else (settings.data_dir / "ledger.db")
        self.schema_path = Path(schema_path) if schema_path else (settings.root_dir / "src" / "database" / "schema.sql")

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
            conn.executescript(sql)
            conn.commit()
        logger.info("initialized sqlite database at %s", self.db_path)

    def fetch_one(self, query: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
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
                (account_id, display_name, account_type, bank_id, closing_day, currency),
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
    ) -> str:
        raw = f"{bank_id}|{source_file}|{date}|{float(amount):.2f}|{(description or '').strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def insert_transaction(self, txn: Dict[str, Any], import_id: Optional[int] = None) -> bool:
        source_hash = txn.get("source_hash") or self.build_source_hash(
            bank_id=txn["bank_id"],
            source_file=txn["source_file"],
            date=txn["date"],
            amount=float(txn["amount"]),
            description=txn.get("description", ""),
        )

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    source_hash, date, amount, currency, merchant, description,
                    account_id, canonical_account_id, bank_id, statement_period,
                    category, tags, source_file, import_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_hash,
                    txn["date"],
                    float(txn["amount"]),
                    txn.get("currency", "MXN"),
                    txn.get("merchant"),
                    txn.get("description", ""),
                    txn["account_id"],
                    txn["canonical_account_id"],
                    txn["bank_id"],
                    txn.get("statement_period"),
                    txn.get("category"),
                    txn.get("tags"),
                    txn["source_file"],
                    import_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0
