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
    row = service.fetch_one(
        "SELECT raw_description, normalized_description FROM transactions WHERE description = ?",
        ("OXXO QRO",),
    )
    assert row["raw_description"] == "OXXO QRO"
    assert row["normalized_description"] == "Oxxo Qro"


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


def test_migrate_backfills_missing_normalized_description(tmp_path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"

    _write_firefly_csv(
        data_dir / "hsbc" / "firefly_hsbc.csv",
        [
            'withdrawal,2026-01-20,200.00,MXN,MERPAGO NETFLIX 12345,Liabilities:CC:HSBC,Expenses:Entertainment:DigitalServices,Entertainment,"bucket:subs,merchant:netflix,period:2026-01"',
        ],
    )
    migr.migrate_csvs_to_db(db_path=db_path, data_dir=data_dir)

    service = DatabaseService(db_path=db_path)
    # Simulate older row without normalized text
    with service._connect() as conn:
        conn.execute("UPDATE transactions SET normalized_description = ''")
        conn.commit()

    summary = migr.migrate_csvs_to_db(db_path=db_path, data_dir=data_dir)
    assert summary["rows_inserted"] == 0
    row = service.fetch_one("SELECT normalized_description FROM transactions LIMIT 1")
    assert row["normalized_description"] == "MercadoPago Netflix"


def test_discover_firefly_csvs_skips_generated_shadow_when_preferred_exists(tmp_path):
    data_dir = tmp_path / "data"
    sant = data_dir / "santander"
    sant.mkdir(parents=True, exist_ok=True)
    (sant / "firefly_likeu.csv").write_text("x", encoding="utf-8")
    (sant / "firefly_santander.csv").write_text("x", encoding="utf-8")

    found = migr.discover_firefly_csvs(data_dir)
    names = [p.name for p in found]
    assert "firefly_likeu.csv" in names
    assert "firefly_santander.csv" not in names


def test_discover_firefly_csvs_keeps_generated_when_no_preferred_exists(tmp_path):
    data_dir = tmp_path / "data"
    bank = data_dir / "nubank"
    bank.mkdir(parents=True, exist_ok=True)
    (bank / "firefly_nubank.csv").write_text("x", encoding="utf-8")

    found = migr.discover_firefly_csvs(data_dir)
    names = [p.name for p in found]
    assert names == ["firefly_nubank.csv"]
