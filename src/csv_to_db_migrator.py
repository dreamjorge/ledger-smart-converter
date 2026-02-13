import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yaml

from account_mapping import resolve_canonical_account_id
from description_normalizer import normalize_description
from logging_config import get_logger
from services.db_service import DatabaseService
from settings import load_settings

logger = get_logger("csv_to_db_migrator")

PERIOD_RX = re.compile(r"\bperiod:(\d{4}-\d{2})\b", re.IGNORECASE)
MERCHANT_RX = re.compile(r"\bmerchant:([a-z0-9_]+)\b", re.IGNORECASE)


def discover_firefly_csvs(data_dir: Path) -> List[Path]:
    return sorted([p for p in data_dir.glob("**/firefly*.csv") if p.is_file()])


def _infer_bank_id_from_csv(csv_path: Path, data_dir: Path) -> str:
    rel = csv_path.relative_to(data_dir)
    parts = rel.parts
    if parts:
        return parts[0]
    return "unknown"


def _extract_period(tags: str) -> Optional[str]:
    if not tags:
        return None
    m = PERIOD_RX.search(tags)
    return m.group(1) if m else None


def _extract_merchant(tags: str) -> Optional[str]:
    if not tags:
        return None
    m = MERCHANT_RX.search(tags)
    if not m:
        return None
    return f"merchant:{m.group(1)}"


def _load_accounts_catalog(accounts_path: Optional[Path]) -> Dict[str, Dict]:
    if not accounts_path or not accounts_path.exists():
        return {}
    cfg = yaml.safe_load(accounts_path.read_text(encoding="utf-8")) or {}
    return cfg.get("canonical_accounts", {}) or {}


def _seed_accounts(db: DatabaseService, accounts_catalog: Dict[str, Dict]) -> None:
    for canonical_id, entry in accounts_catalog.items():
        bank_ids = entry.get("bank_ids", []) or []
        db.upsert_account(
            account_id=canonical_id,
            display_name=entry.get("display_name", canonical_id),
            account_type=entry.get("type", "credit_card"),
            bank_id=bank_ids[0] if bank_ids else None,
            closing_day=entry.get("closing_day"),
            currency=entry.get("currency", "MXN"),
        )


def migrate_csvs_to_db(
    db_path: Path,
    data_dir: Path,
    accounts_path: Optional[Path] = None,
    csv_paths: Optional[Iterable[Path]] = None,
) -> Dict[str, int]:
    db = DatabaseService(db_path=db_path)
    db.initialize()

    accounts_catalog = _load_accounts_catalog(accounts_path)
    _seed_accounts(db, accounts_catalog)

    files = [Path(p) for p in (csv_paths or discover_firefly_csvs(data_dir))]
    rows_inserted = 0
    rows_seen = 0
    files_processed = 0

    for csv_path in files:
        if not csv_path.exists():
            logger.warning("skipping missing csv: %s", csv_path)
            continue

        bank_id = _infer_bank_id_from_csv(csv_path, data_dir)
        import_id = db.record_import(
            bank_id=bank_id,
            source_file=str(csv_path),
            status="started",
            row_count=0,
        )

        try:
            frame = pd.read_csv(csv_path)
            inserted_for_file = 0
            for _, row in frame.iterrows():
                rows_seen += 1
                source_name = str(row.get("source_name", "")).strip()
                canonical_id = resolve_canonical_account_id(
                    bank_id=bank_id,
                    account_id=source_name,
                    accounts_path=accounts_path,
                )
                db.upsert_account(
                    account_id=canonical_id,
                    display_name=source_name or canonical_id,
                    account_type="credit_card",
                    bank_id=bank_id,
                    currency=str(row.get("currency_code", "MXN") or "MXN"),
                )
                tags = str(row.get("tags", "") or "")
                raw_description = str(row.get("description", "")).strip()
                normalized_description = normalize_description(raw_description, bank_id=bank_id)
                txn = {
                    "date": str(row.get("date", "")).strip(),
                    "amount": float(row.get("amount", 0.0)),
                    "currency": str(row.get("currency_code", "MXN") or "MXN"),
                    "merchant": _extract_merchant(tags),
                    "description": raw_description,
                    "raw_description": raw_description,
                    "normalized_description": normalized_description,
                    "account_id": source_name,
                    "canonical_account_id": canonical_id,
                    "bank_id": bank_id,
                    "statement_period": _extract_period(tags),
                    "category": str(row.get("category_name", "")).strip() or None,
                    "tags": tags or None,
                    "transaction_type": str(row.get("type", "withdrawal") or "withdrawal"),
                    "source_name": source_name,
                    "destination_name": str(row.get("destination_name", "")).strip() or None,
                    "source_file": str(csv_path),
                }
                if db.insert_transaction(txn, import_id=import_id):
                    rows_inserted += 1
                    inserted_for_file += 1

            db.update_import_status(import_id=import_id, status="success", row_count=inserted_for_file)
            files_processed += 1
        except Exception as exc:
            db.update_import_status(import_id=import_id, status="failed", error=str(exc))
            logger.error("failed migrating %s: %s", csv_path, exc)
    backfilled_rows = db.backfill_normalized_descriptions(
        lambda raw: normalize_description(raw)
    )

    summary = {
        "files_processed": files_processed,
        "rows_seen": rows_seen,
        "rows_inserted": rows_inserted,
        "rows_backfilled": backfilled_rows,
    }
    logger.info("migration summary: %s", summary)
    return summary


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Migrate Firefly CSV files into SQLite.")
    parser.add_argument("--db", default=str(settings.data_dir / "ledger.db"), help="SQLite DB path")
    parser.add_argument("--data-dir", default=str(settings.data_dir), help="Data directory with firefly CSV files")
    parser.add_argument("--accounts", default=str(settings.config_dir / "accounts.yml"), help="accounts.yml path")
    parser.add_argument("--csv", action="append", default=None, help="Specific CSV path (repeatable)")
    args = parser.parse_args()

    csv_paths = [Path(p) for p in args.csv] if args.csv else None
    migrate_csvs_to_db(
        db_path=Path(args.db),
        data_dir=Path(args.data_dir),
        accounts_path=Path(args.accounts) if args.accounts else None,
        csv_paths=csv_paths,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
