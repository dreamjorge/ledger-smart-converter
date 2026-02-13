import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from csv_to_db_migrator import migrate_csvs_to_db
from services.db_service import DatabaseService
from services.firefly_export_service import export_firefly_csv_from_db
from settings import load_settings


def run_db_pipeline(
    db_path: Path,
    data_dir: Path,
    accounts_path: Optional[Path] = None,
    export_dir: Optional[Path] = None,
    banks: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    migration_summary = migrate_csvs_to_db(
        db_path=db_path,
        data_dir=data_dir,
        accounts_path=accounts_path,
    )

    db = DatabaseService(db_path=db_path)
    out_dir = export_dir or data_dir

    if banks:
        bank_list = [b.strip() for b in banks if b and b.strip()]
    else:
        rows = db.fetch_all("SELECT DISTINCT bank_id FROM transactions ORDER BY bank_id")
        bank_list = [r["bank_id"] for r in rows]

    exports: List[Dict[str, object]] = []
    for bank_id in bank_list:
        out_csv = out_dir / bank_id / f"firefly_{bank_id}.csv"
        row_count = export_firefly_csv_from_db(
            db_path=db_path,
            out_csv=out_csv,
            bank_id=bank_id,
        )
        exports.append(
            {
                "bank_id": bank_id,
                "out_csv": str(out_csv),
                "rows_exported": row_count,
            }
        )

    return {
        "migration": migration_summary,
        "exports": exports,
    }


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Run CSV->DB migration + DB->Firefly export pipeline.")
    parser.add_argument("--db", default=str(settings.data_dir / "ledger.db"), help="SQLite DB path")
    parser.add_argument("--data-dir", default=str(settings.data_dir), help="Data directory")
    parser.add_argument("--accounts", default=str(settings.config_dir / "accounts.yml"), help="accounts.yml path")
    parser.add_argument("--export-dir", default=None, help="Directory where exported CSVs are written")
    parser.add_argument("--bank", action="append", default=None, help="Bank ID to export (repeatable)")
    args = parser.parse_args()

    summary = run_db_pipeline(
        db_path=Path(args.db),
        data_dir=Path(args.data_dir),
        accounts_path=Path(args.accounts) if args.accounts else None,
        export_dir=Path(args.export_dir) if args.export_dir else None,
        banks=args.bank,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
