# -*- coding: utf-8 -*-
"""Shared analytics components for dashboard rendering.

This module contains reusable UI components for rendering analytics
dashboards, charts, and metrics to eliminate code duplication.
"""
import pandas as pd
import streamlit as st
import plotly.express as px


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
        st.metric(t("metric_total_spent"), f"${stats['total_spent']:,.2f}", help=t("help_total_spent"))
    with col3:
        st.metric(t("metric_categorized"), f"{stats['categorized']} ({stats['coverage_pct']:.1f}%)", help=t("help_coverage"))
    with col4:
        st.metric(t("metric_category_field"), f"{stats['category_populated']} ({stats['category_pct']:.1f}%)")
    with col5:
        st.metric(t("metric_withdrawals"), stats["type_counts"].get("withdrawal", 0))


def render_charts(t, stats, tc):
    """Render analytics charts (coverage, types, spending share).

    Args:
        t: Translation function
        stats: Dictionary with statistics
        tc: Translation category function
    """
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            names=[t("metric_categorized"), t("uncategorized")],
            values=[stats["categorized"], stats["uncategorized"]],
            title=t("chart_coverage_title"),
            color_discrete_sequence=["#6366f1", "#475569"],
            hole=0.6,
            template="plotly_dark",
        )
        fig.update_layout(font_family="Outfit", title_font_size=20, margin=dict(t=80, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        if stats["type_counts"]:
            fig = px.bar(
                x=list(stats["type_counts"].keys()),
                y=list(stats["type_counts"].values()),
                title=t("chart_types_title"),
                labels={"x": t("chart_types_x"), "y": t("chart_types_y")},
                color=list(stats["type_counts"].keys()),
                color_discrete_sequence=["#6366f1", "#818cf8", "#94a3b8"],
                template="plotly_dark",
            )
            fig.update_layout(font_family="Outfit", title_font_size=20, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    if stats["category_spending"]:
        st.markdown("---")
        st.subheader(t("chart_spending_share"))
        spending_fig = px.pie(
            names=[tc(n) for n in stats["category_spending"].keys()],
            values=list(stats["category_spending"].values()),
            hole=0.5,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        spending_fig.update_traces(textposition="inside", textinfo="percent+label")
        spending_fig.update_layout(font_family="Outfit", showlegend=True, margin=dict(t=40, b=40, l=40, r=40))
        st.caption(t("spending_share_caption"))
        st.plotly_chart(spending_fig, use_container_width=True)


def render_category_deep_dive(t, tc, stats):
    """Render category deep dive with transaction counts and spending.

    Args:
        t: Translation function
        tc: Translation category function
        stats: Dictionary with category statistics
    """
    if stats["categories"] or stats["category_spending"]:
        st.subheader(t("category_deep_dive"))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(t("txns_by_category"))
            categories_sorted = dict(sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)[:10])
            fig_count = px.bar(
                x=list(categories_sorted.values()),
                y=[tc(n) for n in categories_sorted.keys()],
                orientation="h",
                labels={"x": "Transaction Count", "y": "Category"},
                color=list(categories_sorted.values()),
                color_continuous_scale="Blues",
            )
            fig_count.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_count, width="stretch")
        with col2:
            st.markdown(t("money_by_category"))
            spending_sorted = dict(sorted(stats["category_spending"].items(), key=lambda x: x[1], reverse=True)[:10])
            fig_spent = px.bar(
                x=list(spending_sorted.values()),
                y=[tc(n) for n in spending_sorted.keys()],
                orientation="h",
                labels={"x": "Total Amount ($)", "y": "Category"},
                color=list(spending_sorted.values()),
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig_spent, width="stretch")

        st.markdown(t("category_summary"))
        cat_data = []
        for cat in sorted(stats["categories"].keys()):
            cat_data.append(
                {
                    "Category": tc(cat),
                    "Transactions": stats["categories"].get(cat, 0),
                    "Total Spent": f"${stats['category_spending'].get(cat, 0.0):,.2f}",
                }
            )
        st.dataframe(pd.DataFrame(cat_data), width="stretch")


def render_monthly_spending_trends(t, tc, stats):
    """Render monthly spending trends chart.

    Args:
        t: Translation function
        tc: Translation category function
        stats: Dictionary with monthly_spending_trends data
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
            trends_df["Month"] = pd.to_datetime(trends_df["Month"])
            trends_df = trends_df.sort_values(by="Month")
            trends_df["Month"] = trends_df["Month"].dt.strftime("%Y-%m")

            fig_trends = px.line(
                trends_df,
                x="Month",
                y="Amount",
                color="Category",
                title=t("monthly_spending_trends_chart_title"),
                labels={"Amount": "Total Spent ($)"},
                template="plotly_dark",
            )
            fig_trends.update_layout(font_family="Outfit", title_font_size=20, hovermode="x unified")
            st.plotly_chart(fig_trends, use_container_width=True)
        else:
            st.info(t("no_monthly_spending_data"))
