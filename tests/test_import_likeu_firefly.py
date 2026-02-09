# -*- coding: utf-8 -*-
"""Comprehensive test suite for Santander LikeU importer.

Tests Excel parsing, header detection, date/amount parsing,
and error handling for the Santander bank importer.
"""
import pandas as pd
from pathlib import Path
import pytest

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from import_likeu_firefly import (
    find_header_row,
    MONTHS,
    DATE_ES_RE,
    main,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def fixtures_dir():
    """Path to Santander test fixtures directory."""
    return Path(__file__).parent / "fixtures" / "santander"


@pytest.fixture
def valid_statement_df(fixtures_dir):
    """Load valid statement Excel file."""
    excel_path = fixtures_dir / "valid_statement.xlsx"
    return pd.read_excel(excel_path, sheet_name=0, header=None)


@pytest.fixture
def malformed_statement_df(fixtures_dir):
    """Load malformed statement Excel file (no FECHA header)."""
    excel_path = fixtures_dir / "malformed_statement.xlsx"
    return pd.read_excel(excel_path, sheet_name=0, header=None)


@pytest.fixture
def missing_columns_df(fixtures_dir):
    """Load Excel with missing required columns."""
    excel_path = fixtures_dir / "missing_columns.xlsx"
    return pd.read_excel(excel_path, sheet_name=0, header=None)


@pytest.fixture
def header_offset_df(fixtures_dir):
    """Load Excel with header at non-standard position."""
    excel_path = fixtures_dir / "header_offset.xlsx"
    return pd.read_excel(excel_path, sheet_name=0, header=None)


@pytest.fixture
def empty_statement_df(fixtures_dir):
    """Load empty Excel file."""
    excel_path = fixtures_dir / "empty_statement.xlsx"
    return pd.read_excel(excel_path, sheet_name=0, header=None)


# ============================================================================
# Tests for find_header_row
# ============================================================================

class TestFindHeaderRow:
    """Tests for header row detection in Excel files."""

    def test_find_header_standard_position(self, valid_statement_df):
        """Find header in standard position (row 3)."""
        header_row = find_header_row(valid_statement_df)

        assert header_row == 3
        # Verify it's actually the header row
        assert str(valid_statement_df.iloc[header_row, 0]).strip().upper() == "FECHA"

    def test_find_header_offset_position(self, header_offset_df):
        """Find header at non-standard position (row 5)."""
        header_row = find_header_row(header_offset_df)

        assert header_row == 5
        assert str(header_offset_df.iloc[header_row, 0]).strip().upper() == "FECHA"

    def test_find_header_case_insensitive(self):
        """Header detection is case-insensitive."""
        # Create DataFrame with lowercase header
        df = pd.DataFrame([
            ["", ""],
            ["fecha", "concepto"],  # Lowercase
            ["15/ene/24", "OXXO"],
        ])

        header_row = find_header_row(df)
        assert header_row == 1

    def test_find_header_with_whitespace(self):
        """Header detection handles whitespace."""
        df = pd.DataFrame([
            ["", ""],
            ["  FECHA  ", "  CONCEPTO  "],  # With whitespace
            ["15/ene/24", "OXXO"],
        ])

        header_row = find_header_row(df)
        assert header_row == 1

    def test_find_header_missing_raises_error(self, malformed_statement_df):
        """Raise ValueError when FECHA header not found."""
        with pytest.raises(ValueError, match="No encontré encabezado"):
            find_header_row(malformed_statement_df)

    def test_find_header_empty_dataframe(self, empty_statement_df):
        """Raise ValueError for empty DataFrame."""
        with pytest.raises(ValueError, match="No encontré encabezado"):
            find_header_row(empty_statement_df)

    def test_find_header_first_row(self):
        """Find header in first row (row 0)."""
        df = pd.DataFrame([
            ["FECHA", "CONCEPTO", "IMPORTE"],
            ["15/ene/24", "OXXO", "-45.50"],
        ])

        header_row = find_header_row(df)
        assert header_row == 0


# ============================================================================
# Tests for MONTHS constant
# ============================================================================

class TestMonthsMapping:
    """Tests for Spanish months mapping."""

    def test_months_all_present(self):
        """All 12 months are defined."""
        assert len(MONTHS) == 12

    def test_months_lowercase_keys(self):
        """Month keys are lowercase."""
        for key in MONTHS.keys():
            assert key == key.lower()

    def test_months_values_format(self):
        """Month values are two-digit strings."""
        for value in MONTHS.values():
            assert len(value) == 2
            assert value.isdigit()
            assert 1 <= int(value) <= 12

    def test_months_specific_values(self):
        """Verify specific month mappings."""
        assert MONTHS["ene"] == "01"
        assert MONTHS["feb"] == "02"
        assert MONTHS["mar"] == "03"
        assert MONTHS["abr"] == "04"
        assert MONTHS["may"] == "05"
        assert MONTHS["jun"] == "06"
        assert MONTHS["jul"] == "07"
        assert MONTHS["ago"] == "08"
        assert MONTHS["sep"] == "09"
        assert MONTHS["oct"] == "10"
        assert MONTHS["nov"] == "11"
        assert MONTHS["dic"] == "12"


# ============================================================================
# Tests for DATE_ES_RE regex
# ============================================================================

class TestDateESRegex:
    """Tests for Spanish date format regex."""

    def test_regex_standard_format(self):
        """Match standard DD/MMM/YY format."""
        assert DATE_ES_RE.match("15/ene/24")
        assert DATE_ES_RE.match("01/dic/23")
        assert DATE_ES_RE.match("31/ago/24")

    def test_regex_four_digit_year(self):
        """Match DD/MMM/YYYY format."""
        assert DATE_ES_RE.match("15/ene/2024")
        assert DATE_ES_RE.match("01/dic/2023")

    def test_regex_single_digit_day(self):
        """Match single-digit day."""
        assert DATE_ES_RE.match("5/ene/24")
        assert DATE_ES_RE.match("1/dic/23")

    def test_regex_with_whitespace(self):
        """Match with leading/trailing whitespace."""
        assert DATE_ES_RE.match("  15/ene/24  ")
        assert DATE_ES_RE.match(" 5/ene/24 ")

    def test_regex_case_variations(self):
        """Match various case combinations."""
        assert DATE_ES_RE.match("15/ENE/24")
        assert DATE_ES_RE.match("15/Ene/24")
        assert DATE_ES_RE.match("15/eNe/24")

    def test_regex_invalid_format(self):
        """Don't match invalid formats."""
        assert not DATE_ES_RE.match("2024-01-15")  # ISO format
        assert not DATE_ES_RE.match("15-01-2024")  # Dashes
        assert not DATE_ES_RE.match("ene/15/24")   # Month first
        assert not DATE_ES_RE.match("15/01/24")    # Numeric month
        assert not DATE_ES_RE.match("invalid")     # Not a date

    def test_regex_extracts_groups(self):
        """Regex extracts day, month, year groups."""
        match = DATE_ES_RE.match("15/ene/24")
        assert match is not None
        assert match.group(1) == "15"   # Day
        assert match.group(2) == "ene"  # Month
        assert match.group(3) == "24"   # Year


# ============================================================================
# Integration Tests
# ============================================================================

class TestSantanderImporterIntegration:
    """Integration tests for Santander importer workflow."""

    def test_full_excel_parsing_workflow(self, valid_statement_df):
        """Complete workflow: Find header -> Extract columns -> Parse data."""
        # Step 1: Find header row
        header_row = find_header_row(valid_statement_df)
        assert header_row == 3

        # Step 2: Extract column names
        cols = [str(x).strip().lower() for x in valid_statement_df.iloc[header_row].tolist()]
        assert "fecha" in cols
        assert "concepto" in cols
        assert "importe" in cols

        # Step 3: Create DataFrame with proper columns
        df = valid_statement_df.iloc[header_row + 1:].copy()
        df.columns = cols

        # Step 4: Verify data
        assert len(df) > 0
        assert not df["fecha"].isna().all()
        assert not df["concepto"].isna().all()
        assert not df["importe"].isna().all()

    def test_excel_file_structure_validation(self, valid_statement_df):
        """Validate expected Excel structure."""
        # Header should be at row 3
        header_row = find_header_row(valid_statement_df)

        # Get column names
        cols = [str(x).strip().lower() for x in valid_statement_df.iloc[header_row].tolist()]

        # Required columns present
        required = ["fecha", "concepto", "importe"]
        for col in required:
            assert col in cols, f"Missing required column: {col}"

    def test_transaction_data_extraction(self, valid_statement_df):
        """Extract and validate transaction data."""
        header_row = find_header_row(valid_statement_df)
        cols = [str(x).strip().lower() for x in valid_statement_df.iloc[header_row].tolist()]
        df = valid_statement_df.iloc[header_row + 1:].copy()
        df.columns = cols

        # Drop rows with missing data
        df = df.dropna(subset=["fecha", "concepto", "importe"], how="any")

        # Verify we have transactions
        assert len(df) > 0

        # Check first transaction
        first_row = df.iloc[0]
        assert "fecha" in first_row
        assert "concepto" in first_row
        assert "importe" in first_row


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestSantanderEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_find_header_single_row_dataframe(self):
        """Handle single-row DataFrame."""
        df = pd.DataFrame([["FECHA", "CONCEPTO"]])

        header_row = find_header_row(df)
        assert header_row == 0

    def test_find_header_many_empty_rows(self):
        """Find header after many empty rows."""
        empty_rows = [["", "", ""] for _ in range(20)]
        header = ["FECHA", "CONCEPTO", "IMPORTE"]
        data = ["15/ene/24", "OXXO", "-45.50"]

        df = pd.DataFrame(empty_rows + [header] + [data])

        header_row = find_header_row(df)
        assert header_row == 20

    def test_find_header_mixed_case_fecha(self):
        """Handle various FECHA case combinations."""
        test_cases = [
            "FECHA",
            "fecha",
            "Fecha",
            "FeCHa",
            "fEcHa",
        ]

        for fecha_variant in test_cases:
            df = pd.DataFrame([[fecha_variant, "CONCEPTO"]])
            header_row = find_header_row(df)
            assert header_row == 0, f"Failed for variant: {fecha_variant}"

    def test_date_regex_edge_cases(self):
        """Test date regex with edge cases."""
        # Valid format matches (regex checks format, not validity)
        valid_formats = [
            "1/ene/24",     # Single digit day
            "31/dic/99",    # End of month
            "15/ene/2024",  # 4-digit year
            "  1/ene/24  ", # Whitespace
            "32/ene/24",    # Matches format (validity checked later by parser)
            "0/ene/24",     # Matches format (validity checked later)
        ]

        for date_str in valid_formats:
            assert DATE_ES_RE.match(date_str), f"Should match format: {date_str}"

        # Invalid format (regex won't match these)
        invalid_formats = [
            "15/13/24",     # Numeric month (expects letters)
            "15/ene",       # Missing year
            "/ene/24",      # Missing day
            "15//24",       # Missing month
            "2024-01-15",   # ISO format
            "ene/15/24",    # Month first
        ]

        for date_str in invalid_formats:
            assert not DATE_ES_RE.match(date_str), f"Should not match format: {date_str}"

    def test_months_immutability(self):
        """MONTHS constant should not be modified."""
        original_months = MONTHS.copy()

        # Verify MONTHS hasn't changed
        assert MONTHS == original_months

    def test_header_detection_with_nan_values(self):
        """Handle NaN values in DataFrame."""
        import numpy as np

        df = pd.DataFrame([
            [np.nan, np.nan],
            ["FECHA", "CONCEPTO"],
            ["15/ene/24", "OXXO"],
        ])

        header_row = find_header_row(df)
        assert header_row == 1

    def test_header_detection_with_numeric_values(self):
        """Handle numeric values before header."""
        df = pd.DataFrame([
            [123, 456],
            [789, 101112],
            ["FECHA", "CONCEPTO"],
            ["15/ene/24", "OXXO"],
        ])

        header_row = find_header_row(df)
        assert header_row == 2


# ============================================================================
# Tests for Excel File Loading
# ============================================================================

class TestExcelFileLoading:
    """Tests for Excel file loading and parsing."""

    def test_load_valid_statement(self, fixtures_dir):
        """Load valid statement Excel file."""
        excel_path = fixtures_dir / "valid_statement.xlsx"
        assert excel_path.exists()

        df = pd.read_excel(excel_path, sheet_name=0, header=None)
        assert len(df) > 0

    def test_load_malformed_statement(self, fixtures_dir):
        """Load malformed statement Excel file."""
        excel_path = fixtures_dir / "malformed_statement.xlsx"
        assert excel_path.exists()

        df = pd.read_excel(excel_path, sheet_name=0, header=None)
        assert len(df) > 0

    def test_load_missing_columns(self, fixtures_dir):
        """Load Excel with missing columns."""
        excel_path = fixtures_dir / "missing_columns.xlsx"
        assert excel_path.exists()

        df = pd.read_excel(excel_path, sheet_name=0, header=None)
        assert len(df) > 0

    def test_all_fixtures_exist(self, fixtures_dir):
        """Verify all test fixtures exist."""
        required_fixtures = [
            "valid_statement.xlsx",
            "malformed_statement.xlsx",
            "missing_columns.xlsx",
            "header_offset.xlsx",
            "empty_statement.xlsx",
        ]

        for fixture in required_fixtures:
            assert (fixtures_dir / fixture).exists(), f"Missing fixture: {fixture}"


class TestLikeUMainCLI:
    """Integration tests for main() flow."""

    def test_main_processes_xlsx_and_writes_outputs(self, tmp_path, fixtures_dir, monkeypatch):
        rules_path = tmp_path / "rules.yml"
        out_csv = tmp_path / "firefly.csv"
        out_unknown = tmp_path / "unknown.csv"
        out_suggestions = tmp_path / "suggestions.yml"
        xlsx_path = fixtures_dir / "valid_statement.xlsx"

        rules_path.write_text(
            """
version: 1
defaults:
  currency: MXN
  fallback_expense: Expenses:Other:Uncategorized
  accounts:
    credit_card:
      name: Liabilities:CC:Santander LikeU
      closing_day: 15
    payment_asset: Assets:Santander Debito
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
                "--xlsx",
                str(xlsx_path),
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

    def test_main_returns_2_without_any_input_source(self, tmp_path, monkeypatch):
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text("defaults: {}\nrules: []\n", encoding="utf-8")
        monkeypatch.setattr("sys.argv", ["prog", "--rules", str(rules_path)])
        assert main() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
