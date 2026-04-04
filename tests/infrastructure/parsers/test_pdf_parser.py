import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from infrastructure.parsers.pdf_parser import PdfParser
from infrastructure.parsers.models import TxnRaw

@patch("pdf_utils.extract_transactions_from_pdf")
def test_pdf_parser_extracts_transactions(mock_extract):
    mock_extract.return_value = [
        {"raw_date": "15 ENE", "description": "COMPRA 1", "amount": -200.0},
        {"raw_date": "INVALID", "description": "COMPRA 2", "amount": -100.0},
        {"raw_date": "20 FEB", "description": "COMPRA 3", "amount": -50.0}
    ]
    
    parser = PdfParser()
    txns = parser.parse(Path("dummy.pdf"))
    
    # INVALID date is skipped
    assert len(txns) == 2
    assert txns[0].description == "COMPRA 1"
    assert txns[0].amount == -200.0
    
    assert txns[1].description == "COMPRA 3"
    assert txns[1].amount == -50.0
