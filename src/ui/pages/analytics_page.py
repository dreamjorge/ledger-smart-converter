from pathlib import Path
from typing import Callable
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import smart_matching as sm
import ml_categorizer as ml
from services import import_service as imp
from services import rule_service as rulesvc
from services import data_service
from services.analytics_service import calculate_categorization_stats
from ui.components.analytics_components import (
    render_metrics,
    render_charts,
    render_category_deep_dive,
    render_monthly_spending_trends,
)

def render_comparison(df_sant: pd.DataFrame, df_hsbc: pd.DataFrame, *, t: Callable, tc: Callable = None):
    """Render comparison view between Santander and HSBC banks.

    Args:
        df_sant: Santander transactions DataFrame
        df_hsbc: HSBC transactions DataFrame
        t: Translation function
        tc: Category translation function (optional)
    """
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
        st.metric("Santander Spent", f"${stats_sant['total_spent']:,.2f}")

    with col2:
        st.metric("HSBC Total", stats_hsbc["total"])
        st.metric("HSBC Spent", f"${stats_hsbc['total_spent']:,.2f}")

    with col3:
        total_txns = stats_sant["total"] + stats_hsbc["total"]
        total_spent = stats_sant["total_spent"] + stats_hsbc["total_spent"]
        st.metric("Combined Total", total_txns)
        st.metric("Combined Spent", f"${total_spent:,.2f}")

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
            st.plotly_chart(fig_sant, width="stretch")

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
            st.plotly_chart(fig_hsbc, width="stretch")

    # Combined category spending bar chart
    st.markdown("---")
    st.markdown("### 📈 Combined Category Spending")

    # Merge category spending from both banks
    all_categories = set(stats_sant["category_spending"].keys()) | set(stats_hsbc["category_spending"].keys())

    comparison_data = []
    for cat in all_categories:
        comparison_data.append({
            "Category": tc(cat),
            "Santander": stats_sant["category_spending"].get(cat, 0),
            "HSBC": stats_hsbc["category_spending"].get(cat, 0),
        })

    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        comp_df = comp_df.sort_values("Santander", ascending=False)

        fig_comparison = go.Figure()
        fig_comparison.add_trace(go.Bar(
            name="Santander",
            x=comp_df["Category"],
            y=comp_df["Santander"],
            marker_color="#6366f1"
        ))
        fig_comparison.add_trace(go.Bar(
            name="HSBC",
            x=comp_df["Category"],
            y=comp_df["HSBC"],
            marker_color="#818cf8"
        ))

        fig_comparison.update_layout(
            barmode="group",
            template="plotly_dark",
            font_family="Outfit",
            title="Spending by Category (Both Banks)",
            xaxis_title="Category",
            yaxis_title="Amount (MXN)",
            height=500,
        )

        st.plotly_chart(fig_comparison, width="stretch")

    # Coverage comparison
    st.markdown("---")
    st.markdown("### 🎯 Categorization Coverage")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Santander**")
        fig_cov_sant = px.pie(
            names=["Categorized", "Uncategorized"],
            values=[stats_sant["categorized"], stats_sant["uncategorized"]],
            color_discrete_sequence=["#6366f1", "#475569"],
            hole=0.6,
        )
        fig_cov_sant.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig_cov_sant, width="stretch")
        st.caption(f"{stats_sant['coverage_pct']:.1f}% categorized")

    with col2:
        st.markdown("**HSBC**")
        fig_cov_hsbc = px.pie(
            names=["Categorized", "Uncategorized"],
            values=[stats_hsbc["categorized"], stats_hsbc["uncategorized"]],
            color_discrete_sequence=["#818cf8", "#475569"],
            hole=0.6,
        )
        fig_cov_hsbc.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig_cov_hsbc, width="stretch")
        st.caption(f"{stats_hsbc['coverage_pct']:.1f}% categorized")


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
    df_sant = data_service.load_transactions("santander_likeu", prefer_db=True, db_path=db_path)
    df_hsbc = data_service.load_transactions("hsbc", prefer_db=True, db_path=db_path)

    if df_sant.empty and df_hsbc.empty:
        st.warning(t("no_csv_found"))
        return

    tabs = []
    if not df_sant.empty:
        tabs.append("Santander")
    if not df_hsbc.empty:
        tabs.append("HSBC")
    if not df_sant.empty and not df_hsbc.empty:
        tabs.append(t("tab_comparison"))

    selected_tabs = st.tabs(tabs)
    tab_idx = 0
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
        display_df = display_df[display_df["destination_name"].str.contains(f":{selected_cat}", na=False)]
    if not display_df.empty:
        st.markdown(t("showing_txns", count=len(display_df), cat=tc(selected_cat)))
        view_cols = ["date", "description", "amount", "destination_name", "tags"]
        st.dataframe(display_df[view_cols], width="stretch")
    else:
        st.info(t("no_txns_found"))

