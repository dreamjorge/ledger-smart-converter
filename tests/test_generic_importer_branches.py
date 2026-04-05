from pathlib import Path

import pandas as pd
import pytest
import yaml
from unittest.mock import Mock

import generic_importer as gi
from errors import ValidationError


def _write_rules(tmp_path: Path, bank_id: str, bank_type: str = "xlsx") -> Path:
    rules_path = tmp_path / f"rules_{bank_id}.yml"
    cfg = {
        "banks": {
            bank_id: {
                "account_key": "acc",
                "payment_asset_key": "pay",
                "card_tag": f"card:{bank_id}",
                "type": bank_type,
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


def test_load_data_pdf_source_branch(tmp_path, monkeypatch):
    importer = gi.GenericImporter(
        _write_rules(tmp_path, "test_pdf", "xlsx"), "test_pdf"
    )

    mock_parser = Mock()
    mock_parser.parse.return_value = [gi.TxnRaw("2026-01-12", "A", -10.0, source="pdf")]

    mock_factory = Mock(return_value=mock_parser)
    monkeypatch.setattr("generic_importer.ParserFactory.get_parser", mock_factory)

    txns = importer.load_data(None, Path("dummy.pdf"), True)

    assert len(txns) == 1
    assert txns[0].source == "pdf"
    mock_factory.assert_called_once_with(
        "xlsx", bank_id="test_pdf", use_pdf_source=True
    )
    mock_parser.parse.assert_called_once_with(Path("dummy.pdf"))


def test_load_data_dispatches_factory(tmp_path, monkeypatch):
    xml_importer = gi.GenericImporter(
        _write_rules(tmp_path, "test_xml", "xml"), "test_xml"
    )
    xlsx_importer = gi.GenericImporter(
        _write_rules(tmp_path, "test_xlsx", "xlsx"), "test_xlsx"
    )

    # Mock the parser factory
    mock_parser = Mock()

    calls = []

    def get_parser_side_effect(bank_type, bank_id="", use_pdf_source=False):
        calls.append((bank_type, bank_id, use_pdf_source))
        if bank_type == "xml":
            mock_parser.parse.return_value = [
                gi.TxnRaw("2026-01-02", "B", -20.0, ""),
                gi.TxnRaw("2026-01-01", "A", -10.0, ""),
            ]
            return mock_parser
        elif bank_type == "xlsx":
            mock_parser.parse.return_value = [gi.TxnRaw("2026-01-03", "C", -30.0, "")]
            return mock_parser
        return mock_parser

    monkeypatch.setattr(
        "generic_importer.ParserFactory.get_parser",
        Mock(side_effect=get_parser_side_effect),
    )

    tx_xml = xml_importer.load_data(Path("in.xml"), None, False)
    assert [t.description for t in tx_xml] == ["A", "B"]

    tx_xlsx = xlsx_importer.load_data(Path("in.xlsx"), None, False)
    assert len(tx_xlsx) == 1
    assert tx_xlsx[0].description == "C"

    assert xlsx_importer.load_data(None, None, False) == []
    assert calls == [
        ("xml", "test_xml", False),
        ("xlsx", "test_xlsx", False),
    ]


def test_process_strict_validation_and_tag_errors(tmp_path, monkeypatch):
    importer = gi.GenericImporter(
        _write_rules(tmp_path, "strict_bank", "xlsx"), "strict_bank"
    )
    txns = [gi.TxnRaw("2026-01-10", "Store X", -25.0, "")]

    monkeypatch.setattr(gi, "validate_transaction", lambda _c: ["bad txn"])
    rows, unknown, warnings = importer.process(txns, strict=False)
    assert rows == []
    assert unknown == []
    assert warnings == 1

    with pytest.raises(ValidationError):
        importer.process(txns, strict=True)

    monkeypatch.setattr(gi, "validate_transaction", lambda _c: [])
    monkeypatch.setattr(
        gi.cu, "classify", lambda *_a: ("Expenses:Food:Groceries", ["tag1"], "store_x")
    )
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")
    monkeypatch.setattr(gi, "validate_tags", lambda _tags: ["bad tag"])

    rows, unknown, warnings = importer.process(txns, strict=False)
    assert len(rows) == 1
    assert warnings == 1
    with pytest.raises(ValidationError):
        importer.process(txns, strict=True)


def test_process_hsbc_infer_kind_branches(tmp_path, monkeypatch):
    importer = gi.GenericImporter(_write_rules(tmp_path, "hsbc", "xml"), "hsbc")
    monkeypatch.setattr(gi, "validate_transaction", lambda _c: [])
    monkeypatch.setattr(gi, "validate_tags", lambda _t: [])
    monkeypatch.setattr(
        gi.cu, "classify", lambda *_a: ("Expenses:Other:Uncategorized", [], "m")
    )
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")

    txns = [
        gi.TxnRaw("2026-01-10", "DESC", -100.0, ""),
        gi.TxnRaw("2026-01-11", "DESC", 100.0, ""),
        gi.TxnRaw("2026-01-12", "DESC", 20.0, ""),
    ]
    kinds = iter(["charge", "payment", "cashback"])
    monkeypatch.setattr("import_hsbc_cfdi_firefly.infer_kind", lambda *_a: next(kinds))

    rows, _, _ = importer.process(txns, strict=False)
    assert [r.transaction_type for r in rows] == ["withdrawal", "transfer", "transfer"]
    assert rows[2].account_id == "Income:Cashback"


def test_process_populates_canonical_account_id(tmp_path, monkeypatch):
    importer = gi.GenericImporter(
        _write_rules(tmp_path, "canon_bank", "xlsx"), "canon_bank"
    )
    txns = [gi.TxnRaw("2026-01-10", "DESC", -100.0, "")]

    captured = {}

    def _capture_validate(canonical_txn):
        captured["canonical_account_id"] = canonical_txn.canonical_account_id
        return []

    monkeypatch.setattr(gi, "validate_transaction", _capture_validate)
    monkeypatch.setattr(gi, "validate_tags", lambda _t: [])
    monkeypatch.setattr(
        gi, "resolve_canonical_account_id", lambda *_a, **_k: "cc:canon_bank"
    )
    monkeypatch.setattr(
        gi.cu, "classify", lambda *_a: ("Expenses:Other:Uncategorized", [], "m")
    )
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")

    rows, _, _ = importer.process(txns, strict=False)
    assert len(rows) == 1
    assert captured["canonical_account_id"] == "cc:canon_bank"


def test_main_dry_run_and_write_modes(tmp_path, monkeypatch):
    rules_path = _write_rules(tmp_path, "main_bank", "xlsx")
    out_csv = tmp_path / "out.csv"
    out_unknown = tmp_path / "unknown.csv"
    log_path = tmp_path / "manifest.json"

    class DummyImporter:
        def __init__(self, _rules, _bank):
            pass

        def load_data(self, *_a):
            return [gi.TxnRaw("2026-01-10", "DESC", -10.0, "")]

        def process(self, _txns, strict=False):
            return ([{"type": "withdrawal"}], [{"merchant": "x"}], 0)

    monkeypatch.setattr(gi, "GenericImporter", DummyImporter)
    monkeypatch.setattr(gi.pu, "extract_pdf_metadata", lambda _p: {"ok": True})

    write_calls = {"count": 0}
    monkeypatch.setattr(
        gi,
        "write_csv_atomic",
        lambda _df, _path: write_calls.__setitem__("count", write_calls["count"] + 1),
    )
    monkeypatch.setattr(
        gi,
        "write_json_atomic",
        lambda path, manifest: path.write_text(str(manifest), encoding="utf-8"),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--bank",
            "main_bank",
            "--rules",
            str(rules_path),
            "--out",
            str(out_csv),
            "--unknown-out",
            str(out_unknown),
            "--dry-run",
            "--pdf",
            str(tmp_path / "dummy.pdf"),
            "--log-json",
            str(log_path),
        ],
    )
    gi.main()
    assert write_calls["count"] == 0
    assert log_path.exists()

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--bank",
            "main_bank",
            "--rules",
            str(rules_path),
            "--out",
            str(out_csv),
            "--unknown-out",
            str(out_unknown),
        ],
    )
    gi.main()
    assert write_calls["count"] == 2
