# -*- coding: utf-8 -*-
"""Streamlit page for manual single-transaction entry."""
import datetime
from pathlib import Path
from typing import Callable, Optional

import streamlit as st

from services.manual_entry_service import (
    get_category_label,
    load_accounts_from_config,
    load_categories_from_rules,
    submit_manual_transaction,
)


def render_manual_entry_page(
    *,
    t: Callable,
    config_dir: Path,
    db_path: Optional[Path] = None,
    user_id: Optional[str] = None,
    lang: str = "es",
) -> None:
    """Render the manual transaction entry form.

    Args:
        t: Translation helper callable.
        config_dir: Path to the config/ directory (contains rules.yml, accounts.yml).
        db_path: Optional path to the SQLite database. Uses settings default if None.
    """
    st.header(t("manual_entry_title"))
    st.caption(t("manual_entry_desc"))
    st.divider()

    rules_path = config_dir / "rules.yml"
    accounts_path = config_dir / "accounts.yml"

    categories = load_categories_from_rules(rules_path)
    accounts = load_accounts_from_config(accounts_path, rules_path)

    if not accounts:
        st.error(t("manual_entry_no_accounts"))
        return

    with st.form("manual_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_val = st.date_input(
                t("field_date"),
                value=datetime.date.today(),
            )
        with col2:
            amount = st.number_input(
                t("field_amount"),
                min_value=0.01,
                step=0.01,
                format="%.2f",
            )

        description = st.text_input(t("field_description"), max_chars=255)

        col3, col4 = st.columns(2)
        with col3:
            account_labels = list(accounts.values())
            account_ids = list(accounts.keys())
            selected_label = st.selectbox(t("field_bank_account"), options=account_labels)
            canonical_account_id = account_ids[account_labels.index(selected_label)]

        with col4:
            txn_type = st.selectbox(
                t("field_transaction_type"),
                options=["withdrawal", "transfer", "deposit"],
                format_func=lambda x: t(f"type_{x}"),
            )

        category = st.selectbox(
            t("field_category"),
            options=[""] + categories,
            format_func=lambda x: get_category_label(x, lang) if x else t("manual_entry_select_placeholder"),
        )

        submitted = st.form_submit_button(t("nav_manual_entry"))

    if submitted:
        # Resolve bank_id and account_id from the canonical_account selection
        import yaml
        with open(accounts_path, encoding="utf-8") as f:
            acc_cfg = yaml.safe_load(f) or {}
        canonical_accounts = acc_cfg.get("canonical_accounts", {})
        acc_entry = canonical_accounts.get(canonical_account_id, {})
        bank_ids = acc_entry.get("bank_ids", [])
        account_ids_list = acc_entry.get("account_ids", [])

        bank_id = bank_ids[0] if bank_ids else canonical_account_id
        account_id = account_ids_list[0] if account_ids_list else canonical_account_id

        ok, errors = submit_manual_transaction(
            date=date_val.isoformat(),
            description=description,
            amount=float(amount),
            bank_id=bank_id,
            account_id=account_id,
            canonical_account_id=canonical_account_id,
            transaction_type=txn_type,
            category=category,
            db_path=db_path,
            user_id=user_id,
        )

        if ok:
            st.success(t("manual_entry_success"))
        elif errors == ["duplicate"]:
            st.warning(t("manual_entry_duplicate"))
        else:
            st.error(t("manual_entry_validation_error", errors=", ".join(errors)))
