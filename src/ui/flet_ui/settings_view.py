# -*- coding: utf-8 -*-
"""Flet view: Settings — language preference + family user profiles."""
from typing import Callable, Dict

import flet as ft

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


def get_settings_view(
    page: ft.Page,
    t: Callable,
    config: Dict,
    global_state: Dict,
) -> ft.Control:
    """Build and return the settings view."""

    db = _get_db()
    status_text = ft.Text("", color=ft.Colors.GREEN_400)

    # -----------------------------------------------------------------------
    # State
    # -----------------------------------------------------------------------
    state = {
        "users": list_users(db),
        "active_user": global_state.get("active_user"),
        "new_id": "",
        "new_name": "",
        "new_color": "#4fc3f7",
        "new_pin": "",
        "new_pin2": "",
        # PIN dialog state for switching to a password-protected profile
        "pin_dialog_uid": None,
        "pin_dialog_value": "",
    }

    # -----------------------------------------------------------------------
    # User list display
    # -----------------------------------------------------------------------
    user_list_col = ft.Column(spacing=8)

    # PIN dialog overlay (shown inline when a protected user is selected)
    pin_dialog_field = ft.TextField(
        label=f"🔒 {t('user_pin_confirm')}",
        password=True,
        can_reveal_password=True,
        width=200,
        on_change=lambda e: state.update({"pin_dialog_value": e.data}),
    )
    pin_dialog_row = ft.Row(
        [
            pin_dialog_field,
            ft.ElevatedButton(
                t("switch_user"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            ft.TextButton(t("settings_cancel")),
        ],
        visible=False,
        spacing=12,
    )

    def build_user_list():
        rows = []
        for u in state["users"]:
            uid = u["user_id"]
            is_active = uid == state["active_user"]
            has_pin = bool(u.get("password_hash"))

            def make_activate(uid=uid, has_pin=has_pin):
                def _activate(e):
                    if has_pin:
                        # Show PIN dialog inline
                        state["pin_dialog_uid"] = uid
                        state["pin_dialog_value"] = ""
                        pin_dialog_field.value = ""

                        def _confirm_pin(e):
                            if verify_password(db, uid, state["pin_dialog_value"]):
                                state["active_user"] = uid
                                global_state["active_user"] = uid
                                set_active_user(uid)
                                status_text.value = f"✅ {t('active_user')}: {uid}"
                                status_text.color = ft.Colors.GREEN_400
                                pin_dialog_row.visible = False
                                build_user_list()
                                user_list_col.update()
                                pin_dialog_row.update()
                                status_text.update()
                            else:
                                status_text.value = f"❌ {t('user_pin_wrong')}"
                                status_text.color = ft.Colors.RED_400
                                status_text.update()

                        def _cancel_pin(e):
                            pin_dialog_row.visible = False
                            pin_dialog_row.update()

                        pin_dialog_row.controls[1].on_click = _confirm_pin
                        pin_dialog_row.controls[2].on_click = _cancel_pin
                        pin_dialog_row.visible = True
                        pin_dialog_row.update()
                    else:
                        state["active_user"] = uid
                        global_state["active_user"] = uid
                        set_active_user(uid)
                        status_text.value = f"✅ {t('active_user')}: {uid}"
                        status_text.color = ft.Colors.GREEN_400
                        build_user_list()
                        user_list_col.update()
                        status_text.update()
                return _activate

            def make_delete(uid=uid):
                def _delete(e):
                    delete_user(db, uid)
                    if state["active_user"] == uid:
                        state["active_user"] = None
                        global_state["active_user"] = None
                    state["users"] = list_users(db)
                    build_user_list()
                    user_list_col.update()
                return _delete

            pin_badge = ft.Icon(
                ft.Icons.LOCK_OUTLINE,
                size=14,
                color=ft.Colors.GREY_400,
                tooltip=t("user_pin_protected"),
            ) if has_pin else ft.Container(width=0)

            row = ft.Row([
                ft.Icon(ft.Icons.CIRCLE, color=u.get("color", "#4fc3f7"), size=16),
                ft.Text(u["display_name"], weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL, expand=True),
                pin_badge,
                ft.Text(f"({uid})", color=ft.Colors.GREY_400, size=12),
                ft.TextButton(
                    t("switch_user") if not is_active else f"✓ {t('active_user')}",
                    on_click=make_activate(),
                    disabled=is_active,
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    on_click=make_delete(),
                    icon_color=ft.Colors.RED_400,
                    tooltip=t("settings_delete_user"),
                ),
            ], spacing=8)
            rows.append(row)

        user_list_col.controls = rows if rows else [ft.Text(t("no_active_user"), color=ft.Colors.GREY_400, italic=True)]

    build_user_list()

    # -----------------------------------------------------------------------
    # Add user form
    # -----------------------------------------------------------------------
    new_id_field = ft.TextField(
        label=t("user_id_label"),
        hint_text="maria",
        width=180,
        on_change=lambda e: state.update({"new_id": e.data}),
    )
    new_name_field = ft.TextField(
        label=t("user_display_name"),
        hint_text="María",
        width=200,
        on_change=lambda e: state.update({"new_name": e.data}),
    )
    new_pin_field = ft.TextField(
        label=f"🔒 {t('user_pin_label')}",
        password=True,
        can_reveal_password=True,
        width=200,
        on_change=lambda e: state.update({"new_pin": e.data}),
    )
    new_pin2_field = ft.TextField(
        label=t("user_pin_confirm"),
        password=True,
        can_reveal_password=True,
        width=200,
        on_change=lambda e: state.update({"new_pin2": e.data}),
    )

    def handle_add(e):
        uid = state["new_id"].strip().lower()
        name = state["new_name"].strip()
        pin = state["new_pin"]
        pin2 = state["new_pin2"]
        if not uid or not name:
            status_text.value = f"❌ {t('settings_profile_required')}"
            status_text.color = ft.Colors.RED_400
            status_text.update()
            return
        if pin and pin != pin2:
            status_text.value = f"❌ {t('user_pin_mismatch')}"
            status_text.color = ft.Colors.RED_400
            status_text.update()
            return
        ok = create_user(db, user_id=uid, display_name=name, color=state["new_color"], password=pin if pin else None)
        if ok:
            status_text.value = t("user_created", user_id=uid)
            status_text.color = ft.Colors.GREEN_400
            state["users"] = list_users(db)
            new_id_field.value = ""
            new_name_field.value = ""
            new_pin_field.value = ""
            new_pin2_field.value = ""
            state["new_id"] = ""
            state["new_name"] = ""
            state["new_pin"] = ""
            state["new_pin2"] = ""
            build_user_list()
            user_list_col.update()
        else:
            status_text.value = t("user_exists")
            status_text.color = ft.Colors.ORANGE_400
        status_text.update()
        new_id_field.update()
        new_name_field.update()
        new_pin_field.update()
        new_pin2_field.update()

    add_btn = ft.ElevatedButton(
        t("add_user"),
        icon=ft.Icons.PERSON_ADD,
        on_click=handle_add,
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
    )

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------
    return ft.Column(
        [
            ft.Text(t("settings_title"), size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text(t("settings_users_title"), size=20, weight=ft.FontWeight.BOLD),
            ft.Text(t("settings_users_desc"), color=ft.Colors.GREY_400, size=14),
            ft.Container(height=8),
            user_list_col,

            ft.Container(height=16),
            ft.Text(t("add_user"), size=16, weight=ft.FontWeight.BOLD),
            ft.Row([new_id_field, new_name_field], spacing=16, wrap=True),
            ft.Row([new_pin_field, new_pin2_field], spacing=16, wrap=True),
            add_btn,

            ft.Container(height=16),
            pin_dialog_row,
            status_text,
        ],
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
