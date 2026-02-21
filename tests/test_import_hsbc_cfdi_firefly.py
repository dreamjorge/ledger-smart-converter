import pytest
import xml.etree.ElementTree as ET
import sys
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from import_hsbc_cfdi_firefly import (
    parse_iso_date,
    TxnRaw,
    txn_match_key,
    apply_xml_reference_to_pdf,
    print_pdf_xml_validation_summary,
    get_addenda,
    get_datos_generales,
    extract_movimientos,
    infer_kind,
    CFDI_NS,
    main
)

# ----------------------------
# Unit Tests: parse_iso_date
# ----------------------------

def test_parse_iso_date_valid():
    assert parse_iso_date("2025-12-20T12:00:00") == "2025-12-20"
    assert parse_iso_date("2024-01-15T00:00:00") == "2024-01-15"

def test_parse_iso_date_invalid_but_long():
    # It falls back to first 10 chars if fromisoformat fails
    assert parse_iso_date("2024/01/15/some/extra") == "2024/01/15"

def test_parse_iso_date_empty():
    assert parse_iso_date("") == ""
    assert parse_iso_date(None) == ""

# ----------------------------
# Unit Tests: TxnRaw & txn_match_key
# ----------------------------

def test_txn_match_key():
    txn = TxnRaw(date="2024-01-15", description="TEST", amount=-500.0, rfc="", account_hint="")
    assert txn_match_key(txn) == ("2024-01-15", 500.0)
    
    txn2 = TxnRaw(date="2024-01-15", description="TEST", amount=500.0, rfc="", account_hint="")
    assert txn_match_key(txn2) == ("2024-01-15", 500.0)

# ----------------------------
# Unit Tests: apply_xml_reference_to_pdf
# ----------------------------

def test_apply_xml_reference_to_pdf_match():
    pdf_txns = [
        TxnRaw(date="2024-01-15", description="OXXO", amount=-500.0, rfc="", account_hint="", source="pdf")
    ]
    xml_txns = [
        TxnRaw(date="2024-01-15", description="OXXO GAS 123", amount=-500.0, rfc="RFC123", account_hint="ACC123", source="xml")
    ]
    
    merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)
    
    assert len(merged) == 1
    assert merged[0].description == "OXXO"
    assert merged[0].rfc == "RFC123"
    assert merged[0].account_hint == "ACC123"
    assert merged[0].source == "pdf"
    assert summary["matched"] == 1

def test_apply_xml_reference_to_pdf_no_match():
    pdf_txns = [
        TxnRaw(date="2024-01-15", description="OXXO", amount=-500.0, rfc="", account_hint="", source="pdf")
    ]
    xml_txns = [
        TxnRaw(date="2024-01-16", description="OXXO GAS 123", amount=-500.0, rfc="RFC123", account_hint="ACC123", source="xml")
    ]
    
    merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)
    
    assert len(merged) == 1
    assert merged[0].description == "OXXO"
    assert merged[0].rfc == ""
    assert summary["matched"] == 0
    assert len(summary["xml_only"]) == 1

def test_apply_xml_reference_to_pdf_diff_description():
    pdf_txns = [
        TxnRaw(date="2024-01-15", description="OXXO", amount=-500.0, rfc="", account_hint="", source="pdf")
    ]
    xml_txns = [
        TxnRaw(date="2024-01-15", description="DIFERENTE", amount=-500.0, rfc="RFC123", account_hint="ACC123", source="xml")
    ]
    
    merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)
    assert len(summary["differences"]) == 1
    assert summary["differences"][0]["pdf_desc"] == "OXXO"
    assert summary["differences"][0]["xml_desc"] == "DIFERENTE"

# ----------------------------
# Unit Tests: print_pdf_xml_validation_summary
# ----------------------------

def test_print_pdf_xml_validation_summary_none():
    # Should not crash
    print_pdf_xml_validation_summary(None)

def test_print_pdf_xml_validation_summary_full(caplog):
    import logging
    caplog.set_level(logging.INFO)
    
    summary = {
        "matched": 1,
        "total_pdf": 2,
        "total_xml": 2,
        "pdf_only": [TxnRaw(date="2024-01-15", description="PDF ONLY", amount=-100.0, rfc="", account_hint="")],
        "xml_only": [TxnRaw(date="2024-01-16", description="XML ONLY", amount=-200.0, rfc="", account_hint="")],
        "differences": [{"date": "2024-01-17", "pdf_amount": 10.0, "xml_amount": 11.0, "pdf_desc": "P", "xml_desc": "X"}],
    }
    
    print_pdf_xml_validation_summary(summary)
    
    assert "PDF vs XML Validation" in caplog.text
    assert "Matches: 1 / 2 (PDF) vs 2 (XML)" in caplog.text
    assert "Detected 1 differences" in caplog.text
    assert "PDF-only entries: 1" in caplog.text
    assert "XML-only entries: 1" in caplog.text

