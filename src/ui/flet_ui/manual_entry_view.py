# -*- coding: utf-8 -*-
"""Flet view for manual single-transaction entry."""
import datetime
import threading
from pathlib import Path
from typing import Callable, Dict

import flet as ft

from services.manual_entry_service import (
    get_category_label,
    load_accounts_from_config,
    load_categories_from_rules,
    submit_manual_transaction,
)


def get_manual_entry_view(page: ft.Page, t: Callable, config: Dict, lang: str = "es") -> ft.Control:
    """Build and return the manual transaction entry view.

    Args:
        page: The Flet page instance.
        t: Translation helper callable.
        config: App configuration dict (may contain config_dir, db_path).
    """
    root_dir = Path.cwd()
    config_dir = config.get("config_dir", root_dir / "config")
    db_path = config.get("db_path", None)

    rules_path = config_dir / "rules.yml"
    accounts_path = config_dir / "accounts.yml"

    categories = load_categories_from_rules(rules_path)
    accounts = load_accounts_from_config(accounts_path, rules_path)

    # State
    state: Dict = {
        "date": datetime.date.today().isoformat(),
        "amount": "",
        "description": "",
        "canonical_account_id": next(iter(accounts), ""),
        "transaction_type": "withdrawal",
        "category": categories[0] if categories else "",
    }

    # UI components
    status_text = ft.Text("", color=ft.Colors.GREEN_400)
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)

    date_field = ft.TextField(
        label=t("field_date"),
        hint_text="YYYY-MM-DD",
        value=state["date"],
        width=200,
        on_change=lambda e: state.update({"date": e.data}),
    )
    amount_field = ft.TextField(
        label=t("field_amount"),
        hint_text="0.00",
        value="",
        width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: state.update({"amount": e.data}),
    )
    description_field = ft.TextField(
        label=t("field_description"),
        expand=True,
        on_change=lambda e: state.update({"description": e.data}),
    )

    account_dropdown = ft.Dropdown(
        label=t("field_bank_account"),
        width=300,
        options=[
            ft.dropdown.Option(canonical_id, label)
            for canonical_id, label in accounts.items()
        ],
        value=state["canonical_account_id"],
        on_select=lambda e: state.update({"canonical_account_id": e.control.value}),
    )

    type_dropdown = ft.Dropdown(
        label=t("field_transaction_type"),
        width=200,
        options=[
            ft.dropdown.Option("withdrawal", t("type_withdrawal")),
            ft.dropdown.Option("transfer", t("type_transfer")),
            ft.dropdown.Option("deposit", t("type_deposit")),
        ],
        value="withdrawal",
        on_select=lambda e: state.update({"transaction_type": e.control.value}),
    )

    category_dropdown = ft.Dropdown(
        label=t("field_category"),
        width=350,
        options=[ft.dropdown.Option(c, get_category_label(c, lang)) for c in categories],
        value=state["category"],
        on_select=lambda e: state.update({"category": e.control.value}),
    )

    save_btn = ft.ElevatedButton(
        t("nav_manual_entry"),
        icon=ft.Icons.ADD_CIRCLE,
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        height=50,
    )

    def handle_save(e):
        status_text.value = ""
        progress_ring.visible = True
        save_btn.disabled = True
        page.update()

        def _run():
            # Resolve bank_id and account_id from accounts.yml
            import yaml
            try:
                with open(accounts_path, encoding="utf-8") as f:
                    acc_cfg = yaml.safe_load(f) or {}
                canonical_accounts = acc_cfg.get("canonical_accounts", {})
                canonical_account_id = state["canonical_account_id"]
                acc_entry = canonical_accounts.get(canonical_account_id, {})
                bank_ids = acc_entry.get("bank_ids", [])
                account_ids_list = acc_entry.get("account_ids", [])
                bank_id = bank_ids[0] if bank_ids else canonical_account_id
                account_id = account_ids_list[0] if account_ids_list else canonical_account_id

                try:
                    amount_val = float(state["amount"])
                except (ValueError, TypeError):
                    status_text.value = t("manual_entry_validation_error", errors=t("manual_entry_invalid_amount"))
                    status_text.color = ft.Colors.RED_400
                    return

                ok, errors = submit_manual_transaction(
                    date=state["date"],
                    description=state["description"],
                    amount=amount_val,
                    bank_id=bank_id,
                    account_id=account_id,
                    canonical_account_id=canonical_account_id,
                    transaction_type=state["transaction_type"],
                    category=state["category"],
                    db_path=Path(db_path) if db_path else None,
                    user_id=config.get("active_user"),
                )

                if ok:
                    status_text.value = t("manual_entry_success")
                    status_text.color = ft.Colors.GREEN_400
                    # Reset amount and description fields
                    amount_field.value = ""
                    description_field.value = ""
                    state["amount"] = ""
                    state["description"] = ""
                elif errors == ["duplicate"]:
                    status_text.value = t("manual_entry_duplicate")
                    status_text.color = ft.Colors.ORANGE_400
                else:
                    status_text.value = t("manual_entry_validation_error", errors=", ".join(errors))
                    status_text.color = ft.Colors.RED_400

            except Exception as ex:
                status_text.value = f"Error: {ex}"
                status_text.color = ft.Colors.RED_400
            finally:
                progress_ring.visible = False
                save_btn.disabled = False
                page.update()

        threading.Thread(target=_run, daemon=True).start()

    save_btn.on_click = handle_save

    return ft.Column(
        [
            ft.Text(t("manual_entry_title"), size=32, weight=ft.FontWeight.BOLD),
            ft.Text(t("manual_entry_desc"), size=16, color=ft.Colors.GREY_400),
            ft.Divider(),

            ft.Row([date_field, amount_field], spacing=20),
            description_field,
            ft.Row([account_dropdown, type_dropdown], spacing=20, wrap=True),
            category_dropdown,

            ft.Container(height=10),
            ft.Row([save_btn, progress_ring], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            status_text,
        ],
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
