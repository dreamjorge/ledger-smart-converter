import flet as ft
from ui.flet_ui.layout import AppLayout, create_header
from ui.flet_ui.import_view import get_import_view
from ui.flet_ui.analytics_view import get_analytics_view
from ui.flet_ui.rule_hub_view import get_rule_hub_view
from ui.flet_ui.manual_entry_view import get_manual_entry_view
from ui.flet_ui.settings_view import get_settings_view
from translations import TRANSLATIONS
from services.user_service import get_pref, get_active_user

def main(page: ft.Page):
    # Configuration
    page.title = "Ledger Smart Converter (Flet Desktop)"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0
    page.window.width = 1200
    page.window.height = 800

    # Fonts & Theme
    page.fonts = {
        "Outfit": "https://raw.githubusercontent.com/Outfit-Fonts/Outfit/main/fonts/ttf/Outfit-Regular.ttf",
        "Inter": "https://rsms.me/inter/font-files/Inter-Regular.woff2?v=3.19"
    }
    page.theme = ft.Theme(
        font_family="Inter",
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.BLUE_400,
            secondary=ft.Colors.TEAL_400,
            surface=ft.Colors.SURFACE,
            error=ft.Colors.RED_400,
        )
    )

    # Global state — language and active user loaded from prefs.json
    global_state = {
        "lang": get_pref("lang", "es"),
        "selected_nav_index": 0,
        "active_user": get_active_user(),
    }

    def t(key, **kwargs):
        translation = TRANSLATIONS.get(global_state["lang"], {}).get(key, key)
        return translation.format(**kwargs) if kwargs else translation

    def _config():
        return {"active_user": global_state["active_user"]}

    # View Builders
    def get_import_page():
        return get_import_view(page=page, t=t, config=_config())

    def get_analytics_page():
        return get_analytics_view(page=page, t=t, config=_config())

    def get_rule_hub_page():
        return get_rule_hub_view(page=page, t=t, config=_config())

    def get_manual_entry_page():
        return get_manual_entry_view(page=page, t=t, config=_config(), lang=global_state["lang"])

    def get_settings_page():
        return get_settings_view(page=page, t=t, config=_config(), global_state=global_state)

    # Route Handling Logic
    content_map = {
        0: get_import_page,
        1: get_analytics_page,
        2: get_rule_hub_page,
        3: get_manual_entry_page,
        4: get_settings_page,
    }

    content_area = ft.Container(content=content_map[0](), expand=True)

    def on_nav_change(index):
        global_state["selected_nav_index"] = index
        content_area.content = content_map[index]()
        page.update()

    # Build Header and Main Layout
    header = create_header(global_state["lang"])
    layout = AppLayout(
        page=page,
        content=content_area,
        selected_index=global_state["selected_nav_index"],
        on_navigation_change=on_nav_change,
        lang=global_state["lang"]
    )

    page.add(
        header,
        layout
    )

if __name__ == "__main__":
    ft.run(main)
