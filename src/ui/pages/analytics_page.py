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
from services.analytics_service import calculate_categorization_stats


def _load_csv_if_exists(path):
    if path and Path(path).exists():
        return pd.read_csv(path)
    return None


def render_analytics_dashboard(
    *,
    t: Callable,
    tc: Callable,
    data_dir: Path,
    config_dir: Path,
    copy_feedback_key: str,
    ml_engine,
):
    feedback = st.session_state.pop(copy_feedback_key, None)
    if feedback:
        st.success(feedback)

    st.header(t("analytics_title"))
    santander_csv = data_dir / "santander" / "firefly_likeu.csv"
    hsbc_csv = data_dir / "hsbc" / "firefly_hsbc.csv"
    df_sant = _load_csv_if_exists(santander_csv)
    df_hsbc = _load_csv_if_exists(hsbc_csv)

    if df_sant is None and df_hsbc is None:
        st.warning(t("no_csv_found"))
        return

    tabs = []
    if df_sant is not None:
        tabs.append("Santander")
    if df_hsbc is not None:
        tabs.append("HSBC")
    if df_sant is not None and df_hsbc is not None:
        tabs.append(t("tab_comparison"))

    selected_tabs = st.tabs(tabs)
    tab_idx = 0
    if df_sant is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="Santander"))
            stats = calculate_categorization_stats(df_sant)
            render_bank_analytics(
                df=df_sant,
                stats=stats,
                bank_name="Santander",
                bank_id="santander_likeu",
                csv_path=santander_csv,
                t=t,
                tc=tc,
                config_dir=config_dir,
                ml_engine=ml_engine,
            )
        tab_idx += 1
    if df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="HSBC"))
            stats = calculate_categorization_stats(df_hsbc)
            render_bank_analytics(
                df=df_hsbc,
                stats=stats,
                bank_name="HSBC",
                bank_id="hsbc",
                csv_path=hsbc_csv,
                t=t,
                tc=tc,
                config_dir=config_dir,
                ml_engine=ml_engine,
            )
        tab_idx += 1
    if df_sant is not None and df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_comparison"))
            render_comparison(df_sant, df_hsbc, t=t)


def render_bank_analytics(df, stats, bank_name, bank_id, csv_path, t, tc, config_dir: Path, ml_engine):
    if df is None or df.empty:
        st.error("No data available")
        return

    last_updated = imp.get_csv_last_updated(Path(csv_path))
    if last_updated:
        st.caption(t("last_data_update", timestamp=last_updated))

    periods = set()
    if "tags" in df.columns:
        for tag_str in df["tags"].dropna():
            for tag in str(tag_str).split(","):
                if tag.startswith("period:"):
                    periods.add(tag.split(":")[1])

    sorted_periods = sorted(list(periods), reverse=True)
    selected_period = t("all")
    if sorted_periods:
        selected_period = st.selectbox(t("filter_period", bank=bank_name), [t("all")] + sorted_periods, key=f"{bank_name}_period_filter")

    if selected_period != t("all"):
        df_filtered = df[df["tags"].str.contains(f"period:{selected_period}", na=False)]
        stats = calculate_categorization_stats(df_filtered)
    else:
        df_filtered = df

    if stats is None:
        st.error(t("no_data_selection"))
        return

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

        st.markdown("---")
        st.subheader(t("drilldown_title"))
        selected_cat = st.selectbox(
            t("drilldown_select"),
            options=[t("all")] + sorted(list(stats["categories"].keys())),
            format_func=lambda x: tc(x) if x != t("all") else x,
            key=f"{bank_id}_drilldown_cat",
        )

        display_df = df_filtered.copy()
        if selected_cat != t("all"):
            display_df = display_df[display_df["destination_name"].str.contains(f":{selected_cat}", na=False)]
        if not display_df.empty:
            st.markdown(t("showing_txns", count=len(display_df), cat=tc(selected_cat)))
            view_cols = ["date", "description", "amount", "destination_name", "tags"]
            st.dataframe(display_df[view_cols], width="stretch")
        else:
            st.info(t("no_txns_found"))

    st.markdown("---")
    with st.expander(t("rule_hub_title"), expanded=False):
        st.subheader(t("rule_hub_subtitle"))
        st.markdown(t("rule_hub_desc"))
        st.info(t("rule_hub_tip"))
        if "tags" in df_filtered.columns:
            merchants = set()
            for tags in df_filtered["tags"].dropna():
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
            ml_predictions = ml_engine.predict(selected_merchant)
            suggested_cat_hub = None
            if ml_predictions:
                top_cat, confidence = ml_predictions[0]
                if confidence > 0.3:
                    st.success(t("ml_prediction", cat=top_cat, conf=confidence))
                    if ":" in top_cat:
                        suggested_cat_hub = top_cat.split(":")[-1]

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
                    )
                    if ok:
                        st.success(f"Rule staged. Pending changes: {result['pending_count']}")
                    else:
                        st.error(f"Could not stage rule ({result['status']}): {', '.join(result.get('conflicts', []))}")
            with c2:
                if st.button("Apply Pending Rules", key=f"{bank_name}_apply_rules"):
                    ok, result = rulesvc.merge_pending_rules(rules_path, pending_path, backup_dir)
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


def render_comparison(df_sant, df_hsbc, t):
    stats_sant = calculate_categorization_stats(df_sant)
    stats_hsbc = calculate_categorization_stats(df_hsbc)
    if stats_sant is None or stats_hsbc is None:
        st.warning(t("no_data_comparison"))
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Santander")
        st.metric(t("metric_total_txns"), stats_sant["total"], help=t("help_total_txns"))
        st.metric(t("metric_total_spent"), f"${stats_sant['total_spent']:,.2f}", help=t("help_total_spent"))
        st.metric(t("metric_categorized"), f"{stats_sant['coverage_pct']:.1f}%", help=t("help_coverage"))
    with col2:
        st.markdown("### HSBC")
        st.metric(t("metric_total_txns"), stats_hsbc["total"], help=t("help_total_txns"))
        st.metric(t("metric_total_spent"), f"${stats_hsbc['total_spent']:,.2f}", help=t("help_total_spent"))
        st.metric(t("metric_categorized"), f"{stats_hsbc['coverage_pct']:.1f}%", help=t("help_coverage"))

    st.markdown("---")
    fig = go.Figure(
        data=[
            go.Bar(name=t("metric_categorized"), x=["Santander", "HSBC"], y=[stats_sant["categorized"], stats_hsbc["categorized"]], marker_color="#6366f1"),
            go.Bar(name=t("uncategorized"), x=["Santander", "HSBC"], y=[stats_sant["uncategorized"], stats_hsbc["uncategorized"]], marker_color="#475569"),
        ]
    )
    fig.update_layout(barmode="stack", title=t("chart_coverage_title"), template="plotly_dark", font_family="Outfit", title_font_size=20)
    st.plotly_chart(fig, use_container_width=True)
