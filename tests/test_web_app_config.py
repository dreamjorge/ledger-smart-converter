"""Tests for web_app.py configuration and mobile UX."""
import ast
import sys
from pathlib import Path

WEB_APP = Path(__file__).parent.parent / "src" / "web_app.py"


def _get_page_config_kwargs():
    """Parse web_app.py and extract st.set_page_config keyword arguments (literals only)."""
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "set_page_config"
        ):
            result = {}
            for kw in node.keywords:
                try:
                    result[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    pass  # skip non-literal args like t("page_title")
            return result
    return {}


def _get_function_names():
    """Return set of all top-level function names defined in web_app.py."""
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def test_sidebar_collapsed_by_default():
    """Sidebar is info-only; controls live in main content so sidebar can start collapsed."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("initial_sidebar_state") == "collapsed", (
        "initial_sidebar_state should be 'collapsed' — language/bank selectors "
        "are now in the top bar, so the sidebar holds only optional info."
    )


def test_lang_and_bank_selectors_in_main_content():
    """Language and bank selectors must be in the main content area, not sidebar-only."""
    source = WEB_APP.read_text(encoding="utf-8")
    assert "sidebar.selectbox" not in source, (
        "st.sidebar.selectbox should not be used for language or bank selection. "
        "Move these controls to the main content so they are visible on mobile."
    )


def test_page_config_layout_wide():
    """Wide layout gives more space on all screen sizes."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("layout") == "wide"


def test_build_bank_map_defined():
    """build_bank_map helper must exist for testable bank mapping logic."""
    assert "build_bank_map" in _get_function_names()


def test_navigation_uses_tabs_not_sidebar_radio():
    """Primary navigation must use st.tabs so it is always visible on mobile.

    When navigation is sidebar-only, collapsing the sidebar on mobile makes
    it impossible to switch between Import and Analytics pages.
    """
    source = WEB_APP.read_text(encoding="utf-8")
    assert "st.tabs(" in source, "main() must use st.tabs for primary navigation"
    # sidebar radio for navigation must not be the routing mechanism anymore
    assert 'sidebar.radio' not in source, (
        "st.sidebar.radio should not drive page routing — use st.tabs instead "
        "so navigation is accessible even when the sidebar is hidden on mobile."
    )


def test_build_bank_map_with_config():
    """build_bank_map returns display_name→id mapping when config is provided."""
    sys.path.insert(0, str(WEB_APP.parent))
    from web_app import build_bank_map

    banks_cfg = {
        "santander_likeu": {"display_name": "Santander LikeU"},
        "hsbc": {"display_name": "HSBC Mexico"},
    }
    result = build_bank_map(banks_cfg, lambda k: k)
    assert result == {"Santander LikeU": "santander_likeu", "HSBC Mexico": "hsbc"}


def test_build_bank_map_fallback_empty_config():
    """build_bank_map falls back to translated defaults when config is empty."""
    sys.path.insert(0, str(WEB_APP.parent))
    from web_app import build_bank_map

    def mock_t(key):
        return {"bank_santander": "Santander", "bank_hsbc": "HSBC"}[key]

    result = build_bank_map({}, mock_t)
    assert result == {"Santander": "santander_likeu", "HSBC": "hsbc"}


def test_build_bank_map_uses_bid_when_no_display_name():
    """build_bank_map falls back to bank_id when display_name is missing."""
    sys.path.insert(0, str(WEB_APP.parent))
    from web_app import build_bank_map

    banks_cfg = {"mybank": {}}  # no display_name key
    result = build_bank_map(banks_cfg, lambda k: k)
    assert result == {"mybank": "mybank"}