# ----------------------------
# Unit Tests: XML Extraction
# ----------------------------

@pytest.fixture
def valid_xml_path():
    return Path("tests/fixtures/hsbc/valid_cfdi.xml")

@pytest.fixture
def malformed_xml_path():
    return Path("tests/fixtures/hsbc/malformed_cfdi.xml")

@pytest.fixture
def missing_fields_xml_path():
    return Path("tests/fixtures/hsbc/missing_fields.xml")

@pytest.fixture
def rules_path():
    return Path("tests/fixtures/hsbc/rules.yml")

def test_get_addenda(valid_xml_path):
    root = ET.fromstring(valid_xml_path.read_text())
    addenda = get_addenda(root)
    assert addenda is not None
    assert addenda.tag.endswith("Addenda")

def test_get_addenda_missing(malformed_xml_path):
    root = ET.fromstring(malformed_xml_path.read_text())
    addenda = get_addenda(root)
    assert addenda is None

def test_get_datos_generales(valid_xml_path):
    root = ET.fromstring(valid_xml_path.read_text())
    addenda = get_addenda(root)
    datos = get_datos_generales(addenda)
    assert datos["numerodecuenta"] == "12345678"
    assert datos["nombredelCliente"] == "JUAN PEREZ"

def test_extract_movimientos(valid_xml_path):
    root = ET.fromstring(valid_xml_path.read_text())
    addenda = get_addenda(root)
    txns = extract_movimientos(addenda)
    
    assert len(txns) == 3
    # Sorted by date
    assert txns[0].date == "2024-01-15"
    assert txns[0].description == "OXXO GAS"
    assert txns[0].amount == -500.0
    
    assert txns[1].date == "2024-01-20"
    assert txns[1].rfc == "TACO123456"
    
    assert txns[2].date == "2024-01-25"
    assert txns[2].amount == 750.0

def test_extract_movimientos_missing_fields(missing_fields_xml_path):
    root = ET.fromstring(missing_fields_xml_path.read_text())
    addenda = get_addenda(root)
    # The current implementation of extract_movimientos skips incomplete entries
    txns = extract_movimientos(addenda)
    assert len(txns) == 0

# ----------------------------
# Unit Tests: infer_kind
# ----------------------------

def test_infer_kind_charge_known_service():
    assert infer_kind("NETFLIX", -150.0, "") == "charge"
    assert infer_kind("SPOTIFY", -100.0, "") == "charge"

def test_infer_kind_cashback():
    assert infer_kind("CASHBACK PARA TI", 10.0, "") == "cashback"

def test_infer_kind_refund():
    assert infer_kind("REEMBOLSO DE COMPRA", 50.0, "") == "refund"

def test_infer_kind_payment_processor():
    assert infer_kind("MERCADOPAGO", -100.0, "") == "charge"
    assert infer_kind("MERCADOPAGO SU PAGO GRACIAS", 1000.0, "") == "payment"

def test_infer_kind_payment_keywords():
    assert infer_kind("PAGO DE TARJETA", 1500.0, "") == "payment"
    assert infer_kind("ABONO SPEI", 500.0, "") == "payment"

def test_infer_kind_with_rfc():
    assert infer_kind("ESTABLECIMIENTO", -500.0, "RFC123") == "charge"

def test_infer_kind_default():
    assert infer_kind("UNKNOWN", -100.0, "") == "charge"
    assert infer_kind("UNKNOWN", 100.0, "") == "payment"

# ----------------------------
# Integration Tests: main()
# ----------------------------

def test_main_xml_only(tmp_path, valid_xml_path, rules_path):
    out_csv = tmp_path / "firefly_hsbc.csv"
    unknown_csv = tmp_path / "unknown_merchants.csv"
    suggestions_yml = tmp_path / "rules_suggestions.yml"
    
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--xml", str(valid_xml_path),
        "--rules", str(rules_path),
        "--out", str(out_csv),
        "--unknown-out", str(unknown_csv),
        "--suggestions-out", str(suggestions_yml)
    ]
    
    with patch("sys.argv", test_args):
        exit_code = main()
        
    assert exit_code == 0
    assert out_csv.exists()
    assert unknown_csv.exists()
    assert suggestions_yml.exists()
    
    content = out_csv.read_text()
    assert "OXXO GAS" in content
    assert "RESTAURANTE EL TACO" in content
    assert "SU PAGO GRACIAS" in content

