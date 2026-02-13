from pathlib import Path

from db_pipeline import run_db_pipeline


def _write_firefly_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags\n"
    body = "\n".join(rows) + "\n"
    path.write_text(header + body, encoding="utf-8")


def test_run_db_pipeline_migrates_and_exports(tmp_path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    accounts_path = tmp_path / "accounts.yml"
    export_dir = tmp_path / "exports"

    accounts_path.write_text(
        """
version: 1
canonical_accounts:
  cc:santander_likeu:
    bank_ids: [santander_likeu]
    account_ids: ["Liabilities:CC:Santander LikeU"]
""".strip(),
        encoding="utf-8",
    )

    _write_firefly_csv(
        data_dir / "santander_likeu" / "firefly_santander_likeu.csv",
        [
            'withdrawal,2026-01-15,100.00,MXN,OXXO QRO,Liabilities:CC:Santander LikeU,Expenses:Food:Groceries,Food,"bucket:groceries,merchant:oxxo,period:2026-01"',
        ],
    )

    summary = run_db_pipeline(
        db_path=db_path,
        data_dir=data_dir,
        accounts_path=accounts_path,
        export_dir=export_dir,
    )

    assert summary["migration"]["rows_inserted"] == 1
    assert len(summary["exports"]) == 1
    assert summary["exports"][0]["bank_id"] == "santander_likeu"
    exported = export_dir / "santander_likeu" / "firefly_santander_likeu.csv"
    assert exported.exists()
    assert "OXXO QRO" in exported.read_text(encoding="utf-8")
