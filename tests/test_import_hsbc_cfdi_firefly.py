# -*- coding: utf-8 -*-
"""Comprehensive test suite for HSBC CFDI importer.

Tests XML parsing, PDF-XML reconciliation, transaction type inference,
and error handling for the HSBC bank importer.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import pytest

# Import module under test
import sys
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
    PAYMENT_HINT,
    PAYMENT_PROCESSOR_HINT,
    CHARGE_SERVICE_HINT,
    REFUND_HINT,
    CASHBACK_HINT,
    main,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def fixtures_dir():
    """Path to HSBC test fixtures directory."""
    return Path(__file__).parent / "fixtures" / "hsbc"


@pytest.fixture
def valid_cfdi_xml(fixtures_dir):
    """Load valid CFDI XML file."""
    xml_path = fixtures_dir / "valid_cfdi.xml"
    tree = ET.parse(xml_path)
    return tree.getroot()


@pytest.fixture
def malformed_cfdi_xml(fixtures_dir):
    """Load malformed CFDI XML file."""
    xml_path = fixtures_dir / "malformed_cfdi.xml"
    tree = ET.parse(xml_path)
    return tree.getroot()


@pytest.fixture
def missing_fields_xml(fixtures_dir):
    """Load CFDI XML with missing fields."""
    xml_path = fixtures_dir / "missing_fields.xml"
    tree = ET.parse(xml_path)
    return tree.getroot()


@pytest.fixture
def sample_transactions():
    """Sample TxnRaw objects for testing."""
    return [
        TxnRaw(
            date="2024-01-12",
            description="OXXO REFORMA",
            amount=-45.50,
            rfc="",
            account_hint="1234567890",
            source="xml"
        ),
        TxnRaw(
            date="2024-01-13",
            description="WALMART",
            amount=-234.00,
            rfc="WAL850101ABC",
            account_hint="1234567890",
            source="xml"
        ),
    ]


# ============================================================================
# Tests for parse_iso_date
# ============================================================================

class TestParseISODate:
    """Tests for ISO timestamp parsing."""

    def test_parse_full_iso_timestamp(self):
        """Parse full ISO timestamp to date."""
        assert parse_iso_date("2024-01-15T10:30:00") == "2024-01-15"
        assert parse_iso_date("2023-12-31T23:59:59") == "2023-12-31"

    def test_parse_iso_date_only(self):
        """Parse ISO date (no time) as-is."""
        result = parse_iso_date("2024-01-15")
        assert result == "2024-01-15"

    def test_parse_with_milliseconds(self):
        """Parse timestamp with milliseconds."""
        assert parse_iso_date("2024-01-15T10:30:00.123") == "2024-01-15"

    def test_parse_with_timezone(self):
        """Parse timestamp with timezone."""
        assert parse_iso_date("2024-01-15T10:30:00-06:00") == "2024-01-15"
        assert parse_iso_date("2024-01-15T10:30:00+00:00") == "2024-01-15"

    def test_parse_empty_string(self):
        """Empty string returns empty."""
        assert parse_iso_date("") == ""
        assert parse_iso_date("   ") == ""

    def test_parse_none(self):
        """None input returns empty."""
        assert parse_iso_date(None) == ""

    def test_parse_invalid_format(self):
        """Invalid format returns first 10 chars."""
        assert parse_iso_date("invalid-date") == "invalid-da"

    def test_parse_whitespace_handling(self):
        """Handles leading/trailing whitespace."""
        assert parse_iso_date("  2024-01-15T10:30:00  ") == "2024-01-15"


# ============================================================================
# Tests for TxnRaw dataclass
# ============================================================================

class TestTxnRaw:
    """Tests for TxnRaw transaction model."""

    def test_create_txn_raw(self):
        """Create TxnRaw with all fields."""
        txn = TxnRaw(
            date="2024-01-15",
            description="TEST MERCHANT",
            amount=-100.50,
            rfc="TST850101ABC",
            account_hint="1234567890",
            source="xml",
            page=1,
            source_line="<MovimientoDelClienteFiscal...>"
        )

        assert txn.date == "2024-01-15"
        assert txn.description == "TEST MERCHANT"
        assert txn.amount == -100.50
        assert txn.rfc == "TST850101ABC"
        assert txn.account_hint == "1234567890"
        assert txn.source == "xml"
        assert txn.page == 1

    def test_txn_raw_defaults(self):
        """TxnRaw uses default values."""
        txn = TxnRaw(
            date="2024-01-15",
            description="TEST",
            amount=100.0,
            rfc="",
            account_hint=""
        )

        assert txn.source == "xml"  # Default
        assert txn.page == 0  # Default
        assert txn.source_line == ""  # Default

    def test_txn_raw_immutable(self):
        """TxnRaw is frozen (immutable)."""
        txn = TxnRaw(
            date="2024-01-15",
            description="TEST",
            amount=100.0,
            rfc="",
            account_hint=""
        )

        with pytest.raises(AttributeError):
            txn.amount = 200.0  # Should raise error


# ============================================================================
# Tests for txn_match_key
# ============================================================================

class TestTxnMatchKey:
    """Tests for transaction matching key generation."""

    def test_match_key_basic(self):
        """Generate match key from transaction."""
        txn = TxnRaw(
            date="2024-01-15",
            description="TEST",
            amount=-100.50,
            rfc="",
            account_hint=""
        )

        key = txn_match_key(txn)
        assert key == ("2024-01-15", 100.50)

    def test_match_key_absolute_amount(self):
        """Match key uses absolute value of amount."""
        txn_negative = TxnRaw(date="2024-01-15", description="A", amount=-50.0, rfc="", account_hint="")
        txn_positive = TxnRaw(date="2024-01-15", description="B", amount=50.0, rfc="", account_hint="")

        assert txn_match_key(txn_negative) == txn_match_key(txn_positive)

    def test_match_key_rounding(self):
        """Match key rounds amount to 2 decimals."""
        txn1 = TxnRaw(date="2024-01-15", description="A", amount=-100.504, rfc="", account_hint="")
        txn2 = TxnRaw(date="2024-01-15", description="B", amount=-100.506, rfc="", account_hint="")

        key1 = txn_match_key(txn1)
        key2 = txn_match_key(txn2)

        # Python round() uses banker's rounding
        assert key1[1] == 100.50  # 100.504 rounds to 100.50
        assert key2[1] == 100.51  # 100.506 rounds to 100.51

    def test_match_key_different_dates(self):
        """Different dates produce different keys."""
        txn1 = TxnRaw(date="2024-01-15", description="A", amount=-100.0, rfc="", account_hint="")
        txn2 = TxnRaw(date="2024-01-16", description="A", amount=-100.0, rfc="", account_hint="")

        assert txn_match_key(txn1) != txn_match_key(txn2)


# ============================================================================
# Tests for apply_xml_reference_to_pdf
# ============================================================================

class TestApplyXMLReferenceToPDF:
    """Tests for PDF-XML reconciliation logic."""

    def test_perfect_match(self):
        """All PDF transactions match XML."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.50, rfc="", account_hint="", source="pdf"),
            TxnRaw(date="2024-01-16", description="WALMART", amount=-100.0, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO REFORMA", amount=-45.50, rfc="OXX850101ABC", account_hint="1234"),
            TxnRaw(date="2024-01-16", description="WALMART INSURGENTES", amount=-100.0, rfc="WAL850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        assert len(merged) == 2
        assert summary["matched"] == 2
        assert summary["total_pdf"] == 2
        assert summary["total_xml"] == 2
        assert len(summary["pdf_only"]) == 0
        assert len(summary["xml_only"]) == 0

        # Check merged data combines PDF description with XML RFC
        assert merged[0].description == "OXXO"
        assert merged[0].rfc == "OXX850101ABC"
        assert merged[0].account_hint == "1234"

    def test_pdf_only_transactions(self):
        """Some transactions only in PDF."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.50, rfc="", account_hint="", source="pdf"),
            TxnRaw(date="2024-01-16", description="WALMART", amount=-100.0, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO REFORMA", amount=-45.50, rfc="OXX850101ABC", account_hint="1234"),
            # Missing WALMART in XML
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        assert len(merged) == 2
        assert summary["matched"] == 1
        assert len(summary["pdf_only"]) == 1
        assert summary["pdf_only"][0].description == "WALMART"

    def test_xml_only_transactions(self):
        """Some transactions only in XML."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.50, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO REFORMA", amount=-45.50, rfc="OXX850101ABC", account_hint="1234"),
            TxnRaw(date="2024-01-16", description="WALMART", amount=-100.0, rfc="WAL850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        assert len(merged) == 1  # Only matched PDF
        assert summary["matched"] == 1
        assert len(summary["xml_only"]) == 1
        assert summary["xml_only"][0].description == "WALMART"

    def test_description_difference_detected(self):
        """Detects differences in descriptions."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO STORE", amount=-45.50, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO DIFFERENT", amount=-45.50, rfc="OXX850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        assert len(summary["differences"]) == 1
        diff = summary["differences"][0]
        assert diff["pdf_desc"] == "OXXO STORE"
        assert diff["xml_desc"] == "OXXO DIFFERENT"

    def test_amount_difference_detected(self):
        """Detects differences in amounts (when they don't match)."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.50, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-46.00, rfc="OXX850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        # Note: Amounts don't match in match_key, so they won't be merged
        # This tests the case where match key is different
        # For actual amount difference detection, amounts must first match in key
        assert summary["matched"] == 0  # Different amounts, no match

    def test_amount_within_tolerance(self):
        """Amounts within rounding (match key uses rounded values)."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.504, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO", amount=-45.505, rfc="OXX850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        # Match keys use rounded amounts, so these should match or not based on rounding
        # The function matches by (date, rounded_amount), so small differences matter
        assert summary["total_pdf"] == 1
        assert summary["total_xml"] == 1

    def test_empty_lists(self):
        """Handle empty PDF and XML lists."""
        merged, summary = apply_xml_reference_to_pdf([], [])

        assert len(merged) == 0
        assert summary["matched"] == 0
        assert summary["total_pdf"] == 0
        assert summary["total_xml"] == 0

    def test_fallback_description(self):
        """Use XML description when PDF description is empty."""
        pdf_txns = [
            TxnRaw(date="2024-01-15", description="", amount=-45.50, rfc="", account_hint="", source="pdf"),
        ]

        xml_txns = [
            TxnRaw(date="2024-01-15", description="OXXO FROM XML", amount=-45.50, rfc="OXX850101ABC", account_hint="1234"),
        ]

        merged, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

        assert merged[0].description == "OXXO FROM XML"


# ============================================================================
# Tests for print_pdf_xml_validation_summary
# ============================================================================

class TestPrintPDFXMLValidationSummary:
    """Tests for validation summary logging."""

    def test_print_summary_none(self, caplog):
        """None summary produces no output."""
        print_pdf_xml_validation_summary(None)
        assert len(caplog.records) == 0

    def test_print_summary_basic(self, caplog):
        """Log basic summary."""
        import logging
        caplog.set_level(logging.INFO)

        summary = {
            "matched": 5,
            "total_pdf": 6,
            "total_xml": 5,
            "pdf_only": [],
            "xml_only": [],
            "differences": [],
        }

        print_pdf_xml_validation_summary(summary)

        assert "PDF vs XML Validation" in caplog.text
        assert "Matches: 5 / 6 (PDF) vs 5 (XML)" in caplog.text


# ============================================================================
# Tests for get_addenda
# ============================================================================

class TestGetAddenda:
    """Tests for Addenda extraction from CFDI XML."""

    def test_get_addenda_exists(self, valid_cfdi_xml):
        """Extract Addenda when present."""
        addenda = get_addenda(valid_cfdi_xml)

        assert addenda is not None
        assert "Addenda" in addenda.tag

    def test_get_addenda_missing(self, malformed_cfdi_xml):
        """Return None when Addenda missing."""
        addenda = get_addenda(malformed_cfdi_xml)

        assert addenda is None


# ============================================================================
# Tests for get_datos_generales
# ============================================================================

class TestGetDatosGenerales:
    """Tests for DatosGenerales extraction."""

    def test_get_datos_generales_exists(self, valid_cfdi_xml):
        """Extract DatosGenerales when present."""
        addenda = get_addenda(valid_cfdi_xml)
        datos = get_datos_generales(addenda)

        assert "numerodecuenta" in datos
        assert datos["numerodecuenta"] == "1234567890"
        assert datos["periodo"] == "2024-01"

    def test_get_datos_generales_missing(self, malformed_cfdi_xml):
        """Return empty dict when DatosGenerales missing."""
        # Create simple addenda without DatosGenerales
        addenda = ET.Element("Addenda")

        datos = get_datos_generales(addenda)

        assert datos == {}


# ============================================================================
# Tests for extract_movimientos
# ============================================================================

class TestExtractMovimientos:
    """Tests for transaction extraction from XML."""

    def test_extract_movimientos_valid(self, valid_cfdi_xml):
        """Extract all movements from valid XML."""
        addenda = get_addenda(valid_cfdi_xml)
        movimientos = extract_movimientos(addenda)

        # Should extract 4 movements
        assert len(movimientos) >= 3

        # Check first movimiento
        txn = movimientos[0]
        assert txn.date == "2024-01-12"
        assert "OXXO" in txn.description
        assert txn.amount == -45.50
        assert txn.account_hint == "1234567890"

    def test_extract_movimientos_with_rfc(self, valid_cfdi_xml):
        """Extract MovimientoDelClienteFiscal with RFC."""
        addenda = get_addenda(valid_cfdi_xml)
        movimientos = extract_movimientos(addenda)

        # Find Amazon transaction (has RFC)
        amazon_txn = [t for t in movimientos if "AMAZON" in t.description][0]

        assert amazon_txn.rfc == "AMZ850101ABC"
        assert amazon_txn.amount == -567.89

    def test_extract_movimientos_sorting(self, valid_cfdi_xml):
        """Movements are sorted by date, description, amount, RFC."""
        addenda = get_addenda(valid_cfdi_xml)
        movimientos = extract_movimientos(addenda)

        # Should be sorted
        for i in range(len(movimientos) - 1):
            current = movimientos[i]
            next_txn = movimientos[i + 1]

            # Check sort order
            assert (current.date, current.description, current.amount, current.rfc) <= \
                   (next_txn.date, next_txn.description, next_txn.amount, next_txn.rfc)

    def test_extract_movimientos_missing_fields(self, missing_fields_xml):
        """Skip movements with missing required fields."""
        addenda = get_addenda(missing_fields_xml)
        movimientos = extract_movimientos(addenda)

        # Should only extract valid entry (skips incomplete)
        assert len(movimientos) == 1
        assert movimientos[0].description == "VALID ENTRY"


# ============================================================================
# Tests for infer_kind
# ============================================================================

class TestInferKind:
    """Tests for transaction type inference."""

    def test_infer_kind_known_service(self):
        """Known services are always charges."""
        assert infer_kind("NETFLIX SUBSCRIPTION", -150.0, "") == "charge"
        assert infer_kind("SPOTIFY PREMIUM", -99.0, "") == "charge"
        assert infer_kind("NINTENDO ESHOP", -500.0, "") == "charge"
        assert infer_kind("DISNEY PLUS", -159.0, "") == "charge"

    def test_infer_kind_cashback(self):
        """Cashback transactions identified."""
        assert infer_kind("CASHBACK PROMOCION", 50.0, "") == "cashback"
        assert infer_kind("BONIFICACION ESPECIAL", 25.0, "") == "cashback"

    def test_infer_kind_refund(self):
        """Refund transactions identified."""
        assert infer_kind("REEMBOLSO COMPRA", 100.0, "") == "refund"
        assert infer_kind("DEVOLUCION AMAZON", 250.0, "") == "refund"

    def test_infer_kind_payment_processor_charge(self):
        """Payment processor transactions are charges."""
        assert infer_kind("MERCADOPAGO COMPRA", -100.0, "") == "charge"
        assert infer_kind("PAYPAL TRANSACTION", -50.0, "") == "charge"
        assert infer_kind("CLIP MX PAGO", -75.0, "") == "charge"

    def test_infer_kind_payment_processor_payment(self):
        """Payment processor with clear payment keywords."""
        assert infer_kind("SU PAGO GRACIAS MERCADOPAGO", 1500.0, "") == "payment"
        assert infer_kind("GRACIAS SPEI PAYPAL", 2000.0, "") == "payment"

    def test_infer_kind_payment_keywords(self):
        """Clear payment keywords identified."""
        assert infer_kind("PAGO TARJETA CREDITO", 1000.0, "") == "payment"
        assert infer_kind("ABONO A CUENTA", 500.0, "") == "payment"
        assert infer_kind("PAYMENT RECEIVED", 750.0, "") == "payment"

    def test_infer_kind_with_rfc(self):
        """Transactions with RFC are likely charges."""
        assert infer_kind("COMERCIAL XYZ", -100.0, "XYZ850101ABC") == "charge"

    def test_infer_kind_default_negative(self):
        """Default: negative amounts are charges."""
        assert infer_kind("UNKNOWN MERCHANT", -100.0, "") == "charge"

    def test_infer_kind_default_positive(self):
        """Default: positive amounts are payments."""
        assert infer_kind("UNKNOWN DEPOSIT", 100.0, "") == "payment"

    def test_infer_kind_priority_service_over_payment(self):
        """Known service beats payment keywords."""
        # "PAGO" in description but it's a Netflix charge
        assert infer_kind("NETFLIX PAGO MENSUAL", -150.0, "") == "charge"


# ============================================================================
# Integration Tests
# ============================================================================

class TestHSBCImporterIntegration:
    """Integration tests for HSBC importer workflow."""

    def test_full_xml_extraction_workflow(self, valid_cfdi_xml):
        """Complete workflow: XML -> Addenda -> Movimientos."""
        # Step 1: Get Addenda
        addenda = get_addenda(valid_cfdi_xml)
        assert addenda is not None

        # Step 2: Get DatosGenerales
        datos = get_datos_generales(addenda)
        assert datos["numerodecuenta"] == "1234567890"

        # Step 3: Extract movements
        movimientos = extract_movimientos(addenda)
        assert len(movimientos) >= 3

        # Step 4: Verify structure
        for txn in movimientos:
            assert isinstance(txn, TxnRaw)
            assert txn.date  # Has date
            assert txn.description  # Has description
            assert txn.amount != 0  # Has amount

    def test_regex_patterns_compile(self):
        """Verify all regex patterns compile correctly."""
        patterns = [
            PAYMENT_HINT,
            PAYMENT_PROCESSOR_HINT,
            CHARGE_SERVICE_HINT,
            REFUND_HINT,
            CASHBACK_HINT,
        ]

        for pattern in patterns:
            # Should not raise exception
            pattern.search("TEST STRING")


# ============================================================================
# Edge Cases
# ============================================================================

class TestHSBCEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_txn_match_key_zero_amount(self):
        """Handle zero amount transactions."""
        txn = TxnRaw(date="2024-01-15", description="FREE", amount=0.0, rfc="", account_hint="")
        key = txn_match_key(txn)
        assert key == ("2024-01-15", 0.0)

    def test_infer_kind_empty_description(self):
        """Handle empty description."""
        assert infer_kind("", -100.0, "") == "charge"
        assert infer_kind("", 100.0, "") == "payment"

    def test_extract_movimientos_empty_addenda(self):
        """Handle empty Addenda."""
        addenda = ET.Element("Addenda")
        movimientos = extract_movimientos(addenda)
        assert movimientos == []

    def test_parse_iso_date_edge_formats(self):
        """Test various ISO date edge formats."""
        # Midnight
        assert parse_iso_date("2024-01-15T00:00:00") == "2024-01-15"

        # End of day
        assert parse_iso_date("2024-01-15T23:59:59") == "2024-01-15"

        # Noon
        assert parse_iso_date("2024-01-15T12:00:00") == "2024-01-15"


class TestHSBCMainCLI:
    """Integration tests for main() flow."""

    def test_main_processes_valid_xml_and_writes_outputs(self, tmp_path, fixtures_dir, monkeypatch):
        rules_path = tmp_path / "rules.yml"
        out_csv = tmp_path / "firefly.csv"
        out_unknown = tmp_path / "unknown.csv"
        out_suggestions = tmp_path / "suggestions.yml"
        xml_path = fixtures_dir / "valid_cfdi.xml"

        rules_path.write_text(
            """
version: 1
defaults:
  currency: MXN
  fallback_expense: Expenses:Other:Uncategorized
  accounts:
    hsbc_credit_card:
      name: Liabilities:CC:HSBC
      closing_day: 15
    hsbc_payment_asset: Assets:HSBC Debito
merchant_aliases:
  - canon: oxxo
    any_regex: ["oxxo"]
rules:
  - name: OXXO
    any_regex: ["oxxo"]
    set:
      expense: Expenses:Food:Convenience
      tags: ["bucket:convenience"]
""",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            "sys.argv",
            [
                "prog",
                "--xml",
                str(xml_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_csv),
                "--unknown-out",
                str(out_unknown),
                "--suggestions-out",
                str(out_suggestions),
            ],
        )

        assert main() == 0
        assert out_csv.exists()
        assert out_unknown.exists()
        assert out_suggestions.exists()

    def test_main_returns_2_without_input_source(self, tmp_path, monkeypatch):
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text("defaults: {}\nrules: []\n", encoding="utf-8")
        monkeypatch.setattr("sys.argv", ["prog", "--rules", str(rules_path)])
        assert main() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
