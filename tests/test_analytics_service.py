import pandas as pd
import pytest
import numpy as np

from services.analytics_service import calculate_categorization_stats, is_categorized


class TestIsCategorized:
    """Test the is_categorized helper function."""

    def test_valid_categorized_names(self):
        """Test that properly structured names are recognized as categorized."""
        assert is_categorized("Expenses:Food") is True
        assert is_categorized("Expenses:Food:Groceries") is True
        assert is_categorized("Assets:Cash") is True
        assert is_categorized("Liabilities:CreditCard") is True
        assert is_categorized("Income:Salary") is True

    def test_uncategorized_names_without_colon(self):
        """Test that names without colons are uncategorized."""
        assert is_categorized("PlainName") is False
        assert is_categorized("Uncategorized") is False
        assert is_categorized("SomeExpense") is False
        assert is_categorized("Food") is False

    def test_empty_and_none_values(self):
        """Test that empty strings and None are uncategorized."""
        assert is_categorized("") is False
        assert is_categorized(None) is False
        assert is_categorized(pd.NA) is False
        assert is_categorized(np.nan) is False

    def test_edge_cases(self):
        """Test edge cases and unusual inputs."""
        # Single colon only
        assert is_categorized(":") is True  # Has colon, so technically categorized

        # Colon at start
        assert is_categorized(":Food") is True

        # Colon at end
        assert is_categorized("Expenses:") is True

        # Multiple colons
        assert is_categorized("A:B:C:D") is True

    def test_whitespace_handling(self):
        """Test handling of whitespace in names."""
        # Space in name but has colon - still categorized
        assert is_categorized("Expenses: Food") is True
        assert is_categorized("Expenses :Food") is True

        # Just spaces - no colon
        assert is_categorized("   ") is False

        # Only whitespace with empty string
        assert is_categorized("") is False


class TestBasicCategorization:
    """Test basic categorization statistics."""

    def test_no_double_counting_regression(self):
        """Regression test: ensure None/empty values are not double-counted.

        This test verifies the fix for the double-counting bug where None and empty
        strings were counted in both isna()/empty checks AND the colon check.

        Before fix: uncategorized=5, categorized=-1 (bug!)
        After fix: uncategorized=3, categorized=1 (correct)
        """
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 50.0, "destination_name": "", "date": pd.Timestamp("2024-01-16")},
                {"type": "withdrawal", "amount": 75.0, "destination_name": None, "date": pd.Timestamp("2024-01-17")},
                {"type": "withdrawal", "amount": 25.0, "destination_name": "NoColon", "date": pd.Timestamp("2024-01-18")},
            ]
        )
        stats = calculate_categorization_stats(df)

        # Verify correct counting (no double-counting)
        assert stats["total"] == 4
        assert stats["categorized"] == 1  # Only "Expenses:Food"
        assert stats["uncategorized"] == 3  # Empty, None, NoColon (each counted once)

        # Verify categorized + uncategorized = total (basic sanity check)
        assert stats["categorized"] + stats["uncategorized"] == stats["total"]

    def test_calculate_categorization_stats_basic(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food:Groceries", "category_name": "Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "transfer", "amount": 200.0, "destination_name": "Assets:Cash", "category_name": "", "date": pd.Timestamp("2024-01-16")},
                {"type": "withdrawal", "amount": 50.0, "destination_name": "Unstructured Name", "category_name": "Other", "date": pd.Timestamp("2024-01-17")},  # No colon = uncategorized
            ]
        )
        stats = calculate_categorization_stats(df)
        assert stats["total"] == 3
        assert stats["uncategorized"] == 1  # Only the third entry (no colon)
        assert stats["categorized"] == 2  # First two have proper structure with colons
        assert stats["total_spent"] == 150.0
        assert stats["categories"]["Food"] == 1

    def test_handles_none_dataframe(self):
        stats = calculate_categorization_stats(None)
        assert stats is None

    def test_handles_empty_dataframe(self):
        df = pd.DataFrame()
        stats = calculate_categorization_stats(df)
        assert stats["total"] == 0
        assert stats["categorized"] == 0
        assert stats["uncategorized"] == 0
        assert stats["total_spent"] == 0.0
        assert stats["categories"] == {}

    def test_uncategorized_detection_with_unstructured_names(self):
        """Test uncategorized detection for names without colon structure."""
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},  # Categorized
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Assets:Cash", "date": pd.Timestamp("2024-01-16")},  # Categorized
                {"type": "withdrawal", "amount": 50.0, "destination_name": "PlainName", "date": pd.Timestamp("2024-01-17")},  # Uncategorized (no colon)
                {"type": "withdrawal", "amount": 75.0, "destination_name": "Another Name", "date": pd.Timestamp("2024-01-18")},  # Uncategorized (no colon)
            ]
        )
        stats = calculate_categorization_stats(df)
        assert stats["total"] == 4
        assert stats["uncategorized"] == 2  # PlainName and Another Name
        assert stats["categorized"] == 2  # Expenses:Food and Assets:Cash

    def test_uncategorized_detection_edge_cases(self):
        """Test edge cases: None and empty strings."""
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 50.0, "destination_name": "", "date": pd.Timestamp("2024-01-16")},
                {"type": "withdrawal", "amount": 75.0, "destination_name": None, "date": pd.Timestamp("2024-01-17")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "UnstructuredName", "date": pd.Timestamp("2024-01-18")},
            ]
        )
        stats = calculate_categorization_stats(df)
        assert stats["total"] == 4
        assert stats["categorized"] == 1  # Only Expenses:Food
        assert stats["uncategorized"] == 3  # Empty, None, and UnstructuredName


