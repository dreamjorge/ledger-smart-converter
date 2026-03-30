from __future__ import annotations
from pathlib import Path
from typing import Callable
import re

import streamlit as st
import pandas as pd
import plotly.express as px

from services import import_service as imp
from services import rule_service as rulesvc
from services import data_service, ui_service
from ui.components.analytics_components import (
    render_metrics,
    render_charts,
    render_category_deep_dive,
    render_monthly_spending_trends,
)
from ui.components.rule_components import render_rule_staging_hub


def render_comparison(df_sant: pd.DataFrame, df_hsbc: pd.DataFrame, *, t: Callable, tc: Callable = None):
    """Render comparison view between Santander and HSBC banks."""
    from services.analytics_service import calculate_categorization_stats

    # Default tc to t if not provided
    if tc is None:
        tc = lambda x: x
    st.markdown(t("comparison_desc"))

    # Calculate stats for both banks
    stats_sant = calculate_categorization_stats(df_sant)
    stats_hsbc = calculate_categorization_stats(df_hsbc)

    # Comparison metrics
    st.markdown("### 📊 Overall Comparison")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Santander Total", stats_sant["total"])
        st.metric("Santander Spent", ui_service.format_currency(stats_sant['total_spent']))

    with col2:
        st.metric("HSBC Total", stats_hsbc["total"])
        st.metric("HSBC Spent", ui_service.format_currency(stats_hsbc['total_spent']))

    with col3:
        total_txns = stats_sant["total"] + stats_hsbc["total"]
        total_spent = stats_sant["total_spent"] + stats_hsbc["total_spent"]
        st.metric("Combined Total", total_txns)
        st.metric("Combined Spent", ui_service.format_currency(total_spent))

    # Side-by-side spending comparison
    st.markdown("---")
    st.markdown("### 💰 Spending Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Santander**")
        if stats_sant["category_spending"]:
            fig_sant = px.pie(
                names=[tc(n) for n in stats_sant["category_spending"].keys()],
                values=list(stats_sant["category_spending"].values()),
                hole=0.4,
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_sant.update_traces(textposition="inside", textinfo="percent+label")
            fig_sant.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_sant, use_container_width=True)

    with col2:
        st.markdown("**HSBC**")
        if stats_hsbc["category_spending"]:
            fig_hsbc = px.pie(
                names=[tc(n) for n in stats_hsbc["category_spending"].keys()],
                values=list(stats_hsbc["category_spending"].values()),
                hole=0.4,
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_hsbc.update_traces(textposition="inside", textinfo="percent+label")
            fig_hsbc.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_hsbc, use_container_width=True)

    # Combined category spending bar chart
    st.markdown("---")
    st.markdown("### 📈 Combined Category Spending")

    fig_comparison = ui_service.get_bank_comparison_fig(stats_sant, stats_hsbc, tc)
    if fig_comparison.data:
        st.plotly_chart(fig_comparison, use_container_width=True)

    # Coverage comparison
    st.markdown("---")
    st.markdown("### 🎯 Categorization Coverage")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Santander**")
        fig_cov_sant = ui_service.get_coverage_pie_fig(stats_sant, t)
        st.plotly_chart(fig_cov_sant, use_container_width=True)
        st.caption(f"{ui_service.format_percentage(stats_sant['coverage_pct'])} categorized")

    with col2:
        st.markdown("**HSBC**")
        fig_cov_hsbc = ui_service.get_coverage_pie_fig(stats_hsbc, t)
        st.plotly_chart(fig_cov_hsbc, use_container_width=True)
        st.caption(f"{ui_service.format_percentage(stats_hsbc['coverage_pct'])} categorized")


def render_analytics_dashboard(
    *,
    t: Callable,
    tc: Callable,
    config_dir: Path,
    data_dir: Path,
    copy_feedback_key: str,
    ml_engine,
):
    feedback = st.session_state.pop(copy_feedback_key, None)
    if feedback:
        st.success(feedback)

    st.header(t("analytics_title"))
    db_path = data_dir / "ledger.db"
    
    # Load data for all banks
    df_sant = data_service.load_transactions("santander_likeu", prefer_db=True, db_path=db_path)
    df_hsbc = data_service.load_transactions("hsbc", prefer_db=True, db_path=db_path)

    if df_sant.empty and df_hsbc.empty:
        st.warning(t("no_csv_found"))
        return

    # Add "Global Overview" if we have data from multiple sources
    tabs = []
    if not df_sant.empty or not df_hsbc.empty:
        tabs.append("🌍 " + t("all"))
    if not df_sant.empty:
        tabs.append("Santander")
    if not df_hsbc.empty:
        tabs.append("HSBC")
    if not df_sant.empty and not df_hsbc.empty:
        tabs.append(t("tab_comparison"))

    selected_tabs = st.tabs(tabs)
    tab_idx = 0
    
    # Global Overview Tab
    if not df_sant.empty or not df_hsbc.empty:
        with selected_tabs[tab_idx]:
            # FIX: Only concat non-empty dataframes to avoid crash
            dfs_to_concat = [df for df in [df_sant, df_hsbc] if not df.empty]
            if len(dfs_to_concat) > 1:
                df_all = pd.concat(dfs_to_concat, ignore_index=True)
            else:
                df_all = dfs_to_concat[0]
                
            render_bank_analytics(
                df=df_all,
                bank_name=t("all"),
                bank_id="all_accounts",
                t=t,
                tc=tc,
                config_dir=config_dir,
                data_dir=data_dir,
                ml_engine=ml_engine,
                show_rule_hub=False # Rule hub is better per-bank
            )
        tab_idx += 1

    if not df_sant.empty:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="Santander"))
            render_bank_analytics(
                df=df_sant,
                bank_name="Santander",
                bank_id="santander_likeu",
                t=t,
                tc=tc,
                config_dir=config_dir,
                data_dir=data_dir,
                ml_engine=ml_engine,
            )
        tab_idx += 1
    if not df_hsbc.empty:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="HSBC"))
            render_bank_analytics(
                df=df_hsbc,
                bank_name="HSBC",
                bank_id="hsbc",
                t=t,
                tc=tc,
                config_dir=config_dir,
                data_dir=data_dir,
                ml_engine=ml_engine,
            )
        tab_idx += 1
    if not df_sant.empty and not df_hsbc.empty:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_comparison"))
            render_comparison(df_sant, df_hsbc, t=t, tc=tc)


