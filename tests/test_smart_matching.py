"""Tests for smart_matching.py - fuzzy merchant matching utilities."""

import pytest
from smart_matching import find_similar_merchants, normalize_for_matching


class TestFindSimilarMerchants:
    """Test find_similar_merchants fuzzy matching function."""

    def test_finds_exact_match(self):
        """Test that exact matches return 100 score."""
        target = "STARBUCKS"
        existing = ["STARBUCKS", "WALMART", "TARGET"]

        results = find_similar_merchants(target, existing, threshold=70)

        assert len(results) > 0
        assert results[0][0] == "STARBUCKS"
        assert results[0][1] == 100.0

    def test_finds_close_matches_above_threshold(self):
        """Test that similar merchants above threshold are found."""
        target = "STARBUCKS COFFEE"
        existing = ["STARBUCKS", "STARBUCKS CORP", "WALMART", "TARGET"]

        results = find_similar_merchants(target, existing, threshold=70)

        # Should find STARBUCKS and STARBUCKS CORP
        assert len(results) >= 2
        merchant_names = [m for m, _ in results]
        assert "STARBUCKS" in merchant_names or "STARBUCKS CORP" in merchant_names

    def test_filters_matches_below_threshold(self):
        """Test that matches below threshold are excluded."""
        target = "AMAZON"
        existing = ["WALMART", "TARGET", "COSTCO"]

        results = find_similar_merchants(target, existing, threshold=80)

        # Should find no good matches
        assert len(results) == 0

    def test_handles_different_word_order(self):
        """Test token_sort_ratio handles word order differences."""
        target = "WALMART SUPERCENTER"
        existing = ["SUPERCENTER WALMART", "WALMART", "TARGET"]

        results = find_similar_merchants(target, existing, threshold=70)

        # Should match despite word order difference
        assert len(results) > 0
        assert any("WALMART" in m for m, _ in results)

    def test_returns_up_to_5_matches(self):
        """Test that at most 5 matches are returned."""
        target = "STORE"
        existing = [
            "STORE A", "STORE B", "STORE C",
            "STORE D", "STORE E", "STORE F",
            "STORE G", "STORE H"
        ]

        results = find_similar_merchants(target, existing, threshold=50)

        # Should limit to 5 matches
        assert len(results) <= 5

    def test_sorts_results_by_score_descending(self):
        """Test that results are sorted by score in descending order."""
        target = "WALMART"
        existing = ["WALMART", "WALMART SUPER", "WALMART STORE", "TARGET"]

        results = find_similar_merchants(target, existing, threshold=60)

        # Scores should be in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_handles_empty_target(self):
        """Test handling of empty target string."""
        results = find_similar_merchants("", ["WALMART", "TARGET"], threshold=70)
        assert results == []

    def test_handles_none_target(self):
        """Test handling of None target."""
        results = find_similar_merchants(None, ["WALMART", "TARGET"], threshold=70)
        assert results == []

    def test_handles_empty_merchants_list(self):
        """Test handling of empty existing merchants list."""
        results = find_similar_merchants("WALMART", [], threshold=70)
        assert results == []

    def test_handles_none_merchants_list(self):
        """Test handling of None existing merchants list."""
        results = find_similar_merchants("WALMART", None, threshold=70)
        assert results == []

    def test_custom_threshold_works(self):
        """Test that custom threshold parameter is respected."""
        target = "WALMART"
        existing = ["WALMART STORE", "WAL-MART", "TARGET"]

        # Higher threshold should return fewer results
        results_high = find_similar_merchants(target, existing, threshold=90)
        results_low = find_similar_merchants(target, existing, threshold=50)

        assert len(results_low) >= len(results_high)

    def test_handles_special_characters(self):
        """Test matching with special characters."""
        target = "WAL-MART"
        existing = ["WALMART", "WAL MART", "TARGET"]

        results = find_similar_merchants(target, existing, threshold=70)

        # Should find WALMART despite punctuation difference
        assert len(results) > 0

    def test_case_sensitivity(self):
        """Test that matching works with same case."""
        target = "walmart"
        existing = ["walmart", "target"]

        results = find_similar_merchants(target, existing, threshold=50)

        # Should find exact match
        assert len(results) > 0
        assert results[0][0] == "walmart"
        assert results[0][1] == 100.0

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        target = "CAFÉ STARBUCKS"
        existing = ["CAFE STARBUCKS", "STARBUCKS", "WALMART"]

        results = find_similar_merchants(target, existing, threshold=70)

        # Should find close matches
        assert len(results) > 0


class TestNormalizeForMatching:
    """Test normalize_for_matching text normalization function."""

    def test_converts_to_lowercase(self):
        """Test that text is converted to lowercase."""
        assert normalize_for_matching("WALMART") == "walmart"
        assert normalize_for_matching("WalMart") == "walmart"

    def test_removes_numbers(self):
        """Test that numbers are removed."""
        assert normalize_for_matching("WALMART 12345") == "walmart"
        assert normalize_for_matching("STORE 123 LOCATION 456") == "store location"

    def test_collapses_multiple_spaces(self):
        """Test that multiple spaces are collapsed to single space."""
        assert normalize_for_matching("WALMART   STORE") == "walmart store"
        assert normalize_for_matching("A    B     C") == "a b c"

    def test_strips_leading_trailing_whitespace(self):
        """Test that leading and trailing whitespace is removed."""
        assert normalize_for_matching("  WALMART  ") == "walmart"
        assert normalize_for_matching("\tSTORE\n") == "store"

    def test_handles_empty_string(self):
        """Test handling of empty string."""
        assert normalize_for_matching("") == ""

    def test_handles_none(self):
        """Test handling of None input."""
        assert normalize_for_matching(None) == ""

    def test_handles_whitespace_only(self):
        """Test handling of whitespace-only string."""
        assert normalize_for_matching("   ") == ""
        assert normalize_for_matching("\t\n  ") == ""

    def test_handles_numbers_only(self):
        """Test handling of strings with only numbers."""
        assert normalize_for_matching("12345") == ""
        assert normalize_for_matching("123 456 789") == ""

    def test_preserves_special_characters(self):
        """Test that special characters (except numbers) are preserved."""
        assert normalize_for_matching("WAL-MART") == "wal-mart"
        assert normalize_for_matching("CAFÉ") == "café"
        assert normalize_for_matching("STORE!@#") == "store!@#"

    def test_handles_mixed_content(self):
        """Test normalization of realistic merchant names."""
        assert normalize_for_matching("WALMART SUPERCENTER #1234") == "walmart supercenter #"
        assert normalize_for_matching("AMAZON.COM SERVICES 9999") == "amazon.com services"
        assert normalize_for_matching("STARBUCKS COFFEE 12345") == "starbucks coffee"

    def test_handles_unicode_characters(self):
        """Test handling of Unicode characters."""
        assert normalize_for_matching("CAFÉ MÜNCHEN") == "café münchen"
        assert normalize_for_matching("日本語123") == "日本語"

    def test_idempotent_normalization(self):
        """Test that normalizing twice gives same result."""
        text = "WALMART 123 STORE"
        normalized_once = normalize_for_matching(text)
        normalized_twice = normalize_for_matching(normalized_once)

        assert normalized_once == normalized_twice

    def test_combined_with_find_similar(self):
        """Test that normalization improves matching accuracy."""
        target = normalize_for_matching("WALMART STORE 12345")
        existing = [
            normalize_for_matching("WALMART SUPERCENTER 6789"),
            normalize_for_matching("TARGET STORE 1111"),
        ]

        results = find_similar_merchants(target, existing, threshold=60)

        # After normalization, WALMART should match better
        assert len(results) > 0
