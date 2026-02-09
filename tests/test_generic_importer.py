"""Comprehensive tests for generic_importer.py - core import orchestration."""

import pytest
import pandas as pd
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict

from generic_importer import (
    parse_iso_date, parse_es_date, GenericImporter, TxnRaw,
    write_csv_atomic
)
from errors import ConfigError, ValidationError


# ===========================
# Date Parsing Tests
# ===========================

class TestParseIsoDate:
    """Test parse_iso_date function."""

    def test_parses_full_iso_datetime(self):
        """Test parsing full ISO datetime string."""
        result = parse_iso_date("2026-01-15T10:30:00")
        assert result == "2026-01-15"

    def test_parses_iso_date_only(self):
        """Test parsing ISO date without time."""
        result = parse_iso_date("2026-01-15")
        assert result == "2026-01-15"

    def test_extracts_first_10_chars_on_parse_failure(self):
        """Test fallback to first 10 characters on parse failure."""
        result = parse_iso_date("2026-01-15 invalid")
        assert result == "2026-01-15"

    def test_handles_empty_string(self):
        """Test handling of empty string."""
        result = parse_iso_date("")
        assert result == ""

    def test_handles_none(self):
        """Test handling of None input."""
        result = parse_iso_date(None)
        assert result == ""

    def test_handles_whitespace(self):
        """Test that whitespace is stripped."""
        result = parse_iso_date("  2026-01-15  ")
        assert result == "2026-01-15"

    def test_handles_iso_with_timezone(self):
        """Test parsing ISO datetime with timezone."""
        result = parse_iso_date("2026-01-15T10:30:00+00:00")
        assert result == "2026-01-15"


class TestParseEsDate:
    """Test parse_es_date function for Spanish date formats."""

    def test_parses_spanish_date_format(self):
        """Test parsing Spanish date format (dd/mmm/yy)."""
        assert parse_es_date("30/ene/26") == "2026-01-30"
        assert parse_es_date("15/feb/26") == "2026-02-15"
        assert parse_es_date("01/dic/25") == "2025-12-01"

    def test_parses_all_spanish_months(self):
        """Test all Spanish month abbreviations."""
        test_cases = [
            ("01/ene/26", "2026-01-01"),
            ("01/feb/26", "2026-02-01"),
            ("01/mar/26", "2026-03-01"),
            ("01/abr/26", "2026-04-01"),
            ("01/may/26", "2026-05-01"),
            ("01/jun/26", "2026-06-01"),
            ("01/jul/26", "2026-07-01"),
            ("01/ago/26", "2026-08-01"),
            ("01/sep/26", "2026-09-01"),
            ("01/oct/26", "2026-10-01"),
            ("01/nov/26", "2026-11-01"),
            ("01/dic/26", "2026-12-01"),
        ]
        for input_date, expected in test_cases:
            assert parse_es_date(input_date) == expected

    def test_handles_four_digit_year(self):
        """Test parsing with 4-digit year."""
        result = parse_es_date("15/mar/2026")
        assert result == "2026-03-15"

    def test_handles_single_digit_day(self):
        """Test parsing with single-digit day."""
        result = parse_es_date("5/abr/26")
        assert result == "2026-04-05"

    def test_returns_iso_format_unchanged(self):
        """Test that ISO format dates are returned unchanged."""
        result = parse_es_date("2026-01-15")
        assert result == "2026-01-15"

    def test_handles_case_insensitive_months(self):
        """Test that month abbreviations are case-insensitive."""
        assert parse_es_date("15/ENE/26") == "2026-01-15"
        assert parse_es_date("15/Ene/26") == "2026-01-15"
        assert parse_es_date("15/eNe/26") == "2026-01-15"

    def test_returns_none_for_invalid_format(self):
        """Test that None is returned for invalid formats."""
        assert parse_es_date("invalid") is None
        assert parse_es_date("15-01-2026") is None
        assert parse_es_date("2026/01/15") is None

    def test_returns_none_for_invalid_month(self):
        """Test that None is returned for invalid month abbreviation."""
        result = parse_es_date("15/xyz/26")
        assert result is None

    def test_handles_none_input(self):
        """Test handling of None input."""
        result = parse_es_date(None)
        assert result is None

    def test_handles_whitespace(self):
        """Test that whitespace is handled."""
        result = parse_es_date("  15/ene/26  ")
        assert result == "2026-01-15"


