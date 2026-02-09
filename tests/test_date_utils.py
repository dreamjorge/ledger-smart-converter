# -*- coding: utf-8 -*-
"""Comprehensive test suite for unified date parsing utilities.

Tests all date parsing functions across different formats and edge cases.
"""
from pathlib import Path
import pytest
from datetime import datetime

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from date_utils import (
    parse_spanish_date,
    parse_mexican_date,
    parse_iso_date,
    MONTHS_ES,
)


# ============================================================================
# Tests for parse_spanish_date
# ============================================================================

class TestParseSpanishDate:
    """Tests for Spanish date format parsing (DD/MMM/YY or DD/MMM/YYYY)."""

    def test_parse_day_month_two_digit_year(self):
        """Parse DD/MMM/YY format."""
        assert parse_spanish_date("30/ene/26") == "2026-01-30"
        assert parse_spanish_date("15/dic/24") == "2024-12-15"

    def test_parse_day_month_four_digit_year(self):
        """Parse DD/MMM/YYYY format."""
        assert parse_spanish_date("15/ene/2024") == "2024-01-15"
        assert parse_spanish_date("31/dic/2023") == "2023-12-31"

    def test_parse_full_month_name(self):
        """Parse with full month name."""
        assert parse_spanish_date("10/enero/2024") == "2024-01-10"
        assert parse_spanish_date("25/diciembre/2024") == "2024-12-25"

    def test_parse_all_months(self):
        """Test all month abbreviations."""
        months = [
            ("ene", "01"), ("feb", "02"), ("mar", "03"), ("abr", "04"),
            ("may", "05"), ("jun", "06"), ("jul", "07"), ("ago", "08"),
            ("sep", "09"), ("oct", "10"), ("nov", "11"), ("dic", "12")
        ]
        for month_abbr, month_num in months:
            result = parse_spanish_date(f"15/{month_abbr}/2024")
            assert result == f"2024-{month_num}-15", f"Failed for {month_abbr}"

    def test_parse_mixed_case(self):
        """Case-insensitive month parsing."""
        assert parse_spanish_date("15/ENE/2024") == "2024-01-15"
        assert parse_spanish_date("15/Ene/2024") == "2024-01-15"
        assert parse_spanish_date("15/eNe/2024") == "2024-01-15"

    def test_parse_with_whitespace(self):
        """Parse with leading/trailing whitespace."""
        assert parse_spanish_date("  15/ene/2024  ") == "2024-01-15"

    def test_parse_already_iso(self):
        """If already ISO format, return as-is."""
        assert parse_spanish_date("2024-01-15") == "2024-01-15"
        assert parse_spanish_date("2023-12-31") == "2023-12-31"

    def test_parse_invalid_month(self):
        """Invalid month returns None."""
        assert parse_spanish_date("15/xyz/2024") is None
        assert parse_spanish_date("15/invalid/2024") is None

    def test_parse_none_input(self):
        """None input returns None."""
        assert parse_spanish_date(None) is None

    def test_parse_empty_string(self):
        """Empty string returns None."""
        assert parse_spanish_date("") is None

    def test_parse_invalid_format(self):
        """Invalid format returns None."""
        assert parse_spanish_date("invalid") is None
        assert parse_spanish_date("15-01-2024") is None

    def test_parse_single_digit_day(self):
        """Single digit day is zero-padded."""
        assert parse_spanish_date("5/ene/2024") == "2024-01-05"


# ============================================================================
# Tests for parse_mexican_date
# ============================================================================