def test_main_no_rules():
    test_args = ["import_hsbc_cfdi_firefly.py"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
    assert excinfo.value.code == 2

def test_main_missing_source(rules_path, caplog):
    import logging
    caplog.set_level(logging.ERROR)
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--rules", str(rules_path)
    ]
    with patch("sys.argv", test_args):
        exit_code = main()
    assert exit_code == 2
    assert "Debe proporcionar --xml, --csv o --pdf" in caplog.text

def test_main_invalid_rules():
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--xml", "tests/fixtures/hsbc/valid_cfdi.xml",
        "--rules", "non_existent.yml"
    ]
    with patch("sys.argv", test_args):
        exit_code = main()
    assert exit_code == 2

def test_main_xml_missing_addenda(tmp_path, malformed_xml_path, rules_path):
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--xml", str(malformed_xml_path),
        "--rules", str(rules_path),
        "--out", str(tmp_path / "out.csv")
    ]
    with patch("sys.argv", test_args):
        exit_code = main()
    assert exit_code == 3

@patch("pdf_utils.extract_pdf_metadata")
@patch("pdf_utils.extract_transactions_from_pdf")
@patch("pdf_utils.parse_mx_date")
def test_main_pdf_source(mock_parse_date, mock_extract_txns, mock_meta, tmp_path, rules_path):
    mock_meta.return_value = {"cutoff_date": "2024-01-31"}
    mock_extract_txns.return_value = [
        {"raw_date": "15 ENE", "description": "PDF TXN", "amount": -100.0}
    ]
    mock_parse_date.return_value = "2024-01-15"
    
    pdf_file = tmp_path / "statement.pdf"
    pdf_file.write_text("fake pdf")
    
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--pdf", str(pdf_file),
        "--pdf-source",
        "--rules", str(rules_path),
        "--out", str(tmp_path / "out.csv")
    ]
    
    with patch("sys.argv", test_args):
        exit_code = main()
        
    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
    content = (tmp_path / "out.csv").read_text()
    assert "PDF TXN" in content

def test_main_csv_source(tmp_path, rules_path):
    csv_file = tmp_path / "test.csv"
    df = pd.DataFrame({
        "fecha": ["2024-01-15"],
        "descripcion": ["CSV TXN"],
        "importe": ["-100.00"]
    })
    df.to_csv(csv_file, index=False)
    
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--csv", str(csv_file),
        "--rules", str(rules_path),
        "--out", str(tmp_path / "out.csv")
    ]
    
    with patch("sys.argv", test_args):
        exit_code = main()
    
    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
    content = (tmp_path / "out.csv").read_text()
    assert "CSV TXN" in content

@patch("pandas.read_excel")
def test_main_xlsx_source(mock_read_excel, tmp_path, rules_path):
    xlsx_file = tmp_path / "test.xlsx"
    xlsx_file.touch()
    
    mock_read_excel.return_value = pd.DataFrame({
        "fecha": ["2024-01-15"],
        "descripcion": ["XLSX TXN"],
        "importe": ["-100.00"]
    })
    
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--xml", str(xlsx_file), # Passing XLSX to --xml also works if extension is correct
        "--rules", str(rules_path),
        "--out", str(tmp_path / "out.csv")
    ]
    
    with patch("sys.argv", test_args):
        exit_code = main()
    
    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
    content = (tmp_path / "out.csv").read_text()
    assert "XLSX TXN" in content

@patch("pdf_utils.extract_pdf_metadata")
def test_main_xml_and_pdf_reconcile(mock_meta, tmp_path, valid_xml_path, rules_path):
    mock_meta.return_value = {"cutoff_date": "2024-01-31"}
    
    pdf_file = tmp_path / "statement.pdf"
    pdf_file.write_text("fake pdf")
    
    test_args = [
        "import_hsbc_cfdi_firefly.py",
        "--xml", str(valid_xml_path),
        "--pdf", str(pdf_file),
        "--rules", str(rules_path),
        "--out", str(tmp_path / "out.csv")
    ]
    
    with patch("sys.argv", test_args):
        exit_code = main()
        
    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