# ===========================
# TxnRaw Dataclass Tests
# ===========================

class TestTxnRaw:
    """Test TxnRaw dataclass."""

    def test_creates_basic_transaction(self):
        """Test creating a basic transaction."""
        txn = TxnRaw(date="2026-01-15", description="Test", amount=100.50)
        assert txn.date == "2026-01-15"
        assert txn.description == "Test"
        assert txn.amount == 100.50

    def test_has_default_values(self):
        """Test that default values are set correctly."""
        txn = TxnRaw(date="2026-01-15", description="Test", amount=100.0)
        assert txn.rfc == ""
        assert txn.account_hint == ""
        assert txn.source == "data"
        assert txn.page == 0
        assert txn.source_line == ""

    def test_can_override_defaults(self):
        """Test that default values can be overridden."""
        txn = TxnRaw(
            date="2026-01-15",
            description="Test",
            amount=100.0,
            rfc="RFC123",
            account_hint="credit",
            source="pdf",
            page=3,
            source_line="line content"
        )
        assert txn.rfc == "RFC123"
        assert txn.source == "pdf"
        assert txn.page == 3

    def test_is_frozen(self):
        """Test that TxnRaw is immutable (frozen)."""
        txn = TxnRaw(date="2026-01-15", description="Test", amount=100.0)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            txn.amount = 200.0


# ===========================
# GenericImporter Initialization Tests
# ===========================

class TestGenericImporterInit:
    """Test GenericImporter initialization."""

    def test_initializes_with_valid_config(self, tmp_path):
        """Test successful initialization with valid config."""
        rules_path = tmp_path / "rules.yml"
        config = {
            "banks": {
                "test_bank": {
                    "account_key": "test_account",
                    "payment_asset_key": "test_payment",
                    "card_tag": "test_card",
                    "type": "xlsx",
                    "fallback_name": "Test Bank Account"
                }
            },
            "defaults": {
                "accounts": {},
                "fallback_expense": "Expenses:Other",
                "currency": "USD"
            },
            "rules": []
        }
        rules_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        importer = GenericImporter(rules_path, "test_bank")

        assert importer.bank_id == "test_bank"
        assert importer.currency == "USD"
        assert importer.fallback_expense == "Expenses:Other"

    def test_raises_config_error_for_unknown_bank(self, tmp_path):
        """Test that ConfigError is raised for unknown bank_id."""
        rules_path = tmp_path / "rules.yml"
        config = {"banks": {}, "defaults": {}}
        rules_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        with pytest.raises(ConfigError, match="Bank ID 'unknown' not found"):
            GenericImporter(rules_path, "unknown")

    def test_loads_default_values(self, tmp_path):
        """Test that default values are loaded correctly."""
        rules_path = tmp_path / "rules.yml"
        config = {
            "banks": {
                "test": {
                    "account_key": "acc",
                    "payment_asset_key": "pay",
                    "card_tag": "card",
                    "type": "xlsx"
                }
            },
            "defaults": {
                "fallback_expense": "Expenses:Test",
                "currency": "EUR"
            }
        }
        rules_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        importer = GenericImporter(rules_path, "test")

        assert importer.fallback_expense == "Expenses:Test"
        assert importer.currency == "EUR"

    def test_compiles_rules_on_init(self, tmp_path):
        """Test that rules are compiled during initialization."""
        rules_path = tmp_path / "rules.yml"
        config = {
            "banks": {
                "test": {
                    "account_key": "acc",
                    "payment_asset_key": "pay",
                    "card_tag": "card",
                    "type": "xlsx"
                }
            },
            "defaults": {},
            "rules": [
                {"name": "TestRule", "any_regex": ["test.*"], "set": {"expense": "Expenses:Test"}}
            ]
        }
        rules_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        importer = GenericImporter(rules_path, "test")

        assert len(importer.compiled_rules) == 1
        assert importer.compiled_rules[0]["name"] == "TestRule"


