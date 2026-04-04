from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional, cast
import re

import streamlit as st
import pandas as pd
import plotly.express as px

from services import import_service as imp
from services import rule_service as rulesvc
from services import ui_service, analytics_service
from ui.components.analytics_components import (
    render_metrics,
    render_charts,
    render_category_deep_dive,
    render_monthly_spending_trends,
)
from ui.components.rule_components import render_rule_staging_hub

from application.use_cases.calculate_analytics import CalculateAnalytics, AnalyticsResult
from application.use_cases.get_filtered_transactions import GetFilteredTransactions
from infrastructure.adapters.sqlite_transaction_repository import SqliteTransactionRepository
from services.db_service import DatabaseService
from dataclasses import asdict

if False:
    from application.use_cases.generate_monthly_report import GenerateMonthlyReport


def render_comparison(
    stats_sant: dict,
    stats_hsbc: dict,
    *,
    t: Callable,
    tc: Optional[Callable[[str], str]] = None,
):
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
        st.metric(
            "Santander Spent", ui_service.format_currency(stats_sant["total_spent"])
        )

    with col2:
        st.metric("HSBC Total", stats_hsbc["total"])
        st.metric("HSBC Spent", ui_service.format_currency(stats_hsbc["total_spent"]))

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
        st.caption(
            f"{ui_service.format_percentage(stats_sant['coverage_pct'])} categorized"
        )

    with col2:
        st.markdown("**HSBC**")
        fig_cov_hsbc = ui_service.get_coverage_pie_fig(stats_hsbc, t)
        st.plotly_chart(fig_cov_hsbc, width="stretch", key="comparison_cov_hsbc")
        st.caption(
            f"{ui_service.format_percentage(stats_hsbc['coverage_pct'])} categorized"
        )


def render_analytics_dashboard(
    *,
    t: Callable,
    tc: Callable,
    config_dir: Path,
    data_dir: Path,
    copy_feedback_key: str,
    ml_engine,
    report_use_case: Optional[GenerateMonthlyReport] = None,
):
    feedback = st.session_state.pop(copy_feedback_key, None)
    if feedback:
        st.success(feedback)

    st.header(t("analytics_title"))
    db_path = data_dir / "ledger.db"

    # 1. Initialize Clean Architecture layers (Pure DI)
    db_service = DatabaseService(db_path=db_path)
    db_service.initialize()
    txn_repo = SqliteTransactionRepository(db_service)
    
    calculate_analytics_uc = CalculateAnalytics(txn_repo)
    get_filtered_txns_uc = GetFilteredTransactions(txn_repo)

    # Check if DB has data
    total_db_rows = 0
    if db_path.exists():
        row = db_service.fetch_one("SELECT COUNT(*) AS c FROM transactions")
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
            db_path=db_path,
            calculate_analytics_uc=calculate_analytics_uc,
            get_filtered_txns_uc=get_filtered_txns_uc,
            report_use_case=report_use_case,
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
            db_path=db_path,
            calculate_analytics_uc=calculate_analytics_uc,
            get_filtered_txns_uc=get_filtered_txns_uc,
            report_use_case=report_use_case,
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
            db_path=db_path,
            calculate_analytics_uc=calculate_analytics_uc,
            get_filtered_txns_uc=get_filtered_txns_uc,
            report_use_case=report_use_case,
        )

    # Comparison Tab
    with selected_tabs[3]:
        st.subheader(t("bank_comparison"))
        # Unified Use Case calls
        res_sant = calculate_analytics_uc.execute(bank_id="santander_likeu")
        res_hsbc = calculate_analytics_uc.execute(bank_id="hsbc")
        
        render_comparison(asdict(res_sant), asdict(res_hsbc), t=t, tc=tc)


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
        display_df = display_df[
            display_df["destination_name"].str.contains(f":{selected_cat}$", na=False)
            | (display_df["destination_name"] == selected_cat)
        ]
    if not display_df.empty:
        st.markdown(t("showing_txns", count=len(display_df), cat=tc(selected_cat)))
        view_cols = ["date", "description", "amount", "destination_name", "tags"]
        st.dataframe(display_df[view_cols], width="stretch")
    else:
        st.info(t("no_txns_found"))


