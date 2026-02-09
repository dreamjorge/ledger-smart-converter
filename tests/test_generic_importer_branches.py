from pathlib import Path

import pandas as pd
import pytest
import yaml

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
    importer = gi.GenericImporter(_write_rules(tmp_path, "test_pdf", "xlsx"), "test_pdf")
    monkeypatch.setattr(
        gi.pu,
        "extract_transactions_from_pdf",
        lambda _p, use_ocr=True: [
            {"raw_date": "12 ENE", "description": "A", "amount": -10.0},
            {"raw_date": "bad", "description": "B", "amount": -20.0},
        ],
    )
    monkeypatch.setattr(gi.pu, "parse_mx_date", lambda raw_date, year: "2026-01-12" if raw_date == "12 ENE" else None)
    txns = importer.load_data(None, Path("dummy.pdf"), True)
    assert len(txns) == 1
    assert txns[0].source == "pdf"


def test_load_data_dispatches_xml_xlsx_and_generic(tmp_path, monkeypatch):
    xml_importer = gi.GenericImporter(_write_rules(tmp_path, "test_xml", "xml"), "test_xml")
    xlsx_importer = gi.GenericImporter(_write_rules(tmp_path, "test_xlsx", "xlsx"), "test_xlsx")

    monkeypatch.setattr(
        xml_importer,
        "_load_xml",
        lambda _p: [
            gi.TxnRaw("2026-01-02", "B", -20.0, ""),
            gi.TxnRaw("2026-01-01", "A", -10.0, ""),
        ],
    )
    monkeypatch.setattr(
        xlsx_importer,
        "_load_xlsx",
        lambda _p: [gi.TxnRaw("2026-01-03", "C", -30.0, "")],
    )
    monkeypatch.setattr(
        xlsx_importer,
        "_load_generic",
        lambda _p: [gi.TxnRaw("2026-01-04", "D", -40.0, "")],
    )

    tx_xml = xml_importer.load_data(Path("in.xml"), None, False)
    assert [t.description for t in tx_xml] == ["A", "B"]

    tx_xlsx = xlsx_importer.load_data(Path("in.xlsx"), None, False)
    assert len(tx_xlsx) == 1
    assert tx_xlsx[0].description == "C"

    tx_fallback = xlsx_importer.load_data(Path("in.csv"), None, False)
    assert len(tx_fallback) == 1
    assert tx_fallback[0].description == "D"

    assert xlsx_importer.load_data(None, None, False) == []


def test_load_xml_and_generic_parser_branches(tmp_path):
    importer_xml = gi.GenericImporter(_write_rules(tmp_path, "parser_xml", "xml"), "parser_xml")
    xml_path = tmp_path / "cfdi.xml"
    xml_path.write_text(
        """
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4">
  <cfdi:Addenda>
    <MovimientosDelCliente fecha="2026-01-10T10:00:00" descripcion="STORE A" importe="-100.00"/>
    <MovimientoDelClienteFiscal fecha="2026-01-11T11:00:00" descripcion="STORE B" importe="-50.00" RFCenajenante="RFC123"/>
  </cfdi:Addenda>
</cfdi:Comprobante>
""",
        encoding="utf-8",
    )
    rows = importer_xml._load_xml(xml_path)
    assert len(rows) == 2
    assert rows[1].rfc == "RFC123"

    xml_no_addenda = tmp_path / "no_addenda.xml"
    xml_no_addenda.write_text("<root/>", encoding="utf-8")
    assert importer_xml._load_xml(xml_no_addenda) == []

    importer_generic = gi.GenericImporter(_write_rules(tmp_path, "parser_generic", "xlsx"), "parser_generic")
    csv_ok = tmp_path / "data.csv"
    pd.DataFrame(
        [
            {"Fecha": "2026-01-10", "Descripcion": "Store C", "Monto": "-44.00"},
            {"Fecha": "2026-01-11", "Descripcion": "Store D", "Monto": "55.00"},
        ]
    ).to_csv(csv_ok, index=False)
    generic_rows = importer_generic._load_generic(csv_ok)
    assert len(generic_rows) == 2

    csv_bad = tmp_path / "bad.csv"
    pd.DataFrame([{"Only": "x"}]).to_csv(csv_bad, index=False)
    assert importer_generic._load_generic(csv_bad) == []


def test_process_strict_validation_and_tag_errors(tmp_path, monkeypatch):
    importer = gi.GenericImporter(_write_rules(tmp_path, "strict_bank", "xlsx"), "strict_bank")
    txns = [gi.TxnRaw("2026-01-10", "Store X", -25.0, "")]

    monkeypatch.setattr(gi, "validate_transaction", lambda _c: ["bad txn"])
    rows, unknown, warnings = importer.process(txns, strict=False)
    assert rows == []
    assert unknown == []
    assert warnings == 1

    with pytest.raises(ValidationError):
        importer.process(txns, strict=True)

    monkeypatch.setattr(gi, "validate_transaction", lambda _c: [])
    monkeypatch.setattr(gi.cu, "classify", lambda *_a: ("Expenses:Food:Groceries", ["tag1"], "store_x"))
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
    monkeypatch.setattr(gi.cu, "classify", lambda *_a: ("Expenses:Other:Uncategorized", [], "m"))
    monkeypatch.setattr(gi.cu, "get_statement_period", lambda *_a: "2026-01")

    txns = [
        gi.TxnRaw("2026-01-10", "DESC", -100.0, ""),
        gi.TxnRaw("2026-01-11", "DESC", 100.0, ""),
        gi.TxnRaw("2026-01-12", "DESC", 20.0, ""),
    ]
    kinds = iter(["charge", "payment", "cashback"])
    monkeypatch.setattr("import_hsbc_cfdi_firefly.infer_kind", lambda *_a: next(kinds))

    rows, _, _ = importer.process(txns, strict=False)
    assert [r["type"] for r in rows] == ["withdrawal", "transfer", "transfer"]
    assert rows[2]["source_name"] == "Income:Cashback"


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
    monkeypatch.setattr(gi, "write_csv_atomic", lambda _df, _path: write_calls.__setitem__("count", write_calls["count"] + 1))
    monkeypatch.setattr(gi, "write_json_atomic", lambda path, manifest: path.write_text(str(manifest), encoding="utf-8"))

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