def _render_drilldown(t, tc, stats, df_filtered_for_display, bank_id):
    st.markdown("---")
    st.subheader(t("drilldown_title"))
    selected_cat = st.selectbox(
        t("drilldown_select"),
        options=[t("all")] + sorted(list(stats["categories"].keys())),
        format_func=lambda x: tc(x) if x != t("all") else x,
        key=f"{bank_id}_drilldown_cat",
    )

    display_df = df_filtered_for_display.copy()
    if selected_cat != t("all"):
        # Improved filtering to match full category name or leaf
        display_df = display_df[display_df["destination_name"].str.contains(f":{selected_cat}$", na=False) | 
                                (display_df["destination_name"] == selected_cat)]
    if not display_df.empty:
        st.markdown(t("showing_txns", count=len(display_df), cat=tc(selected_cat)))
        view_cols = ["date", "description", "amount", "destination_name", "tags"]
        st.dataframe(display_df[view_cols], use_container_width=True)
    else:
        st.info(t("no_txns_found"))


def render_bank_analytics(df, bank_name, bank_id, t, tc, config_dir: Path, data_dir: Path, ml_engine, show_rule_hub=True):
    from services.analytics_service import calculate_categorization_stats
    
    if df is None or df.empty:
        st.error("No data available")
        return

    # Info caption for last update (if applicable)
    if bank_id != "all_accounts":
        last_updated = imp.get_csv_last_updated(data_service.get_csv_path(bank_id))
        if last_updated:
            st.caption(t("last_data_update", timestamp=last_updated))

    # Global Date Range Selector
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date_filter = st.date_input(t("start_date_filter"), value=None, key=f"{bank_id}_start_date")
    with col_date2:
        end_date_filter = st.date_input(t("end_date_filter"), value=None, key=f"{bank_id}_end_date")

    date_range_active = start_date_filter is not None and end_date_filter is not None and start_date_filter <= end_date_filter

    periods = set()
    if "tags" in df.columns:
        for tag_str in df["tags"].dropna():
            for tag in str(tag_str).split(","):
                if tag.startswith("period:"):
                    periods.add(tag.split(":")[1])

    sorted_periods = sorted(list(periods), reverse=True)
    selected_period = t("all")
    if sorted_periods:
        selected_period = st.selectbox(
            t("filter_period", bank=bank_name), 
            [t("all")] + sorted_periods, 
            key=f"{bank_id}_period_filter",
            disabled=date_range_active # Disable if date range is active
        )

    # Determine filtering parameters
    selected_period_value = selected_period if selected_period != t("all") and not date_range_active else None
    
    # Re-filter df to create df_filtered based on the selected period or date range for drill-down and rule hub
    df_filtered_for_display = df.copy()
    if date_range_active:
        df_filtered_for_display = df_filtered_for_display[
            (df_filtered_for_display["date"] >= pd.to_datetime(start_date_filter)) &
            (df_filtered_for_display["date"] <= pd.to_datetime(end_date_filter))
        ]
    elif selected_period_value:
        df_filtered_for_display = df_filtered_for_display[
            df_filtered_for_display["tags"].str.contains(f"period:{selected_period_value}", na=False)
        ]

    # Calculate stats using the date range filters or period filter
    stats = calculate_categorization_stats(
        df,
        period=selected_period_value,
        start_date=pd.to_datetime(start_date_filter) if start_date_filter else None,
        end_date=pd.to_datetime(end_date_filter) if end_date_filter else None,
    )

    if stats is None:
        st.error(t("no_data_selection"))
        return

    render_metrics(t, stats)
    render_charts(t, stats, tc, key_suffix=bank_id)
    render_category_deep_dive(t, tc, stats, key_suffix=bank_id)
    render_monthly_spending_trends(t, tc, stats, key_suffix=bank_id)
    _render_drilldown(t, tc, stats, df_filtered_for_display, bank_id)
    
    if show_rule_hub:
        render_rule_staging_hub(
            t=t,
            tc=tc,
            df_filtered_for_display=df_filtered_for_display,
            bank_name=bank_name,
            bank_id=bank_id,
            config_dir=config_dir,
            data_dir=data_dir,
            ml_engine=ml_engine
        )
