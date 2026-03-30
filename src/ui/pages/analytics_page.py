from __future__ import annotations
from pathlib import Path
from typing import Callable
import re

import streamlit as st
import pandas as pd
import plotly.express as px

from services import import_service as imp
from services import rule_service as rulesvc
from services import data_service, ui_service, analytics_service
from ui.components.analytics_components import (
    render_metrics,
    render_charts,
    render_category_deep_dive,
    render_monthly_spending_trends,
)
from ui.components.rule_components import render_rule_staging_hub


def render_comparison(stats_sant: dict, stats_hsbc: dict, *, t: Callable, tc: Callable = None):
    """Render comparison view between Santander and HSBC banks using pre-calculated stats."""
    # Default tc to t if not provided
    if tc is None:
        tc = lambda x: x
    st.markdown(t("comparison_desc"))

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
            st.plotly_chart(fig_sant, width="stretch", key="comparison_pie_sant")

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
            st.plotly_chart(fig_hsbc, width="stretch", key="comparison_pie_hsbc")

    # Combined category spending bar chart
    st.markdown("---")
    st.markdown("### 📈 Combined Category Spending")

    fig_comparison = ui_service.get_bank_comparison_fig(stats_sant, stats_hsbc, tc)
    if fig_comparison.data:
        st.plotly_chart(fig_comparison, width="stretch", key="comparison_bar_combined")

    # Coverage comparison
    st.markdown("---")
    st.markdown("### 🎯 Categorization Coverage")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Santander**")
        fig_cov_sant = ui_service.get_coverage_pie_fig(stats_sant, t)
        st.plotly_chart(fig_cov_sant, width="stretch", key="comparison_cov_sant")
        st.caption(f"{ui_service.format_percentage(stats_sant['coverage_pct'])} categorized")

    with col2:
        st.markdown("**HSBC**")
        fig_cov_hsbc = ui_service.get_coverage_pie_fig(stats_hsbc, t)
        st.plotly_chart(fig_cov_hsbc, width="stretch", key="comparison_cov_hsbc")
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
    
    # Check if DB has data
    total_db_rows = 0
    if db_path.exists():
        from services.db_service import DatabaseService
        db = DatabaseService(db_path=db_path)
        row = db.fetch_one("SELECT COUNT(*) AS c FROM transactions")
        total_db_rows = row["c"] if row else 0

    if total_db_rows == 0:
        st.warning(t("no_csv_found"))
        st.info("Try importing some files or 'Sync Historical Data' in Settings.")
        return

    # Add tabs for different views
    tabs = ["🌍 " + t("all"), "Santander", "HSBC", t("tab_comparison")]
    selected_tabs = st.tabs(tabs)
    
    # Global Overview Tab
    with selected_tabs[0]:
        render_bank_analytics(
            bank_name=t("all"),
            bank_id="all_accounts",
            t=t,
            tc=tc,
            config_dir=config_dir,
            data_dir=data_dir,
            ml_engine=ml_engine,
            show_rule_hub=False,
            db_path=db_path
        )

    # Santander Tab
    with selected_tabs[1]:
        st.subheader(t("bank_analytics_header", bank="Santander"))
        render_bank_analytics(
            bank_name="Santander",
            bank_id="santander_likeu",
            t=t,
            tc=tc,
            config_dir=config_dir,
            data_dir=data_dir,
            ml_engine=ml_engine,
            db_path=db_path
        )

    # HSBC Tab
    with selected_tabs[2]:
        st.subheader(t("bank_analytics_header", bank="HSBC"))
        render_bank_analytics(
            bank_name="HSBC",
            bank_id="hsbc",
            t=t,
            tc=tc,
            config_dir=config_dir,
            data_dir=data_dir,
            ml_engine=ml_engine,
            db_path=db_path
        )

    # Comparison Tab
    with selected_tabs[3]:
        st.subheader(t("bank_comparison"))
        stats_sant = analytics_service.calculate_categorization_stats_from_db(db_path, bank_id="santander_likeu")
        stats_hsbc = analytics_service.calculate_categorization_stats_from_db(db_path, bank_id="hsbc")
        render_comparison(stats_sant, stats_hsbc, t=t, tc=tc)


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
        st.dataframe(display_df[view_cols], width="stretch")
    else:
        st.info(t("no_txns_found"))


def render_bank_analytics(bank_name, bank_id, t, tc, config_dir: Path, data_dir: Path, ml_engine, db_path: Path, show_rule_hub=True):
    # Global Date Range Selector
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date_filter = st.date_input(t("start_date_filter"), value=None, key=f"{bank_id}_start_date")
    with col_date2:
        end_date_filter = st.date_input(t("end_date_filter"), value=None, key=f"{bank_id}_end_date")

    date_range_active = start_date_filter is not None and end_date_filter is not None and start_date_filter <= end_date_filter

    # If it's a specific bank, we can still filter by period from the tags
    selected_period_value = None
    if bank_id != "all_accounts":
        # We need a small DF just to extract periods for the dropdown
        # This is a bit inefficient but keep it for now for the period UI
        df_minimal = data_service.load_transactions_from_db(bank_id, db_path=db_path)
        periods = set()
        if not df_minimal.empty and "tags" in df_minimal.columns:
            for tag_str in df_minimal["tags"].dropna():
                for tag in str(tag_str).split(","):
                    if tag.startswith("period:"):
                        periods.add(tag.split(":")[1])

        sorted_periods = sorted(list(periods), reverse=True)
        if sorted_periods:
            selected_period = st.selectbox(
                t("filter_period", bank=bank_name), 
                [t("all")] + sorted_periods, 
                key=f"{bank_id}_period_filter",
                disabled=date_range_active
            )
            if selected_period != t("all") and not date_range_active:
                selected_period_value = selected_period

    # Calculate stats directly from DB
    stats = analytics_service.calculate_categorization_stats_from_db(
        db_path=db_path,
        bank_id=None if bank_id == "all_accounts" else bank_id,
        period=selected_period_value,
        start_date=pd.to_datetime(start_date_filter) if start_date_filter else None,
        end_date=pd.to_datetime(end_date_filter) if end_date_filter else None,
    )

    if stats["total"] == 0:
        st.error(t("no_data_selection"))
        return

    render_metrics(t, stats)
    render_charts(t, stats, tc, key_suffix=bank_id)
    render_category_deep_dive(t, tc, stats, key_suffix=bank_id)
    render_monthly_spending_trends(t, tc, stats, key_suffix=bank_id)
    
    # For drilldown and rule hub, we still need a DataFrame
    # In Approach 2 we would ideally have a "DataService.get_filtered_transactions"
    df_filtered = data_service.load_transactions_from_db(
        bank_id=None if bank_id == "all_accounts" else bank_id,
        db_path=db_path
    )
    if not df_filtered.empty:
        # Apply the same filtering as the stats query for the UI display
        if date_range_active:
            df_filtered = df_filtered[
                (df_filtered["date"] >= pd.to_datetime(start_date_filter)) &
                (df_filtered["date"] <= pd.to_datetime(end_date_filter))
            ]
        elif selected_period_value:
            df_filtered = df_filtered[df_filtered["tags"].str.contains(f"period:{selected_period_value}", na=False)]

        _render_drilldown(t, tc, stats, df_filtered, bank_id)
        
        if show_rule_hub:
            render_rule_staging_hub(
                t=t,
                tc=tc,
                df_filtered_for_display=df_filtered,
                bank_name=bank_name,
                bank_id=bank_id,
                config_dir=config_dir,
                data_dir=data_dir,
                ml_engine=ml_engine
            )
