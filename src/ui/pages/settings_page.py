# -*- coding: utf-8 -*-
"""Streamlit settings page: language preference + family user profiles."""
from typing import Callable, Optional

import streamlit as st

from services.user_service import (
    create_user,
    delete_user,
    list_users,
    set_active_user,
    verify_password,
)
from services.db_service import DatabaseService
from settings import load_settings


def _get_db() -> DatabaseService:
    settings = load_settings()
    db = DatabaseService(db_path=settings.data_dir / "ledger.db")
    db.initialize()
    return db


def render_settings_page(*, t: Callable, active_user: Optional[str] = None) -> None:
    """Render the settings page."""
    st.header(t("settings_title"))

    # -----------------------------------------------------------------------
    # Family profiles
    # -----------------------------------------------------------------------
    st.subheader(t("settings_users_title"))
    st.caption(t("settings_users_desc"))

    db = _get_db()
    users = list_users(db)

    # Active profile switcher
    user_options = {u["user_id"]: f"{u['display_name']} ({u['user_id']})" for u in users}
    all_options = {"": t("no_active_user")} | user_options
    current_active = st.session_state.get("active_user") or ""
    if current_active not in all_options:
        current_active = ""

    chosen = st.selectbox(
        t("switch_user"),
        options=list(all_options.keys()),
        format_func=lambda k: all_options[k],
        index=list(all_options.keys()).index(current_active),
        key="settings_user_switcher",
    )
    if chosen != current_active:
        # Check if the chosen profile has a password
        chosen_user = next((u for u in users if u["user_id"] == chosen), None)
        needs_pin = chosen_user and chosen_user.get("password_hash") is not None
        if needs_pin:
            pin_input = st.text_input(
                "🔒 " + t("switch_user") + " — PIN",
                type="password",
                key="switch_pin_input",
            )
            if st.button(t("switch_user"), key="switch_pin_confirm"):
                if verify_password(db, chosen, pin_input):
                    st.session_state.active_user = chosen
                    set_active_user(chosen)
                    st.rerun()
                else:
                    st.error(f"❌ {t('user_pin_wrong')}")
        else:
            st.session_state.active_user = chosen or None
            set_active_user(chosen or None)
            st.rerun()

    # Current users table
    if users:
        for u in users:
            col_color, col_name, col_id, col_del = st.columns([0.3, 2, 1.5, 0.8])
            col_color.markdown(
                f"<span style='font-size:1.5rem; color:{u['color']}'>■</span>",
                unsafe_allow_html=True,
            )
            col_name.write(u["display_name"])
            col_id.code(u["user_id"])
            if col_del.button("✕", key=f"del_user_{u['user_id']}", help=t("settings_delete_user")):
                delete_user(db, u["user_id"])
                st.rerun()
    else:
        st.info(t("no_active_user"))

    st.markdown("---")

    # Add new profile form
    with st.expander(t("add_user"), expanded=not users):
        with st.form("add_user_form", clear_on_submit=True):
            col_name, col_id, col_color = st.columns([2, 1.5, 1])
            display_name = col_name.text_input(t("user_display_name"), placeholder="María")
            user_id_input = col_id.text_input(t("user_id_label"), placeholder="maria")
            color = col_color.color_picker(t("user_color"), value="#4fc3f7")
            col_pin1, col_pin2 = st.columns(2)
            pin1 = col_pin1.text_input(f"🔒 {t('user_pin_label')}", type="password")
            pin2 = col_pin2.text_input(t("user_pin_confirm"), type="password")
            submitted = st.form_submit_button(t("add_user"))
            if submitted:
                uid = user_id_input.strip().lower()
                if not uid or not display_name.strip():
                    st.error(t("settings_profile_required"))
                elif not uid.replace("-", "").replace("_", "").isalnum():
                    st.error(t("settings_profile_id_invalid"))
                elif pin1 and pin1 != pin2:
                    st.error(t("user_pin_mismatch"))
                else:
                    ok = create_user(
                        db,
                        user_id=uid,
                        display_name=display_name.strip(),
                        color=color,
                        password=pin1 if pin1 else None,
                    )
                    if ok:
                        st.success(t("user_created", user_id=uid))
                        st.rerun()
                    else:
                        st.warning(t("user_exists"))
