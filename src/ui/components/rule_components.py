# -*- coding: utf-8 -*-
"""Components for the categorization rule hub.

This module contains UI components for staging, reviewing, and applying
categorization rules based on merchant names and patterns.
"""
import re
from pathlib import Path
from typing import Callable, Dict

import streamlit as st
from services import rule_service as rulesvc


def render_pending_rules_summary(t: Callable, pending_path: Path):
    """Render a summary of pending rules to be applied."""
    pending_count = rulesvc.get_pending_count(pending_path)
    if pending_count:
        st.warning(f"⚠️ {t('pending_rules_count', count=pending_count)}")
        # We could add a more detailed list here if desired in the future
    return pending_count


def render_rule_staging_hub(
    *,
    t: Callable,
    tc: Callable,
    df_filtered_for_display,
    bank_name: str,
    bank_id: str,
    config_dir: Path,
    data_dir: Path,
    ml_engine,
):
    # Merchant extraction and lookup
    try:
        import smart_matching as sm
        import ml_categorizer as ml
    except ImportError:
        st.error("Missing internal dependencies (smart_matching or ml_categorizer)")
        return

    st.markdown("---")
    with st.expander(t("rule_hub_title"), expanded=False):
        st.subheader(t("rule_hub_subtitle"))
        st.markdown(t("rule_hub_desc"))
        st.info(t("rule_hub_tip"))

        if "tags" not in df_filtered_for_display.columns:
            st.warning(t("no_merchant_data"))
            return

        # Merchant extraction and lookup
        merchants = set()
        for tags in df_filtered_for_display["tags"].dropna():
            for tag in str(tags).split(","):
                if tag.startswith("merchant:"):
                    merchants.add(tag.split(":")[1])
        merchant_list = sorted(list(merchants))

        if not merchant_list:
            st.info(t("no_merchants_found"))
            return

        st.markdown(f"### 🔍 {t('smart_lookup')}")
        c_search, _ = st.columns([2, 3])
        with c_search:
            search_term = st.text_input(t("fuzzy_search"), "", key=f"{bank_id}_fuzzy_search", label_visibility="visible")
            if search_term:
                matches = sm.find_similar_merchants(search_term, merchant_list, threshold=50)
                if matches:
                    merchant_list = [m for m, _score in matches]
                else:
                    st.warning(t("no_similar_merchants"))

        selected_merchant = st.selectbox(t("select_merchant"), merchant_list, key=f"{bank_id}_fix_merchant", label_visibility="visible")

        # ML Prediction logic
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

        # Category and account selection
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

        expense_account = st.text_input(t("confirm_destination"), suggested_expense, key=f"{bank_id}_fix_expense")
        safe_pattern = re.escape(selected_merchant.replace("_", " "))
        regex_pattern = st.text_input(t("regex_pattern"), safe_pattern, key=f"{bank_id}_fix_regex")

        # Rule actions
        rules_path = config_dir / "rules.yml"
        pending_path = config_dir / "rules.pending.yml"
        backup_dir = config_dir / "backups"
        
        pending_count = render_pending_rules_summary(t, pending_path)

        c1, c2 = st.columns(2)
        with c1:
            if st.button(t("btn_stage_rule"), type="primary", key=f"{bank_id}_stage_rule"):
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
                    st.success(t("rule_staged_success", count=result['pending_count']))
                    st.rerun()
                else:
                    st.error(t("rule_stage_error", status=result['status'], details=', '.join(result.get('conflicts', []))))
        with c2:
            if st.button(t("btn_apply_rules"), key=f"{bank_id}_apply_rules", disabled=not pending_count):
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
                    st.success(t("rule_merge_success", count=result['merged_count'], backup=result['backup_path']))
                    st.info(t("reprocess_warning"))
                    st.balloons()
                    st.rerun()
                else:
                    if result.get("status") == "conflict":
                        lines = [f"{c.get('rule')}: {', '.join(c.get('conflicts', []))}" for c in result.get("conflicts", [])]
                        st.error(t("rule_conflict_error", details=" | ".join(lines)))
                    else:
                        st.warning(t("no_pending_rules"))
