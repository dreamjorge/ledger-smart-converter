# -*- coding: utf-8 -*-
"""Comprehensive test suite for analytics UI components.

Tests UI component rendering logic, data transformation, and edge cases
for analytics dashboards without requiring a running Streamlit app.
"""
import pandas as pd
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import module under test
from ui.components.analytics_components import (
    render_metrics,
    render_charts,
    render_category_deep_dive,
    render_monthly_spending_trends,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_streamlit():
    """Mock streamlit module."""
    with patch("ui.components.analytics_components.st") as mock_st:
        # Mock columns to return the requested number of columns
        def columns_side_effect(n):
            cols = [Mock() for _ in range(n)]
            for col in cols:
                col.__enter__ = Mock(return_value=col)
                col.__exit__ = Mock(return_value=False)
            return cols

        mock_st.columns.side_effect = columns_side_effect

        yield mock_st


@pytest.fixture
def mock_plotly():
    """Mock plotly express."""
    with patch("ui.components.analytics_components.px") as mock_px:
        # Mock figure objects
        mock_px.pie.return_value = Mock(update_layout=Mock(), update_traces=Mock())
        mock_px.bar.return_value = Mock(update_layout=Mock())
        mock_px.line.return_value = Mock(update_layout=Mock())
        yield mock_px


@pytest.fixture
def translation_func():
    """Mock translation function."""
    def t(key):
        return f"translated_{key}"
    return t


@pytest.fixture
def category_translation_func():
    """Mock category translation function."""
    def tc(key):
        return f"cat_{key}"
    return tc


@pytest.fixture
def basic_stats():
    """Basic statistics dictionary."""
    return {
        "total": 100,
        "total_spent": 5000.50,
        "categorized": 85,
        "uncategorized": 15,
        "coverage_pct": 85.0,
        "category_populated": 80,
        "category_pct": 80.0,
        "type_counts": {
            "withdrawal": 90,
            "deposit": 10,
        },
        "category_spending": {
            "groceries": 1500.00,
            "transport": 800.50,
            "entertainment": 600.00,
        },
        "categories": {
            "groceries": 40,
            "transport": 25,
            "entertainment": 20,
        },
        "monthly_spending_trends": {
            "2024-01": {
                "groceries": 500.00,
                "transport": 200.00,
            },
            "2024-02": {
                "groceries": 600.00,
                "transport": 300.00,
            },
        },
    }


# ============================================================================
# Tests for render_metrics
# ============================================================================

class TestRenderMetrics:
    """Tests for metrics card rendering."""

    def test_render_metrics_basic(self, mock_streamlit, translation_func, basic_stats):
        """Render basic metrics."""
        render_metrics(translation_func, basic_stats)

        # Verify columns created
        mock_streamlit.columns.assert_called_once_with(5)

        # Verify metrics called
        assert mock_streamlit.metric.call_count == 5

    def test_render_metrics_all_fields(self, mock_streamlit, translation_func, basic_stats):
        """Verify all metric fields are rendered correctly."""
        render_metrics(translation_func, basic_stats)

        calls = mock_streamlit.metric.call_args_list

        # Check each metric call
        assert any("translated_metric_total_txns" in str(c) for c in calls)
        assert any("translated_metric_total_spent" in str(c) for c in calls)
        assert any("translated_metric_categorized" in str(c) for c in calls)
        assert any("5,000.50" in str(c) for c in calls)

    def test_render_metrics_zero_values(self, mock_streamlit, translation_func):
        """Handle zero values gracefully."""
        stats = {
            "total": 0,
            "total_spent": 0.0,
            "categorized": 0,
            "coverage_pct": 0.0,
            "category_populated": 0,
            "category_pct": 0.0,
            "type_counts": {},
        }

        render_metrics(translation_func, stats)
        assert mock_streamlit.metric.call_count == 5

    def test_render_metrics_missing_withdrawal_type(self, mock_streamlit, translation_func):
        """Handle missing withdrawal count in type_counts."""
        stats = {
            "total": 50,
            "total_spent": 1000.0,
            "categorized": 40,
            "coverage_pct": 80.0,
            "category_populated": 35,
            "category_pct": 70.0,
            "type_counts": {"deposit": 10},  # No withdrawal
        }

        render_metrics(translation_func, stats)
        # Should default to 0 for missing withdrawal
        assert mock_streamlit.metric.call_count == 5


# ============================================================================
# Tests for render_charts
# ============================================================================

class TestRenderCharts:
    """Tests for chart rendering."""

    def test_render_charts_creates_pie_chart(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Create pie chart for coverage."""
        render_charts(translation_func, basic_stats, category_translation_func)

        # Verify pie chart created
        mock_plotly.pie.assert_called()
        call_kwargs = mock_plotly.pie.call_args[1]
        assert "names" in call_kwargs
        assert "values" in call_kwargs

    def test_render_charts_creates_bar_chart_when_type_counts(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Create bar chart when type counts exist."""
        render_charts(translation_func, basic_stats, category_translation_func)

        # Verify bar chart created
        assert mock_plotly.bar.call_count >= 1

    def test_render_charts_skips_bar_chart_when_empty_type_counts(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Skip bar chart when type_counts is empty."""
        stats = {
            "categorized": 50,
            "uncategorized": 10,
            "type_counts": {},  # Empty
            "category_spending": {},
        }

        render_charts(translation_func, stats, category_translation_func)

        # Pie chart created, but no bar chart
        mock_plotly.pie.assert_called()

    def test_render_charts_spending_share_pie(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Create spending share pie chart."""
        render_charts(translation_func, basic_stats, category_translation_func)

        # Should create 2 pie charts (coverage + spending)
        assert mock_plotly.pie.call_count == 2

    def test_render_charts_no_spending_share_when_empty(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Don't create spending share chart when category_spending is empty."""
        stats = {
            "categorized": 50,
            "uncategorized": 10,
            "type_counts": {"withdrawal": 50},
            "category_spending": {},  # Empty
        }

        render_charts(translation_func, stats, category_translation_func)

        # Only 1 pie chart (coverage)
        assert mock_plotly.pie.call_count == 1

    def test_render_charts_uses_custom_colors(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Verify custom color schemes are applied."""
        render_charts(translation_func, basic_stats, category_translation_func)

        # Check pie chart has custom colors
        pie_kwargs = mock_plotly.pie.call_args_list[0][1]
        assert "color_discrete_sequence" in pie_kwargs


# ============================================================================
# Tests for render_category_deep_dive
# ============================================================================

class TestRenderCategoryDeepDive:
    """Tests for category deep dive rendering."""

    def test_render_category_deep_dive_with_data(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Render category deep dive with data."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Verify subheader called
        mock_streamlit.subheader.assert_called()

        # Verify 2 bar charts created (count + spending)
        assert mock_plotly.bar.call_count == 2

        # Verify dataframe displayed
        mock_streamlit.dataframe.assert_called_once()

    def test_render_category_deep_dive_creates_dataframe(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Create DataFrame with category data."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Check dataframe call
        df_call = mock_streamlit.dataframe.call_args[0][0]
        assert isinstance(df_call, pd.DataFrame)
        assert "Category" in df_call.columns
        assert "Transactions" in df_call.columns
        assert "Total Spent" in df_call.columns

    def test_render_category_deep_dive_limits_to_top_10(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Limit charts to top 10 categories."""
        stats = {
            "categories": {f"cat_{i}": i * 10 for i in range(20)},
            "category_spending": {f"cat_{i}": i * 100.0 for i in range(20)},
        }

        render_category_deep_dive(translation_func, category_translation_func, stats)

        # Verify bar charts called (should limit data to 10 items)
        assert mock_plotly.bar.call_count == 2

    def test_render_category_deep_dive_no_render_when_empty(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Don't render when both categories and spending are empty."""
        stats = {
            "categories": {},
            "category_spending": {},
        }

        render_category_deep_dive(translation_func, category_translation_func, stats)

        # Nothing should be rendered
        mock_streamlit.subheader.assert_not_called()
        mock_plotly.bar.assert_not_called()

    def test_render_category_deep_dive_translates_categories(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Apply category translation to labels."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Check that category translation was used
        df_call = mock_streamlit.dataframe.call_args[0][0]
        assert all("cat_" in cat for cat in df_call["Category"])


# ============================================================================
# Tests for render_monthly_spending_trends
# ============================================================================

class TestRenderMonthlySpendingTrends:
    """Tests for monthly spending trends rendering."""

    def test_render_monthly_trends_with_data(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Render monthly trends with data."""
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Verify line chart created
        mock_plotly.line.assert_called_once()

        # Verify chart displayed
        mock_streamlit.plotly_chart.assert_called()

    def test_render_monthly_trends_creates_dataframe(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Transform monthly data into DataFrame."""
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Verify line chart received DataFrame
        line_call = mock_plotly.line.call_args[0][0]
        assert isinstance(line_call, pd.DataFrame)
        assert "Month" in line_call.columns
        assert "Category" in line_call.columns
        assert "Amount" in line_call.columns

    def test_render_monthly_trends_formats_dates(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Format dates to YYYY-MM."""
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Check line chart data
        line_call = mock_plotly.line.call_args[0][0]

        # Months should be formatted as YYYY-MM strings
        assert all("-" in str(m) for m in line_call["Month"])

    def test_render_monthly_trends_sorts_by_date(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Sort data by date chronologically."""
        stats = {
            "monthly_spending_trends": {
                "2024-03": {"groceries": 300.0},
                "2024-01": {"groceries": 100.0},
                "2024-02": {"groceries": 200.0},
            }
        }

        render_monthly_spending_trends(translation_func, category_translation_func, stats)

        # Verify data was sorted
        line_call = mock_plotly.line.call_args[0][0]
        months = line_call["Month"].tolist()
        assert months == sorted(months)

    def test_render_monthly_trends_shows_info_when_empty(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Show info message when no trends data."""
        stats = {
            "monthly_spending_trends": {}
        }

        render_monthly_spending_trends(translation_func, category_translation_func, stats)

        # Should not create chart
        mock_plotly.line.assert_not_called()

    def test_render_monthly_trends_no_render_when_missing(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Don't render when monthly_spending_trends is empty dict."""
        stats = {"monthly_spending_trends": {}}

        render_monthly_spending_trends(translation_func, category_translation_func, stats)

        # Should not create chart for empty data
        mock_plotly.line.assert_not_called()

    def test_render_monthly_trends_translates_categories(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """Apply category translation to chart labels."""
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Check translated categories in DataFrame
        line_call = mock_plotly.line.call_args[0][0]
        assert all("cat_" in str(cat) for cat in line_call["Category"])


# ============================================================================
# Integration Tests
# ============================================================================

class TestAnalyticsComponentsIntegration:
    """Integration tests for analytics components."""

    def test_all_components_work_together(self, mock_streamlit, mock_plotly, translation_func, category_translation_func, basic_stats):
        """All components can render without errors."""
        render_metrics(translation_func, basic_stats)
        render_charts(translation_func, basic_stats, category_translation_func)
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Verify all components executed
        assert mock_streamlit.metric.call_count > 0
        assert mock_plotly.pie.call_count > 0
        assert mock_plotly.bar.call_count > 0
        assert mock_plotly.line.call_count > 0

    def test_components_handle_minimal_stats(self, mock_streamlit, mock_plotly, translation_func, category_translation_func):
        """Handle minimal statistics gracefully."""
        minimal_stats = {
            "total": 0,
            "total_spent": 0.0,
            "categorized": 0,
            "uncategorized": 0,
            "coverage_pct": 0.0,
            "category_populated": 0,
            "category_pct": 0.0,
            "type_counts": {},
            "category_spending": {},
            "categories": {},
            "monthly_spending_trends": {},
        }

        # Should not raise errors
        render_metrics(translation_func, minimal_stats)
        render_charts(translation_func, minimal_stats, category_translation_func)
        render_category_deep_dive(translation_func, category_translation_func, minimal_stats)
        render_monthly_spending_trends(translation_func, category_translation_func, minimal_stats)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
