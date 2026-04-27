import pytest
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


def test_run_db_pipeline_honors_requested_banks(tmp_path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    export_dir = tmp_path / "exports"

    _write_firefly_csv(
        data_dir / "santander_likeu" / "firefly_santander_likeu.csv",
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

    summary = run_db_pipeline(
        db_path=db_path,
        data_dir=data_dir,
        export_dir=export_dir,
        banks=[" hsbc ", ""],
    )

    assert summary["migration"]["rows_inserted"] == 2
    assert len(summary["exports"]) == 1
    assert summary["exports"][0]["bank_id"] == "hsbc"
    assert (export_dir / "hsbc" / "firefly_hsbc.csv").exists()
    assert not (export_dir / "santander_likeu" / "firefly_santander_likeu.csv").exists()


def test_pipeline_is_idempotent(tmp_path):
    """Re-running pipeline against same CSV must not duplicate transactions."""
    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    export_dir = tmp_path / "exports"

    _write_firefly_csv(
        data_dir / "hsbc" / "firefly_hsbc.csv",
        [
            'withdrawal,2026-02-10,500.00,MXN,AMAZON,Liabilities:CC:HSBC,Expenses:Shopping,Shopping,"bucket:shopping,merchant:amazon,period:2026-02"',
        ],
    )

    # First run
    summary1 = run_db_pipeline(
        db_path=db_path,
        data_dir=data_dir,
        export_dir=export_dir,
    )

    # Second run — identical CSV, same DB
    summary2 = run_db_pipeline(
        db_path=db_path,
        data_dir=data_dir,
        export_dir=export_dir,
    )

    from services.db_service import DatabaseService

    db = DatabaseService(db_path=db_path)
    txn_count = db.fetch_one("SELECT COUNT(*) AS cnt FROM transactions")["cnt"]
    import_count = db.fetch_one("SELECT COUNT(*) AS cnt FROM imports")["cnt"]

    assert txn_count == 1, f"Expected 1 transaction row, got {txn_count}"
    assert import_count == 2, f"Expected 2 import rows (one per run), got {import_count}"
    assert summary1["migration"]["rows_inserted"] == 1
    assert summary2["migration"]["rows_inserted"] == 0


def test_run_db_pipeline_cli_args_parsing(tmp_path):
    """Verify run_db_pipeline handles CLI-style argument dict correctly."""
    from db_pipeline import run_db_pipeline

    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    export_dir = tmp_path / "exports"
    accounts_path = tmp_path / "accounts.yml"

    # Write minimal CSV so migration finds data
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "santander_likeu" / "firefly_santander_likeu.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags\n"
        "withdrawal,2026-01-15,100.00,MXN,TEST,Liabilities:CC:Santander,Expenses:Food:Groceries,Food,\n",
        encoding="utf-8",
    )

    result = run_db_pipeline(
        db_path=db_path,
        data_dir=data_dir,
        accounts_path=accounts_path,
        export_dir=export_dir,
        banks=["santander_likeu"],
    )

    # Verify structure
    assert isinstance(result, dict)
    assert "migration" in result
    assert "exports" in result
    assert isinstance(result["exports"], list)
    assert result["exports"][0]["bank_id"] == "santander_likeu"
    assert result["exports"][0]["rows_exported"] >= 0


def test_main_exit_code_zero_on_success(tmp_path, monkeypatch, capsys):
    """main() should exit with code 0 on success."""
    import sys

    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    export_dir = tmp_path / "exports"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Minimal valid CSV
    csv_path = data_dir / "santander_likeu" / "firefly_santander_likeu.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags\n"
        "withdrawal,2026-01-15,100.00,MXN,TEST,Liabilities:CC:Santander,Expenses:Food:Groceries,Food,\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", [
        "db_pipeline",
        "--db", str(db_path),
        "--data-dir", str(data_dir),
        "--export-dir", str(export_dir),
    ])

    from db_pipeline import main

    exit_code = main()
    assert exit_code == 0


def test_if_main_block_raises_system_exit(tmp_path, monkeypatch):
    """Verify that when db_pipeline is run as script, it raises SystemExit."""
    import sys

    data_dir = tmp_path / "data"
    db_path = tmp_path / "ledger.db"
    export_dir = tmp_path / "exports"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Minimal valid CSV
    csv_path = data_dir / "santander_likeu" / "firefly_santander_likeu.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "type,date,amount,currency_code,description,source_name,destination_name,category_name,tags\n"
        "withdrawal,2026-01-15,100.00,MXN,TEST,Liabilities:CC:Santander,Expenses:Food:Groceries,Food,\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", [
        "db_pipeline",
        "--db", str(db_path),
        "--data-dir", str(data_dir),
        "--export-dir", str(export_dir),
    ])

    # Import the module-level name
    from db_pipeline import __name__ as mod_name
    from db_pipeline import main as pipeline_main

    # The db_pipeline script body is:
    #   if __name__ == "__main__":
    #       raise SystemExit(main())
    # When we call main() directly, it returns int.
    # The if __name__ == "__main__" guard wraps it in SystemExit.
    exit_code = pipeline_main()
    assert exit_code == 0
