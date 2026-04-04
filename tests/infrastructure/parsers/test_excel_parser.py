import pytest
import pandas as pd
from pathlib import Path
from infrastructure.parsers.excel_parser import ExcelParser
from infrastructure.parsers.models import TxnRaw

def test_excel_parser_extracts_transactions_from_xlsx(tmp_path: Path):
    parser = ExcelParser()
    
    # Create dummy Excel data mocking Santander format
    data = [
        ["OTHER", "DATA", "IGNORE"],
        ["FECHA", "CONCEPTO", "IMPORTE"],
        ["15/mar/2026", "COMPRA SUPERMERCADO", "-1500.50"],
        ["18/abr/26", "TRANSFERENCIA", "5000.00"]
    ]
    df = pd.DataFrame(data)
    file_path = tmp_path / "test.xlsx"
    df.to_excel(file_path, index=False, header=False)

    txns = parser.parse(file_path, bank_type="xlsx")

    assert len(txns) == 2
    assert txns[0].date == "2026-03-15"
    assert txns[0].description == "COMPRA SUPERMERCADO"
    assert txns[0].amount == -1500.50

    assert txns[1].date == "2026-04-18"
    assert txns[1].description == "TRANSFERENCIA"
    assert txns[1].amount == 5000.0

def test_excel_parser_extracts_transactions_generic(tmp_path: Path):
    parser = ExcelParser()
    
    data = {
        "Date": ["2026-01-01", "2026-02-05"],
        "Description": ["TEST TXN 1", "TEST TXN 2"],
        "Amount": ["-10.0", "50.5"]
    }
    df = pd.DataFrame(data)
    file_path = tmp_path / "generic.csv"
    df.to_csv(file_path, index=False)

    txns = parser.parse(file_path, bank_type="generic")

    assert len(txns) == 2
    assert txns[0].date == "2026-01-01"
    assert txns[0].description == "TEST TXN 1"
    assert txns[0].amount == -10.0

    assert txns[1].date == "2026-02-05"
    assert txns[1].description == "TEST TXN 2"
    assert txns[1].amount == 50.5