def _render_rule_hub(t, tc, df_filtered_for_display, bank_name, bank_id, config_dir, data_dir: Path, ml_engine):
    st.markdown("---")
    with st.expander(t("rule_hub_title"), expanded=False):
        st.subheader(t("rule_hub_subtitle"))
        st.markdown(t("rule_hub_desc"))
        st.info(t("rule_hub_tip"))
        if "tags" in df_filtered_for_display.columns:
            merchants = set()
            for tags in df_filtered_for_display["tags"].dropna():
                for tag in str(tags).split(","):
                    if tag.startswith("merchant:"):
                        merchants.add(tag.split(":")[1])
            merchant_list = sorted(list(merchants))
            st.markdown(t("smart_lookup"))
            c_search, _ = st.columns([2, 3])
            with c_search:
                search_term = st.text_input(t("fuzzy_search"), "", key=f"{bank_id}_fuzzy_search")
                if search_term:
                    matches = sm.find_similar_merchants(search_term, merchant_list, threshold=50)
                    if matches:
                        merchant_list = [m for m, _score in matches]
                    else:
                        st.warning(t("no_similar_merchants"))

            selected_merchant = st.selectbox(t("select_merchant"), merchant_list, key=f"{bank_id}_fix_merchant")
            ml_predictions = []
            suggested_cat_hub = None
            try:
                ml_predictions = ml_engine.predict(selected_merchant) or []
                if ml_predictions:
                    top_cat, confidence = ml_predictions[0]
                    if confidence > 0.3:
                        st.success(t("ml_prediction", cat=top_cat, conf=confidence))
                        if ":" in top_cat:
                            suggested_cat_hub = top_cat.split(":")[-1]
            except Exception:
                st.caption("ML prediction unavailable")

            col1, col2 = st.columns(2)
            with col1:
                common_cats = ["Groceries", "Restaurants", "Shopping", "Transport", "Subscriptions", "Entertainment", "Health", "Fees", "Online"]
                if suggested_cat_hub and suggested_cat_hub not in common_cats:
                    common_cats.insert(0, suggested_cat_hub)
                default_ix = common_cats.index(suggested_cat_hub) if suggested_cat_hub in common_cats else 0
                category = st.selectbox(
                    t("select_category"),
                    options=common_cats,
                    index=default_ix,
                    format_func=lambda x: tc(x),
                    key=f"{bank_id}_fix_category",
                )

            if ml_predictions and ml_predictions[0][0].endswith(f":{category}"):
                suggested_expense = ml_predictions[0][0]
            else:
                suggested_expense = (
                    f"Expenses:Food:{category}" if category in ["Groceries", "Restaurants"] else
                    f"Expenses:Transport:{category}" if category in ["Transport"] else
                    f"Expenses:Entertainment:{category}" if category in ["Entertainment", "Subscriptions"] else
                    f"Expenses:Shopping:{category}" if category in ["Shopping", "Online"] else
                    f"Expenses:Fees:{category}" if category in ["Fees"] else
                    f"Expenses:{category}"
                )

            expense_account = st.text_input(t("confirm_destination"), suggested_expense, key=f"{bank_name}_fix_expense")
            safe_pattern = re.escape(selected_merchant.replace("_", " "))
            regex_pattern = st.text_input(t("regex_pattern"), safe_pattern, key=f"{bank_name}_fix_regex")
            rules_path = config_dir / "rules.yml"
            pending_path = config_dir / "rules.pending.yml"
            backup_dir = config_dir / "backups"
            pending_count = rulesvc.get_pending_count(pending_path)
            if pending_count:
                st.warning(f"Pending rule changes: {pending_count}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Stage Rule Change", type="primary", key=f"{bank_name}_stage_rule"):
                    ok, result = rulesvc.stage_rule_change(
                        rules_path=rules_path,
                        pending_path=pending_path,
                        merchant_name=selected_merchant,
                        regex_pattern=regex_pattern,
                        expense_account=expense_account,
                        bucket_tag=category.lower(),
                        db_path=data_dir / "ledger.db",
                    )
                    if ok:
                        st.success(f"Rule staged. Pending changes: {result['pending_count']}")
                    else:
                        st.error(f"Could not stage rule ({result['status']}): {', '.join(result.get('conflicts', []))}")
            with c2:
                if st.button("Apply Pending Rules", key=f"{bank_name}_apply_rules"):
                    ok, result = rulesvc.merge_pending_rules(
                        rules_path,
                        pending_path,
                        backup_dir,
                        db_path=data_dir / "ledger.db",
                    )
                    if ok:
                        with st.spinner(t("teaching_ai")):
                            ml.train_global_model()
                            st.cache_resource.clear()
                        st.success(f"Merged {result['merged_count']} rule(s). Backup: {result['backup_path']}")
                        st.info(t("reprocess_warning"))
                        st.balloons()
                    else:
                        if result.get("status") == "conflict":
                            lines = []
                            for conflict in result.get("conflicts", []):
                                lines.append(f"{conflict.get('rule')}: {', '.join(conflict.get('conflicts', []))}")
                            st.error("Pending rules have conflicts: " + " | ".join(lines))
                        else:
                            st.warning("No pending rules to apply.")


def render_bank_analytics(df, bank_name, bank_id, t, tc, config_dir: Path, data_dir: Path, ml_engine):
    if df is None or df.empty:
        st.error("No data available")
        return

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
            key=f"{bank_name}_period_filter",
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
    render_charts(t, stats, tc)
    render_category_deep_dive(t, tc, stats)
    render_monthly_spending_trends(t, tc, stats)
    _render_drilldown(t, tc, stats, df_filtered_for_display, bank_id)
    _render_rule_hub(t, tc, df_filtered_for_display, bank_name, bank_id, config_dir, data_dir, ml_engine)