class TestParseMexicanDate:
    """Tests for Mexican date format parsing."""

    def test_parse_day_month_abbrev_with_year(self):
        """Parse 'DD MMM' format with year parameter."""
        assert parse_mexican_date("12 ENE", year=2024) == "2024-01-12"
        assert parse_mexican_date("25 DIC", year=2024) == "2024-12-25"

    def test_parse_day_month_no_space(self):
        """Parse 'DDMMM' format without space."""
        assert parse_mexican_date("15FEB", year=2024) == "2024-02-15"

    def test_parse_full_month_name(self):
        """Parse with full month name."""
        assert parse_mexican_date("10 ENERO", year=2024) == "2024-01-10"
        assert parse_mexican_date("20 DICIEMBRE", year=2024) == "2024-12-20"

    def test_parse_dd_mm_yy_slash(self):
        """Parse 'DD/MM/YY' format."""
        assert parse_mexican_date("12/01/24") == "2024-01-12"
        assert parse_mexican_date("31/12/23") == "2023-12-31"

    def test_parse_dd_mm_yyyy_slash(self):
        """Parse 'DD/MM/YYYY' format."""
        assert parse_mexican_date("15/06/2024") == "2024-06-15"
        assert parse_mexican_date("01/01/2023") == "2023-01-01"

    def test_parse_dd_mm_yy_dash(self):
        """Parse 'DD-MM-YY' format."""
        assert parse_mexican_date("20-03-24") == "2024-03-20"

    def test_parse_dd_mm_yyyy_dash(self):
        """Parse 'DD-MM-YYYY' format."""
        assert parse_mexican_date("05-11-2024") == "2024-11-05"

    def test_parse_iso_format(self):
        """Parse already ISO format 'YYYY-MM-DD'."""
        assert parse_mexican_date("2024-01-15") == "2024-01-15"
        assert parse_mexican_date("2023/12/31") == "2023-12-31"

    def test_parse_all_months(self):
        """Test all month abbreviations."""
        months = [
            ("ENE", "01"), ("FEB", "02"), ("MAR", "03"), ("ABR", "04"),
            ("MAY", "05"), ("JUN", "06"), ("JUL", "07"), ("AGO", "08"),
            ("SEP", "09"), ("OCT", "10"), ("NOV", "11"), ("DIC", "12")
        ]
        for month_abbr, month_num in months:
            result = parse_mexican_date(f"15 {month_abbr}", year=2024)
            assert result == f"2024-{month_num}-15", f"Failed for {month_abbr}"

    def test_parse_ocr_variant_set(self):
        """Test OCR variant 'SET' for September."""
        assert parse_mexican_date("15 SET", year=2024) == "2024-09-15"

    def test_parse_invalid_day(self):
        """Invalid day returns None."""
        assert parse_mexican_date("32 ENE", year=2024) is None
        assert parse_mexican_date("00 FEB", year=2024) is None
        assert parse_mexican_date("32/01/2024") is None

    def test_parse_invalid_month(self):
        """Invalid month returns None."""
        assert parse_mexican_date("15 XYZ", year=2024) is None
        assert parse_mexican_date("15/13/2024") is None

    def test_parse_none_input(self):
        """None input returns None."""
        assert parse_mexican_date(None) is None

    def test_parse_empty_string(self):
        """Empty string returns None."""
        assert parse_mexican_date("") is None

    def test_parse_non_string_input(self):
        """Non-string input returns None."""
        assert parse_mexican_date(12345) is None

    def test_parse_invalid_format(self):
        """Unrecognized format returns None."""
        assert parse_mexican_date("invalid date") is None
        assert parse_mexican_date("ABC/DEF/GHI") is None

    def test_parse_default_year(self):
        """When no year provided, use current year."""
        current_year = datetime.now().year
        result = parse_mexican_date("15 ENE")
        assert result == f"{current_year}-01-15"

    def test_parse_two_digit_year_2000s(self):
        """Two-digit years assumed to be 2000s."""
        assert parse_mexican_date("15/01/24") == "2024-01-15"
        assert parse_mexican_date("15/01/99") == "2099-01-15"

    def test_parse_boundary_days(self):
        """Test boundary days (1st and 31st)."""
        assert parse_mexican_date("01/01/2024") == "2024-01-01"
        assert parse_mexican_date("31/12/2024") == "2024-12-31"

    def test_parse_leap_year(self):
        """Test February 29 on leap year."""
        assert parse_mexican_date("29/02/2024") == "2024-02-29"


