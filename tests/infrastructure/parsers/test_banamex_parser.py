"""
Tests for BanamexPdfParser.

Unit tests use synthetic text lines (no PDF file needed).
Integration test uses the real PDF if present at BANAMEX_PDF_PATH.
"""

import os
import pytest
from pathlib import Path

from infrastructure.parsers.banamex_parser import (
    BanamexPdfParser,
    _parse_date,
    _parse_amount,
    _parse_transactions,
)


# ---------------------------------------------------------------------------
# Unit: date parsing
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_full_date(self):
        assert _parse_date("21-feb-2026") == "2026-02-21"

    def test_short_year(self):
        assert _parse_date("15-mar-26") == "2026-03-15"

    def test_all_months(self):
        months = [
            ("ene", "01"),
            ("feb", "02"),
            ("mar", "03"),
            ("abr", "04"),
            ("may", "05"),
            ("jun", "06"),
            ("jul", "07"),
            ("ago", "08"),
            ("sep", "09"),
            ("oct", "10"),
            ("nov", "11"),
            ("dic", "12"),
        ]
        for abbr, num in months:
            assert _parse_date(f"01-{abbr}-2026") == f"2026-{num}-01"

    def test_invalid_returns_none(self):
        assert _parse_date("not a date") is None

    def test_date_embedded_in_line(self):
        assert _parse_date("21-feb-2026 24-feb-2026 PAYPAL") == "2026-02-21"


# ---------------------------------------------------------------------------
# Unit: amount parsing
# ---------------------------------------------------------------------------


class TestParseAmount:
    def test_cargo(self):
        assert _parse_amount("+ $300.00") == -300.0

    def test_abono(self):
        assert _parse_amount("- $576.84") == 576.84

    def test_with_thousands_separator(self):
        assert _parse_amount("+ $1,234.56") == -1234.56

    def test_no_space_between_sign_and_dollar(self):
        assert _parse_amount("+$95.00") == -95.0

    def test_invalid_returns_none(self):
        assert _parse_amount("no amount here") is None


# ---------------------------------------------------------------------------
# Unit: transaction parsing from synthetic text lines
# ---------------------------------------------------------------------------

SYNTHETIC_LINES = [
    "DESGLOSE DE MOVIMIENTOS14",
    "CARGOS, ABONOS Y COMPRAS REGULARES (NO A MESES)",
    "Tarjeta titular: 55462590 27896796 JORGE A UGALDE ONTIVEROS",
    "Fecha de la",
    "operación",
    "Fecha",
    "de cargo",
    "Descripción del movimiento",
    "Monto",
    "21-feb-2026 24-feb-2026 PAYPAL *ORDENARISB2 OPM 150323DI1MX + $300.00",
    "23-feb-2026 23-feb-2026 PAGO INTERBANCARIO",
    "PAGO RECIBIDO DE: BBVA MEXICO",
    "CUENTA ORDENANTE: 012180029693267589",
    "POR ORDEN DE: JORGE ALBERTO UGALDE ONTIVEROS",
    "CLAVE DE RASTREO: MBAN01002602240078226691",
    "CONCEPTO: PAGO TARJETA",
    "FECHA Y HORA DE LIQUIDACIÓN: 23/02/2026 18:12:35",
    "REFERENCIA: 2901260 - $576.84",
    "CARGOS, ABONOS Y COMPRAS REGULARES (NO A MESES)",
    "Tarjeta digital: 55462590 41971211 JORGE A UGALDE ONTIVEROS",
    "Fecha de la",
    "operación",
    "Fecha",
    "de cargo",
    "Descripción del movimiento",
    "Monto",
    "15-feb-2026 16-feb-2026 GOOGLE MEDIUM MOUNTAIN VIEWCA + $95.00",
    "Total cargos + $395.00",
    "Total abonos - $576.84",
    "CARGOS NO RECONOCIDOS",
    "04-feb-2026 23-feb-2026 COMISION PENALIZACION INACTIVIDAD $149.00",
]


class TestParseTransactions:
    def setup_method(self):
        self.txns = _parse_transactions(SYNTHETIC_LINES)

    def test_extracts_three_transactions(self):
        assert len(self.txns) == 3

    def test_paypal_cargo(self):
        paypal = next(t for t in self.txns if "PAYPAL" in t.description)
        assert paypal.date == "2026-02-21"
        assert paypal.amount == -300.0
        assert paypal.source == "pdf"

    def test_pago_interbancario_abono(self):
        pago = next(t for t in self.txns if "PAGO INTERBANCARIO" in t.description)
        assert pago.date == "2026-02-23"
        assert pago.amount == 576.84

    def test_pago_interbancario_desc_excludes_metadata(self):
        pago = next(t for t in self.txns if "PAGO INTERBANCARIO" in t.description)
        assert "CUENTA ORDENANTE" not in pago.description
        assert "CLAVE DE RASTREO" not in pago.description
        assert "FECHA Y HORA" not in pago.description

    def test_google_digital_card(self):
        google = next(t for t in self.txns if "GOOGLE" in t.description)
        assert google.date == "2026-02-15"
        assert google.amount == -95.0

    def test_stops_at_cargos_no_reconocidos(self):
        # The disputed charge after the stop marker should NOT be included
        assert not any("COMISION PENALIZACION" in t.description for t in self.txns)


# ---------------------------------------------------------------------------
# Integration: real PDF (skipped if file not present)
# ---------------------------------------------------------------------------

REAL_PDF = Path("C:/Users/uidn7961/Downloads/Estado de Cuenta.pdf")


@pytest.mark.skipif(not REAL_PDF.exists(), reason="Real Banamex PDF not available")
class TestBanamexPdfParserIntegration:
    def setup_method(self):
        parser = BanamexPdfParser()
        self.txns = parser.parse(REAL_PDF)

    def test_extracts_at_least_one_transaction(self):
        assert len(self.txns) >= 1

    def test_all_dates_are_iso(self):
        import re

        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for t in self.txns:
            assert iso_re.match(t.date), f"Bad date: {t.date!r}"

    def test_amounts_are_nonzero(self):
        for t in self.txns:
            assert t.amount != 0.0, f"Zero amount for: {t.description!r}"

    def test_known_paypal_transaction(self):
        assert any("PAYPAL" in t.description for t in self.txns)

    def test_known_google_transaction(self):
        assert any("GOOGLE" in t.description for t in self.txns)

    def test_pago_is_positive(self):
        pagos = [t for t in self.txns if "PAGO" in t.description]
        assert any(t.amount > 0 for t in pagos)

    def test_source_is_pdf(self):
        for t in self.txns:
            assert t.source == "pdf"
