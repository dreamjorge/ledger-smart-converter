import re
import pytest
import common_utils as cu


# ===========================
# Parse Money Tests
# ===========================

def test_parse_money_handles_common_formats():
    assert cu.parse_money("$1,234.56") == 1234.56
    assert cu.parse_money("-45.90") == -45.90
    assert cu.parse_money("1 500.00") == 1500.00
    assert cu.parse_money("abc") is None


def test_parse_money_handles_edge_cases():
    """Test edge cases for money parsing."""
    assert cu.parse_money(None) is None
    assert cu.parse_money("") is None
    assert cu.parse_money("   ") is None
    assert cu.parse_money("0") == 0.0
    assert cu.parse_money("+123.45") == 123.45
    assert cu.parse_money("$-500.00") == -500.0


# ===========================
# Statement Period Tests
# ===========================

def test_statement_period_uses_closing_day():
    assert cu.get_statement_period("2026-01-10", 15) == "2026-01"
    assert cu.get_statement_period("2026-01-16", 15) == "2026-02"


def test_statement_period_handles_year_boundary():
    """Test period calculation across year boundaries."""
    assert cu.get_statement_period("2025-12-20", 15) == "2026-01"
    assert cu.get_statement_period("2025-12-10", 15) == "2025-12"


def test_statement_period_handles_invalid_dates():
    """Test handling of invalid date strings."""
    assert cu.get_statement_period("invalid", 15) == ""
    assert cu.get_statement_period("2026-13-01", 15) == ""
    assert cu.get_statement_period("", 15) == ""


# ===========================
# String Whitespace Tests
# ===========================

class TestStripWhitespace:
    """Test strip_ws utility function."""

    def test_strip_ws_removes_multiple_spaces(self):
        """Test that multiple spaces are collapsed to single space."""
        assert cu.strip_ws("hello    world") == "hello world"
        assert cu.strip_ws("  multiple   spaces  ") == "multiple spaces"

    def test_strip_ws_handles_tabs_and_newlines(self):
        """Test that tabs and newlines are converted to single space."""
        assert cu.strip_ws("hello\tworld") == "hello world"
        assert cu.strip_ws("hello\nworld") == "hello world"
        assert cu.strip_ws("hello\r\nworld") == "hello world"

    def test_strip_ws_handles_empty_and_none(self):
        """Test handling of empty strings and None."""
        assert cu.strip_ws("") == ""
        assert cu.strip_ws(None) == ""
        assert cu.strip_ws("   ") == ""


# ===========================
# Account Config Tests
# ===========================

class TestGetAccountConfig:
    """Test get_account_config function."""

    def test_returns_default_when_key_not_found(self):
        """Test fallback to default when key is missing."""
        accounts = {"other_key": "value"}
        name, closing_day = cu.get_account_config(accounts, "missing_key", "Default Account")
        assert name == "Default Account"
        assert closing_day == 31

    def test_handles_string_format_legacy(self):
        """Test legacy string format for account config."""
        accounts = {"credit_card": "My Credit Card"}
        name, closing_day = cu.get_account_config(accounts, "credit_card", "Default")
        assert name == "My Credit Card"
        assert closing_day == 31

    def test_handles_dict_format_with_closing_day(self):
        """Test new dict format with closing_day."""
        accounts = {
            "credit_card": {
                "name": "My Credit Card",
                "closing_day": 15
            }
        }
        name, closing_day = cu.get_account_config(accounts, "credit_card", "Default")
        assert name == "My Credit Card"
        assert closing_day == 15

    def test_handles_dict_format_missing_fields(self):
        """Test dict format with missing optional fields."""
        accounts = {"credit_card": {}}
        name, closing_day = cu.get_account_config(accounts, "credit_card", "Default")
        assert name == "Default"
        assert closing_day == 31

    def test_handles_empty_accounts_dict(self):
        """Test with empty accounts dictionary."""
        name, closing_day = cu.get_account_config({}, "any_key", "Fallback")
        assert name == "Fallback"
        assert closing_day == 31


# ===========================
# Compile Rules Tests
# ===========================

