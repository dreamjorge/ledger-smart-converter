# -*- coding: utf-8 -*-
"""Shared analytics components for dashboard rendering.

This module contains reusable UI components for rendering analytics
dashboards, charts, and metrics to eliminate code duplication.
"""
import pandas as pd
import streamlit as st
from services import ui_service


def render_metrics(t, stats):
    """Render metrics cards with transaction statistics.

    Args:
        t: Translation function
        stats: Dictionary with statistics (total, total_spent, categorized, etc.)
    """
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(t("metric_total_txns"), stats["total"], help=t("help_total_txns"))
    with col2:
        st.metric(t("metric_total_spent"), ui_service.format_currency(stats["total_spent"]), help=t("help_total_spent"))
    with col3:
        st.metric(t("metric_categorized"), f"{stats['categorized']} ({ui_service.format_percentage(stats['coverage_pct'])})", help=t("help_coverage"))
    with col4:
        st.metric(t("metric_category_field"), f"{stats['category_populated']} ({ui_service.format_percentage(stats['category_pct'])})")
    with col5:
        st.metric(t("metric_withdrawals"), stats["type_counts"].get("withdrawal", 0))


def render_charts(t, stats, tc, key_suffix: str = ""):
    """Render analytics charts (coverage, types, spending share).

    Args:
        t: Translation function
        stats: Dictionary with statistics
        tc: Translation category function
        key_suffix: Unique suffix for widget keys
    """
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        fig = ui_service.get_coverage_pie_fig(stats, t)
        st.plotly_chart(fig, width="stretch", key=f"coverage_pie_{key_suffix}")
    with col2:
        fig = ui_service.get_type_bar_fig(stats, t)
        if fig.data:
            st.plotly_chart(fig, width="stretch", key=f"type_bar_{key_suffix}")

    if stats["category_spending"]:
        st.markdown("---")
        st.subheader(t("chart_spending_share"))
        spending_fig = ui_service.get_spending_share_fig(stats, t, tc)
        st.caption(t("spending_share_caption"))
        st.plotly_chart(spending_fig, width="stretch", key=f"spending_share_{key_suffix}")


def render_category_deep_dive(t, tc, stats, key_suffix: str = ""):
    """Render category deep dive with transaction counts and spending.

    Args:
        t: Translation function
        tc: Translation category function
        stats: Dictionary with category statistics
        key_suffix: Unique suffix for widget keys
    """
    if stats["categories"] or stats["category_spending"]:
        st.subheader(t("category_deep_dive"))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(t("txns_by_category"))
            fig_count = ui_service.get_category_count_fig(stats, tc)
            st.plotly_chart(fig_count, width="stretch", key=f"cat_count_{key_suffix}")
        with col2:
            st.markdown(t("money_by_category"))
            fig_spent = ui_service.get_category_spending_fig(stats, tc)
            st.plotly_chart(fig_spent, width="stretch", key=f"cat_spending_{key_suffix}")

        st.markdown(t("category_summary"))
        cat_data = []
        for cat in sorted(stats["categories"].keys()):
            cat_data.append(
                {
                    "Category": tc(cat),
                    "Transactions": stats["categories"].get(cat, 0),
                    "Total Spent": ui_service.format_currency(stats['category_spending'].get(cat, 0.0)),
                }
            )
        st.dataframe(pd.DataFrame(cat_data), width="stretch")


def render_monthly_spending_trends(t, tc, stats, key_suffix: str = ""):
    """Render monthly spending trends chart.

    Args:
        t: Translation function
        tc: Translation category function
        stats: Dictionary with monthly_spending_trends data
        key_suffix: Unique suffix for widget keys
    """
    if stats["monthly_spending_trends"]:
        st.markdown("---")
        st.subheader(t("monthly_spending_trends_title"))

        trends_data = []
        for month_year, categories in stats["monthly_spending_trends"].items():
            for category, amount in categories.items():
                trends_data.append({"Month": month_year, "Category": tc(category), "Amount": amount})
        trends_df = pd.DataFrame(trends_data)

        if not trends_df.empty:
            fig_trends = ui_service.get_monthly_trends_fig(stats, t, tc)
            st.plotly_chart(fig_trends, width="stretch", key=f"monthly_trends_{key_suffix}")
        else:
            st.info(t("no_monthly_spending_data"))
