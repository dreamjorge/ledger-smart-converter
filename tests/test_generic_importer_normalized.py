from pathlib import Path

import yaml

import generic_importer as gi


def _write_rules(tmp_path: Path, bank_id: str) -> Path:
    rules_path = tmp_path / f"rules_{bank_id}.yml"
    cfg = {
        "banks": {
            bank_id: {
                "account_key": "acc",
                "payment_asset_key": "pay",
                "card_tag": f"card:{bank_id}",
                "type": "xlsx",
                "fallback_name": "Liabilities:CC:Test",
                "fallback_asset": "Assets:Test",
            }
        },
        "defaults": {
            "accounts": {},
            "fallback_expense": "Expenses:Other:Uncategorized",
            "currency": "MXN",
        },
        "merchant_aliases": [],
        "rules": [],
    }
    rules_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return rules_path


def test_process_uses_normalized_description_for_classification(tmp_path, monkeypatch):
    importer = gi.GenericImporter(_write_rules(tmp_path, "norm_bank"), "norm_bank")
    txns = [gi.TxnRaw("2026-01-10", "MERPAGO NETFLIX 12345", -100.0, "")]

    captured = {}

    def _classify(desc, *_args, **_kwargs):
        captured["desc"] = desc
        return "Expenses:Entertainment:DigitalServices", [], "netflix"

    monkeypatch.setattr(gi.cu, "classify", _classify)
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")
    monkeypatch.setattr(gi, "validate_tags", lambda _t: [])
    monkeypatch.setattr(gi, "validate_transaction", lambda _c: [])
    monkeypatch.setattr(gi, "resolve_canonical_account_id", lambda *_a, **_k: "cc:norm_bank")

    rows, _, _ = importer.process(txns, strict=False)
    assert len(rows) == 1
    assert captured["desc"] == "MercadoPago Netflix"


def test_process_sets_raw_and_normalized_fields_in_canonical_txn(tmp_path, monkeypatch):
    importer = gi.GenericImporter(_write_rules(tmp_path, "norm_bank"), "norm_bank")
    txns = [gi.TxnRaw("2026-01-10", "MERPAGO NETFLIX 12345", -100.0, "")]
    captured = {}

    def _validate(canonical_txn):
        captured["raw"] = canonical_txn.raw_description
        captured["normalized"] = canonical_txn.normalized_description
        return []

    monkeypatch.setattr(gi, "validate_transaction", _validate)
    monkeypatch.setattr(gi, "validate_tags", lambda _t: [])
    monkeypatch.setattr(gi.cu, "classify", lambda *_a: ("Expenses:Other:Uncategorized", [], "m"))
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")
    monkeypatch.setattr(gi, "resolve_canonical_account_id", lambda *_a, **_k: "cc:norm_bank")

    rows, _, _ = importer.process(txns, strict=False)
    assert len(rows) == 1
    assert captured["raw"] == "MERPAGO NETFLIX 12345"
    assert captured["normalized"] == "MercadoPago Netflix"
