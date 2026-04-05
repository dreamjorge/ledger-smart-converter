import pytest
from pathlib import Path
from infrastructure.parsers.parser_factory import ParserFactory
from infrastructure.parsers.xml_parser import XmlParser
from infrastructure.parsers.excel_parser import ExcelParser
from infrastructure.parsers.pdf_parser import PdfParser
from infrastructure.parsers.banamex_parser import BanamexPdfParser


def test_parser_factory_returns_xml_parser():
    parser = ParserFactory.get_parser("xml", use_pdf_source=False)
    assert isinstance(parser, XmlParser)

def test_parser_factory_returns_excel_parser_for_xlsx():
    parser = ParserFactory.get_parser("xlsx", use_pdf_source=False)
    assert isinstance(parser, ExcelParser)

def test_parser_factory_returns_excel_parser_for_default():
    parser = ParserFactory.get_parser("unknown", use_pdf_source=False)
    assert isinstance(parser, ExcelParser)

def test_parser_factory_returns_pdf_parser_if_use_pdf_true():
    parser = ParserFactory.get_parser("xml", use_pdf_source=True)
    assert isinstance(parser, PdfParser)

def test_parser_factory_returns_banamex_parser_by_bank_id():
    parser = ParserFactory.get_parser("pdf", bank_id="banamex", use_pdf_source=False)
    assert isinstance(parser, BanamexPdfParser)

def test_parser_factory_returns_banamex_parser_when_pdf_source_and_bank_id():
    parser = ParserFactory.get_parser("pdf", bank_id="banamex", use_pdf_source=True)
    assert isinstance(parser, BanamexPdfParser)

def test_parser_factory_unknown_bank_id_falls_through_to_type_routing():
    parser = ParserFactory.get_parser("xml", bank_id="unknown_bank", use_pdf_source=False)
    assert isinstance(parser, XmlParser)