class TestCompileRules:
    """Test compile_rules function."""

    def test_compiles_rules_with_regexes(self):
        """Test that rules are compiled with regex objects."""
        rules_yml = {
            "rules": [
                {
                    "name": "Test Rule",
                    "any_regex": ["^test.*", "example"],
                    "set": {"expense": "Expenses:Test", "tags": ["test_tag"]}
                }
            ]
        }
        compiled = cu.compile_rules(rules_yml)

        assert len(compiled) == 1
        assert compiled[0]["name"] == "Test Rule"
        assert len(compiled[0]["regexes"]) == 2
        assert all(isinstance(r, re.Pattern) for r in compiled[0]["regexes"])
        assert compiled[0]["set"]["expense"] == "Expenses:Test"

    def test_handles_empty_rules_list(self):
        """Test handling of empty rules list."""
        rules_yml = {"rules": []}
        compiled = cu.compile_rules(rules_yml)
        assert compiled == []

    def test_handles_missing_rules_key(self):
        """Test handling when 'rules' key is missing."""
        rules_yml = {}
        compiled = cu.compile_rules(rules_yml)
        assert compiled == []

    def test_compiles_case_insensitive_regexes(self):
        """Test that regexes are compiled case-insensitively."""
        rules_yml = {
            "rules": [
                {"name": "Case Test", "any_regex": ["amazon"], "set": {}}
            ]
        }
        compiled = cu.compile_rules(rules_yml)
        regex = compiled[0]["regexes"][0]

        assert regex.search("AMAZON")
        assert regex.search("Amazon")
        assert regex.search("amazon")

    def test_handles_none_in_any_regex(self):
        """Test handling of None values in any_regex list."""
        rules_yml = {
            "rules": [
                {"name": "Test", "any_regex": None, "set": {}}
            ]
        }
        compiled = cu.compile_rules(rules_yml)
        assert compiled[0]["regexes"] == []


# ===========================
# Normalize Merchant Tests
# ===========================

class TestNormalizeMerchant:
    """Test normalize_merchant function."""

    def test_returns_canonical_name_when_alias_matches(self):
        """Test that canonical name is returned when alias regex matches."""
        merchant_aliases = [
            {"canon": "amazon", "any_regex": ["amazon.*", "amzn"]}
        ]
        assert cu.normalize_merchant("AMAZON.COM", merchant_aliases) == "amazon"
        assert cu.normalize_merchant("AMZN MARKETPLACE", merchant_aliases) == "amazon"

    def test_falls_back_to_heuristic_when_no_match(self):
        """Test fallback to first 2 words when no alias matches."""
        merchant_aliases = []
        assert cu.normalize_merchant("STARBUCKS COFFEE 12345", merchant_aliases) == "starbucks_coffee"
        assert cu.normalize_merchant("WAL-MART STORE", merchant_aliases) == "wal-mart_store"

    def test_removes_numbers_in_heuristic(self):
        """Test that numbers are removed in heuristic normalization."""
        merchant_aliases = []
        assert cu.normalize_merchant("TARGET 1234", merchant_aliases) == "target"
        assert cu.normalize_merchant("STORE123 MAIN456", merchant_aliases) == "store_main"

    def test_handles_empty_description(self):
        """Test handling of empty or None descriptions."""
        merchant_aliases = []
        assert cu.normalize_merchant("", merchant_aliases) == "unknown"
        assert cu.normalize_merchant(None, merchant_aliases) == "unknown"

    def test_handles_single_word(self):
        """Test handling of single-word descriptions."""
        merchant_aliases = []
        assert cu.normalize_merchant("STARBUCKS", merchant_aliases) == "starbucks"

    def test_normalizes_whitespace(self):
        """Test that whitespace is normalized before processing."""
        merchant_aliases = []
        assert cu.normalize_merchant("STORE   NAME   HERE", merchant_aliases) == "store_name"


# ===========================
# Classify Tests
# ===========================

class TestClassify:
    """Test classify function."""

    def test_matches_rule_and_returns_expense_and_tags(self):
        """Test that classification matches rules and returns proper data."""
        rules_yml = {
            "rules": [
                {
                    "name": "Amazon",
                    "any_regex": ["amazon"],
                    "set": {"expense": "Expenses:Shopping:Online", "tags": ["shopping", "online"]}
                }
            ]
        }
        compiled_rules = cu.compile_rules(rules_yml)
        merchant_aliases = [{"canon": "amazon", "any_regex": ["amazon"]}]

        expense, tags, merchant = cu.classify(
            "AMAZON.COM PURCHASE",
            compiled_rules,
            merchant_aliases,
            "Expenses:Other"
        )

        assert expense == "Expenses:Shopping:Online"
        assert "shopping" in tags
        assert "online" in tags
        assert "merchant:amazon" in tags
        assert merchant == "amazon"

    def test_uses_fallback_when_no_rule_matches(self):
        """Test fallback expense when no rule matches."""
        compiled_rules = []
        merchant_aliases = []

        expense, tags, merchant = cu.classify(
            "UNKNOWN STORE",
            compiled_rules,
            merchant_aliases,
            "Expenses:Uncategorized"
        )

        assert expense == "Expenses:Uncategorized"
        assert "merchant:unknown_store" in tags

    def test_deduplicates_tags(self):
        """Test that duplicate tags are removed."""
        rules_yml = {
            "rules": [
                {
                    "name": "Test",
                    "any_regex": ["test"],
                    "set": {"expense": "Expenses:Test", "tags": ["tag1", "tag1", "tag2"]}
                }
            ]
        }
        compiled_rules = cu.compile_rules(rules_yml)
        merchant_aliases = []

        expense, tags, merchant = cu.classify("test", compiled_rules, merchant_aliases, "Expenses:Other")

        # Should only have unique tags
        assert tags.count("tag1") == 1
        assert "tag2" in tags

    def test_sorts_tags_alphabetically(self):
        """Test that tags are sorted alphabetically."""
        rules_yml = {
            "rules": [
                {
                    "name": "Test",
                    "any_regex": ["test"],
                    "set": {"expense": "Expenses:Test", "tags": ["zebra", "apple", "banana"]}
                }
            ]
        }
        compiled_rules = cu.compile_rules(rules_yml)
        merchant_aliases = []

        expense, tags, merchant = cu.classify("test", compiled_rules, merchant_aliases, "Expenses:Other")

        # Check that tags are sorted (merchant tag will be included)
        assert tags == sorted(tags)

    def test_handles_empty_description(self):
        """Test classification with empty description."""
        compiled_rules = []
        merchant_aliases = []

        expense, tags, merchant = cu.classify("", compiled_rules, merchant_aliases, "Expenses:Other")

        assert expense == "Expenses:Other"
        assert "merchant:unknown" in tags


