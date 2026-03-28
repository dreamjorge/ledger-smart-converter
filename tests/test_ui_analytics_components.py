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
def mock_ui_service():
    """Mock ui_service."""
    with patch("ui.components.analytics_components.ui_service") as mock_service:
        # Create a mock figure that has data
        mock_fig = Mock()
        mock_fig.data = [Mock()]
        
        # Mock figure objects
        mock_service.get_coverage_pie_fig.return_value = mock_fig
        mock_service.get_type_bar_fig.return_value = mock_fig
        mock_service.get_spending_share_fig.return_value = mock_fig
        mock_service.get_category_count_fig.return_value = mock_fig
        mock_service.get_category_spending_fig.return_value = mock_fig
        mock_service.get_monthly_trends_fig.return_value = mock_fig
        
        # Mock formatting
        mock_service.format_currency.side_effect = lambda x: f"${x:,.2f}"
        mock_service.format_percentage.side_effect = lambda x: f"{x:.1f}%"
        
        yield mock_service


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

    def test_render_metrics_basic(self, mock_streamlit, mock_ui_service, translation_func, basic_stats):
        """Render basic metrics."""
        render_metrics(translation_func, basic_stats)

        # Verify columns created
        mock_streamlit.columns.assert_called_once_with(5)

        # Verify metrics called
        assert mock_streamlit.metric.call_count == 5

    def test_render_metrics_all_fields(self, mock_streamlit, mock_ui_service, translation_func, basic_stats):
        """Verify all metric fields are rendered correctly."""
        render_metrics(translation_func, basic_stats)

        calls = mock_streamlit.metric.call_args_list

        # Check each metric call
        assert any("translated_metric_total_txns" in str(c) for c in calls)
        assert any("translated_metric_total_spent" in str(c) for c in calls)
        assert any("translated_metric_categorized" in str(c) for c in calls)
        assert any("5,000.50" in str(c) for c in calls)

    def test_render_metrics_zero_values(self, mock_streamlit, mock_ui_service, translation_func):
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

    def test_render_metrics_missing_withdrawal_type(self, mock_streamlit, mock_ui_service, translation_func):
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

    def test_render_charts_creates_pie_chart(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Create pie chart for coverage."""
        render_charts(translation_func, basic_stats, category_translation_func)

        mock_ui_service.get_coverage_pie_fig.assert_called_once()
        assert mock_streamlit.plotly_chart.call_count >= 1

    def test_render_charts_creates_bar_chart_when_type_counts(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Create bar chart when type counts exist."""
        render_charts(translation_func, basic_stats, category_translation_func)

        mock_ui_service.get_type_bar_fig.assert_called_once()
        # Coverage + Type + Spending Share = 3 charts
        assert mock_streamlit.plotly_chart.call_count == 3

    def test_render_charts_skips_bar_chart_when_empty_type_counts(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
        """Skip bar chart when type_counts is empty."""
        stats = {
            "categorized": 50,
            "uncategorized": 10,
            "type_counts": {},  # Empty
            "category_spending": {},
        }
        
        # Simulate ui_service returning an empty figure
        empty_fig = Mock()
        empty_fig.data = []
        mock_ui_service.get_type_bar_fig.return_value = empty_fig

        render_charts(translation_func, stats, category_translation_func)

        mock_ui_service.get_type_bar_fig.assert_called_once()
        # Only coverage pie chart is plotted with plotly_chart
        assert mock_streamlit.plotly_chart.call_count == 1

    def test_render_charts_spending_share_pie(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Create spending share pie chart."""
        render_charts(translation_func, basic_stats, category_translation_func)

        mock_ui_service.get_spending_share_fig.assert_called_once()

    def test_render_charts_no_spending_share_when_empty(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
        """Don't create spending share chart when category_spending is empty."""
        stats = {
            "categorized": 50,
            "uncategorized": 10,
            "type_counts": {"withdrawal": 50},
            "category_spending": {},  # Empty
        }

        render_charts(translation_func, stats, category_translation_func)

        mock_ui_service.get_spending_share_fig.assert_not_called()
        # Pie chart + Bar chart
        assert mock_streamlit.plotly_chart.call_count == 2


# ============================================================================
# Tests for render_category_deep_dive
# ============================================================================

class TestRenderCategoryDeepDive:
    """Tests for category deep dive rendering."""

    def test_render_category_deep_dive_with_data(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Render category deep dive with data."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Verify subheader called
        mock_streamlit.subheader.assert_called()

        # Verify 2 bar charts created (count + spending)
        mock_ui_service.get_category_count_fig.assert_called_once()
        mock_ui_service.get_category_spending_fig.assert_called_once()

        # Verify dataframe displayed
        mock_streamlit.dataframe.assert_called_once()

    def test_render_category_deep_dive_creates_dataframe(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Create DataFrame with category data."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Check dataframe call
        df_call = mock_streamlit.dataframe.call_args[0][0]
        assert isinstance(df_call, pd.DataFrame)
        assert "Category" in df_call.columns
        assert "Transactions" in df_call.columns
        assert "Total Spent" in df_call.columns

    def test_render_category_deep_dive_translates_categories(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Apply category translation to labels."""
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)

        # Check that category translation was used
        df_call = mock_streamlit.dataframe.call_args[0][0]
        assert all("cat_" in cat for cat in df_call["Category"])

    def test_render_category_deep_dive_no_render_when_empty(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
        """Don't render when both categories and spending are empty."""
        stats = {
            "categories": {},
            "category_spending": {},
        }

        render_category_deep_dive(translation_func, category_translation_func, stats)

        # Nothing should be rendered
        mock_streamlit.subheader.assert_not_called()


# ============================================================================
# Tests for render_monthly_spending_trends
# ============================================================================

class TestRenderMonthlySpendingTrends:
    """Tests for monthly spending trends rendering."""

    def test_render_monthly_trends_with_data(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """Render monthly trends with data."""
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Verify chart created and displayed
        mock_ui_service.get_monthly_trends_fig.assert_called_once()
        mock_streamlit.plotly_chart.assert_called()

    def test_render_monthly_trends_shows_info_when_empty(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
        """Show info message when no trends data."""
        stats = {
            "monthly_spending_trends": {"2024-01": {}}
        }

        render_monthly_spending_trends(translation_func, category_translation_func, stats)

        # Information called because trends_df may be empty
        mock_streamlit.info.assert_called()
        mock_ui_service.get_monthly_trends_fig.assert_not_called()

    def test_render_monthly_trends_no_render_when_missing(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
        """Don't render when monthly_spending_trends is empty dict."""
        stats = {"monthly_spending_trends": {}}

        render_monthly_spending_trends(translation_func, category_translation_func, stats)

        # Should not create chart for empty data
        mock_ui_service.get_monthly_trends_fig.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestAnalyticsComponentsIntegration:
    """Integration tests for analytics components."""

    def test_all_components_work_together(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func, basic_stats):
        """All components can render without errors."""
        render_metrics(translation_func, basic_stats)
        render_charts(translation_func, basic_stats, category_translation_func)
        render_category_deep_dive(translation_func, category_translation_func, basic_stats)
        render_monthly_spending_trends(translation_func, category_translation_func, basic_stats)

        # Verify all components executed
        assert mock_streamlit.metric.call_count > 0
        assert mock_streamlit.plotly_chart.call_count > 0

    def test_components_handle_minimal_stats(self, mock_streamlit, mock_ui_service, translation_func, category_translation_func):
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
        
        # Simulate empty fig
        empty_fig = Mock()
        empty_fig.data = []
        mock_ui_service.get_type_bar_fig.return_value = empty_fig

        # Should not raise errors
        render_metrics(translation_func, minimal_stats)
        render_charts(translation_func, minimal_stats, category_translation_func)
        render_category_deep_dive(translation_func, category_translation_func, minimal_stats)
        render_monthly_spending_trends(translation_func, category_translation_func, minimal_stats)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
