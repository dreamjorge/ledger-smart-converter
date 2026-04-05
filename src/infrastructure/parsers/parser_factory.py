from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.xml_parser import XmlParser
from infrastructure.parsers.excel_parser import ExcelParser
from infrastructure.parsers.pdf_parser import PdfParser
from infrastructure.parsers.banamex_parser import BanamexPdfParser

# Banks that require a dedicated parser regardless of generic type routing.
# Key: bank_id, Value: parser class (no-arg constructor).
_BANK_SPECIFIC_PARSERS = {
    "banamex": BanamexPdfParser,
}


class ParserFactory:
    """Factory for creating the appropriate StatementParser based on configuration."""

    @staticmethod
    def get_parser(bank_type: str, bank_id: str = "", use_pdf_source: bool = False) -> StatementParser:
        if use_pdf_source:
            # Bank-specific PDF parsers take precedence over generic PdfParser
            if bank_id in _BANK_SPECIFIC_PARSERS:
                return _BANK_SPECIFIC_PARSERS[bank_id]()
            return PdfParser()

        if bank_id in _BANK_SPECIFIC_PARSERS:
            return _BANK_SPECIFIC_PARSERS[bank_id]()

        if bank_type == "xml":
            return XmlParser()
        return ExcelParser()
