# -*- coding: utf-8 -*-
"""Unit tests for UI Service.

Verifies that the UI-agnostic data formatting and chart creation logic
produces expected data structures and visuals.
"""
import pytest
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services import ui_service

@pytest.fixture
def mock_t():
    """Mock translation function."""
    def t(key, **kwargs):
        return f"translated_{key}"
    return t

@pytest.fixture
def mock_tc():
    """Mock category translation function."""
    def tc(key):
        return f"cat_{key}"
    return tc

@pytest.fixture
def sample_stats():
    """Sample statistics dictionary for testing."""
    return {
        "total": 100,
        "categorized": 80,
        "uncategorized": 20,
        "coverage_pct": 80.0,
        "category_populated": 75,
        "category_pct": 75.0,
        "total_spent": 1234.56,
        "type_counts": {"withdrawal": 90, "deposit": 10},
        "categories": {"Food": 40, "Bills": 20, "Transport": 20},
        "category_spending": {"Food": 500.0, "Bills": 400.0, "Transport": 334.56},
        "monthly_spending_trends": {
            "2024-01": {"Food": 250.0, "Bills": 200.0},
            "2024-02": {"Food": 250.0, "Bills": 200.0, "Transport": 334.56}
        }
    }

class TestFormatting:
    """Tests for basic formatting functions."""
    
    def test_format_currency(self):
        assert ui_service.format_currency(1234.56) == "$1,234.56"
        assert ui_service.format_currency(0) == "$0.00"
        assert ui_service.format_currency(-10.5) == "$-10.50"

    def test_format_percentage(self):
        assert ui_service.format_percentage(85.432) == "85.4%"
        assert ui_service.format_percentage(0) == "0.0%"
        assert ui_service.format_percentage(100) == "100.0%"

class TestFigureGeneration:
    """Tests for Plotly figure generation functions."""

    def test_get_coverage_pie_fig(self, sample_stats, mock_t):
        fig = ui_service.get_coverage_pie_fig(sample_stats, mock_t)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == "pie"
        assert "translated_metric_categorized" in fig.data[0].labels
        assert 80 in fig.data[0].values

    def test_get_type_bar_fig(self, sample_stats, mock_t):
        fig = ui_service.get_type_bar_fig(sample_stats, mock_t)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "bar"

    def test_get_type_bar_fig_empty(self, mock_t):
        fig = ui_service.get_type_bar_fig({"type_counts": {}}, mock_t)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_get_spending_share_fig(self, sample_stats, mock_t, mock_tc):
        fig = ui_service.get_spending_share_fig(sample_stats, mock_t, mock_tc)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"
        assert "cat_Food" in fig.data[0].labels
        assert 500.0 in fig.data[0].values

    def test_get_category_count_fig(self, sample_stats, mock_tc):
        fig = ui_service.get_category_count_fig(sample_stats, mock_tc)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"
        assert "cat_Food" in fig.data[0].y
        assert 40 in fig.data[0].x

    def test_get_monthly_trends_fig(self, sample_stats, mock_t, mock_tc):
        fig = ui_service.get_monthly_trends_fig(sample_stats, mock_t, mock_tc)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "scatter"  # Line charts are scatter with mode='lines'
        # Plotly Express encodes traces by category
        categories_in_chart = [trace.name for trace in fig.data]
        assert "cat_Food" in categories_in_chart
        assert "cat_Bills" in categories_in_chart

    def test_get_bank_comparison_fig(self, sample_stats, mock_tc):
        stats_hsbc = sample_stats.copy()
        stats_hsbc["category_spending"] = {"Food": 300.0, "Transport": 500.0}
        
        fig = ui_service.get_bank_comparison_fig(sample_stats, stats_hsbc, mock_tc)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Santander and HSBC traces
        assert fig.data[0].name == "Santander"
        assert fig.data[1].name == "HSBC"
        assert "cat_Food" in fig.data[0].x
