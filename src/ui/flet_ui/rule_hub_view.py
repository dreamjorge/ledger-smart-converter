import flet as ft
from pathlib import Path
from typing import Callable, Dict, List, Optional
import sys

# Add src to sys.path to resolve internal modules
sys.path.append(str(Path(__file__).parents[2]))
from services import rule_service
from ml_categorizer import TransactionCategorizer
from smart_matching import find_similar_merchants

def get_rule_hub_view(page: ft.Page, t: Callable, config: Dict):
    """
    Flet implementation of the Smart Rule Correction Hub.
    """
    # State
    state = {
        "search_query": "",
        "selected_merchant": "",
        "predicted_cat": "",
        "confidence": 0.0,
        "selected_category": "",
        "dest_account": "",
        "regex": "",
        "pending_count": 0
    }

    # Initialize ML
    ml = TransactionCategorizer()
    ml.load_model()

    # Paths
    root_dir = Path.cwd()
    rules_path = root_dir / "config" / "rules.yml"
    pending_path = root_dir / "config" / "rules.pending.yml"
    backup_dir = root_dir / "config" / "backups"

    state["pending_count"] = rule_service.get_pending_count(pending_path)

    # UI Components
    search_input = ft.TextField(
        label=t("fuzzy_search"),
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: (state.update({"search_query": e.data}), update_merchants()),
        expand=True
    )

    merchant_list = ft.ListView(expand=True, height=200, spacing=5)
    
    prediction_text = ft.Text(italic=True, color=ft.Colors.BLUE_400)
    
    category_dropdown = ft.Dropdown(
        label=t("select_category"),
        options=[
            ft.dropdown.Option("Expenses:Food:Groceries", t("cat_groceries")),
            ft.dropdown.Option("Expenses:Food:Restaurants", t("cat_restaurants")),
            ft.dropdown.Option("Expenses:Shopping:General", t("cat_general")),
            ft.dropdown.Option("Expenses:Services:Digital", t("cat_digitalservices")),
            ft.dropdown.Option("Expenses:Other", t("cat_other")),
        ],
        on_change=lambda e: (state.update({"selected_category": e.data}), page.update())
    )

    regex_input = ft.TextField(
        label=t("regex_pattern"),
        on_change=lambda e: (state.update({"regex": e.data}), page.update())
    )

    # Handlers
    def update_merchants():
        # This would normally pull from all unique merchants in CSV/DB
        # For simplicity, we use a mock list for the prototype transition
        mock_merchants = ["WALMART", "OXXO", "UBER", "NETFLIX", "AMAZON", "7-ELEVEN", "SAMS CLUB"]
        similar = find_similar_merchants(state["search_query"], mock_merchants)
        
        merchant_list.controls = [
            ft.ListTile(
                title=ft.Text(m),
                subtitle=ft.Text(f"Score: {score}"),
                on_click=lambda e, name=m: select_merchant(name)
            ) for m, score in similar
        ]
        page.update()

    def select_merchant(name):
        state["selected_merchant"] = name
        state["regex"] = name.lower()
        regex_input.value = state["regex"]
        
        # Predict
        preds = ml.predict(name)
        if preds:
            cat, conf = preds[0]
            state["predicted_cat"] = cat
            state["confidence"] = conf
            prediction_text.value = t("ml_prediction", cat=cat, conf=conf)
        else:
            prediction_text.value = "No prediction available"
        
        page.update()

    def handle_save(e):
        if not state["selected_merchant"] or not state["selected_category"]:
            page.snack_bar = ft.SnackBar(ft.Text("Please select merchant and category!"))
            page.snack_bar.open = True
            page.update()
            return
            
        success, res = rule_service.stage_rule_change(
            rules_path=rules_path,
            pending_path=pending_path,
            merchant_name=state["selected_merchant"],
            regex_pattern=state["regex"],
            expense_account=state["selected_category"],
            bucket_tag="correction", # Default for now
            db_path=root_dir / "data" / "ledger.db"
        )
        
        if success:
            state["pending_count"] = res["pending_count"]
            pending_status.value = f"Pending rules: {state['pending_count']}"
            page.snack_bar = ft.SnackBar(ft.Text(t("rule_saved", merchant=state["selected_merchant"])))
            page.snack_bar.open = True
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Conflict: {res.get('conflicts')}"))
            page.snack_bar.open = True
        page.update()

    def handle_merge(e):
        success, res = rule_service.merge_pending_rules(
            rules_path=rules_path,
            pending_path=pending_path,
            backup_dir=backup_dir
        )
        if success:
            state["pending_count"] = 0
            pending_status.value = "All rules merged!"
            page.snack_bar = ft.SnackBar(ft.Text("Rules merged and AI retrained!"))
            page.snack_bar.open = True
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Merge error: {res.get('status')}"))
            page.snack_bar.open = True
        page.update()

    # View Construction
    pending_status = ft.Text(f"Pending rules: {state['pending_count']}", weight=ft.FontWeight.BOLD)

    return ft.Column(
        [
            ft.Text(t("rule_hub_title"), size=32, weight=ft.FontWeight.BOLD),
            ft.Text(t("rule_hub_desc"), color=ft.Colors.GREY_400),
            ft.Divider(),
            
            ft.Row([
                ft.Column([
                    ft.Text(t("smart_lookup"), size=20, weight=ft.FontWeight.W_500),
                    search_input,
                    merchant_list,
                ], expand=True),
                ft.VerticalDivider(),
                ft.Column([
                    ft.Text("Rule Definition", size=20, weight=ft.FontWeight.W_500),
                    prediction_text,
                    category_dropdown,
                    regex_input,
                    ft.ElevatedButton(t("save_rule"), icon=ft.Icons.SAVE, on_click=handle_save, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                ], expand=True),
            ], expand=True),
            
            ft.Divider(),
            ft.Row([
                pending_status,
                ft.ElevatedButton("Merge & Apply All Rules", icon=ft.Icons.MERGE_TYPE, on_click=handle_merge, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ],
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
