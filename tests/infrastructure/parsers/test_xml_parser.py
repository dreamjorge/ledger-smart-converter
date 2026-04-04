import pytest
from pathlib import Path
from infrastructure.parsers.xml_parser import XmlParser
from infrastructure.parsers.models import TxnRaw

def test_xml_parser_extracts_transactions_correctly(tmp_path: Path):
    parser = XmlParser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3">
        <cfdi:Addenda>
            <MovimientosDelCliente fecha="2026-01-15T00:00:00" descripcion="Pago de Servicio" importe="-150.00" RFCenajenante="ABC123456T1"/>
            <MovimientoDelClienteFiscal fecha="2026-01-16T10:30:00" descripcion="Transferencia" importe="500.00"/>
        </cfdi:Addenda>
    </cfdi:Comprobante>
    """
    file_path = tmp_path / "test.xml"
    file_path.write_text(xml_content, encoding="utf-8")

    txns = parser.parse(file_path)

    assert len(txns) == 2
    assert txns[0].date == "2026-01-15"
    assert txns[0].description == "Pago de Servicio"
    assert txns[0].amount == -150.0
    assert txns[0].rfc == "ABC123456T1"

    assert txns[1].date == "2026-01-16"
    assert txns[1].description == "Transferencia"
    assert txns[1].amount == 500.0
    assert txns[1].rfc == ""

def test_xml_parser_empty_or_invalid_addenda(tmp_path: Path):
    parser = XmlParser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?><cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3"></cfdi:Comprobante>"""
    file_path = tmp_path / "invalid.xml"
    file_path.write_text(xml_content, encoding="utf-8")
    
    txns = parser.parse(file_path)
    assert txns == []