# ===========================
# write_csv_atomic Tests
# ===========================

class TestWriteCsvAtomic:
    """Test write_csv_atomic function."""

    def test_writes_dataframe_to_csv(self, tmp_path):
        """Test that DataFrame is written to CSV file."""
        csv_path = tmp_path / "output.csv"
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        write_csv_atomic(df, csv_path)

        assert csv_path.exists()
        loaded_df = pd.read_csv(csv_path)
        assert len(loaded_df) == 3
        assert list(loaded_df.columns) == ["col1", "col2"]

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        csv_path = tmp_path / "nested" / "dir" / "output.csv"
        df = pd.DataFrame({"data": [1, 2]})

        write_csv_atomic(df, csv_path)

        assert csv_path.exists()
        assert csv_path.parent.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Test that existing file is overwritten."""
        csv_path = tmp_path / "output.csv"

        # Write initial data
        df1 = pd.DataFrame({"col": [1, 2]})
        write_csv_atomic(df1, csv_path)

        # Overwrite with new data
        df2 = pd.DataFrame({"col": [3, 4, 5]})
        write_csv_atomic(df2, csv_path)

        loaded_df = pd.read_csv(csv_path)
        assert len(loaded_df) == 3
        assert loaded_df["col"].tolist() == [3, 4, 5]

    def test_does_not_leave_temp_file(self, tmp_path):
        """Test that temporary file is cleaned up."""
        csv_path = tmp_path / "output.csv"
        df = pd.DataFrame({"data": [1]})

        write_csv_atomic(df, csv_path)

        # Check temp file doesn't exist
        temp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
        assert not temp_path.exists()

    def test_handles_empty_dataframe(self, tmp_path):
        """Test writing empty DataFrame."""
        csv_path = tmp_path / "empty.csv"
        df = pd.DataFrame()

        write_csv_atomic(df, csv_path)

        assert csv_path.exists()
        # Empty DataFrame creates a file with just a newline
        content = csv_path.read_text()
        assert content.strip() == ""


# ===========================
# GenericImporter Helper Methods Tests
# ===========================

class TestGenericImporterHelpers:
    """Test GenericImporter helper methods."""

    @pytest.fixture
    def importer(self, tmp_path):
        """Create a test importer instance."""
        rules_path = tmp_path / "rules.yml"
        config = {
            "banks": {
                "test": {
                    "account_key": "acc",
                    "payment_asset_key": "pay",
                    "card_tag": "test_card",
                    "type": "xlsx",
                    "fallback_name": "Test Account"
                }
            },
            "defaults": {
                "currency": "MXN",
                "accounts": {},
                "fallback_expense": "Expenses:Other"
            },
            "rules": []
        }
        rules_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return GenericImporter(rules_path, "test")

    def test_make_withdrawal(self, importer):
        """Test _make_withdrawal creates correct withdrawal row."""
        txn = TxnRaw(date="2026-01-15", description="Test purchase", amount=-100.50)
        tags = {"tag1", "tag2"}

        row = importer._make_withdrawal(txn, "Test purchase", "Expenses:Food", "Food", tags)

        assert row["type"] == "withdrawal"
        assert row["date"] == "2026-01-15"
        assert row["amount"] == "100.50"  # Absolute value
        assert row["currency_code"] == "MXN"
        assert row["description"] == "Test purchase"
        assert row["destination_name"] == "Expenses:Food"
        assert row["category_name"] == "Food"
        assert "tag1" in row["tags"]
        assert "tag2" in row["tags"]

    def test_make_transfer(self, importer):
        """Test _make_transfer creates correct transfer row."""
        txn = TxnRaw(date="2026-01-15", description="Payment", amount=500.00)
        tags = {"tag1"}

        row = importer._make_transfer(txn, "Payment", "Source Account", "Dest Account", tags, "payment")

        assert row["type"] == "transfer"
        assert row["date"] == "2026-01-15"
        assert row["amount"] == "500.00"
        assert row["source_name"] == "Source Account"
        assert row["destination_name"] == "Dest Account"
        assert row["category_name"] == ""
        assert "payment" in row["tags"]
        assert "tag1" in row["tags"]

    def test_format_unknown(self, importer):
        """Test _format_unknown formats unknown merchants correctly."""
        agg = defaultdict(lambda: {"count": 0, "total": 0.0, "examples": set()})
        agg["merchant1"]["count"] = 3
        agg["merchant1"]["total"] = 150.50
        agg["merchant1"]["examples"] = {"Example 1", "Example 2"}
        agg["merchant2"]["count"] = 1
        agg["merchant2"]["total"] = 50.00
        agg["merchant2"]["examples"] = {"Example 3"}

        result = importer._format_unknown(agg)

        assert len(result) == 2
        # Should be sorted by total descending
        assert result[0]["merchant"] == "merchant1"
        assert result[0]["count"] == 3
        assert result[0]["total"] == "150.50"
        assert "Example 1" in result[0]["examples"]


# ===========================
# Integration Test (Existing - Updated)
# ===========================

def test_process_is_deterministic_for_same_input(tmp_path: Path):
    """Existing test - verify process output is deterministic."""
    rules_path = tmp_path / "rules.yml"
    config = {
        "version": 1,
        "banks": {
            "santander_likeu": {
                "display_name": "Santander LikeU (XLSX/PDF)",
                "type": "xlsx",
                "account_key": "credit_card",
                "payment_asset_key": "payment_asset",
                "card_tag": "card:likeu",
                "fallback_name": "Liabilities:CC:Santander LikeU",
                "fallback_asset": "Assets:Santander Debito",
            }
        },
        "defaults": {
            "currency": "MXN",
            "accounts": {
                "credit_card": {"name": "Liabilities:CC:Santander LikeU", "closing_day": 15},
                "payment_asset": "Assets:Santander Debito",
            },
            "fallback_expense": "Expenses:Other:Uncategorized",
        },
        "merchant_aliases": [{"canon": "wal_mart", "any_regex": ["wal\\s*mart"]}],
        "rules": [
            {
                "name": "Groceries",
                "any_regex": ["wal\\s*mart"],
                "set": {"expense": "Expenses:Food:Groceries", "tags": ["bucket:groceries"]},
            }
        ],
    }
    rules_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    csv_path = tmp_path / "input.csv"
    pd.DataFrame(
        [
            {"date": "2026-02-02", "descripcion": "WAL MART ANTEA", "monto": -150.0},
            {"date": "2026-02-01", "descripcion": "PAGO TARJETA", "monto": 500.0},
        ]
    ).to_csv(csv_path, index=False)

    importer = GenericImporter(rules_path, "santander_likeu")

    txns_run_1 = importer.load_data(csv_path, None, False)
    rows_1, unknown_1, warnings_1 = importer.process(txns_run_1)

    txns_run_2 = importer.load_data(csv_path, None, False)
    rows_2, unknown_2, warnings_2 = importer.process(txns_run_2)

    assert rows_1 == rows_2
    assert unknown_1 == unknown_2
    assert warnings_1 == 0
    assert warnings_2 == 0
    assert any("txn:" in row["tags"] for row in rows_1)
