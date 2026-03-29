from pathlib import Path

import pandas as pd


def test_ui_pages_importable():
    import ui.pages.analytics_page  # noqa: F401
    import ui.pages.import_page  # noqa: F401
    import ui.pages.manual_entry_page  # noqa: F401
    import ui.pages.settings_page  # noqa: F401


def test_flet_import_view_does_not_reference_removed_filepicker_result_event() -> None:
    content = Path("src/ui/flet_ui/import_view.py").read_text(encoding="utf-8")

    assert "FilePickerResultEvent" not in content


def test_flet_import_view_uses_async_pick_files_api() -> None:
    content = Path("src/ui/flet_ui/import_view.py").read_text(encoding="utf-8")

    assert "on_result=" not in content
    assert "await main_picker.pick_files" in content
    assert "await pdf_picker.pick_files" in content
    assert "page.services.extend" in content


def test_flet_dropdowns_use_on_select_not_on_change() -> None:
    for relative_path in (
        "src/ui/flet_ui/import_view.py",
        "src/ui/flet_ui/manual_entry_view.py",
        "src/ui/flet_ui/analytics_view.py",
        "src/ui/flet_ui/rule_hub_view.py",
    ):
        content = Path(relative_path).read_text(encoding="utf-8")
        assert "ft.Dropdown(" in content
        assert "on_select=" in content


class _DummyPage:
    def __init__(self) -> None:
        self.overlay = []
        self.services = []
        self.snack_bar = None

    def update(self) -> None:
        pass


def test_flet_import_view_builds_with_current_flet_api() -> None:
    from ui.flet_ui.import_view import get_import_view

    view = get_import_view(
        page=_DummyPage(),
        t=lambda key, **kwargs: key,
        config={},
    )

    assert view is not None


def test_flet_manual_entry_view_builds_with_current_flet_api() -> None:
    from ui.flet_ui.manual_entry_view import get_manual_entry_view

    view = get_manual_entry_view(
        page=_DummyPage(),
        t=lambda key, **kwargs: key,
        config={},
    )

    assert view is not None


def test_flet_analytics_view_builds_with_current_flet_api(monkeypatch) -> None:
    from ui.flet_ui import analytics_view

    monkeypatch.setattr(analytics_view.data_service, "load_transactions", lambda bank_id: pd.DataFrame())

    view = analytics_view.get_analytics_view(
        page=_DummyPage(),
        t=lambda key, **kwargs: key,
        config={},
    )

    assert view is not None


def test_flet_layout_builds_with_current_flet_api() -> None:
    from ui.flet_ui.layout import AppLayout, create_header
    import flet as ft

    content = ft.Container()
    layout = AppLayout(
        page=_DummyPage(),
        content=content,
        selected_index=0,
        on_navigation_change=lambda index: None,
        lang="es",
    )
    header = create_header("es")

    assert layout is not None
    assert header is not None