class TestDateFiltering:
    """Test date range filtering functionality."""

    def test_filters_by_start_date(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "category_name": "Food", "date": pd.Timestamp("2024-01-10")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "category_name": "Transport", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "category_name": "Entertainment", "date": pd.Timestamp("2024-01-30")},
            ]
        )
        stats = calculate_categorization_stats(df, start_date=pd.Timestamp("2024-01-15"))
        assert stats["total"] == 2  # Only Jan 20 and Jan 30
        assert stats["total_spent"] == 500.0

    def test_filters_by_end_date(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "category_name": "Food", "date": pd.Timestamp("2024-01-10")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "category_name": "Transport", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "category_name": "Entertainment", "date": pd.Timestamp("2024-01-30")},
            ]
        )
        stats = calculate_categorization_stats(df, end_date=pd.Timestamp("2024-01-25"))
        assert stats["total"] == 2  # Only Jan 10 and Jan 20
        assert stats["total_spent"] == 300.0

    def test_filters_by_date_range(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "category_name": "Food", "date": pd.Timestamp("2024-01-05")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "category_name": "Transport", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "category_name": "Entertainment", "date": pd.Timestamp("2024-01-25")},
                {"type": "withdrawal", "amount": 400.0, "destination_name": "Expenses:Shopping", "category_name": "Shopping", "date": pd.Timestamp("2024-02-05")},
            ]
        )
        stats = calculate_categorization_stats(
            df,
            start_date=pd.Timestamp("2024-01-10"),
            end_date=pd.Timestamp("2024-01-31")
        )
        assert stats["total"] == 2  # Only Jan 15 and Jan 25
        assert stats["total_spent"] == 500.0

    def test_returns_empty_stats_when_date_filter_yields_no_results(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
            ]
        )
        stats = calculate_categorization_stats(df, start_date=pd.Timestamp("2024-02-01"))
        assert stats["total"] == 0
        assert stats["categorized"] == 0
        assert stats["total_spent"] == 0.0