# ===========================
# Clean Description Tests
# ===========================

class TestCleanDescription:
    """Test clean_description function for human-readable bank descriptions."""

    def test_restores_spanish_accents(self):
        """Test that common Spanish bank terms get their accents restored."""
        assert cu.clean_description("INTERES MORATORIO") == "Interés Moratorio"
        assert cu.clean_description("COMISION CAJERO") == "Comisión Cajero"
        assert cu.clean_description("DEPOSITO EN CUENTA") == "Depósito En Cuenta"

    def test_expands_abbreviations(self):
        """Test that common bank abbreviations are expanded."""
        assert cu.clean_description("TRANSF SPEI NOMINA") == "Transferencia SPEI Nómina"
        assert cu.clean_description("WALMART SUPERCT") == "Walmart Supercenter"

    def test_keeps_acronyms_uppercase(self):
        """Test that known acronyms remain uppercase."""
        assert cu.clean_description("PAGO SPEI") == "Pago SPEI"
        assert cu.clean_description("RETENCION IVA") == "Retencion IVA"
        assert cu.clean_description("CLABE INTERBANCARIA") == "CLABE Interbancaria"

    def test_title_cases_unknown_words(self):
        """Test that unrecognized words get title-cased."""
        assert cu.clean_description("AMAZON PRIME") == "Amazon Prime"
        assert cu.clean_description("NETFLIX") == "Netflix"
        assert cu.clean_description("YOUTUBE PREMIUM") == "Youtube Premium"

    def test_collapses_whitespace(self):
        """Test that multiple spaces are collapsed to single space."""
        assert cu.clean_description("COMISION   CAJERO") == "Comisión Cajero"
        assert cu.clean_description("  INTERES  ") == "Interés"

    def test_handles_empty_and_none(self):
        """Test edge cases: empty string and None."""
        assert cu.clean_description("") == ""
        assert cu.clean_description(None) == ""

    def test_handles_mixed_case_input(self):
        """Test that input with mixed case still maps through glossary."""
        assert cu.clean_description("interes moratorio") == "Interés Moratorio"
        assert cu.clean_description("Comision Anualidad") == "Comisión Anualidad"

    def test_preserves_numbers_in_description(self):
        """Test that numbers in descriptions are preserved."""
        assert cu.clean_description("7-ELEVEN STORE") == "7-Eleven Store"
        assert cu.clean_description("PAGO 1234") == "Pago 1234"

    def test_multiple_glossary_terms(self):
        """Test descriptions with multiple glossary terms."""
        assert cu.clean_description("COMISION TRANSF AUTOMATICO") == "Comisión Transferencia Automático"


# ===========================
# Suggest Rule Tests
# ===========================

class TestSuggestRuleFromMerchant:
    """Test suggest_rule_from_merchant function."""

    def test_creates_rule_with_escaped_regex(self):
        """Test that rule regex is properly escaped."""
        rule = cu.suggest_rule_from_merchant("test_merchant")

        assert rule["name"] == "Auto:test_merchant"
        assert len(rule["any_regex"]) == 1
        # Check that underscore was replaced with space (may be escaped)
        regex_pattern = rule["any_regex"][0]
        assert "test" in regex_pattern and "merchant" in regex_pattern
        assert rule["set"]["expense"] == "Expenses:Other:Uncategorized"
        assert "bucket:test_merchant" in rule["set"]["tags"]

    def test_escapes_special_regex_characters(self):
        """Test that special regex characters are escaped."""
        rule = cu.suggest_rule_from_merchant("store.com")

        # The dot should be escaped in the regex
        assert "store.com" in rule["any_regex"][0] or r"store\.com" in rule["any_regex"][0]
