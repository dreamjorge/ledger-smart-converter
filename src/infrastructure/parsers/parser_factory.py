from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.xml_parser import XmlParser
from infrastructure.parsers.excel_parser import ExcelParser
from infrastructure.parsers.pdf_parser import PdfParser

class ParserFactory:
    """Factory for creating the appropriate StatementParser based on configuration."""
    
    @staticmethod
    def get_parser(bank_type: str, use_pdf_source: bool = False) -> StatementParser:
        if use_pdf_source:
            return PdfParser()
            
        if bank_type == "xml":
            return XmlParser()
        else:
            return ExcelParser()
