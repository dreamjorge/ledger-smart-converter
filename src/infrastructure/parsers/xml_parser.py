import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.models import TxnRaw, parse_iso_date
import common_utils as cu

class XmlParser(StatementParser):
    """Parser for HSBC-like CFDI XML files."""
    
    def parse(self, file_path: Path) -> List[TxnRaw]:
        root = ET.fromstring(file_path.read_text(encoding="utf-8", errors="ignore"))
        addenda = root.find(".//{*}Addenda")
        if addenda is None:
            return []
        
        out = []
        for e in addenda.iter():
            tag = e.tag.split("}")[-1]
            if tag in ["MovimientosDelCliente", "MovimientoDelClienteFiscal"]:
                date = parse_iso_date(e.attrib.get("fecha", ""))
                desc = cu.strip_ws(e.attrib.get("descripcion", ""))
                amt = cu.parse_money(e.attrib.get("importe"))
                rfc = e.attrib.get("RFCenajenante", "")
                if date and desc and amt is not None:
                    out.append(TxnRaw(date=date, description=desc, amount=amt, rfc=rfc))
        return out
