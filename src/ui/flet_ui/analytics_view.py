import flet as ft
from pathlib import Path
from typing import Callable, Dict, Optional
import sys
import pandas as pd

# Add src to sys.path to resolve internal modules
sys.path.append(str(Path(__file__).parents[2]))
from services import data_service
from services import ui_service
from ui.flet_ui.components import MetricCard, ChartContainer

def get_analytics_view(page: ft.Page, t: Callable, config: Dict):
    """
    Flet implementation of the Analytics Dashboard.
    """
    # State
    state = {
        "selected_bank_id": "santander_likeu",
        "df": pd.DataFrame(),
        "loading": False
    }

    # UI Components
    metrics_row = ft.ResponsiveRow(spacing=20, controls=[])
    charts_col = ft.Column(spacing=20, expand=True)
    status_text = ft.Text("")

    def refresh_data(e=None):
        state["loading"] = True
        status_text.value = "Loading data..."
        page.update()

        try:
            # Load transactions
            bank_id = state["selected_bank_id"]
            df = data_service.load_transactions(bank_id)
            state["df"] = df
            
            if df.empty:
                status_text.value = t("no_data")
                metrics_row.controls = []
                charts_col.controls = []
            else:
                status_text.value = ""
                # Get Stats using analytics_service
                from services.analytics_service import calculate_categorization_stats
                stats = calculate_categorization_stats(df)
                
                # Update Metrics
                metrics_row.controls = [
                    ft.Column([MetricCard(t("metric_total_txns"), str(stats.get("total", 0)), ft.Icons.LIST_ALT)], col={"sm": 6, "md": 3}),
                    ft.Column([MetricCard(t("metric_total_spent"), ui_service.format_currency(stats.get("total_spent", 0.0)), ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.RED_400)], col={"sm": 6, "md": 3}),
                    ft.Column([MetricCard(t("metric_categorized"), ui_service.format_percentage(stats.get("coverage_pct", 0.0)), ft.Icons.PIE_CHART_OUTLINED, color=ft.Colors.GREEN_400)], col={"sm": 6, "md": 3}),
                    ft.Column([MetricCard(t("metric_withdrawals"), str(stats.get("type_counts", {}).get("withdrawal", 0)), ft.Icons.ARROW_DOWNWARD, color=ft.Colors.ORANGE_400)], col={"sm": 6, "md": 3}),
                ]

                def tc(cat):
                    return t(f"cat_{cat.lower()}")

                # Update Charts
                pie_fig = ui_service.get_spending_share_fig(stats, t, tc)
                bar_fig = ui_service.get_monthly_trends_fig(stats, t, tc)
                
                charts_col.controls = [
                    ft.Row([
                        ChartContainer(t("chart_spending_share"), ft.PlotlyChart(pie_fig, expand=True), expand=True),
                    ], expand=True),
                    ft.Row([
                        ChartContainer(t("monthly_spending_trends_title"), ft.PlotlyChart(bar_fig, expand=True), expand=True),
                    ], expand=True),
                ]
        except Exception as ex:
            status_text.value = f"Error: {str(ex)}"
            print(f"Analytics Error: {ex}")

        state["loading"] = False
        page.update()

    # Initial Load
    refresh_data()

    return ft.Column(
        [
            ft.Row([
                ft.Text(t("analytics_title"), size=32, weight=ft.FontWeight.BOLD),
                ft.Row(expand=True),
                ft.Dropdown(
                    label=t("select_bank"),
                    width=250,
                    options=[
                        ft.dropdown.Option("santander_likeu", t("bank_santander")),
                        ft.dropdown.Option("hsbc", t("bank_hsbc")),
                    ],
                    value=state["selected_bank_id"],
                    on_change=lambda e: (state.update({"selected_bank_id": e.data}), refresh_data()),
                ),
                ft.IconButton(ft.Icons.REFRESH, on_click=refresh_data, tooltip="Refresh Data"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Divider(),
            status_text,
            metrics_row,
            ft.Container(height=20),
            charts_col,
        ],
        expand=True,
        spacing=0,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