class TestPeriodFiltering:
    """Test period-based filtering using tags."""

    def test_filters_by_period_tag(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "tags": "period:2024-01", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "tags": "period:2024-02", "date": pd.Timestamp("2024-02-15")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "tags": "period:2024-02", "date": pd.Timestamp("2024-02-20")},
            ]
        )
        stats = calculate_categorization_stats(df, period="2024-02")
        assert stats["total"] == 2  # Only February transactions
        assert stats["total_spent"] == 500.0

    def test_period_filter_with_multiple_tags(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "tags": "automated,period:2024-01,reviewed", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "tags": "period:2024-01", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "tags": "automated,period:2024-02", "date": pd.Timestamp("2024-02-15")},
            ]
        )
        stats = calculate_categorization_stats(df, period="2024-01")
        assert stats["total"] == 2  # Both January transactions
        assert stats["total_spent"] == 300.0

    def test_period_filter_returns_empty_when_no_matches(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "tags": "period:2024-01", "date": pd.Timestamp("2024-01-15")},
            ]
        )
        stats = calculate_categorization_stats(df, period="2024-12")
        assert stats["total"] == 0
        assert stats["total_spent"] == 0.0

    def test_period_filter_ignored_when_date_filter_present(self):
        """Period filtering should only apply if no date range filtering is active."""
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "tags": "period:2024-01", "date": pd.Timestamp("2024-01-10")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "tags": "period:2024-01", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Entertainment", "tags": "period:2024-02", "date": pd.Timestamp("2024-02-15")},
            ]
        )
        # When start_date is provided, period should be ignored
        stats = calculate_categorization_stats(
            df,
            period="2024-01",  # This should be ignored
            start_date=pd.Timestamp("2024-01-15")
        )
        # Should use date filter, not period filter
        assert stats["total"] == 2  # Jan 20 and Feb 15 (based on date, not period tag)
        assert stats["total_spent"] == 500.0


class TestMonthlySpendingTrends:
    """Test monthly spending trends calculation."""

    def test_calculates_monthly_trends_by_category(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 150.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "date": pd.Timestamp("2024-01-25")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-02-10")},
            ]
        )
        stats = calculate_categorization_stats(df)
        trends = stats["monthly_spending_trends"]

        # Check January trends
        assert "2024-01" in trends
        assert trends["2024-01"]["Food"] == 250.0  # 100 + 150
        assert trends["2024-01"]["Transport"] == 200.0

        # Check February trends
        assert "2024-02" in trends
        assert trends["2024-02"]["Food"] == 300.0

    def test_monthly_trends_ignores_non_withdrawal_transactions(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "deposit", "amount": 500.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-16")},
                {"type": "transfer", "amount": 200.0, "destination_name": "Expenses:Transport", "date": pd.Timestamp("2024-01-17")},
            ]
        )
        stats = calculate_categorization_stats(df)
        trends = stats["monthly_spending_trends"]

        # Should only include withdrawal
        assert "2024-01" in trends
        assert trends["2024-01"]["Food"] == 100.0
        assert "Transport" not in trends["2024-01"]  # Transfer not included

    def test_monthly_trends_only_for_expenses_categories(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Assets:Savings", "date": pd.Timestamp("2024-01-16")},
                {"type": "withdrawal", "amount": 300.0, "destination_name": "Liabilities:Debt", "date": pd.Timestamp("2024-01-17")},
            ]
        )
        stats = calculate_categorization_stats(df)
        trends = stats["monthly_spending_trends"]

        # Should only include Expenses:* categories
        assert "2024-01" in trends
        assert trends["2024-01"]["Food"] == 100.0
        assert len(trends["2024-01"]) == 1  # Only Food

    def test_monthly_trends_empty_when_no_expense_withdrawals(self):
        df = pd.DataFrame(
            [
                {"type": "deposit", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "transfer", "amount": 200.0, "destination_name": "Assets:Cash", "date": pd.Timestamp("2024-01-16")},
            ]
        )
        stats = calculate_categorization_stats(df)
        trends = stats["monthly_spending_trends"]
        assert trends == {}


class TestCategorySpending:
    """Test category spending calculations."""

    def test_category_spending_sums_by_category(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 150.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-20")},
                {"type": "withdrawal", "amount": 200.0, "destination_name": "Expenses:Transport", "date": pd.Timestamp("2024-01-25")},
            ]
        )
        stats = calculate_categorization_stats(df)
        assert stats["category_spending"]["Food"] == 250.0
        assert stats["category_spending"]["Transport"] == 200.0

    def test_category_counts_transactions(self):
        df = pd.DataFrame(
            [
                {"type": "withdrawal", "amount": 100.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-15")},
                {"type": "withdrawal", "amount": 150.0, "destination_name": "Expenses:Food", "date": pd.Timestamp("2024-01-20")},
                {"type": "deposit", "amount": 200.0, "destination_name": "Expenses:Transport", "date": pd.Timestamp("2024-01-25")},
            ]
        )
        stats = calculate_categorization_stats(df)
        assert stats["categories"]["Food"] == 2  # Two transactions
        assert stats["categories"]["Transport"] == 1  # One transaction (even though it's deposit)