# ============================================================================
# Tests for parse_iso_date
# ============================================================================

class TestParseISODate:
    """Tests for ISO 8601 date parsing."""

    def test_parse_valid_iso_date(self):
        """Parse valid ISO format."""
        assert parse_iso_date("2024-01-15") == "2024-01-15"
        assert parse_iso_date("2023-12-31") == "2023-12-31"

    def test_parse_invalid_iso_format(self):
        """Invalid ISO format returns None."""
        assert parse_iso_date("24-01-15") is None
        assert parse_iso_date("2024/01/15") is None
        assert parse_iso_date("15-01-2024") is None

    def test_parse_invalid_date(self):
        """Valid format but invalid date returns None."""
        assert parse_iso_date("2024-13-01") is None  # Month 13
        assert parse_iso_date("2024-02-30") is None  # Feb 30

    def test_parse_none_input(self):
        """None input returns None."""
        assert parse_iso_date(None) is None

    def test_parse_empty_string(self):
        """Empty string returns None."""
        assert parse_iso_date("") is None

    def test_parse_non_string_input(self):
        """Non-string input returns None."""
        assert parse_iso_date(12345) is None

    def test_parse_with_whitespace(self):
        """Parse with leading/trailing whitespace."""
        assert parse_iso_date("  2024-01-15  ") == "2024-01-15"

    def test_parse_leap_year_valid(self):
        """Test valid leap year date."""
        assert parse_iso_date("2024-02-29") == "2024-02-29"

    def test_parse_leap_year_invalid(self):
        """Test invalid leap year date."""
        assert parse_iso_date("2023-02-29") is None  # 2023 not leap year


# ============================================================================
# Integration Tests
# ============================================================================

class TestDateUtilsIntegration:
    """Integration tests for date utilities."""

    def test_spanish_and_mexican_compatibility(self):
        """Both parsers handle overlapping formats."""
        # ISO format works for both
        assert parse_spanish_date("2024-01-15") == "2024-01-15"
        assert parse_mexican_date("2024-01-15") == "2024-01-15"

    def test_months_mapping_completeness(self):
        """Verify months mapping is complete."""
        # Should have all 12 months
        month_numbers = set(MONTHS_ES.values())
        expected = {f"{i:02d}" for i in range(1, 13)}
        assert expected.issubset(month_numbers)

    def test_round_trip_parsing(self):
        """Parse and validate round-trip consistency."""
        original = "2024-01-15"

        # All parsers should handle ISO and return same value
        assert parse_iso_date(original) == original
        assert parse_spanish_date(original) == original
        assert parse_mexican_date(original) == original


# ============================================================================
# Edge Cases
# ============================================================================

class TestDateUtilsEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_all_days_of_month(self):
        """Test all valid days (1-31)."""
        for day in range(1, 32):
            date_str = f"{day:02d}/ene/2024"
            result = parse_spanish_date(date_str)
            assert result is not None
            assert result.endswith(f"-{day:02d}")

    def test_year_boundaries(self):
        """Test different year formats."""
        # 2-digit years
        assert parse_spanish_date("15/ene/00") == "2000-01-15"
        assert parse_spanish_date("15/ene/99") == "2099-01-15"

        # 4-digit years
        assert parse_spanish_date("15/ene/2000") == "2000-01-15"
        assert parse_spanish_date("15/ene/2099") == "2099-01-15"

    def test_unicode_handling(self):
        """Test Unicode characters in input."""
        # Should handle without errors
        assert parse_spanish_date("15/ene/2024") == "2024-01-15"

    def test_extreme_whitespace(self):
        """Test extreme whitespace scenarios."""
        assert parse_spanish_date("   15/ene/2024   ") == "2024-01-15"
        assert parse_mexican_date("   15 ENE   ", year=2024) == "2024-01-15"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