def render_bank_analytics(
    bank_name,
    bank_id,
    t,
    tc,
    config_dir: Path,
    data_dir: Path,
    ml_engine,
    db_path: Path,
    calculate_analytics_uc: CalculateAnalytics,
    get_filtered_txns_uc: GetFilteredTransactions,
    report_use_case: Optional[GenerateMonthlyReport] = None,
    show_rule_hub=True,
):
    # Global Date Range Selector
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date_filter = st.date_input(
            t("start_date_filter"), value=None, key=f"{bank_id}_start_date"
        )
    with col_date2:
        end_date_filter = st.date_input(
            t("end_date_filter"), value=None, key=f"{bank_id}_end_date"
        )

    date_range_active = (
        start_date_filter is not None
        and end_date_filter is not None
        and start_date_filter <= end_date_filter
    )

    # If it's a specific bank, we can still filter by period from the tags
    selected_period_value = None
    if bank_id != "all_accounts":
        # Using the Use Case to get transactions and extract periods
        all_txns = get_filtered_txns_uc.execute(bank_id=bank_id)
        periods = set()
        for txn in all_txns:
            if txn.tags:
                for tag in str(txn.tags).split(","):
                    if tag.startswith("period:"):
                        periods.add(tag.split(":")[1])

        sorted_periods = sorted(list(periods), reverse=True)
        if sorted_periods:
            selected_period = st.selectbox(
                t("filter_period", bank=bank_name),
                [t("all")] + sorted_periods,
                key=f"{bank_id}_period_filter",
                disabled=date_range_active,
            )
            if selected_period != t("all") and not date_range_active:
                selected_period_value = selected_period

    # Report Generation Button
    if report_use_case:
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            # We use the current filters for the report
            if st.button(t("btn_generate_report"), key=f"{bank_id}_gen_report"):
                with st.spinner(t("processing")):
                    try:
                        period_label = selected_period_value or f"{start_date_filter} to {end_date_filter}" if date_range_active else t("all")
                        report_bytes = report_use_case.execute(
                            bank_id=None if bank_id == "all_accounts" else bank_id,
                            period=selected_period_value,
                            start_date=start_date_filter,
                            end_date=end_date_filter,
                        )
                        st.download_button(
                            label=t("download_report"),
                            data=report_bytes,
                            file_name=f"report_{bank_id}_{period_label}.pdf",
                            mime="application/pdf",
                            key=f"{bank_id}_dl_report"
                        )
                        st.success(t("report_generated", period=period_label))
                    except Exception as e:
                        st.error(f"Failed to generate report: {str(e)}")

    # Invoke Analytics Use Case
    stats_res = calculate_analytics_uc.execute(
        bank_id=None if bank_id == "all_accounts" else bank_id,
        period=selected_period_value,
        start_date=start_date_filter,
        end_date=end_date_filter,
    )
    stats = asdict(stats_res)

    if stats["total"] == 0:
        st.error(t("no_data_selection"))
        return

    render_metrics(t, stats)
    render_charts(t, stats, tc, key_suffix=bank_id)
    render_category_deep_dive(t, tc, stats, key_suffix=bank_id)
    render_monthly_spending_trends(t, tc, stats, key_suffix=bank_id)

    # For drilldown and rule hub, we fetch filtered transactions
    txns_filtered = get_filtered_txns_uc.execute(
        bank_id=None if bank_id == "all_accounts" else bank_id,
        period=selected_period_value,
        start_date=start_date_filter,
        end_date=end_date_filter,
    )
    
    if txns_filtered:
        # Convert to DataFrame for legacy UI components compatibility
        df_filtered = pd.DataFrame([
            {
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "destination_name": t.destination_name,
                "tags": t.tags,
                "bank_id": t.bank_id,
                "transaction_type": t.transaction_type,
                "category": t.category
            } for t in txns_filtered
        ])

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
                ml_engine=ml_engine,
            )
