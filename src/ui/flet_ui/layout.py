import flet as ft
from typing import Callable, Optional
from translations import TRANSLATIONS

class AppLayout(ft.Row):
    def __init__(
        self,
        page: ft.Page,
        content: ft.Control,
        selected_index: int = 0,
        on_navigation_change: Optional[Callable] = None,
        lang: str = "en"
    ):
        super().__init__()
        self.page = page
        self.main_content = content
        self.selected_index = selected_index
        self.on_navigation_change = on_navigation_change
        self.lang = lang
        
        self.expand = True
        self.spacing = 0
        
        # Translations helper
        self.t = lambda key: TRANSLATIONS.get(self.lang, {}).get(key, key)
        
        # Sidebar (Navigation Rail)
        self.rail = ft.NavigationRail(
            selected_index=self.selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                    selected_icon=ft.Icons.UPLOAD_FILE,
                    label=self.t("nav_import"),
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INSERT_CHART_OUTLINED,
                    selected_icon=ft.Icons.INSERT_CHART,
                    label=self.t("nav_analytics"),
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label=self.t("config"),
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    selected_icon=ft.Icons.ADD_CIRCLE,
                    label=self.t("nav_manual_entry"),
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.MANAGE_ACCOUNTS_OUTLINED,
                    selected_icon=ft.Icons.MANAGE_ACCOUNTS,
                    label=self.t("nav_settings"),
                ),
            ],
            on_change=self._handle_nav_change,
            bgcolor=ft.Colors.SURFACE_VARIANT,
        )
        
        # Content Area
        self.content_container = ft.Container(
            content=self.main_content,
            expand=True,
            padding=ft.padding.all(30),
            bgcolor=ft.Colors.SURFACE,
        )
        
        self.controls = [
            self.rail,
            ft.VerticalDivider(width=1),
            self.content_container,
        ]

    def _handle_nav_change(self, e):
        if self.on_navigation_change:
            self.on_navigation_change(e.control.selected_index)

def create_header(lang: str = "en") -> ft.Control:
    t = lambda key: TRANSLATIONS.get(lang, {}).get(key, key)
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.BLUE_400, size=30),
                ft.Text(
                    t("app_title"),
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_400,
                ),
                ft.VerticalDivider(),
                ft.Text("Flet Desktop v1.0", size=14, color=ft.Colors.GREY_500),
                ft.Row(expand=True), # Spacer
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.padding.only(left=20, right=20, top=10, bottom=10),
        bgcolor=ft.Colors.SURFACE_VARIANT,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )
