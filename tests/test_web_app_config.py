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


def test_sidebar_auto_state():
    """Sidebar should be in 'auto' state to allow st.navigation to work correctly."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("initial_sidebar_state") == "auto", (
        "initial_sidebar_state should be 'auto' to allow Streamlit's native navigation "
        "to manage the sidebar visibility."
    )


def test_sidebar_contains_controls():
    """Language and bank selectors are now in the sidebar for consistency."""
    source = WEB_APP.read_text(encoding="utf-8")
    assert "st.sidebar.selectbox" in source, (
        "st.sidebar.selectbox should be used for language or bank selection "
        "to maintain consistent controls across all pages."
    )


def test_page_config_layout_wide():
    """Wide layout gives more space on all screen sizes."""
    kwargs = _get_page_config_kwargs()
    assert kwargs.get("layout") == "wide"


def test_navigation_is_native():
    """Application must use native st.navigation."""
    source = WEB_APP.read_text(encoding="utf-8")
    assert "st.navigation" in source, "web_app.py must use st.navigation for routing"
    assert "st.Page" in source, "web_app.py must use st.Page objects"


def test_page_functions_defined():
    """Page wrapper functions must be defined for navigation."""
    funcs = _get_function_names()
    assert "page_import" in funcs
    assert "page_analytics" in funcs
    assert "page_manual" in funcs
    assert "page_settings" in funcs
