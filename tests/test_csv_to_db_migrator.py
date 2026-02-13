from pathlib import Path

import csv_to_db_migrator as migr
from services.db_service import DatabaseService


def _write_firefly_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags\n"
    body = "\n".join(rows) + "\n"
    path.write_text(header + body, encoding="utf-8")


def test_migrate_csvs_to_db(tmp_path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    accounts_path = tmp_path / "accounts.yml"

    accounts_path.write_text(
        """
version: 1
canonical_accounts:
  cc:santander_likeu:
    bank_ids: [santander_likeu, santander]
    account_ids: ["Liabilities:CC:Santander LikeU"]
  cc:hsbc:
    bank_ids: [hsbc]
    account_ids: ["Liabilities:CC:HSBC"]
""".strip(),
        encoding="utf-8",
    )

    _write_firefly_csv(
        data_dir / "santander" / "firefly_likeu.csv",
        [
            'withdrawal,2026-01-15,100.00,MXN,OXXO QRO,Liabilities:CC:Santander LikeU,Expenses:Food:Groceries,Food,"bucket:groceries,merchant:oxxo,period:2026-01"',
        ],
    )
    _write_firefly_csv(
        data_dir / "hsbc" / "firefly_hsbc.csv",
        [
            'withdrawal,2026-01-20,200.00,MXN,NETFLIX,Liabilities:CC:HSBC,Expenses:Entertainment:DigitalServices,Entertainment,"bucket:subs,merchant:netflix,period:2026-01"',
        ],
    )

    summary = migr.migrate_csvs_to_db(
        db_path=db_path,
        data_dir=data_dir,
        accounts_path=accounts_path,
    )
    assert summary["files_processed"] == 2
    assert summary["rows_inserted"] == 2

    service = DatabaseService(db_path=db_path)
    tx_count = service.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]
    accounts_count = service.fetch_one("SELECT COUNT(*) AS c FROM accounts")["c"]
    assert tx_count == 2
    assert accounts_count == 2

    canonical_ids = {
        r["canonical_account_id"]
        for r in service.fetch_all("SELECT canonical_account_id FROM transactions")
    }
    assert canonical_ids == {"cc:santander_likeu", "cc:hsbc"}


def test_migrate_is_idempotent_for_transactions(tmp_path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"

    _write_firefly_csv(
        data_dir / "santander_likeu" / "firefly_santander_likeu.csv",
        [
            'withdrawal,2026-01-15,100.00,MXN,OXXO QRO,Liabilities:CC:Santander LikeU,Expenses:Food:Groceries,Food,"bucket:groceries,merchant:oxxo,period:2026-01"',
        ],
    )

    first = migr.migrate_csvs_to_db(db_path=db_path, data_dir=data_dir)
    second = migr.migrate_csvs_to_db(db_path=db_path, data_dir=data_dir)

    assert first["rows_inserted"] == 1
    assert second["rows_inserted"] == 0

    service = DatabaseService(db_path=db_path)
    tx_count = service.fetch_one("SELECT COUNT(*) AS c FROM transactions")["c"]
    assert tx_count == 1
