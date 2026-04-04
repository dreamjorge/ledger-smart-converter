from pathlib import Path
from typing import List
from datetime import datetime

from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.models import TxnRaw
import pdf_utils as pu

class PdfParser(StatementParser):
    """Parser for extracting transactions from PDF files via OCR or text extraction."""
    
    def parse(self, file_path: Path) -> List[TxnRaw]:
        raw_pdf = pu.extract_transactions_from_pdf(file_path, use_ocr=True)
        year = datetime.now().year
        
        txns = []
        for pt in raw_pdf:
            iso_date = pu.parse_mx_date(pt["raw_date"], year=year)
            if iso_date:
                txns.append(TxnRaw(
                    date=iso_date, 
                    description=pt["description"], 
                    amount=pt["amount"], 
                    source="pdf"
                ))
        return txns
