from pathlib import Path

import pandas as pd
import yaml

from generic_importer import GenericImporter


def _write_rules(path: Path) -> None:
    config = {
        "version": 1,
        "banks": {
            "santander_likeu": {
                "display_name": "Santander LikeU (XLSX/PDF)",
                "type": "xlsx",
                "account_key": "credit_card",
                "payment_asset_key": "payment_asset",
                "card_tag": "card:likeu",
                "fallback_name": "Liabilities:CC:Santander LikeU",
                "fallback_asset": "Assets:Santander Debito",
            }
        },
        "defaults": {
            "currency": "MXN",
            "accounts": {
                "credit_card": {"name": "Liabilities:CC:Santander LikeU", "closing_day": 15},
                "payment_asset": "Assets:Santander Debito",
            },
            "fallback_expense": "Expenses:Other:Uncategorized",
        },
        "merchant_aliases": [{"canon": "wal_mart", "any_regex": ["wal\\s*mart"]}],
        "rules": [
            {
                "name": "Groceries",
                "any_regex": ["wal\\s*mart"],
                "set": {"expense": "Expenses:Food:Groceries", "tags": ["bucket:groceries"]},
            }
        ],
    }
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def test_process_is_deterministic_for_same_input(tmp_path: Path):
    rules_path = tmp_path / "rules.yml"
    _write_rules(rules_path)

    csv_path = tmp_path / "input.csv"
    pd.DataFrame(
        [
            {"date": "2026-02-02", "descripcion": "WAL MART ANTEA", "monto": -150.0},
            {"date": "2026-02-01", "descripcion": "PAGO TARJETA", "monto": 500.0},
        ]
    ).to_csv(csv_path, index=False)

    importer = GenericImporter(rules_path, "santander_likeu")

    txns_run_1 = importer.load_data(csv_path, None, False)
    rows_1, unknown_1, warnings_1 = importer.process(txns_run_1)

    txns_run_2 = importer.load_data(csv_path, None, False)
    rows_2, unknown_2, warnings_2 = importer.process(txns_run_2)

    assert rows_1 == rows_2
    assert unknown_1 == unknown_2
    assert warnings_1 == 0
    assert warnings_2 == 0
    assert any("txn:" in row["tags"] for row in rows_1)
